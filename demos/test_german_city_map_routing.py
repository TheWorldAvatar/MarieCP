"""Offline payload → TWA map item shaping for German city location workflows."""

from __future__ import annotations

from demos.twa_adapter import _data_from_offline, _map_items_from_rows, _rows_to_table


def test_recenter_pirmasens_wkt_from_czech_blunder():
    from mini_marie.zaha.twa_city.gis_visualization import recenter_wkts_to_city
    from shapely import wkt as sw

    bad = "POLYGON ((13.587 49.242, 13.588 49.242, 13.588 49.243, 13.587 49.243, 13.587 49.242))"
    fixed = recenter_wkts_to_city([bad], "pirmasens")
    assert len(fixed) == 1
    g = sw.loads(fixed[0])
    assert abs(g.centroid.x - 7.605) < 0.05
    assert abs(g.centroid.y - 49.203) < 0.05


def test_recenter_leaves_bremen_untouched():
    from mini_marie.zaha.twa_city.gis_visualization import recenter_wkts_to_city

    good = "POLYGON ((8.80 53.08, 8.81 53.08, 8.81 53.09, 8.80 53.09, 8.80 53.08))"
    fixed = recenter_wkts_to_city([good], "bremen")
    assert fixed == [good]


def test_map_items_from_rows_supports_multiple_footprints():
    rows = [
        {"building": "http://ex/1", "height": "70", "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"},
        {"building": "http://ex/2", "height": "60", "wkt": "POLYGON((2 2, 3 2, 3 3, 2 3, 2 2))"},
    ]
    items = _map_items_from_rows("bremen top 2", rows)
    assert len(items) == 1
    assert items[0]["type"] == "map"
    assert items[0]["wkt_crs84"].startswith("POLYGON")
    assert len(items[0]["wkt_list"]) == 2


def test_rows_to_table_can_skip_inline_map():
    rows = [{"building": "http://ex/1", "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"}]
    items = _rows_to_table("results", rows, include_map=False)
    assert len(items) == 1
    assert items[0]["type"] == "table"


def test_data_from_offline_prefers_wkt_sidecar_for_map(tmp_path):
    payload = {
        "workflow_name": "city_ranked_buildings",
        "city": "bremen",
        "resolved_parameters": {"city": "bremen", "top_n": 2, "include_locations": True},
        "variables": {
            "top_building_rows": {
                "sample": [
                    {"building": "http://ex/1", "height": "70"},
                    {"building": "http://ex/2", "height": "60"},
                ]
            },
            "buildings_with_wkt": {
                "sample": [
                    {
                        "building": "http://ex/1",
                        "height": "70",
                        "r_wkt": (
                            "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> "
                            "POLYGON Z ((0 0 1, 1 0 1, 1 1 1, 0 1 1, 0 0 1))"
                        ),
                    },
                    {
                        "building": "http://ex/2",
                        "height": "60",
                        "r_wkt": (
                            "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> "
                            "POLYGON Z ((2 2 1, 3 2 1, 3 3 1, 2 3 1, 2 2 1))"
                        ),
                    },
                ]
            },
        },
    }
    path = tmp_path / "offline.json"
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")

    items = _data_from_offline(str(path))
    types = [item["type"] for item in items]
    assert "table" in types
    assert "map" in types
    maps = [item for item in items if item.get("type") == "map"]
    assert maps[0].get("wkt_list")
    assert len(maps[0]["wkt_list"]) == 2
