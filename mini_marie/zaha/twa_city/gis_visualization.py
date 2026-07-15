"""Query building footprints (WKT) and render interactive Leaflet maps."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shapely import force_2d, wkt as shapely_wkt
from shapely.geometry import mapping

from mini_marie.zaha.twa_city.twa_city_operations import (
    ONTOBUILTENV_PREFIX,
    QUERIES_DIR,
    execute_sparql,
    format_results_as_tsv,
    load_query,
    resolve_city,
)

MAPS_DIR = Path(__file__).resolve().parent / "maps"

# Default map centres (lon, lat) and ~2 km bbox half-width in degrees
CITY_VIEW = {
    "bremen": {"center": [53.0793, 8.8017], "half_deg": 0.02},
    "kaiserslautern": {"center": [49.4431, 7.7681], "half_deg": 0.015},
    "pirmasens": {"center": [49.2030, 7.6050], "half_deg": 0.02},
}

MAP_BUILDING_LIMIT = 25
MAP_WKT_TIMEOUT_SECONDS = 180

USAGE_COLORS = {
    "Domestic": "#3388ff",
    "IndustrialFacility": "#e67e22",
    "Office": "#9b59b6",
    "University": "#2ecc71",
    "MultiResidential": "#1abc9c",
    "SingleResidential": "#3498db",
    "CulturalFacility": "#e74c3c",
    "RetailEstablishment": "#f39c12",
    "default": "#555555",
}


def parse_geosparql_wkt(raw: str):
    """Strip optional CRS IRI prefix and parse WKT with shapely."""
    text = raw.strip()
    if text.startswith("<") and ">" in text:
        text = text.split(">", 1)[1].strip()
    # Drop Z/M for 2D map display if needed
    text = re.sub(r"\bPOLYGON Z\b", "POLYGON", text, flags=re.IGNORECASE)
    text = re.sub(r"\bMULTIPOLYGON Z\b", "MULTIPOLYGON", text, flags=re.IGNORECASE)
    return force_2d(shapely_wkt.loads(text))


def _city_expected_lon_lat(city: str) -> Optional[Tuple[float, float]]:
    key = (city or "").strip().lower().replace(" ", "_")
    if key == "kl":
        key = "kaiserslautern"
    view = CITY_VIEW.get(key)
    if not view:
        return None
    # CITY_VIEW centers are stored as [lat, lon]
    lat, lon = view["center"]
    return float(lon), float(lat)


def recenter_wkts_to_city(
    wkts: List[str],
    city: str,
    *,
    max_offset_deg: float = 0.35,
) -> List[str]:
    """
    Translate WKT footprints when the cluster is far from the known city centre.

    Pirmasens CityGML Ontop currently publishes CRS84 building geometries ~6° too
    far east (western Czech Republic), while the plots Ontop layer is correct.
    Translating the whole cluster to CITY_VIEW keeps relative footprints and puts
    markers on Pirmasens for the Zaha demo map.
    """
    if not wkts:
        return wkts
    expected = _city_expected_lon_lat(city)
    if expected is None:
        return wkts
    exp_lon, exp_lat = expected

    geoms = []
    for text in wkts:
        try:
            geoms.append(parse_geosparql_wkt(text) if text.lstrip().startswith("<") else force_2d(shapely_wkt.loads(text)))
        except Exception:
            try:
                geoms.append(force_2d(shapely_wkt.loads(text)))
            except Exception:
                continue
    if not geoms:
        return wkts

    from shapely.ops import unary_union
    from shapely.affinity import translate

    cluster = unary_union(geoms)
    clon, clat = cluster.centroid.x, cluster.centroid.y
    # Already near the city — leave alone (Bremen/KL and corrected Pirmasens).
    if abs(clon - exp_lon) <= max_offset_deg and abs(clat - exp_lat) <= max_offset_deg:
        return wkts

    dlon = exp_lon - clon
    dlat = exp_lat - clat
    # Only auto-correct large, city-scale blunders (not tiny GPS noise).
    if abs(dlon) < 1.0 and abs(dlat) < 1.0:
        return wkts

    out: List[str] = []
    for geom in geoms:
        shifted = translate(geom, xoff=dlon, yoff=dlat)
        out.append(shapely_wkt.dumps(force_2d(shifted)))
    return out or wkts


def _usage_short(usage_iri: Optional[str]) -> str:
    if not usage_iri:
        return "unknown"
    if usage_iri.startswith(ONTOBUILTENV_PREFIX):
        return usage_iri[len(ONTOBUILTENV_PREFIX) :]
    return usage_iri.rsplit("/", 1)[-1]


def _usage_color(usage_iri: Optional[str]) -> str:
    return USAGE_COLORS.get(_usage_short(usage_iri), USAGE_COLORS["default"])


def _dedupe_buildings(rows: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """Keep one polygon per building (shortest WKT string ≈ simpler footprint)."""
    by_building: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        bid = row["building"]
        if bid not in by_building or len(row.get("wkt", "")) < len(by_building[bid].get("wkt", "")):
            by_building[bid] = row
    ordered = sorted(
        by_building.values(),
        key=lambda r: float(r.get("height") or 0),
        reverse=True,
    )
    return ordered[:limit]


def fetch_buildings_with_wkt_top_height(
    city: str,
    limit: int = MAP_BUILDING_LIMIT,
) -> List[Dict[str, Any]]:
    endpoint = resolve_city(city)
    query = load_query("20_buildings_with_wkt_top_height.sparql")
    rows = execute_sparql(query, endpoint, timeout=MAP_WKT_TIMEOUT_SECONDS)
    return _dedupe_buildings(rows, limit)


def fetch_buildings_with_wkt_in_bbox(
    city: str,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    limit: int = MAP_BUILDING_LIMIT,
) -> List[Dict[str, Any]]:
    endpoint = resolve_city(city)
    bbox_wkt = (
        f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, "
        f"{max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    )
    template = (QUERIES_DIR / "21_buildings_with_wkt_in_bbox.sparql").read_text(encoding="utf-8")
    query = template.replace("{{bbox_wkt}}", bbox_wkt).replace("{{limit}}", str(limit * 3))
    rows = execute_sparql(query, endpoint, timeout=MAP_WKT_TIMEOUT_SECONDS)
    return _dedupe_buildings(rows, limit)


def rows_to_geojson(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    features: List[Dict[str, Any]] = []
    for row in rows:
        try:
            geom = parse_geosparql_wkt(row["wkt"])
        except Exception:
            continue
        usage = row.get("usage_type")
        bid = row["building"]
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": {
                    "building": bid,
                    "uuid": bid.rsplit("/", 1)[-1],
                    "height_m": float(row.get("height") or 0),
                    "usage": _usage_short(usage),
                    "label": row.get("label") or "",
                    "color": _usage_color(usage),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _leaflet_html(title: str, center_lat: float, center_lon: float, geojson: Dict[str, Any]) -> str:
    gj = json.dumps(geojson)
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>{title}</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>html, body, #map {{ height: 100%; margin: 0; }}</style>
</head>
<body>
  <div id="map"></div>
  <script>
    const map = L.map('map').setView([{center_lat}, {center_lon}], 14);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap'
    }}).addTo(map);
    const data = {gj};
    const layer = L.geoJSON(data, {{
      style: feat => ({{ color: feat.properties.color, weight: 1, fillOpacity: 0.45 }}),
      onEachFeature: (feat, lyr) => {{
        const p = feat.properties;
        lyr.bindPopup(
          '<b>' + (p.label || p.uuid) + '</b><br/>' +
          'Height: ' + p.height_m + ' m<br/>' +
          'Usage: ' + p.usage + '<br/>' +
          '<small>' + p.building + '</small>'
        );
      }}
    }}).addTo(map);
    if (layer.getBounds().isValid()) map.fitBounds(layer.getBounds(), {{ padding: [20, 20] }});
  </script>
</body>
</html>
"""


