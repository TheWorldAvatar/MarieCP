# MOF demo — 12 canonical questions (local run)

Generated: 2026-09-29 14:13 UTC

Execution path (this report only): `route_question` → direct competency bypass (`MOF_COMPETENCY_DIRECT=1`) → `kgqa_result_to_marie`. **Default for Marie / TWA:** **ReAct agent** + MCP; set `MOF_COMPETENCY_DIRECT=1` (or `MARIE_MOF_DIRECT=1`) only for the old Python bypass.

**Live agent run (12/12):** [MOF_DEMO_TWELVE_AGENT_RESULTS.md](./MOF_DEMO_TWELVE_AGENT_RESULTS.md) (generated 2026-09-29).

## Summary

- **Ready (non-weak NL + at least one table):** 12 / 12

- All twelve passed local readiness checks.

---

Tables use **user-facing column headers** (from `columns_meta`); internal KG fields such as `mof` are hidden by default in the Marie Classic UI. See [MOF_AGENT_IDENTITY_TEST.md](./MOF_AGENT_IDENTITY_TEST.md).

## 1. What are the average and variance of the pore limiting diameter for UiO-66?

- **Workflow:** `CQ01_PLD_UIO66`
- **Status:** **READY**

### Natural language answer

For **UiO-66**, average pore limiting diameter (PLD) is **3.81 Å** with variance **0.04 Å²** (n=4 PLD values).
PLD values by source: **CSD MOF Collection**: 3.5284 Å (RUBTAK), 3.7332 Å (RUBTAK01); **CoRE MOF 2025**: 4.00843 Å (RUBTAK01), 3.95727 Å (RUBTAK03).

### Tables

#### Table 1 (1 rows per metadata, 1 in sample payload)
_Table columns (user-facing):_ Average PLD (Å), PLD variance (Å²), Sample count

| Average PLD (Å) | PLD variance (Å²) | Sample count |
| --- | --- | --- |
| 3.806825 | 0.03655484882500026 | 4 |

---

## 2. Which MOFs have the same topology as ZIF-8?

- **Workflow:** `CQ07_SAME_TOPO_ZIF8`
- **Status:** **READY**

### Natural language answer

**ZIF-8** has **sod** topology.
Other MOFs with the same topology include:
- **Cu · sod · ASR** — topology **sod** · CoRE MOF 2025
- **Cu · sod · FSR** — topology **sod** · CoRE MOF 2025
- **Cu · sod · ASR** — topology **sod** · CoRE MOF 2025
- **Co · sod · ASR** — topology **sod** · CoRE MOF 2025
- **Co · sod · FSR** — topology **sod** · CoRE MOF 2025
- … and **145** more in the table.

### Tables

#### Table 1 (150 rows per metadata, 150 in sample payload)
_Table columns (user-facing):_ MOF, Network topology, Dataset, At a glance

| MOF | Network topology | Dataset | At a glance |
| --- | --- | --- | --- |
| Cu · sod · ASR | sod | CoRE MOF 2025 | topology **sod** · CoRE MOF 2025 |
| Cu · sod · FSR | sod | CoRE MOF 2025 | topology **sod** · CoRE MOF 2025 |
| Cu · sod · ASR | sod | CoRE MOF 2025 | topology **sod** · CoRE MOF 2025 |
| Co · sod · ASR | sod | CoRE MOF 2025 | topology **sod** · CoRE MOF 2025 |
| Co · sod · FSR | sod | CoRE MOF 2025 | topology **sod** · CoRE MOF 2025 |
| In · sod · ASR | sod | CoRE MOF 2025 | topology **sod** · CoRE MOF 2025 |
| In · sod · FSR | sod | CoRE MOF 2025 | topology **sod** · CoRE MOF 2025 |
| Zn · sod · ASR | sod | CoRE MOF 2025 | topology **sod** · CoRE MOF 2025 |

