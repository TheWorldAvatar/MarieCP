"""
Pre-cache Pirmasens Ontop SPARQL for Zaha page questions (toilet / plots / solarthermie).

  python -m mini_marie.zaha.twa_city.warm_pirmasens_ontop_cache --page-questions
  python -m mini_marie.zaha.twa_city.warm_pirmasens_ontop_cache --full-fast --missing-only
  python -m mini_marie.zaha.twa_city.warm_pirmasens_ontop_cache --status
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any, Dict, List

from mini_marie.warm_manifest import specs_missing_full_tier
from mini_marie.zaha.twa_city.limits import warm_delay_seconds
from mini_marie.zaha.twa_city.pirmasens_md_sparql import (
    PIRMASENS_ALL_CITY_QUERY_FILES,
    PIRMASENS_CITY_PAGE_QUERY_FILES,
    md_all_warm_specs,
    page_ontop_warm_specs,
)
from mini_marie.zaha.twa_city.pirmasens_ontop_cache import (
    PirmasensOntopCache,
    RUN_SPARQL_TOOL,
    get_cache_status_text,
    warm_run_sparql,
)
from mini_marie.zaha.twa_city.pirmasens_operations import load_pirmasens_query


def city_page_warm_specs() -> List[Dict[str, Any]]:
    """Named .sparql files on the main city endpoint used by the Zaha page."""
    return _city_named_warm_specs(PIRMASENS_CITY_PAGE_QUERY_FILES)


def all_city_named_warm_specs() -> List[Dict[str, Any]]:
    """All named .sparql files under queries/pirmasens/."""
    return _city_named_warm_specs(PIRMASENS_ALL_CITY_QUERY_FILES)


def _city_named_warm_specs(files: List[str]) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    for name in files:
        specs.append(
            {
                "tool": RUN_SPARQL_TOOL,
                "args": {
                    "endpoint_id": "city",
                    "query": load_pirmasens_query(name).strip(),
                },
                "label": name,
            }
        )
    return specs


def page_warm_specs(*, include_city_named: bool = True) -> List[Dict[str, Any]]:
    specs = page_ontop_warm_specs()
    if include_city_named:
        return _merge_specs(specs, city_page_warm_specs())
    return specs


def full_fast_warm_specs() -> List[Dict[str, Any]]:
    """All 24 md CQs + all 8 city named .sparql files (deduped by args)."""
    return _merge_specs(md_all_warm_specs(), all_city_named_warm_specs())


def _merge_specs(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for specs in groups:
        for spec in specs:
            key = json.dumps(spec["args"], sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            merged.append(spec)
    return merged


def warm_specs(
    specs: List[Dict[str, Any]],
    *,
    missing_only: bool = False,
    force: bool = False,
) -> List[Dict[str, Any]]:
    ck = PirmasensOntopCache()
    results: List[Dict[str, Any]] = []
    try:
        todo = specs
        if missing_only and not force:
            todo = specs_missing_full_tier(specs, has_full=ck.has_full)
            print(f"  to warm: {len(todo)}/{len(specs)} (missing full tier)", flush=True)
        for i, spec in enumerate(todo, 1):
            args = spec.get("args") or {}
            label = spec.get("label") or args.get("endpoint_id")
            print(
                f"  [{i}/{len(todo)}] {label} endpoint={args.get('endpoint_id')} ...",
                flush=True,
            )
            rows, meta = warm_run_sparql(
                str(args["endpoint_id"]),
                str(args["query"]),
                force=force,
                cache=ck,
            )
            results.append(
                {
                    "label": label,
                    "endpoint_id": args.get("endpoint_id"),
                    "row_count": len(rows),
                    **meta,
                }
            )
            print(f"    -> {len(rows)} rows in {meta.get('elapsed_ms', '?')}ms", flush=True)
            if i < len(todo):
                delay = warm_delay_seconds()
                if delay > 0 and not meta.get("from_cache"):
                    time.sleep(delay)
    finally:
        ck.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Warm Pirmasens Ontop SQLite cache")
    parser.add_argument(
        "--page-questions",
        action="store_true",
        help="Warm Zaha page ontop + 3 city named queries (23 specs)",
    )
    parser.add_argument(
        "--full-fast",
        action="store_true",
        help="Warm all 24 md CQs + 8 city named .sparql files (32 specs, deduped)",
    )
    parser.add_argument("--missing-only", action="store_true", help="Skip cached entries")
    parser.add_argument("--force", action="store_true", help="Re-fetch all")
    parser.add_argument("--status", action="store_true", help="Print cache status and exit")
    parser.add_argument(
        "--city-named-only",
        action="store_true",
        help="Warm only city endpoint named .sparql files",
    )
    args = parser.parse_args()

    if args.status:
        print(get_cache_status_text())
        return

    if args.city_named_only:
        specs = city_page_warm_specs()
    elif args.full_fast:
        specs = full_fast_warm_specs()
    elif args.page_questions:
        specs = page_warm_specs()
    else:
        raise SystemExit("Use --page-questions, --full-fast, --city-named-only, or --status")

    print(f"Warming {len(specs)} Pirmasens Ontop specs ...", flush=True)
    results = warm_specs(specs, missing_only=args.missing_only, force=args.force)
    print(json.dumps({"warmed": len(results), "results": results}, indent=2), flush=True)


if __name__ == "__main__":
    main()
