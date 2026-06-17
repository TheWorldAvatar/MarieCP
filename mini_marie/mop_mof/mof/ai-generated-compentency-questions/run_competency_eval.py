"""
Run MOF TWA competency questions against MCP tool backends.

Each question maps to one atomic MCP tool in mini_marie.mop_mof.mof.main.
Results are written to competency_results.json and competency_results.md.
"""

from __future__ import annotations

import asyncio
import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from mini_marie.mop_mof.mof import mof_operations as ops

DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = DIR / "competency_questions.json"
RESULTS_JSON = DIR / "competency_results.json"
RESULTS_MD = DIR / "competency_results.md"
CALL_TRACE_JSON = DIR / "competency_call_trace.json"
CALL_TRACE_MD = DIR / "competency_call_trace.md"
MCP_SERVER_NAME = "mof-twa"

# Mirrors mini_marie.mop_mof.mof.main MCP tool registry (same functions, sync layer).
TOOL_REGISTRY = {
    "get_mof_total_count": lambda **_: ops.get_mof_total_count(),
    "get_source_database_stats": lambda **_: ops.get_source_database_stats(),
    "get_tobassco_co2_coverage": lambda **_: ops.get_tobassco_co2_coverage(),
    "get_tobassco_co2_uptake_stats": lambda **_: ops.get_tobassco_co2_uptake_stats(),
    "get_top_tobassco_co2_uptake": lambda **_: ops.get_top_tobassco_co2_uptake(),
    "get_top_tobassco_co2_valid_pore_geometry": lambda **_: ops.get_top_tobassco_co2_valid_pore_geometry(),
    "get_large_pore_co2_candidates": lambda **_: ops.get_large_pore_co2_candidates(),
    "get_tobassco_topology_counts": lambda **_: ops.get_tobassco_topology_counts(),
    "get_tobassco_mofs_by_topology": lambda **kw: ops.get_tobassco_mofs_by_topology(kw["topology"]),
    "get_tobassco_mofs_by_metal_node": lambda **kw: ops.get_tobassco_mofs_by_metal_node(kw["metal_smiles"]),
    "get_mofs_by_sourcedb": lambda **kw: ops.get_mofs_by_sourcedb(kw["source_db"]),
    "lookup_mof_by_mofid_fragment": lambda **kw: ops.lookup_mof_by_mofid_fragment(kw["mofid_fragment"]),
    "get_mof_properties_by_mofid_fragment": lambda **kw: ops.get_mof_properties_by_mofid_fragment(
        kw["mofid_fragment"]
    ),
}


def _summarize_answer(question: dict, rows: list[dict]) -> str:
    if not rows:
        return "No results returned."

    grading = question.get("grading", "")
    if grading == "numeric_count":
        key = next(iter(rows[0]))
        return f"{key} = {rows[0][key]}"

    if grading == "aggregate_stats":
        parts = [f"{k}={v}" for k, v in rows[0].items()]
        return ", ".join(parts)

    if grading == "ranked_list":
        first = rows[0]
        if "db" in first and "count" in first:
            return f"Top source: {first['db']} ({first['count']} MOFs); {len(rows)} rows returned."
        if "topology" in first and "count" in first:
            return f"Most common topology: {first['topology']} ({first['count']} MOFs); {len(rows)} rows returned."
        if "co2_uptake" in first:
            return f"Top CO2 uptake: {first.get('co2_uptake')} mmol/g; {len(rows)} rows returned."
        return f"{len(rows)} rows returned."

    if grading == "lookup_hits":
        return f"{len(rows)} MOF(s) matched; top CO2 uptake = {rows[0].get('co2_uptake', 'n/a')}."

    if grading == "property_list":
        props = [r.get("p", "").split("/")[-1] for r in rows[:5]]
        return f"{len(rows)} property triples; sample: {', '.join(props)}"

    return f"{len(rows)} rows returned."


def run_question(question: dict) -> dict:
    tool_name = question["tool"]
    fn = TOOL_REGISTRY[tool_name]
    started = time.perf_counter()
    try:
        rows = fn(**question.get("args", {}))
        tsv = ops.format_results_as_tsv(rows)
        summary = _summarize_answer(question, rows)
        status = "pass" if rows else "empty"
        error = None
    except Exception as exc:
        rows = []
        tsv = ""
        summary = ""
        status = "error"
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return {
        "id": question["id"],
        "category": question["category"],
        "question": question["question"],
        "tool": tool_name,
        "args": question.get("args", {}),
        "status": status,
        "elapsed_ms": elapsed_ms,
        "summary": summary,
        "row_count": len(rows),
        "rows": rows,
        "tsv": tsv,
        "error": error,
    }