_Showing 8 of 150 rows in payload sample._

---

## 3. What synthesis routes are recorded for UiO-66?

- **Workflow:** `CQ04_SYNTHESIS_UIO66`
- **Status:** **READY**

### Natural language answer

**1** synthesis route(s) from **Park_Syn** / **SynMOF** for **UiO-66**:
- **Route A** — **Ce-UiO-66-BPyDC**, solvents: N,N-dimethylformamide; aqueous, yield **38%** (Park_Syn)
**Route A** with N,N-dimethylformamide; aqueous has the highest reported yield of **38%**.

### Tables

#### Table 1 (1 rows per metadata, 1 in sample payload)
_Table columns (user-facing):_ MOF name, Yield (%), Synthesis method, Solvents, Source database, Publication DOI

| MOF name | Yield (%) | Synthesis method | Solvents | Source database | Publication DOI |
| --- | --- | --- | --- | --- | --- |
| Ce-UiO-66-BPyDC | 38 | Conventional solvothermal | N,N-dimethylformamide; aqueous | Park_Syn | 10.1021/acs.cgd.6b01512 |

---

## 4. Which MOFs are reported as thermally stable?

- **Workflow:** `CQ_D6_THERMAL`
- **Status:** **READY**

### Natural language answer

**2,326** MOF(s) have an experimental thermal decomposition temperature above **300 °C**; top **5** by thermal stability:
**IFAREN** has the highest thermal decomposition temperature of **654.32 °C** from DOI **10.1021/ic701573r**, recorded in **MOFSimplify Thermal Dataset**.
- **IFAREN**: 654.32 °C (MOFSimplify Thermal Dataset) — DOI 10.1021/ic701573r
- **EQERIC**: 639.13 °C (MOFSimplify Thermal Dataset) — DOI 10.1039/c1cc10899a
- **IFAQUC**: 634.87 °C (MOFSimplify Thermal Dataset) — DOI 10.1021/ic701573r
- **KIFKEQ**: 626.17 °C (MOFSimplify Thermal Dataset) — DOI 10.1039/b705028c
- **MUMYAW**: 604.15 °C (MOFSimplify Thermal Dataset) — DOI 10.1002/ejic.201500294
No **WS24** Burtch/acid–base stability record was found for the top thermal MOFs (IFAREN, EQERIC, IFAQUC).

### Tables

#### Table 1 (500 rows per metadata, 500 in sample payload)
_Table columns (user-facing):_ MOF, CSD refcode, Thermal stability (°C), Source database, Publication DOI, At a glance

| MOF | CSD refcode | Thermal stability (°C) | Source database | Publication DOI | At a glance |
| --- | --- | --- | --- | --- | --- |
| IFAREN | IFAREN | 654.3239796 | MOFSimplify Thermal Dataset | 10.1021/ic701573r | MOFSimplify Thermal Dataset |
| EQERIC | EQERIC | 639.1312089 | MOFSimplify Thermal Dataset | 10.1039/c1cc10899a | MOFSimplify Thermal Dataset |
| IFAQUC | IFAQUC | 634.8680022 | MOFSimplify Thermal Dataset | 10.1021/ic701573r | MOFSimplify Thermal Dataset |
| KIFKEQ | KIFKEQ | 626.173347 | MOFSimplify Thermal Dataset | 10.1039/b705028c | MOFSimplify Thermal Dataset |
| MUMYAW | MUMYAW | 604.1485695 | MOFSimplify Thermal Dataset | 10.1002/ejic.201500294 | MOFSimplify Thermal Dataset |
| KINFEU | KINFEU | 601.5644621 | MOFSimplify Thermal Dataset | 10.1021/cg400531j | MOFSimplify Thermal Dataset |
| WAPSUE | WAPSUE | 598.9593238 | MOFSimplify Thermal Dataset | 10.1039/C7DT00615B | MOFSimplify Thermal Dataset |
| NAQQED | NAQQED | 598.8876929 | MOFSimplify Thermal Dataset | 10.1002/ejic.201100944 | MOFSimplify Thermal Dataset |

