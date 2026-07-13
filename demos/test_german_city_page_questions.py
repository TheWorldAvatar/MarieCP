"""Route smoke test for German city competency questions on Zaha page.

Loads demos/german_city_competency_questions.json and checks each question
routes to twa-city (domain=city) with qa_domain=city hint.

  python -m demos.test_german_city_page_questions
  python -m demos.test_german_city_page_questions --llm --limit 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from demos.demo_env import load_demo_env

REPO = Path(__file__).resolve().parents[1]
load_demo_env()

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

QA_DOMAIN = "city"
_CATALOG = REPO / "demos" / "german_city_competency_questions.json"


@dataclass
class QuestionResult:
    qid: str
    city: str
    question: str
    mode: str
    ok: bool
    detail: str
    elapsed_ms: int


def _load_questions() -> List[tuple[str, str, str]]:
    data = json.loads(_CATALOG.read_text(encoding="utf-8"))
    out: List[tuple[str, str, str]] = []
    for city_key, block in data.items():
        label = block.get("label") or city_key
        for item in block.get("questions") or []:
            qid = str(item.get("id") or "")
            question = str(item.get("question") or "").strip()
            if question:
                out.append((qid, label, question))
    return out


def _check_route(question: str) -> tuple[bool, str]:
    from demos.twa_adapter import route_for_qa_domain

    route = route_for_qa_domain(question, QA_DOMAIN)
    if route.domain == "city" and "twa-city" in route.mcp_servers:
        return True, f"route OK → {route.mcp_servers}"
    if "twa-city" in route.mcp_servers:
        return True, f"route OK (domain={route.domain}) → {route.mcp_servers}"
    return False, f"expected twa-city, got domain={route.domain!r} servers={route.mcp_servers}"


async def _run_llm(question: str) -> Dict[str, Any]:
    from demos.twa_adapter import run_twa_qa

    return await run_twa_qa(question, qa_domain=QA_DOMAIN, recursion_limit=80)


def run_tests(*, use_llm: bool, limit: Optional[int]) -> List[QuestionResult]:
    results: List[QuestionResult] = []
    questions = _load_questions()
    if limit is not None:
        questions = questions[:limit]

    for qid, city, question in questions:
        t0 = time.perf_counter()
        try:
            if use_llm:
                payload = asyncio.run(_run_llm(question))
                narrative = (payload.get("narrative") or "").strip()
                ok = bool(narrative) and len(narrative) >= 15
                detail = narrative[:160] if ok else f"weak answer: {narrative[:120]!r}"
                results.append(
                    QuestionResult(qid, city, question, "llm", ok, detail, int((time.perf_counter() - t0) * 1000))
                )
                continue

            ok, detail = _check_route(question)
            results.append(
                QuestionResult(
                    qid,
                    city,
                    question,
                    "route-only",
                    ok,
                    detail + (" (use --llm to execute)" if ok else ""),
                    int((time.perf_counter() - t0) * 1000),
                )
            )
        except Exception as exc:
            results.append(
                QuestionResult(
                    qid,
                    city,
                    question,
                    "llm" if use_llm else "route-only",
                    False,
                    f"{type(exc).__name__}: {exc}",
                    int((time.perf_counter() - t0) * 1000),
                )
            )
    return results


def _print_report(results: List[QuestionResult]) -> int:
    passed = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    print(f"\nGerman city questions: {len(results)} total, {len(passed)} passed, {len(failed)} failed\n")
    print(f"{'ID':<10} {'City':<14} {'Mode':<10} {'ms':>6}  Status")
    print("-" * 80)
    for r in results:
        mark = "OK" if r.ok else "FAIL"
        q_short = r.question[:42] + ("…" if len(r.question) > 42 else "")
        print(f"{r.qid:<10} {r.city:<14} {r.mode:<10} {r.elapsed_ms:>6}  [{mark}] {q_short}")
        if not r.ok:
            print(f"           -> {r.detail}")
    if failed:
        print(f"\nFailed: {', '.join(r.qid for r in failed)}")
        return 1
    print("\nAll checks passed.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="German city competency questions routing test")
    parser.add_argument("--llm", action="store_true", help="Run KGQA agent for each question")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N questions")
    args = parser.parse_args()

    if not _CATALOG.is_file():
        raise SystemExit(f"Missing catalog: {_CATALOG}")

    results = run_tests(use_llm=args.llm, limit=args.limit)
    raise SystemExit(_print_report(results))


if __name__ == "__main__":
    main()
