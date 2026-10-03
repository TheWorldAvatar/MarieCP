"""
Recover a corrupted sg-old Ontop SQLite cache (database disk image is malformed).

Usage:
  python -m mini_marie.zaha.sg_old.recover_ontop_cache
  python -m mini_marie.zaha.sg_old.recover_ontop_cache --full
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import time

import mini_marie.zaha.sg_old.ontop_store as ontop_store
from mini_marie.zaha.sg_old.ontop_store import db_path, ensure_schema, set_meta
from mini_marie.zaha.sg_old.warm_ontop_cache import (
    enrich_land_plots,
    warm_buildings,
    warm_land_plots,
    warm_names,
)


def _integrity_ok(path) -> bool:
    if not path.is_file():
        return True
    try:
        conn = sqlite3.connect(path)
        row = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        return row and row[0] == "ok"
    except sqlite3.DatabaseError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover corrupted sg-old Ontop SQLite cache")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full warm (slow). Default: minimal warm for server status + smoke use.",
    )
    parser.add_argument("--page-size", type=int, default=3000)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    path = db_path()
    rebuild_path = path.with_name(f"{path.name}.new")
    if rebuild_path.is_file():
        rebuild_path.unlink()

    if path.is_file() and not _integrity_ok(path):
        backup = path.with_name(f"{path.name}.corrupt.{int(time.time())}")
        try:
            shutil.move(path, backup)
            print(f"Moved corrupt database to {backup}")
        except OSError as exc:
            print(f"Could not move corrupt DB ({exc}); building {rebuild_path.name} instead.")
            ontop_store.db_path = lambda: rebuild_path  # type: ignore[method-assign]
            path = rebuild_path

    ensure_schema()
    print(f"Rebuilding {db_path()} from Ontop endpoint (full={args.full})…")

    max_pages = None if args.full else 2
    bstats = warm_buildings(
        page_size=args.page_size,
        timeout=args.timeout,
        with_footprints=False,
        max_pages=max_pages,
    )
    lpstats = warm_land_plots(page_size=args.page_size, timeout=args.timeout)
    if args.full:
        estats = enrich_land_plots(page_size=args.page_size, timeout=args.timeout)
        nstats = warm_names(page_size=args.page_size, timeout=args.timeout)
        print("Enrichment:", estats, nstats)
    set_meta("warm_complete", "1")
    set_meta("building_rows", str(bstats.get("rows", 0)))
    set_meta("land_plot_rows", str(lpstats.get("land_plot_rows", 0)))
    print("Done:", bstats, lpstats)

    final = ontop_store.db_path()
    default = ontop_store.cache_dir() / "ontop_cache.sqlite"
    if final != default and final.is_file():
        try:
            if default.is_file():
                bad = default.with_name(f"{default.name}.corrupt.{int(time.time())}")
                shutil.move(default, bad)
            shutil.move(final, default)
            print(f"Installed fresh cache at {default}")
        except OSError as exc:
            print(
                f"Stop the demo server, then run:\n"
                f"  move \"{default}\" \"{default}.old\"\n"
                f"  move \"{final}\" \"{default}\""
            )
            print(f"(install failed: {exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
