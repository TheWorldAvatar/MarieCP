"""Clone and configure the TWA hybrid RAG frontend (qa.theworldavatar.io).

Upstream: https://github.com/TheWorldAvatar/RAG

Run from repo root:
  python -m demos.setup_rag_frontend
  python -m demos.setup_rag_frontend --install   # also pip install into .venv-rag
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAG_ROOT = REPO / "vendor" / "RAG"
RAG_REPO = "https://github.com/TheWorldAvatar/RAG.git"
VENV = REPO / ".venv-rag"
CONFIG_NAME = "config-hybrid.yaml"
ENV_EXAMPLE = REPO / "configs" / "rag_hybrid.env.example"


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def clone_rag(*, force: bool) -> Path:
    if RAG_ROOT.is_dir() and (RAG_ROOT / "app.py").is_file() and not force:
        print(f"RAG repo already present at {RAG_ROOT}")
        return RAG_ROOT
    RAG_ROOT.parent.mkdir(parents=True, exist_ok=True)
    if RAG_ROOT.exists() and force:
        import shutil

        shutil.rmtree(RAG_ROOT)
    _run(["git", "clone", "--depth", "1", RAG_REPO, str(RAG_ROOT)])
    print(f"Cloned {RAG_REPO} -> {RAG_ROOT}")
    return RAG_ROOT


def _load_repo_env() -> dict[str, str]:
    from dotenv import dotenv_values

    merged: dict[str, str] = {}
    for path in (REPO / ".env", REPO / "configs" / "demo_local.env"):
        if path.is_file():
            merged.update({k: v for k, v in (dotenv_values(path) or {}).items() if v})
    return merged


def write_config(*, rag_root: Path) -> Path:
    template = rag_root / "config-template.yaml"
    dest = rag_root / CONFIG_NAME
    if not template.is_file():
        raise FileNotFoundError(template)

    text = template.read_text(encoding="utf-8")
    env = _load_repo_env()
    api_key = (env.get("OPENAI_API_KEY") or env.get("REMOTE_API_KEY") or "").strip()
    if api_key and "OPENAI_API_KEY:" in text:
        lines = []
        for line in text.splitlines():
            if line.startswith("OPENAI_API_KEY:"):
                lines.append(f"OPENAI_API_KEY: {api_key}")
            else:
                lines.append(line)
        text = "\n".join(lines) + "\n"

    dest.write_text(text, encoding="utf-8")
    print(f"Wrote {dest}")
    if not api_key:
        print(
            "WARNING: No OPENAI_API_KEY / REMOTE_API_KEY in .env — "
            "set one before running queries (UI will still load in RAG_UI_ONLY mode)."
        )
    return dest


def install_deps(*, rag_root: Path) -> None:
    if not VENV.is_dir():
        _run([sys.executable, "-m", "venv", str(VENV)])
    py = VENV / "Scripts" / "python.exe"
    if not py.is_file():
        py = VENV / "bin" / "python"
    _run([str(py), "-m", "pip", "install", "-q", "-U", "pip"])
    _run([str(py), "-m", "pip", "install", "-q", "-r", str(rag_root / "requirements.txt")])


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up TWA hybrid RAG frontend locally")
    parser.add_argument("--force-clone", action="store_true", help="Re-clone vendor/RAG")
    parser.add_argument("--install", action="store_true", help="Create .venv-rag and pip install")
    args = parser.parse_args()

    rag_root = clone_rag(force=args.force_clone)
    write_config(rag_root=rag_root)
    from demos.patch_rag_frontend import patch_rag_frontend

    patch_rag_frontend(rag_root=rag_root)
    if args.install:
        install_deps(rag_root=rag_root)

    print()
    print("Next steps:")
    print("  python -m demos.setup_rag_frontend --install   # if not done yet")
    print("  python -m demos.run_rag_frontend")
    print("  Open http://127.0.0.1:8000/")


if __name__ == "__main__":
    main()
