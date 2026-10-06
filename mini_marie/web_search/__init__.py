"""Web search for Marie dual-source QA (internet + knowledge graph)."""

from mini_marie.web_search.service import WebSearchResult, marie_web_search_enabled, run_web_search

__all__ = ["WebSearchResult", "marie_web_search_enabled", "run_web_search"]
