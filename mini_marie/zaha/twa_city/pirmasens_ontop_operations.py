"""
Generic atomic operations for Pirmasens Ontop stacks beyond the main city TWA.

Endpoints (from german_competency_questions/pirmasens.md):
- toilet: public toilets
- plots: land plots / zoning / planning regulations
- solarthermie: solar thermal collector UBEM slice
- city: main CityGML + DABGEO stack (alias of twa_city_operations CITY_ENDPOINTS)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from mini_marie.zaha.twa_city.twa_city_operations import (
    CITY_ENDPOINTS,
    RESULT_LIMIT,
    execute_sparql,
    format_results_as_tsv,
)

PIRMASENS_ONTOP_ENDPOINTS: Dict[str, str] = {
    "toilet": "https://pirmasens.cmpg.io/ontop-toilet/sparql/",
    "plots": "https://pirmasens.cmpg.io/ontop-plots/sparql/",
    "solarthermie": "https://pirmasens.cmpg.io/ontop-solarthermie/sparql/",
    "city": CITY_ENDPOINTS["pirmasens"],
}

_ENDPOINT_ALIASES = {
    "toilets": "toilet",
    "toilet": "toilet",
    "ontop-toilet": "toilet",
    "plot": "plots",
    "plots": "plots",
    "ontop-plots": "plots",
    "zoning": "plots",
    "solar": "solarthermie",
    "solarthermie": "solarthermie",
    "ontop-solarthermie": "solarthermie",
    "pirmasens": "city",
    "city": "city",
    "ontop": "city",
}

_LIMIT_RE = re.compile(r"\bLIMIT\s+\d+\b", re.I)


def normalize_endpoint_id(endpoint_id: str) -> str:
    """Return canonical endpoint key (toilet, plots, solarthermie, city)."""
    key = (endpoint_id or "").strip().lower().replace(" ", "_").replace("-", "-")
    key = key.replace("_", "-") if key in ("ontop-toilet", "ontop-plots", "ontop-solarthermie") else key
    key_simple = key.replace("-", "_")
    if key in _ENDPOINT_ALIASES:
        return _ENDPOINT_ALIASES[key]
    if key_simple in _ENDPOINT_ALIASES:
        return _ENDPOINT_ALIASES[key_simple]
    if key in PIRMASENS_ONTOP_ENDPOINTS:
        return key
    raise ValueError(
        f"Unknown endpoint_id={endpoint_id!r}. "
        f"Use one of: {', '.join(sorted(PIRMASENS_ONTOP_ENDPOINTS))}"
    )


def resolve_pirmasens_endpoint(endpoint_id: str) -> str:
    """Resolve endpoint_id to SPARQL URL."""
    return PIRMASENS_ONTOP_ENDPOINTS[normalize_endpoint_id(endpoint_id)]


def list_pirmasens_endpoints() -> List[Dict[str, str]]:
    """Catalog of Pirmasens Ontop SPARQL endpoints for agents."""
    return [
        {"endpoint_id": key, "sparql_url": url, "description": _endpoint_description(key)}
        for key, url in sorted(PIRMASENS_ONTOP_ENDPOINTS.items())
    ]


def _endpoint_description(key: str) -> str:
    return {
        "toilet": "Public toilets (wheelchair access, fees, facilities)",
        "plots": "Land plots, zoning types, planning regulations (GRZ, BMZ, height)",
        "solarthermie": "Solar thermal collectors, annual heat supply, CO2 savings",
        "city": "CityGML buildings + DABGEO/OEMA UBEM (main Pirmasens TWA)",
    }.get(key, key)


def _ensure_limit(query: str, limit: int) -> str:
    q = query.strip()
    if _LIMIT_RE.search(q):
        return q
    return f"{q}\nLIMIT {limit}"


def run_sparql_on_endpoint(
    endpoint_id: str,
    query: str,
    *,
    limit: int = RESULT_LIMIT,
    timeout: int = 120,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:
    """Execute arbitrary SPARQL SELECT on a registered Pirmasens Ontop endpoint."""
    from mini_marie.zaha.twa_city.pirmasens_ontop_cache import invoke_run_sparql

    capped = min(max(limit, 1), 500)
    rows, _meta = invoke_run_sparql(
        endpoint_id,
        query,
        mode="online",
        limit=capped,
        use_cache=use_cache,
        timeout=timeout,
    )
    return rows


def list_entities_by_type(
    endpoint_id: str,
    class_iri: str,
    *,
    var_name: str = "entity",
    limit: int = RESULT_LIMIT,
) -> List[Dict[str, Any]]:
    """Atomic list: entities of an RDF class on a Pirmasens Ontop endpoint."""
    var = re.sub(r"[^\w]", "", var_name) or "entity"
    iri = class_iri.strip()
    if not (iri.startswith("<") and iri.endswith(">")):
        iri = f"<{iri}>"
    query = f"SELECT ?{var} WHERE {{ ?{var} a {iri} . }}"
    return run_sparql_on_endpoint(endpoint_id, query, limit=limit)


def run_sparql_tsv(
    endpoint_id: str,
    query: str,
    *,
    limit: int = RESULT_LIMIT,
    empty_message: str = "No results found",
) -> str:
    rows = run_sparql_on_endpoint(endpoint_id, query, limit=limit)
    if not rows:
        return empty_message
    return format_results_as_tsv(rows)


def list_endpoints_tsv() -> str:
    rows = list_pirmasens_endpoints()
    return format_results_as_tsv(rows)