def write_call_trace(payload: dict) -> None:
    """Export ordered MCP tool call sequence with explicit input/output payloads."""
    sequence = []
    for index, result in enumerate(payload["results"], start=1):
        sequence.append(
            {
                "step": index,
                "question_id": result["id"],
                "category": result["category"],
                "natural_language_question": result["question"],
                "mcp_server": MCP_SERVER_NAME,
                "mcp_tool": result["tool"],
                "input": result.get("args", {}),
                "output": {
                    "status": result["status"],
                    "elapsed_ms": result["elapsed_ms"],
                    "summary": result.get("summary"),
                    "row_count": result.get("row_count", 0),
                    "rows": result.get("rows", []),
                    "tsv": result.get("tsv", ""),
                    "error": result.get("error"),
                },
            }
        )

    trace = {
        "run_at": payload["run_at"],
        "mcp_server": MCP_SERVER_NAME,
        "endpoint": payload["endpoint"],
        "total_calls": len(sequence),
        "call_sequence": sequence,
    }
    CALL_TRACE_JSON.write_text(json.dumps(trace, indent=2), encoding="utf-8")

    lines = [
        "# MOF TWA MCP Call Trace",
        "",
        f"Run at: {trace['run_at']}",
        f"MCP server: `{trace['mcp_server']}`",
        f"Endpoint: {trace['endpoint']}",
        f"Total calls: {trace['total_calls']}",
        "",
    ]
    for call in sequence:
        lines.extend(
            [
                f"## Step {call['step']} — {call['question_id']} (`{call['mcp_tool']}`)",
                "",
                f"**Question:** {call['natural_language_question']}",
                "",
                "**Input:**",
                "",
                "```json",
                json.dumps(call["input"], indent=2),
                "```",
                "",
                f"**Output status:** {call['output']['status']} ({call['output']['elapsed_ms']} ms)",
                "",
                f"**Summary:** {call['output']['summary'] or call['output'].get('error') or 'n/a'}",
                "",
                f"**Row count:** {call['output']['row_count']}",
                "",
                "**Output rows (JSON):**",
                "",
                "```json",
                json.dumps(call["output"]["rows"], indent=2),
                "```",
                "",
                "**Output (TSV):**",
                "",
                "```tsv",
                call["output"]["tsv"] or "(no data)",
                "```",
                "",
            ]
        )
    CALL_TRACE_MD.write_text("\n".join(lines), encoding="utf-8")


def write_markdown(payload: dict) -> None:
    lines = [
        "# MOF TWA MCP Competency Evaluation",
        "",
        f"Run at: {payload['run_at']}",
        f"Endpoint: {payload['endpoint']}",
        f"Questions: {payload['total']} | Passed: {payload['passed']} | Empty: {payload['empty']} | Errors: {payload['errors']}",
        "",
    ]
    for result in payload["results"]:
        lines.extend(
            [
                f"## {result['id']} — {result['category']}",
                "",
                f"**Question:** {result['question']}",
                "",
                f"**Tool:** `{result['tool']}`",
                "",
                f"**Status:** {result['status']} ({result['elapsed_ms']} ms)",
                "",
                f"**Summary:** {result['summary'] or result.get('error', 'n/a')}",
                "",
                "```tsv",
                result["tsv"] or "(no data)",
                "```",
                "",
            ]
        )
    RESULTS_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    results = [run_question(q) for q in questions]

    passed = sum(1 for r in results if r["status"] == "pass")
    empty = sum(1 for r in results if r["status"] == "empty")
    errors = sum(1 for r in results if r["status"] == "error")

    payload = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": ops.DEFAULT_SPARQL_ENDPOINT,
        "total": len(results),
        "passed": passed,
        "empty": empty,
        "errors": errors,
        "results": results,
    }

    RESULTS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(payload)
    write_call_trace(payload)

    print(f"Evaluated {len(results)} questions: {passed} pass, {empty} empty, {errors} error")
    print(f"Wrote {RESULTS_JSON}")
    print(f"Wrote {RESULTS_MD}")
    print(f"Wrote {CALL_TRACE_JSON}")
    print(f"Wrote {CALL_TRACE_MD}")


if __name__ == "__main__":
    main()
