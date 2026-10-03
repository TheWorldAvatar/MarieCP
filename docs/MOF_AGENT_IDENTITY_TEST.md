# MOF identity — agent vs demo path test report

Generated: 2026-09-29 14:28 UTC

## Configuration

- Model: `gpt-4o-mini`
- OpenAI/Azure key present: **True**
- Agent ReAct run: **True**

## Live KgqaAgent (ReAct + mof-twa MCP)

| Question | Tools | Enrich called? | Opaque slug? | ms |
| --- | --- | --- | --- | --- |
| Which MOFs have the same topology as ZIF-8? | enrich_mof_table_rows, lookup_mof_identity_by_entries, run_competency_online | yes | no | 27220 |
| Which Zr-containing MOFs have carboxylate linker… | enrich_mof_table_rows, run_competency_online | yes | no | 31307 |
| How many experimental Cu-containing MOFs are rec… | enrich_mof_table_rows, run_competency_online | yes | no | 21547 |

### Agent: Which MOFs have the same topology as ZIF-8?

- **Tools:** `enrich_mof_table_rows, lookup_mof_identity_by_entries, run_competency_online`
- **Enrichment MCP used:** True
- **Recording:** `C:\Users\xz378\Documents\GitHub\MarieCP\mini_marie\mop_mof\mof\competency_runs\CQ07_SAME_TOPO_ZIF8_online_1790692112.json`

**Answer preview:**

```
The query regarding MOFs that share the same topology as ZIF-8 has been processed successfully. Here are the results:

### Summary of MOFs with the Same Topology as ZIF-8 (Topology: sod)

1. **Total Count**: There are **393** MOFs that share the same topology as ZIF-8.
2. **Sample of MOFs**:
   - **MOF Name**: ZIF-9
     - **Refcode**: VEJZEQ
     - **MOF ID**: [Co].c1ccc2c(c1)N=C[N]2 MOFid-v1.sod.cat0
     - **Source Database**: CoRE MOF 2025
   - **MOF Name**: (Unnamed)
     - **Refcode**: QEFNAQ
     - **MOF ID**: O=C1N=C[CH]C=N1.[Cu] MOFid-v1.sod.cat0
     - **Source Database**: CoRE MOF 2025
   - **MOF Name**: (Unnamed)
     - **Refcode**: CUIMDZ01
     - **MOF ID**: C1=C[N]C=N1.C1=N[CH]C=N1.[Cu] MOFid-v1.sod.cat0
     - **Source Database**: CoRE MOF 2025

### Additional MOFs:
- **MOF
```

### Agent: Which Zr-containing MOFs have carboxylate linkers?

- **Tools:** `enrich_mof_table_rows, run_competency_online`
- **Enrichment MCP used:** True
- **Recording:** `C:\Users\xz378\Documents\GitHub\MarieCP\mini_marie\mop_mof\mof\competency_runs\CQ_D1_ZR_COOH_online_1790692138.json`

**Answer preview:**

```
The query regarding Zr-containing MOFs with carboxylate linkers has yielded the following results:

### Summary of Findings
- **Total MOFs Found:** 10
- **Source Database:** All entries are from **QMOF_2025**.

### Detailed Results
1. **MOF Name:** OC(=O)c1c(C(=O)O)c(C(=O)[O-])c2c(c1C(=O)[O-])cccc2; [O-]C(=O)c1c(N)c(N)c(c(c1N)N)C(=O)[O-]
   - **MOF ID:** [qmof-1693606](https://www.theworldavatar.com/kg/ontomofs_vkg/mof_qmof-1693606)
   - **Topology:** fcu
   - **Space Group:** 1

2. **MOF Name:** [O-]C(=O)c1c(O)c(O)c(c2c1c(O)c(O)c(c2O)O)C(=O)[O-]; [O-]C(=O)c1cc(C(=O)O)c(cc1C(=O)O)C(=O)[O-]
   - **MOF ID:** [qmof-19945d1](https://www.theworldavatar.com/kg/ontomofs_vkg/mof_qmof-19945d1)
   - **Topology:** fcu
   - **Space Group:** 1

3. **MOF Name:** OC(=O)c1cc(cc2c1cc(cc2C(=O)O)C(=O)[O-])C(
```

### Agent: How many experimental Cu-containing MOFs are recorded?

- **Tools:** `enrich_mof_table_rows, run_competency_online`
- **Enrichment MCP used:** True
- **Recording:** `C:\Users\xz378\Documents\GitHub\MarieCP\mini_marie\mop_mof\mof\competency_runs\CQ03_CU_EXPERIMENTAL_online_1790692169.json`

**Answer preview:**

