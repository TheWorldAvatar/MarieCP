"""Run 12 canonical MOF demo questions and write docs/MOF_DEMO_TWELVE_RESULTS.md."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

# Fast offline report only — production Marie uses ReAct (see run_mof_demo_twelve_agent_test.py).
os.environ.setdefault("MOF_COMPETENCY_DIRECT", "1")

from demos.kg_row_narrative import is_weak_tool_summary, summarize_from_data
from demos.table_presentation import enrich_marie_tables
from demos.test_kg_row_narrative import CANONICAL_DEMO_TWELVE
from demos.twa_adapter import _try_direct_from_route, kgqa_result_to_marie
from mini_marie.kgqa.mcp_router import route_question

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "MOF_DEMO_TWELVE_RESULTS.md"
MAX_TABLE_ROWS = 8
CELL_MAX = 80


def esc(value: object) -> str:
    text = str(value or "").replace("|", "\\|").replace("\n", " ")
    if len(text) > CELL_MAX:
        return text[: CELL_MAX - 3] + "..."
    return text


def md_table(
    rows: list[dict],
    max_rows: int = MAX_TABLE_ROWS,
    *,
    column_labels: dict | None = None,
) -> str:
    if not rows:
        return "_No rows._\n"
    cols = list(rows[0].keys())
    headers = [column_labels.get(c, c) if column_labels else c for c in cols]
    lines = ["| " + " | ".join(esc(h) for h in headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in cols) + " |")
    for row in rows[:max_rows]:
        lines.append("| " + " | ".join(esc(row.get(c)) for c in cols) + " |")
    if len(rows) > max_rows:
        lines.append(
            f"\n_Showing {max_rows} of {len(rows)} rows in payload sample._"
        )
    return "\n".join(lines) + "\n"


def workflow_id(kgqa: dict | None) -> str:
    if not kgqa:
        return "?"
    meta = kgqa.get("metadata") or {}
    for key in ("workflow_id", "competency_workflow_id", "workflow"):
        if meta.get(key):
            return str(meta[key])
    steps = kgqa.get("steps") or []
    if steps and isinstance(steps[0], dict):
        return str(steps[0].get("workflow_id") or steps[0].get("name") or "?")
    return "?"


def main() -> None:
    parts: list[str] = [
        "# MOF demo — 12 canonical questions (local run)",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Execution path: `route_question` → `_try_direct_from_route` → "
        "`kgqa_result_to_marie` (offline competency cache, same stack as Marie Classic).",
        "",
        "Tables use **user-facing column headers** (from `columns_meta`); internal KG fields "
        "such as `mof` are hidden by default in the Marie Classic UI. See "
        "[MOF_AGENT_IDENTITY_TEST.md](./MOF_AGENT_IDENTITY_TEST.md).",
        "",
    ]

    ready = 0
    issues: list[tuple[str, bool, bool, bool]] = []

    for i, question in enumerate(CANONICAL_DEMO_TWELVE, 1):
        route = route_question(question)
        kgqa = _try_direct_from_route(question, route)
        ok_route = bool(kgqa)
        payload = kgqa_result_to_marie(kgqa) if kgqa else {}
        data = payload.get("data") or []
        enriched = enrich_marie_tables(data, question=question) if data else []

        narrative = (payload.get("_narrative") or "").strip()
        if not narrative and data:
            narrative = (summarize_from_data(question, data) or "").strip()

        weak = is_weak_tool_summary(narrative) or len(narrative) < 25
        has_table = any(
            it.get("type") == "table" and (it.get("data") or it.get("bindings"))
            for it in data
        )
        status = "ready" if ok_route and narrative and not weak and has_table else "gap"
        if status == "ready":
            ready += 1
        else:
            issues.append((question, ok_route, has_table, weak))

        parts.append(f"## {i}. {question}")
        parts.append("")
        parts.append(f"- **Workflow:** `{workflow_id(kgqa)}`")
        flags = []
        if weak:
            flags.append("weak/missing NL")
        if not has_table:
            flags.append("no table")
        if not ok_route:
            flags.append("routing failed")
        flag_text = f" ({', '.join(flags)})" if flags else ""
        parts.append(f"- **Status:** **{status.upper()}**{flag_text}")
        parts.append("")
        parts.append("### Natural language answer")
        parts.append("")
        parts.append(narrative if narrative else "_No narrative returned._")
        parts.append("")
        parts.append("### Tables")
        parts.append("")

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
                rc = item.get("row_count") or len(rows)
                parts.append(
                    f"#### {label} ({rc} rows per metadata, {len(rows)} in sample payload)"
                )
                col_meta = {
                    m["key"]: m.get("label", m["key"])
                    for m in (item.get("columns_meta") or [])
                }
                show_cols = item.get("display_columns") or list(rows[0].keys()) if rows else []
                show_cols = [c for c in show_cols if rows and c in rows[0]]
                if col_meta and show_cols:
                    hdr = ", ".join(col_meta.get(c, c) for c in show_cols[:8])
                    parts.append(f"_Table columns (user-facing):_ {hdr}")
                parts.append("")
                trimmed = [{k: r.get(k) for k in show_cols} for r in rows] if show_cols else rows
                parts.append(md_table(trimmed, column_labels=col_meta))

        parts.append("---")
        parts.append("")

    summary: list[str] = [
        "## Summary",
        "",
        f"- **Ready (non-weak NL + at least one table):** {ready} / {len(CANONICAL_DEMO_TWELVE)}",
        "",
    ]
    if issues:
        summary.append("- **Gaps:**")
        for q, ok_r, ht, wk in issues:
            summary.append(
                f"  - {q} — route_ok={ok_r}, has_table={ht}, weak_nl={wk}"
            )
    else:
        summary.append("- All twelve passed local readiness checks.")
    summary.extend(["", "---", ""])

    doc = "\n".join(parts[:6] + summary + parts[6:])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"Wrote {OUT} ({len(doc)} chars); ready {ready}/{len(CANONICAL_DEMO_TWELVE)}")


if __name__ == "__main__":
    main()
