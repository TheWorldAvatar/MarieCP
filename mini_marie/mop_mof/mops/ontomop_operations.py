"""
Remote OntoMOPs A-box operations (Blazegraph namespace ontomops_ogm).

The full MOP polyhedra corpus (~2.3k MOPs, CBUs, geometry) lives on legacy
Blazegraph hosts, not on theworldavatar.io/chemistry or the local synthesis TWA.

Local synthesis data remains in twa_operations.py (merged TTL).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from mini_marie.cache_paths import mini_marie_cache_root
from mini_marie.mop_mof.mof.mof_operations import execute_sparql, format_results_as_tsv
from mini_marie.zaha.twa_city.twa_city_operations import probe_sparql_endpoint

ONTOMOPS_PREFIX = "https://www.theworldavatar.com/kg/ontomops/"
OM2_PREFIX = "http://www.ontology-of-units-of-measure.org/resource/om-2/"

DEFAULT_ENDPOINT_CANDIDATES: List[str] = [
    "http://68.183.227.15:3838/blazegraph/namespace/ontomops_ogm/sparql",
    "http://174.138.23.221:3838/blazegraph/namespace/ontomops_ogm/sparql",
    "http://174.138.23.221:3839/blazegraph/namespace/ontomops_ogm/sparql",
]

SPARQL_TIMEOUT_SECONDS = 90
PROBE_TIMEOUT_SECONDS = 12
RESULT_LIMIT = 10
ENDPOINT_CACHE_TTL_SECONDS = 3600

MOP_COUNT_QUERY = f"""
PREFIX ontomops: <{ONTOMOPS_PREFIX}>
SELECT (COUNT(DISTINCT ?m) AS ?n) WHERE {{
  ?m a ontomops:MetalOrganicPolyhedron .
}}
"""


def _cache_dir() -> Path:
    d = mini_marie_cache_root() / "mop_blazegraph"
    d.mkdir(parents=True, exist_ok=True)
    return d


def endpoint_probe_cache_path() -> Path:
    return _cache_dir() / "endpoint_probe.json"


def endpoint_candidates() -> List[str]:
    override = os.environ.get("ONTOMOPS_OGM_ENDPOINT", "").strip()
    if override:
        return [override.rstrip("/")]
    extra = os.environ.get("ONTOMOPS_OGM_ENDPOINT_CANDIDATES", "").strip()
    out = list(DEFAULT_ENDPOINT_CANDIDATES)
    if extra:
        for item in extra.split(","):
            url = item.strip().rstrip("/")
            if url and url not in out:
                out.append(url)
    return out


def _read_endpoint_cache() -> Optional[Dict[str, Any]]:
    path = endpoint_probe_cache_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_endpoint_cache(payload: Dict[str, Any]) -> None:
    endpoint_probe_cache_path().write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def probe_all_endpoints(timeout: float = PROBE_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """Probe every candidate; persist report under mini_marie_cache/mop_blazegraph/."""
    results: List[Dict[str, Any]] = []
    working: List[str] = []
    for url in endpoint_candidates():
        row = probe_sparql_endpoint(url, timeout=timeout)
        row["mop_count"] = None
        row["mop_count_error"] = None
        if row.get("ok"):
            working.append(url)
            try:
                count_rows = execute_sparql(
                    MOP_COUNT_QUERY,
                    endpoint=url,
                    timeout=min(int(timeout) + 8, SPARQL_TIMEOUT_SECONDS),
                )
                row["mop_count"] = count_rows[0].get("n") if count_rows else None
            except Exception as exc:
                row["mop_count_error"] = str(exc)[:300]
        results.append(row)

    payload = {
        "probed_at_unix": time.time(),
        "working": working,
        "preferred_endpoint": working[0] if working else None,
        "candidates": endpoint_candidates(),
        "results": results,
    }
    _write_endpoint_cache(payload)
    return payload


def get_endpoint_status(force_probe: bool = False) -> Dict[str, Any]:
    cached = _read_endpoint_cache()
    if not force_probe and cached:
        age = time.time() - float(cached.get("probed_at_unix") or 0)
        if age < ENDPOINT_CACHE_TTL_SECONDS:
            cached = dict(cached)
            cached["from_cache"] = True
            return cached
    report = probe_all_endpoints()
    report["from_cache"] = False
    return report


def resolve_endpoint(force_probe: bool = False) -> str:
    status = get_endpoint_status(force_probe=force_probe)
    endpoint = status.get("preferred_endpoint")
    if endpoint:
        return str(endpoint)
    errors = []
    for row in status.get("results") or []:
        if row.get("error"):
            errors.append(f"{row.get('url')}: {row['error'][:120]}")
    detail = "; ".join(errors[:3]) if errors else "no candidates configured"
    raise RuntimeError(
        "No reachable OntoMOPs Blazegraph endpoint (ontomops_ogm). "
        f"Probe details: {detail}. "
        "Run: python -m mini_marie.mop_mof.mops.probe_blazegraph"
    )


def execute_remote_sparql(
    query: str,
    *,
    endpoint: Optional[str] = None,
    timeout: int = SPARQL_TIMEOUT_SECONDS,
    tool: Optional[str] = None,
    tool_args: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Execute SPARQL against remote Blazegraph.

    On success, writes tool + query caches. When the endpoint is unreachable (or the
    query fails), returns the newest matching cache row if present.
    """
    from mini_marie.mop_mof.mops.mop_blazegraph_cache import MopBlazegraphCache

    cache = MopBlazegraphCache()
    tool_args = tool_args if tool_args is not None else {}

    if _cache_only_mode():
        hit = _lookup_cached_rows(cache, query, tool, tool_args)
        if hit:
            return hit["rows"]
        raise RemoteUnavailableError("ONTOMOPS_CACHE_ONLY=1 and no cache entry for query")

    status = get_endpoint_status(force_probe=False) if endpoint is None else None
    if status and not status.get("preferred_endpoint"):
        hit = _lookup_cached_rows(cache, query, tool, tool_args)
        if hit:
            return hit["rows"]

    try:
        url = endpoint or resolve_endpoint()
        rows = execute_sparql(query, endpoint=url, timeout=timeout)
        cache.put_query(query, url, rows)
        if tool:
            cache.put(tool, tool_args, url, rows)
        return rows
    except Exception as exc:
        hit = _lookup_cached_rows(cache, query, tool, tool_args)
        if hit:
            return hit["rows"]
        raise RemoteUnavailableError(str(exc)) from exc


