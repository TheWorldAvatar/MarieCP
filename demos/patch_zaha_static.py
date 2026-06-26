"""Patch mirrored Zaha HTML for offline/local serving (no Cloudflare Rocket Loader)."""

from __future__ import annotations

import re
from pathlib import Path

ZAHA_ROOT = Path(__file__).resolve().parent / "static" / "zaha"

# Cloudflare Rocket Loader rewrites script types; restore executable JS.
_CF_SCRIPT_TYPE = re.compile(r'type="[a-f0-9]+-text/javascript"')

# Cloudflare wraps inline handlers so they no-op without __cfRLUnblockHandlers.
_CF_ONCLICK_GUARD = re.compile(
    r"if \(!window\.__cfRLUnblockHandlers\) return false;\s*",
    re.I,
)
_CF_DATA_ATTR = re.compile(r"\s*data-cf-modified-[a-f0-9-]+=\"\"")


def patch_html(text: str) -> str:
    text = _CF_SCRIPT_TYPE.sub('type="text/javascript"', text)
    text = _CF_ONCLICK_GUARD.sub("", text)
    text = _CF_DATA_ATTR.sub("", text)
    text = re.sub(r"\s*onclick=\"\s*\"", "", text)

    # Drop Cloudflare rocket-loader and challenge iframe bootstrap.
    text = re.sub(
        r'<script[^>]*src="/cdn-cgi/scripts/[^"]*rocket-loader[^"]*"[^>]*></script>',
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"<script>\(function\(\)\{function c\(\).*?</script>\s*",
        "",
        text,
        flags=re.S,
    )
    return text


def patch_all(root: Path = ZAHA_ROOT) -> int:
    count = 0
    for html in root.rglob("*.html"):
        original = html.read_text(encoding="utf-8", errors="replace")
        patched = patch_html(original)
        if patched != original:
            html.write_text(patched, encoding="utf-8")
            count += 1
            print(f"patched {html.relative_to(root)}")
    return count


if __name__ == "__main__":
    n = patch_all()
    print(f"Patched {n} file(s) under {ZAHA_ROOT}")
