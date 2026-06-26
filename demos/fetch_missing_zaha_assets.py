"""Download missing Zaha static assets referenced by mirrored HTML/CSS."""
from __future__ import annotations

import re
import ssl
import urllib.request
from pathlib import Path

BASE = "https://theworldavatar.io"
UA = "curl/8.0"
CTX = ssl.create_default_context()
ROOT = Path(__file__).resolve().parent / "static" / "zaha"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120, context=CTX) as resp:
        return resp.read()


def _collect_asset_paths() -> set[str]:
    paths: set[str] = set()
    for html in ROOT.rglob("*.html"):
        text = html.read_text(encoding="utf-8", errors="replace")
        for match in re.findall(r'(?:href|src)="(\./static/[^"]+)"', text):
            paths.add(match.removeprefix("./"))

    for css in ROOT.rglob("*.css"):
        text = css.read_text(encoding="utf-8", errors="replace")
        for match in re.findall(r"url\((['\"]?)(\.\./img/[^)'\"]+)\1\)", text):
            rel = "static/" + match[1].removeprefix("../")
            paths.add(rel)

    return paths


def main() -> None:
    paths = _collect_asset_paths()
    missing = sorted(p for p in paths if not (ROOT / p).is_file())
    print(f"referenced {len(paths)} assets, missing {len(missing)}")
    for rel in missing:
        url = f"{BASE}/demos/zaha/{rel}"
        dest = ROOT / rel
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(_get(url))
            print("  fetched", rel)
        except Exception as exc:
            print("  skip", rel, exc)


if __name__ == "__main__":
    main()
