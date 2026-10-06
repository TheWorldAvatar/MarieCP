"""Ensure MOP competency assets exist for Marie classic (not Zaha).

Historically this module overwrote ``demos/static/zaha/index.html`` with the
Marie classic page whenever MOP markers were present — that made /demos/zaha/
serve Marie. MOP sample questions belong on Marie only.
"""

from __future__ import annotations

import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE_JSON = REPO / "demos" / "mop_competency_questions.json"
MOP_JS_SRC = REPO / "demos" / "marie-classic" / "static" / "js" / "mop_questions.js"
MARIE_ROOT = REPO / "demos" / "marie-classic"
ZAHA_ROOT = REPO / "demos" / "static" / "zaha"


def _ensure_data_json() -> None:
    if not SOURCE_JSON.is_file():
        raise FileNotFoundError(SOURCE_JSON)
    for dest_dir in (
        MARIE_ROOT / "static" / "data",
        ZAHA_ROOT / "static" / "data",
    ):
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE_JSON, dest_dir / "mop_competency_questions.json")


def _ensure_js() -> None:
    if not MOP_JS_SRC.is_file():
        raise FileNotFoundError(MOP_JS_SRC)
    for dest in (
        MARIE_ROOT / "static" / "js" / "mop_questions.js",
        ZAHA_ROOT / "static" / "js" / "mop_questions.js",
    ):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MOP_JS_SRC, dest)


def patch_all(root: Path = ZAHA_ROOT) -> int:
    """Sync MOP JSON/JS assets only — never rewrite Zaha HTML from Marie."""
    del root  # kept for call-site compatibility with patch_zaha_static
    _ensure_data_json()
    _ensure_js()
    return 0


if __name__ == "__main__":
    n = patch_all()
    print(f"MOP asset sync complete (html_rewrites={n})")
