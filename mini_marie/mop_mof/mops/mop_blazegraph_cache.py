"""SQLite cache for remote OntoMOPs Blazegraph query results."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from mini_marie.cache_paths import mini_marie_cache_root


def cache_dir() -> Path:
    d = mini_marie_cache_root() / "mop_blazegraph"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return cache_dir() / "query_cache.sqlite"


def normalize_sparql(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").strip())


def sparql_hash(query: str) -> str:
    return hashlib.sha256(normalize_sparql(query).encode("utf-8")).hexdigest()


class MopBlazegraphCache:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or db_path()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS query_cache (
                    cache_key TEXT PRIMARY KEY,
                    tool TEXT NOT NULL,
                    args_json TEXT NOT NULL,
                    endpoint TEXT,
                    fetched_at REAL NOT NULL,
                    row_count INTEGER NOT NULL,
                    rows_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sparql_cache (
                    query_hash TEXT PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    endpoint TEXT,
                    fetched_at REAL NOT NULL,
                    row_count INTEGER NOT NULL,
                    rows_json TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def make_key(tool: str, args: Dict[str, Any]) -> str:
        payload = json.dumps({"tool": tool, "args": args}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def put(
        self,
        tool: str,
        args: Dict[str, Any],
        endpoint: str,
        rows: List[Dict[str, Any]],
    ) -> str:
        key = self.make_key(tool, args)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO query_cache
                (cache_key, tool, args_json, endpoint, fetched_at, row_count, rows_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    tool,
                    json.dumps(args, sort_keys=True, ensure_ascii=False),
                    endpoint,
                    time.time(),
                    len(rows),
                    json.dumps(rows, ensure_ascii=False),
                ),
            )
        return key

    def get(self, tool: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        key = self.make_key(tool, args)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM query_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_payload(row)

    def put_query(
        self,
        query: str,
        endpoint: str,
        rows: List[Dict[str, Any]],
    ) -> str:
        qhash = sparql_hash(query)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sparql_cache
                (query_hash, query_text, endpoint, fetched_at, row_count, rows_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    qhash,
                    normalize_sparql(query),
                    endpoint,
                    time.time(),
                    len(rows),
                    json.dumps(rows, ensure_ascii=False),
                ),
            )
        return qhash

    def get_query(self, query: str) -> Optional[Dict[str, Any]]:
        qhash = sparql_hash(query)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT query_hash AS cache_key, query_text, endpoint, fetched_at, row_count, rows_json FROM sparql_cache WHERE query_hash = ?",
                (qhash,),
            ).fetchone()
        if not row:
            return None
        payload = {
            "cache_key": row["cache_key"],
            "query": row["query_text"],
            "rows": json.loads(row["rows_json"]),
            "meta": {
                "endpoint": row["endpoint"],
                "fetched_at_unix": row["fetched_at"],
                "row_count": row["row_count"],
            },
        }
        return payload

    @staticmethod
    def _row_to_payload(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "cache_key": row["cache_key"],
            "tool": row["tool"],
            "args": json.loads(row["args_json"]),
            "rows": json.loads(row["rows_json"]),
            "meta": {
                "endpoint": row["endpoint"],
                "fetched_at_unix": row["fetched_at"],
                "row_count": row["row_count"],
            },
        }

    def last_known_endpoint(self) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT endpoint FROM query_cache
                WHERE endpoint IS NOT NULL AND endpoint != ''
                ORDER BY fetched_at DESC LIMIT 1
                """
            ).fetchone()
            if row:
                return str(row["endpoint"])
            row = conn.execute(
                """
                SELECT endpoint FROM sparql_cache
                WHERE endpoint IS NOT NULL AND endpoint != ''
                ORDER BY fetched_at DESC LIMIT 1
                """
            ).fetchone()
        return str(row["endpoint"]) if row else None

    def has_entries(self) -> bool:
        with self._connect() as conn:
            n = conn.execute(
                "SELECT (SELECT COUNT(*) FROM query_cache) + (SELECT COUNT(*) FROM sparql_cache)"
            ).fetchone()[0]
        return int(n or 0) > 0

    def stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            tool_total = conn.execute("SELECT COUNT(*) FROM query_cache").fetchone()[0]
            sparql_total = conn.execute("SELECT COUNT(*) FROM sparql_cache").fetchone()[0]
            tools = conn.execute(
                "SELECT tool, COUNT(*) AS n FROM query_cache GROUP BY tool ORDER BY n DESC"
            ).fetchall()
        return {
            "tool_entries": int(tool_total),
            "sparql_entries": int(sparql_total),
            "entries": int(tool_total) + int(sparql_total),
            "by_tool": {r["tool"]: int(r["n"]) for r in tools},
            "last_known_endpoint": self.last_known_endpoint(),
            "db_path": str(self.path),
        }
