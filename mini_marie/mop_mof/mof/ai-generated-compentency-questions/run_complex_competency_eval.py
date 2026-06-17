"""
Run complex MOF TWA competency workflows that chain multiple MCP tool calls.

Each workflow passes extracted values from one step as inputs to the next.
Exports JSON/MD results plus a full nested call trace with I/O.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from mini_marie.mop_mof.mof.competency_engine import MCP_SERVER_NAME, run_workflow

DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = DIR / "complex_competency_questions.json"
RESULTS_JSON = DIR / "complex_competency_results.json"
RESULTS_MD = DIR / "complex_competency_results.md"
CALL_TRACE_JSON = DIR / "complex_competency_call_trace.json"
CALL_TRACE_MD = DIR / "complex_competency_call_trace.md"


def write_markdown(payload: dict) -> None:
    lines = [
        "# MOF TWA Complex Competency Evaluation",
        "",
        f"Run at: {payload['run_at']}",
        f"Endpoint: {payload['endpoint']}",
        f"Workflows: {payload['total']} | Passed: {payload['passed']} | Errors: {payload['errors']}",
        f"Total MCP tool calls: {payload['total_tool_calls']}",
        "",
    ]
    for result in payload["results"]:
        lines.extend(
            [
                f"## {result['id']} — {result['category']}",
                "",
                f"**Question:** {result['question']}",
                "",
                f"**Status:** {result['status']} ({result['elapsed_ms']} ms, {result['total_tool_calls']} tool calls)",
                "",
                f"**Answer:** {result['answer']}",
                "",
                "**Resolved variables:**",
                "",
                "```json",
                json.dumps(result.get("variables", {}), indent=2),
                "```",
                "",
            ]
        )
        for call in result.get("call_trace", []):
            label = call.get("mcp_tool") or call.get("name", "aggregate")
            lines.extend(
                [
                    f"### Step {call['step']}: `{label}`",
                    "",
                    f"Status: {call['status']} ({call['elapsed_ms']} ms)",
                    "",
                    "**Input:**",
                    "",
                    "```json",
                    json.dumps(call.get("input", {}), indent=2),
                    "```",
                    "",
                    f"**Summary:** {call.get('summary', 'n/a')}",
                    "",
                    "**Output (TSV):**",
                    "",
                    "```tsv",
                    call.get("tsv") or "(no data)",
                    "```",
                    "",
                ]
            )
    RESULTS_MD.write_text("\n".join(lines), encoding="utf-8")


def write_call_trace(payload: dict) -> None:
    trace = {
        "run_at": payload["run_at"],
        "mcp_server": MCP_SERVER_NAME,
        "endpoint": payload["endpoint"],
        "workflow_count": payload["total"],
        "total_tool_calls": payload["total_tool_calls"],
        "workflows": [],
    }

    for result in payload["results"]:
        trace["workflows"].append(
            {
                "workflow_id": result["id"],
                "question": result["question"],
                "status": result["status"],
                "answer": result["answer"],
                "variables": result.get("variables", {}),
                "call_sequence": result.get("call_trace", []),
            }
        )

    CALL_TRACE_JSON.write_text(json.dumps(trace, indent=2), encoding="utf-8")

    lines = [
        "# MOF TWA Complex MCP Call Trace",
        "",
        f"Run at: {trace['run_at']}",
        f"MCP server: `{trace['mcp_server']}`",
        f"Endpoint: {trace['endpoint']}",
        f"Workflows: {trace['workflow_count']} | Tool calls: {trace['total_tool_calls']}",
        "",
    ]
    for workflow in trace["workflows"]:
        lines.extend(
            [
                f"## {workflow['workflow_id']}",
                "",
                f"**Question:** {workflow['question']}",
                "",
                f"**Answer:** {workflow['answer']}",
                "",
                "**Variables:**",
                "",
                "```json",
                json.dumps(workflow["variables"], indent=2),
                "```",
                "",
            ]
        )
        for call in workflow["call_sequence"]:
            tool_label = call.get("mcp_tool") or call.get("name", "aggregate")
            lines.extend(
                [
                    f"### Step {call['step']} — `{tool_label}`",
                    "",
                    "**Input:**",
                    "",
                    "```json",
                    json.dumps(call.get("input", {}), indent=2),
                    "```",
                    "",
                    f"**Status:** {call['status']} ({call['elapsed_ms']} ms)",
                    "",
                    f"**Summary:** {call.get('summary', 'n/a')}",
                    "",
                    "**Output rows:**",
                    "",
                    "```json",
                    json.dumps(call.get("rows", []), indent=2),
                    "```",
                    "",
                    "**Output (TSV):**",
                    "",
                    "```tsv",
                    call.get("tsv") or "(no data)",
                    "```",
                    "",
                ]
            )
    CALL_TRACE_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    from mini_marie.mop_mof.mof import mof_operations as ops

    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    results = [run_workflow(question) for question in questions]

    passed = sum(1 for r in results if r["status"] == "pass")
    errors = sum(1 for r in results if r["status"] == "error")
    total_tool_calls = sum(r.get("total_tool_calls", 0) for r in results)

    payload = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": ops.DEFAULT_SPARQL_ENDPOINT,
        "total": len(results),
        "passed": passed,
        "errors": errors,
        "total_tool_calls": total_tool_calls,
        "results": results,
    }

    RESULTS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(payload)
    write_call_trace(payload)

    print(
        f"Evaluated {len(results)} complex workflows: {passed} pass, {errors} error, "
        f"{total_tool_calls} tool calls"
    )
    print(f"Wrote {RESULTS_JSON}")
    print(f"Wrote {RESULTS_MD}")
    print(f"Wrote {CALL_TRACE_JSON}")
    print(f"Wrote {CALL_TRACE_MD}")


if __name__ == "__main__":
    main()
