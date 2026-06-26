"""LLM-based KGQA routing — replaces keyword/token catalog matching."""

from __future__ import annotations

import os
from typing import List, Optional, Sequence

from pydantic import BaseModel, Field

from mini_marie.kgqa.mcp_router import (
    MAX_MCP_SERVERS,
    RouteResult,
    _dedupe_keep_order,
)
from mini_marie.kgqa.question_catalog import (
    CatalogEntry,
    catalog_entries_by_ids,
    catalog_index_for_llm,
    match_catalog_exact,
)

KNOWN_DOMAINS = frozenset(
    {"chemistry", "sg", "mof", "city", "mops", "cross_kg", "catalog", "sg_kb"}
)

MCP_ALLOWLIST = frozenset(
    {
        "kg-catalog",
        "sg-old",
        "twa-city",
        "twa-mops",
        "mof-twa",
        "chemistry-ontospecies",
        "chemistry-ontokin",
        "chemistry-ontocompchem",
        "chemistry-ontozeolite",
        "chemistry-ontomops",
        "chemistry-ontoprovenance",
        "chemistry-ontopesscan",
    }
)


class RoutingDecision(BaseModel):
    """Structured routing judgement from the LLM."""

    domains: List[str] = Field(
        description=(
            "One or more domain labels. Use multiple when the question spans knowledge graphs "
            "(e.g. ['chemistry', 'sg']). Valid labels: chemistry, sg, mof, city, mops, cross_kg."
        )
    )
    mcp_servers: List[str] = Field(
        description="Up to 3 MCP server names to load for answering.",
        max_length=MAX_MCP_SERVERS,
    )
    catalog_entry_ids: List[str] = Field(
        default_factory=list,
        description=(
            "Zero or more catalog entry ids that best match sub-parts of the question. "
            "For cross-domain questions include ids from each relevant domain."
        ),
    )
    reason: str = Field(description="Brief explanation of the routing decision.")


