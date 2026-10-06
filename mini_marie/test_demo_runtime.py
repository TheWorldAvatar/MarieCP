"""Demo cache policy defaults."""

from __future__ import annotations

import os


def test_demo_cache_defaults_without_env(monkeypatch):
    monkeypatch.delenv("DEMO_AUTO_OFFLINE", raising=False)
    monkeypatch.delenv("DEMO_FORCE_REFRESH", raising=False)
    from mini_marie import demo_runtime

    assert demo_runtime.demo_auto_offline() is True
    assert demo_runtime.demo_force_refresh() is False
    assert demo_runtime.demo_use_cache() is True


def test_demo_force_refresh_opt_in(monkeypatch):
    monkeypatch.setenv("DEMO_FORCE_REFRESH", "true")
    from mini_marie import demo_runtime

    assert demo_runtime.demo_force_refresh() is True
    assert demo_runtime.demo_use_cache() is False


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