_Showing 8 of 500 rows in payload sample._

---

## 5. Which MOFs have high binary gas uptake?

- **Workflow:** `CQ_D7_BINARY_UPTAKE`
- **Status:** **READY**

### Natural language answer

The MOF with the highest binary-gas uptake has **MOFid**: `N=N.O=C1N(c2ccc(c(c2)C(C)C)C(=O)[O-])C(=O)c2c3c1ccc1c3c(cc2)c2c3c1ccc1c3c(cc2)C(=O)N(C1=O)c1ccc(c(c1)C(C)C)C(=O)[O-].[Cu][Cu].[O-]C(=O)C=CC(=O)[O-] MOFid-v1.nbo.cat0`.
- Post-combustion (CO2N2 at 0.9 bar, 298 K (mmolg)): **7.02 mmol/g**
- Pre-combustion (CO2H2 at 40.0 bar, 313 K (mmolg)): **10.7 mmol/g**
Source: **ARC_MOF 2025**.
Pore properties: **PLD** = 3.62954 Å, **LFPD** = 4.99139 Å.
(127,137 MOFs exceed the uptake thresholds.)

### Tables

#### Table 1 (500 rows per metadata, 500 in sample payload)
_Table columns (user-facing):_ Structure ID (MOFid), Post-combustion uptake (mmol/g), Pre-combustion uptake (mmol/g), Dataset

