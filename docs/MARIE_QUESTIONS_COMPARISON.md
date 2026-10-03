# Marie competency questions — response comparison

**Reference:** `Marie_Questions.pdf` (September 2026)  
**Updated:** 25 September 2026  
**Demo:** [Marie classic](https://www.theworldavatar.io/demos/marie-classic/)

This document is for whoever supplied the PDF feedback. It compares **Marie’s original answers** (September 2026), **what the PDF asked for**, and **what Marie returns now** after query, narrative, and presentation fixes.

---

## Executive summary

| # | Topic | Old problem | Fixed? |
|---|--------|-------------|--------|
| 1 | UiO-66 PLD | Generic `Summary:` dump | **Yes** — prose + per-source PLD breakdown |
| 2 | Thermal stability | Single MOF row only | **Mostly** — count, top 5, DOIs; WS24 not in KG for top MOFs |
| 3 | ZIF-8 topology peers | Returned ZIF-8 itself | **Yes** — sod topology + other MOFs listed |
| 4 | Binary gas uptake | Raw field dump, no conditions | **Mostly** — conditions + PLD/LFPD; GSA/GPV absent in KG |
| 5 | UiO-66 synthesis | ~8k irrelevant CSD rows | **Yes** — Park_Syn only (1 route); SynMOF empty in KG |

**Cross-cutting change:** Marie no longer answers with `Summary: field; field; field`. Responses are short natural-language summaries plus interactive tables (sortable columns, bar charts where relevant, CSV export, column tooltips).

---

## Question 1 — UiO-66 pore limiting diameter (PLD)

**Question:** *What are the average and variance of the pore limiting diameter for UiO-66?*

### Marie’s original answer

```
Summary: 3.81 avgPLD; 4 n; 0.04 variance.
```

### What the PDF asked for

- Average PLD **3.81 Å**, variance **0.04 Å**
- Over **4 values**, ideally naming the **sources** (or confirming 4 unique sources)

### Marie’s current answer

> For **UiO-66**, average pore limiting diameter (PLD) is **3.81 Å** with variance **0.04 Å²** (n=4 PLD values).  
> PLD values by source: **CSD MOF Collection**: 3.5284 Å (RUBTAK), 3.7332 Å (RUBTAK01); **CoRE MOF 2025**: 4.00843 Å (RUBTAK01), 3.95727 Å (RUBTAK03).

### What changed

| Aspect | Before | After |
|--------|--------|-------|
| Format | Semicolon-separated field dump | Readable sentence |
| Numbers | Correct but unlabelled | Same values, with units (Å, Å²) |
| Sources | Not stated | **2 databases**, 4 PLD entries with refcodes |
| Table | None / minimal | Aggregate row + source detail in rich table |

### Remaining note

The PDF mentions “4 unique sources”; the knowledge graph has **4 PLD measurements from 2 source databases** (CoRE and CSD), not four distinct catalogue names. Marie now reports that explicitly.

---

## Question 2 — Thermally stable MOFs

**Question:** *Which MOFs are reported as thermally stable?*  
*(PDF also suggested: highest experimental thermal stability + top 5.)*

### Marie’s original answer

```
Summary: 10.1021/ic701573r doi; mof_720_mofsimplify_thermal mof; IFAREN refcode;
MOFSimplify Thermal Dataset sourcedb; 654.32 thermal.
```

### What the PDF asked for

- Count of MOFs above **300 °C** (PDF example used **500** — likely from an older dataset snapshot)
- **IFAREN** highest at **654.32 °C**, DOI **10.1021/ic701573r**, plus next refcodes/temperatures
- Ideally **WS24** Burtch label and acid/base stability for the top MOF(s)

### Marie’s current answer

> **2,326** MOF(s) have an experimental thermal decomposition temperature above **300 °C**; top **5** by thermal stability:  
> **IFAREN** has the highest thermal decomposition temperature of **654.32 °C** from DOI **10.1021/ic701573r**, recorded in **MOFSimplify Thermal Dataset**.  
> - **IFAREN**: 654.32 °C — DOI 10.1021/ic701573r  
> - **EQERIC**: 639.13 °C — DOI 10.1039/c1cc10899a  
> - **IFAQUC**: 634.87 °C — DOI 10.1021/ic701573r  
> - **KIFKEQ**: 626.17 °C — DOI 10.1039/b705028c  
> - **MUMYAW**: 604.15 °C — DOI 10.1002/ejic.201500294  
> No **WS24** Burtch/acid–base stability record was found for the top thermal MOFs (IFAREN, EQERIC, IFAQUC).

### What changed

| Aspect | Before | After |
|--------|--------|-------|
| Scope | One MOF | **Full count** + **top 5** ranked list |
| Lead sentence | None | Explicit “highest decomposition temperature” line |
| DOIs | One field in dump | Attached to each top entry |
| Threshold | Unclear | Stated: **> 300 °C** |
| WS24 | Not attempted | Looked up by refcode; **not present** for top thermal MOFs in KG |
| Table | Single row | Ranked table with bar chart on thermal stability |

### Remaining gaps

- **Count:** live KG has **2,326** MOFs > 300 °C, not 500 as in the PDF (dataset growth / different snapshot).
- **WS24:** the WS24 Kulik Group dataset (954 MOFs with Burtch labels) does **not** include refcodes IFAREN, EQERIC, or IFAQUC. Marie states this rather than omitting it.

---

## Question 3 — MOFs with the same topology as ZIF-8

**Question:** *Which MOFs have the same topology as ZIF-8?*

### Marie’s original answer

```
Summary: CC1=NC=C[N]1.[Zn] MOFid-v1.sod.cat0 mofid; ZIF-8 name; EWIDUK refcode;
CoRE MOF 2025 sourcedb; 1 space group; sod topology.
```

*(This described **ZIF-8 itself**, not other MOFs.)*

### What the PDF asked for

- State **ZIF-8** has **sod** topology
- List **other** MOFs (different MOFid) with refcode/source
- Do **not** return ZIF-8 as the only “peer”
- db_id for CIF download was optional / deferred

### Marie’s current answer

> **ZIF-8** has **sod** topology.  
> Other MOFs with the same topology include:  
> - `mof_2000[Cu][sod]3[ASR]1` from **CoRE MOF 2025**  
> - `mof_2000[Cu][sod]3[FSR]1` from **CoRE MOF 2025**  
> - … and **145** more in the table.

### What changed

| Aspect | Before | After |
|--------|--------|-------|
| Wrong focus | ZIF-8 identity row | **Peer listing** workflow step |
| ZIF-8 in peer list | Included | **Excluded** from “other MOFs” |
| Topology | Buried in summary | Lead sentence: “ZIF-8 has sod topology” |
| Table | One identity row | ~150+ peer rows with MOF id and source |

### Identity enrichment (cross-cutting, 2026-09)

Peer and listing answers no longer rely on raw `mof_*` URL slugs alone:

- **MCP:** `enrich_mof_table_rows` / `lookup_mof_identity_by_entries` (agents encouraged via KgqaAgent prompt).
- **Demo UI:** `display_label` column (decoded chemistry tokens or refcode/MOFid when enriched).
- **Verified:** [MOF_AGENT_IDENTITY_TEST.md](./MOF_AGENT_IDENTITY_TEST.md) — MCP simulation for **CQ07** attaches **refcode** + **MOFid** via batch SPARQL; Marie Classic offline path uses cache + display labels.

Re-run: `PYTHONPATH=. python scripts/run_mof_agent_identity_test.py --offline-only`.

### Remaining note

Peer rows use internal MOF identifiers from CoRE MOF 2025; refcodes are shown when present. CIF/db_id linking was not implemented (PDF marked this as optional).

---

## Question 4 — High binary gas uptake

**Question:** *Which MOFs have high binary gas uptake?*

### Marie’s original answer

```
Summary: [long MOFid string] mofid; 7.02 postcomb; 10.7 precomb; ARC_MOF 2025 source.
```

### What the PDF asked for

- **MOFid** of top MOF
- **Post-combustion:** CO₂ from CO₂/N₂ at **0.9 bar**, **298 K** → **7.02 mmol/g**
- **Pre-combustion:** CO₂ from CO₂/H₂ at **40 bar**, **313 K** → **10.7 mmol/g**
- Ideally **PLD, LFPD, GSA, GPV**

### Marie’s current answer

> The MOF with the highest binary-gas uptake has **MOFid**: `[MOFid-v1.nbo.cat0 …]`.  
> - Post-combustion (CO₂/N₂ at 0.9 bar, 298 K): **7.02 mmol/g**  
> - Pre-combustion (CO₂/H₂ at 40 bar, 313 K): **10.7 mmol/g**  
> Source: **ARC_MOF 2025**.  
> Pore properties: **PLD** = 3.63 Å, **LFPD** = 4.99 Å.

### What changed

| Aspect | Before | After |
|--------|--------|-------|
| Conditions | Property names only (`postcomb`) | **Decoded** gas mixtures, pressure, temperature |
| Uptake values | Correct | Same (**7.02**, **10.7** mmol/g) |
| Pore props | Missing | **PLD** and **LFPD** joined by MOFid |
| Presentation | One summary line | Narrative + ranked uptake table |

### Remaining gaps

- **GSA** and **GPV** are **0 or missing** in the KG for this MOFid (no CoRE match). Only ARC_MOF pore fields are populated.

---

## Question 5 — UiO-66 synthesis routes

**Question:** *What synthesis routes are recorded for UiO-66?*

### Marie’s original answer

```
Summary: 10.5517/ccdc.csd.cc2dn4ks doi; reo Hf-UiO-66 name; WIYFUJ refcode;
Solvothermal synthesis solvent; CSD MOF Collection sourcedb.
```

*(One CSD row; query also matched **thousands** of non-synthesis catalogue entries.)*

### What the PDF asked for

- Query **Park_Syn** (common names) and **SynMOF** (refcodes) **only**
- Table: Route | MOF | Temperature | Yield | Solvents | Source
- Narrative: route count, **highest-yield route** highlighted

### Marie’s current answer

> **1** synthesis route(s) from **Park_Syn** / **SynMOF** for **UiO-66**:  
> - **Route A** — **Ce-UiO-66-BPyDC**, solvents: N,N-dimethylformamide; aqueous, yield **38%** (Park_Syn)  
> **Route A** with N,N-dimethylformamide; aqueous has the highest reported yield of **38%**.

### What changed

| Aspect | Before | After |
|--------|--------|-------|
| Data sources | All DBs (8,000+ name matches) | **Park_Syn + SynMOF only** |
| Row count | ~8,117 irrelevant rows | **1** synthesis route |
| Route labelling | None | **Route A**, **Route B**, … |
| Yield ranking | Not stated | Highest yield called out |
| CSD noise | Included | **Excluded** from synthesis filter |
| Table | Misleading bulk CSD data | Synthesis columns with tooltips |

### Remaining gaps

- **SynMOF** has **no UiO-66 rows** in the current KG (0 routes). Only **Park_Syn** returns data.
- **Temperature** is not populated for this Park_Syn entry in the KG (solvent and yield are present).

### Park_Syn data quality — why we show one route (stakeholder agreement)

Domain review flagged that Park_Syn is **incomplete** for UiO-66:

| Match strategy | Rows (approx.) | Issue |
|----------------|----------------|--------|
| **`hasNames` contains `uio-66`** (what Marie uses) | **1** | Named route: **Ce-UiO-66-BPyDC**, yield **38%** |
| **`hasMetadata` contains `uio-66`** | **3** | Often **no `name`**; UiO-66 appears in **paper title/metadata** (DOI, journal), not as a reliable MOF label |

The extra metadata hits include papers such as “Immobilisation … on **UiO-66 and -67**” (one paper, multiple MOFs) and **Zr-BDC** (structure paper whose metadata mentions UiO-66). Pulling all metadata matches would:

- Mix **different MOFs from the same paper**
- Duplicate or mis-attribute routes where **`name` is empty**
- Work against the PDF goal of a clean **Route | MOF | Yield | …** table

**Decision (for now):** keep **`hasNames` only** for UiO-66 synthesis. Do **not** broaden to metadata search unless Markus/Simon explicitly want more rows and accept ambiguity.

**Alternative considered — ZIF-8 (original paper competency example):**

| MOF | Park_Syn routes via `hasNames` | Yields |
|-----|----------------------------------|--------|
| **ZIF-8** | **3** (sonochemical / solvothermal, different solvents & DOIs) | **None** in KG |
| **UiO-66** | **1** | **38%** on the named route |

ZIF-8 would give a **multi-route table** but **cannot rank by highest yield**, which was a core PDF ask. UiO-66 stays the demo question because yield ranking is meaningful on the one complete row.

If product owners want multiple UiO-66 entries later, options are: manual curation, refcode-union (SynMOF + Park_Syn per `CompetencyQs.md` ZIF-8 pattern), or metadata match with **paper-level deduplication** — not implemented today.

---

## Presentation improvements (all questions)

These apply across the five questions:

- **Interpretation pane** — natural-language answer (no `Summary:` dumps)
- **Rich table pane** — DataTables sorting/filtering, CSV export
- **Column headers** — human label + KG field name + description tooltip
- **Charts** — e.g. bar chart for thermal stability ranking
- **Offline replay** — full-scale cached KG results for large corpora

---

## How to verify

1. Open [https://www.theworldavatar.io/demos/marie-classic/](https://www.theworldavatar.io/demos/marie-classic/)
2. Click each sample question (or paste the five questions from the PDF)
3. Compare the **Interpretation** text and **table** to the “current answer” sections above

---

## Technical notes (for maintainers)

| Item | Detail |
|------|--------|
| Narrative layer | `demos/kg_row_narrative.py`, `demos/kg_answer_enrich.py`, `demos/mof_display_identity.py` |
| Identity MCP | `enrich_mof_table_rows`, `lookup_mof_identity_by_entries` — see `docs/MOF_AGENT_IDENTITY_TEST.md` |
| Queries | `mini_marie/mop_mof/mof/mof_competency_operations.py` |
| Synthesis filter | `Park_Syn`, `SynMOF` only (`synthesis_only=true`) |
| Thermal threshold | **300 °C** (count + ranked list) |
| Cache | MOF competency SQLite; re-warm after query changes |

---

## Status legend

- **Yes** — matches PDF intent with current KG data  
- **Mostly** — core facts correct; PDF “ideal” items blocked by KG coverage or snapshot differences  
- **No** — not yet addressed (none of the five core questions remain at “No” for primary facts)

If you need further changes (e.g. WS24 join when refcodes overlap, SynMOF refcode-union for UiO-66, or GSA/GPV from CoRE), say which question to prioritise and we can extend the queries accordingly.
