"""
TWA City TWA MCP Server

FastMCP server exposing SPARQL-backed tools for Bremen, Kaiserslautern, and Pirmasens (UBEM).
Query limits are hardcoded in twa_city_operations.py.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from functools import wraps

from fastmcp import FastMCP

from mini_marie.row_filters import filter_row_pool_text
from mini_marie.zaha.twa_city.twa_city_operations import (
    CITY_ENDPOINTS,
    format_results_as_tsv,
    get_building_count,
    get_building_properties,
    get_buildings_by_usage,
    get_height_stats,
    get_property_coverage,
    get_top_buildings_by_height,
    get_usage_type_counts,
    lookup_building_by_uuid_fragment,
)
from mini_marie.zaha.twa_city.pirmasens_ontop_cache import get_cache_status_text
from mini_marie.zaha.twa_city.pirmasens_ontop_operations import (
    list_endpoints_tsv,
    list_entities_by_type,
    run_sparql_tsv,
)
from mini_marie.zaha.twa_city.pirmasens_operations import (
    get_building_ubem_profile,
    get_class_overview,
    get_co2_savings_stats,
    get_device_type_counts,
    get_heat_supply_stats,
    get_pirmasens_schema_summary,
    get_radiation_stats,
    get_solar_collector_sample,
    get_top_buildings_by_co2_savings,
    get_top_buildings_by_heat_supply,
    get_ubem_class_counts,
    lookup_dabgeo_building,
)
from mini_marie.zaha.twa_city.gis_visualization import (
    generate_building_map,
    summarize_map_buildings,
)
from mini_marie.zaha.twa_city.workflow_mcp import (
    MCP_ONLINE_LIMIT,
    list_workflows_text,
    replay_workflow_offline,
    run_workflow_online,
)

logger = logging.getLogger("twa_city_mcp")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.WARNING)
    handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] [%(name)s] %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)


def twa_city_tool_logger(func):
    """Log MCP tool invocations."""

    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.info("Tool call: %s args=%s kwargs=%s", func.__name__, args, kwargs)
            try:
                return await func(*args, **kwargs)
            except Exception:
                logger.exception("Tool failed: %s", func.__name__)
                raise

        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger.info("Tool call: %s args=%s kwargs=%s", func.__name__, args, kwargs)
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception("Tool failed: %s", func.__name__)
            raise

    return sync_wrapper


mcp = FastMCP(name="twa-city")


@mcp.prompt(name="instruction")
def instruction_prompt():
    cities = ", ".join(sorted(CITY_ENDPOINTS))
    return (
        "Query TWA city building TWAs (CityGML + ontobuiltenv + Pirmasens UBEM) via SPARQL tools.\n\n"
        f"**Cities:** {cities}\n"
        "**Building IRI (Bremen/KL):** https://theworldavatar.io/kg/Building/{{uuid}}\n"
        "**Building IRI (Pirmasens):** https://www.theworldavatar.com/kg/Building/{{uuid}}\n"
        "**DABGEO/UBEM IRI (Pirmasens):** https://www.theworldavatar.com/kg/DABGEO/Building_{{GebId}}\n"
        "**Usage prefix:** https://www.theworldavatar.com/kg/ontobuiltenv/ "
        "(e.g. Domestic, Office, IndustrialFacility)\n\n"
        "**Corpus tools:**\n"
        "1. get_building_count(city) - total buildings\n"
        "2. get_property_coverage(city) - counts with height, address, usage, geometry, label "
        "(Pirmasens also reports dabgeo_buildings, with_ubem_devices)\n"
        "3. get_usage_type_counts(city) - buildings per usage type\n"
        "4. get_height_stats(city) - min/max/avg measuredHeight (metres)\n\n"
        "**Ranking / filter tools:**\n"
        "5. get_top_buildings_by_height(city) - tallest buildings\n"
        "6. get_buildings_by_usage(city, usage_type) - e.g. usage_type='Domestic' or 'Office'\n"
        "7. lookup_building_by_uuid_fragment(city, uuid_fragment) - search by UUID substring\n"
        "8. get_building_properties(city, uuid_fragment) - predicates for first match (no WKT)\n\n"
        "**Pirmasens UBEM / energy tools (city must be 'pirmasens'):**\n"
        "9. get_pirmasens_schema_summary() - live layer overview (queries endpoint, no static counts)\n"
        "10. get_class_overview(city) - top RDF classes in graph\n"
        "11. get_ubem_class_counts(city) - ontoubemmp class counts\n"
        "12. get_heat_supply_stats(city) - annual heat supply min/max/avg (kWh/m²)\n"
        "13. get_co2_savings_stats(city) - CO2 savings min/max/avg from solar modelling\n"
        "14. get_radiation_stats(city) - received radiation min/max/avg\n"
        "15. get_device_type_counts(city) - solar/plate/tube collector counts\n"
        "16. get_top_buildings_by_heat_supply(city) - top DABGEO buildings by heat output\n"
        "17. get_top_buildings_by_co2_savings(city) - top by modelled CO2 savings\n"
        "18. get_solar_collector_sample(city) - sample with CO2 + radiation\n"
        "19. get_building_ubem_profile(city, building_id_fragment) - per-device heat/CO2/radiation\n"
        "20. lookup_dabgeo_building(building_id_fragment, city) - DABGEO lookup by GebId substring\n\n"
        "**Pirmasens Ontop stacks (generic atomic SPARQL):**\n"
        "21. list_pirmasens_endpoints() - toilet, plots, solarthermie, city SPARQL URLs\n"
        "22. run_sparql(endpoint_id, query) - arbitrary SELECT on a registered endpoint\n"
        "23. list_entities(endpoint_id, class_iri) - atomic class listing (full IRI rows)\n"
        "24. filter_row_pool(input_tsv, filters_json) - generic numeric/string row filters\n\n"
        "**GIS visualization:**\n"
        "25. generate_building_map(city, mode, limit) - query footprint WKT and write Leaflet HTML map\n"
        "   - mode='top_height' (default): tallest buildings with polygons\n"
        "   - mode='bbox': buildings in city centre window (falls back to top_height)\n\n"
        "**Scalable workflows (online probe → record → offline replay):**\n"
        "26. list_workflows - available workflow definitions\n"
        "27. run_workflow_online(workflow_name, parameters_json) - online probe LIMIT 10\n"
        "28. replay_workflow_offline(recording_path) - rerun without online limits\n\n"
        "**Workflow pattern:**\n"
        "- Online (agent): small LIMIT (~10) validates call chain; recording saved under workflow_runs/\n"
        "- Offline: replay_workflow_offline on recording_path for full-scale SPARQL\n\n"
        "**Notes:**\n"
        "- Pass city as 'bremen', 'kaiserslautern' (aliases: kl), or 'pirmasens'.\n"
        "- Pirmasens has 3D POLYGON Z geometries; maps flatten to 2D.\n"
        "- UBEM metrics link via DABGEO buildings → hasDevice → producesEnergy / producesCO2Savings.\n"
        "- **Numeric filters:** atomic list (full IRI + numeric column) → filter_rows / top_n_by_field "
        "(do not bake thresholds into SPARQL); use filter_row_pool or city_ranked_buildings workflows.\n"
        "- Row limits are hardcoded (typically 10).\n"
        "- measuredHeight is in metres; not all buildings have height in KL.\n"
        "- Do not expect footprint area via hasMetricArea (often empty).\n"
        "- All outputs are TSV.\n"
        "- GIS maps saved under mini_marie/zaha/twa_city/maps/ as HTML (open in browser).\n"
    )


def _tsv_or_message(results, empty_message: str) -> str:
    if not results:
        return empty_message
    return format_results_as_tsv(results)


@twa_city_tool_logger
@mcp.tool(name="get_building_count", description="Total number of CityGML buildings in the city TWA")
async def get_building_count_tool(city: str) -> str:
    return _tsv_or_message(get_building_count(city), f"No building count for city: {city}")


@twa_city_tool_logger
@mcp.tool(
    name="get_property_coverage",
    description="How many buildings have height, storeys, address, usage, geometry, or label",
)
async def get_property_coverage_tool(city: str) -> str:
    return _tsv_or_message(get_property_coverage(city), f"No property coverage for city: {city}")


@twa_city_tool_logger
@mcp.tool(
    name="get_usage_type_counts",
    description="Building counts per ontobuiltenv usage type (Domestic, Office, etc.)",
)
async def get_usage_type_counts_tool(city: str) -> str:
    return _tsv_or_message(get_usage_type_counts(city), f"No usage type counts for city: {city}")


@twa_city_tool_logger
@mcp.tool(
    name="get_height_stats",
    description="Min, max, and average measuredHeight (metres) for buildings with height data",
)
async def get_height_stats_tool(city: str) -> str:
    return _tsv_or_message(get_height_stats(city), f"No height stats for city: {city}")


@twa_city_tool_logger
@mcp.tool(
    name="get_top_buildings_by_height",
    description="Top buildings by measuredHeight with optional storeys, usage type, and label",
)
async def get_top_buildings_by_height_tool(city: str) -> str:
    return _tsv_or_message(
        get_top_buildings_by_height(city),
        f"No buildings with height found for city: {city}",
    )


@twa_city_tool_logger
@mcp.tool(
    name="get_buildings_by_usage",
    description="Top buildings for an ontobuiltenv usage type (e.g. Domestic, Office, IndustrialFacility)",
)
async def get_buildings_by_usage_tool(city: str, usage_type: str) -> str:
    results = get_buildings_by_usage(city, usage_type)
    return _tsv_or_message(
        results,
        f"No buildings found for city={city} usage_type={usage_type}",
    )


@twa_city_tool_logger
@mcp.tool(
    name="lookup_building_by_uuid_fragment",
    description="Search buildings by substring in the Building IRI (UUID fragment)",
)
async def lookup_building_by_uuid_fragment_tool(city: str, uuid_fragment: str) -> str:
    results = lookup_building_by_uuid_fragment(city, uuid_fragment)
    return _tsv_or_message(
        results,
        f"No buildings matching UUID fragment '{uuid_fragment}' in {city}",
    )


@twa_city_tool_logger
@mcp.tool(
    name="get_building_properties",
    description="Predicate/value pairs for the first building matching a UUID fragment (excludes geo:asWKT)",
)
async def get_building_properties_tool(city: str, uuid_fragment: str) -> str:
    results = get_building_properties(city, uuid_fragment)
    return _tsv_or_message(
        results,
        f"No properties for UUID fragment '{uuid_fragment}' in {city}",
    )


@twa_city_tool_logger
@mcp.tool(
    name="generate_building_map",
    description=(
        "Query building footprint polygons (GeoSPARQL WKT) and write an interactive Leaflet HTML map. "
        "Returns map file path and building summary TSV."
    ),
)
async def generate_building_map_tool(
    city: str,
    mode: str = "top_height",
    limit: int = 10,
) -> str:
    if limit > 20:
        limit = 20
    path, rows, geojson = generate_building_map(city=city, mode=mode, limit=limit)
    summary = summarize_map_buildings(rows)
    return (
        f"map_html_path\t{path.resolve()}\n"
        f"feature_count\t{len(geojson['features'])}\n"
        f"mode\t{mode}\n\n"
        f"{summary}"
    )


@twa_city_tool_logger
@mcp.tool(
    name="list_workflows",
    description="List available multi-step SPARQL workflows for online probe and offline replay",
)
async def list_workflows_tool() -> str:
    return list_workflows_text()


@twa_city_tool_logger
@mcp.tool(
    name="run_workflow_online",
    description=(
        "Run a recorded workflow online with LIMIT 10 per SPARQL step. "
        "Pass parameters_json (JSON object) with workflow parameters the agent derived "
        "from the user question — e.g. city, top_n, sort_field, sort_order, usage_type, "
        "min_height_m, include_locations. Prefer workflow city_ranked_buildings for "
        "generic ranking/filter/location questions. Returns compact TSV + recording_path."
    ),
)
async def run_workflow_online_tool(
    workflow_name: str,
    online_limit: int = MCP_ONLINE_LIMIT,
    question: str = "",
    parameters_json: str = "",
) -> str:
    if online_limit > 20:
        online_limit = MCP_ONLINE_LIMIT
    return run_workflow_online(
        workflow_name,
        online_limit=online_limit,
        question=question,
        parameters_json=parameters_json,
    )


@twa_city_tool_logger
@mcp.tool(
    name="replay_workflow_offline",
    description=(
        "Replay a workflow from recording_path with online limits removed/raised for full results. "
        "Use recording_path returned by run_workflow_online."
    ),
)
async def replay_workflow_offline_tool(
    recording_path: str,
    offline_cap: int = 500_000,
    workflow_name: str = "",
    workflow_path: str = "",
) -> str:
    return replay_workflow_offline(
        recording_path,
        offline_cap=offline_cap,
        workflow_name=workflow_name or None,
        workflow_path=workflow_path or None,
    )


@twa_city_tool_logger
@mcp.tool(
    name="filter_row_pool",
    description=(
        "Apply filter_rows clauses to a TSV row pool (numeric or string). "
        "Use after an atomic list step that returns full IRI + extracted values."
    ),
)
async def filter_row_pool_tool(input_tsv: str, filters_json: str, logic: str = "and") -> str:
    return filter_row_pool_text(input_tsv, filters_json, logic=logic)


@twa_city_tool_logger
@mcp.tool(
    name="get_pirmasens_schema_summary",
    description="Live Pirmasens schema overview: queries SPARQL for current counts and energy stats (not static)",
)
async def get_pirmasens_schema_summary_tool(city: str = "pirmasens") -> str:
    return get_pirmasens_schema_summary(city)


@twa_city_tool_logger
@mcp.tool(name="get_class_overview", description="Top RDF classes in the Pirmasens knowledge graph")
async def get_class_overview_tool(city: str = "pirmasens") -> str:
    return _tsv_or_message(get_class_overview(city), f"No class overview for city: {city}")


@twa_city_tool_logger
@mcp.tool(
    name="get_ubem_class_counts",
    description="Counts per ontoubemmp class (AnnualHeatSupply, Radabshz, RoofSolarCollectors, etc.)",
)
async def get_ubem_class_counts_tool(city: str = "pirmasens") -> str:
    return _tsv_or_message(get_ubem_class_counts(city), f"No UBEM class counts for city: {city}")


@twa_city_tool_logger
@mcp.tool(
    name="get_heat_supply_stats",
    description="Min/max/avg annual heat supply (kWh/m²) from thermal collector UBEM modelling",
)
async def get_heat_supply_stats_tool(city: str = "pirmasens") -> str:
    return _tsv_or_message(get_heat_supply_stats(city), f"No heat supply stats for city: {city}")


@twa_city_tool_logger
@mcp.tool(
    name="get_co2_savings_stats",
    description="Min/max/avg annual CO2 savings from solar collector UBEM modelling",
)
async def get_co2_savings_stats_tool(city: str = "pirmasens") -> str:
    return _tsv_or_message(get_co2_savings_stats(city), f"No CO2 savings stats for city: {city}")


@twa_city_tool_logger
@mcp.tool(
    name="get_radiation_stats",
    description="Min/max/avg received radiation (Radabshz) from solar collector modelling",
)
async def get_radiation_stats_tool(city: str = "pirmasens") -> str:
    return _tsv_or_message(get_radiation_stats(city), f"No radiation stats for city: {city}")


@twa_city_tool_logger
@mcp.tool(
    name="get_device_type_counts",
    description="UBEM collector device counts per type (solar, plate, tube) on DABGEO buildings",
)
async def get_device_type_counts_tool(city: str = "pirmasens") -> str:
    return _tsv_or_message(get_device_type_counts(city), f"No device counts for city: {city}")


@twa_city_tool_logger
@mcp.tool(
    name="get_top_buildings_by_heat_supply",
    description="Top DABGEO buildings by annual heat supply from thermal collectors (Pirmasens UBEM)",
)
async def get_top_buildings_by_heat_supply_tool(city: str = "pirmasens") -> str:
    return _tsv_or_message(
        get_top_buildings_by_heat_supply(city),
        f"No heat supply rankings for city: {city}",
    )


@twa_city_tool_logger
@mcp.tool(
    name="get_top_buildings_by_co2_savings",
    description="Top DABGEO buildings by modelled annual CO2 savings from solar collectors",
)
async def get_top_buildings_by_co2_savings_tool(city: str = "pirmasens") -> str:
    return _tsv_or_message(
        get_top_buildings_by_co2_savings(city),
        f"No CO2 savings rankings for city: {city}",
    )


@twa_city_tool_logger
@mcp.tool(
    name="get_solar_collector_sample",
    description="Sample Pirmasens buildings with solar collector CO2 savings and radiation values",
)
async def get_solar_collector_sample_tool(city: str = "pirmasens") -> str:
    return _tsv_or_message(get_solar_collector_sample(city), f"No solar collector sample for city: {city}")


@twa_city_tool_logger
@mcp.tool(
    name="get_building_ubem_profile",
    description="UBEM profile for a DABGEO building: devices, heat, CO2 savings, radiation (match by GebId substring)",
)
async def get_building_ubem_profile_tool(city: str, building_id_fragment: str) -> str:
    return _tsv_or_message(
        get_building_ubem_profile(city, building_id_fragment),
        f"No UBEM profile for fragment '{building_id_fragment}' in {city}",
    )


@twa_city_tool_logger
@mcp.tool(
    name="lookup_dabgeo_building",
    description="Find DABGEO/OEMA buildings by GebId substring with OntoCityGML link and device count",
)
async def lookup_dabgeo_building_tool(building_id_fragment: str, city: str = "pirmasens") -> str:
    return _tsv_or_message(
        lookup_dabgeo_building(building_id_fragment, city),
        f"No DABGEO building matching '{building_id_fragment}' in {city}",
    )


@twa_city_tool_logger
@mcp.tool(
    name="list_pirmasens_endpoints",
    description="List Pirmasens Ontop SPARQL endpoints (toilet, plots, solarthermie, city)",
)
async def list_pirmasens_endpoints_tool() -> str:
    return list_endpoints_tsv()


@twa_city_tool_logger
@mcp.tool(
    name="get_pirmasens_ontop_cache_status",
    description="Pirmasens Ontop SQLite cache status (toilet/plots/solarthermie/city SPARQL)",
)
async def get_pirmasens_ontop_cache_status_tool() -> str:
    return get_cache_status_text()


@twa_city_tool_logger
@mcp.tool(
    name="run_sparql",
    description=(
        "Execute a SPARQL SELECT on a registered Pirmasens Ontop endpoint. "
        "endpoint_id: toilet | plots | solarthermie | city. "
        "Appends LIMIT when missing (default 10, max 500)."
    ),
)
async def run_sparql_tool(
    endpoint_id: str,
    query: str,
    limit: int = 10,
) -> str:
    if limit > 500:
        limit = 500
    return run_sparql_tsv(
        endpoint_id,
        query,
        limit=limit,
        empty_message=f"No SPARQL results for endpoint={endpoint_id}",
    )


@twa_city_tool_logger
@mcp.tool(
    name="list_entities",
    description=(
        "List entities of an RDF class on a Pirmasens Ontop endpoint (atomic row pool). "
        "Returns full IRI column suitable for filter_row_pool."
    ),
)
async def list_entities_tool(
    endpoint_id: str,
    class_iri: str,
    var_name: str = "entity",
    limit: int = 10,
) -> str:
    if limit > 500:
        limit = 500
    return _tsv_or_message(
        list_entities_by_type(endpoint_id, class_iri, var_name=var_name, limit=limit),
        f"No entities of type {class_iri!r} on endpoint={endpoint_id}",
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
