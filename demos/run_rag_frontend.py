"""Run the TWA Elisa (Bundestag Q&A) web UI locally (vendor/RAG FastAPI frontend).

Run from repo root:
  python -m demos.setup_rag_frontend --install
  python -m demos.run_rag_frontend
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAG_ROOT = REPO / "vendor" / "RAG"


def _ui_only() -> bool:
    return os.environ.get("RAG_UI_ONLY", "true").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _ensure_rag_root() -> Path:
    if not (RAG_ROOT / "app.py").is_file():
        raise SystemExit(
            "vendor/RAG missing. Run: python -m demos.setup_rag_frontend --install"
        )
    return RAG_ROOT


def main() -> None:
    rag_root = _ensure_rag_root()
    os.chdir(rag_root)
    if str(rag_root) not in sys.path:
        sys.path.insert(0, str(rag_root))
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))

    from dotenv import load_dotenv

    load_dotenv(REPO / ".env", override=False)
    load_dotenv(REPO / "configs" / "demo_local.env", override=False)
    load_dotenv(REPO / "configs" / "rag_hybrid.env.example", override=False)

    from demos.patch_rag_frontend import patch_rag_frontend

    patch_rag_frontend(rag_root=rag_root)

    port = int(os.environ.get("RAG_PORT", "8000"))
    host = os.environ.get("RAG_HOST", "127.0.0.1")
    ui_only = _ui_only()

    print(f"Elisa frontend http://{host}:{port}/")
    print(f"  vendor: {rag_root}")
    print(f"  RAG_UI_ONLY={ui_only} (set false + Blazegraph for live answers)")

    import uvicorn

    uvicorn.run("app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
