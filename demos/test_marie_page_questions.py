"""Backend smoke test: Marie homepage questions → POST /demos/marie/api/qa shape.

Uses direct competency workflows where catalogued (fast, no LLM). Questions
without a workflow_id are routing-checked only unless --llm is passed.

Run from repo root:
  python -m demos.test_marie_page_questions
  python -m demos.test_marie_page_questions --llm          # also run LLM for all
  python -m demos.test_marie_page_questions --http         # hit running server
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from demos.demo_env import load_demo_env

REPO = Path(__file__).resolve().parents[1]
load_demo_env()

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_META_COLUMNS = frozenset({"id", "mcp_server", "endpoint", "scale", "path", "exists", "mb"})


@dataclass
class QuestionResult:
    mq_id: str
    question: str
    mode: str
    ok: bool
    detail: str
    elapsed_ms: int
    data_rows: int = 0
    workflow_id: Optional[str] = None


def _load_questions():
    from mini_marie.kgqa.question_catalog import CatalogEntry, match_catalog_exact

    page = REPO / "demos" / "marie-classic" / "index.html"
    text = page.read_text(encoding="utf-8")
    questions: List[CatalogEntry] = []
    seen: set[str] = set()
    for match in re.finditer(r"populateInputText\(&quot;(.*?)&quot;\)", text, re.S):
        question = html.unescape(match.group(1)).strip()
        if not question or question in seen:
            continue
        seen.add(question)
        entry = match_catalog_exact(question)
        if not entry:
            entry = CatalogEntry(
                id=f"page_{len(questions) + 1}",
                question=question,
                domain="unknown",
                mcp_servers=[],
                workflow_id=None,
                tags=["marie_page"],
                kind="example",
            )
        questions.append(entry)
    return questions


def _is_meta_table(table: Dict[str, Any]) -> bool:
    cols = set(table.get("columns") or [])
    if "mcp_server" in cols or ("path" in cols and "exists" in cols):
        return True
    return bool(cols) and cols.issubset(_META_COLUMNS)


def _evaluate_payload(payload: Dict[str, Any], *, expect_data: bool) -> tuple[bool, str, int]:
    data = payload.get("data") or []
    rows = sum(len(t.get("data") or []) for t in data if t.get("type") == "table")
    meta_tables = [t for t in data if t.get("type") == "table" and _is_meta_table(t)]

    narrative = (payload.get("_narrative") or "").strip()
    if not narrative:
        # HTTP responses omit _narrative; infer from first table or metadata
        for t in data:
            cols = t.get("columns") or []
            if cols == ["answer"] and t.get("data"):
                narrative = str(t["data"][0].get("answer", ""))
                break
            if cols == ["Summary"] and t.get("data"):
                narrative = str(t["data"][0].get("Summary", ""))
                break

    weak = not narrative or len(narrative) < 15
    infra = "infrastructure" in narrative.lower() or "mcp_server" in narrative.lower()

    if meta_tables:
        return False, f"meta/infrastructure table(s): {[t.get('columns') for t in meta_tables]}", rows
    if infra:
        return False, "narrative describes infrastructure only", rows
    if rows > 0 and not meta_tables:
        preview = narrative[:160] if narrative else f"{rows} data row(s) in {len(data)} table(s)"
        return True, preview, rows
    if expect_data and rows == 0 and weak:
        return False, "no data rows and empty/weak answer", rows
    if weak:
        return False, f"weak answer: {narrative[:120]!r}", rows
    return True, narrative[:160], rows


def _run_direct(question: str) -> Dict[str, Any]:
    from demos.twa_adapter import _try_direct_from_route, kgqa_result_to_marie
    from mini_marie.kgqa.mcp_router import route_question

    route = route_question(question)
    kgqa = _try_direct_from_route(question, route)
    if not kgqa:
        raise RuntimeError("direct workflow path returned None")
    payload = kgqa_result_to_marie(kgqa)
    payload["_narrative"] = payload.pop("_narrative", "")
    return payload


async def _run_llm(question: str) -> Dict[str, Any]:
    from demos.twa_adapter import run_marie_qa

    payload = await run_marie_qa(question, qa_domain="marie", recursion_limit=80)
    return payload


def _run_http(question: str, base_url: str, timeout: int) -> Dict[str, Any]:
    body = json.dumps({"question": question}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/demos/marie/api/qa",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _check_route(entry) -> tuple[bool, str]:
    from mini_marie.kgqa.mcp_router import route_question

    route = route_question(entry.question)
    if route.domain == "catalog" and route.mcp_servers == ["kg-catalog"]:
        return False, "routes to kg-catalog only"
    if not any(s.startswith("chemistry-") or s in ("twa-mops", "mof-twa") for s in route.mcp_servers):
        return False, f"unexpected servers: {route.mcp_servers}"
    return True, f"route OK → {route.mcp_servers}"


def run_tests(*, use_http: bool, use_llm: bool, base_url: str, llm_timeout: int) -> List[QuestionResult]:
    results: List[QuestionResult] = []
    questions = _load_questions()

    for entry in questions:
        if use_http and not use_llm and not entry.workflow_id:
            ok, detail = _check_route(entry)
            results.append(
                QuestionResult(
                    entry.id,
                    entry.question,
                    "route-only",
                    ok,
                    detail + " (skipped HTTP — no workflow_id; use --llm)",
                    0,
                    0,
                    entry.workflow_id,
                )
            )
            continue

        t0 = time.perf_counter()
        mq = entry.id
        q = entry.question
        wf = entry.workflow_id

        try:
            if use_http:
                payload = _run_http(q, base_url, timeout=llm_timeout if use_llm or not wf else 30)
                ok, detail, rows = _evaluate_payload(payload, expect_data=True)
                results.append(
                    QuestionResult(mq, q, "http", ok, detail, int((time.perf_counter() - t0) * 1000), rows, wf)
                )
                continue

            if wf:
                payload = _run_direct(q)
                ok, detail, rows = _evaluate_payload(payload, expect_data=True)
                results.append(
                    QuestionResult(mq, q, "direct", ok, detail, int((time.perf_counter() - t0) * 1000), rows, wf)
                )
                continue

            if use_llm:
                payload = asyncio.run(_run_llm(q))
                ok, detail, rows = _evaluate_payload(payload, expect_data=True)
                results.append(
                    QuestionResult(mq, q, "llm", ok, detail, int((time.perf_counter() - t0) * 1000), rows, wf)
                )
                continue

            ok, detail = _check_route(entry)
            results.append(
                QuestionResult(
                    mq,
                    q,
                    "route-only",
                    ok,
                    detail + " (no workflow_id — use --llm to execute)",
                    int((time.perf_counter() - t0) * 1000),
                    0,
                    wf,
                )
            )
        except Exception as exc:
            results.append(
                QuestionResult(
                    mq,
                    q,
                    wf and "direct" or ("llm" if use_llm else "route-only"),
                    False,
                    f"{type(exc).__name__}: {exc}",
                    int((time.perf_counter() - t0) * 1000),
                    0,
                    wf,
                )
            )

    return results


def _print_report(results: List[QuestionResult]) -> int:
    passed = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]

    print(f"\nMarie page questions: {len(results)} total, {len(passed)} passed, {len(failed)} failed\n")
    print(f"{'ID':<6} {'Mode':<10} {'ms':>6}  {'Rows':>4}  Status")
    print("-" * 90)
    for r in results:
        mark = "OK" if r.ok else "FAIL"
        q_short = r.question[:55] + ("…" if len(r.question) > 55 else "")
        print(f"{r.mq_id:<6} {r.mode:<10} {r.elapsed_ms:>6}  {r.data_rows:>4}  [{mark}] {q_short}")
        if not r.ok:
            print(f"       → {r.detail}")

    if failed:
        print(f"\nFailed: {', '.join(r.mq_id for r in failed)}")
        return 1
    print("\nAll checks passed.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Backend test for Marie homepage questions")
    parser.add_argument("--http", action="store_true", help="Call running demo server HTTP API")
    parser.add_argument("--llm", action="store_true", help="Run LLM agent for questions without direct workflow")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080", help="Demo server base URL (--http)")
    parser.add_argument("--llm-timeout", type=int, default=120, help="Per-question timeout seconds")
    args = parser.parse_args()

    results = run_tests(
        use_http=args.http,
        use_llm=args.llm,
        base_url=args.base_url,
        llm_timeout=args.llm_timeout,
    )
    raise SystemExit(_print_report(results))


if __name__ == "__main__":
    main()
