"""Run web search via OpenRouter/OpenAI-compatible chat or Tavily."""

from __future__ import annotations

import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

_FALSE = frozenset({"0", "false", "no", "off", "disabled", "none"})


@dataclass
class WebSearchResult:
    """Compact web search bundle for hybrid Marie answers."""

    summary: str
    sources: List[Dict[str, str]] = field(default_factory=list)
    backend: str = ""
    model: str = ""
    elapsed_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def marie_web_search_enabled() -> bool:
    if os.environ.get("MARIE_WEB_SEARCH", "1").strip().lower() in _FALSE:
        return False
    backend = _backend_name()
    if backend in _FALSE:
        return False
    if backend == "tavily":
        return bool(os.environ.get("TAVILY_API_KEY", "").strip())
    return bool(os.environ.get("REMOTE_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def _backend_name() -> str:
    return os.environ.get("WEB_SEARCH_BACKEND", "openrouter").strip().lower()


def _api_credentials() -> tuple[str, str]:
    base = (
        os.environ.get("REMOTE_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    ).rstrip("/")
    key = os.environ.get("REMOTE_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    return base, key


def _extended_web_search() -> bool:
    return os.environ.get("MARIE_EXTENDED_ANSWERS", "1").strip().lower() not in _FALSE


def _search_model() -> str:
    return (
        os.environ.get("WEB_SEARCH_MODEL")
        or os.environ.get("MARIE_WEB_SEARCH_MODEL")
        or "openai/gpt-4o:online"
    ).strip()


def _web_search_system_prompt() -> str:
    if _extended_web_search():
        return (
            "You are a research assistant. Search the public web and produce a detailed factual "
            "brief for the user's question. Cover definitions, properties, applications, notable "
            "examples, and recent literature. Cite every major claim with markdown links [title](url). "
            "Use headings and bullet lists. Target 300–600 words of substantive content; no filler."
        )
    return (
        "You answer using current public web information. "
        "Cite sources with markdown links [title](url). "
        "Be factual and concise (2–8 sentences or short bullets)."
    )


def _extract_urls(text: str) -> List[str]:
    return re.findall(r"https?://[^\s\)\]>\"']+", text or "")


def _normalize_sources(raw: List[Dict[str, str]], summary: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        url = (item.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(
            {
                "title": (item.get("title") or urlparse(url).netloc or "Source")[:200],
                "url": url[:500],
                "snippet": (item.get("snippet") or item.get("content") or "")[:500],
            }
        )
    for url in _extract_urls(summary):
        if url in seen:
            continue
        seen.add(url)
        out.append({"title": urlparse(url).netloc, "url": url, "snippet": ""})
    cap = 16 if _extended_web_search() else 12
    return out[:cap]


async def run_web_search(question: str) -> Optional[WebSearchResult]:
    """Search the public web for the question. Returns None when disabled or on failure."""
    if not marie_web_search_enabled():
        return None
    q = (question or "").strip()
    if not q:
        return None

    backend = _backend_name()
    t0 = time.perf_counter()
    try:
        if backend == "tavily":
            result = await _tavily_search(q)
        else:
            result = await _openrouter_search(q)
    except Exception as exc:
        elapsed = int((time.perf_counter() - t0) * 1000)
        return WebSearchResult(
            summary="",
            backend=backend,
            elapsed_ms=elapsed,
            error=f"{type(exc).__name__}: {exc}",
        )
    result.elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return result


async def _tavily_search(question: str) -> WebSearchResult:
    key = os.environ["TAVILY_API_KEY"].strip()
    depth = "advanced" if _extended_web_search() else "basic"
    payload = {
        "api_key": key,
        "query": question,
        "search_depth": depth,
        "include_answer": True,
        "max_results": 12 if _extended_web_search() else 8,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post("https://api.tavily.com/search", json=payload)
        resp.raise_for_status()
        data = resp.json()
    answer = str(data.get("answer") or "").strip()
    sources = [
        {
            "title": r.get("title") or "",
            "url": r.get("url") or "",
            "snippet": r.get("content") or "",
        }
        for r in (data.get("results") or [])
    ]
    if not answer and sources:
        answer = sources[0].get("snippet", "")
    return WebSearchResult(
        summary=answer,
        sources=_normalize_sources(sources, answer),
        backend="tavily",
    )


async def _openrouter_search(question: str) -> WebSearchResult:
    base, key = _api_credentials()
    if not key:
        raise RuntimeError("REMOTE_API_KEY or OPENAI_API_KEY required for web search")

    model = _search_model()
    # OpenRouter: `:online` enables web plugin on supported models.
    if os.environ.get("WEB_SEARCH_OPENROUTER_ONLINE", "1").strip().lower() not in _FALSE:
        if ":online" not in model and "search" not in model.lower():
            model = f"{model}:online"

    user_msg = question
    if _extended_web_search():
        user_msg = (
            f"{question.strip()}\n\n"
            "Provide a thorough web-based research summary with citations."
        )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": _web_search_system_prompt()},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.25 if _extended_web_search() else 0.2,
        "max_tokens": int(os.environ.get("WEB_SEARCH_MAX_TOKENS", "4096")),
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(f"{base}/chat/completions", headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    summary = str(message.get("content") or "").strip()

    sources: List[Dict[str, str]] = []
    for ann in message.get("annotations") or []:
        if not isinstance(ann, dict):
            continue
        url_citation = ann.get("url_citation") or ann.get("citation") or ann
        if isinstance(url_citation, dict):
            sources.append(
                {
                    "title": str(url_citation.get("title") or ""),
                    "url": str(url_citation.get("url") or ""),
                    "snippet": str(url_citation.get("content") or url_citation.get("snippet") or ""),
                }
            )

    return WebSearchResult(
        summary=summary,
        sources=_normalize_sources(sources, summary),
        backend="openrouter",
        model=model,
    )
