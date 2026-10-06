"""
SQLite cache for Pirmasens Ontop SPARQL (toilet / plots / solarthermie / city).

Probe tier: online MCP with LIMIT.
Full tier: pre-warmed uncapped results for Zaha offline deploy.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mini_marie.cache_paths import mini_marie_cache_root
from mini_marie.cache_tiers import (
    TIER_FULL,
    TIER_PROBE,
    CacheMissError,
    make_cache_key,
    row_limit_for_tier,
)
from mini_marie.sparql_utils import apply_sparql_limit, normalize_sparql
from mini_marie.zaha.twa_city.limits import online_sparql_delay_seconds
from mini_marie.zaha.twa_city.pirmasens_ontop_operations import resolve_pirmasens_endpoint
from mini_marie.zaha.twa_city.sparql_plans import DEFAULT_ONLINE_LIMIT
from mini_marie.zaha.twa_city.twa_city_operations import execute_sparql

# Cap full-tier warm rows (keeps deploy/upload size reasonable for Zaha).
DEFAULT_WARM_LIMIT = 500
WARM_LIMIT_BY_ENDPOINT: Dict[str, int] = {
    "toilet": 50,
    "plots": 50,
    "solarthermie": 50,
    "city": 500,
}

RUN_SPARQL_TOOL = "run_sparql"
_LIMIT_RE = re.compile(r"\bLIMIT\s+\d+\b", re.I)


def cache_dir() -> Path:
    d = mini_marie_cache_root() / "twa_city"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return cache_dir() / "pirmasens_ontop_cache.sqlite"


def _canonical_args(args: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key in sorted(args):
        val = args[key]
        if key == "query" and isinstance(val, str):
            out[key] = normalize_sparql(val)
        else:
            out[key] = val
    return out


def _strip_limit(query: str) -> str:
    return _LIMIT_RE.sub("", query).strip()


class PirmasensOntopCache:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path or db_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        except sqlite3.OperationalError:
            pass
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS atomic_calls (
                cache_key TEXT PRIMARY KEY,
                tool TEXT NOT NULL,
                endpoint_id TEXT NOT NULL,
                args_json TEXT NOT NULL,
                tier TEXT NOT NULL,
                row_limit INTEGER,
                endpoint_url TEXT,
                fetched_at REAL NOT NULL,
                elapsed_ms INTEGER,
                row_count INTEGER NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS atomic_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT NOT NULL,
                row_index INTEGER NOT NULL,
                data_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_pirmasens_rows_key ON atomic_rows(cache_key);
            CREATE INDEX IF NOT EXISTS idx_pirmasens_calls_endpoint ON atomic_calls(endpoint_id);
            """
        )
        self._conn.commit()

    def has_tier(self, tool: str, args: Dict[str, Any], tier: str) -> bool:
        key = make_cache_key(
            tool, _canonical_args(args), tier, probe_limit=DEFAULT_ONLINE_LIMIT
        )
        cur = self._conn.execute(
            "SELECT 1 FROM atomic_calls WHERE cache_key = ? LIMIT 1", (key,)
        )
        return cur.fetchone() is not None

    def has_full(self, tool: str, args: Dict[str, Any]) -> bool:
        return self.has_tier(tool, args, TIER_FULL)

    def get(self, tool: str, args: Dict[str, Any], tier: str) -> Optional[List[Dict[str, Any]]]:
        if not self.has_tier(tool, args, tier):
            return None
        key = make_cache_key(
            tool, _canonical_args(args), tier, probe_limit=DEFAULT_ONLINE_LIMIT
        )
        cur = self._conn.execute(
            "SELECT data_json FROM atomic_rows WHERE cache_key = ? ORDER BY row_index",
            (key,),
        )
        return [json.loads(r["data_json"]) for r in cur]

    def put(
        self,
        tool: str,
        args: Dict[str, Any],
        rows: List[Dict[str, Any]],
        *,
        tier: str,
        row_limit: Optional[int],
        endpoint_url: str,
        elapsed_ms: int,
        status: str = "pass",
    ) -> str:
        key = make_cache_key(
            tool, _canonical_args(args), tier, probe_limit=DEFAULT_ONLINE_LIMIT
        )
        endpoint_id = str(args.get("endpoint_id") or "")
        self._conn.execute("DELETE FROM atomic_rows WHERE cache_key = ?", (key,))
        self._conn.execute("DELETE FROM atomic_calls WHERE cache_key = ?", (key,))
        self._conn.execute(
            """
            INSERT INTO atomic_calls
            (cache_key, tool, endpoint_id, args_json, tier, row_limit, endpoint_url,
             fetched_at, elapsed_ms, row_count, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                tool,
                endpoint_id,
                json.dumps(_canonical_args(args)),
                tier,
                row_limit,
                endpoint_url,
                time.time(),
                elapsed_ms,
                len(rows),
                status,
            ),
        )
        for i, row in enumerate(rows):
            self._conn.execute(
                "INSERT INTO atomic_rows (cache_key, row_index, data_json) VALUES (?, ?, ?)",
                (key, i, json.dumps(row, ensure_ascii=False)),
            )
        self._conn.commit()
        return key

    def status_rows(self) -> List[Dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT endpoint_id, tier, COUNT(*) AS entries, SUM(row_count) AS rows
            FROM atomic_calls
            GROUP BY endpoint_id, tier
            ORDER BY endpoint_id, tier
            """
        )
        return [dict(r) for r in cur]


