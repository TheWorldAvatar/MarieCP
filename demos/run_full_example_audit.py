"""Full backend audit: Marie + Zaha example questions via ReAct KGQA (no direct shortcuts).

Uses _execute_kgqa (same path as demo server LLM mode) — not _try_direct_chemistry_workflow
or _try_direct_sg_tool.

Run from repo root:
  python -m demos.run_full_example_audit
  python -m demos.run_full_example_audit --suite marie
  python -m demos.run_full_example_audit --suite zaha --limit 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
load_dotenv(REPO / ".env", override=True)
load_dotenv(REPO / "configs" / "demo_local.env", override=True)

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_META_COLUMNS = frozenset({"id", "mcp_server", "endpoint", "scale", "path", "exists", "mb"})
OUT_DIR = REPO / "demos" / "audit_runs"


@dataclass
class AuditResult:
    suite: str
    qid: str
    question: str
    ok: bool
    detail: str
    elapsed_ms: int
    data_rows: int = 0
    steps: int = 0
    tools: Optional[List[str]] = None
    workflow_id: Optional[str] = None
    offline_status: Optional[str] = None
    error: Optional[str] = None


def _load_marie_questions() -> List[tuple[str, str, Optional[str], List[str]]]:
    from mini_marie.kgqa.question_catalog import _load_marie_nl_questions

    entries = sorted(_load_marie_nl_questions(), key=lambda e: int(e.id.replace("MQ", "")))
    return [(e.id, e.question, e.workflow_id, list(e.tags or [])) for e in entries]


def _load_zaha_questions() -> List[tuple[str, str, Optional[str]]]:
    path = REPO / "mini_marie" / "zaha" / "sg_old" / "competency_questions.json"
    items = json.loads(path.read_text(encoding="utf-8"))
    return [(str(it["id"]), str(it["question"]), None) for it in items]


def _is_meta_table(table: Dict[str, Any]) -> bool:
    cols = set(table.get("columns") or [])
    if "mcp_server" in cols or ("path" in cols and "exists" in cols):
        return True
    return bool(cols) and cols.issubset(_META_COLUMNS)


def _table_rows(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    if item.get("type") != "table":
        return []
    return list(item.get("bindings") or item.get("data") or [])


def _narrative_is_echo(narrative: str, question: str) -> bool:
    text = (narrative or "").strip()
    q = question.strip()
    return bool(text) and (text == f"**Question:** {q}" or (text.startswith("**Question:**") and len(text) < len(q) + 40))


def _evaluate_marie(
    payload: Dict[str, Any],
    narrative: str,
    *,
    question: str,
    tags: Optional[List[str]] = None,
    offline_status: Optional[str] = None,
) -> tuple[bool, str, int]:
    data = payload.get("data") or []
    rows = sum(len(t.get("data") or []) for t in data if t.get("type") == "table")
    substantive_rows = sum(
        len(t.get("data") or [])
        for t in data
        if t.get("type") == "table"
        and (t.get("columns") or []) not in (["answer"], ["Summary"])
    )
    meta_tables = [t for t in data if t.get("type") == "table" and _is_meta_table(t)]
    narrative = (narrative or payload.get("_narrative") or "").strip()
    weak = not narrative or len(narrative) < 15
    infra = "infrastructure" in narrative.lower() or "mcp_server" in narrative.lower()
    expected_empty = "expected_empty" in (tags or [])
    no_results_only = any(
        phrase in narrative.lower()
        for phrase in (
            "no matching records",
            "returned zero rows",
            "no uses of",
            "not found in the local",
            "result set is empty",
        )
    )
    if meta_tables:
        return False, "meta/infrastructure table(s)", rows
    if infra:
        return False, "infrastructure-only narrative", rows
    if _narrative_is_echo(narrative, question):
        return False, "question echo (no substantive answer)", rows
    if substantive_rows > 0:
        return True, (narrative or f"{substantive_rows} data row(s)")[:200], rows
    if expected_empty and (offline_status == "empty" or no_results_only):
        return True, narrative[:200], rows
    if offline_status == "empty" and not no_results_only and not expected_empty:
        return False, "offline replay empty without explanatory answer", rows
    if rows > 0 and no_results_only:
        return True, narrative[:200], rows
    if weak:
        return False, f"weak answer: {narrative[:120]!r}", rows
    return True, narrative[:200], rows


def _evaluate_zaha(payload: Dict[str, Any], *, question: str = "") -> tuple[bool, str, int, int]:
    data = payload.get("data") or []
    rows = sum(len(_table_rows(item)) for item in data)
    steps = len((payload.get("metadata") or {}).get("steps") or [])
    narrative = ""
    for item in data:
        bindings = _table_rows(item)
        vars_ = item.get("vars") or item.get("columns") or []
        if vars_ == ["answer"] and bindings:
            narrative = str(bindings[0].get("answer", ""))
            break
        if bindings and len(vars_) == 1:
            cell = str(bindings[0].get(vars_[0], ""))
            if len(cell) > len(narrative):
                narrative = cell
    weak = not narrative or len(narrative) < 15
    infra = "infrastructure" in narrative.lower() or "mcp_server" in narrative.lower()
    if infra:
        return False, "infrastructure-only narrative", rows, steps
    if "http status 500" in narrative.lower() and "partial" not in narrative.lower():
        return False, "live probe HTTP 500 without partial KG answer", rows, steps
    if rows > 0:
        return True, (narrative or f"{rows} data row(s)")[:200], rows, steps
    if weak:
        return False, f"weak answer: {narrative[:120]!r}", rows, steps
    return True, narrative[:200], rows, steps


async def _run_one(
    suite: str,
    qid: str,
    question: str,
    workflow_id: Optional[str],
    *,
    tags: Optional[List[str]] = None,
    model_name: str,
    recursion_limit: int,
) -> AuditResult:
    from demos.twa_adapter import _execute_kgqa, kgqa_result_to_marie, kgqa_result_to_twa

    qa_domain = "marie" if suite == "marie" else "singapore"
    t0 = time.perf_counter()
    try:
        kgqa = await _execute_kgqa(
            question,
            qa_domain=qa_domain,
            model_name=model_name,
            recursion_limit=recursion_limit,
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        meta = kgqa.get("metadata") or {}
        tools = list(meta.get("tool_activity", {}).get("executed_tool_name_set") or [])
        offline = kgqa.get("offline") or {}
        offline_status = str(offline.get("status") or ("skipped" if not kgqa.get("recording_path") else "none"))

        if suite == "marie":
            payload = kgqa_result_to_marie(kgqa)
            narrative = payload.pop("_narrative", "")
            ok, detail, rows = _evaluate_marie(
                payload,
                narrative,
                question=question,
                tags=tags,
                offline_status=offline_status,
            )
            steps = len((payload.get("metadata") or {}).get("steps") or [])
        else:
            payload = kgqa_result_to_twa(kgqa)
            ok, detail, rows, steps = _evaluate_zaha(payload, question=question)

        return AuditResult(
            suite=suite,
            qid=qid,
            question=question,
            ok=ok,
            detail=detail,
            elapsed_ms=elapsed,
            data_rows=rows,
            steps=steps,
            tools=tools,
            workflow_id=kgqa.get("workflow_id") or workflow_id,
            offline_status=offline_status,
        )
    except Exception as exc:
        return AuditResult(
            suite=suite,
            qid=qid,
            question=question,
            ok=False,
            detail=f"{type(exc).__name__}: {exc}",
            elapsed_ms=int((time.perf_counter() - t0) * 1000),
            error=traceback.format_exc(),
            workflow_id=workflow_id,
        )


def _write_report(results: List[AuditResult], path: Path, *, model_name: str) -> Dict[str, Any]:
    passed = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "mode": "full_kgqa_execute",
        "total": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "marie_total": sum(1 for r in results if r.suite == "marie"),
        "marie_passed": sum(1 for r in results if r.suite == "marie" and r.ok),
        "zaha_total": sum(1 for r in results if r.suite == "zaha"),
        "zaha_passed": sum(1 for r in results if r.suite == "zaha" and r.ok),
        "total_elapsed_ms": sum(r.elapsed_ms for r in results),
    }
    payload = {"summary": summary, "results": [asdict(r) for r in results]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return summary


async def _main_async(args: argparse.Namespace) -> int:
    suites: List[tuple[str, List[tuple[str, str, Optional[str], List[str]]]]] = []
    if args.suite in ("all", "marie"):
        suites.append(("marie", _load_marie_questions()))
    if args.suite in ("all", "zaha"):
        zq = [(qid, q, wf, []) for qid, q, wf in _load_zaha_questions()]
        suites.append(("zaha", zq))

    questions: List[tuple[str, str, str, Optional[str], List[str]]] = []
    for suite, items in suites:
        for qid, q, wf, tags in items:
            questions.append((suite, qid, q, wf, tags))
    if args.limit:
        questions = questions[: args.limit]

    ts = int(time.time())
    report_path = OUT_DIR / f"full_audit_{ts}.json"
    results: List[AuditResult] = []

    print(f"Running {len(questions)} questions (model={args.model}, mode=full KGQA)…")
    for i, (suite, qid, question, wf, tags) in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {suite}:{qid} …", flush=True)
        result = await _run_one(
            suite,
            qid,
            question,
            wf,
            tags=tags,
            model_name=args.model,
            recursion_limit=args.recursion_limit,
        )
        results.append(result)
        mark = "OK" if result.ok else "FAIL"
        print(
            f"  -> [{mark}] {result.elapsed_ms}ms rows={result.data_rows} "
            f"tools={result.tools} offline={result.offline_status}",
            flush=True,
        )
        if not result.ok:
            print(f"     {result.detail}", flush=True)
        _write_report(results, report_path, model_name=args.model)

    summary = _write_report(results, report_path, model_name=args.model)
    print(json.dumps(summary, indent=2))
    print(f"Report: {report_path}")
    return 0 if summary["failed"] == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Full KGQA audit for Marie + Zaha example questions")
    parser.add_argument("--suite", choices=["all", "marie", "zaha"], default="all")
    parser.add_argument("--limit", type=int, default=0, help="Max questions (0 = all)")
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--recursion-limit", type=int, default=80)
    args = parser.parse_args()
    if args.limit == 0:
        args.limit = None  # type: ignore[assignment]
    raise SystemExit(asyncio.run(_main_async(args)))


if __name__ == "__main__":
    main()
