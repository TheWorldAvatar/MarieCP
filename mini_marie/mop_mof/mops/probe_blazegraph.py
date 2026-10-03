"""Probe OntoMOPs Blazegraph endpoints and print/cache status."""

from __future__ import annotations

import argparse
import json

from mini_marie.mop_mof.mops.ontomop_operations import (
    endpoint_probe_cache_path,
    get_endpoint_status,
    probe_all_endpoints,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe OntoMOPs Blazegraph (ontomops_ogm)")
    parser.add_argument("--force", action="store_true", help="Ignore endpoint cache TTL")
    parser.add_argument("--json-out", type=str, default="", help="Optional JSON output path")
    args = parser.parse_args()

    report = get_endpoint_status(force_probe=args.force) if not args.force else probe_all_endpoints()
    print("OntoMOPs Blazegraph probe")
    print(f"  cache: {endpoint_probe_cache_path()}")
    print(f"  preferred: {report.get('preferred_endpoint') or '(none)'}")
    print(f"  working: {len(report.get('working') or [])}")
    for row in report.get("results") or []:
        mark = "OK" if row.get("ok") else "FAIL"
        extra = ""
        if row.get("mop_count") is not None:
            extra = f"  mop_count={row['mop_count']}"
        err = row.get("error") or row.get("mop_count_error")
        if err and not row.get("ok"):
            extra = f"  ({str(err)[:100]})"
        print(f"  [{mark}] {row.get('url')}{extra}")

    if args.json_out:
        path = endpoint_probe_cache_path() if not args.json_out else args.json_out
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"\nWrote {path}")

    return 0 if report.get("preferred_endpoint") else 1


if __name__ == "__main__":
    raise SystemExit(main())
