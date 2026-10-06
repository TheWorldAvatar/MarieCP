# MOF identity enrichment

Many competency tools return **`mof` entry ids** (IRIs or CoRE slugs) without **`hasNames`** or **refcode** on the same row. Summaries and tables should not show raw slugs when identity exists elsewhere in the KG.

## Layers

| Layer | Role |
|--------|------|
| **SPARQL** | Prefer OPTIONAL `hasNames`, `hasCsdRefcode`, `hasMofidV1` on list queries (e.g. same-topology peers). |
| **`mof_identity_enrichment.py`** | Batch lookup + merge identity onto arbitrary row lists (cache first, then SPARQL). |
| **MCP tools** | `lookup_mof_identity_by_entries`, `enrich_mof_table_rows` — for ReAct agents after any tool. |
| **`demos/mof_display_identity.py`** | Presentation: `display_label` / `display_detail` when names are still missing. |
| **Marie demo path** | `twa_adapter._kg_enrich_marie_table_identities` runs offline cache merge before rich tables. |

## Agent policy

KgqaAgent appends a **MOF identity enrichment** block for `mof` routes: after competency or atomic tools, call **`enrich_mof_table_rows`** when rows lack human labels.

## Offline cache

`CompetencyCache.local_identity_by_mof_keys` reads warmed **`facet_identity`**. Re-warm after SPARQL shape changes (`warm_competency_cache`).

## Typical agent flow

1. `run_competency_online(workflow_id="CQ07_SAME_TOPO_ZIF8")`
2. Parse sample rows → JSON array
3. `enrich_mof_table_rows(rows_json=...)`
4. Answer using **name** / **refcode** / **MOFid** columns

## Testing

| Report | Command |
|--------|---------|
| [docs/MOF_AGENT_IDENTITY_TEST.md](../../../../docs/MOF_AGENT_IDENTITY_TEST.md) | `PYTHONPATH=. python scripts/run_mof_agent_identity_test.py` |
| [docs/MOF_DEMO_TWELVE_RESULTS.md](../../../../docs/MOF_DEMO_TWELVE_RESULTS.md) | `PYTHONPATH=. python scripts/run_mof_demo_twelve_report.py` |

**MCP simulation (no API key):** the agent test script runs `run_competency_online` → offline replay → `enrich_mof_rows` (same as MCP `enrich_mof_table_rows`). Example result for ZIF-8 peers: rows gain **refcode** and **MOFid** from live SPARQL even when `hasNames` is `-`.

**Live ReAct:** set `OPENAI_API_KEY` and run `python scripts/run_mof_agent_identity_test.py` without `--offline-only`. Check the report table column **Enrich called?** for `enrich_mof_table_rows`.

**Unit tests:**

```bash
PYTHONPATH=. python mini_marie/mop_mof/mof/test_mof_identity_enrichment.py
PYTHONPATH=. python demos/test_mof_display_identity.py
```

Optional integration (network + ~60s):

```bash
set RUN_MOF_INTEGRATION=1
PYTHONPATH=. python scripts/run_mof_agent_identity_test.py --offline-only
```
