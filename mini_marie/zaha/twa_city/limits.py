"""Rate-limit settings for TWA city / Pirmasens Ontop SPARQL (online probe + warm)."""

from __future__ import annotations

import os

DEFAULT_ONLINE_SPARQL_DELAY_SECONDS = 3.0


def _parse_delay(raw: str, default: float) -> float:
    if not raw.strip():
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


def online_sparql_delay_seconds() -> float:
    """Pause before remote SPARQL on online (probe tier) cache miss."""
    return _parse_delay(
        os.environ.get("ONLINE_SPARQL_DELAY_SECONDS", ""),
        DEFAULT_ONLINE_SPARQL_DELAY_SECONDS,
    )


def warm_delay_seconds() -> float:
    """Pause between warm-loop remote fetches (WARM_DELAY_SECONDS or online default)."""
    raw = os.environ.get("WARM_DELAY_SECONDS", "")
    if raw.strip():
        return _parse_delay(raw, DEFAULT_ONLINE_SPARQL_DELAY_SECONDS)
    return online_sparql_delay_seconds()
