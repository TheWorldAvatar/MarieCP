"""Backend smoke test: Zaha homepage questions → POST /demos/zaha/qa/ shape.

Default mode checks Singapore routing (qa_domain=singapore) for all sample
questions from the mirrored static page. Use --llm or --http to execute answers.

Run from repo root:
  python -m demos.test_zaha_page_questions
  python -m demos.test_zaha_page_questions --llm
  python -m demos.test_zaha_page_questions --http
  python -m demos.test_zaha_page_questions --llm --limit 3
"""

from __future__ import annotations

import argparse
import asyncio
import html as html_module
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

QA_DOMAIN = "singapore"
_ZAHA_HTML = REPO / "demos" / "static" / "zaha" / "index.html"
# sg-old has no public air-pollution timeseries; agent may explain infrastructure gap.
_KNOWN_HTTP_LIMITATIONS = frozenset({"ZQ15"})


@dataclass
class QuestionResult:
    zq_id: str
    question: str
    mode: str
    ok: bool
    detail: str
    elapsed_ms: int
    data_rows: int = 0
    steps: int = 0


def _load_questions() -> List[tuple[str, str]]:
    if not _ZAHA_HTML.exists():
        raise FileNotFoundError(f"Zaha static mirror missing: {_ZAHA_HTML}")

    text = html_module.unescape(_ZAHA_HTML.read_text(encoding="utf-8"))
    pattern = re.compile(r'populateInputText\("([^"]+)"\)')
    seen: set[str] = set()
    out: List[tuple[str, str]] = []
    for idx, match in enumerate(pattern.finditer(text), 1):
        question = html_module.unescape(match.group(1)).strip()
        if not question or question in seen:
            continue
        seen.add(question)
        out.append((f"ZQ{idx:02d}", question))
    return out


def _table_rows(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    if item.get("type") != "table":
        return []
    return list(item.get("bindings") or item.get("data") or [])


def _evaluate_twa_payload(payload: Dict[str, Any], *, expect_data: bool) -> tuple[bool, str, int, int]:
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
        return False, "narrative describes infrastructure only", rows, steps
    if rows > 0:
        preview = narrative[:160] if narrative else f"{rows} data row(s) in {len(data)} item(s)"
        return True, preview, rows, steps
    if expect_data and rows == 0 and weak:
        return False, "no data rows and empty/weak answer", rows, steps
    if weak:
        return False, f"weak answer: {narrative[:120]!r}", rows, steps
    return True, narrative[:160], rows, steps


async def _run_llm(question: str, timeout_hint: int) -> Dict[str, Any]:
    from demos.twa_adapter import run_twa_qa

    return await run_twa_qa(question, qa_domain=QA_DOMAIN, recursion_limit=80)


def _run_http(question: str, base_url: str, timeout: int) -> Dict[str, Any]:
    body = json.dumps({"question": question, "qa_domain": QA_DOMAIN}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/demos/zaha/qa/",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _check_route(question: str) -> tuple[bool, str]:
    from demos.twa_adapter import route_for_qa_domain

    route = route_for_qa_domain(question, QA_DOMAIN)
    # Unified routing: Zaha UI hint is soft; chemistry/MOF questions may leave sg domain.
    if route.domain == "sg":
        if "sg-old" not in route.mcp_servers:
            return False, f"expected sg-old in servers, got {route.mcp_servers}"
        return True, f"route OK → {route.mcp_servers}"
    if route.domain in {"chemistry", "mof", "city"}:
        return True, f"unified route → domain={route.domain} servers={route.mcp_servers}"
    return False, f"unexpected domain {route.domain!r}"


def run_tests(
    *,
    use_http: bool,
    use_llm: bool,
    base_url: str,
    llm_timeout: int,
    limit: Optional[int],
) -> List[QuestionResult]:
    results: List[QuestionResult] = []
    questions = _load_questions()
    if limit is not None:
        questions = questions[:limit]

    for zq_id, question in questions:
        t0 = time.perf_counter()
        try:
            if use_http or use_llm:
                if use_http:
                    payload = _run_http(question, base_url, timeout=llm_timeout)
                    mode = "http"
                else:
                    payload = asyncio.run(_run_llm(question, llm_timeout))
                    mode = "llm"

                ok, detail, rows, steps = _evaluate_twa_payload(payload, expect_data=True)
                if not ok and zq_id in _KNOWN_HTTP_LIMITATIONS:
                    ok = True
                    detail = f"known limitation (accepted): {detail}"
                results.append(
                    QuestionResult(
                        zq_id,
                        question,
                        mode,
                        ok,
                        detail,
                        int((time.perf_counter() - t0) * 1000),
                        rows,
                        steps,
                    )
                )
                continue

            ok, detail = _check_route(question)
            results.append(
                QuestionResult(
                    zq_id,
                    question,
                    "route-only",
                    ok,
                    detail + (" (use --llm or --http to execute)" if ok else ""),
                    int((time.perf_counter() - t0) * 1000),
                    0,
                    0,
                )
            )
        except Exception as exc:
            mode = "http" if use_http else ("llm" if use_llm else "route-only")
            results.append(
                QuestionResult(
                    zq_id,
                    question,
                    mode,
                    False,
                    f"{type(exc).__name__}: {exc}",
                    int((time.perf_counter() - t0) * 1000),
                    0,
                    0,
                )
            )

    return results


def _print_report(results: List[QuestionResult]) -> int:
    passed = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]

    print(f"\nZaha page questions: {len(results)} total, {len(passed)} passed, {len(failed)} failed\n")
    print(f"{'ID':<6} {'Mode':<10} {'ms':>6}  {'Rows':>4}  {'Steps':>5}  Status")
    print("-" * 96)
    for r in results:
        mark = "OK" if r.ok else "FAIL"
        q_short = r.question[:50] + ("…" if len(r.question) > 50 else "")
        print(
            f"{r.zq_id:<6} {r.mode:<10} {r.elapsed_ms:>6}  {r.data_rows:>4}  {r.steps:>5}  "
            f"[{mark}] {q_short}"
        )
        if not r.ok:
            print(f"       -> {r.detail}")

    if failed:
        print(f"\nFailed: {', '.join(r.zq_id for r in failed)}")
        return 1
    print("\nAll checks passed.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Backend test for Zaha homepage questions")
    parser.add_argument("--http", action="store_true", help="Call running demo server HTTP API")
    parser.add_argument("--llm", action="store_true", help="Run KGQA agent for each question")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080", help="Demo server base URL (--http)")
    parser.add_argument("--llm-timeout", type=int, default=120, help="Per-question timeout seconds")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N questions")
    args = parser.parse_args()

    if args.http and args.llm:
        parser.error("Use either --http or --llm, not both")

    results = run_tests(
        use_http=args.http,
        use_llm=args.llm,
        base_url=args.base_url,
        llm_timeout=args.llm_timeout,
        limit=args.limit,
    )
    raise SystemExit(_print_report(results))


if __name__ == "__main__":
    main()
