# Web search (Marie dual-source QA)

Marie runs **two parallel routes** for each question:

1. **Web** — public internet summary + links (`run_web_search`)
2. **KG** — existing ReAct / competency pipeline (`_run_kgqa_core`)

An LLM **merges** both in `demos/hybrid_interpretation.py` (same stack as TWA narrative).

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `MARIE_WEB_SEARCH` | `1` | Set `0` to disable web route |
| `WEB_SEARCH_BACKEND` | `openrouter` | `openrouter` or `tavily` |
| `WEB_SEARCH_MODEL` | `openai/gpt-4o-search-preview` | Chat model with search (OpenRouter/OpenAI-compatible) |
| `WEB_SEARCH_OPENROUTER_ONLINE` | `1` | Append `:online` for OpenRouter web plugin |
| `TAVILY_API_KEY` | — | Required when `WEB_SEARCH_BACKEND=tavily` (e.g. ontology-to-tool) |
| `REMOTE_BASE_URL` / `REMOTE_API_KEY` | — | Used for OpenRouter-style web chat |

Disable only web: `MARIE_WEB_SEARCH=0`

**Extended answers** (default on): `MARIE_EXTENDED_ANSWERS=1` — long merged narrative + richer web brief. Tune `MARIE_HYBRID_MAX_TOKENS`, `MARIE_HYBRID_TABLE_ROWS`, `WEB_SEARCH_MAX_TOKENS`.

**Web sources table** in the UI is **off by default** (links live in Interpretation → Sources). Set `MARIE_SHOW_WEB_SOURCES_TABLE=1` for a raw title/url/snippet grid (auditors, demos).