def invoke_run_sparql(
    endpoint_id: str,
    query: str,
    *,
    mode: str = "online",
    limit: int = DEFAULT_ONLINE_LIMIT,
    warm_limit: int = DEFAULT_WARM_LIMIT,
    use_cache: bool = True,
    cache: Optional[PirmasensOntopCache] = None,
    timeout: int = 120,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Execute or load cached SPARQL on a Pirmasens Ontop endpoint."""
    q = normalize_sparql(query)
    args = {"endpoint_id": endpoint_id, "query": q}
    endpoint_url = resolve_pirmasens_endpoint(endpoint_id)

    if mode == "offline":
        tier = TIER_FULL
        allow_remote = False
        cap = WARM_LIMIT_BY_ENDPOINT.get(endpoint_id, warm_limit)
        exec_query = apply_sparql_limit(_strip_limit(q), cap)
    elif mode == "warm":
        tier = TIER_FULL
        allow_remote = True
        cap = WARM_LIMIT_BY_ENDPOINT.get(endpoint_id, warm_limit)
        exec_query = apply_sparql_limit(_strip_limit(q), cap)
    else:
        tier = TIER_PROBE
        allow_remote = True
        exec_query = apply_sparql_limit(q, int(limit))

    ck = cache or PirmasensOntopCache()
    own = cache is None
    meta: Dict[str, Any] = {
        "tool": RUN_SPARQL_TOOL,
        "mode": mode,
        "cache_tier": tier,
        "from_cache": False,
        "endpoint_id": endpoint_id,
    }

    cache_miss = False
    if use_cache:
        cached = ck.get(RUN_SPARQL_TOOL, args, tier)
        if cached is not None:
            meta["from_cache"] = True
            if own:
                ck.close()
            if tier == TIER_PROBE and limit:
                return cached[: int(limit)], meta
            return cached, meta
        if mode == "online":
            full_rows = ck.get(RUN_SPARQL_TOOL, args, TIER_FULL)
            if full_rows is not None:
                meta["from_cache"] = True
                meta["cache_tier"] = TIER_FULL
                if own:
                    ck.close()
                return full_rows[: int(limit)], meta
        cache_miss = True

    if not allow_remote:
        if own:
            ck.close()
        raise CacheMissError(
            f"Missing full cache for run_sparql endpoint={endpoint_id!r}. "
            "Warm with: python -m mini_marie.zaha.twa_city.warm_pirmasens_ontop_cache --page-questions"
        )

    if cache_miss and tier == TIER_PROBE:
        delay = online_sparql_delay_seconds()
        if delay > 0:
            time.sleep(delay)

    started = time.perf_counter()
    rows = execute_sparql(exec_query, endpoint_url, timeout=timeout)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    ck.put(
        RUN_SPARQL_TOOL,
        args,
        rows,
        tier=tier,
        row_limit=row_limit_for_tier(tier, probe_limit=int(limit)),
        endpoint_url=endpoint_url,
        elapsed_ms=elapsed_ms,
        status="pass" if rows else "empty",
    )
    meta["elapsed_ms"] = elapsed_ms
    if own:
        ck.close()
    if tier == TIER_PROBE and limit:
        return rows[: int(limit)], meta
    return rows, meta


def warm_run_sparql(
    endpoint_id: str,
    query: str,
    *,
    force: bool = False,
    cache: Optional[PirmasensOntopCache] = None,
    timeout: int = 120,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    ck = cache or PirmasensOntopCache()
    own = cache is None
    args = {"endpoint_id": endpoint_id, "query": normalize_sparql(query)}
    if force:
        key = make_cache_key(
            RUN_SPARQL_TOOL, _canonical_args(args), TIER_FULL, probe_limit=DEFAULT_ONLINE_LIMIT
        )
        ck._conn.execute("DELETE FROM atomic_rows WHERE cache_key = ?", (key,))
        ck._conn.execute("DELETE FROM atomic_calls WHERE cache_key = ?", (key,))
        ck._conn.commit()
    rows, meta = invoke_run_sparql(
        endpoint_id,
        query,
        mode="warm",
        use_cache=not force,
        cache=ck,
        timeout=timeout,
    )
    if own:
        ck.close()
    return rows, meta


def get_cache_status_text() -> str:
    path = db_path()
    if not path.exists():
        return (
            f"No cache at {path}\n"
            "Warm: python -m mini_marie.zaha.twa_city.warm_pirmasens_ontop_cache --page-questions"
        )
    size_mb = path.stat().st_size / 1e6
    ck = PirmasensOntopCache(path)
    try:
        rows = ck.status_rows()
        lines = [f"DB: {path}", f"Size: {size_mb:.2f} MB", "endpoint_id\ttier\tentries\trows"]
        for r in rows:
            lines.append(
                f"{r['endpoint_id']}\t{r['tier']}\t{r['entries']}\t{r['rows']}"
            )
        full_count = sum(1 for r in rows if r["tier"] == TIER_FULL)
        return "\n".join(lines) + f"\n\nFull-tier entries: {full_count}"
    finally:
        ck.close()
