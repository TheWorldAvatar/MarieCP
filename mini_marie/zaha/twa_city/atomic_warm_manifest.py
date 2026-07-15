"""
Comprehensive full-tier warm specs for every TWA city SPARQL atomic plan.

Each city gets a full building-height pool and full location facet (batched WKT warm).
"""

from __future__ import annotations

from typing import Any, Dict, List

from mini_marie.zaha.twa_city.sparql_plans import PLAN_BUILDERS
from mini_marie.warm_manifest import merge_warm_specs, is_resolved_warm_spec

CITIES: List[str] = ["bremen", "kaiserslautern", "pirmasens"]

# Usage types observed in city workflows / probes
USAGE_TYPES: List[str] = ["Non-Domestic", "Domestic"]

# Zaha German-city dropdown: tallest-N location warm targets (see demos/german_city_competency_questions.json)
GERMAN_PAGE_LOCATIONS_TOP_N: Dict[str, int] = {
    "bremen": 14,
    "kaiserslautern": 10,
    "pirmasens": 12,
}


def comprehensive_warm_specs(*, include_usage: bool = True) -> List[Dict[str, Any]]:
    """One uncapped warm per (plan tool, city[, usage]) — not workflow-selective."""
    specs: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def add(tool: str, args: Dict[str, Any]) -> None:
        if tool not in PLAN_BUILDERS:
            return
        key = f"{tool}:{sorted(args.items())}"
        if key in seen:
            return
        seen.add(key)
        specs.append({"tool": tool, "args": args})

    for city in CITIES:
        add("list_buildings_with_height", {"city": city})
        add("rank_buildings_by_height", {"city": city})
        if include_usage:
            for usage in USAGE_TYPES:
                add("buildings_by_usage", {"city": city, "usage_type": usage})
        if city == "pirmasens":
            add("list_dabgeo_heat_supply", {"city": city})
            add("list_dabgeo_co2_savings", {"city": city})

    return specs


def specs_for_city(city: str, *, include_usage: bool = True) -> List[Dict[str, Any]]:
    """All warm specs (comprehensive + workflow-driven) for one city slug."""
    city_lc = city.strip().lower()
    all_specs = workflow_driven_warm_specs(include_usage=include_usage)
    return [
        s
        for s in all_specs
        if (s.get("args") or {}).get("city", "").lower() == city_lc and is_resolved_warm_spec(s)
    ]


def german_page_warm_targets() -> Dict[str, Dict[str, Any]]:
    """Per-city warm profile aligned with Zaha German-city competency dropdown."""
    return {
        city: {
            "atomics": specs_for_city(city),
            "locations_top_n": GERMAN_PAGE_LOCATIONS_TOP_N.get(city),
        }
        for city in CITIES
    }


def cities_for_comprehensive_warm() -> List[str]:
    return list(CITIES)


def workflow_driven_warm_specs(*, include_usage: bool = True) -> List[Dict[str, Any]]:
    """Comprehensive city plans plus atomics from every workflows/*.json file."""
    from pathlib import Path

    from mini_marie.zaha.twa_city.workflow_engine import WORKFLOWS_DIR, resolve_value
    from mini_marie.warm_manifest import collect_atomic_specs_from_workflow_dir

    workflow_specs = collect_atomic_specs_from_workflow_dir(
        WORKFLOWS_DIR, resolve=resolve_value
    )
    return merge_warm_specs(
        comprehensive_warm_specs(include_usage=include_usage),
        workflow_specs,
    )
