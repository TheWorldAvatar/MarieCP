"""Shape KGQA output for the Marie chemistry demo UI (tables + readable chat)."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

# Tools that discover infrastructure — hide from Marie "Retrieved data" and chat narrative.
_META_TOOLS = frozenset(
    {
        "list_kg_domains",
        "kg_cache_status",
        "list_workflows",
        "describe_kg_domain",
        "run_competency_online",
        "run_workflow_online",
    }
)

_COMPETENCY_KV_PREFIXES = frozenset(
    {
        "status",
        "mode",
        "workflow_id",
        "title",
        "elapsed_ms",
        "recording_path",
        "answer",
        "next_step",
        "step",
        "sample_results",
    }
)

_TOOL_TITLES = {
    "list_kg_domains": "Knowledge graph domains",
    "kg_cache_status": "Local cache status",
    "search_species_names": "Species search results",
    "lookup_individuals": "Species lookup results",
    "query_species_pka": "pKa values",
    "search_species_uses": "Species uses",
    "run_competency_online": "Competency workflow results",
    "run_workflow_online": "Workflow results",
}

_FAILURE_RE = re.compile(
    r"(^sorry[, ]|need more steps|unable to (find|process)|could not find)",
    re.IGNORECASE,
)


def extract_competency_sample_tsv(content: str) -> Optional[str]:
    """Pull sample_results TSV from competency MCP envelope output."""
    if "sample_results" not in content:
        return None
    tail = content.split("sample_results", 1)[1]
    cleaned = re.sub(r"^--- step \d+ ---\s*", "", tail, flags=re.M)
    cleaned = cleaned.split("next_step")[0].strip()
    return cleaned or None


def _is_competency_envelope_table(columns: List[str], rows: List[Dict[str, Any]]) -> bool:
    """Detect mis-parsed competency status/mode key-value lines as a table."""
    if set(columns) == {"status", "empty"}:
        return True
    if len(columns) == 2 and columns[0] in _COMPETENCY_KV_PREFIXES:
        return True
    if rows and all(set(row.keys()) <= {"status", "empty"} for row in rows):
        return True
    return False


def _tool_title(name: str) -> str:
    return _TOOL_TITLES.get(name, name.replace("_", " ").title())


def _is_weak_answer(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped or len(stripped) < 20:
        return True
    if stripped in ("None", "[]", "null"):
        return True
    return bool(_FAILURE_RE.search(stripped))


def parse_tabular_content(content: str) -> Optional[Tuple[List[str], List[Dict[str, Any]]]]:
    """Parse TSV or JSON array tool output into columns + row dicts."""
    text = (content or "").strip()
    if not text:
        return None

    if text.startswith("[") or text.startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            columns = list(parsed[0].keys())
            return columns, parsed
        if isinstance(parsed, dict):
            for key in ("rows", "data", "bindings", "results"):
                rows = parsed.get(key)
                if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                    columns = list(rows[0].keys())
                    return columns, rows

    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 2 and "\t" in lines[0]:
        headers = [h.strip() for h in lines[0].split("\t")]
        if len(headers) < 2:
            return None
        rows: List[Dict[str, Any]] = []
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) != len(headers):
                continue
            row = {headers[i]: parts[i].strip() for i in range(len(headers))}
            if any(v for v in row.values()):
                rows.append(row)
        if rows:
            return headers, rows

    return None


def marie_table(columns: List[str], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"type": "table", "columns": columns, "data": rows}


def tables_from_tool_outputs(
    tool_outputs: List[Dict[str, str]],
    *,
    skip_meta: bool = False,
) -> List[Dict[str, Any]]:
    tables: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in tool_outputs:
        name = (item.get("name") or "tool").strip()
        if skip_meta and name in _META_TOOLS:
            continue
        content = item.get("content") or ""
        if name in {"run_competency_online", "run_workflow_online"}:
            content = extract_competency_sample_tsv(content) or ""
        parsed = parse_tabular_content(content)
        if not parsed:
            continue
        columns, rows = parsed
        if _is_competency_envelope_table(columns, rows):
            continue
        if not rows:
            continue
        key = f"{name}:{columns[0]}:{len(rows)}"
        if key in seen:
            continue
        seen.add(key)
        tables.append(marie_table(columns, rows[:500]))
    return tables


def tables_from_zaha_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in items:
        if item.get("type") != "table":
            continue
        cols = item.get("vars") or item.get("columns") or []
        rows = item.get("bindings") or item.get("data") or []
        if cols and rows:
            out.append(marie_table(list(cols), rows))
    return out


def build_marie_data(
    *,
    offline_tables: List[Dict[str, Any]],
    tool_outputs: List[Dict[str, str]],
    online_answer: Any,
) -> List[Dict[str, Any]]:
    """Prefer offline/workflow rows, then parsed tool tables, then a summary row."""
    data: List[Dict[str, Any]] = []
    data.extend(offline_tables)

    if not data:
        data.extend(tables_from_tool_outputs(tool_outputs, skip_meta=True))

    if not data:
        if isinstance(online_answer, list) and online_answer and isinstance(online_answer[0], dict):
            cols = list(online_answer[0].keys())
            data.append(marie_table(cols, online_answer[:500]))
        elif isinstance(online_answer, str) and online_answer.strip() and not _is_weak_answer(online_answer):
            data.append(marie_table(["Summary"], [{"Summary": online_answer.strip()}]))

    meta_only = bool(tool_outputs) and not any(
        (item.get("name") or "") not in _META_TOOLS and (item.get("content") or "").strip()
        for item in tool_outputs
    )
    if not data and isinstance(online_answer, str) and online_answer.strip():
        if not (meta_only and _is_weak_answer(online_answer)):
            data.append(marie_table(["Summary"], [{"Summary": online_answer.strip()}]))

    return data


def build_marie_metadata(
    question: str,
    kgqa: Dict[str, Any],
    tool_outputs: List[Dict[str, str]],
) -> Dict[str, Any]:
    route = kgqa.get("route") or {}
    servers = route.get("mcp_servers") or []
    properties: List[List[Any]] = []
    for srv in servers:
        properties.append([srv, {"label": srv, "comment": route.get("reason") or ""}])

    executed = [
        name for name in (item.get("name") or "" for item in tool_outputs) if name
    ]
    entity_bindings = {f"step_{i}": [name] for i, name in enumerate(executed, start=1)}

    return {
        "rewritten_question": question,
        "translation_context": {"properties": properties, "examples": []},
        "data_request": {
            "var2cls": {},
            "entity_bindings": entity_bindings,
            "req_form": None,
        },
        "linked_variables": {},
    }


def _narrative_is_question_echo(text: str, question: str) -> bool:
    stripped = (text or "").strip()
    q = question.strip()
    if not stripped or not q:
        return False
    if stripped == q or stripped == f"**Question:** {q}":
        return True
    return stripped.startswith("**Question:**") and q in stripped and len(stripped) < len(q) + 40


def build_marie_narrative(
    question: str,
    *,
    online_answer: Any,
    tool_outputs: List[Dict[str, str]],
    data: List[Dict[str, Any]],
) -> str:
    """Human-readable chat stream — never dump raw tool TSV."""
    summary_from_data = ""
    for item in data:
        if item.get("type") != "table":
            continue
        cols = item.get("columns") or []
        rows = item.get("data") or []
        if cols == ["Summary"] and rows:
            summary_from_data = str(rows[0].get("Summary", "")).strip()
            if summary_from_data and not _is_weak_answer(summary_from_data):
                return summary_from_data

    if isinstance(online_answer, str) and not _is_weak_answer(online_answer):
        text = online_answer.strip()
        if not _narrative_is_question_echo(text, question):
            return text

    has_substantive_tools = any(
        (item.get("name") or "") not in _META_TOOLS and (item.get("content") or "").strip()
        for item in tool_outputs
    )
    only_meta = bool(tool_outputs) and not has_substantive_tools

    parts: List[str] = []

    substantive = [
        item
        for item in tool_outputs
        if (item.get("name") or "") not in _META_TOOLS and (item.get("content") or "").strip()
    ]
    for item in substantive[-3:]:
        name = item.get("name") or "tool"
        content = (item.get("content") or "").strip()
        parsed = parse_tabular_content(content)
        title = _tool_title(name)
        if parsed:
            _cols, rows = parsed
            parts.append(f"**{title}** — {len(rows)} row(s)")
            for row in rows[:5]:
                preview = ", ".join(f"{k}: {v}" for k, v in row.items() if v)[:200]
                if preview:
                    parts.append(f"- {preview}")
            parts.append("")
        elif not _FAILURE_RE.search(content) and len(content) < 800:
            parts.append(f"**{title}:** {content}")
            parts.append("")

    if data:
        total_rows = sum(len(t.get("data") or []) for t in data if t.get("type") == "table")
        substantive_table = any(
            (t.get("columns") or []) not in (["answer"], ["Summary"]) for t in data if t.get("type") == "table"
        )
        if total_rows and substantive_table:
            parts.append(
                f"Retrieved **{total_rows}** row(s) in **{len(data)}** table(s). "
                "Expand **Retrieved data** below for details."
            )
        elif summary_from_data:
            parts.append(summary_from_data)
        elif isinstance(online_answer, str) and not _is_weak_answer(online_answer):
            if not _narrative_is_question_echo(online_answer, question):
                parts.append(online_answer.strip())
    elif only_meta:
        parts.append(
            "The agent only checked infrastructure (available knowledge graphs and cache files) "
            "and did not retrieve chemistry data for your question. "
            "Try one of the **Example Questions**, or ask about a species by name, formula, or SMILES."
        )
    elif isinstance(online_answer, str) and online_answer.strip():
        if not _narrative_is_question_echo(online_answer, question):
            parts.append(online_answer.strip())
    elif summary_from_data:
        parts.append(summary_from_data)
    else:
        parts.append(
            "No structured results were returned. "
            "The knowledge graph cache may need warming, or the agent may need more steps."
        )

    text = "\n".join(parts).strip()
    if _narrative_is_question_echo(text, question) or not text:
        return (
            "No matching records were found in the local chemistry cache for this question. "
            "The query completed successfully but the result set is empty."
        )
    return text
