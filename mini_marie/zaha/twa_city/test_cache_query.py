"""Tests for generic city cache query pipeline."""

from __future__ import annotations

from mini_marie.zaha.twa_city.cache_query import CityBuildingQueryPlan, execute_city_building_query
from mini_marie.zaha.twa_city.city_cache import dedupe_rows_by_building
from mini_marie.workflow_parameters import parse_parameters_json, resolve_workflow_parameters, workflow_with_parameters
from mini_marie.zaha.twa_city.workflow_engine import load_workflow, run_workflow


def test_dedupe_rows_by_building():
    rows = [
        {"building": "https://x/b1", "height": 100.0, "usage_type": "A"},
        {"building": "https://x/b1", "height": 100.0, "usage_type": "B"},
        {"building": "https://x/b2", "height": 90.0},
    ]
    out = dedupe_rows_by_building(rows)
    assert len(out) == 2
    assert {r["building"] for r in out} == {"https://x/b1", "https://x/b2"}


def test_bremen_14_tallest_with_locations():
    """Matches: 14 tallest buildings in Bremen, where are they, what type."""
    wf = load_workflow("city_ranked_buildings")
    params = resolve_workflow_parameters(
        wf,
        "",
        parse_parameters_json(
            '{"city":"bremen","top_n":14,"sort_field":"height","sort_order":"desc","include_locations":true}'
        ),
    )
    wf = workflow_with_parameters(wf, params)
    result = run_workflow(wf, mode="offline", workflow_name="city_ranked_buildings")
    if result["status"] == "empty":
        return
    rows = result.get("variables", {}).get("top_building_rows") or []
    assert len(rows) == 14
    assert len(rows) == len({r.get("building") for r in rows})
    assert all(r.get("city") == "bremen" for r in rows)
    wkt_rows = result.get("variables", {}).get("buildings_with_wkt") or []
    if wkt_rows:
        assert len(wkt_rows) == len({r.get("building") for r in wkt_rows})


def test_city_ranked_buildings_offline_limit_14():
    wf = load_workflow("city_ranked_buildings")
    params = resolve_workflow_parameters(
        wf, "", parse_parameters_json('{"city":"kaiserslautern","top_n":14,"include_locations":true}')
    )
    wf = workflow_with_parameters(wf, params)
    result = run_workflow(wf, mode="offline", workflow_name="city_ranked_buildings")
    if result["status"] == "empty":
        return
    rows = result.get("variables", {}).get("top_building_rows") or []
    assert len(rows) <= 14
    assert len(rows) == len({r.get("building") for r in rows})


def test_city_ranked_buildings_offline_limit_200():
    wf = load_workflow("city_ranked_buildings")
    params = resolve_workflow_parameters(
        wf, "", parse_parameters_json('{"city":"kaiserslautern","top_n":200,"sort_field":"height"}')
    )
    wf = workflow_with_parameters(wf, params)
    result = run_workflow(wf, mode="offline", workflow_name="city_ranked_buildings")
    if result["status"] == "empty":
        return
    rows = result.get("variables", {}).get("top_building_rows") or []
    assert len(rows) == 200
    assert len(rows) == len({r.get("building") for r in rows})


def test_row_annotations_custom_columns():
    wf = load_workflow("city_ranked_buildings")
    params = resolve_workflow_parameters(
        wf,
        "",
        parse_parameters_json(
            '{"city":"kaiserslautern","top_n":3,"row_annotations":{"region":"southwest"}}'
        ),
    )
    wf = workflow_with_parameters(wf, params)
    result = run_workflow(wf, mode="offline", workflow_name="city_ranked_buildings")
    if result["status"] == "empty":
        return
    rows = result.get("variables", {}).get("top_building_rows") or []
    assert rows
    assert all(r.get("city") == "kaiserslautern" for r in rows)
    assert all(r.get("region") == "southwest" for r in rows)


def test_execute_kl_top10_fast():
    plan = CityBuildingQueryPlan(city="kaiserslautern", limit=10)
    result = execute_city_building_query(plan)
    if result["status"] == "empty":
        return
    assert len(result["rows"]) <= 10
    assert len(result["rows"]) == len({r.get("building") for r in result["rows"]})


if __name__ == "__main__":
    test_dedupe_rows_by_building()
    test_bremen_14_tallest_with_locations()
    test_city_ranked_buildings_offline_limit_14()
    test_city_ranked_buildings_offline_limit_200()
    test_row_annotations_custom_columns()
    test_execute_kl_top10_fast()
    print("cache_query tests OK")
