"""Tests for German city question specs and map routing metadata."""

from __future__ import annotations

from demos.german_city_specs import (
    is_location_workflow_spec,
    iter_german_city_questions,
    lookup_german_city_question,
)


def test_lookup_location_questions_have_workflow_params():
    spec = lookup_german_city_question(
        "Find the locations of the 10 highest buildings in Bremen"
    )
    assert spec is not None
    assert spec["id"] == "DE-BR-03"
    assert spec["workflow"] == "city_ranked_buildings"
    assert spec["parameters"]["include_locations"] is True
    assert is_location_workflow_spec(spec)


def test_pirmasens_map_question_matches_pq10_routing():
    spec = lookup_german_city_question("Show a map of the tallest Pirmasens building footprints.")
    assert spec is not None
    assert spec["id"] == "DE-PS-13"
    assert spec["parameters"]["city"] == "pirmasens"
    assert spec["parameters"]["top_n"] == 12
    assert spec["parameters"]["include_locations"] is True


def test_map_questions_are_tagged():
    map_ids = {item["id"] for item in iter_german_city_questions() if item.get("map")}
    assert "DE-BR-01" in map_ids
    assert "DE-BR-03" in map_ids
    assert "DE-KL-02" in map_ids
    assert "DE-PS-04" in map_ids
    assert "DE-PS-13" in map_ids


def test_bremen_non_domestic_has_workflow_params():
    spec = lookup_german_city_question("List the tallest non-domestic buildings in Bremen.")
    assert spec is not None
    assert spec["id"] == "DE-BR-02"
    assert spec["workflow"] == "city_ranked_buildings"
    assert spec["parameters"]["city"] == "bremen"
    assert spec["parameters"]["usage_type"] == "Non-Domestic"
    assert spec["parameters"]["top_n"] == 50


def test_kaiserslautern_tallest_has_workflow_params():
    spec = lookup_german_city_question("What are the tallest buildings in Kaiserslautern?")
    assert spec is not None
    assert spec["id"] == "DE-KL-01"
    assert spec["workflow"] == "city_ranked_buildings"
    assert spec["parameters"]["city"] == "kaiserslautern"
    assert spec["parameters"]["top_n"] == 10
    assert spec["parameters"]["sort_field"] == "height"