class RemoteUnavailableError(RuntimeError):
    """Raised when remote Blazegraph is down and no cache entry exists."""


def _cache_only_mode() -> bool:
    return os.environ.get("ONTOMOPS_CACHE_ONLY", "").strip().lower() in ("1", "true", "yes")


def _format_cache_tsv(cached: Dict[str, Any], remote_error: str = "") -> str:
    meta = cached.get("meta") or {}
    header = (
        "status\tcache_fallback\n"
        f"cached_endpoint\t{meta.get('endpoint', '')}\n"
        f"cached_at_unix\t{meta.get('fetched_at_unix', '')}\n"
    )
    if remote_error:
        header += f"remote_error\t{remote_error[:200]}\n"
    rows = cached.get("rows") or []
    if not rows:
        header += "message\tcached query returned no rows\n"
        return header.strip()
    return header + format_results_as_tsv(rows)


def _lookup_cached_rows(
    cache: "MopBlazegraphCache",
    query: str,
    tool: Optional[str],
    tool_args: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if tool and tool_args is not None:
        hit = cache.get(tool, tool_args)
        if hit and hit.get("rows") is not None:
            return hit
    return cache.get_query(query)


def _run_named(tool: str, query: str, **args: Any) -> List[Dict[str, Any]]:
    return execute_remote_sparql(query, tool=tool, tool_args=dict(args))


def _escape_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def get_mop_corpus_stats() -> List[Dict[str, Any]]:
    query = f"""
PREFIX ontomops: <{ONTOMOPS_PREFIX}>
SELECT
  (COUNT(DISTINCT ?mop) AS ?mopCount)
  (COUNT(DISTINCT ?cbu) AS ?cbuCount)
  (COUNT(DISTINCT ?ccdc) AS ?ccdcCount)
WHERE {{
  OPTIONAL {{ ?mop a ontomops:MetalOrganicPolyhedron . }}
  OPTIONAL {{
    ?mop ontomops:hasChemicalBuildingUnit ?cbu .
    ?cbu a ontomops:ChemicalBuildingUnit .
  }}
  OPTIONAL {{
    ?mop ontomops:hasCCDCNumber ?ccdc .
    FILTER(BOUND(?ccdc) && STRLEN(STR(?ccdc)) > 0)
  }}
}}
"""
    return _run_named("get_mop_corpus_stats", query)


def get_mops_by_outer_diameter_min(
    min_angstrom: float,
    limit: int = RESULT_LIMIT,
) -> List[Dict[str, Any]]:
    query = f"""
PREFIX ontomops: <{ONTOMOPS_PREFIX}>
PREFIX om-2: <{OM2_PREFIX}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?mopLabel ?outerDiameter ?unit
WHERE {{
  ?mop a ontomops:MetalOrganicPolyhedron .
  ?mop rdfs:label ?mopLabel .
  ?mop ontomops:hasOuterDiameter ?d .
  ?d om-2:hasNumericalValue ?outerDiameter .
  OPTIONAL {{ ?d om-2:hasUnit ?unit }}
  FILTER(xsd:decimal(?outerDiameter) > {float(min_angstrom)})
}}
ORDER BY DESC(?outerDiameter)
LIMIT {int(limit)}
"""
    return _run_named("get_mops_by_outer_diameter_min", query, min_angstrom=float(min_angstrom), limit=int(limit))


def get_mops_by_cbu_formula(
    cbu_formula: str,
    limit: int = RESULT_LIMIT,
) -> List[Dict[str, Any]]:
    formula = _escape_literal(cbu_formula.strip())
    query = f"""
PREFIX ontomops: <{ONTOMOPS_PREFIX}>
PREFIX om-2: <{OM2_PREFIX}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?mopLabel ?cbuFormula ?innerSphereDiameter ?unit
WHERE {{
  ?mop a ontomops:MetalOrganicPolyhedron .
  ?mop rdfs:label ?mopLabel .
  ?mop ontomops:hasChemicalBuildingUnit ?cbu .
  ?cbu ontomops:hasCBUFormula ?cbuFormula .
  FILTER(STR(?cbuFormula) = "{formula}")
  OPTIONAL {{
    ?mop ontomops:hasPoreSize ?ps .
    ?ps ontomops:hasLargestInnerSphereDiameter ?isd .
    ?isd om-2:hasNumericalValue ?innerSphereDiameter .
    OPTIONAL {{ ?isd om-2:hasUnit ?unit }}
  }}
}}
ORDER BY ?mopLabel
LIMIT {int(limit)}
"""
    return _run_named("get_mops_by_cbu_formula", query, cbu_formula=cbu_formula, limit=int(limit))


def get_assembly_models_by_polyhedral_shape(
    shape_symbol: str,
    limit: int = RESULT_LIMIT,
) -> List[Dict[str, Any]]:
    symbol = _escape_literal(shape_symbol.strip())
    query = f"""
PREFIX ontomops: <{ONTOMOPS_PREFIX}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?modelLabel ?shapeSymbol ?symmetryPointGroup
WHERE {{
  ?model a ontomops:AssemblyModel .
  OPTIONAL {{ ?model rdfs:label ?modelLabel }}
  ?model ontomops:hasPolyhedralShape ?shape .
  ?shape ontomops:hasSymbol ?shapeSymbol .
  FILTER(CONTAINS(LCASE(STR(?shapeSymbol)), LCASE("{symbol}")))
  OPTIONAL {{ ?model ontomops:hasSymmetryPointGroup ?symmetryPointGroup }}
}}
ORDER BY ?modelLabel
LIMIT {int(limit)}
"""
    return _run_named(
        "get_assembly_models_by_polyhedral_shape",
        query,
        shape_symbol=shape_symbol,
        limit=int(limit),
    )


def lookup_remote_mop_by_label(name: str, limit: int = 5) -> List[Dict[str, Any]]:
    label = _escape_literal(name.strip())
    query = f"""
PREFIX ontomops: <{ONTOMOPS_PREFIX}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?mop ?mopLabel ?mopFormula ?ccdcNumber
WHERE {{
  ?mop a ontomops:MetalOrganicPolyhedron .
  ?mop rdfs:label ?mopLabel .
  FILTER(CONTAINS(LCASE(STR(?mopLabel)), LCASE("{label}")))
  OPTIONAL {{ ?mop ontomops:hasMOPFormula ?mopFormula }}
  OPTIONAL {{ ?mop ontomops:hasCCDCNumber ?ccdcNumber }}
}}
ORDER BY ?mopLabel
LIMIT {int(limit)}
"""
    return _run_named("lookup_remote_mop_by_label", query, name=name, limit=int(limit))


def get_mop_provenance_by_formula(mop_formula: str, limit: int = RESULT_LIMIT) -> List[Dict[str, Any]]:
    formula = _escape_literal(mop_formula.strip())
    query = f"""
PREFIX ontomops: <{ONTOMOPS_PREFIX}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?mopLabel ?mopFormula ?referenceDOI ?provenanceLabel
WHERE {{
  ?mop a ontomops:MetalOrganicPolyhedron .
  ?mop ontomops:hasMOPFormula ?mopFormula .
  FILTER(CONTAINS(STR(?mopFormula), "{formula}"))
  OPTIONAL {{ ?mop rdfs:label ?mopLabel }}
  OPTIONAL {{
    ?mop ontomops:hasProvenance ?prov .
    OPTIONAL {{ ?prov rdfs:label ?provenanceLabel }}
    OPTIONAL {{ ?prov ontomops:hasReferenceDOI ?referenceDOI }}
  }}
}}
ORDER BY ?mopLabel
LIMIT {int(limit)}
"""
    return _run_named("get_mop_provenance_by_formula", query, mop_formula=mop_formula, limit=int(limit))


def get_mop_with_largest_pore_diameter(limit: int = 1) -> List[Dict[str, Any]]:
    """Marie MQ51: assembly model type for MOP with largest pore diameter."""
    query = f"""
PREFIX ontomops: <{ONTOMOPS_PREFIX}>
PREFIX om-2: <{OM2_PREFIX}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?mopLabel ?assemblyModelLabel ?poreDiameter ?unit
WHERE {{
  ?mop a ontomops:MetalOrganicPolyhedron .
  OPTIONAL {{ ?mop rdfs:label ?mopLabel }}
  ?mop ontomops:hasAssemblyModel ?am .
  OPTIONAL {{ ?am rdfs:label ?assemblyModelLabel }}
  ?mop ontomops:hasPoreSize ?ps .
  ?ps ontomops:hasPoreDiameter ?pd .
  ?pd om-2:hasNumericalValue ?poreDiameter .
  OPTIONAL {{ ?pd om-2:hasUnit ?unit }}
}}
ORDER BY DESC(xsd:decimal(?poreDiameter))
LIMIT {int(limit)}
"""
    return _run_named("get_mop_with_largest_pore_diameter", query, limit=int(limit))


def get_mops_by_reference_doi(doi: str, limit: int = RESULT_LIMIT) -> List[Dict[str, Any]]:
    """Marie MQ56: MOPs linked to a reference DOI."""
    doi_safe = _escape_literal(doi.strip())
    query = f"""
PREFIX ontomops: <{ONTOMOPS_PREFIX}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?mopLabel ?mopFormula ?referenceDOI
WHERE {{
  ?mop a ontomops:MetalOrganicPolyhedron .
  OPTIONAL {{ ?mop rdfs:label ?mopLabel }}
  OPTIONAL {{ ?mop ontomops:hasMOPFormula ?mopFormula }}
  ?mop ontomops:hasProvenance ?prov .
  ?prov ontomops:hasReferenceDOI ?referenceDOI .
  FILTER(CONTAINS(LCASE(STR(?referenceDOI)), LCASE("{doi_safe}")))
}}
ORDER BY ?mopLabel
LIMIT {int(limit)}
"""
    return _run_named("get_mops_by_reference_doi", query, doi=doi, limit=int(limit))


def get_cbus_as_linear_generic_building_units(
    label_fragment: str = "2-linear",
    limit: int = RESULT_LIMIT,
) -> List[Dict[str, Any]]:
    """Marie MQ57: CBUs functioning as generic building units matching a type label."""
    frag = _escape_literal(label_fragment.strip())
    query = f"""
PREFIX ontomops: <{ONTOMOPS_PREFIX}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?cbuFormula ?gbuTypeLabel ?modularity
WHERE {{
  ?cbu a ontomops:ChemicalBuildingUnit .
  OPTIONAL {{ ?cbu ontomops:hasCBUFormula ?cbuFormula }}
  ?cbu ontomops:isFunctioningAs ?gbu .
  ?gbu ontomops:hasGenericBuildingUnitType ?gbut .
  ?gbut rdfs:label ?gbuTypeLabel .
  OPTIONAL {{ ?gbut ontomops:hasModularity ?modularity }}
  FILTER(CONTAINS(LCASE(STR(?gbuTypeLabel)), LCASE("{frag}")))
}}
ORDER BY ?gbuTypeLabel ?cbuFormula
LIMIT {int(limit)}
"""
    return _run_named(
        "get_cbus_as_linear_generic_building_units",
        query,
        label_fragment=label_fragment,
        limit=int(limit),
    )


def endpoint_status_tsv(force_probe: bool = False) -> str:
    from mini_marie.mop_mof.mops.mop_blazegraph_cache import MopBlazegraphCache

    status = get_endpoint_status(force_probe=force_probe)
    cache_stats = MopBlazegraphCache().stats()
    rows = [
        {
            "preferred_endpoint": status.get("preferred_endpoint") or cache_stats.get("last_known_endpoint") or "",
            "working_count": len(status.get("working") or []),
            "from_cache": status.get("from_cache"),
            "probed_at_unix": status.get("probed_at_unix"),
            "query_cache_entries": cache_stats.get("entries"),
            "cache_fallback_ready": cache_stats.get("entries", 0) > 0,
        }
    ]
    for row in status.get("results") or []:
        rows.append(
            {
                "url": row.get("url"),
                "ok": row.get("ok"),
                "mop_count": row.get("mop_count"),
                "error": (row.get("error") or row.get("mop_count_error") or "")[:160],
            }
        )
    return format_results_as_tsv(rows)


def remote_or_cached_tsv(
    tool: str,
    args: Dict[str, Any],
    fetcher,
    *,
    force_probe: bool = False,
) -> str:
    """Try live remote SPARQL; on failure return cached rows if present."""
    from mini_marie.mop_mof.mops.mop_blazegraph_cache import MopBlazegraphCache

    cache = MopBlazegraphCache()
    preloaded = cache.get(tool, args)
    try:
        rows = fetcher()
        fresh = cache.get(tool, args) or preloaded
        endpoint = (fresh.get("meta") or {}).get("endpoint") if fresh else cache.last_known_endpoint()
        header = f"status\tlive\nendpoint\t{endpoint or ''}\n"
        return header + format_results_as_tsv(rows)
    except Exception as exc:
        hit = cache.get(tool, args) or preloaded
        if hit:
            return _format_cache_tsv(hit, remote_error=str(exc))
        status = get_endpoint_status(force_probe=False)
        hint = (
            "Remote OntoMOPs Blazegraph is unreachable and no cache entry exists for this query. "
            f"preferred_endpoint={status.get('preferred_endpoint')!r}. "
            "Warm cache when endpoint returns: "
            "python -m mini_marie.mop_mof.mops.warm_blazegraph_cache --page"
        )
        return format_results_as_tsv([{"error": str(exc)[:200], "hint": hint}])


__all__ = [
    "DEFAULT_ENDPOINT_CANDIDATES",
    "RemoteUnavailableError",
    "endpoint_candidates",
    "probe_all_endpoints",
    "get_endpoint_status",
    "resolve_endpoint",
    "execute_remote_sparql",
    "get_mop_corpus_stats",
    "get_mops_by_outer_diameter_min",
    "get_mops_by_cbu_formula",
    "get_assembly_models_by_polyhedral_shape",
    "lookup_remote_mop_by_label",
    "get_mop_provenance_by_formula",
    "get_mop_with_largest_pore_diameter",
    "get_mops_by_reference_doi",
    "get_cbus_as_linear_generic_building_units",
    "endpoint_status_tsv",
    "remote_or_cached_tsv",
    "format_results_as_tsv",
]
