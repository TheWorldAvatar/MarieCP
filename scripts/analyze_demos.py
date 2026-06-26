"""Quick analysis of Marie and Zaha demo frontends."""
from __future__ import annotations

import json
import re
import ssl
import urllib.request
from pathlib import Path

BASE = "https://theworldavatar.io"
CTX = ssl.create_default_context()
UA = "curl/8.0"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
        return r.read().decode("utf-8", errors="replace")


def analyze_zaha() -> dict:
    html = fetch(f"{BASE}/demos/zaha/")
    js = fetch(f"{BASE}/demos/zaha/static/js/script.js")
    static_refs = sorted(set(re.findall(r'(?:href|src)="(\./static/[^"]+)"', html)))
    api_hits = sorted(set(re.findall(r'["\'](/[^"\']*(?:api|agent|query|chat|stream|zaha)[^"\']*)["\']', js, re.I)))
    url_hits = sorted(set(re.findall(r"https?://[a-zA-Z0-9._/-]+", js)))
    fn_hits = sorted(set(re.findall(r"(?:async )?function (askQuestion|fetch[A-Za-z]+|[a-zA-Z]*Agent[a-zA-Z]*)", js)))
    class_hits = sorted(set(re.findall(r"class ([A-Za-z][A-Za-z0-9_]*)", js)))
    return {
        "static_refs": static_refs[:40],
        "api_hits": api_hits,
        "url_hits": url_hits[:50],
        "functions": fn_hits,
        "classes": class_hits[:30],
        "js_size": len(js),
    }


def analyze_marie() -> dict:
    html = fetch(f"{BASE}/demos/marie")
    build = re.search(r'"buildId":"([^"]+)"', html)
    chunks = sorted(set(re.findall(r"/demos/marie/_next/static/chunks/[^\"']+\.js", html)))
    css = sorted(set(re.findall(r"/demos/marie/_next/static/css/[^\"']+\.css", html)))
    eq = re.search(r'"exampleQuestionGroups":(\[.*?\])\}\]\}', html, re.S)
    groups = json.loads(eq.group(1)) if eq else []
    return {
        "build_id": build.group(1) if build else None,
        "js_chunks": len(chunks),
        "css_files": css,
        "example_groups": len(groups),
        "sample_chunks": chunks[:10],
    }


if __name__ == "__main__":
    out = Path("data/demo_analysis.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {"marie": analyze_marie(), "zaha": analyze_zaha()}
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
