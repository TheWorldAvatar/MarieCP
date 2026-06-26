"""Load demo server env (``.env`` + ``configs/demo_<name>.env``)."""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def demo_config_name() -> str:
    return os.environ.get("DEMO_CONFIG", "demo_local").strip() or "demo_local"


def demo_config_path() -> Path:
    return REPO / "configs" / f"{demo_config_name()}.env"


def load_demo_env(*, override: bool = True) -> Path | None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return None
    load_dotenv(REPO / ".env", override=override)
    path = demo_config_path()
    if path.is_file():
        load_dotenv(path, override=override)
    return path if path.is_file() else None
