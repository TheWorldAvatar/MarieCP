"""Unit tests for sg-old footprint map generation (offline geometry)."""

from __future__ import annotations

from mini_marie.zaha.sg_old.gis_visualization import (
    footprints_to_geojson,
    leaflet_html,
    parse_geosparql_wkt,
)


def test_parse_geosparql_wkt_strips_crs_and_z():
    raw = (
        "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> "
        "POLYGON Z ((103.7 1.3, 103.71 1.3, 103.71 1.31, 103.7 1.31, 103.7 1.3))"
    )
    geom = parse_geosparql_wkt(raw)
    assert geom.geom_type == "Polygon"
    assert geom.exterior.coords[0][0] == 103.7


def test_leaflet_html_renders_geojson():
    rows = [
        {
            "name": "Abbott Manufacturing Singapore",
            "building_iri": "https://example/kg/b1",
            "wkt": "POLYGON((103.7 1.3, 103.71 1.3, 103.71 1.31, 103.7 1.31, 103.7 1.3))",
            "source": "test",
        }
    ]
    geojson = footprints_to_geojson(rows)
    html = leaflet_html("Abbott", geojson)
    assert "leaflet" in html.lower()
    assert "Abbott Manufacturing Singapore" in html
