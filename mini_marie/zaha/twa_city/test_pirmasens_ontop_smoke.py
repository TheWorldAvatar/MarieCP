"""Unit smoke test for Pirmasens Ontop generic MCP operations."""

from __future__ import annotations

from mini_marie.zaha.twa_city.pirmasens_ontop_operations import (
    list_entities_by_type,
    list_pirmasens_endpoints,
    normalize_endpoint_id,
    run_sparql_on_endpoint,
)


def test_normalize_endpoint_aliases() -> None:
    assert normalize_endpoint_id("ontop-toilet") == "toilet"
    assert normalize_endpoint_id("plots") == "plots"
    assert normalize_endpoint_id("solar") == "solarthermie"


def test_list_endpoints() -> None:
    rows = list_pirmasens_endpoints()
    assert len(rows) == 4
    assert {r["endpoint_id"] for r in rows} == {"city", "plots", "solarthermie", "toilet"}


def test_list_entities_toilet() -> None:
    rows = list_entities_by_type(
        "toilet",
        "https://www.theworldavatar.com/kg/ontobuiltenv/Toilet",
        var_name="toilet",
        limit=5,
    )
    assert rows
    assert "toilet" in rows[0]


def test_run_sparql_plots() -> None:
    rows = run_sparql_on_endpoint(
        "plots",
        """PREFIX plt: <https://www.theworldavatar.com/kg/ontoplot/>
SELECT ?plot WHERE { ?plot a plt:Plot . }""",
        limit=5,
    )
    assert rows
    assert "plot" in rows[0]
