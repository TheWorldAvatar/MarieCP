"""Tests for MOF display identity helpers."""

from demos.mof_display_identity import (
    decode_core_mof_slug,
    enrich_rows_with_display_identity,
    mof_row_display_label,
    table_benefits_from_display_column,
)
from demos.table_presentation import enrich_table_item


def test_decode_core_mof_slug():
    slug = "mof_2000%5BCu%5D%5Bsod%5D3%5BASR%5D1"
    assert decode_core_mof_slug(slug) == "Cu · sod · ASR"


def test_display_label_prefers_name_then_refcode():
    assert mof_row_display_label({"name": "ZIF-8", "mof": "mof_x"}) == "ZIF-8"
    assert mof_row_display_label({"refcode": "EWIDUK", "mof": "mof_x"}) == "EWIDUK"


def test_enrich_adds_display_columns():
    rows = enrich_rows_with_display_identity(
        [{"mof": "mof_2000%5BCu%5D%5Bsod%5D3%5BASR%5D1", "source": "CoRE MOF 2025", "topology": "sod"}]
    )
    assert rows[0]["display_label"] == "Cu · sod · ASR"
    assert "topology" in rows[0]["display_detail"]


def test_enrich_table_item_prepends_display_label():
    item = {
        "type": "table",
        "vars": ["mof", "source", "topology"],
        "bindings": [
            {
                "mof": "mof_2000%5BCu%5D%5Bsod%5D3%5BASR%5D1",
                "source": "CoRE MOF 2025",
                "topology": "sod",
            }
        ],
    }
    assert table_benefits_from_display_column(item["bindings"])
    out = enrich_table_item(item, question="Which MOFs have the same topology as ZIF-8?")
    assert out["vars"][0] == "display_label"
    assert out["bindings"][0]["display_label"] == "Cu · sod · ASR"


if __name__ == "__main__":
    test_decode_core_mof_slug()
    test_display_label_prefers_name_then_refcode()
    test_enrich_adds_display_columns()
    test_enrich_table_item_prepends_display_label()
    print("mof_display_identity tests OK")
