"""
Pre-cache Pirmasens Ontop SPARQL for Zaha page questions (toilet / plots / solarthermie).

  python -m mini_marie.zaha.twa_city.warm_pirmasens_ontop_cache --page-questions
  python -m mini_marie.zaha.twa_city.warm_pirmasens_ontop_cache --status
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from mini_marie.warm_manifest import specs_missing_full_tier
from mini_marie.zaha.twa_city.pirmasens_md_sparql import (
    PIRMASENS_CITY_PAGE_QUERY_FILES,
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
    specs: List[Dict[str, Any]] = []
    for name in PIRMASENS_CITY_PAGE_QUERY_FILES:
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
        seen = {json.dumps(s["args"], sort_keys=True) for s in specs}
        for spec in city_page_warm_specs():
            key = json.dumps(spec["args"], sort_keys=True)
            if key not in seen:
                specs.append(spec)
                seen.add(key)
    return specs


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
    finally:
        ck.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Warm Pirmasens Ontop SQLite cache")
    parser.add_argument(
        "--page-questions",
        action="store_true",
        help="Warm all Zaha page ontop + city named queries",
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
    elif args.page_questions:
        specs = page_warm_specs()
    else:
        raise SystemExit("Use --page-questions, --city-named-only, or --status")

    print(f"Warming {len(specs)} Pirmasens Ontop specs ...", flush=True)
    results = warm_specs(specs, missing_only=args.missing_only, force=args.force)
    print(json.dumps({"warmed": len(results), "results": results}, indent=2), flush=True)


if __name__ == "__main__":
    main()
