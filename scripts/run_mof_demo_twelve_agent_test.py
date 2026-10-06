"""
Run all 12 canonical MOF demo questions via Marie ReAct (run_marie_qa).

Writes docs/MOF_DEMO_TWELVE_AGENT_RESULTS.md

Usage (repo root):
  python scripts/run_mof_demo_twelve_agent_test.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dotenv import load_dotenv

load_dotenv(REPO / ".env")
from demos.demo_env import load_demo_env  # noqa: E402

load_demo_env()

from demos.kg_row_narrative import is_weak_tool_summary, summarize_from_data  # noqa: E402
from demos.table_presentation import enrich_marie_tables  # noqa: E402
from demos.test_kg_row_narrative import CANONICAL_DEMO_TWELVE  # noqa: E402
from demos.twa_adapter import _MARIE_SESSIONS, run_marie_qa  # noqa: E402
from mini_marie.kgqa.mcp_router import route_question  # noqa: E402
from mini_marie.kgqa.question_catalog import match_catalog_exact  # noqa: E402

OUT = REPO / "docs" / "MOF_DEMO_TWELVE_AGENT_RESULTS.md"
MAX_TABLE_ROWS = 8
CELL_MAX = 80


def esc(value: object) -> str:
    text = str(value or "").replace("|", "\\|").replace("\n", " ")
    if len(text) > CELL_MAX:
        return text[: CELL_MAX - 3] + "..."
    return text


def md_table(rows: list[dict], *, column_labels: dict | None = None) -> str:
    if not rows:
        return "_No rows._\n"
    cols = list(rows[0].keys())
    headers = [column_labels.get(c, c) if column_labels else c for c in cols]
    lines = ["| " + " | ".join(esc(h) for h in headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in cols) + " |")
    for row in rows[:MAX_TABLE_ROWS]:
        lines.append("| " + " | ".join(esc(row.get(c)) for c in cols) + " |")
    if len(rows) > MAX_TABLE_ROWS:
        lines.append(f"\n_Showing {MAX_TABLE_ROWS} of {len(rows)} rows._")
    return "\n".join(lines) + "\n"


def _tools_from_payload(payload: dict) -> list[str]:
    meta = payload.get("metadata") or {}
    bindings = (meta.get("data_request") or {}).get("entity_bindings") or {}
    return [v[0] for v in bindings.values() if v]


async def _run_one(question: str, *, model: str, recursion_limit: int) -> dict:
    t0 = time.perf_counter()
    payload = await run_marie_qa(
        question,
        qa_domain="marie",
        model_name=model,
        recursion_limit=recursion_limit,
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    sid = payload.get("request_id")
    narrative = ((_MARIE_SESSIONS.get(sid) or {}).get("narrative") or "").strip()
    data = payload.get("data") or []
    if not narrative and data:
        narrative = (summarize_from_data(question, data) or "").strip()
    enriched = enrich_marie_tables(data, question=question) if data else []
    meta = payload.get("metadata") or {}
    entry = match_catalog_exact(question)
    wf = (entry.workflow_id if entry else None) or "?"
    weak = is_weak_tool_summary(narrative) or len(narrative) < 25
    has_table = any(
        it.get("type") == "table" and (it.get("data") or it.get("bindings"))
        for it in data
    )
    ready = bool(meta.get("agent_driven")) and narrative and not weak and has_table
    return {
        "question": question,
        "workflow_id": wf,
        "elapsed_ms": elapsed_ms,
        "agent_driven": meta.get("agent_driven"),
        "tools": _tools_from_payload(payload),
        "narrative": narrative,
        "data": data,
        "enriched": enriched,
        "weak": weak,
        "has_table": has_table,
        "ready": ready,
    }


async def main_async() -> int:
    has_key = bool(
        os.environ.get("REMOTE_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("AZURE_OPENAI_API_KEY")
    )
    if not has_key:
        print("ERROR: set REMOTE_API_KEY or OPENAI_API_KEY in .env")
        return 1

    model = os.environ.get("KGQA_TEST_MODEL", "gpt-4o-mini")
    recursion_limit = int(os.environ.get("MARIE_MOFS_RECURSION_LIMIT", "80"))

    parts: list[str] = [
        "# MOF demo — 12 canonical questions (live ReAct agent)",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Execution path: `route_question` → `KgqaAgent` (ReAct) → MCP "
        "(`run_competency_online`, optional identity tools) → `kgqa_result_to_marie`.",
        "",
        "Post-feedback fixes (Q6/Q9/Q10): David-aligned Zr+carboxylate SPARQL, full water-stability "
        "filter (Burtch/acid/base/details), synthesis solvent normalization and smarter table columns.",
        "",
        f"- **Model:** `{model}`",
        f"- **Recursion limit:** {recursion_limit}",
        "",
    ]

    results: list[dict] = []
    for question in CANONICAL_DEMO_TWELVE:
        print(f"Running: {question[:70]}…")
        try:
            row = await _run_one(question, model=model, recursion_limit=recursion_limit)
        except Exception as exc:
            entry = match_catalog_exact(question)
            row = {
                "question": question,
                "workflow_id": entry.workflow_id if entry else "?",
                "error": f"{type(exc).__name__}: {exc}",
                "ready": False,
                "narrative": "",
                "enriched": [],
                "tools": [],
                "agent_driven": False,
                "elapsed_ms": 0,
            }
        results.append(row)
        tools = row.get("tools") or []
        print(
            f"  → ready={row.get('ready')} ms={row.get('elapsed_ms')} tools={tools}"
        )

    ready_count = sum(1 for r in results if r.get("ready"))
    parts.extend(
        [
            "## Summary",
            "",
            f"- **Ready (agent + NL + table):** {ready_count} / {len(CANONICAL_DEMO_TWELVE)}",
            "",
            "| # | Workflow | ms | Tools | Status |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for i, row in enumerate(results, 1):
        wf = row.get("workflow_id") or "?"
        st = "READY" if row.get("ready") else "GAP"
        if row.get("error"):
            st = "ERROR"
        tools = ", ".join(row.get("tools") or []) or "—"
        parts.append(
            f"| {i} | `{wf}` | {row.get('elapsed_ms', 0)} | {esc(tools)} | **{st}** |"
        )
    parts.append("")
    parts.append("---")
    parts.append("")

    for i, row in enumerate(results, 1):
        parts.append(f"## {i}. {row['question']}")
        parts.append("")
        parts.append(f"- **Workflow:** `{row.get('workflow_id')}`")
        parts.append(f"- **Agent driven:** {row.get('agent_driven')}")
        parts.append(f"- **Tools:** `{', '.join(row.get('tools') or []) or '—'}`")
        parts.append(f"- **Elapsed:** {row.get('elapsed_ms')} ms")
        if row.get("error"):
            parts.append(f"- **Error:** {row['error']}")
        flags = []
        if row.get("weak"):
            flags.append("weak/missing NL")
        if not row.get("has_table"):
            flags.append("no table")
        if not row.get("agent_driven"):
            flags.append("not agent-driven")
        flag_text = f" ({', '.join(flags)})" if flags else ""
        status = "READY" if row.get("ready") else "GAP"
        if row.get("error"):
            status = "ERROR"
        parts.append(f"- **Status:** **{status}**{flag_text}")
        parts.append("")
        parts.append("### Natural language answer")
        parts.append("")
        parts.append(row.get("narrative") or "_No narrative._")
        parts.append("")
        parts.append("### Tables")
        parts.append("")
        enriched = row.get("enriched") or []
        if not enriched:
            parts.append("_No table data._")
        else:
            tnum = 0
            for item in enriched:
                if item.get("type") != "table":
                    continue
                tnum += 1
                label = item.get("label") or item.get("step_tool") or f"Table {tnum}"
                rows = item.get("data") or item.get("bindings") or []
                parts.append(f"#### {label} ({len(rows)} rows in payload)")
                col_meta = {
                    m["key"]: m.get("label", m["key"])
                    for m in (item.get("columns_meta") or [])
                }
                show_cols = item.get("display_columns") or (list(rows[0].keys()) if rows else [])
                show_cols = [c for c in show_cols if rows and c in rows[0]]
                trimmed = [{k: r.get(k) for k in show_cols} for r in rows] if show_cols else rows
                parts.append(md_table(trimmed, column_labels=col_meta))
        parts.append("---")
        parts.append("")

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"\nWrote {OUT} — ready {ready_count}/{len(CANONICAL_DEMO_TWELVE)}")
    return 0 if ready_count == len(CANONICAL_DEMO_TWELVE) else 1


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
