"""Patch vendor/RAG UI for local Elisa demo (portrait + branding)."""

from __future__ import annotations

import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAG_ROOT = REPO / "vendor" / "RAG"
PORTRAIT_SRC = REPO / "demos" / "hub" / "portraits" / "elisa.png"

ELISA_BRANCH = (
    '        {% elif name == "elisa" %}\n'
    '        <img style="width: 175px; height: 250px; box-shadow: none; object-fit: cover;" '
    'src="./static/img/elisa.png" alt="Elisabeth Selbert" />'
)


def patch_qa_template(*, rag_root: Path) -> None:
    qa = rag_root / "html_templates" / "qa.html"
    if not qa.is_file():
        raise FileNotFoundError(qa)
    text = qa.read_text(encoding="utf-8")
    if 'name == "elisa"' not in text:
        needle = (
            '        {% elif name == "zaha" %}\n'
            '        <img style="width: 175px; height: 250px; box-shadow: none; object-fit: cover;" '
            'src="./static/img/zaha.png" />'
        )
        if needle not in text:
            raise RuntimeError("Unexpected qa.html layout in vendor/RAG")
        text = text.replace(needle, needle + "\n" + ELISA_BRANCH)
    text = text.replace("{{ title }}'s response", "Antwort")
    qa.write_text(text, encoding="utf-8")


def install_portrait(*, rag_root: Path) -> None:
    if not PORTRAIT_SRC.is_file():
        raise FileNotFoundError(PORTRAIT_SRC)
    dest = rag_root / "static" / "img" / "elisa.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PORTRAIT_SRC, dest)


def patch_app_py(*, rag_root: Path) -> None:
    app_py = rag_root / "app.py"
    text = app_py.read_text(encoding="utf-8")
    text = text.replace('"title": "RAG-System"', '"title": "Elisa"')
    text = text.replace('"name": "replace_me_name"', '"name": "elisa"')
    if 'TemplateResponse(\n        "qa.html",' in text:
        text = text.replace(
            '    return app.html_templates.TemplateResponse(\n        "qa.html",\n        {\n            "request": request,',
            '    return app.html_templates.TemplateResponse(\n        request,\n        "qa.html",\n        {',
        )
    if "RAG_UI_ONLY" not in text:
        old = (
            "@asynccontextmanager\n"
            "async def lifespan(r: RAGApp):\n"
            '    """\n'
            "    Context manager to ensure initialisation of hybrid RAG system.\n"
            '    """\n'
            "    r.rag = HybridRAG(r.config)\n"
            "    yield"
        )
        new = (
            "def _ui_only() -> bool:\n"
            "    import os\n\n"
            '    return os.environ.get("RAG_UI_ONLY", "true").strip().lower() not in (\n'
            '        "0",\n'
            '        "false",\n'
            '        "no",\n'
            '        "off",\n'
            "    )\n\n\n"
            "@asynccontextmanager\n"
            "async def lifespan(r: RAGApp):\n"
            '    """\n'
            "    Context manager to ensure initialisation of hybrid RAG system.\n"
            '    """\n'
            "    if _ui_only():\n"
            '        log_msg("RAG_UI_ONLY: serving frontend without HybridRAG backend")\n'
            "        r.rag = None\n"
            "    else:\n"
            "        r.rag = HybridRAG(r.config)\n"
            "    yield"
        )
        if old not in text:
            raise RuntimeError("Unexpected app.py layout in vendor/RAG")
        text = text.replace(old, new)
    if "Backend nicht verfügbar" not in text:
        old_query = """    if (question == "") or (app.rag is None):
        answer = ""
        sources = """
        new_query = """    if question == "":
        answer = ""
        sources = ""
    elif app.rag is None:
        answer = (
            "Backend nicht verfügbar. Starten Sie den TWA-Stack (Blazegraph unter "
            "localhost:3838) und setzen Sie RAG_UI_ONLY=false."
        )
        sources = """
        text = text.replace(old_query, new_query)
    app_py.write_text(text, encoding="utf-8")


def patch_rag_frontend(*, rag_root: Path | None = None) -> None:
    root = rag_root or RAG_ROOT
    if not (root / "app.py").is_file():
        raise FileNotFoundError(root)
    install_portrait(rag_root=root)
    patch_qa_template(rag_root=root)
    patch_app_py(rag_root=root)
    print(f"Patched Elisa UI under {root}")


def main() -> None:
    patch_rag_frontend()


if __name__ == "__main__":
    main()
