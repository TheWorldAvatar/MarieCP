"""Probe all competency questions from pirmasens.md against live Ontop endpoints.

  python -m demos.test_pirmasens_md_cqs
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from mini_marie.zaha.twa_city.pirmasens_md_sparql import CASES, ENDPOINTS
from mini_marie.zaha.twa_city.twa_city_operations import execute_sparql


@dataclass
class ProbeResult:
    qid: str
    domain: str
    question: str
    ok: bool
    detail: str
    rows: int
    elapsed_ms: int


def run_probe(case: Dict[str, Any]) -> ProbeResult:
    domain = case["domain"]
    endpoint = ENDPOINTS[domain]
    t0 = time.perf_counter()
    try:
        query = case["query"].strip()
        if "LIMIT" not in query.upper():
            query = f"{query}\nLIMIT 20"
        rows = execute_sparql(query, endpoint, timeout=60)
        elapsed = int((time.perf_counter() - t0) * 1000)
        n = len(rows)
        min_rows = int(case.get("min_rows", 1))
        if n >= min_rows:
            sample = json.dumps(rows[0], ensure_ascii=False)[:100] if rows else "[]"
            return ProbeResult(
                case["id"], domain, case["question"], True, f"{n} rows; sample={sample}", n, elapsed
            )
        return ProbeResult(
            case["id"],
            domain,
            case["question"],
            False,
            f"expected >= {min_rows} rows, got {n}",
            n,
            elapsed,
        )
    except Exception as exc:
        elapsed = int((time.perf_counter() - t0) * 1000)
        return ProbeResult(
            case["id"], domain, case["question"], False, str(exc)[:200], 0, elapsed
        )


def main() -> int:
    results = [run_probe(c) for c in CASES]
    passed = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]

    print(f"\n=== Pirmasens.md CQ probe: {len(passed)}/{len(results)} passed ===\n")
    for r in results:
        mark = "PASS" if r.ok else "FAIL"
        print(f"[{mark}] {r.qid} ({r.domain}) {r.elapsed_ms}ms rows={r.rows}")
        print(f"  Q: {r.question}")
        print(f"  {r.detail}\n")

    if failed:
        print("FAILED:", ", ".join(r.qid for r in failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
