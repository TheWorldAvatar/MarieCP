"""
Pirmasens-specific TWA operations — CityGML buildings + DABGEO/OEMA UBEM energy layer.

Pirmasens uses a richer stack than Bremen/KL:
- CityGML buildings with 3D footprints and bldg:measuredHeight
- DABGEO/OEMA buildings with solar/thermal collector devices
- UBEM metrics via om:hasValue chains (heat, CO2 savings, radiation)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from mini_marie.zaha.twa_city.twa_city_operations import (
    LOOKUP_LIMIT,
    PROPERTY_LIMIT,
    RESULT_LIMIT,
    _escape_literal,
    execute_sparql,
    load_query,
    resolve_city,
)

PIRMASENS_QUERIES_DIR = Path(__file__).resolve().parent / "queries" / "pirmasens"

UBEM_PREFIX = "http://www.theworldavatar.com/kg/ontoubemmp/"
OEMA_PREFIX = "http://www.purl.org/oema/enaeq/"
OM_PREFIX = "http://www.ontology-of-units-of-measure.org/resource/om-2/"
BUILDING_IRI_PREFIX = "https://www.theworldavatar.com/kg/Building/"
DABGEO_IRI_PREFIX = "https://www.theworldavatar.com/kg/DABGEO/"


def _require_pirmasens(city: str) -> str:
    """Return SPARQL endpoint; raise if city is not Pirmasens."""
    key = city.strip().lower().replace(" ", "_").replace("-", "_")
    if key not in ("pirmasens",):
        raise ValueError("UBEM tools require city='pirmasens'")
    return resolve_city(city)


def load_pirmasens_query(name: str) -> str:
    path = PIRMASENS_QUERIES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Pirmasens query not found: {path}")
    return path.read_text(encoding="utf-8")


def run_pirmasens_query(name: str, city: str = "pirmasens", **kwargs: Any) -> List[Dict[str, Any]]:
    query = load_pirmasens_query(name)
    use_cache = kwargs.pop("use_cache", True)
    from mini_marie.zaha.twa_city.pirmasens_ontop_cache import invoke_run_sparql

    rows, _meta = invoke_run_sparql(
        "city",
        query,
        mode="online",
        limit=int(kwargs.get("limit", RESULT_LIMIT)),
        use_cache=use_cache,
        timeout=int(kwargs.get("timeout", 120)),
    )
    return rows


def get_pirmasens_property_coverage(city: str = "pirmasens") -> List[Dict[str, Any]]:
    """CityGML + DABGEO/UBEM coverage metrics."""
    return run_pirmasens_query("15_property_coverage.sparql", city)


def get_pirmasens_usage_type_counts(city: str = "pirmasens") -> List[Dict[str, Any]]:
    """Usage counts via hasPropertyUsage (kg/Domestic_* types)."""
    return run_pirmasens_query("14_usage_type_counts.sparql", city)


def get_ubem_class_counts(city: str = "pirmasens") -> List[Dict[str, Any]]:
    """Counts per ontoubemmp class (AnnualHeatSupply, Radabshz, etc.)."""
    return run_pirmasens_query("ubem_class_counts.sparql", city)


def get_class_overview(city: str = "pirmasens") -> List[Dict[str, Any]]:
    """Top RDF classes in the Pirmasens graph."""
    return run_pirmasens_query("class_overview.sparql", city)


def get_heat_supply_stats(city: str = "pirmasens") -> List[Dict[str, Any]]:
    """Min/max/avg annual heat supply (kWh/m² via energyPerArea dimension)."""
    return run_pirmasens_query("heat_supply_stats.sparql", city)


def get_co2_savings_stats(city: str = "pirmasens") -> List[Dict[str, Any]]:
    """Min/max/avg annual CO2 savings from solar collector modelling."""
    return run_pirmasens_query("co2_savings_stats.sparql", city)


def get_radiation_stats(city: str = "pirmasens") -> List[Dict[str, Any]]:
    """Min/max/avg received radiation (Radabshz) values."""
    return run_pirmasens_query("radiation_stats.sparql", city)


def get_device_type_counts(city: str = "pirmasens") -> List[Dict[str, Any]]:
    """Collector device counts per DABGEO building (solar, plate, tube)."""
    return run_pirmasens_query("device_type_counts.sparql", city)


def get_top_buildings_by_heat_supply(city: str = "pirmasens") -> List[Dict[str, Any]]:
    """Top DABGEO buildings by annual heat supply from thermal collectors."""
    endpoint = _require_pirmasens(city)
    query = f"""
