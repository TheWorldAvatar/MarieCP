"""Tests for KG answer enrichment helpers."""

from __future__ import annotations

from demos.kg_answer_enrich import (
    aggregate_pore_properties,
    burtch_water_stability_text,
    filter_synthesis_rows,
    format_pore_properties_clause,
)


def test_filter_synthesis_rows():
    rows = [
        {"name": "UiO-66", "sourcedb": "CSD MOF Collection", "yield": "90"},
        {"name": "Ce-UiO-66", "sourcedb": "Park_Syn", "yield": "38"},
    ]
    out = filter_synthesis_rows(rows)
    assert len(out) == 1
    assert out[0]["sourcedb"] == "Park_Syn"


def test_burtch_labels():
    assert "highly stable" in burtch_water_stability_text(4)
    assert "unstable" in burtch_water_stability_text(1)
    assert "moderate" in burtch_water_stability_text(2)


def test_aggregate_pore_properties_prefers_nonzero():
    rows = [
        {"sourcedb": "ARC_MOF 2025", "pld": "3.6", "lfpd": "5.0", "gsa": "0", "gpv": "0"},
        {"sourcedb": "CoRE MOF 2025", "pld": "3.7", "gsa": "1200", "gpv": "0.5"},
    ]
    props = aggregate_pore_properties(rows)
    assert props["pld"] == 3.7
    assert props["gsa"] == 1200.0


def test_format_pore_properties_clause():
    text = format_pore_properties_clause({"pld": 3.6, "lfpd": 5.0})
    assert "PLD" in text
    assert "LFPD" in text


if __name__ == "__main__":
    test_filter_synthesis_rows()
    test_burtch_labels()
    test_aggregate_pore_properties_prefers_nonzero()
    test_format_pore_properties_clause()
    print("kg_answer_enrich tests OK")
