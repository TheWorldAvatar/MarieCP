"""Tests for German city question specs and map routing metadata."""

from __future__ import annotations

from demos.german_city_specs import (
    is_location_workflow_spec,
    is_workflow_spec,
    iter_german_city_questions,
    lookup_german_city_question,
    resolve_city_workflow_parameters,
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


def test_pirmasens_ubem_heat_question_routes_to_ubem_workflow():
    spec = lookup_german_city_question(
        "Which five Pirmasens DABGEO buildings have the highest annual heat supply from thermal collectors?"
    )
    assert spec is not None
    assert spec["id"] == "DE-PS-07"
    assert spec["workflow"] == "pirmasens_ubem_ranked"
    assert spec["parameters"]["sort_field"] == "heat_kwh_per_m2"
    assert spec["parameters"]["top_n"] == 5
    assert is_workflow_spec(spec)
    params = resolve_city_workflow_parameters(spec["question"], spec["workflow"], spec=spec)
    assert params["sort_field"] == "heat_kwh_per_m2"
    assert params["top_n"] == 5


def test_pirmasens_height_workflow_questions_have_catalog_params():
    for qid, question, top_n, extra in (
        (
            "DE-PS-03",
            "What are the seven tallest buildings in Pirmasens?",
            7,
            {},
        ),
        (
            "DE-PS-05",
            "Which Pirmasens buildings are taller than 60 metres?",
            None,
            {"min_height_m": 60},
        ),
        (
            "DE-PS-12",
            "What are the 10 tallest buildings in Pirmasens?",
            10,
            {},
        ),
    ):
        spec = lookup_german_city_question(question)
        assert spec is not None, qid
        assert spec["id"] == qid
        assert spec["workflow"] == "city_ranked_buildings"
        assert spec["parameters"]["city"] == "pirmasens"
        assert spec["parameters"]["sort_field"] == "height"
        if top_n is not None:
            assert spec["parameters"]["top_n"] == top_n
        for key, value in extra.items():
            assert spec["parameters"][key] == value


def test_pirmasens_ubem_co2_question_routes_to_co2_workflow():
    spec = lookup_german_city_question(
        "Which six Pirmasens buildings have the highest modelled CO2 savings from solar collectors?"
    )
    assert spec is not None
    assert spec["id"] == "DE-PS-08"
    assert spec["workflow"] == "pirmasens_ubem_co2_ranked"
    assert spec["parameters"]["sort_field"] == "co2_savings"
    assert spec["parameters"]["top_n"] == 6

    spec = lookup_german_city_question("What are the tallest buildings in Kaiserslautern?")
    assert spec is not None
    assert spec["id"] == "DE-KL-01"
    assert spec["workflow"] == "city_ranked_buildings"
    assert spec["parameters"]["city"] == "kaiserslautern"
    assert spec["parameters"]["top_n"] == 10
    assert spec["parameters"]["sort_field"] == "height"
