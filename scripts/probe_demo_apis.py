"""Probe live Marie and Zaha demo API contracts."""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request

BASE = "https://theworldavatar.io"
UA = {"User-Agent": "curl/8.0", "Content-Type": "application/json", "Accept": "application/json"}
CTX = ssl.create_default_context()


def post(url: str, payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=UA, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            body = r.read()
            ctype = r.headers.get("Content-Type", "")
            if "json" in ctype:
                return {"status": r.status, "json": json.loads(body)}
            return {"status": r.status, "text": body[:500].decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            detail = json.loads(body)
        except json.JSONDecodeError:
            detail = body[:500].decode("utf-8", errors="replace")
        return {"status": e.code, "error": detail}


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            body = r.read()
            return {"status": r.status, "size": len(body), "ctype": r.headers.get("Content-Type")}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "size": len(e.read())}


def main() -> None:
    q_zaha = "How many office buildings are there?"
    q_marie = "Show me all species with molecular formula C6H8O6"

    report = {
        "zaha_qa": post(f"{BASE}/demos/zaha/qa", {"question": q_zaha, "qa_domain": "singapore"}),
        "zaha_get_qa": get(f"{BASE}/demos/zaha/qa"),
        "marie_api_ask": post(f"{BASE}/demos/marie/api/ask", {"question": q_marie}),
        "marie_api_query": post(f"{BASE}/demos/marie/api/query", {"query": q_marie}),
        "chemistry_marie_query": post(f"{BASE}/chemistry/marie/query", {"question": q_marie}),
        "chemistry_agent_query": post(f"{BASE}/chemistry/marie-agent/query", {"question": q_marie}),
    }
    print(json.dumps(report, indent=2)[:8000])


if __name__ == "__main__":
    main()
