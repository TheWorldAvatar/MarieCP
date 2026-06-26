"""Mine Marie Next.js bundles for API endpoint hints."""
from __future__ import annotations

import json
import re
import ssl
import urllib.request
from pathlib import Path

BASE = "https://theworldavatar.io"
UA = {"User-Agent": "curl/8.0"}
CTX = ssl.create_default_context()


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
        return r.read().decode("utf-8", errors="replace")


def main() -> None:
    html = fetch(f"{BASE}/demos/marie")
    chunks = sorted(set(re.findall(r'/demos/marie/_next/static/chunks/[^"\']+\.js', html)))
    css = sorted(set(re.findall(r'/demos/marie/_next/static/css/[^"\']+\.css', html)))
    media = sorted(set(re.findall(r'/demos/marie/_next/static/media/[^"\']+', html)))
    text = html
    for c in chunks:
        try:
            text += fetch(BASE + c)
        except Exception as exc:
            print("skip", c, exc)

    patterns = {
        "chemistry": r"/chemistry/[a-zA-Z0-9_./-]+",
        "marie_api": r"/demos/marie/api/[a-zA-Z0-9_./-]+",
        "marie_paths": r"/demos/marie/[a-zA-Z0-9_./-]+",
        "env": r"NEXT_PUBLIC_[A-Z0-9_]+",
        "urls": r"https?://[a-zA-Z0-9._/-]+",
    }
    report = {k: sorted(set(re.findall(pat, text, re.I))) for k, pat in patterns.items()}
    report["chunks"] = chunks
    report["css"] = css
    report["media"] = media

    out = Path("data/marie_js_mine.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for k in ("chemistry", "marie_api", "env"):
        print(k, len(report[k]))
        for h in report[k][:15]:
            print(" ", h)


if __name__ == "__main__":
    main()