| Structure ID (MOFid) | Post-combustion uptake (mmol/g) | Pre-combustion uptake (mmol/g) | Dataset |
| --- | --- | --- | --- |
| N=N.O=C1N(c2ccc(c(c2)C(C)C)C(=O)[O-])C(=O)c2c3c1ccc1c3c(cc2)c2c3c1ccc1c3c(cc2... | 7.022769 | 10.696522 | ARC_MOF 2025 |
| N=CC=N.[Cd].[O-]C(=O)c1cc2ccc3c4c2c(c1)ccc4cc(c3)C(=O)[O-] MOFid-v1.ERROR,wmp... | 6.886547 | 12.612147 | ARC_MOF 2025 |
| CC(=O)c1cc2c(C(=O)C)c3cncc4c3c3c2c2c1cc1cncc5c1c2c1c3c(c4)c(cc1c5C(=O)C)C(=O)... | 6.824588 | 12.148323 | ARC_MOF 2025 |
| CC(=O)Nc1cc2cc3cnc(c4c3c3c2c2c1cc1c(ncc5c1c2c1c3c(c4)c(cc1c5)NC(=O)C)NC(=O)C)... | 6.609229 | 10.557987 | ARC_MOF 2025 |
| N=N.O=C1N(c2ccc(c(c2)c2ccccc2)C(=O)[O-])C(=O)c2c3c1ccc1c3c(cc2)c2c3c1ccc1c3c(... | 6.55309 | 11.537191 | ARC_MOF 2025 |
| CC(=O)Nc1c(NC(=O)C)c2cc3c(ncc4c3c3c2c2c1cc1cncc5c1c2c1c3c(c4)ccc1c5)NC(=O)C.[... | 6.43354 | 12.450238 | ARC_MOF 2025 |
| O=Cc1cc2cc3cncc4c3c3c2c2c1cc1cncc5c1c2c1c3c(c4)c(cc1c5)C=O.[O-]C(=O)c1cc(cc2c... | 6.425774 | 12.86417 | ARC_MOF 2025 |
| CC(=O)c1cc2c(c3c1ccnc3)cc(c1c2cncc1)C(=O)C.[O-]C(=O)c1cc(C(=O)[O-])c2c3-c4c(C... | 6.350911 | 8.731266 | ARC_MOF 2025 |

_Showing 8 of 500 rows in payload sample._

---

## 6. Which Zr-containing MOFs have carboxylate linkers?

- **Workflow:** `CQ_D1_ZR_COOH`
- **Status:** **READY**

### Natural language answer

**22** MOF(s) match the **metal / linker** chemistry filters (sample):
By source in sample: **QMOF_2025** (22).
- **qmof-1693606** — QMOF_2025
- **qmof-19945d1** — QMOF_2025
- **qmof-2239292** — QMOF_2025
- **qmof-24d6f98** — QMOF_2025
- **qmof-3253d86** — QMOF_2025

### Tables

#### Table 1 (22 rows per metadata, 22 in sample payload)
_Table columns (user-facing):_ MOF, Source database, At a glance

| MOF | Source database | At a glance |
| --- | --- | --- |
| qmof-1693606 | QMOF_2025 | QMOF_2025 |
| qmof-19945d1 | QMOF_2025 | QMOF_2025 |
| qmof-2239292 | QMOF_2025 | QMOF_2025 |
| qmof-24d6f98 | QMOF_2025 | QMOF_2025 |
| qmof-3253d86 | QMOF_2025 | QMOF_2025 |
| qmof-48c7a7e | QMOF_2025 | QMOF_2025 |
| qmof-60cb60d | QMOF_2025 | QMOF_2025 |
| qmof-69ba23e | QMOF_2025 | QMOF_2025 |

_Showing 8 of 22 rows in payload sample._

---

## 7. How is pcu topology distributed across MOF source databases?

- **Workflow:** `CQ_D2_PCU_ALL`
- **Status:** **READY**

### Natural language answer

**272,711** MOF(s) with **pcu** topology appear in this sample; **5** source database(s):
- **Tobassco**: **205,361**
- **ARC_MOF 2025**: **64,393**
- **QMOF_2025**: **1,899**
- **CoRE MOF 2025**: **747**
- **CoRE MOF 2019**: **311**

### Tables

#### Table 1 (254 rows per metadata, 254 in sample payload)
_Table columns (user-facing):_ Structure ID (MOFid), Metal, Network topology, Source database

| Structure ID (MOFid) | Metal | Network topology | Source database |
| --- | --- | --- | --- |
| [Cd].c1ncn(c1)CCn1cncc1 MOFid-v1.pcu.cat0 | [Cd] | pcu | CoRE MOF 2025 |
| O=C(c1ccc(cc1)C(=O)Nc1ccncc1)Nc1ccncc1.[Cd].[O-]C(=O)c1ccc(s1)C(=O)[O-] MOFid... | [Cd] | pcu | CoRE MOF 2025 |
| O1OC=c2c(=C1)c(ccc2c1ccncc1)c1ccncc1.[Cd].[O-]C(=O)c1ccc(cc1)c1ccc(cc1)C(=O)[... | [Cd] | pcu | CoRE MOF 2025 |
| O=C(c1ccc(cc1)Oc1ccc(cc1)C(=O)Nc1ccncc1)Nc1ccncc1.[Co].[O-]C(=O)c1ccc(cc1)C(=... | [Co] | pcu | CoRE MOF 2025 |
| CCc1cnc(c(c1)C(=O)[O-])C(=O)[O-].[Co].n1ccc(cc1)C=Cc1ccncc1 MOFid-v1.pcu.cat0 | [Co] | pcu | CoRE MOF 2025 |
| CCc1cnc(c(c1)C(=O)[O-])C(=O)[O-].[Co].n1ccc(cc1)c1ccncc1 MOFid-v1.pcu.cat0 | [Co] | pcu | CoRE MOF 2025 |
| [Cu].n1ncn(c1)n1cnnc1 MOFid-v1.pcu.cat0 | [Cu] | pcu | CoRE MOF 2025 |
| [Cu].n1ccc(cc1)c1ccncc1 MOFid-v1.sql.cat1 | [Cu] | pcu | CoRE MOF 2025 |

_Showing 8 of 254 rows in payload sample._

---

## 8. Which ZIF-8 refcodes have matching synthesis records?

- **Workflow:** `CQ_D3_ZIF8_REFCODES_SYNTH`
- **Status:** **READY**

### Natural language answer

**2,977** row(s) link **ZIF-8** to **CSD refcodes** and publications (44 distinct refcodes in sample):
- **EWIDUK** (CoRE MOF 2025) — DOI **10.1002/cssc.201100261**
- **FAWCEN** (CoRE MOF 2025) — DOI **10.1021/jp303907p**
- **FAWCEN01** (CoRE MOF 2025) — DOI **10.1021/jp303907p**
- **FAWCEN02** (CoRE MOF 2025) — DOI **10.1021/jp303907p**
- **FAWCEN03** (CoRE MOF 2025) — DOI **10.1021/jp303907p**
Expand the table for the full refcode list.

### Tables

#### Table 1 (54 rows per metadata, 54 in sample payload)
_Table columns (user-facing):_ MOF name, CSD refcode, Source database, Publication DOI

| MOF name | CSD refcode | Source database | Publication DOI |
| --- | --- | --- | --- |
| ZIF-8 | EWIDUK | CoRE MOF 2025 | 10.1002/cssc.201100261 |
| ZIF-8 | FAWCEN | CoRE MOF 2025 | 10.1021/jp303907p |
| ZIF-8 | FAWCEN01 | CoRE MOF 2025 | 10.1021/jp303907p |
| ZIF-8 | FAWCEN02 | CoRE MOF 2025 | 10.1021/jp303907p |
| ZIF-8 | FAWCEN03 | CoRE MOF 2025 | 10.1021/jp303907p |
| Mn-ZIF-8 | FEHHEI | CSD MOF Collection | 10.5517/ccdc.csd.cc1p2w7w |
| ZIF-8-6.05Ar | NIFFIU | CSD MOF Collection | 10.5517/ccdc.csd.cc1q0hy5 |
| ZIF-8 unknown solvate | NIFNOI | CSD MOF Collection | 10.5517/ccdc.csd.cc1q0h6f |

_Showing 8 of 54 rows in payload sample._

---

## 9. Which MOFs have aqueous low-temperature synthesis routes?

- **Workflow:** `CQ_D4_AQUEOUS`
- **Status:** **READY**

### Natural language answer

**1,188** synthesis record(s) match **aqueous / low-temperature** filters (sample):
- `18728 park syn mof` at **293.15** Kelvin, **Mechanochemical**; solvents: 0; acetic acid; hydrochloric acid; water (Park_Syn)
- `24522 park syn mof` at **293.15** Kelvin; solvents: distilled water; dry ethyl ether (Park_Syn)
- `29059 park syn mof` at **293.15** Kelvin; solvents: H2O; NaHCO3; NaNO2; concentrated hydrochloric acid; methylene chloride; water (Park_Syn)
- `25938 park syn mof` at **293.15** Kelvin, **Conventional solvothermal**; solvents: NaOH; water (Park_Syn)
- `19737 park syn mof` at **293.15** Kelvin, **Conventional solvothermal**; solvents: THF; chloroform; distilled water; dry THF (Park_Syn)

### Tables

#### Table 1 (500 rows per metadata, 500 in sample payload)
_Table columns (user-facing):_ MOF, Synthesis method, Solvents, Synthesis temperature, Temperature unit, Source database, At a glance

| MOF | Synthesis method | Solvents | Synthesis temperature | Temperature unit | Source database | At a glance |
| --- | --- | --- | --- | --- | --- | --- |
| 18728 park syn mof | Mechanochemical | 0; acetic acid; hydrochloric acid; water | 293.15 | Kelvin | Park_Syn | Park_Syn |
| 24522 park syn mof |  | distilled water; dry ethyl ether | 293.15 | Kelvin | Park_Syn | Park_Syn |
| 29059 park syn mof |  | H2O; NaHCO3; NaNO2; concentrated hydrochloric acid; methylene chloride; water | 293.15 | Kelvin | Park_Syn | Park_Syn |
| 25938 park syn mof | Conventional solvothermal | NaOH; water | 293.15 | Kelvin | Park_Syn | Park_Syn |
| 19737 park syn mof | Conventional solvothermal | THF; chloroform; distilled water; dry THF | 293.15 | Kelvin | Park_Syn | Park_Syn |
| 10666 park syn mof | Conventional solvothermal | water | 293.15 | Kelvin | Park_Syn | Park_Syn |
| 21238 park syn mof |  | water | 293.15 | Kelvin | Park_Syn | Park_Syn |
| 36696 park syn mof |  | H2O; ethanol | 295.15 | Kelvin | Park_Syn | Park_Syn |

_Showing 8 of 500 rows in payload sample._

---

## 10. Which MOFs are reported as water-stable?

- **Workflow:** `CQ_D5_WATER_STABLE`
- **Status:** **READY**

### Natural language answer

**7,120** MOF(s) carry a reported **water-stability** signal in the KG (top sample):
- **Mn · gfy · ASR** — score/label **1** (CoRE MOF 2025)
- **Mn · gfy · ASR** — score/label **1** (CoRE MOF 2025)
- **Mn · gfy · FSR** — score/label **1** (CoRE MOF 2025)
- **Mn · gfy · FSR** — score/label **1** (CoRE MOF 2025)
- **Fe · pts · ASR** — score/label **0.99** (CoRE MOF 2025)
See the table for **7,120** rows.

### Tables

#### Table 1 (500 rows per metadata, 500 in sample payload)
_Table columns (user-facing):_ MOF, MOF name, Predicted water stability, Source database, At a glance

| MOF | MOF name | Predicted water stability | Source database | At a glance |
| --- | --- | --- | --- | --- |
| Mn · gfy · ASR | - | 1 | CoRE MOF 2025 | CoRE MOF 2025 |
| Mn · gfy · ASR | - | 1 | CoRE MOF 2025 | CoRE MOF 2025 |
| Mn · gfy · FSR | - | 1 | CoRE MOF 2025 | CoRE MOF 2025 |
| Mn · gfy · FSR | - | 1 | CoRE MOF 2025 | CoRE MOF 2025 |
| Fe · pts · ASR | - | 0.99 | CoRE MOF 2025 | CoRE MOF 2025 |
| Co · pts · ASR | - | 0.99 | CoRE MOF 2025 | CoRE MOF 2025 |
| Co · pts · FSR | - | 0.99 | CoRE MOF 2025 | CoRE MOF 2025 |
| Fe · pts · FSR | - | 0.99 | CoRE MOF 2025 | CoRE MOF 2025 |

_Showing 8 of 500 rows in payload sample._

---

## 11. How many experimental Cu-containing MOFs are recorded?

- **Workflow:** `CQ03_CU_EXPERIMENTAL`
- **Status:** **READY**

### Natural language answer

The knowledge graph records **9,325** experimental Cu-containing MOFs.

### Tables

#### Table 1 (1 rows per metadata, 1 in sample payload)
_Table columns (user-facing):_ Number of matching MOFs

| Number of matching MOFs |
| --- |
| 9325 |

---

## 12. How many experimental MOFs have pcu topology?

- **Workflow:** `CQ10_EXP_PCU`
- **Status:** **READY**

### Natural language answer

The knowledge graph records **1,778** experimental MOFs have pcu topology.

### Tables

#### Table 1 (1 rows per metadata, 1 in sample payload)
_Table columns (user-facing):_ Number of matching MOFs

| Number of matching MOFs |
| --- |
| 1778 |

---
