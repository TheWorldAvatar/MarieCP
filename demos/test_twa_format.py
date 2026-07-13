"""Unit tests for TWA display shaping (no LLM)."""

from __future__ import annotations

import json

from demos.twa_format import (
    _dedupe_rows,
    _humanize_rows,
    _merge_wkts,
    _normalize_wkt,
    _rows_to_twa_items,
    build_twa_data,
    build_twa_narrative_rule,
    kgqa_result_to_twa,
)


def test_humanize_strips_iri_to_label():
    rows = [
        {
            "building_iri": "http://www.theworldavatar.com/kb/ontocitygml/building/123",
            "name": "Abbott Manufacturing Singapore",
            "height": "42",
        }
    ]
    cols, out = _humanize_rows(rows)
    assert "building_iri" in cols or "name" in cols
    assert out[0]["name"] == "Abbott Manufacturing Singapore"
    if "building_iri" in out[0]:
        assert out[0]["building_iri"] == "123"


def test_dedupe_rows_by_building():
    rows = [
        {"building_iri": "http://example/kg/b1", "height": "10"},
        {"building_iri": "http://example/kg/b1", "height": "20"},
        {"building_iri": "http://example/kg/b2", "height": "5"},
    ]
    deduped = _dedupe_rows(rows)
    assert len(deduped) == 2
    heights = {r["building_iri"]: r["height"] for r in deduped}
    assert heights["http://example/kg/b1"] == "20"


def test_rows_to_twa_items_adds_map_for_footprint():
    rows = [
        {
            "name": "Abbott Manufacturing Singapore",
            "footprint_wkt": (
                "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> "
                "POLYGON Z ((103.7 1.3, 103.71 1.3, 103.71 1.31, 103.7 1.31, 103.7 1.3))"
            ),
        }
    ]
    items = _rows_to_twa_items("Abbott", rows, question="Show the footprint map")
    types = [item["type"] for item in items]
    assert "table" in types
    assert "map" in types
    assert items[-1]["wkt_crs84"].startswith("POLYGON")


def test_rows_to_twa_items_map_includes_wkt_list_for_multiple_footprints():
    rows = [
        {
            "name": "Abbott Manufacturing Singapore",
            "footprint_wkt": (
                "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> "
                "POLYGON Z ((103.70 1.30, 103.71 1.30, 103.71 1.31, 103.70 1.31, 103.70 1.30))"
            ),
        },
        {
            "name": "Abbott Manufacturing Singapore",
            "footprint_wkt": (
                "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> "
                "POLYGON Z ((103.72 1.32, 103.73 1.32, 103.73 1.33, 103.72 1.33, 103.72 1.32))"
            ),
        },
    ]
    items = _rows_to_twa_items("Abbott", rows, question="Show the footprint map")
    maps = [item for item in items if item.get("type") == "map"]
    assert maps
    assert maps[0].get("wkt_list")
    assert len(maps[0]["wkt_list"]) >= 2


def test_merge_wkts_single():
    wkt = "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
    assert _merge_wkts([wkt]) == wkt


def test_normalize_wkt_strips_elevation():
    raw = (
        "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> "
        "POLYGON Z ((103.7 1.3 5.0, 103.71 1.3 5.0, 103.71 1.31 5.0, 103.7 1.31 5.0, 103.7 1.3 5.0))"
    )
    wkt = _normalize_wkt(raw)
    assert wkt
    assert " 5.0" not in wkt
    assert wkt.startswith("POLYGON")


def test_build_twa_data_from_tool_outputs():
    kgqa = {
        "question": "How many office buildings are there in Singapore?",
        "online_answer": "There are **1234** office buildings.",
        "metadata": {
            "tool_activity": {
                "tool_outputs": [
                    {
                        "name": "Q12",
                        "content": json.dumps([{"office_building_count": 1234}]),
                    }
                ]
            }
        },
        "timing": {"online_ms": 10},
    }
    data = build_twa_data(kgqa)
    assert data
    table = next(item for item in data if item["type"] == "table")
    assert table["bindings"]
    assert "office_building_count" in table["vars"] or "1234" in str(table["bindings"][0].values())


def test_narrative_rule_uses_sg_summary():
    kgqa = {
        "question": "How many office buildings are there in Singapore?",
        "online_answer": "",
        "metadata": {
            "tool_activity": {
                "tool_outputs": [
                    {
                        "name": "Q12",
                        "content": json.dumps([{"office_building_count": 5678}]),
                    }
                ]
            }
        },
    }
    data = build_twa_data(kgqa)
    text = build_twa_narrative_rule(kgqa["question"], kgqa, data)
    assert "5678" in text
    assert "office" in text.lower()


def test_kgqa_result_to_twa_shape():
    kgqa = {
        "question": "test",
        "online_answer": "hello world answer",
        "metadata": {"tool_activity": {}},
        "timing": {"online_ms": 1},
    }
    payload = kgqa_result_to_twa(kgqa)
    assert payload["metadata"]["steps"]
    assert payload["data"]
    assert "narrative" not in payload


def test_stream_chat_uses_narrative():
    from demos.twa_adapter import stream_chat_events

    chunks = list(
        stream_chat_events(
            "How many buildings?",
            [{"type": "table", "vars": ["count"], "bindings": [{"count": "1"}]}],
            narrative="There is **1** building.",
        )
    )
    body = "".join(chunks)
    assert "1" in body
    assert "building" in body.lower()