```
There are a total of **9,325 experimental copper-containing MOFs** recorded in the database. 

For further details, the results can be accessed through the recording path: `C:\Users\xz378\Documents\GitHub\MarieCP\mini_marie\mop_mof\mof\competency_runs\CQ03_CU_EXPERIMENTAL_online_1790692169.json`.
```

## MCP toolchain simulation (agent-equivalent, no LLM)

Exercises the same tools the ReAct agent should call: `run_competency_online` → offline replay → `enrich_mof_rows` (MCP: `enrich_mof_table_rows`).

### Simulation: Which MOFs have the same topology as ZIF-8?

- **Workflow:** `CQ07_SAME_TOPO_ZIF8`
- **Tool chain:** run_competency_online → replay_competency_offline (orchestrator) → enrich_mof_table_rows
- **Rows:** 150 (46322 ms)
- **Label before enrich:** `Cu · sod · ASR`
- **After enrich:** name=`-` refcode=`QEFNAQ` display=`QEFNAQ`

**Enriched sample TSV (3 rows):**

```tsv
mof	source	topology	name	refcode	mofid	sourcedb	space_group
https://www.theworldavatar.com/kg/ontomofs_vkg/mof_2000%5BCu%5D%5Bsod%5D3%5BASR%5D1	CoRE MOF 2025	sod	-	QEFNAQ	O=C1N=C[CH]C=N1.[Cu] MOFid-v1.sod.cat0	CoRE MOF 2025	224
https://www.theworldavatar.com/kg/ontomofs_vkg/mof_2000%5BCu%5D%5Bsod%5D3%5BFSR%5D1	CoRE MOF 2025	sod	-	QEFNAQ	O=C1N=C[CH]C=N1.[Cu] MOFid-v1.sod.cat0	CoRE MOF 2025	7
https://www.theworldavatar.com/kg/ontomofs_vkg/mof_2001%5BCu%5D%5Bsod%5D3%5BASR%5D1	CoRE MOF 2025	sod	-	CUIMDZ01	C1=C[N]C=N1.C1=N[CH]C=N1.[Cu] MOFid-v1.sod.cat0	CoRE MOF 2025	148
```

### Simulation: Which Zr-containing MOFs have carboxylate linkers?

- **Workflow:** `CQ_D1_ZR_COOH`
- **Tool chain:** run_competency_online → replay_competency_offline (orchestrator) → enrich_mof_table_rows
- **Rows:** 22 (23150 ms)
- **Label before enrich:** `qmof-1693606`
- **After enrich:** name=`None` refcode=`None` display=`OC(=O)c1c(C(=O)O)c(C(=O)[O-])c2c(c1C(=O)[O-])cccc2.[O-]C(=O)c1c(N)c(N)c…`

**Enriched sample TSV (3 rows):**

```tsv
mof	node	linker	sourcedb	mofid	source	topology	space_group
https://www.theworldavatar.com/kg/ontomofs_vkg/mof_qmof-1693606	[O]12[Zr]34[OH]5[Zr]62[OH]2[Zr]71[OH]4[Zr]14[O]3[Zr]35[O]6[Zr]2([O]71)[OH]43	OC(=O)c1c(C(=O)O)c(C(=O)[O-])c2c(c1C(=O)[O-])cccc2; [O-]C(=O)c1c(N)c(N)c(c(c1N)N)C(=O)[O-]	QMOF_2025	OC(=O)c1c(C(=O)O)c(C(=O)[O-])c2c(c1C(=O)[O-])cccc2.[O-]C(=O)c1c(N)c(N)c(c(c1N)N)C(=O)[O-].[O]12[Zr]34[OH]5[Zr]62[OH]2[Zr]71[OH]4[Zr]14[O]3[Zr]35[O]6[Zr]2([O]71)[OH]43 MOFid-v1.fcu.cat0	QMOF_2025	fcu	1
https://www.theworldavatar.com/kg/ontomofs_vkg/mof_qmof-19945d1	[O]12[Zr]34[OH]5[Zr]62[OH]2[Zr]71[OH]4[Zr]14[O]3[Zr]35[O]6[Zr]2([O]71)[OH]43	[O-]C(=O)c1c(O)c(O)c(c2c1c(O)c(O)c(c2O)O)C(=O)[O-]; [O-]C(=O)c1cc(C(=O)O)c(cc1C(=O)O)C(=O)[O-]	QMOF_2025	[O-]C(=O)c1c(O)c(O)c(c2c1c(O)c(O)c(c2O)O)C(=O)[O-].[O-]C(=O)c1cc(C(=O)O)c(cc1C(=O)O)C(=O)[O-].[O]12[Zr]34[OH]5[Zr]62[OH]2[Zr]71[OH]4[Zr]14[O]3[Zr]35[O]6[Zr]2([O]71)[OH]43 MOFid-v1.fcu.cat0	QMOF_2025	fcu	1
https://www.theworldavatar.com/kg/ontomofs_vkg/mof_qmof-2239292	[O]12[Zr]34[OH]5[Zr]62[OH]2[Zr]71[OH]4[Zr]14[O]3[Zr]35[O]6[Zr]2([O]71)[OH]43	OC(=O)c1cc(cc2c1cc(cc2C(=O)O)C(=O)[O-])C(=O)[O-]; [O-]C(=O)c1sc2c(c1F)sc(c2F)C(=O)[O-]	QMOF_2025	OC(=O)c1cc(cc2c1cc(cc2C(=O)O)C(=O)[O-])C(=O)[O-].[O-]C(=O)c1sc2c(c1F)sc(c2F)C(=O)[O-].[O]12[Zr]34[OH]5[Zr]62[OH]2[Zr]71[OH]4[Zr]14[O]3[Zr]35[O]6[Zr]2([O]71)[OH]43 MOFid-v1.fcu.cat0	QMOF_2025	fcu	5
```

