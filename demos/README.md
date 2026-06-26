# TWA demo compatibility layer

**TWA** = [The World Avatar](https://theworldavatar.io/) — the Cambridge CARES knowledge-graph ecosystem this repo integrates with.

Mirrors the public [Zaha](https://theworldavatar.io/demos/zaha/) static demo and serves **Marie + Zaha KGQA** with the original API contract. Marie UI is the official **next_app_marie** dev server (not static HTML).

## Official Marie frontend (recommended for compatibility testing)

The live Marie UI is built from **[next_app_marie](https://github.com/cambridge-cares/TheWorldAvatar/tree/main/QuestionAnswering/QA_ICL/frontend/next_app_marie)** in TheWorldAvatar (`BASE_PATH=/demos/marie`, API at `/demos/marie/api/`). Flask serves the API only; `/demos/marie/*` redirects to the Next.js dev server (`MARIE_FRONTEND_URL`, default `http://127.0.0.1:3000/demos/marie`).

To test **our Flask backend against the real frontend**:

**Use WSL/Linux for Node/npm** (upstream [next_app_marie README](https://github.com/cambridge-cares/TheWorldAvatar/tree/main/QuestionAnswering/QA_ICL/frontend/next_app_marie) targets Linux; avoid installing Node on Windows for this).

**Recommended (hybrid):** Flask API on Windows (existing `.venv`), official Next.js in WSL:

```powershell
# Windows — API backend (0.0.0.0 so WSL Next SSR can reach it)
$env:MARIE_FRONTEND_DEV = "1"
$env:DEMO_HOST = "0.0.0.0"
python -m demos.server
```

```powershell
# WSL — frontend (Node via nvm; npm already under vendor/.../next_app_marie)
wsl bash demos/run_marie_compat_wsl.sh setup
wsl bash demos/run_marie_compat_wsl.sh frontend
```

**All-in-WSL** (needs once: `sudo apt install python3.12-venv`):

```powershell
wsl bash demos/run_marie_compat_wsl.sh setup
wsl bash demos/run_marie_compat_wsl.sh both
```

Open **http://127.0.0.1:3000/demos/marie/** in your browser.

Check API contract without starting servers:

```powershell
python -m demos.verify_marie_frontend_compat
```

See `configs/marie_frontend.env.example`.

## API contract (unchanged from TWA demos)

| Endpoint | Body | Response |
|----------|------|----------|
| `POST /demos/zaha/qa/` | `{question, qa_domain}` | `{metadata: {steps: [...]}, data: [...]}` |
| `POST /demos/zaha/chat/` | `{question, data: "<json>"}` | SSE `data: {"content":"...","latency":123}` |
| `POST /demos/marie/api/qa/` | same | same |
| `POST /demos/marie/api/chat/` | same | same |

The frontends use relative `./qa` and `./chat` URLs; when served from this server they hit our adapter in `demos/twa_adapter.py`, which runs `mini_marie.kgqa` (ReAct + MCP tools) and shapes results into tables/maps + reasoning steps.

**Advanced search & Explore** use GET endpoints backed by the warmed SQLite cache (`MINI_MARIE_DATA_DIR`):

| UI page | Route | API prefix |
|---------|-------|------------|
| Species search | `/demos/marie/search/species` | `/demos/marie/api/ontospecies/` (`chemical-classes`, `uses`, `species`, `species-partial`) |
| Zeolite framework search | `/demos/marie/search/zeolite-frameworks` | `/demos/marie/api/ontozeolite/` |
| Zeolitic material search | `/demos/marie/search/zeolitic-materials` | `/demos/marie/api/ontozeolite/zeolitic-materials` |
| SpeciesExplorer | `/demos/marie/plots/species` | `/demos/marie/api/ontospecies/` (same as species search) |
| ZeoliteExplorer | `/demos/marie/plots/zeolite-frameworks` | `/demos/marie/api/ontozeolite/zeolite-frameworks`, `zeolite-frameworks-partial`, lookup lists (`framework-components`, `guest-components`, `secondary-building-units`, `composite-building-units`, `journals`) |

Local cache path is configured in `configs/demo_local.env` (default: `D:/mini_marie_data/data`). **In WSL**, use `configs/demo_local.wsl.env` (`/mnt/d/...`) — loaded automatically by `demos/run_marie_compat_wsl.sh`.

## Quick start

From repo root (requires `.env` with `REMOTE_BASE_URL` and `REMOTE_API_KEY`):

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-demo.txt

# Download Zaha static UI (once; Marie uses next_app_marie instead)
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe -m demos.mirror

# Run local demo server (API + Zaha static; Marie UI on :3000 via run_marie_compat_wsl.sh)
.\.venv\Scripts\python.exe -m demos.server
```

Open:

- Marie UI: http://127.0.0.1:3000/demos/marie/ (Next.js — run `bash demos/run_marie_compat_wsl.sh both`)
- Marie API: http://127.0.0.1:8080/demos/marie/api/
- Zaha: http://127.0.0.1:8080/demos/zaha/

### Zaha (Singapore) cache

Land-plot and building questions use a **local Ontop SQLite cache** (`mini_marie_cache/sg_old/ontop_cache.sqlite`). If that file is missing or empty, tools like `get_sg_residential_commercial_percent` fail and the agent cannot answer zoning/GFA questions.

Warm the cache once (downloads ~114k buildings + land plots from `sg-old.theworldavatar.io`; takes several minutes):

```powershell
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe -m mini_marie.zaha.sg_old.warm_ontop_cache
```

Check status:

```powershell
.\.venv\Scripts\python.exe -c "from mini_marie.zaha.sg_old.ontop_operations import get_sg_ontop_cache_status; print(get_sg_ontop_cache_status())"
```

Environment:

| Variable | Default | Purpose |
|----------|---------|---------|
| `REMOTE_BASE_URL` | — | OpenRouter/OpenAI-compatible LLM base URL |
| `REMOTE_API_KEY` | — | LLM API key |
| `MINI_MARIE_DATA_DIR` | `<repo>/data` | Warmed cache root (see `configs/demo_local.env`) |
| `DEMO_HOST` | `127.0.0.1` | Bind address |
| `DEMO_PORT` | `8080` | Port |
| `DEMO_LLM_MODEL` | `gpt-4o` | Model for KGQA agent |
| `DEMO_AUTO_OFFLINE` | `true` | After online probe, replay full cache from `recording_path` |

## Pointing an external frontend at our backend

If you host the mirrored static files elsewhere, set the API base to your server:

- Zaha: relative `./qa` and `./chat` already work when HTML and API share origin.
- Marie (Next.js export): replace `https://theworldavatar.io/demos/marie/api/` with `https://your-host/demos/marie/api/` in JS bundles (the mirror script does this automatically for local copies).
