"""Aggregate competency and example questions for KGQA routing and GUI."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from mini_marie.cache_paths import repo_root


def _repo_root() -> Path:
    return repo_root()
CHEMISTRY_NS_TO_MCP = {
    "ontospecies": "chemistry-ontospecies",
    "ontokin": "chemistry-ontokin",
    "ontocompchem": "chemistry-ontocompchem",
    "ontozeolite": "chemistry-ontozeolite",
    "ontomops": "chemistry-ontomops",
    "ontoprovenance": "chemistry-ontoprovenance",
    "ontopesscan": "chemistry-ontopesscan",
}


@dataclass
class CatalogEntry:
    id: str
    question: str
    domain: str
    mcp_servers: List[str] = field(default_factory=list)
    workflow_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    kind: str = "competency"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "domain": self.domain,
            "mcp_servers": self.mcp_servers,
            "workflow_id": self.workflow_id,
            "tags": self.tags,
            "kind": self.kind,
        }


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _chemistry_mcp_from_workflow(wf: Dict[str, Any]) -> List[str]:
    servers: List[str] = []
    for step in wf.get("steps") or []:
        ns = (step.get("args") or {}).get("namespace")
        if ns and ns in CHEMISTRY_NS_TO_MCP:
            mcp = CHEMISTRY_NS_TO_MCP[ns]
            if mcp not in servers:
                servers.append(mcp)
    if not servers:
        return ["chemistry-ontospecies"]
    return servers


def _load_mof_entries() -> List[CatalogEntry]:
    path = _repo_root() / "mini_marie" / "mop_mof" / "mof" / "workflows" / "competency_suite.json"
    manifest = _read_json(path) or {}
    out: List[CatalogEntry] = []
    for wf in manifest.get("workflows") or []:
        q = wf.get("question") or wf.get("title") or wf.get("id", "")
        out.append(
            CatalogEntry(
                id=str(wf.get("id", "")),
                question=str(q),
                domain="mof",
                mcp_servers=["mof-twa"],
                workflow_id=str(wf.get("id", "")),
                tags=["competency", "mof"],
                kind="competency",
            )
        )
    return out


def _load_chemistry_entries() -> List[CatalogEntry]:
    path = _repo_root() / "mini_marie" / "marie" / "chemistry" / "workflows" / "competency_suite.json"
    manifest = _read_json(path) or {}
    out: List[CatalogEntry] = []
    for wf in manifest.get("workflows") or []:
        q = wf.get("title") or wf.get("question") or wf.get("id", "")
        out.append(
            CatalogEntry(
                id=str(wf.get("id", "")),
                question=str(q),
                domain="chemistry",
                mcp_servers=_chemistry_mcp_from_workflow(wf),
                workflow_id=str(wf.get("id", "")),
                tags=["competency", "chemistry"] + list(wf.get("tags") or []),
                kind="competency",
            )
        )
    return out


def _load_city_entries() -> List[CatalogEntry]:
    from mini_marie.zaha.twa_city.workflow_engine import discover_workflow_catalog

    out: List[CatalogEntry] = []
    for name, meta in discover_workflow_catalog().items():
        out.append(
            CatalogEntry(
                id=str(meta.get("id") or name),
                question=str(meta.get("description") or meta.get("label") or name),
                domain="city",
                mcp_servers=["twa-city"],
                workflow_id=str(name),
                tags=["workflow", "city"],
                kind="competency",
            )
        )
    return out


def _load_sg_entries() -> List[CatalogEntry]:
    path = _repo_root() / "mini_marie" / "zaha" / "sg_old" / "competency_questions.json"
    items = _read_json(path) or []
    out: List[CatalogEntry] = []
    for item in items:
        out.append(
            CatalogEntry(
                id=str(item.get("id", "")),
                question=str(item.get("question", "")),
                domain=str(item.get("domain", "sg")),
                mcp_servers=list(item.get("mcp_servers") or ["sg-old"]),
                tags=["competency", "sg", "zaha"] + list(item.get("tags") or []),
                kind="competency",
            )
        )
    return out


def _load_marie_form_entries() -> List[CatalogEntry]:
    """Advanced-search / explorer phrasing for Marie form-style queries (routing hints)."""
    items = [
        (
            "form_mq34_aen",
            "List all zeolitic materials recorded for framework code AEN",
            "chemistry",
            ["chemistry-ontozeolite"],
            "mq34_framework_aen",
            ["form_search", "zeolite", "framework"],
        ),
        (
            "form_mq43_h2s",
            "What are zeolitic materials that take H2S as guest species?",
            "chemistry",
            ["chemistry-ontozeolite"],
            "mq43_h2s_guest",
            ["form_search", "zeolite", "guest"],
        ),
        (
            "form_mq41_area_volume",
            "Show me all zeolites with accessible area per cell greater than 500 and occupiable volume per cell less than 200",
            "chemistry",
            ["chemistry-ontozeolite"],
            "mq41_zeolite_area_volume",
            ["form_search", "zeolite", "property"],
        ),
        (
            "form_mq40_triclinic",
            "Find zeolitic materials with triclinic lattice system",
            "chemistry",
            ["chemistry-ontozeolite"],
            None,
            ["form_search", "zeolite", "lattice"],
        ),
        (
            "form_mq03_formula",
            "Find chemical species with formula C6H8O6",
            "chemistry",
            ["chemistry-ontospecies"],
            "mq03_formula_c6h8o6",
            ["form_search", "species", "formula"],
        ),
        (
            "form_species_smiles_water",
            "Search species where SMILES is O",
            "chemistry",
            ["chemistry-ontospecies"],
            None,
            ["form_search", "species", "smiles"],
        ),
        (
            "form_species_hbond",
            "Species with hydrogen bond donor count at least 2 and acceptor count at least 2",
            "chemistry",
            ["chemistry-ontospecies"],
            "mq01_ethylene_glycol_hbond",
            ["form_search", "species", "physprop"],
        ),
    ]
    return [
        CatalogEntry(
            id=eid,
            question=q,
            domain=domain,
            mcp_servers=servers,
            workflow_id=workflow_id,
            tags=["form_search", "marie"] + tags,
            kind="form",
        )
        for eid, q, domain, servers, workflow_id, tags in items
    ]


def _load_marie_mq_entries() -> List[CatalogEntry]:
    """Marie demo questions without chemistry workflow JSON (routing hints only)."""
    extras = [
        (
            "MQ37",
            "Retrieve unit cell information of zeolitic material |Na20|[Al20Si76O192]",
            "chemistry",
            ["chemistry-ontozeolite"],
        ),
        (
            "MQ49",
            "Which MOPs have an outer diameter greater than 70 Angstrom?",
            "mops",
            ["twa-mops", "chemistry-ontomops"],
        ),
        (
            "MQ50",
            "What MOPs are based on the CBU [(C6H3)O(CH2)13CH3(CO2)2] and what are their inner sphere diameters?",
            "mops",
            ["twa-mops", "chemistry-ontomops"],
        ),
        (
            "MQ54",
            "What assembly models are representative of icosahedral geometry?",
            "mops",
            ["twa-mops", "chemistry-ontomops"],
        ),
    ]
    return [
        CatalogEntry(
            id=eid,
            question=q,
            domain=domain,
            mcp_servers=servers,
            tags=["competency", "marie", "mq"],
            kind="competency",
        )
        for eid, q, domain, servers in extras
    ]


def _load_cross_kg_entries() -> List[CatalogEntry]:
    path = _repo_root() / "mini_marie" / "cross_kg_competency" / "questions.json"
    items = _read_json(path) or []
    domain_to_mcp = {
        "mof": "mof-twa",
        "city": "twa-city",
        "mops": "twa-mops",
        "catalog": "kg-catalog",
        "sg_ontop": "sg-old",
        "sg_carpark": "sg-old",
        "sg_kb": "sg-old",
        "sg_plot": "sg-old",
        "sg_company": "sg-old",
    }
    out: List[CatalogEntry] = []
    for item in items:
        domains = item.get("domains") or []
        servers: List[str] = []
        for d in domains:
            mcp = domain_to_mcp.get(str(d))
            if mcp and mcp not in servers:
                servers.append(mcp)
        if "catalog" in domains and "kg-catalog" not in servers:
            servers.insert(0, "kg-catalog")
        if not servers:
            servers = ["kg-catalog"]
        out.append(
            CatalogEntry(
                id=str(item.get("id", "")),
                question=str(item.get("question", "")),
                domain="cross_kg",
                mcp_servers=servers[:3],
                tags=["cross_kg"] + [str(d) for d in domains],
                kind="competency",
            )
        )
    return out


def _example_questions() -> List[CatalogEntry]:
    examples = [
        ("ex_mops_vmop17", "What is the synthesis route for VMOP-17?", "mops", ["twa-mops"], None),
        ("ex_mof_co2", "What is the average CO2 uptake for Tobassco MOFs?", "mof", ["mof-twa"], None),
        (
            "ex_city_bremen_14",
            "14 tallest building in bremen and where are they? what kind of type",
            "city",
            ["twa-city"],
            None,
        ),
        (
            "ex_city_bremen",
            "List the tallest non-domestic buildings in Bremen.",
            "city",
            ["twa-city"],
            None,
        ),
        (
            "ex_city_kl",
            "What are the tallest buildings in Kaiserslautern?",
            "city",
            ["twa-city"],
            None,
        ),
        (
            "ex_species_formula",
            "Find chemical species with formula C6H8O6.",
            "chemistry",
            ["chemistry-ontospecies"],
            "mq03_formula_c6h8o6",
        ),
        (
            "ex_zeolite_aen",
            "Which zeolite has framework code AEN?",
            "chemistry",
            ["chemistry-ontozeolite"],
            "mq34_framework_aen",
        ),
        (
            "ex_zeolite_guest_h2s",
            "Find zeolitic materials that take H2S as guest species.",
            "chemistry",
            ["chemistry-ontozeolite"],
            None,
        ),
        (
            "ex_zeolite_lattice_triclinic",
            "Find zeolitic materials with triclinic lattice system.",
            "chemistry",
            ["chemistry-ontozeolite"],
            None,
        ),
        (
            "ex_species_hbond",
            "How many hydrogen bonds can an ethylene glycol molecule accept and donate?",
            "chemistry",
            ["chemistry-ontospecies"],
            "mq01_ethylene_glycol_hbond",
        ),
        ("ex_sg_emissions", "How many emission individuals are in the Singapore kb namespace?", "sg_kb", ["sg-old"], None),
        ("ex_catalog", "Which KG domains are available in mini_marie?", "catalog", ["kg-catalog"], None),
    ]
    return [
        CatalogEntry(
            id=eid,
            question=q,
            domain=domain,
            mcp_servers=servers,
            workflow_id=workflow_id,
            tags=["example"],
            kind="example",
        )
        for eid, q, domain, servers, workflow_id in examples
    ]


def _load_marie_nl_questions() -> List[CatalogEntry]:
    """Natural-language Marie homepage questions from marie_competency_questions.md."""
    path = (
        _repo_root()
        / "mini_marie"
        / "docs"
        / "resources"
        / "marie"
        / "marie_competency_questions.md"
    )
    if not path.exists():
        return []

    wf_by_mq: Dict[int, str] = {}
    wf_tags_by_mq: Dict[int, List[str]] = {}
    suite_path = (
        _repo_root() / "mini_marie" / "marie" / "chemistry" / "workflows" / "competency_suite.json"
    )
    for wf in (_read_json(suite_path) or {}).get("workflows") or []:
        wid = str(wf.get("id") or "")
        m = re.match(r"mq(\d+)_", wid.lower())
        if m:
            mq_num = int(m.group(1))
            wf_by_mq[mq_num] = wid
            wf_tags_by_mq[mq_num] = list(wf.get("tags") or [])

    ns_re = re.compile(r"\*\*Namespace:\*\* `(\w+)`")
    mq_re = re.compile(r"^### MQ(\d+)\s*$")
    current_ns = "ontospecies"
    pending_mq: Optional[int] = None
    out: List[CatalogEntry] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        ns_match = ns_re.search(line)
        if ns_match:
            current_ns = ns_match.group(1)
            continue
        mq_match = mq_re.match(line.strip())
        if mq_match:
            pending_mq = int(mq_match.group(1))
            continue
        if pending_mq is None:
            continue
        question = line.strip()
        if not question or question.startswith("-") or question.startswith("#"):
            continue
        mq_num = pending_mq
        pending_mq = None
        mcp = CHEMISTRY_NS_TO_MCP.get(current_ns, "chemistry-ontospecies")
        servers = [mcp]
        if current_ns == "ontomops":
            servers.append("twa-mops")
        extra_tags = wf_tags_by_mq.get(mq_num, [])
        out.append(
            CatalogEntry(
                id=f"MQ{mq_num}",
                question=question,
                domain="chemistry",
                mcp_servers=servers,
                workflow_id=wf_by_mq.get(mq_num),
                tags=["competency", "chemistry", "marie", "mq", f"mq{mq_num}"] + extra_tags,
                kind="competency",
            )
        )
    return out


@lru_cache(maxsize=1)
def load_catalog() -> List[CatalogEntry]:
    entries: List[CatalogEntry] = []
    entries.extend(_load_mof_entries())
    entries.extend(_load_chemistry_entries())
    entries.extend(_load_marie_nl_questions())
    entries.extend(_load_marie_form_entries())
    entries.extend(_load_sg_entries())
    entries.extend(_load_marie_mq_entries())
    entries.extend(_load_city_entries())
    entries.extend(_load_cross_kg_entries())
    entries.extend(_example_questions())
    return entries


def list_domains() -> List[str]:
    domains = sorted({e.domain for e in load_catalog()})
    return ["all"] + domains


def filter_catalog(
    *,
    domain: Optional[str] = None,
    kind: Optional[str] = None,
    search: Optional[str] = None,
) -> List[CatalogEntry]:
    items = load_catalog()
    if domain and domain != "all":
        items = [e for e in items if e.domain == domain]
    if kind:
        items = [e for e in items if e.kind == kind]
    if search:
        needle = search.strip().lower()
        items = [
            e
            for e in items
            if needle in e.question.lower()
            or needle in e.id.lower()
            or any(needle in t for t in e.tags)
        ]
    return items


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _mq_prefix(text: str) -> Optional[str]:
    m = re.search(r"\bmq(\d+)\b", text, re.I)
    return f"mq{m.group(1)}" if m else None


def match_catalog_exact(question: str) -> Optional[CatalogEntry]:
    """Exact catalog match only (id, normalized question, MQ prefix) — no fuzzy token overlap."""
    qn = _normalize(question)
    if not qn:
        return None

    for entry in load_catalog():
        if qn == _normalize(entry.question) or qn == _normalize(entry.id):
            return entry

    mq = _mq_prefix(question)
    if mq:
        for entry in load_catalog():
            eid = entry.id.lower()
            eq = _normalize(entry.question)
            if eid.startswith(f"{mq}_") or eid == mq:
                return entry
            if eq.startswith(f"{mq} —") or eq.startswith(f"{mq} -"):
                return entry

    for entry in load_catalog():
        if _normalize(entry.id) == qn:
            return entry
    return None


def catalog_entries_by_ids(entry_ids: Sequence[str]) -> List[CatalogEntry]:
    out: List[CatalogEntry] = []
    seen = set()
    for raw in entry_ids:
        eid = str(raw).strip()
        if not eid or eid in seen:
            continue
        entry = catalog_entry_by_id(eid)
        if entry:
            seen.add(eid)
            out.append(entry)
    return out


def catalog_index_for_llm() -> str:
    lines: List[str] = []
    for entry in load_catalog():
        q = entry.question.replace("\n", " ").strip()
        if len(q) > 120:
            q = q[:117] + "..."
        lines.append(f"{entry.id}\t{entry.domain}\t{q}")
    return "\n".join(lines)


def match_catalog(question: str) -> Optional[CatalogEntry]:
    """Backward-compatible alias for exact catalog lookup (no fuzzy matching)."""
    return match_catalog_exact(question)


def catalog_entry_by_id(entry_id: str) -> Optional[CatalogEntry]:
    for entry in load_catalog():
        if entry.id == entry_id:
            return entry
    return None