## Demo path (direct route + auto enrichment)

Legacy comparison only: set `MOF_COMPETENCY_DIRECT=1`, then `route_question` → `_try_direct_from_route` → `kgqa_result_to_marie` (`_kg_enrich_marie_table_identities` + `display_label`). **Production default is ReAct** (see [MOF_DEMO_TWELVE_AGENT_RESULTS.md](./MOF_DEMO_TWELVE_AGENT_RESULTS.md)).

### Demo: Which MOFs have the same topology as ZIF-8?

- **Columns (head):** `['display_label', 'topology', 'source', 'display_detail', 'mof']`
- **display_label sample:** `Cu · sod · ASR`
- **name / refcode sample:** `None` / `None`
- **Weak narrative:** False

**Narrative preview:**

**ZIF-8** has **sod** topology.
Other MOFs with the same topology include:
- **Cu · sod · ASR** — topology **sod** · CoRE MOF 2025
- **Cu · sod · FSR** — topology **sod** · CoRE MOF 2025
- **Cu · sod · ASR** — topology **sod** · CoRE MOF 2025
- **Co · sod · ASR** — topology **sod** · CoRE MOF 2025
- **Co · sod · FSR** — topology **sod** · CoRE MOF 2025
- … and **145** more in the table.

### Demo: Which Zr-containing MOFs have carboxylate linkers?

- **Columns (head):** `['display_label', 'sourcedb', 'display_detail', 'node', 'linker', 'mof']`
- **display_label sample:** `qmof-1693606`
- **name / refcode sample:** `None` / `None`
- **Weak narrative:** False

**Narrative preview:**

**22** MOF(s) match the **metal / linker** chemistry filters (sample):
By source in sample: **QMOF_2025** (22).
- **qmof-1693606** — QMOF_2025
- **qmof-19945d1** — QMOF_2025
- **qmof-2239292** — QMOF_2025
- **qmof-24d6f98** — QMOF_2025
- **qmof-3253d86** — QMOF_2025

### Demo: How many experimental Cu-containing MOFs are recorded?

- **Columns (head):** `['count']`
- **display_label sample:** `None`
- **name / refcode sample:** `None` / `None`
- **Weak narrative:** False

**Narrative preview:**

The knowledge graph records **9,325** experimental Cu-containing MOFs.

## Interpretation

- **Agent path** depends on the model calling `enrich_mof_table_rows` after competency tools (prompt instructs this in `KgqaAgent._mof_identity_enrichment_hint`).
- **Demo path** enriches tables automatically (cache-only merge + `display_label`); MCP simulation also hits **live SPARQL** for refcode/MOFid when cache misses.
- **Live ReAct** requires `REMOTE_API_KEY` or `OPENAI_API_KEY` in `.env`.
- **MOF competency default:** ReAct + MCP; use `MOF_COMPETENCY_DIRECT=1` only for the old Python bypass.
- Re-run this script after prompt or MCP changes to compare `Enrich called?` column.
- **MCP simulation** always runs without an API key; use it in CI.

## How to re-run

```bash
export PYTHONPATH=$(pwd)
python scripts/run_mof_agent_identity_test.py          # + live agent if REMOTE_API_KEY set
python scripts/run_mof_agent_identity_test.py --offline-only
python scripts/run_mof_demo_twelve_report.py           # direct path (sets MOF_COMPETENCY_DIRECT)
python scripts/run_mof_demo_twelve_agent_test.py       # all 12 via ReAct → MOF_DEMO_TWELVE_AGENT_RESULTS.md
```
