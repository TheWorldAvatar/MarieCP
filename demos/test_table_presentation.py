"""Tests for table presentation enrichment."""

from demos.table_presentation import (
    enrich_data_items,
    enrich_table_item,
    human_column_description,
    human_column_label,
)


def test_human_column_label():
    assert human_column_label("avgPLD") == "Average PLD (Å)"
    assert human_column_label("refcode") == "CSD refcode"
    assert human_column_label("mof") == "MOF entry"


def test_human_column_description():
    desc = human_column_description("thermal")
    assert "decomposition" in desc.lower()
    assert "refcode" in human_column_description("refcode").lower()


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
    test_human_column_label()
    test_enrich_table_item_adds_metadata()
    test_enrich_data_items_preserves_maps()
    print("table_presentation tests OK")
