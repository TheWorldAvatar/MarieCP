"""Warm TWA city caches aligned with Zaha German-city competency dropdown.

  python -m demos.warm_german_city_caches
  python -m demos.warm_german_city_caches --status
  python -m demos.warm_german_city_caches --ubem
  python -m demos.warm_german_city_caches --ontop
  python -m demos.warm_german_city_caches --all-page
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(REPO))


def main() -> None:
    parser = argparse.ArgumentParser(description="Warm German city caches for Zaha page questions")
    parser.add_argument("--status", action="store_true", help="Print cache status only")
    parser.add_argument("--ubem", action="store_true", help="Also warm Pirmasens UBEM row pools (slow)")
    parser.add_argument("--ontop", action="store_true", help="Warm Pirmasens Ontop cache (toilet/plots/solar)")
    parser.add_argument("--all-page", action="store_true", help="Warm city_cache + pirmasens_ontop for page")
    parser.add_argument("--atomics-only", action="store_true", help="Skip WKT location batches")
    args = parser.parse_args()

    py = sys.executable
    city_mod = "mini_marie.zaha.twa_city.warm_city_cache"
    ontop_mod = "mini_marie.zaha.twa_city.warm_pirmasens_ontop_cache"

    if args.status:
        code = _run([py, "-m", city_mod, "--status"])
        _run([py, "-m", ontop_mod, "--status"])
        raise SystemExit(code)

    if args.all_page:
        args.ontop = True

    if args.ontop and not args.all_page:
        code = _run([py, "-m", ontop_mod, "--page-questions", "--missing-only"])
        raise SystemExit(code)

    cmd = [py, "-m", city_mod, "--page-questions"]
    if args.atomics_only:
        cmd.append("--atomics-only")
    if args.ubem:
        cmd.append("--include-ubem")
    code = _run(cmd)
    if code:
        raise SystemExit(code)

    if args.all_page:
        code = _run([py, "-m", ontop_mod, "--page-questions", "--missing-only"])
        if code:
            raise SystemExit(code)

    if args.ubem:
        raise SystemExit(0)

    print("\nOptional warm steps:")
    print(f"  {py} -m {city_mod} --city pirmasens --atomics-only --missing-only --include-ubem")
    print(f"  {py} -m {ontop_mod} --page-questions --missing-only")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
