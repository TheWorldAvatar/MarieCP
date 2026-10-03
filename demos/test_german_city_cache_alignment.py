"""Verify German-city page questions have matching cache warm specs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_CATALOG = REPO / "demos" / "german_city_competency_questions.json"

# Page catalog keys that use live Ontop SPARQL (no SQLite warm cache).
_LIVE_ONTOP_CATALOG_KEYS = frozenset(
    {"pirmasens_toilets", "pirmasens_plots", "pirmasens_solarthermie"}
)


def main() -> None:
    from mini_marie.zaha.twa_city.atomic_warm_manifest import (
        CITIES,
        GERMAN_PAGE_LOCATIONS_TOP_N,
        german_page_warm_targets,
        specs_for_city,
    )
    from mini_marie.zaha.twa_city.warm_pirmasens_ontop_cache import page_warm_specs

    catalog = json.loads(_CATALOG.read_text(encoding="utf-8"))
    catalog_cities = set(catalog.keys())
    cached_catalog = catalog_cities - _LIVE_ONTOP_CATALOG_KEYS
    assert cached_catalog <= set(CITIES), f"cached catalog cities {cached_catalog} not in CITIES"

    targets = german_page_warm_targets()
    assert set(targets) == set(CITIES)

    for city in CITIES:
        specs = specs_for_city(city)
        assert specs, f"no warm specs for {city}"
        top_n = GERMAN_PAGE_LOCATIONS_TOP_N.get(city)
        assert top_n, f"no locations top-N for {city}"
        print(f"OK {city}: {len(specs)} atomic specs, locations_top_n={top_n}")

    ontop_specs = page_warm_specs()
    ontop_page_ids = {
        item["id"]
        for key in _LIVE_ONTOP_CATALOG_KEYS
        for item in catalog.get(key, {}).get("questions") or []
    }
    assert len(ontop_specs) >= len(ontop_page_ids), (
        f"ontop warm specs {len(ontop_specs)} < page questions {len(ontop_page_ids)}"
    )
    print(f"OK pirmasens_ontop: {len(ontop_specs)} warm specs for {len(ontop_page_ids)} page questions")

    print(f"\nAll {len(CITIES)} cached cities aligned with german_city_competency_questions.json")
    print(f"Live Ontop catalog keys (SQLite: pirmasens_ontop_cache.sqlite): {sorted(_LIVE_ONTOP_CATALOG_KEYS)}")


if __name__ == "__main__":
    main()
