"""Fetch Singapore building footprints (Ontop) and render Leaflet HTML maps."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from shapely import force_2d, wkt as shapely_wkt
from shapely.geometry import mapping

from mini_marie.zaha.sg_old import ontop_operations as ontop

MAPS_DIR = Path(__file__).resolve().parent / "maps"

FOOTPRINT_COLOR = "#dc2626"


def parse_geosparql_wkt(raw: str):
    """Strip CRS prefix / Z dimension and parse WKT."""
    text = raw.strip()
    if text.startswith("<") and ">" in text:
        text = text.split(">", 1)[1].strip()
    text = re.sub(r"\bPOLYGON Z\b", "POLYGON", text, flags=re.IGNORECASE)
    text = re.sub(r"\bMULTIPOLYGON Z\b", "MULTIPOLYGON", text, flags=re.IGNORECASE)
    return force_2d(shapely_wkt.loads(text))


def fetch_footprints_by_name(name_fragment: str) -> List[Dict[str, Any]]:
    """Return footprint rows from warmed cache with live Ontop fallback."""
    rows = ontop.get_sg_building_footprint_by_name(name_fragment)
    out: List[Dict[str, Any]] = []
    for row in rows:
        wkt_raw = row.get("footprint_wkt") or ""
        if not wkt_raw or row.get("footprint_kind") != "wkt":
            continue
        try:
            geom = parse_geosparql_wkt(wkt_raw)
        except Exception:
            continue
        out.append(
            {
                "name": row.get("name") or name_fragment,
                "building_iri": row.get("building_iri"),
                "wkt": geom.wkt,
                "source": row.get("source") or "ontop",
            }
        )
    return out


def footprints_to_geojson(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    features: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        try:
            geom = shapely_wkt.loads(row["wkt"])
        except Exception:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": {
                    "name": row.get("name") or f"footprint {idx + 1}",
                    "building": row.get("building_iri") or "",
                    "source": row.get("source") or "",
                    "color": FOOTPRINT_COLOR,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _map_center(geojson: Dict[str, Any]) -> tuple[float, float]:
    lons: List[float] = []
    lats: List[float] = []

    def _walk_coords(obj: Any) -> None:
        if isinstance(obj, (list, tuple)):
            if len(obj) >= 2 and isinstance(obj[0], (int, float)) and isinstance(obj[1], (int, float)):
                lons.append(float(obj[0]))
                lats.append(float(obj[1]))
                return
            for part in obj:
                _walk_coords(part)

    for feat in geojson.get("features") or []:
        _walk_coords((feat.get("geometry") or {}).get("coordinates"))
    if not lats:
        return 1.3521, 103.8198
    return sum(lats) / len(lats), sum(lons) / len(lons)


def leaflet_html(title: str, geojson: Dict[str, Any]) -> str:
    center_lat, center_lon = _map_center(geojson)
    gj = json.dumps(geojson)
    safe_title = title.replace("<", "").replace(">", "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{safe_title}</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>html, body, #map {{ height: 100%; margin: 0; }}</style>
</head>
<body>
  <div id="map"></div>
  <script>
    const map = L.map('map').setView([{center_lat}, {center_lon}], 16);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);
    const data = {gj};
    const layer = L.geoJSON(data, {{
      style: feat => ({{
        color: feat.properties.color || '#dc2626',
        weight: 2,
        fillOpacity: 0.35
      }}),
      onEachFeature: (feat, lyr) => {{
        const p = feat.properties;
        lyr.bindPopup('<b>' + p.name + '</b><br/><small>' + (p.building || '') + '</small>');
      }}
    }}).addTo(map);
    if (layer.getBounds().isValid()) map.fitBounds(layer.getBounds(), {{ padding: [24, 24] }});
  </script>
</body>
</html>
"""


def generate_footprint_map(
    name_fragment: str,
    *,
    output_path: Optional[Path] = None,
    title: Optional[str] = None,
) -> tuple[Path, List[Dict[str, Any]], Dict[str, Any]]:
    rows = fetch_footprints_by_name(name_fragment)
    if not rows:
        raise RuntimeError(f"No WKT footprints found for {name_fragment!r}")
    label = title or rows[0].get("name") or name_fragment
    geojson = footprints_to_geojson(rows)
    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", name_fragment.lower()).strip("_") or "footprint"
    path = output_path or (MAPS_DIR / f"{slug}_footprint.html")
    path.write_text(leaflet_html(label, geojson), encoding="utf-8")
    return path, rows, geojson


def summarize_footprints(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "No footprints."
    names = {r.get("name") or "?" for r in rows}
    return f"{len(rows)} polygon(s) for {', '.join(sorted(names))}"
