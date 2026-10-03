"""
Run real KgqaAgent (ReAct + mof-twa MCP) on MOF demo questions and report identity enrichment.

Writes docs/MOF_AGENT_IDENTITY_TEST.md

Usage:
  PYTHONPATH=. python scripts/run_mof_agent_identity_test.py
  PYTHONPATH=. python scripts/run_mof_agent_identity_test.py --offline-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dotenv import load_dotenv

load_dotenv(REPO / ".env")

QUESTIONS = [
    "Which MOFs have the same topology as ZIF-8?",
    "Which Zr-containing MOFs have carboxylate linkers?",
    "How many experimental Cu-containing MOFs are recorded?",
]

_OPAQUE_MOF_RE = re.compile(
    r"mof_\d+%5B|mof_\d+\[|MetalOrganicFramework/",
    re.I,
)
_ENRICH_TOOLS = frozenset(
    {"enrich_mof_table_rows", "lookup_mof_identity_by_entries"}
)


def _tools_from_result(result: dict) -> list[str]:
    meta = result.get("metadata") or {}
    return list(meta.get("tool_activity", {}).get("executed_tool_name_set") or [])


def _answer_text(result: dict) -> str:
    return (result.get("online_answer") or "").strip()


def _score_agent_answer(question: str, answer: str, tools: list[str]) -> dict:
    opaque = bool(_OPAQUE_MOF_RE.search(answer))
    enrich_called = bool(_ENRICH_TOOLS & set(tools))
    has_human = any(
        tok in answer
        for tok in ("refcode", "MOFid", "EWIDUK", "ZIF-8", "sod topology", "9,325", "9325")
    )
    return {
        "enrich_tool_called": enrich_called,
        "tools": tools,
        "opaque_slug_in_answer": opaque,
        "has_human_identity_signal": has_human,
        "answer_len": len(answer),
    }


def _demo_marie_row(question: str) -> dict:
    from mini_marie.kgqa.mcp_router import route_question
    from demos.twa_adapter import _try_direct_from_route, kgqa_result_to_marie
    from demos.kg_row_narrative import is_weak_tool_summary

    route = route_question(question)
    prev = os.environ.get("MOF_COMPETENCY_DIRECT")
    os.environ["MOF_COMPETENCY_DIRECT"] = "1"
    try:
        kgqa = _try_direct_from_route(question, route)
    finally:
        if prev is None:
            os.environ.pop("MOF_COMPETENCY_DIRECT", None)
        else:
            os.environ["MOF_COMPETENCY_DIRECT"] = prev
    payload = kgqa_result_to_marie(kgqa) if kgqa else {}
    narrative = (payload.get("_narrative") or "").strip()
    data = payload.get("data") or []
    table = next((t for t in data if t.get("type") == "table"), {})
    rows = table.get("data") or []
    cols = table.get("columns") or []
    sample = rows[0] if rows else {}
    return {
        "path": "direct_route + kgqa_result_to_marie",
        "narrative_preview": narrative[:500],
        "weak_narrative": is_weak_tool_summary(narrative),
        "columns_head": cols[:6],
        "sample_display_label": sample.get("display_label"),
        "sample_name": sample.get("name"),
        "sample_refcode": sample.get("refcode"),
    }


async def _run_agent(question: str, *, model: str) -> dict:
    from mini_marie.kgqa.orchestrator import run_online_phase_async

    t0 = time.perf_counter()
    result = await run_online_phase_async(question, model_name=model, recursion_limit=80)
    elapsed = round((time.perf_counter() - t0) * 1000)
    tools = _tools_from_result(result)
    answer = _answer_text(result)
    score = _score_agent_answer(question, answer, tools)
    score["elapsed_ms"] = elapsed
    score["answer_preview"] = answer[:800]
    score["recording_path"] = result.get("recording_path")
    score["workflow_id"] = result.get("workflow_id")
    return score


def _md_table_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _parse_recording_path(envelope: str) -> str:
    for line in envelope.splitlines():
        if line.startswith("recording_path\t"):
            return line.split("\t", 1)[1].strip()
    raise ValueError("recording_path not found in competency envelope")


def mcp_toolchain_simulation(question: str, workflow_id: str) -> dict:
    """
    Agent-equivalent MCP sequence (no LLM):
    run_competency_online → offline replay → enrich_mof_table_rows logic.
    """
    import json

    from demos.kg_row_narrative import pick_best_call_trace_rows
    from demos.mof_display_identity import mof_row_display_label
    from mini_marie.mop_mof.mof.competency_cache import CompetencyCache
    from mini_marie.mop_mof.mof.competency_workflow_engine import (
        load_workflow,
        replay_competency_from_recording,
    )
    from mini_marie.mop_mof.mof.competency_workflow_mcp import run_competency_online
    from mini_marie.mop_mof.mof.mof_identity_enrichment import enrich_mof_rows
    from mini_marie.mop_mof.mof.mof_operations import format_results_as_tsv

    t0 = time.perf_counter()
    online_env = run_competency_online(workflow_id)
    rec_path = _parse_recording_path(online_env)
    recorded = json.loads(Path(rec_path).read_text(encoding="utf-8"))
    offline_result = replay_competency_from_recording(recorded, load_workflow(workflow_id))
    rows = pick_best_call_trace_rows(offline_result, question)
    if not rows:
        return {
            "workflow_id": workflow_id,
            "error": "no rows from offline replay",
            "tools": ["run_competency_online", "replay_competency_offline"],
        }

    before = rows[0]
    cache = CompetencyCache()
    enriched = enrich_mof_rows(rows, cache=cache, allow_remote=True)
    after = enriched[0]
    elapsed = round((time.perf_counter() - t0) * 1000)

    return {
        "workflow_id": workflow_id,
        "recording_path": rec_path,
        "tools": [
            "run_competency_online",
            "replay_competency_offline (orchestrator)",
            "enrich_mof_table_rows",
        ],
        "row_count": len(rows),
        "before_keys": sorted(before.keys()),
        "before_label": mof_row_display_label(before),
        "after_name": after.get("name"),
        "after_refcode": after.get("refcode"),
        "after_mofid": (after.get("mofid") or "")[:80],
        "after_label": mof_row_display_label(after),
        "enriched_tsv_head": format_results_as_tsv(enriched[:3]),
        "elapsed_ms": elapsed,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("KGQA_TEST_MODEL", "gpt-4o-mini"))
    parser.add_argument(
        "--offline-only",
        action="store_true",
        help="Skip live ReAct (no API key); only document demo-path enrichment.",
    )
    args = parser.parse_args()

    has_key = bool(
        os.environ.get("REMOTE_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("AZURE_OPENAI_API_KEY")
    )
    lines: list[str] = [
        "# MOF identity — agent vs demo path test report",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Configuration",
        "",
        f"- Model: `{args.model}`",
        f"- OpenAI/Azure key present: **{has_key}**",
        f"- Agent ReAct run: **{not args.offline_only and has_key}**",
        "",
    ]

    agent_results: list[tuple[str, dict]] = []
    if args.offline_only or not has_key:
        lines.append(
            "> **Agent ReAct skipped** — set `REMOTE_API_KEY` (or `OPENAI_API_KEY`) and omit `--offline-only` "
            "to run live tool traces including `enrich_mof_table_rows`."
        )
        lines.append("")
    else:
        lines.extend(["## Live KgqaAgent (ReAct + mof-twa MCP)", ""])
        lines.append(_md_table_row(["Question", "Tools", "Enrich called?", "Opaque slug?", "ms"]))
        lines.append(_md_table_row(["---"] * 5))
        for q in QUESTIONS:
            try:
                row = await _run_agent(q, model=args.model)
            except Exception as exc:
                row = {
                    "tools": [],
                    "enrich_tool_called": False,
                    "opaque_slug_in_answer": True,
                    "elapsed_ms": 0,
                    "answer_preview": f"ERROR: {exc}",
                }
            agent_results.append((q, row))
            tools_short = ", ".join(row.get("tools") or [])[:80] or "—"
            lines.append(
                _md_table_row(
                    [
                        q[:48] + ("…" if len(q) > 48 else ""),
                        tools_short,
                        "yes" if row.get("enrich_tool_called") else "no",
                        "yes" if row.get("opaque_slug_in_answer") else "no",
                        str(row.get("elapsed_ms", "")),
                    ]
                )
            )
        lines.append("")
        for q, row in agent_results:
            lines.append(f"### Agent: {q}")
            lines.append("")
            lines.append(f"- **Tools:** `{', '.join(row.get('tools') or [])}`")
            lines.append(
                f"- **Enrichment MCP used:** {row.get('enrich_tool_called')}"
            )
            lines.append(f"- **Recording:** `{row.get('recording_path') or '—'}`")
            lines.append("")
            lines.append("**Answer preview:**")
            lines.append("")
            lines.append("```")
            lines.append(row.get("answer_preview") or "(empty)")
            lines.append("```")
            lines.append("")

    lines.extend(["## MCP toolchain simulation (agent-equivalent, no LLM)", ""])
    lines.append(
        "Exercises the same tools the ReAct agent should call: "
        "`run_competency_online` → offline replay → `enrich_mof_rows` (MCP: `enrich_mof_table_rows`)."
    )
    lines.append("")
    sim_cases = [
        ("Which MOFs have the same topology as ZIF-8?", "CQ07_SAME_TOPO_ZIF8"),
        ("Which Zr-containing MOFs have carboxylate linkers?", "CQ_D1_ZR_COOH"),
    ]
    for question, wf_id in sim_cases:
        try:
            sim = mcp_toolchain_simulation(question, wf_id)
        except Exception as exc:
            sim = {"error": str(exc), "workflow_id": wf_id}
        lines.append(f"### Simulation: {question}")
        lines.append("")
        if sim.get("error"):
            lines.append(f"**Error:** {sim['error']}")
            lines.append("")
            continue
        lines.append(f"- **Workflow:** `{sim['workflow_id']}`")
        lines.append(f"- **Tool chain:** {' → '.join(sim.get('tools') or [])}")
        lines.append(f"- **Rows:** {sim.get('row_count')} ({sim.get('elapsed_ms')} ms)")
        lines.append(f"- **Label before enrich:** `{sim.get('before_label')}`")
        lines.append(
            f"- **After enrich:** name=`{sim.get('after_name')}` refcode=`{sim.get('after_refcode')}` "
            f"display=`{sim.get('after_label')}`"
        )
        lines.append("")
        lines.append("**Enriched sample TSV (3 rows):**")
        lines.append("")
        lines.append("```tsv")
        lines.append(sim.get("enriched_tsv_head") or "")
        lines.append("```")
        lines.append("")

    lines.extend(["## Demo path (direct route + auto enrichment)", ""])
    lines.append(
        "Same questions via `route_question` → `_try_direct_from_route` → "
        "`kgqa_result_to_marie` (always runs `_kg_enrich_marie_table_identities` + `display_label`)."
    )
    lines.append("")
    for q in QUESTIONS:
        demo = _demo_marie_row(q)
        lines.append(f"### Demo: {q}")
        lines.append("")
        lines.append(f"- **Columns (head):** `{demo['columns_head']}`")
        lines.append(f"- **display_label sample:** `{demo.get('sample_display_label')}`")
        lines.append(f"- **name / refcode sample:** `{demo.get('sample_name')}` / `{demo.get('sample_refcode')}`")
        lines.append(f"- **Weak narrative:** {demo['weak_narrative']}")
        lines.append("")
        lines.append("**Narrative preview:**")
        lines.append("")
        lines.append(demo["narrative_preview"] or "_empty_")
        lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            "- **Agent path** depends on the model calling `enrich_mof_table_rows` after competency tools "
            "(prompt instructs this in `KgqaAgent._mof_identity_enrichment_hint`).",
            "- **Demo path** enriches tables automatically (cache-only merge + `display_label`); "
            "MCP simulation also hits **live SPARQL** for refcode/MOFid when cache misses.",
            "- **Live ReAct** requires `REMOTE_API_KEY` or `OPENAI_API_KEY` in `.env`; skipped if unset.",
            "- Re-run this script after prompt or MCP changes to compare `Enrich called?` column.",
            "- **MCP simulation** always runs without an API key; use it in CI.",
            "",
            "## How to re-run",
            "",
            "```bash",
            "export PYTHONPATH=$(pwd)",
            "python scripts/run_mof_agent_identity_test.py          # + live agent if REMOTE_API_KEY set",
            "python scripts/run_mof_agent_identity_test.py --offline-only",
            "python scripts/run_mof_demo_twelve_report.py",
            "```",
            "",
        ]
    )

    out = REPO / "docs" / "MOF_AGENT_IDENTITY_TEST.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")
    if agent_results:
        summary = {
            q: {
                "enrich": r.get("enrich_tool_called"),
                "tools": r.get("tools"),
            }
            for q, r in agent_results
        }
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