PREFIX ubem: <{UBEM_PREFIX}>
PREFIX oema: <{OEMA_PREFIX}>
PREFIX om: <{OM_PREFIX}>
SELECT ?dab_building ?device ?device_type ?heat_kwh_per_m2
WHERE {{
  ?dab_building a oema:Building .
  ?dab_building ubem:hasDevice ?device .
  ?device a ?device_type .
  ?device oema:producesEnergy ?heat .
  ?heat om:hasValue ?val .
  ?val om:hasNumericalValue ?heat_kwh_per_m2 .
}}
ORDER BY DESC(xsd:decimal(?heat_kwh_per_m2))
LIMIT {RESULT_LIMIT}
"""
    return execute_sparql(query, endpoint)


def get_top_buildings_by_co2_savings(city: str = "pirmasens") -> List[Dict[str, Any]]:
    """Top DABGEO buildings by modelled annual CO2 savings (solar collectors)."""
    endpoint = _require_pirmasens(city)
    query = f"""
PREFIX ubem: <{UBEM_PREFIX}>
PREFIX oema: <{OEMA_PREFIX}>
PREFIX om: <{OM_PREFIX}>
SELECT ?dab_building ?solar_device ?co2_savings
WHERE {{
  ?dab_building a oema:Building .
  ?dab_building ubem:hasDevice ?solar_device .
  ?solar_device a ubem:RoofSolarCollectors .
  ?solar_device ubem:producesCO2Savings ?co2 .
  ?co2 om:hasValue ?val .
  ?val om:hasNumericalValue ?co2_savings .
}}
ORDER BY DESC(xsd:decimal(?co2_savings))
LIMIT {RESULT_LIMIT}
"""
    return execute_sparql(query, endpoint)


def get_building_ubem_profile(city: str, building_id_fragment: str) -> List[Dict[str, Any]]:
    """
    UBEM profile for a DABGEO or CityGML building (match by ID substring).

    Returns device types, heat supply, CO2 savings, and radiation per collector.
    """
    endpoint = _require_pirmasens(city)
    fragment = _escape_literal(building_id_fragment.strip())
    query = f"""
PREFIX ubem: <{UBEM_PREFIX}>
PREFIX oema: <{OEMA_PREFIX}>
PREFIX om: <{OM_PREFIX}>
SELECT ?dab_building ?device ?device_type ?heat ?co2 ?radiation
WHERE {{
  ?dab_building a oema:Building .
  FILTER(CONTAINS(LCASE(STR(?dab_building)), LCASE("{fragment}")))
  ?dab_building ubem:hasDevice ?device .
  ?device a ?device_type .
  OPTIONAL {{
    ?device oema:producesEnergy ?heat_q .
    ?heat_q om:hasValue ?hv .
    ?hv om:hasNumericalValue ?heat .
  }}
  OPTIONAL {{
    ?device ubem:producesCO2Savings ?co2_q .
    ?co2_q om:hasValue ?cv .
    ?cv om:hasNumericalValue ?co2 .
  }}
  OPTIONAL {{
    ?device ubem:receivesRadiation ?rad_q .
    ?rad_q om:hasValue ?rv .
    ?rv om:hasNumericalValue ?radiation .
  }}
}}
LIMIT {PROPERTY_LIMIT}
"""
    return execute_sparql(query, endpoint)


def lookup_dabgeo_building(building_id_fragment: str, city: str = "pirmasens") -> List[Dict[str, Any]]:
    """Find DABGEO buildings and linked OntoCityGML representation."""
    endpoint = _require_pirmasens(city)
    fragment = _escape_literal(building_id_fragment.strip())
    query = f"""
PREFIX ubem: <{UBEM_PREFIX}>
SELECT ?dab_building ?ontocitygml_rep ?device_count
WHERE {{
  ?dab_building a <{OEMA_PREFIX}Building> .
  FILTER(CONTAINS(LCASE(STR(?dab_building)), LCASE("{fragment}")))
  OPTIONAL {{
    ?dab_building <https://www.theworldavatar.com/kg/ontobuiltenv/hasOntoCityGMLRepresentation> ?ontocitygml_rep .
  }}
  {{
    SELECT ?dab_building (COUNT(?d) AS ?device_count)
    WHERE {{
      ?dab_building a <{OEMA_PREFIX}Building> .
      FILTER(CONTAINS(LCASE(STR(?dab_building)), LCASE("{fragment}")))
      ?dab_building ubem:hasDevice ?d .
    }}
    GROUP BY ?dab_building
  }}
}}
LIMIT {LOOKUP_LIMIT}
"""
    return execute_sparql(query, endpoint)


def get_solar_collector_sample(city: str = "pirmasens") -> List[Dict[str, Any]]:
    """Sample buildings with solar collector CO2 savings and radiation."""
    endpoint = _require_pirmasens(city)
    query = f"""
