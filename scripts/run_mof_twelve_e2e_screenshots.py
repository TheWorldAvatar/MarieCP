"""
Spin up demo server (if needed), run 12 MOF questions via Marie API, write HTML report, capture screenshots.

Outputs:
  docs/MOF_TWELVE_E2E_REPORT.html
  docs/screenshots/mof_twelve/*.png

Usage (repo root):
  python scripts/run_mof_twelve_e2e_screenshots.py
  python scripts/run_mof_twelve_e2e_screenshots.py --skip-agent   # API only if server up
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dotenv import load_dotenv

load_dotenv(REPO / ".env")
from demos.demo_env import load_demo_env  # noqa: E402

load_demo_env()

from demos.kg_row_narrative import is_weak_tool_summary  # noqa: E402
from demos.test_kg_row_narrative import CANONICAL_DEMO_TWELVE  # noqa: E402

OUT_DIR = REPO / "docs" / "screenshots" / "mof_twelve"
REPORT_HTML = REPO / "docs" / "MOF_TWELVE_E2E_REPORT.html"
DEFAULT_PORT = int(os.environ.get("DEMO_PORT", "8080"))
BASE = f"http://127.0.0.1:{DEFAULT_PORT}"


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return True
    except OSError:
        return False


def _wait_port(port: int, timeout_s: float = 60) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _port_open(port):
            return True
        time.sleep(0.5)
    return False


def ensure_server(port: int = DEFAULT_PORT) -> subprocess.Popen | None:
    if _port_open(port):
        print(f"Server already listening on {port}")
        return None
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO)
    env.setdefault("DEMO_CONFIG", "fullstack")
    env["DEMO_PORT"] = str(port)
    env.setdefault("MARIE_FRONTEND_PROXY", "0")
    print(f"Starting demos.server on port {port}...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "demos.server"],
        cwd=str(REPO),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not _wait_port(port, 90):
        proc.kill()
        raise RuntimeError(f"Demo server did not start on port {port}")
    return proc


def _post_qa(question: str, timeout_s: int) -> dict:
    body = json.dumps({"question": question, "qa_domain": "marie"}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/demos/marie/api/qa",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def _post_qa_async(question: str, timeout_s: int) -> dict:
    from demos.twa_adapter import _MARIE_SESSIONS, run_marie_qa

    model = os.environ.get("KGQA_TEST_MODEL", "gpt-4o-mini")
    t0 = time.perf_counter()
    payload = await run_marie_qa(
        question,
        qa_domain="marie",
        model_name=model,
        recursion_limit=80,
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    sid = payload.get("request_id")
    narrative = ((_MARIE_SESSIONS.get(sid) or {}).get("narrative") or "").strip()
    meta = payload.get("metadata") or {}
    bindings = (meta.get("data_request") or {}).get("entity_bindings") or {}
    tools = [v[0] for v in bindings.values() if v]
    rows = sum(
        len(t.get("data") or [])
        for t in (payload.get("data") or [])
        if t.get("type") == "table"
    )
    weak = is_weak_tool_summary(narrative) or len(narrative) < 25
    ok = bool(meta.get("agent_driven")) and narrative and not weak and rows > 0
    return {
        "question": question,
        "ok": ok,
        "elapsed_ms": elapsed_ms,
        "agent_driven": meta.get("agent_driven"),
        "tools": tools,
        "table_rows": rows,
        "narrative": narrative,
        "detail": "" if ok else f"weak={weak} rows={rows} agent={meta.get('agent_driven')}",
    }


async def run_twelve_agent(*, per_question_timeout: int) -> list[dict]:
    has_key = bool(
        os.environ.get("REMOTE_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("AZURE_OPENAI_API_KEY")
    )
    if not has_key:
        raise SystemExit("REMOTE_API_KEY or OPENAI_API_KEY required for agent E2E")

    results: list[dict] = []
    for i, q in enumerate(CANONICAL_DEMO_TWELVE, 1):
        print(f"[{i}/12] {q[:70]}…")
        try:
            row = await _post_qa_async(q, per_question_timeout)
        except Exception as exc:
            row = {
                "question": q,
                "ok": False,
                "elapsed_ms": 0,
                "detail": f"{type(exc).__name__}: {exc}",
                "narrative": "",
                "tools": [],
                "table_rows": 0,
            }
        results.append(row)
        mark = "OK" if row.get("ok") else "FAIL"
        print(f"  -> {mark} {row.get('elapsed_ms')}ms")
    return results


def run_twelve_http(*, per_question_timeout: int) -> list[dict]:
    results: list[dict] = []
    for i, q in enumerate(CANONICAL_DEMO_TWELVE, 1):
        print(f"[{i}/12] HTTP {q[:60]}…")
        t0 = time.perf_counter()
        try:
            payload = _post_qa(q, per_question_timeout)
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            meta = payload.get("metadata") or {}
            data = payload.get("data") or []
            narrative = (payload.get("narrative") or "").strip()
            if not narrative:
                for t in data:
                    if t.get("columns") == ["Summary"] and t.get("data"):
                        narrative = str(t["data"][0].get("Summary", "")).strip()
                        break
            rows = sum(len(t.get("data") or []) for t in data if t.get("type") == "table")
            weak = is_weak_tool_summary(narrative) or len(narrative) < 25
            ok = (
                bool(meta.get("agent_driven"))
                and narrative
                and not weak
                and rows > 0
            )
            row = {
                "question": q,
                "ok": ok,
                "elapsed_ms": elapsed_ms,
                "agent_driven": meta.get("agent_driven"),
                "tools": [],
                "table_rows": rows,
                "narrative": narrative,
                "detail": "" if ok else "weak or empty",
            }
        except Exception as exc:
            row = {
                "question": q,
                "ok": False,
                "elapsed_ms": 0,
                "detail": str(exc),
                "narrative": "",
                "tools": [],
                "table_rows": 0,
            }
        results.append(row)
        print(f"  -> {'OK' if row['ok'] else 'FAIL'}")
    return results


def write_html_report(results: list[dict]) -> None:
    passed = sum(1 for r in results if r.get("ok"))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        "<title>MOF twelve E2E</title>",
        "<style>body{font-family:system-ui;max-width:960px;margin:24px auto;padding:0 16px}",
        "h1{font-size:1.4rem}.ok{color:#0a0}.fail{color:#c00}.q{margin-top:1.5rem;border-top:1px solid #ddd;padding-top:12px}",
        "pre{white-space:pre-wrap;background:#f6f6f6;padding:12px;font-size:13px}</style></head><body>",
        f"<h1>Marie MOF — 12 question E2E</h1>",
        f"<p>Generated {ts} · <strong>{passed}/12</strong> passed · Base URL: {html.escape(BASE)}</p>",
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;width:100%'>",
        "<tr><th>#</th><th>Status</th><th>ms</th><th>Rows</th><th>Question</th></tr>",
    ]
    for i, r in enumerate(results, 1):
        st = "OK" if r.get("ok") else "FAIL"
        cls = "ok" if r.get("ok") else "fail"
        parts.append(
            f"<tr><td>{i}</td><td class='{cls}'>{st}</td><td>{r.get('elapsed_ms', 0)}</td>"
            f"<td>{r.get('table_rows', 0)}</td><td>{html.escape(r['question'][:100])}</td></tr>"
        )
    parts.append("</table>")
    for i, r in enumerate(results, 1):
        parts.append(f"<div class='q'><h2>{i}. {html.escape(r['question'])}</h2>")
        parts.append(f"<p class='{'ok' if r.get('ok') else 'fail'}'>{'PASS' if r.get('ok') else 'FAIL'} — "
                     f"{r.get('elapsed_ms', 0)} ms · tools: {html.escape(', '.join(r.get('tools') or []))}</p>")
        parts.append(f"<pre>{html.escape((r.get('narrative') or r.get('detail') or '')[:2000])}</pre></div>")
    parts.append("</body></html>")
    REPORT_HTML.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {REPORT_HTML}")


def capture_screenshots(*, ui_sample: bool) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Install Playwright: pip install playwright && python -m playwright install chromium"
        ) from exc

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    marie_url = f"{BASE}/demos/marie-classic/"
    report_url = REPORT_HTML.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        print("Screenshot: Marie Classic (MOF section)…")
        page.goto(marie_url, wait_until="networkidle", timeout=120_000)
        page.locator("text=MOF").first.scroll_into_view_if_needed(timeout=30_000)
        page.screenshot(path=str(OUT_DIR / "01_marie_classic_mof_questions.png"), full_page=True)

        print("Screenshot: E2E HTML report…")
        page.goto(report_url, wait_until="load", timeout=60_000)
        page.screenshot(path=str(OUT_DIR / "02_twelve_e2e_report.png"), full_page=True)

        if ui_sample:
            sample_q = CANONICAL_DEMO_TWELVE[-1]
            print(f"Screenshot: UI answer (Q12 count)…")
            page.goto(marie_url, wait_until="domcontentloaded", timeout=120_000)
            page.fill("#input-field", sample_q)
            try:
                with page.expect_response(
                    lambda r: "/qa" in r.url and r.request.method == "POST",
                    timeout=180_000,
                ):
                    page.evaluate("askQuestion()")
                page.wait_for_selector("#result-section", state="visible", timeout=30_000)
                page.wait_for_selector(
                    "#qa-insight-container .marie-insight-card, #qa-data-container table",
                    timeout=30_000,
                )
                page.wait_for_timeout(1500)
                page.screenshot(path=str(OUT_DIR / "03_ui_sample_marie_answer.png"), full_page=True)
            except Exception as exc:
                print(f"WARNING: UI sample screenshot skipped: {exc}")
                page.screenshot(path=str(OUT_DIR / "03_ui_sample_error_state.png"), full_page=True)

        browser.close()
    print(f"Screenshots in {OUT_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--skip-server", action="store_true")
    parser.add_argument("--http-only", action="store_true", help="POST via HTTP (server must implement agent path)")
    parser.add_argument("--skip-agent", action="store_true", help="Skip tests; only report + screenshots")
    parser.add_argument("--no-screenshots", action="store_true")
    parser.add_argument("--ui-sample", action="store_true", help="One slow UI screenshot (Q1 via browser)")
    parser.add_argument("--timeout", type=int, default=300, help="Per-question timeout seconds")
    args = parser.parse_args()

    global BASE
    BASE = f"http://127.0.0.1:{args.port}"

    proc = None
    if not args.skip_server:
        proc = ensure_server(args.port)

    results: list[dict] = []
    try:
        if not args.skip_agent:
            if args.http_only:
                results = run_twelve_http(per_question_timeout=args.timeout)
            else:
                results = asyncio.run(run_twelve_agent(per_question_timeout=args.timeout))
            write_html_report(results)
        elif REPORT_HTML.is_file():
            print(f"Using existing {REPORT_HTML}")
        else:
            raise SystemExit("--skip-agent but no report HTML found")

        if not args.no_screenshots:
            capture_screenshots(ui_sample=args.ui_sample)
    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=10)

    if results:
        passed = sum(1 for r in results if r.get("ok"))
        raise SystemExit(0 if passed == len(CANONICAL_DEMO_TWELVE) else 1)


if __name__ == "__main__":
    main()
