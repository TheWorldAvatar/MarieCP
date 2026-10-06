"""Compare MOF twelve API results: local vs remote (row counts + sample cells)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from demos.test_kg_row_narrative import CANONICAL_DEMO_TWELVE  # noqa: E402

_HEADERS = {
    "User-Agent": "MarieCP-compare/1.0 (TheWorldAvatar demo QA)",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def _post(base: str, question: str, timeout: int) -> dict:
    url = f"{base.rstrip('/')}/demos/marie/api/qa"
    body = json.dumps({"question": question, "qa_domain": "marie"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers=_HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _signature(payload: dict) -> dict:
    meta = payload.get("metadata") or {}
    data = payload.get("data") or []
    tables = [t for t in data if t.get("type") == "table"]
    rows = sum(len(t.get("data") or []) for t in tables)
    cols = tables[0].get("columns") or tables[0].get("display_columns") if tables else []
    sample = (tables[0].get("data") or [{}])[0] if tables else {}
    sample = {k: sample.get(k) for k in (cols or list(sample.keys()))[:6]}
    return {
        "agent_driven": meta.get("agent_driven"),
        "table_rows": rows,
        "sample": sample,
        "narrative_len": len((payload.get("narrative") or "")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", default="http://127.0.0.1:8080")
    parser.add_argument("--remote", default="https://theworldavatar.io")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    mismatches = 0
    for i, q in enumerate(CANONICAL_DEMO_TWELVE, 1):
        print(f"[{i}/12] {q[:60]}…")
        try:
            loc = _signature(_post(args.local, q, args.timeout))
            rem = _signature(_post(args.remote, q, args.timeout))
        except urllib.error.HTTPError as exc:
            print(f"  HTTP {exc.code}: {exc.read()[:200]}")
            mismatches += 1
            continue
        except Exception as exc:
            print(f"  ERROR: {exc}")
            mismatches += 1
            continue
        ok = loc["table_rows"] == rem["table_rows"]
        if not ok:
            mismatches += 1
        mark = "OK" if ok else "MISMATCH"
        print(
            f"  {mark} rows local={loc['table_rows']} remote={rem['table_rows']} "
            f"agent local={loc['agent_driven']} remote={rem['agent_driven']}"
        )
        if not ok:
            print(f"    local sample:  {loc['sample']}")
            print(f"    remote sample: {rem['sample']}")

    print(f"\nDone: {12 - mismatches}/12 matched row counts")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
