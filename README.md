# MarieCP

Lightweight runtime for querying **[The World Avatar (TWA)](https://theworldavatar.io/)** knowledge graphs via **MCP (Model Context Protocol)** tools.

The `mini_marie` Python package covers three domains:

| Domain | Folder | MCP servers |
|--------|--------|-------------|
| **Zaha** (buildings & cities) | [`mini_marie/zaha/`](mini_marie/zaha/) | `twa-city`, `sg-old` |
| **Marie** (chemistry) | [`mini_marie/marie/`](mini_marie/marie/) | `chemistry-*` (7 servers) |
| **MOP/MOF** (frameworks) | [`mini_marie/mop_mof/`](mini_marie/mop_mof/) | `mof-twa`, `twa-mops` |

Cross-domain tooling (`kg_catalog/`, `kgqa/`, `cross_kg_competency/`) lives under `mini_marie/`.

## Project layout

```text
MarieCP/
├── mini_marie/          # Python package, docs, scripts
├── configs/             # MCP JSON configs (add before deploy)
├── data/                # Runtime SQLite caches (gitignored)
├── evaluation/data/     # Local MOP RDF corpus (gitignored)
├── notebooks/           # Jupyter notebooks
└── requirements-mini-marie.txt
```

See [mini_marie/README.md](mini_marie/README.md) for full documentation, quick start, and deployment.

## Quick start

```bash
pip install -r requirements-mini-marie.txt   # when available
export PYTHONPATH="$(pwd)"
python -m mini_marie.mop_mof.mof.main
```

Runtime caches are written to `data/mini_marie_cache/` (override with `MINI_MARIE_DATA_DIR`).
