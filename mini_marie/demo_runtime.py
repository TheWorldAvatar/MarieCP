"""Demo server runtime policy (cache + offline replay)."""

from __future__ import annotations

import os

_FALSE = frozenset({"0", "false", "no", "off"})


def _env_enabled(name: str, *, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() not in _FALSE


def demo_auto_offline() -> bool:
    """After online probe, replay full-tier results from SQLite (no live SPARQL)."""
    return _env_enabled("DEMO_AUTO_OFFLINE", default="true")


def demo_force_refresh() -> bool:
    """When True, bypass SQLite reads on online steps (cold SPARQL every time)."""
    return _env_enabled("DEMO_FORCE_REFRESH", default="false")


def demo_use_cache() -> bool:
    """Use warmed SQLite on each workflow/competency step."""
    return not demo_force_refresh()
