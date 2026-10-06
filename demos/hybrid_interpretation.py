"""Combine knowledge-graph results with web search via LLM (Marie dual-source QA)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from demos.marie_format import build_marie_narrative
from demos.twa_format import _data_preview_for_llm, _looks_like_raw_json, _llm_narrative_enabled, _narrative_model_name
from mini_marie.web_search.service import WebSearchResult

_FALSE = frozenset({"0", "false", "no", "off"})


def marie_extended_answers() -> bool:
    return os.environ.get("MARIE_EXTENDED_ANSWERS", "1").strip().lower() not in _FALSE


def _hybrid_max_tokens() -> int:
    return int(os.environ.get("MARIE_HYBRID_MAX_TOKENS", "12000"))


def _preview_row_limit() -> int:
    return int(os.environ.get("MARIE_HYBRID_TABLE_ROWS", "40"))


def show_web_sources_table() -> bool:
    """Raw web hits table in the UI (optional; narrative already cites links)."""
    explicit = os.environ.get("MARIE_SHOW_WEB_SOURCES_TABLE", "").strip().lower()
    if explicit in _FALSE:
        return False
    if explicit in ("1", "true", "yes", "on"):
        return True
    # Default off — extended Interpretation includes a Sources section.
    return False


def web_sources_table(web: WebSearchResult) -> Optional[Dict[str, Any]]:
    if not web.sources:
        return None
    rows = [
        {
            "title": s.get("title") or "",
            "url": s.get("url") or "",
            "snippet": s.get("snippet") or "",
        }
        for s in web.sources
    ]
    return {
        "type": "table",
        "title": "Web sources",
        "table_index": 99,
        "columns": ["title", "url", "snippet"],
        "display_columns": ["title", "url", "snippet"],
        "data": rows,
        "row_count": len(rows),
    }


def _web_preview(web: WebSearchResult) -> str:
    snip_cap = 800 if marie_extended_answers() else 240
    parts = [web.summary.strip()] if web.summary else []
    limit = 12 if marie_extended_answers() else 6
    for s in web.sources[:limit]:
        line = f"- [{s.get('title') or 'Source'}]({s.get('url')})"
        snip = (s.get("snippet") or "").strip()
        if snip:
            line += f": {snip[:snip_cap]}"
        parts.append(line)
    return "\n".join(parts).strip()


def _tool_trace_preview(tool_outputs: List[Dict[str, str]], *, cap: int = 12000) -> str:
    chunks: List[str] = []
    for item in tool_outputs[-5:]:
        name = item.get("name") or "tool"
        content = (item.get("content") or "").strip()
        if not content:
            continue
        chunks.append(f"### {name}\n{content[:2500]}")
    text = "\n\n".join(chunks)
    return text[:cap]


def _dual_source_system_prompt() -> str:
    if marie_extended_answers():
        return (
            "You write a long-form Markdown research brief for Marie (The World Avatar science demo). "
            "Merge TWO evidence channels: (1) knowledge-graph agent output and tables, "
            "(2) public web search. "
            "Be exhaustive: use every relevant fact, number, name, and citation from the inputs. "
            "Do not invent data. Prefer KG values for TWA corpus statistics; enrich with web for "
            "definitions, applications, literature context, and recent developments. "
            "Structure with clear headings, e.g. Overview, Key properties, KG findings, "
            "Applications and uses, Web literature, Limitations or gaps, Sources. "
            "Use **bold** for metrics; use bullet lists and short paragraphs; include markdown links. "
            "Target length: roughly 400–900 words when enough evidence exists; never pad with fluff."
        )
    return (
        "You write a single coherent Markdown answer for a science demo (Marie / The World Avatar). "
        "Combine TWO evidence channels: (1) structured knowledge-graph tables and agent notes, "
        "(2) public web search summary and links. "
        "Prefer KG numbers for TWA-specific facts when both agree; use the web for context, "
        "recent literature, or when the KG is empty or weak. "
        "Never paste raw JSON or full IRIs. Use **bold** for key figures. "
        "End with a short 'Sources' bullet list (KG tools + web links)."
    )


def _dual_source_user_prompt(
    question: str,
    *,
    online_answer: str,
    preview: str,
    web_text: str,
    tool_trace: str,
) -> str:
    kg_cap = 8000 if marie_extended_answers() else 2000
    web_cap = 12000 if marie_extended_answers() else 4000
    length_hint = (
        "Write a comprehensive unified answer (multi-section, 400–900 words when evidence allows)."
        if marie_extended_answers()
        else "Write one unified answer (3–10 sentences or bullets)."
    )
    return f"""Question:
{question.strip()}

Knowledge graph agent answer:
{online_answer.strip()[:kg_cap]}

KG tool trace (may include workflow steps and samples):
{tool_trace or '(none)'}

KG table preview:
{preview or '(no tabular rows)'}

Web search summary and links:
{web_text[:web_cap] or '(empty)'}

{length_hint} Do not invent numbers not present above."""


async def synthesize_marie_dual_source(
    question: str,
    *,
    kgqa: Dict[str, Any],
    marie_data: List[Dict[str, Any]],
    display_answer: Any,
    tool_outputs: List[Dict[str, str]],
    web: Optional[WebSearchResult],
) -> str:
    """Merge KG + web into one Markdown answer; fall back to KG-only narrative."""
    kg_only = build_marie_narrative(
        question,
        online_answer=display_answer,
        tool_outputs=tool_outputs,
        data=marie_data,
    )
    if not web or (not web.summary and not web.sources):
        if web and web.error:
            return kg_only + f"\n\n*(Web search unavailable: {web.error})*"
        return kg_only

    web_text = _web_preview(web)
    if not _llm_narrative_enabled():
        return (
            f"{kg_only}\n\n---\n\n**From the web:**\n\n{web_text or '_No web summary._'}"
        )

    from langchain_core.messages import HumanMessage, SystemMessage
    from models.LLMCreator import LLMCreator
    from models.ModelConfig import ModelConfig

    from demos.twa_adapter import _display_answer

    online_answer = _display_answer(kgqa) or kgqa.get("online_answer") or ""
    if _looks_like_raw_json(str(online_answer)):
        online_answer = str(display_answer or "")

    preview = _data_preview_for_llm(marie_data, max_rows=_preview_row_limit())
    tool_trace = _tool_trace_preview(tool_outputs)
    system = _dual_source_system_prompt()
    user = _dual_source_user_prompt(
        question,
        online_answer=str(online_answer),
        preview=preview,
        web_text=web_text,
        tool_trace=tool_trace,
    )

    try:
        model = _narrative_model_name()
        model_config = ModelConfig(
            max_tokens=_hybrid_max_tokens(),
            temperature=0.25 if marie_extended_answers() else 0.2,
        )
        llm = LLMCreator(
            model=model,
            remote_model=True,
            model_config=model_config,
        ).setup_llm()
        result = await llm.ainvoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        text = (result.content if hasattr(result, "content") else str(result)).strip()
        min_len = 200 if marie_extended_answers() else 40
        if text and len(text) >= min_len and not _looks_like_raw_json(text):
            return text
        if text and len(text) >= 40 and not marie_extended_answers():
            return text
    except Exception:
        pass

    if marie_extended_answers():
        return (
            f"{kg_only}\n\n---\n\n## From the knowledge graph\n\n{kg_only}\n\n"
            f"---\n\n## From the web\n\n{web_text or '_No web summary._'}"
        )
    return (
        f"{kg_only}\n\n---\n\n**From the web:**\n\n{web_text or '_No web summary._'}"
    )
