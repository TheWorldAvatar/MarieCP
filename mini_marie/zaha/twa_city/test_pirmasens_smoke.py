"""Smoke-test Pirmasens MCP query functions."""

from __future__ import annotations

from mini_marie.zaha.twa_city.pirmasens_operations import (
    get_co2_savings_stats,
    get_device_type_counts,
    get_heat_supply_stats,
    get_pirmasens_property_coverage,
    get_pirmasens_schema_summary,
    get_top_buildings_by_co2_savings,
    get_top_buildings_by_heat_supply,
    get_ubem_class_counts,
)
from mini_marie.zaha.twa_city.twa_city_operations import (
    get_building_count,
    get_height_stats,
    get_top_buildings_by_height,
    get_usage_type_counts,
)

CITY = "pirmasens"


def _check(name: str, rows: list) -> None:
    assert rows, f"{name} returned no rows"
    print(f"OK {name}: {len(rows)} rows, sample={rows[0]}")


def main() -> None:
    _check("building_count", get_building_count(CITY))
    _check("height_stats", get_height_stats(CITY))
    _check("usage_types", get_usage_type_counts(CITY))
    _check("property_coverage", get_pirmasens_property_coverage(CITY))
    _check("ubem_classes", get_ubem_class_counts(CITY))
    _check("heat_stats", get_heat_supply_stats(CITY))
    _check("co2_stats", get_co2_savings_stats(CITY))
    _check("device_types", get_device_type_counts(CITY))
    _check("top_height", get_top_buildings_by_height(CITY))
    _check("top_heat", get_top_buildings_by_heat_supply(CITY))
    _check("top_co2", get_top_buildings_by_co2_savings(CITY))
    summary = get_pirmasens_schema_summary(CITY)
    live_count = get_building_count(CITY)[0]["building_count"]
    assert live_count in summary
    assert "~73k" not in summary and "avg ~386" not in summary and "~133k" not in summary
    print("OK schema_summary: live counts present, no hardcoded probe literals")
    print("All Pirmasens smoke tests passed.")


if __name__ == "__main__":
    main()
