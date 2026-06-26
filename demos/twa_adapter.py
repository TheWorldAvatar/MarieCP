"""Adapt mini_marie KGQA results to the TWA Marie/Zaha demo API shape."""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

from mini_marie.kgqa.mcp_router import RouteResult, route_question
from mini_marie.kgqa.orchestrator import run_kgqa_async

from demos.marie_format import (
    _is_weak_answer,
    build_marie_data,
    build_marie_metadata,
    build_marie_narrative,
    parse_tabular_content,
    tables_from_tool_outputs,
    tables_from_zaha_items,
)


def load_offline_payload(path: str) -> Optional[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _table_rows(value: Any) -> List[Dict[str, Any]]:
    """Normalize row lists from offline recordings (full list or slim {_row_count, sample})."""
    if isinstance(value, dict):
        sample = value.get("sample")
        if isinstance(sample, list):
            return [row for row in sample if isinstance(row, dict)]
        return []
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    return []


_PREFERRED_OFFLINE_VARS = (
    "top_building_rows",
    "buildings_with_wkt",
    "location_join_rows",
)


def _sidecar_variable_paths(payload: Dict[str, Any]) -> Dict[str, str]:
    sidecar = payload.get("sidecar") or {}
    out: Dict[str, str] = {}
    for artifact in sidecar.get("artifacts") or []:
        if artifact.get("kind") == "variable" and artifact.get("name") and artifact.get("path"):
            out[str(artifact["name"])] = str(artifact["path"])
    return out


def _rows_from_sidecar(path: str, *, limit: int = 500) -> List[Dict[str, Any]]:
    from mini_marie.zaha.twa_city.workflow_sidecar import iter_ndjson_rows

    p = Path(path)
    if not p.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for item in iter_ndjson_rows(p):
        if isinstance(item, dict):
            rows.append(item)
        if len(rows) >= limit:
            break
    return rows


def _preferred_offline_table(payload: Dict[str, Any]) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
    from mini_marie.row_annotations import stamp_offline_table_rows

    sidecar_vars = _sidecar_variable_paths(payload)
    for var in _PREFERRED_OFFLINE_VARS:
        path = sidecar_vars.get(var)
        if path:
            rows = _rows_from_sidecar(path)
            if rows:
                return var, stamp_offline_table_rows(rows, payload)
    variables = payload.get("variables") or {}
    for var in _PREFERRED_OFFLINE_VARS:
        var_rows = _table_rows(variables.get(var))
        if var_rows:
            return var, stamp_offline_table_rows(var_rows, payload)
    for name, rows in collect_row_tables(payload):
        if name.startswith("var:"):
            var_key = name.split(":", 1)[1].strip()
            if var_key in ("rank_pool", "building_pool", "probe_pool"):
                continue
        if rows:
            return name, rows
    return None


def collect_row_tables(payload: Dict[str, Any]) -> List[Tuple[str, List[Dict[str, Any]]]]:
    tables: List[Tuple[str, List[Dict[str, Any]]]] = []
    answer_rows = _table_rows(payload.get("answer"))
    if answer_rows:
        tables.append(("answer", answer_rows))
    for step in payload.get("call_trace") or []:
        rows = _table_rows(step.get("rows"))
        if not rows:
            continue
        label = step.get("tool") or step.get("join") or step.get("name") or f"step_{step.get('step')}"
        tables.append((f"step: {label}", rows))
    variables = payload.get("variables") or {}
    for key, val in variables.items():
        var_rows = _table_rows(val)
        if var_rows:
            tables.append((f"var: {key}", var_rows))
    return tables


_MARIE_SESSIONS: Dict[str, Dict[str, Any]] = {}

_DEFAULT_OFFLINE_CAP = 500_000


def _demo_auto_offline() -> bool:
    """Match core KGQA default: replay full cache when a recording exists."""
    return os.environ.get("DEMO_AUTO_OFFLINE", "true").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _demo_force_refresh() -> bool:
    """Bypass SPARQL/tool result cache so each question runs a fresh online probe."""
    return os.environ.get("DEMO_FORCE_REFRESH", "true").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _replay_offline_if_enabled(
    recording_path: Optional[str],
    *,
    workflow_id: Optional[str] = None,
    offline_cap: int = _DEFAULT_OFFLINE_CAP,
) -> Optional[Dict[str, Any]]:
    if not recording_path or not _demo_auto_offline():
        return None
    from mini_marie.kgqa.offline_runner import replay_offline

    return replay_offline(
        recording_path,
        workflow_id=workflow_id,
        offline_cap=offline_cap,
    )


def _replay_offline_batch_if_enabled(
    recording_paths: List[str],
    *,
    recordings: Optional[List[Dict[str, Any]]] = None,
    workflow_id: Optional[str] = None,
    offline_cap: int = _DEFAULT_OFFLINE_CAP,
) -> Optional[Dict[str, Any]]:
    paths = [p for p in recording_paths if p]
    if not paths or not _demo_auto_offline():
        return None
    from mini_marie.kgqa.offline_runner import replay_offline, replay_offline_batch

    if len(paths) == 1:
        wf_id = workflow_id
        if recordings and recordings[0].get("workflow_id"):
            wf_id = recordings[0]["workflow_id"]
        return replay_offline(paths[0], workflow_id=wf_id, offline_cap=offline_cap)

    workflow_ids = [r.get("workflow_id") for r in (recordings or [])]
    while len(workflow_ids) < len(paths):
        workflow_ids.append(workflow_id)
    return replay_offline_batch(paths, workflow_ids=workflow_ids, offline_cap=offline_cap)


def _competency_envelope_from_metadata(metadata: Dict[str, Any]) -> str:
    """Extract run_competency_online TSV from agent metadata."""
    env = (metadata.get("competency_envelope") or "").strip()
    if env:
        return env
    for item in (metadata.get("tool_activity") or {}).get("tool_outputs") or []:
        if (item.get("name") or "") == "run_competency_online":
            content = (item.get("content") or "").strip()
            if content:
                return content
    return ""


def _is_blank_answer_value(answer: Any) -> bool:
    if answer is None:
        return True
    if isinstance(answer, list):
        return len(answer) == 0
    if isinstance(answer, str):
        stripped = answer.strip()
        return not stripped or stripped in ("[]", "None", "null")
    return False


def _display_answer(kgqa: Dict[str, Any]) -> Any:
    """Prefer offline replay answer for UI when available."""
    offline = kgqa.get("offline") or {}
    if offline.get("status") == "error" and not offline.get("skipped"):
        err = offline.get("error")
        if err:
            return f"Offline replay failed: {err}"
    answer = offline.get("answer")
    if not _is_blank_answer_value(answer):
        if isinstance(answer, list) and len(answer) > 1:
            return "\n\n".join(str(a) for a in answer if a)
        return answer
    row_count = offline.get("row_count")
    if row_count and int(row_count) > 0:
        offline_paths = kgqa.get("offline_recording_paths") or offline.get("offline_paths") or []
        if not offline_paths:
            single = offline.get("offline_path") or kgqa.get("offline_recording_path")
            if single:
                offline_paths = [single]
        for offline_path in offline_paths:
            payload = load_offline_payload(offline_path)
            if payload:
                tables = collect_row_tables(payload)
                for _name, rows in tables:
                    if rows:
                        preview = ", ".join(f"{k}: {v}" for k, v in rows[0].items() if v)[:400]
                        if preview:
                            return f"Full-scale replay returned {row_count} row(s). Top result: {preview}"
    online = kgqa.get("online_answer")
    if not _is_blank_answer_value(online):
        return online
    return None


def _substantive_marie_tables(tables: List[Dict[str, Any]]) -> bool:
    return any(
        (t.get("data") or [])
        and (t.get("columns") or []) not in (["answer"], ["Summary"])
        for t in tables
    )

# qa_domain values sent by the static Marie/Zaha frontends
CHEMISTRY_DOMAINS = {
    "chemistry",
    "ontospecies",
    "ontokin",
    "ontocompchem",
    "ontozeolite",
    "ontomops",
    "ontoprovenance",
    "ontopesscan",
    "species",
    "zeolites",
    "zeolite",
    "marie",
}

SG_DOMAINS = {"singapore", "sg", "zaha"}


def _catalog_entries_from_route(route: RouteResult) -> List[Any]:
    if route.catalog_entries:
        return list(route.catalog_entries)
    if route.catalog_entry:
        return [route.catalog_entry]
    return []


async def route_for_qa_domain_async(
    question: str,
    qa_domain: Optional[str],
    *,
    model_name: Optional[str] = None,
) -> RouteResult:
    """LLM-based routing; qa_domain is a soft UI hint only."""
    from mini_marie.kgqa.llm_router import route_question_async

    return await route_question_async(
        question,
        model_name=model_name,
        qa_domain_hint=qa_domain,
    )


def route_for_qa_domain(question: str, qa_domain: Optional[str]) -> RouteResult:
    """Sync wrapper for tests and legacy callers."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        return route_question(question)
    return asyncio.run(route_for_qa_domain_async(question, qa_domain))


def _wkt_from_row(row: Dict[str, Any]) -> Optional[str]:
    for key, val in row.items():
        if not isinstance(val, str):
            continue
        lk = key.lower()
        if "wkt" in lk or lk in {"geometry", "geom", "footprint"}:
            if val.upper().startswith(("POINT", "POLYGON", "LINESTRING", "MULTI")):
                return val
        if val.upper().startswith(("POINT(", "POLYGON(", "LINESTRING(", "MULTIPOLYGON(")):
            return val
    return None


def _rows_to_table(name: str, rows: List[Dict[str, Any]], *, limit: int = 500) -> List[Dict[str, Any]]:
    if not rows:
        return []
    trimmed = rows[:limit]
    vars_ = list(trimmed[0].keys())
    items: List[Dict[str, Any]] = [
        {"type": "table", "vars": vars_, "bindings": trimmed},
    ]
    wkt = _wkt_from_row(trimmed[0])
    if wkt:
        items.append({"type": "map", "title": name, "wkt_crs84": wkt})
    return items


def _offline_payload_label(payload: Dict[str, Any]) -> str:
    params = payload.get("resolved_parameters") or payload.get("seed_variables") or {}
    city = params.get("city") or payload.get("city")
    top_n = params.get("top_n")
    wf = payload.get("workflow_name") or payload.get("workflow_id") or "result"
    if city and top_n:
        return f"{city} top {top_n}"
    if city:
        return str(city)
    return str(wf)


def _data_from_offline(offline_path: Optional[str]) -> List[Dict[str, Any]]:
    if not offline_path:
        return []
    payload = load_offline_payload(offline_path)
    if not payload:
        return []
    label = _offline_payload_label(payload)
    preferred = _preferred_offline_table(payload)
    if preferred:
        _name, rows = preferred
        return _rows_to_table(label, rows)
    data: List[Dict[str, Any]] = []
    for name, rows in collect_row_tables(payload):
        data.extend(_rows_to_table(name, rows))
    return data


def _data_from_offline_paths(offline_paths: List[str]) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    for path in offline_paths:
        if not path:
            continue
        data.extend(_data_from_offline(path))
    return data


def _steps_from_metadata(question: str, metadata: Dict[str, Any], timing_ms: int) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    tool_activity = metadata.get("tool_activity") or {}
    outputs = tool_activity.get("tool_outputs") or []
    if outputs:
        for out in outputs:
            steps.append(
                {
                    "action": out.get("name") or "tool",
                    "arguments": question,
                    "results": (out.get("content") or "")[:4000],
                    "latency": timing_ms,
                }
            )
        return steps
    for name in tool_activity.get("executed_tool_names") or []:
        steps.append(
            {
                "action": name,
                "arguments": question,
                "results": "",
                "latency": timing_ms,
            }
        )
    if not steps:
        steps.append(
            {
                "action": "kgqa",
                "arguments": question,
                "results": metadata.get("route_reason") or "",
                "latency": timing_ms,
            }
        )
    return steps


def _parse_tsv_field(text: str, field: str) -> Optional[str]:
    for line in text.splitlines():
        if line.startswith(f"{field}\t"):
            return line.split("\t", 1)[1].strip()
    return None


def _summarize_competency_tool_output(tool_content: str, question: str) -> str:
    """Turn compact competency MCP TSV into a readable answer."""
    import ast

    def _row_to_hbond_text(row: Dict[str, Any]) -> Optional[str]:
        if "hbond_donors" not in row or "hbond_acceptors" not in row:
            return None
        label = row.get("primary_label") or row.get("formula") or "This species"
        smiles = row.get("smiles") or ""
        donors = row.get("hbond_donors", "?")
        acceptors = row.get("hbond_acceptors", "?")
        sm = f" (SMILES {smiles})" if smiles else ""
        return (
            f"{label}{sm} can donate **{donors}** hydrogen bond(s) "
            f"and accept **{acceptors}** hydrogen bond(s)."
        )

    if "sample_results" in tool_content:
        tail = tool_content.split("sample_results", 1)[1]
        cleaned = re.sub(r"^--- step \d+ ---\s*", "", tail, flags=re.M)
        cleaned = cleaned.split("next_step")[0].strip()
        parsed = parse_tabular_content(cleaned)
        if parsed:
            _cols, rows = parsed
            if rows:
                hbond = _row_to_hbond_text(rows[0])
                if hbond:
                    return hbond
                preview = ", ".join(f"{k}: {v}" for k, v in rows[0].items() if v)[:400]
                if preview:
                    return f"Top result for your question: {preview}"

    answer = _parse_tsv_field(tool_content, "answer")
    if answer and not _is_blank_answer_value(answer):
        try:
            val = ast.literal_eval(answer)
            if isinstance(val, list) and val and isinstance(val[0], dict):
                hbond = _row_to_hbond_text(val[0])
                if hbond:
                    return hbond
        except (SyntaxError, ValueError):
            pass
        if not answer.startswith("["):
            return answer
    status = _parse_tsv_field(tool_content, "status")
    recording_path = _parse_tsv_field(tool_content, "recording_path")
    if status in ("empty",) or _is_blank_answer_value(answer):
        if recording_path:
            return (
                "The online probe returned no rows within probe limits. "
                "A full-scale offline replay from the workflow recording is required "
                "for the complete answer."
            )
        q = question.strip()
        if re.search(r"\bperrin\b", q, re.I):
            return (
                "No Perrin-attributed pKa measurements were found in the local OntoSpecies cache. "
                "The warmed cache may not include literature provenance labels (e.g. “Perrin 1965”) "
                "on pKa rows — only zero matching compounds were returned."
            )
        if re.search(r"\buses?\b", q, re.I):
            species = re.sub(r"(?i)^find all uses of\s*", "", q).strip(" ?.")
            target = species or "that species"
            return (
                f"No uses of **{target}** are recorded in OntoSpecies. "
                "The knowledge graph search completed successfully but returned zero rows."
            )
        if re.search(r"\buncertain\b", q, re.I):
            return (
                "No pK measurements tagged **Uncertain** were found in the local OntoSpecies cache."
            )
        if re.search(r"\bacidity label\b", q, re.I) or re.search(r"\b“ah”\b|\b\"ah\"\b", q, re.I):
            return (
                "No pK measurements with acidity label **AH** were found in the local OntoSpecies cache."
            )
        if re.search(r"\bhigh pressure\b", q, re.I):
            return (
                "No species with pKa values reported at high pressures were found in the local cache."
            )
        if re.search(r"\btemperature dependence\b", q, re.I):
            return (
                "No temperature-dependent pKa series matching this query were found in the local cache."
            )
        if re.search(r"\bpka\b|\bpk values?\b", q, re.I):
            return (
                f"No matching pKa/pK records were found in OntoSpecies for: {q}. "
                "The query completed successfully but the result set is empty."
            )
        return (
            f"OntoSpecies returned no matching records for: {q}. "
            "The query completed successfully but the result set is empty."
        )
    return ""


def _summarize_sg_tool_rows(rows: List[Dict[str, Any]], question: str) -> str:
    if not rows:
        return ""
    row = rows[0]
    if "residential_pct" in row:
        total = row.get("land_plot_total", "?")
        res_pct = row.get("residential_pct", "?")
        com_pct = row.get("commercial_pct", "?")
        return (
            f"Of **{total}** zoned land plots in the Ontop cache, "
            f"**{res_pct}%** are residential and **{com_pct}%** are commercial "
            f"({row.get('residential_count', '?')} residential, "
            f"{row.get('commercial_count', '?')} commercial)."
        )
    if "commercial_plot_count" in row:
        return f"There are **{row['commercial_plot_count']}** plots zoned commercial."
    if "building_count" in row and len(row) == 1:
        return f"There are **{row['building_count']}** buildings in the Singapore Ontop cache."
    if "office_building_count" in row:
        return f"There are **{row['office_building_count']}** office buildings."
    if "plots_within_max_gfa" in row:
        return (
            f"**{row.get('plots_within_max_gfa', '?')}** plots are within max permitted GFA; "
            f"**{row.get('plots_exceeding_max_gfa', '?')}** exceed it "
            f"(of **{row.get('plots_with_area_and_max_gfa', '?')}** with comparable area and max GFA)."
        )
    if "area_sqm" in row and row.get("land_use_label"):
        return (
            f"The smallest **{row.get('land_use_label', 'agriculture')}** land plot has "
            f"**{row.get('area_sqm')}** sqm plot area"
            + (f" (max GFA **{row['max_gfa']}** sqm)." if row.get("max_gfa") else ".")
        )
    preview = ", ".join(f"{k}: {v}" for k, v in row.items() if v)[:400]
    return preview or f"Tool returned: {row}"


def _sg_tool_for_entry(entry: Any) -> Tuple[Optional[str], Optional[Any]]:
    from mini_marie.zaha.sg_old import ontop_operations as ontop

    tool_map: Dict[str, Any] = {
        "Q11": ontop.get_sg_building_count,
        "Q12": ontop.count_sg_office_buildings,
        "Q13": ontop.get_sg_residential_commercial_percent,
        "Q14": ontop.get_sg_commercial_plot_count,
        "ZQ_GFA": ontop.count_sg_within_max_gfa,
        "ZQ_GFA_LU": ontop.get_sg_gfa_compliance_by_land_use,
        "ZQ_ABBOTT": lambda: ontop.get_sg_building_footprint_by_name("Abbott"),
        "Q18": ontop.get_sg_smallest_agriculture_gfa,
    }
    fn = tool_map.get(entry.id)
    return (entry.id, fn) if fn else (None, None)


def _try_direct_sg_tool(question: str, route: RouteResult) -> Optional[Dict[str, Any]]:
    """Run an LLM-selected sg-old atomic tool without the ReAct LLM loop."""
    from mini_marie.zaha.sg_old import ontop_operations as ontop

    for entry in _catalog_entries_from_route(route):
        if entry.domain != "sg":
            continue
        tool_name, fn = _sg_tool_for_entry(entry)
        if not fn or not tool_name:
            continue

        t0 = time.perf_counter()
        try:
            rows = fn()
        except Exception as exc:
            rows = [{"error": str(exc)}]
        online_ms = round((time.perf_counter() - t0) * 1000)
        tool_content = ontop.format_tsv(rows) if rows else "No results"
        online_answer = _summarize_sg_tool_rows(rows, question)
        if rows and rows[0].get("error"):
            online_answer = str(rows[0]["error"])

        metadata: Dict[str, Any] = {
            "tool_activity": {
                "tool_outputs": [{"name": tool_name, "content": tool_content}],
                "executed_tool_names": [tool_name],
            },
            "catalog_entry_id": entry.id,
        }

        return {
            "question": question,
            "online_answer": online_answer,
            "metadata": metadata,
            "route": {
                "mcp_servers": route.mcp_servers,
                "domain": route.domain,
                "domains": route.domains,
                "reason": f"direct sg tool for {tool_name}",
                "catalog_entry": entry,
            },
            "offline": None,
            "offline_recording_path": None,
            "timing": {"online_ms": online_ms, "offline_ms": 0},
        }
    return None


def _try_direct_chemistry_workflow(
    question: str,
    route: RouteResult,
) -> Optional[Dict[str, Any]]:
    """Run an LLM-selected chemistry competency workflow without the ReAct LLM loop."""
    from mini_marie.marie.chemistry.workflow_mcp import run_competency_online
    from mini_marie.kgqa.recording_utils import extract_from_text

    for entry in _catalog_entries_from_route(route):
        if entry.domain != "chemistry" or not entry.workflow_id:
            continue

        t0 = time.perf_counter()
        tool_content = run_competency_online(
            entry.workflow_id,
            force_refresh=_demo_force_refresh(),
        )
        online_ms = round((time.perf_counter() - t0) * 1000)
        rec = extract_from_text(tool_content)
        online_answer = _summarize_competency_tool_output(tool_content, question)

        tool_outputs: List[Dict[str, str]] = []
        if "sample_results" in tool_content:
            tail = tool_content.split("sample_results", 1)[1]
            cleaned = re.sub(r"^--- step \d+ ---\s*", "", tail, flags=re.M)
            cleaned = cleaned.split("next_step")[0].strip()
            parsed = parse_tabular_content(cleaned)
            if parsed:
                _cols, rows = parsed
                if rows:
                    from mini_marie.marie.chemistry.sparql import format_tsv

                    step_tool = "workflow_step"
                    for line in tool_content.splitlines():
                        parts = line.split("\t")
                        if len(parts) >= 3 and parts[1] == "tool":
                            step_tool = parts[2]
                            break
                    tool_outputs.append({"name": step_tool, "content": format_tsv(rows)})

        metadata: Dict[str, Any] = {
            "tool_activity": {
                "tool_outputs": tool_outputs,
                "executed_tool_names": ["run_competency_online"] + [t["name"] for t in tool_outputs],
            },
            "workflow_id": entry.workflow_id,
            "catalog_entry_id": entry.id,
            "competency_envelope": tool_content,
        }

        t_off = time.perf_counter()
        offline_result = _replay_offline_if_enabled(
            rec.get("recording_path"),
            workflow_id=entry.workflow_id,
        )
        offline_ms = round((time.perf_counter() - t_off) * 1000) if offline_result else 0
        if _is_blank_answer_value(online_answer) and offline_result:
            online_answer = _summarize_competency_tool_output(tool_content, question)

        return {
            "question": question,
            "online_answer": online_answer,
            "metadata": metadata,
            "route": {
                "mcp_servers": route.mcp_servers,
                "domain": route.domain,
                "domains": route.domains,
                "reason": f"direct workflow {entry.workflow_id}",
                "catalog_entry": entry,
            },
            "offline": offline_result,
            "offline_recording_path": (offline_result or {}).get("offline_path"),
            "timing": {"online_ms": online_ms, "offline_ms": offline_ms},
        }
    return None


def _try_direct_mof_competency_workflow(
    question: str,
    route: RouteResult,
) -> Optional[Dict[str, Any]]:
    """Run an LLM-selected MOF competency workflow without the ReAct LLM loop."""
    from mini_marie.kgqa.recording_utils import extract_from_text
    from mini_marie.mop_mof.mof.competency_workflow_mcp import run_competency_online

    for entry in _catalog_entries_from_route(route):
        if entry.domain != "mof" or not entry.workflow_id:
            continue

        t0 = time.perf_counter()
        tool_content = run_competency_online(entry.workflow_id)
        online_ms = round((time.perf_counter() - t0) * 1000)
        rec = extract_from_text(tool_content)
        online_answer = _summarize_competency_tool_output(tool_content, question)

        tool_outputs: List[Dict[str, str]] = []
        if "sample_results" in tool_content:
            tail = tool_content.split("sample_results", 1)[1]
            cleaned = re.sub(r"^--- step \d+ ---\s*", "", tail, flags=re.M)
            cleaned = cleaned.split("next_step")[0].strip()
            parsed = parse_tabular_content(cleaned)
            if parsed:
                cols, rows = parsed
                if rows:
                    tool_outputs.append(
                        {
                            "name": "workflow_step",
                            "content": "\n".join(
                                ["\t".join(cols)]
                                + [
                                    "\t".join(str(row.get(col, "")) for col in cols)
                                    for row in rows
                                ]
                            ),
                        }
                    )

        metadata: Dict[str, Any] = {
            "tool_activity": {
                "tool_outputs": tool_outputs,
                "executed_tool_names": ["run_competency_online"] + [t["name"] for t in tool_outputs],
            },
            "workflow_id": entry.workflow_id,
            "catalog_entry_id": entry.id,
            "competency_envelope": tool_content,
        }

        t_off = time.perf_counter()
        offline_result = _replay_offline_if_enabled(
            rec.get("recording_path"),
            workflow_id=entry.workflow_id,
        )
        offline_ms = round((time.perf_counter() - t_off) * 1000) if offline_result else 0

        return {
            "question": question,
            "online_answer": online_answer,
            "metadata": metadata,
            "route": {
                "mcp_servers": route.mcp_servers,
                "domain": route.domain,
                "domains": route.domains,
                "reason": f"direct MOF workflow {entry.workflow_id}",
                "catalog_entry": entry,
            },
            "workflow_id": entry.workflow_id,
            "offline": offline_result,
            "offline_recording_path": (offline_result or {}).get("offline_path"),
            "timing": {"online_ms": online_ms, "offline_ms": offline_ms},
        }
    return None



def _try_direct_cross_domain(
    question: str,
    route: RouteResult,
) -> Optional[Dict[str, Any]]:
    """Run direct tools for each LLM-selected catalog entry across domains."""
    if route.domain != "cross_kg" and len(route.domains or []) <= 1:
        return None

    chem = _try_direct_chemistry_workflow(question, route)
    sg = _try_direct_sg_tool(question, route)
    if not chem and not sg:
        return None
    if chem and not sg:
        chem["route"] = {
            "mcp_servers": route.mcp_servers,
            "domain": "cross_kg",
            "domains": route.domains,
            "reason": "cross-domain (chemistry direct tool)",
            "catalog_entry": (chem.get("route") or {}).get("catalog_entry"),
        }
        return chem
    if sg and not chem:
        sg["route"] = {
            "mcp_servers": route.mcp_servers,
            "domain": "cross_kg",
            "domains": route.domains,
            "reason": "cross-domain (sg direct tool)",
            "catalog_entry": (sg.get("route") or {}).get("catalog_entry"),
        }
        return sg

    sections: List[str] = []
    if chem.get("online_answer"):
        sections.append(f"**Chemistry:** {chem['online_answer']}")
    if sg.get("online_answer"):
        sections.append(f"**Singapore:** {sg['online_answer']}")

    chem_meta = chem.get("metadata") or {}
    sg_meta = sg.get("metadata") or {}
    chem_tools = (chem_meta.get("tool_activity") or {}).get("tool_outputs") or []
    sg_tools = (sg_meta.get("tool_activity") or {}).get("tool_outputs") or []
    executed = (
        (chem_meta.get("tool_activity") or {}).get("executed_tool_names") or []
    ) + ((sg_meta.get("tool_activity") or {}).get("executed_tool_names") or [])

    chem_timing = chem.get("timing") or {}
    sg_timing = sg.get("timing") or {}
    return {
        "question": question,
        "online_answer": "\n\n".join(sections),
        "metadata": {
            "tool_activity": {
                "tool_outputs": chem_tools + sg_tools,
                "executed_tool_names": executed,
            },
            "catalog_entry_ids": [e.id for e in _catalog_entries_from_route(route)],
            "competency_envelope": chem_meta.get("competency_envelope"),
        },
        "route": {
            "mcp_servers": route.mcp_servers,
            "domain": "cross_kg",
            "domains": route.domains,
            "reason": route.reason or "cross-domain direct tools",
            "catalog_entry": route.catalog_entry,
        },
        "offline": chem.get("offline"),
        "offline_recording_path": chem.get("offline_recording_path"),
        "timing": {
            "online_ms": int(chem_timing.get("online_ms") or 0)
            + int(sg_timing.get("online_ms") or 0),
            "offline_ms": int(chem_timing.get("offline_ms") or 0)
            + int(sg_timing.get("offline_ms") or 0),
        },
    }


def _try_direct_from_route(question: str, route: RouteResult) -> Optional[Dict[str, Any]]:
    cross = _try_direct_cross_domain(question, route)
    if cross:
        return cross
    mof = _try_direct_mof_competency_workflow(question, route)
    if mof:
        return mof
    sg = _try_direct_sg_tool(question, route)
    if sg:
        return sg
    return _try_direct_chemistry_workflow(question, route)


def _resolve_offline_recording_paths(kgqa: Dict[str, Any]) -> List[str]:
    """All offline JSON paths for TWA tables (batch-aware, sidecar-aware)."""
    paths: List[str] = []
    seen: set[str] = set()

    def _add(path: Optional[str]) -> None:
        if not path:
            return
        resolved = str(Path(path).resolve())
        if resolved not in seen:
            seen.add(resolved)
            paths.append(resolved)

    for path in kgqa.get("offline_recording_paths") or []:
        _add(path)
    offline = kgqa.get("offline") or {}
    for path in offline.get("offline_paths") or []:
        _add(path)
    _add(kgqa.get("offline_recording_path"))
    _add(offline.get("offline_path"))

    if paths:
        return paths

    rec_paths = kgqa.get("recording_paths") or []
    rec: Dict[str, Any] = {}
    if not rec_paths and kgqa.get("recording_path"):
        rec_paths = [kgqa["recording_path"]]
    if not rec_paths:
        rec = _extract_recording_for_kgqa(
            str(kgqa.get("online_answer") or ""),
            kgqa.get("metadata") or {},
        )
        rec_paths = rec.get("recording_paths") or []
        if not rec_paths and rec.get("recording_path"):
            rec_paths = [rec["recording_path"]]
    if not rec_paths:
        return []

    if not rec.get("recordings"):
        rec = _extract_recording_for_kgqa(
            str(kgqa.get("online_answer") or ""),
            kgqa.get("metadata") or {},
        )
    recordings = rec.get("recordings") or []
    replay = _replay_offline_batch_if_enabled(
        rec_paths,
        recordings=recordings,
        workflow_id=kgqa.get("workflow_id"),
    )
    if replay:
        for path in replay.get("offline_paths") or []:
            _add(path)
        _add(replay.get("offline_path"))
    return paths


def kgqa_result_to_twa(kgqa: Dict[str, Any]) -> Dict[str, Any]:
    """Convert orchestrator output to {metadata, data} for POST /qa/."""
    timing = kgqa.get("timing") or {}
    metadata = kgqa.get("metadata") or {}
    online_ms = int(timing.get("online_ms") or timing.get("total_ms") or 0)

    offline_paths = _resolve_offline_recording_paths(kgqa)
    data = _data_from_offline_paths(offline_paths)
    if not data:
        answer = kgqa.get("online_answer") or ""
        if isinstance(answer, list) and answer and isinstance(answer[0], dict):
            data = _rows_to_table("answer", answer)
        else:
            text = answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)
            data = [{"type": "table", "vars": ["answer"], "bindings": [{"answer": text}]}]

    return {
        "metadata": {"steps": _steps_from_metadata(kgqa.get("question") or "", metadata, online_ms)},
        "data": data,
    }


def kgqa_result_to_marie(kgqa: Dict[str, Any]) -> Dict[str, Any]:
    """Convert orchestrator output to Marie chemistry demo POST /api/qa/ shape."""
    question = kgqa.get("question") or ""
    metadata = kgqa.get("metadata") or {}
    tool_outputs = (metadata.get("tool_activity") or {}).get("tool_outputs") or []

    twa = kgqa_result_to_twa(kgqa)
    offline_tables = tables_from_zaha_items(twa.get("data") or [])
    tool_tables = tables_from_tool_outputs(tool_outputs, skip_meta=True)
    if tool_tables and not _substantive_marie_tables(offline_tables):
        offline_tables = tool_tables
    elif len(offline_tables) == 1:
        only = offline_tables[0]
        cols = only.get("columns") or []
        rows = only.get("data") or []
        if cols in (["answer"], ["Summary"]) and rows:
            cell = str(rows[0].get(cols[0], ""))
            if _is_weak_answer(cell):
                offline_tables = []
    display_answer = _display_answer(kgqa)
    envelope = _competency_envelope_from_metadata(metadata)
    if envelope:
        metadata.setdefault("competency_envelope", envelope)
    offline = kgqa.get("offline") or {}
    summarized = _summarize_competency_tool_output(envelope, question) if envelope else ""
    if summarized and (
        _is_blank_answer_value(display_answer)
        or offline.get("status") == "empty"
        or _is_weak_answer(str(display_answer or ""))
    ):
        display_answer = summarized
    if _is_blank_answer_value(display_answer):
        display_answer = (
            f"No matching records were found in the local chemistry cache for: {question}"
        )
    marie_data = build_marie_data(
        offline_tables=offline_tables,
        tool_outputs=tool_outputs,
        online_answer=display_answer,
    )

    narrative = build_marie_narrative(
        question,
        online_answer=display_answer,
        tool_outputs=tool_outputs,
        data=marie_data,
    )

    payload = {
        "metadata": build_marie_metadata(question, kgqa, tool_outputs),
        "visualisation": {},
        "data": marie_data,
        "_narrative": narrative,
    }
    return payload


def _extract_recording_for_kgqa(
    online_answer: str,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Best-effort recording extraction from agent answer and tool outputs."""
    from mini_marie.kgqa.recording_utils import extract_all_from_text, extract_recording_info

    rec = extract_recording_info(online_answer=online_answer, metadata=metadata)
    if not rec.get("recording_paths"):
        for source in (metadata.get("competency_envelope"), online_answer):
            if not source:
                continue
            for extra in extract_all_from_text(str(source)):
                path = extra.get("recording_path")
                if not path:
                    continue
                rec.setdefault("recordings", [])
                rec.setdefault("recording_paths", [])
                if path not in rec["recording_paths"]:
                    rec["recording_paths"].append(path)
                    rec["recordings"].append(extra)
            if rec.get("recording_paths"):
                rec["recording_path"] = rec["recording_paths"][0]
                if not rec.get("workflow_id") and rec.get("recordings"):
                    rec["workflow_id"] = rec["recordings"][0].get("workflow_id")
                break
    if not rec.get("workflow_id"):
        rec["workflow_id"] = metadata.get("workflow_id")
    return rec


async def _execute_kgqa(
    question: str,
    *,
    qa_domain: Optional[str] = None,
    model_name: str = "gpt-4o",
    recursion_limit: int = 120,
    route: Optional[RouteResult] = None,
) -> Dict[str, Any]:
    from mini_marie.kgqa.agent import KgqaAgent

    if route is None:
        route = await route_for_qa_domain_async(question, qa_domain, model_name=model_name)
    t0 = time.perf_counter()
    agent = KgqaAgent(model_name=model_name, remote_model=True)
    online_answer, metadata = await agent.ask(
        question,
        route=route,
        recursion_limit=recursion_limit,
    )
    online_ms = round((time.perf_counter() - t0) * 1000)

    rec = _extract_recording_for_kgqa(online_answer, metadata)
    recording_paths = rec.get("recording_paths") or []
    recording_path = rec.get("recording_path") or (recording_paths[0] if recording_paths else None)
    workflow_id = rec.get("workflow_id") or metadata.get("workflow_id")
    if recording_paths:
        metadata.setdefault("recording_paths", recording_paths)
    if recording_path:
        metadata.setdefault("recording_path", recording_path)
    if workflow_id:
        metadata.setdefault("workflow_id", workflow_id)

    t_off = time.perf_counter()
    offline_result = _replay_offline_batch_if_enabled(
        recording_paths,
        recordings=rec.get("recordings"),
        workflow_id=workflow_id,
    )
    offline_ms = round((time.perf_counter() - t_off) * 1000) if offline_result else 0

    envelope = _competency_envelope_from_metadata(metadata)
    if envelope:
        metadata["competency_envelope"] = envelope

    offline_paths = (offline_result or {}).get("offline_paths") or []
    if not offline_paths and (offline_result or {}).get("offline_path"):
        offline_paths = [offline_result["offline_path"]]

    return {
        "question": question,
        "online_answer": online_answer,
        "metadata": metadata,
        "route": {
            "mcp_servers": route.mcp_servers,
            "domain": route.domain,
            "domains": route.domains,
            "reason": route.reason,
        },
        "recording_path": recording_path,
        "recording_paths": recording_paths,
        "workflow_id": workflow_id,
        "offline": offline_result,
        "offline_recording_path": (offline_result or {}).get("offline_path"),
        "offline_recording_paths": offline_paths,
        "timing": {"online_ms": online_ms, "offline_ms": offline_ms},
    }


async def _run_kgqa_core(
    question: str,
    *,
    qa_domain: Optional[str] = None,
    model_name: str = "gpt-4o",
    recursion_limit: int = 120,
) -> Dict[str, Any]:
    """Shared KGQA pipeline for Marie and Zaha (cross-domain, unified backend)."""
    route = await route_for_qa_domain_async(
        question,
        qa_domain,
        model_name=model_name,
    )
    kgqa = _try_direct_from_route(question, route)
    if not kgqa:
        kgqa = await _execute_kgqa(
            question,
            qa_domain=qa_domain,
            model_name=model_name,
            recursion_limit=recursion_limit,
            route=route,
        )
    return kgqa


async def run_twa_qa(
    question: str,
    *,
    qa_domain: Optional[str] = None,
    model_name: str = "gpt-4o",
    recursion_limit: int = 120,
) -> Dict[str, Any]:
    """Execute KGQA and return TWA-compatible QA payload."""
    kgqa = await _run_kgqa_core(
        question,
        qa_domain=qa_domain,
        model_name=model_name,
        recursion_limit=recursion_limit,
    )
    return kgqa_result_to_twa(kgqa)


async def run_marie_qa(
    question: str,
    *,
    qa_domain: Optional[str] = None,
    model_name: str = "gpt-4o",
    recursion_limit: int = 120,
) -> Dict[str, Any]:
    """Execute KGQA and return Marie demo POST /api/qa/ payload."""
    kgqa = await _run_kgqa_core(
        question,
        qa_domain=qa_domain or "marie",
        model_name=model_name,
        recursion_limit=recursion_limit,
    )
    payload = kgqa_result_to_marie(kgqa)
    narrative = payload.pop("_narrative", "")
    request_id = str(uuid.uuid4())
    _MARIE_SESSIONS[request_id] = {
        "question": question,
        "payload": payload,
        "narrative": narrative,
    }
    payload["request_id"] = request_id
    return payload


def stream_marie_chat_events(qa_request_id: str) -> Generator[str, None, None]:
    """SSE stream for Marie ./chat using qa_request_id."""
    session = _MARIE_SESSIONS.get(qa_request_id) or {}
    question = session.get("question") or ""
    payload = session.get("payload") or {}
    data_items = payload.get("data") or []
    narrative = session.get("narrative") or ""
    yield from stream_chat_events(question, data_items, narrative=narrative)


def _extract_table_snippet(item: Dict[str, Any]) -> str:
    rows = item.get("data") or item.get("bindings") or []
    if not rows:
        return ""
    vars_ = item.get("vars") or item.get("columns") or []
    if vars_ == ["answer"] and len(rows) == 1:
        return str(rows[0].get("answer", "")).strip()
    return json.dumps(rows[0], ensure_ascii=False)[:500]


def stream_chat_events(
    question: str,
    data_items: List[Dict[str, Any]],
    *,
    narrative: Optional[str] = None,
) -> Generator[str, None, None]:
    """SSE stream matching Zaha/Marie ./chat contract."""
    text = (narrative or "").strip()
    if not text:
        snippets: List[str] = []
        for item in data_items:
            if item.get("type") == "table":
                snippet = _extract_table_snippet(item)
                if snippet:
                    snippets.append(snippet)
            elif item.get("type") == "map":
                snippets.append(f"Map: {item.get('title') or 'geometry'}")
        text = (
            "\n\n".join(snippets)
            if snippets
            else "No tabular results were returned."
        )

    started = time.perf_counter()
    # First chunk empty-ish then word stream (matches frontend trimStart behavior)
    for idx, token in enumerate(_tokenize_stream(text)):
        latency = round((time.perf_counter() - started) * 1000)
        prefix = " " if idx else ""
        payload = {"content": prefix + token, "latency": latency}
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _tokenize_stream(text: str) -> Iterable[str]:
    for part in re.findall(r"\S+\s*", text):
        yield part
