"""Patch mirrored Zaha HTML for offline/local serving (no Cloudflare Rocket Loader)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ZAHA_ROOT = Path(__file__).resolve().parent / "static" / "zaha"
MARIE_CLASSIC_JS = Path(__file__).resolve().parent / "marie-classic" / "static" / "js" / "script.js"

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

    text = re.sub(
        r'<p id="chatbot-response"([^>]*)></p>',
        r'<div id="chatbot-response"\1 class="chatbot-markdown"></div>',
        text,
        flags=re.I,
    )
    text = re.sub(
        r'<p id="chatbot-response"([^>]*)>',
        r'<div id="chatbot-response"\1 class="chatbot-markdown">',
        text,
        flags=re.I,
    )
    text = re.sub(
        r'(<div id="chatbot-response"[^>]*>)\s*</p>',
        r'\1</div>',
        text,
        count=1,
        flags=re.I,
    )

    if "marked.min.js" not in text and "script.js" in text:
        inject = (
            '<script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js" '
            'type="text/javascript"></script>\n'
            '    <script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.6/dist/purify.min.js" '
            'type="text/javascript"></script>\n    '
        )
        text = re.sub(
            r'(<script src="[^"]*script\.js"[^>]*></script>)',
            inject + r"\1",
            text,
            count=1,
            flags=re.I,
        )

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
    count += sync_shared_script(root)
    try:
        from demos.patch_zaha_german_cities import patch_all as patch_german_cities

        count += patch_german_cities(root)
    except Exception as exc:
        print(f"  warn: german city patch skipped: {exc}")
    try:
        from demos.patch_zaha_mop import patch_all as patch_mop

        count += patch_mop(root)
    except Exception as exc:
        print(f"  warn: mop patch skipped: {exc}")
    return count


def sync_shared_script(root: Path = ZAHA_ROOT) -> int:
    """Overlay Marie classic QA script onto mirrored Zaha static (maps, MD chat, embed)."""
    if not MARIE_CLASSIC_JS.is_file():
        return 0
    dest = root / "static" / "js" / "script.js"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MARIE_CLASSIC_JS, dest)
    print(f"  synced shared script.js -> {dest.relative_to(root)}")
    count = 1
    german_js = Path(__file__).resolve().parent / "marie-classic" / "static" / "js" / "german_city_questions.js"
    if german_js.is_file():
        german_dest = root / "static" / "js" / "german_city_questions.js"
        shutil.copy2(german_js, german_dest)
        print(f"  synced german_city_questions.js -> {german_dest.relative_to(root)}")
        count += 1
    mop_js = Path(__file__).resolve().parent / "marie-classic" / "static" / "js" / "mop_questions.js"
    if mop_js.is_file():
        mop_dest = root / "static" / "js" / "mop_questions.js"
        shutil.copy2(mop_js, mop_dest)
        print(f"  synced mop_questions.js -> {mop_dest.relative_to(root)}")
        count += 1
    return count


if __name__ == "__main__":
    n = patch_all()
    print(f"Patched {n} file(s) under {ZAHA_ROOT}")
