"""Inject MOP polyhedra competency section into mirrored Zaha index.html."""

from __future__ import annotations

import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE_JSON = REPO / "demos" / "mop_competency_questions.json"
MOP_JS_SRC = REPO / "demos" / "marie-classic" / "static" / "js" / "mop_questions.js"
ZAHA_ROOT = REPO / "demos" / "static" / "zaha"
MARKER = "<!-- mop-competency -->"


def _ensure_data_json(root: Path = ZAHA_ROOT) -> None:
    if not SOURCE_JSON.is_file():
        raise FileNotFoundError(SOURCE_JSON)
    for dest_dir in (
        root / "static" / "data",
        REPO / "demos" / "marie-classic" / "static" / "data",
    ):
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE_JSON, dest_dir / "mop_competency_questions.json")


def _ensure_js(root: Path = ZAHA_ROOT) -> None:
    if not MOP_JS_SRC.is_file():
        raise FileNotFoundError(MOP_JS_SRC)
    dest = root / "static" / "js" / "mop_questions.js"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MOP_JS_SRC, dest)


def patch_index_html(root: Path = ZAHA_ROOT) -> bool:
    index = root / "index.html"
    if not index.is_file():
        return False
    text = index.read_text(encoding="utf-8")
    if MARKER in text and "mop_questions.js" in text:
        return False
    return False


def patch_all(root: Path = ZAHA_ROOT) -> int:
    _ensure_data_json(root)
    _ensure_js(root)
    marie_index = REPO / "demos" / "marie-classic" / "index.html"
    zaha_index = root / "index.html"
    if marie_index.is_file() and zaha_index.is_file():
        text = marie_index.read_text(encoding="utf-8")
        if MARKER in text:
            zaha_index.write_text(text, encoding="utf-8")
            return 1
    return 0


if __name__ == "__main__":
    n = patch_all()
    print(f"MOP page patch: {n} file(s)")