PREFIX ubem: <{UBEM_PREFIX}>
PREFIX oema: <{OEMA_PREFIX}>
PREFIX om: <{OM_PREFIX}>
SELECT ?dab_building ?solar_device ?co2_savings ?radiation
WHERE {{
  ?dab_building a oema:Building .
  ?dab_building ubem:hasDevice ?solar_device .
  ?solar_device a ubem:RoofSolarCollectors .
  ?solar_device ubem:producesCO2Savings ?co2_q .
  ?co2_q om:hasValue ?cv .
  ?cv om:hasNumericalValue ?co2_savings .
  ?solar_device ubem:receivesRadiation ?rad_q .
  ?rad_q om:hasValue ?rv .
  ?rv om:hasNumericalValue ?radiation .
}}
LIMIT {RESULT_LIMIT}
"""
    return execute_sparql(query, endpoint)


def get_pirmasens_schema_summary(city: str = "pirmasens") -> str:
    """Live schema overview from SPARQL — counts and stats are queried, not hardcoded."""
    from mini_marie.zaha.twa_city.twa_city_operations import get_building_count, get_height_stats

    building_rows = get_building_count(city)
    citygml_count = building_rows[0].get("building_count", "n/a") if building_rows else "n/a"

    coverage_rows = get_pirmasens_property_coverage(city)
    coverage = {str(r.get("metric", "")): str(r.get("count", "")) for r in coverage_rows}

    height_rows = get_height_stats(city)
    height_line = ""
    if height_rows:
        h = height_rows[0]
        height_line = (
            f"Height (buildings with data): min={h.get('min_height', 'n/a')}m, "
            f"max={h.get('max_height', 'n/a')}m, avg={h.get('avg_height', 'n/a')}m "
            f"(n={h.get('buildings_with_height', 'n/a')})\n"
        )

    heat_rows = get_heat_supply_stats(city)
    heat_line = ""
    if heat_rows:
        t = heat_rows[0]
        heat_line = (
            f"AnnualHeatSupply: min={t.get('min_kwh_per_m2', 'n/a')}, "
            f"max={t.get('max_kwh_per_m2', 'n/a')}, avg={t.get('avg_kwh_per_m2', 'n/a')} "
            f"kWh/m² (n={t.get('measure_count', 'n/a')})\n"
        )

    co2_rows = get_co2_savings_stats(city)
    co2_line = ""
    if co2_rows:
        c = co2_rows[0]
        co2_line = (
            f"AnnualCO2Savings: min={c.get('min_co2_savings', 'n/a')}, "
            f"max={c.get('max_co2_savings', 'n/a')}, avg={c.get('avg_co2_savings', 'n/a')} "
            f"(n={c.get('measure_count', 'n/a')})\n"
        )

    return (
        "Pirmasens data layers (live SPARQL counts):\n"
        f"1. CityGML buildings (bldg:Building): {citygml_count} total\n"
        f"   with_height={coverage.get('with_height', 'n/a')}, "
        f"with_usage={coverage.get('with_usage', 'n/a')}, "
        f"with_geometry={coverage.get('with_geometry', 'n/a')}\n"
        f"   IRI: https://www.theworldavatar.com/kg/Building/{{uuid}}\n"
        f"2. DABGEO/OEMA buildings: {coverage.get('dabgeo_buildings', 'n/a')}; "
        f"with_ubem_devices={coverage.get('with_ubem_devices', 'n/a')}\n"
        f"   IRI: https://www.theworldavatar.com/kg/DABGEO/Building_{{GebId}}\n"
        "3. UBEM devices per DABGEO building: RoofSolarCollectors, "
        "RoofThermalPlateCollectors, RoofThermalTubeCollectors\n"
        "4. Energy metrics via om:hasValue → om:hasNumericalValue:\n"
        f"   {heat_line}"
        f"   {co2_line}"
        f"   {height_line}"
        "Endpoint: https://pirmasens.cmpg.io/ontop/sparql/\n"
        "Map: https://pirmasens.cmpg.io/visualisation/de/map\n"
    )