def _llm_routing_enabled() -> bool:
    if os.environ.get("KGQA_ROUTE_LLM", "1").strip().lower() in {"0", "false", "no"}:
        return False
    return bool(os.environ.get("REMOTE_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def _route_model_name() -> str:
    return os.environ.get("KGQA_ROUTE_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def _normalize_domains(domains: Sequence[str]) -> List[str]:
    out: List[str] = []
    for raw in domains:
        d = raw.strip().lower().replace("-", "_")
        if d in {"singapore", "zaha", "urban"}:
            d = "sg"
        if d in KNOWN_DOMAINS and d not in out:
            out.append(d)
    return out


def _primary_domain(domains: List[str]) -> str:
    if len(domains) > 1:
        return "cross_kg"
    if domains:
        return domains[0]
    return "catalog"


def _merge_servers(
    llm_servers: Sequence[str],
    entries: Sequence[CatalogEntry],
) -> List[str]:
    merged: List[str] = []
    for name in llm_servers:
        if name in MCP_ALLOWLIST and name not in merged:
            merged.append(name)
    for entry in entries:
        for name in entry.mcp_servers:
            if name in MCP_ALLOWLIST and name not in merged:
                merged.append(name)
    if "kg-catalog" not in merged and len(merged) < MAX_MCP_SERVERS:
        merged.append("kg-catalog")
    return merged[:MAX_MCP_SERVERS]


def _route_from_decision(
    question: str,
    decision: RoutingDecision,
    *,
    reason_prefix: str = "llm",
) -> RouteResult:
    domains = _normalize_domains(decision.domains)
    entries = catalog_entries_by_ids(decision.catalog_entry_ids)
    if not entries:
        exact = match_catalog_exact(question)
        if exact:
            entries = [exact]
    servers = _merge_servers(decision.mcp_servers, entries)
    if not servers:
        servers = ["kg-catalog"]
    primary = entries[0] if entries else None
    domain = _primary_domain(domains)
    if domain != "cross_kg" and primary and primary.domain in KNOWN_DOMAINS:
        domain = primary.domain if len(domains) <= 1 else "cross_kg"
    if len(domains) > 1:
        domain = "cross_kg"
    return RouteResult(
        mcp_servers=servers,
        catalog_entry=primary,
        catalog_entries=list(entries),
        domain=domain,
        domains=domains or ([domain] if domain != "catalog" else []),
        reason=f"{reason_prefix}: {decision.reason}".strip(),
    )


def _fallback_route(question: str, *, reason: str) -> RouteResult:
    """Exact catalog id/question match only — no fuzzy keyword routing."""
    exact = match_catalog_exact(question)
    if exact:
        servers = _dedupe_keep_order(list(exact.mcp_servers) + ["kg-catalog"])[:MAX_MCP_SERVERS]
        return RouteResult(
            mcp_servers=servers,
            catalog_entry=exact,
            catalog_entries=[exact],
            domain=exact.domain,
            domains=[exact.domain],
            reason=f"{reason}: exact catalog match ({exact.id})",
        )
    return RouteResult(
        mcp_servers=["kg-catalog"],
        domain="catalog",
        domains=["catalog"],
        reason=f"{reason}: no LLM API key and no exact catalog match",
    )


async def route_question_llm(
    question: str,
    *,
    model_name: Optional[str] = None,
    qa_domain_hint: Optional[str] = None,
) -> RouteResult:
    """Route a question using LLM judgement (supports multi-label cross-domain)."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from models.LLMCreator import LLMCreator
    from models.ModelConfig import ModelConfig

    exact = match_catalog_exact(question)
    if exact and not _question_has_multiple_intents(question):
        servers = _dedupe_keep_order(list(exact.mcp_servers) + ["kg-catalog"])[:MAX_MCP_SERVERS]
        return RouteResult(
            mcp_servers=servers,
            catalog_entry=exact,
            catalog_entries=[exact],
            domain=exact.domain,
            domains=[exact.domain],
            reason=f"exact catalog match ({exact.id})",
        )

    hint_line = ""
    if qa_domain_hint:
        hint_line = (
            f"\nUI hint (soft, content still wins): qa_domain={qa_domain_hint!r}. "
            "Use only if the question itself is ambiguous."
        )

    system = """You route natural-language questions to The World Avatar knowledge-graph MCP servers.

Rules:
- Judge by question CONTENT, not UI labels.
- Return one OR MORE domain labels when the question spans multiple knowledge graphs.
- Pick catalog_entry_ids for each distinct sub-question when possible (can be multiple).
- mcp_servers: at most 3 names from the allowlist below; always prefer the most specific servers.
- For cross-domain questions include servers from each relevant domain (e.g. chemistry-ontospecies + sg-old).
- Do NOT rely on accidental keyword overlap; reason about intent.

Domain labels: chemistry, sg, mof, city, mops, cross_kg (use cross_kg only when multiple domains apply).

MCP allowlist:
kg-catalog, sg-old, twa-city, twa-mops, mof-twa,
chemistry-ontospecies, chemistry-ontokin, chemistry-ontocompchem, chemistry-ontozeolite,
chemistry-ontomops, chemistry-ontoprovenance, chemistry-ontopesscan
"""

    user = f"""Question:
{question.strip()}
{hint_line}

Catalog index (id | domain | question):
{catalog_index_for_llm()}
"""

    llm = LLMCreator(
        model=model_name or _route_model_name(),
        remote_model=True,
        model_config=ModelConfig(),
        structured_output=True,
        structured_output_schema=RoutingDecision,
    ).setup_llm()

    decision: RoutingDecision = await llm.ainvoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    )
    return _route_from_decision(question, decision)


def _question_has_multiple_intents(question: str) -> bool:
    q = question.lower()
    connectors = (" and ", " also ", "; ", " plus ", " as well as ")
    if not any(c in q for c in connectors):
        return False
    chem_markers = ("species", "formula", "zeolite", "molecular", "inchi", "smiles", "pka", "mop", "c6h")
    sg_markers = ("singapore", "jurong", "carpark", "land plot", "land lot", "building", "gfa", "agricultur")
    return any(m in q for m in chem_markers) and any(m in q for m in sg_markers)


async def route_question_async(
    question: str,
    *,
    model_name: Optional[str] = None,
    qa_domain_hint: Optional[str] = None,
) -> RouteResult:
    """Primary async router: LLM when available, exact catalog match otherwise."""
    if _llm_routing_enabled():
        try:
            return await route_question_llm(
                question,
                model_name=model_name,
                qa_domain_hint=qa_domain_hint,
            )
        except Exception as exc:
            return _fallback_route(question, reason=f"llm routing failed ({exc})")
    return _fallback_route(question, reason="llm disabled")