def generate_building_map(
    city: str,
    mode: str = "top_height",
    limit: int = MAP_BUILDING_LIMIT,
    min_lon: Optional[float] = None,
    min_lat: Optional[float] = None,
    max_lon: Optional[float] = None,
    max_lat: Optional[float] = None,
    output_path: Optional[Path] = None,
) -> Tuple[Path, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Query building footprints and write a Leaflet HTML map.

    Returns (html_path, building_rows, geojson).
    mode: 'top_height' | 'bbox'
    """
    city_key = city.strip().lower().replace(" ", "_")
    if city_key == "kl":
        city_key = "kaiserslautern"

    if mode == "bbox":
        view = CITY_VIEW.get(city_key, CITY_VIEW["bremen"])
        half = view["half_deg"]
        clat, clon = view["center"]
        min_lon = min_lon if min_lon is not None else clon - half
        max_lon = max_lon if max_lon is not None else clon + half
        min_lat = min_lat if min_lat is not None else clat - half
        max_lat = max_lat if max_lat is not None else clat + half
        try:
            rows = fetch_buildings_with_wkt_in_bbox(
                city_key, min_lon, min_lat, max_lon, max_lat, limit=limit
            )
        except Exception:
            rows = []
        if not rows:
            rows = fetch_buildings_with_wkt_top_height(city_key, limit=limit)
            mode = "top_height_fallback"
    else:
        rows = fetch_buildings_with_wkt_top_height(city_key, limit=limit)

    # Upstream Pirmasens CityGML Ontop WKT is currently ~6° too far east.
    corrected = recenter_wkts_to_city([str(r.get("wkt") or "") for r in rows], city_key)
    if len(corrected) == len(rows):
        for row, wkt in zip(rows, corrected):
            if wkt:
                row["wkt"] = wkt

    geojson = rows_to_geojson(rows)
    if not geojson["features"]:
        raise RuntimeError(f"No parseable building geometries for city={city} mode={mode}")

    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = MAPS_DIR / f"{city_key}_{mode}_{limit}.html"
    output_path = Path(output_path)

    title = f"TWA {city_key} buildings ({mode}, n={len(geojson['features'])})"

    from shapely.geometry import shape

    all_lons, all_lats = [], []
    for feat in geojson["features"]:
        bounds = shape(feat["geometry"]).bounds  # minx, miny, maxx, maxy
        all_lons.extend([bounds[0], bounds[2]])
        all_lats.extend([bounds[1], bounds[3]])
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)

    output_path.write_text(
        _leaflet_html(title, center_lat, center_lon, geojson),
        encoding="utf-8",
    )
    return output_path, rows, geojson


def summarize_map_buildings(rows: List[Dict[str, Any]]) -> str:
    summary = []
    for row in rows:
        summary.append(
            {
                "uuid": row["building"].rsplit("/", 1)[-1],
                "height_m": row.get("height"),
                "usage": _usage_short(row.get("usage_type")),
                "label": row.get("label") or "",
            }
        )
    return format_results_as_tsv(summary)
