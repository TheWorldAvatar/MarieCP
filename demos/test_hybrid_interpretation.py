"""Tests for dual-source (web + KG) Marie QA helpers."""

from __future__ import annotations

from demos.hybrid_interpretation import web_sources_table
from mini_marie.web_search.service import WebSearchResult, marie_web_search_enabled


def test_web_sources_table():
    web = WebSearchResult(
        summary="UiO-66 is a Zr MOF.",
        sources=[{"title": "Wiki", "url": "https://example.com/uio66", "snippet": "pcu topology"}],
        backend="test",
    )
    table = web_sources_table(web)
    assert table is not None
    assert table["row_count"] == 1
    assert table["data"][0]["url"].startswith("https://")


def test_marie_web_search_disabled_without_keys(monkeypatch):
    monkeypatch.delenv("REMOTE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("MARIE_WEB_SEARCH", "1")
    monkeypatch.setenv("WEB_SEARCH_BACKEND", "openrouter")
    assert marie_web_search_enabled() is False


if __name__ == "__main__":
    test_web_sources_table()
    print("hybrid tests OK")
