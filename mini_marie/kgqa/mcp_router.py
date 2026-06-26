"""Dynamic MCP server selection for KGQA questions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from mini_marie.kg_catalog import catalog as kg_catalog
from mini_marie.kgqa.question_catalog import CatalogEntry

MAX_MCP_SERVERS = 3

CHEMISTRY_KEYWORDS = {
    "chemistry-ontospecies": [
        "species",
        "formula",
        "inchi",
        "smiles",
        "pka",
        "pubchem",
        "chebi",
        "ontospecies",
        "methylamine",
        "ionic strength",
        "hydrogen bond",
        "h-bond",
        "hbond",
        "ethylene glycol",
        "glycol",
        "donor",
        "acceptor",
        "molecule",
        "compound",
        "chemical",
        "advanced search",
        "physprop",
        "molecular weight",
        "polar surface",
    ],
    "chemistry-ontokin": ["reaction", "mechanism", "kinetic", "ontokin", "thermo"],
    "chemistry-ontocompchem": ["gaussian", "calculation", "orbital", "ontocompchem", "dft"],
    "chemistry-ontozeolite": [
        "zeolite",
        "zeolitic",
        "framework",
        "iza",
        "aen",
        "ontozeolite",
        "unit cell",
        "framework code",
        "guest species",
        "h2s",
        "lattice system",
        "triclinic",
        "occupiable area",
        "accessible area",
        "fau",
        "mfi",
    ],
    "chemistry-ontomops": [
        "polyhedra",
        "cbu",
        "ontomops",
        "mop cage",
        "outer diameter",
        "angstrom",
        "metal-organic polyhedron",
        "building unit",
        "rmsd",
        "ccdc",
        "doi",
    ],
    "chemistry-ontoprovenance": ["provenance", "ontoprovenance"],
    "chemistry-ontopesscan": ["pesscan", "scan", "ontopesscan"],
}

MOF_KEYWORDS = [
    "mof",
    "uio-66",
    "zif-8",
    "zif8",
    "pld",
    "lcd",
    "topology",
    "tobassco",
    "co2 uptake",
    "refcode",
    "metal-organic framework",
    "hkust",
    "mil-101",
    "dut-67",
]

CITY_KEYWORDS = ["bremen", "kaiserslautern", "wkt", "geo", "city"]

MOPS_KEYWORDS = [
    "vmop",
    "irmop",
    "mop",
    "mops",
    "polyhedra",
    "mop synthesis",
    "synthesis route",
    "ccdc",
    "merged_tll",
    "outer diameter",
    "inner sphere",
    "icosahedral",
    "cbu",
    "building unit",
    "chemical building",
    "rmsd",
    "homo-lumo",
    "homo lumo",
    "xtb",
    "calculation parameter",
    "metal-organic polyhedron",
    "metal organic polyhedron",
]

SG_KEYWORDS = {
    "sg-old": [
        "singapore",
        "sg-old",
        "carpark",
        "emission",
        "dispersion",
        "land-use",
        "plot regulation",
        "jurong",
        "pollutant",
        "concentration",
        "gfa",
        "land lot",
        "land plot",
        "landplot",
        "create tower",
        "mmsi",
        "virtual sensor",
        "ontoplot",
        "availablelots",
        "zoning",
        "agricultural",
        "agriculture",
        "agricultur",
    ],
}


@dataclass
class RouteResult:
    mcp_servers: List[str]
    catalog_entry: Optional[CatalogEntry] = None
    catalog_entries: List[CatalogEntry] = field(default_factory=list)
    domain: str = "unknown"
    domains: List[str] = field(default_factory=list)
    reason: str = ""


def _dedupe_keep_order(names: Sequence[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _score_keywords(question: str, keywords: Sequence[str]) -> int:
    q = question.lower()
    return sum(1 for kw in keywords if kw in q)


def _heuristic_route(question: str) -> RouteResult:
    q = question.lower()
    scores: List[tuple[int, str]] = []

    sg_score = _score_keywords(q, SG_KEYWORDS["sg-old"])
    if sg_score:
        scores.append((sg_score + 2, "sg-old"))
    mops_score = _score_keywords(q, MOPS_KEYWORDS)
    if mops_score:
        scores.append((mops_score + 1, "twa-mops"))
    if _score_keywords(q, CITY_KEYWORDS):
        scores.append((_score_keywords(q, CITY_KEYWORDS), "twa-city"))
    for mcp, kws in CHEMISTRY_KEYWORDS.items():
        s = _score_keywords(q, kws)
        if s:
            scores.append((s, mcp))
    if _score_keywords(q, MOF_KEYWORDS):
        scores.append((_score_keywords(q, MOF_KEYWORDS), "mof-twa"))

    scores.sort(key=lambda x: (-x[0], x[1]))
    servers = _dedupe_keep_order([s[1] for s in scores])[:MAX_MCP_SERVERS]

    domain = "unknown"
    if servers:
        if servers[0].startswith("chemistry-"):
            domain = "chemistry"
        elif servers[0] == "mof-twa":
            domain = "mof"
        elif servers[0] == "twa-city":
            domain = "city"
        elif servers[0] == "twa-mops":
            domain = "mops"
        elif servers[0] == "sg-old":
            domain = "sg"
    else:
        servers = ["kg-catalog"]
        domain = "catalog"
        return RouteResult(
            mcp_servers=servers[:MAX_MCP_SERVERS],
            domain=domain,
            reason="fallback: kg-catalog only",
        )

    if "kg-catalog" not in servers and len(servers) < MAX_MCP_SERVERS:
        servers = _dedupe_keep_order(["kg-catalog"] + servers)[:MAX_MCP_SERVERS]

    return RouteResult(
        mcp_servers=servers,
        domain=domain,
        reason="keyword heuristic",
    )


def _sg_signal_score(question: str) -> int:
    q = question.lower()
    return _score_keywords(q, SG_KEYWORDS["sg-old"])


def _chemistry_signal_score(question: str) -> int:
    q = question.lower()
    total = 0
    for kws in CHEMISTRY_KEYWORDS.values():
        total += _score_keywords(q, kws)
    total += _score_keywords(q, MOPS_KEYWORDS)
    total += _score_keywords(q, MOF_KEYWORDS)
    return total


def _merge_cross_domain_servers(
    base_servers: List[str],
    question: str,
) -> List[str]:
    """When both Singapore and chemistry signals are present, expose both MCP families."""
    sg_score = _sg_signal_score(question)
    chem_score = _chemistry_signal_score(question)
    if sg_score < 2 or chem_score < 2:
        return base_servers
    merged = list(base_servers)
    if sg_score >= chem_score and "sg-old" not in merged:
        merged.insert(0, "sg-old")
    if chem_score >= 1:
        for mcp in _heuristic_route(question).mcp_servers:
            if mcp.startswith("chemistry-") and mcp not in merged:
                merged.append(mcp)
    if "kg-catalog" not in merged:
        merged.append("kg-catalog")
    return _dedupe_keep_order(merged)[:MAX_MCP_SERVERS]


def route_question(question: str) -> RouteResult:
    """Sync routing wrapper — prefers LLM when available, else exact catalog match."""
    import asyncio

    from mini_marie.kgqa.llm_router import route_question_async

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        return _fallback_route_sync(question)
    return asyncio.run(route_question_async(question))


def _fallback_route_sync(question: str) -> RouteResult:
    from mini_marie.kgqa.llm_router import _fallback_route

    return _fallback_route(question, reason="sync route in running event loop")


def domain_for_recording(recording_path: str, workflow_id: Optional[str] = None) -> str:
    """Infer replay domain from path or workflow id prefix."""
    path = recording_path.replace("\\", "/").lower()
    wf = (workflow_id or "").lower()

    if "/chemistry/competency_runs/" in path or wf.startswith("mq"):
        return "chemistry"
    if "/mof_case/competency_runs/" in path or wf.startswith("cq"):
        return "mof_competency"
    if "/twa_city/" in path or "city" in path:
        return "city"
    if "/twa_mops/" in path or "mops" in path:
        return "mops"
    if "/mof_case/workflow_runs/" in path:
        return "mof_workflow"
    if wf.startswith("xq"):
        return "cross_kg"
    return "unknown"
