"""MCP-safe chemistry competency workflow execution (compact agent responses, full data on disk)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from mini_marie.marie.chemistry.chemistry_workflow_engine import (
    load_manifest,
    load_workflow,
    replay_from_recording,
    run_competency_workflow,
    save_run,
)
from mini_marie.marie.chemistry.limits import DEFAULT_ONLINE_PROBE_LIMIT
from mini_marie.marie.chemistry.sparql import format_tsv
from mini_marie.workflow_parameters import parse_parameters_json, resolve_workflow_parameters

MCP_ONLINE_LIMIT = DEFAULT_ONLINE_PROBE_LIMIT


def _demo_force_refresh() -> bool:
    return os.environ.get("DEMO_FORCE_REFRESH", "true").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def list_competency_workflows_text() -> str:
    manifest = load_manifest()
    lines = ["workflow_id\ttitle"]
    for wf in manifest.get("workflows") or []:
        lines.append(f"{wf.get('id', '')}\t{wf.get('title', '')}")
    return "\n".join(lines)


def _compact_rows(rows: List[Dict[str, Any]], max_rows: int = 5) -> List[Dict[str, Any]]:
    return rows[:max_rows]


def format_competency_mcp_response(result: Dict[str, Any], recording_path: Path) -> str:
    params = result.get("resolved_parameters") or {}
    lines = [
        f"status\t{result.get('status')}",
        f"mode\t{result.get('mode')}",
        f"workflow_id\t{result.get('workflow_id')}",
        f"title\t{result.get('title', '')}",
        f"elapsed_ms\t{result.get('elapsed_ms', '')}",
        f"recording_path\t{recording_path.resolve()}",
        f"resolved_parameters\t{params}",
        f"answer\t{result.get('answer')}",
        "",
        "step\ttype\ttool\tstatus\trow_count\telapsed_ms",
    ]
    for step in result.get("call_trace") or []:
        lines.append(
            "\t".join(
                [
                    str(step.get("step", "")),
                    str(step.get("step_type", "")),
                    str(step.get("tool") or step.get("transform") or ""),
                    str(step.get("status", "")),
                    str(step.get("row_count", "")),
                    str(step.get("elapsed_ms", "")),
                ]
            )
        )

    lines.append("")
    lines.append("sample_results")
    for step in result.get("call_trace") or []:
        rows = _compact_rows(step.get("rows") or [], max_rows=5)
        if rows:
            lines.append(f"--- step {step.get('step')} ---")
            lines.append(format_tsv(rows))

    lines.append("")
    lines.append(
        "next_step\tOffline full answer is produced by replay_competency_offline(recording_path) outside the LLM"
    )
    return "\n".join(lines)


def run_competency_online(
    workflow_id: str,
    online_limit: int = MCP_ONLINE_LIMIT,
    *,
    question: str = "",
    parameters_json: str = "",
    force_refresh: Optional[bool] = None,
) -> str:
    wf = load_workflow(workflow_id)
    overrides = parse_parameters_json(parameters_json)
    parameters = resolve_workflow_parameters(wf, question, overrides)
    result = run_competency_workflow(
        wf,
        mode="online",
        online_limit=min(online_limit, MCP_ONLINE_LIMIT),
        force_refresh=_demo_force_refresh() if force_refresh is None else force_refresh,
        question=question,
        parameters=parameters,
    )
    path = save_run(result)
    return format_competency_mcp_response(result, path)


def replay_competency_offline(recording_path: str) -> str:
    path = Path(recording_path)
    result = replay_from_recording(path)
    result["replayed_from"] = str(path.resolve())
    out_path = save_run(result)
    return format_competency_mcp_response(result, out_path)
