"""Tests for table presentation enrichment."""

from demos.table_presentation import (
    enrich_data_items,
    enrich_table_item,
    human_column_description,
    human_column_label,
    normalize_synthesis_solvents,
    plan_display_columns,
)


def test_human_column_label():
    assert human_column_label("avgPLD") == "Average PLD (Å)"
    assert human_column_label("refcode") == "CSD refcode"
    assert human_column_label("mof") == "Internal entry ID"


def test_human_column_description():
    desc = human_column_description("thermal")
    assert "decomposition" in desc.lower()
    assert "structural database" in human_column_description("refcode").lower()


def test_normalize_synthesis_solvents():
    assert normalize_synthesis_solvents("0; acetic acid; water") == "acetic acid; water"
    assert normalize_synthesis_solvents("H2O; ethanol; water") == "water; ethanol"
    assert normalize_synthesis_solvents("distilled water; dry THF") == "water; dry THF"


def test_plan_display_columns_hides_redundant_at_a_glance():
    keys = ["display_label", "sourcedb", "display_detail", "method"]
    rows = [
        {"display_label": "a", "sourcedb": "Park_Syn", "display_detail": "Park_Syn", "method": "x"},
        {"display_label": "b", "sourcedb": "Park_Syn", "display_detail": "Park_Syn", "method": "y"},
    ]
    visible, hidden = plan_display_columns(keys, rows)
    assert "display_detail" in hidden
    assert "method" in visible


def test_plan_display_columns_hides_internal_mof():
    keys = ["mof", "source", "topology", "display_label"]
    visible, hidden = plan_display_columns(keys, [{}])
    assert visible[0] == "display_label"
    assert "mof" in hidden
    assert "topology" in visible


def test_enrich_table_item_adds_metadata():
    item = {
        "type": "table",
        "vars": ["refcode", "thermal", "sourcedb"],
        "bindings": [
            {"refcode": "IFAREN", "thermal": "654.32", "sourcedb": "MOFSimplify Thermal Dataset"},
            {"refcode": "EQERIC", "thermal": "639.13", "sourcedb": "MOFSimplify Thermal Dataset"},
        ],
    }
    out = enrich_table_item(item, question="Which MOFs are thermally stable?")
    assert out["title"].startswith("Thermal stability")
    assert out["row_count"] == 2
    assert out["columns_meta"][0]["kind"] == "badge"
    assert out["columns_meta"][0]["description"]
    assert out["columns_meta"][1]["label"] == "Thermal stability (°C)"
    assert out.get("display_columns")
    assert out["columns_meta"][0].get("visible") is True
    assert out["chart"]["y_key"] == "thermal"


def test_enrich_data_items_preserves_maps():
    data = enrich_data_items(
        [
            {"type": "table", "vars": ["avgPLD"], "bindings": [{"avgPLD": "3.8"}]},
            {"type": "map", "title": "Footprint", "wkt_crs84": "POINT(0 0)"},
        ],
        question="PLD?",
    )
    assert len(data) == 2
    assert data[0]["columns_meta"]
    assert data[1]["type"] == "map"


if __name__ == "__main__":
    test_plan_display_columns_hides_internal_mof()
    test_human_column_label()
    test_enrich_table_item_adds_metadata()
    test_enrich_data_items_preserves_maps()
    print("table_presentation tests OK")
