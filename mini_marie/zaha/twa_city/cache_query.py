"""
Cached city row queries: atomic filter_rows → sort → limit on SQLite facets.

Planning is done by the ReAct agent (parameters_json → city_ranked_buildings workflow),
not by keyword heuristics in this module.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from mini_marie.row_filters import filter_rows
from mini_marie.zaha.twa_city.city_cache import CityCache, dedupe_rows_by_building
from mini_marie.zaha.twa_city.twa_city_operations import CITY_ENDPOINTS, format_results_as_tsv

HEIGHT_FACET_FIELDS = frozenset({"building", "height", "storeys", "usage_type", "label"})
LOCATION_FIELDS = frozenset({"wkt", "geometry", "footprint"})
MAX_RESULT_LIMIT = 10_000
DEFAULT_POOL_CAP = 5_000


class FilterClause(BaseModel):
    field: str
    op: str = "eq"
    value: Optional[Union[str, float, int, bool]] = None


class CityBuildingQueryPlan(BaseModel):
    """Explicit query plan (agent/MCP supplies fields — no NL parsing here)."""

    city: str
    properties: List[str] = Field(
        default_factory=lambda: ["building", "height", "label", "usage_type"]
    )
    filters: List[FilterClause] = Field(default_factory=list)
    sort_field: str = "height"
    sort_order: str = "desc"
    limit: Optional[int] = None
    filter_logic: str = "and"
    reason: str = ""


def normalize_city_name(city: str) -> str:
    key = city.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {"kl": "kaiserslautern", "kaiserslautern": "kaiserslautern", "bremen": "bremen"}
    key = aliases.get(key, key)
    if key not in CITY_ENDPOINTS:
        allowed = ", ".join(sorted(CITY_ENDPOINTS))
        raise ValueError(f"Unknown city {city!r}. Use one of: {allowed}")
    return key


def city_has_height_cache(city: str) -> bool:
    city_lc = normalize_city_name(city)
    cache = CityCache()
    try:
        row = cache._conn.execute(
            "SELECT COUNT(*) AS c FROM facet_building_height WHERE city_lc = ?",
            (city_lc,),
        ).fetchone()
        return bool(row and int(row["c"]) > 0)
    finally:
        cache.close()


def plan_from_workflow(workflow: Dict[str, Any]) -> CityBuildingQueryPlan:
    """Map legacy workflow JSON fields to an explicit plan (offline engine helper)."""
    filters: List[FilterClause] = []
    usage = workflow.get("usage_type")
    if usage:
        filters.append(FilterClause(field="usage_type", op="icontains", value=str(usage)))
    for key, op in (
        ("min_height_m", "gte"),
        ("min_height", "gte"),
        ("max_height_m", "lte"),
        ("max_height", "lte"),
    ):
        if workflow.get(key) is not None:
            filters.append(
                FilterClause(field="height", op=op, value=float(workflow[key]))
            )
    return CityBuildingQueryPlan(
        city=str(workflow.get("city") or "bremen"),
        properties=["building", "height", "label", "usage_type"],
        filters=filters,
        sort_field="height",
        sort_order="desc",
        limit=int(workflow["top_n"]) if workflow.get("top_n") is not None else None,
        reason=f"workflow {workflow.get('id') or workflow.get('question', '')[:40]}",
    )


def _usage_contains_from_filters(filters: List[FilterClause]) -> Optional[str]:
    for clause in filters:
        if clause.field in ("usage_type", "usage") and clause.op in ("icontains", "contains", "eq"):
            return str(clause.value or "")
    return None


def _non_usage_filters(filters: List[FilterClause]) -> List[FilterClause]:
    return [f for f in filters if f.field not in ("usage_type", "usage")]


def _effective_limit(plan: CityBuildingQueryPlan) -> Optional[int]:
    if plan.limit is None or plan.limit <= 0:
        return None
    return min(int(plan.limit), MAX_RESULT_LIMIT)


def _prefetch_limit(plan: CityBuildingQueryPlan) -> int:
    limit = _effective_limit(plan)
    if _non_usage_filters(plan.filters):
        if limit is None:
            return DEFAULT_POOL_CAP
        return min(max(limit * 50, 500), DEFAULT_POOL_CAP)
    if limit is not None:
        return limit
    return DEFAULT_POOL_CAP


def _sort_rows(rows: List[Dict[str, Any]], field: str, order: str) -> List[Dict[str, Any]]:
    reverse = (order or "desc").lower() != "asc"

    def key(row: Dict[str, Any]) -> float:
        val = row.get(field)
        try:
            return float(val)
        except (TypeError, ValueError):
            return float("-inf") if reverse else float("inf")

    if field in HEIGHT_FACET_FIELDS or field == "height":
        return sorted(rows, key=key, reverse=reverse)
    return sorted(rows, key=lambda r: str(r.get(field) or "").lower(), reverse=reverse)


def _project_properties(rows: List[Dict[str, Any]], properties: List[str]) -> List[Dict[str, Any]]:
    if not properties or properties == ["*"]:
        return rows
    out: List[Dict[str, Any]] = []
    for row in rows:
        out.append({p: row.get(p) for p in properties if p in row or p == "building"})
    return out


def _enrich_wkt(cache: CityCache, city: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    iris = [str(r.get("building")) for r in rows if r.get("building")]
    if not iris:
        return rows
    loc_rows = cache.local_buildings_with_locations_sql(city, iris)
    wkt_by_building: Dict[str, str] = {}
    for loc in loc_rows:
        b = str(loc.get("building") or loc.get("r_building") or "")
        wkt = loc.get("wkt") or loc.get("r_wkt")
        if b and wkt and b not in wkt_by_building:
            wkt_by_building[b] = str(wkt)
    enriched: List[Dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        b = str(copy.get("building") or "")
        if b in wkt_by_building:
            copy["wkt"] = wkt_by_building[b]
        enriched.append(copy)
    return enriched


def execute_city_building_query(plan: CityBuildingQueryPlan) -> Dict[str, Any]:
    """Atomic pipeline: facet pool → dedupe → filter_rows → sort → limit → optional WKT."""
    city = normalize_city_name(plan.city)
    if not city_has_height_cache(city):
        return {"rows": [], "status": "empty", "summary": f"No height cache for {city}"}

    need_wkt = any(p in LOCATION_FIELDS for p in plan.properties)
    usage_contains = _usage_contains_from_filters(plan.filters)
    prefetch = _prefetch_limit(plan)

    cache = CityCache()
    try:
        pool = dedupe_rows_by_building(
            cache.local_top_n_by_height(city, prefetch, usage_contains=usage_contains)
        )
    finally:
        cache.close()

    filter_spec = {
        "logic": plan.filter_logic,
        "filters": [c.model_dump() for c in plan.filters],
    }
    filtered = filter_rows(pool, filter_spec, {})
    sorted_rows = _sort_rows(filtered, plan.sort_field, plan.sort_order)
    limit = _effective_limit(plan)
    if limit is not None:
        sorted_rows = sorted_rows[:limit]

    if need_wkt and sorted_rows:
        cache = CityCache()
        try:
            sorted_rows = _enrich_wkt(cache, city, sorted_rows)
        finally:
            cache.close()

    rows = _project_properties(sorted_rows, plan.properties)
    return {
        "rows": rows,
        "status": "pass" if rows else "empty",
        "city": city,
        "summary": (
            f"{city}: {len(rows)} rows "
            f"(pool={len(pool)}, filtered={len(filtered)}, limit={limit})"
        ),
    }


def summarize_city_building_rows(
    rows: List[Dict[str, Any]],
    plan: CityBuildingQueryPlan,
) -> str:
    if not rows:
        return f"No matching buildings in the local cache for **{plan.city.title()}**."
    limit = _effective_limit(plan) or len(rows)
    lines = [
        f"**{plan.city.title()}** — {len(rows)} row(s) "
        f"(sorted by {plan.sort_field} {plan.sort_order}, limit {limit}):"
    ]
    for idx, row in enumerate(rows, start=1):
        label = row.get("label") or str(row.get("building", "")).rsplit("/", 1)[-1]
        parts = [f"{idx}. **{label}**"]
        if row.get("height") is not None:
            parts.append(f"height **{row['height']}** m")
        if row.get("usage_type"):
            usage = str(row["usage_type"]).rsplit("/", 1)[-1]
            parts.append(f"usage {usage}")
        if row.get("wkt"):
            parts.append(f"WKT ({len(str(row['wkt']))} chars)")
        lines.append(" — ".join(parts))
    return "\n".join(lines)


def format_plan_results_tsv(plan: CityBuildingQueryPlan) -> str:
    result = execute_city_building_query(plan)
    return format_results_as_tsv(result.get("rows") or [])
