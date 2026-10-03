"""Inject German city competency dropdown into mirrored Zaha index.html."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE_JSON = REPO / "demos" / "german_city_competency_questions.json"
GERMAN_JS_SRC = REPO / "demos" / "marie-classic" / "static" / "js" / "german_city_questions.js"
ZAHA_ROOT = REPO / "demos" / "static" / "zaha"
MARKER = "<!-- german-city-competency -->"

GERMAN_SECTION = """
    <!-- german-city-competency -->
    <button type="submit" class="accordion">German cities (TWA buildings)</button>
    <div class="accordion-panel">
        <p>Validated competency questions for German Ontop city stacks (Bremen, Kaiserslautern, Pirmasens). Select a city, then click a question.</p>
        <div id="german-city-container" style="margin-bottom: 1rem;">
            <label for="german-city-select" style="margin-right: 0.5rem;">City:</label>
            <select id="german-city-select" style="min-width: 14rem; padding: 0.25rem 0.5rem;">
            </select>
        </div>
        <ul id="german-city-question-list"></ul>
    </div>
"""


def _ensure_data_json(root: Path = ZAHA_ROOT) -> None:
    if not SOURCE_JSON.is_file():
        raise FileNotFoundError(SOURCE_JSON)
    for dest_dir in (
        root / "static" / "data",
        REPO / "demos" / "marie-classic" / "static" / "data",
    ):
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE_JSON, dest_dir / "german_city_competency_questions.json")


def _ensure_js(root: Path = ZAHA_ROOT) -> None:
    if not GERMAN_JS_SRC.is_file():
        raise FileNotFoundError(GERMAN_JS_SRC)
    dest = root / "static" / "js" / "german_city_questions.js"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GERMAN_JS_SRC, dest)


def patch_index_html(root: Path = ZAHA_ROOT) -> bool:
    index = root / "index.html"
    if not index.is_file():
        return False
    text = index.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        return False

    # Insert German cities accordion after Singapore panel (before closing </section> of examples).
    anchor = "</div>\n    \n</section>"
    if anchor not in text:
        anchor = "</div>\r\n    \r\n</section>"
    if anchor not in text:
        return False

    text = text.replace(anchor, f"</div>\n    \n{GERMAN_SECTION}\n    \n</section>", 1)

    if "german_city_questions.js" not in text:
        text = re.sub(
            r'(<script src="\./static/js/script\.js"[^>]*></script>)',
            r'<script src="./static/js/german_city_questions.js" type="text/javascript"></script>\n    \1',
            text,
            count=1,
            flags=re.I,
        )

    index.write_text(text, encoding="utf-8")
    return True


def patch_all(root: Path = ZAHA_ROOT) -> int:
    count = 0
    _ensure_data_json(root)
    _ensure_js(root)
    if patch_index_html(root):
        count += 1
        print("  injected German cities section into zaha/index.html")
    return count


if __name__ == "__main__":
    n = patch_all()
    print(f"German city patch: {n} html file(s) updated")
