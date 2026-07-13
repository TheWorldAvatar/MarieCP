"""
Pre-cache full-tier atomic SPARQL results for TWA city workflows.

Use --comprehensive to warm every city plan tool (all cities), then batch all WKT locations.

Chunked / resumable:
  --atomics-only       height/usage pools only (fast per city)
  --locations-only     WKT batches only (slow; skips batches already in full tier)
  --missing-only       skip atomics that already have full-tier cache
  --status             print progress and exit (see city_cache_status.py)

Progress:
  python -m mini_marie.zaha.twa_city.city_cache_status --city bremen
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from mini_marie.zaha.twa_city.atomic_warm_manifest import (
    CITIES,
    GERMAN_PAGE_LOCATIONS_TOP_N,
    cities_for_comprehensive_warm,
    specs_for_city,
    workflow_driven_warm_specs,
)
from mini_marie.zaha.twa_city.city_cache import (
    CityCache,
    warm_atomic,
    warm_locations_for_city,
    warm_locations_top_n,
)
from mini_marie.warm_manifest import is_resolved_warm_spec, specs_missing_full_tier

UBEM_ATOMIC_TOOLS = frozenset({"list_dabgeo_heat_supply", "list_dabgeo_co2_savings"})


def warm_city(
    city: str,
    specs: List[Dict[str, Any]],
    *,
    include_atomics: bool = True,
    include_locations: bool = True,
    locations_top_n: int | None = None,
    locations_usage_type: str | None = None,
    force: bool = False,
    missing_only: bool = False,
    batch_size: int = 100,
    skip_cached_batches: bool = True,
) -> Dict[str, Any]:
    ck = CityCache()
    try:
        city_specs = [s for s in specs if (s.get("args") or {}).get("city", "").lower() == city.lower()]
        city_specs = [s for s in city_specs if is_resolved_warm_spec(s)]
        if missing_only and not force:
            before = len(city_specs)
            city_specs = specs_missing_full_tier(city_specs, has_full=ck.has_full)
            print(
                f"  atomics to warm: {len(city_specs)}/{before} (missing full tier)",
                flush=True,
            )

        warmed: List[Dict[str, Any]] = []
        if include_atomics:
            for i, spec in enumerate(city_specs, 1):
                print(
                    f"  atomic [{i}/{len(city_specs)}] {spec['tool']} {spec['args']} ...",
                    flush=True,
                )
                rows, meta = warm_atomic(
                    spec["tool"],
                    spec["args"],
                    force=force,
                    cache=ck,
                )
                print(f"    -> {len(rows)} rows in {meta.get('elapsed_ms', '?')}ms", flush=True)
                warmed.append(
                    {
                        "tool": spec["tool"],
                        "args": spec["args"],
                        "row_count": len(rows),
                        **meta,
                    }
                )
        elif city_specs:
            print(f"  atomics skipped ({len(city_specs)} specs not run)", flush=True)

        loc_stats = None
        if include_locations:
            if locations_top_n is not None:
                loc_stats = warm_locations_top_n(
                    city,
                    locations_top_n,
                    usage_type=locations_usage_type,
                    batch_size=batch_size,
                    force=force,
                    skip_cached=skip_cached_batches,
                    cache=ck,
                )
            else:
                print(f"  locations full-city (batch_size={batch_size}) ...", flush=True)
                loc_stats = warm_locations_for_city(
                    city,
                    batch_size=batch_size,
                    force=force,
                    skip_cached=skip_cached_batches,
                    cache=ck,
                )
    finally:
        ck.close()

    return {"city": city, "atomics": warmed, "locations": loc_stats}


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-cache full-tier TWA city atomics")
    parser.add_argument("--city", action="append", help="City slug (repeatable)")
    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Warm all plan tools for all configured cities + full location facets",
    )
    parser.add_argument("--all", action="store_true", help="Alias for --comprehensive")
    parser.add_argument(
        "--atomics-only",
        action="store_true",
        help="Warm list/rank/usage atomics only (no WKT location batches)",
    )
    parser.add_argument(
        "--locations-only",
        action="store_true",
        help="Warm WKT location batches only (requires height facet; resumes cached batches)",
    )
    parser.add_argument(
        "--locations-top-n",
        type=int,
        metavar="N",
        help="Warm WKT only for tallest N buildings (recommended for workflows; minutes not hours)",
    )
    parser.add_argument(
        "--locations-usage-type",
        help="With --locations-top-n: filter pool by usage (e.g. Non-Domestic)",
    )
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Skip atomics already in full-tier cache (locations always skip cached batches)",
    )
    parser.add_argument(
        "--no-locations",
        action="store_true",
        help="Skip WKT location batches (same as --atomics-only)",
    )
    parser.add_argument("--force", action="store_true", help="Re-fetch even if full cache exists")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Buildings per fetch_building_locations batch (default 100)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print cache progress and exit",
    )
    parser.add_argument(
        "--page-questions",
        action="store_true",
        help="Warm atomics + top-N WKT for Zaha German-city dropdown (Bremen/KL/Pirmasens)",
    )
    parser.add_argument(
        "--include-ubem",
        action="store_true",
        help="With --page-questions: also warm Pirmasens UBEM row pools (slow; 100k+ rows)",
    )
    args = parser.parse_args()

    if args.status:
        from mini_marie.zaha.twa_city.city_cache_status import print_status

        print_status(city_filter=(args.city or [None])[0] if args.city else None)
        return

    comprehensive = args.comprehensive or args.all
    page_questions = args.page_questions
    if page_questions:
        cities = list(CITIES)
        specs = workflow_driven_warm_specs()
        args.missing_only = True
    elif comprehensive:
        cities = cities_for_comprehensive_warm()
        specs = workflow_driven_warm_specs()
    else:
        cities = args.city or []
        specs = workflow_driven_warm_specs() if cities else []

    if not cities:
        raise SystemExit("Provide --city <slug>, --comprehensive, --page-questions, or --status")

    include_atomics = not args.locations_only
    include_locations = not (args.no_locations or args.atomics_only)
    if args.atomics_only:
        include_locations = False
    if args.locations_only:
        include_atomics = False
    locations_top_n = args.locations_top_n
    if locations_top_n is not None and locations_top_n < 1:
        raise SystemExit("--locations-top-n must be >= 1")
    if locations_top_n is not None:
        include_locations = True
        if not comprehensive and not args.locations_only and not page_questions:
            include_atomics = False  # height facet already warmed; avoid full-city location grind
    if page_questions and not args.atomics_only and not args.locations_only:
        include_atomics = True
        include_locations = True

    results = []
    for ci, city in enumerate(cities, 1):
        city_locations_top_n = locations_top_n
        if page_questions and city_locations_top_n is None:
            city_locations_top_n = GERMAN_PAGE_LOCATIONS_TOP_N.get(city.lower())
        loc_mode = (
            f"top_n={city_locations_top_n}"
            if city_locations_top_n is not None
            else ("full" if include_locations else "off")
        )
        mode_label = (
            "page-questions"
            if page_questions
            else ("comprehensive" if comprehensive else "city")
        )
        print(
            f"[{ci}/{len(cities)}] Warming {city} "
            f"({mode_label}) "
            f"atomics={include_atomics} locations={loc_mode} ...",
            flush=True,
        )
        if page_questions or comprehensive:
            city_specs = [s for s in specs if (s.get("args") or {}).get("city", "").lower() == city.lower()]
            if not city_specs:
                city_specs = specs_for_city(city)
            if page_questions and not args.include_ubem:
                city_specs = [s for s in city_specs if s.get("tool") not in UBEM_ATOMIC_TOOLS]
        else:
            city_specs = [s for s in specs if (s.get("args") or {}).get("city", "").lower() == city.lower()]
        if not city_specs:
            city_specs = specs_for_city(city)
        out = warm_city(
            city,
            city_specs,
            include_atomics=include_atomics,
            include_locations=include_locations,
            locations_top_n=city_locations_top_n,
            locations_usage_type=args.locations_usage_type,
            force=args.force,
            missing_only=args.missing_only,
            batch_size=max(1, int(args.batch_size)),
        )
        results.append(out)
        print(json.dumps(out, indent=2)[:4000], flush=True)

    print(json.dumps({"comprehensive": comprehensive, "cities": results}, indent=2), flush=True)


if __name__ == "__main__":
    main()
