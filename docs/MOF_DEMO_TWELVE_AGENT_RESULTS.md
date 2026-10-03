# MOF demo — 12 canonical questions (live ReAct agent)

Generated: 2026-10-02 18:17 UTC

Execution path: `route_question` → `KgqaAgent` (ReAct) → MCP (`run_competency_online`, optional identity tools) → `kgqa_result_to_marie`.

Post-feedback fixes (Q6/Q9/Q10): David-aligned Zr+carboxylate SPARQL, full water-stability filter (Burtch/acid/base/details), synthesis solvent normalization and smarter table columns.

- **Model:** `gpt-4o-mini`
- **Recursion limit:** 80

## Summary

- **Ready (agent + NL + table):** 12 / 12

| # | Workflow | ms | Tools | Status |
| --- | --- | ---: | --- | --- |
| 1 | `CQ01_PLD_UIO66` | 53038 | run_competency_online, enrich_mof_table_rows | **READY** |
| 2 | `CQ07_SAME_TOPO_ZIF8` | 31145 | run_competency_online, enrich_mof_table_rows, lookup_mof_identity_by_entries | **READY** |
| 3 | `CQ04_SYNTHESIS_UIO66` | 22513 | run_competency_online, enrich_mof_table_rows | **READY** |
| 4 | `CQ_D6_THERMAL` | 34836 | run_competency_online, enrich_mof_table_rows | **READY** |
| 5 | `CQ_D7_BINARY_UPTAKE` | 110254 | run_competency_online, enrich_mof_table_rows, lookup_mof_identity_by_entries | **READY** |
| 6 | `CQ_D1_ZR_COOH` | 37960 | run_competency_online, enrich_mof_table_rows | **READY** |
| 7 | `CQ_D2_PCU_ALL` | 74520 | run_competency_online, enrich_mof_table_rows | **READY** |
| 8 | `CQ_D3_ZIF8_REFCODES_SYNTH` | 9781 | run_competency_online | **READY** |
| 9 | `CQ_D4_AQUEOUS` | 29386 | run_competency_online, enrich_mof_table_rows, lookup_mof_identity_by_entries | **READY** |
| 10 | `CQ_D5_WATER_STABLE` | 32529 | run_competency_online, enrich_mof_table_rows | **READY** |
| 11 | `CQ03_CU_EXPERIMENTAL` | 20089 | run_competency_online, enrich_mof_table_rows | **READY** |
| 12 | `CQ10_EXP_PCU` | 5944 | run_competency_online | **READY** |

---

## 1. What are the average and variance of the pore limiting diameter for UiO-66?

- **Workflow:** `CQ01_PLD_UIO66`
- **Agent driven:** True
- **Tools:** `run_competency_online, enrich_mof_table_rows`
- **Elapsed:** 53038 ms
- **Status:** **READY**

### Natural language answer

For **UiO-66**, average pore limiting diameter (PLD) is **3.81 Å** with variance **0.04 Å²** (n=4 PLD values).
PLD values by source: **CSD MOF Collection**: 3.5284 Å (RUBTAK), 3.7332 Å (RUBTAK01); **CoRE MOF 2025**: 4.00843 Å (RUBTAK01), 3.95727 Å (RUBTAK03).

### Tables

#### Table 1 (1 rows in payload)
| Average PLD (Å) | PLD variance (Å²) | Sample count |
| --- | --- | --- |
| 3.806825 | 0.03655484882500026 | 4 |

---

## 2. Which MOFs have the same topology as ZIF-8?

- **Workflow:** `CQ07_SAME_TOPO_ZIF8`
- **Agent driven:** True
- **Tools:** `run_competency_online, enrich_mof_table_rows, lookup_mof_identity_by_entries`
- **Elapsed:** 31145 ms
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

#### Table 1 (150 rows in payload)
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

_Showing 8 of 150 rows._

---

## 3. What synthesis routes are recorded for UiO-66?

- **Workflow:** `CQ04_SYNTHESIS_UIO66`
- **Agent driven:** True
- **Tools:** `run_competency_online, enrich_mof_table_rows`
- **Elapsed:** 22513 ms
- **Status:** **READY**

### Natural language answer

**1** synthesis route(s) from **Park_Syn** / **SynMOF** for **UiO-66**:
- **Route A** — **Ce-UiO-66-BPyDC**, solvents: N,N-dimethylformamide; aqueous, yield **38%** (Park_Syn)
**Route A** with N,N-dimethylformamide; aqueous has the highest reported yield of **38%**.

### Tables

#### Table 1 (1 rows in payload)
| MOF name | Yield (%) | Synthesis method | Solvents | Source database | Publication DOI |
| --- | --- | --- | --- | --- | --- |
| Ce-UiO-66-BPyDC | 38 | Conventional solvothermal | N,N-dimethylformamide; aqueous | Park_Syn | 10.1021/acs.cgd.6b01512 |

---

## 4. Which MOFs are reported as thermally stable?

- **Workflow:** `CQ_D6_THERMAL`
- **Agent driven:** True
- **Tools:** `run_competency_online, enrich_mof_table_rows`
- **Elapsed:** 34836 ms
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

#### Table 1 (500 rows in payload)
| MOF | CSD refcode | Thermal stability (°C) | Source database | Publication DOI |
| --- | --- | --- | --- | --- |
| IFAREN | IFAREN | 654.3239796 | MOFSimplify Thermal Dataset | 10.1021/ic701573r |
| EQERIC | EQERIC | 639.1312089 | MOFSimplify Thermal Dataset | 10.1039/c1cc10899a |
| IFAQUC | IFAQUC | 634.8680022 | MOFSimplify Thermal Dataset | 10.1021/ic701573r |
| KIFKEQ | KIFKEQ | 626.173347 | MOFSimplify Thermal Dataset | 10.1039/b705028c |
| MUMYAW | MUMYAW | 604.1485695 | MOFSimplify Thermal Dataset | 10.1002/ejic.201500294 |
| KINFEU | KINFEU | 601.5644621 | MOFSimplify Thermal Dataset | 10.1021/cg400531j |
| WAPSUE | WAPSUE | 598.9593238 | MOFSimplify Thermal Dataset | 10.1039/C7DT00615B |
| NAQQED | NAQQED | 598.8876929 | MOFSimplify Thermal Dataset | 10.1002/ejic.201100944 |

_Showing 8 of 500 rows._

---

## 5. Which MOFs have high binary gas uptake?

- **Workflow:** `CQ_D7_BINARY_UPTAKE`
- **Agent driven:** True
- **Tools:** `run_competency_online, enrich_mof_table_rows, lookup_mof_identity_by_entries`
- **Elapsed:** 110254 ms
- **Status:** **READY**

### Natural language answer

The MOF with the highest binary-gas uptake has **MOFid**: `N=N.O=C1N(c2ccc(c(c2)C(C)C)C(=O)[O-])C(=O)c2c3c1ccc1c3c(cc2)c2c3c1ccc1c3c(cc2)C(=O)N(C1=O)c1ccc(c(c1)C(C)C)C(=O)[O-].[Cu][Cu].[O-]C(=O)C=CC(=O)[O-] MOFid-v1.nbo.cat0`.
- Post-combustion (CO2N2 at 0.9 bar, 298 K (mmolg)): **7.02 mmol/g**
- Pre-combustion (CO2H2 at 40.0 bar, 313 K (mmolg)): **10.7 mmol/g**
Source: **ARC_MOF 2025**.
Pore properties: **PLD** = 3.62954 Å, **LFPD** = 4.99139 Å.
(127,137 MOFs exceed the uptake thresholds.)

### Tables

#### Table 1 (500 rows in payload)
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

_Showing 8 of 500 rows._

---

## 6. Which Zr-containing MOFs have carboxylate linkers?

- **Workflow:** `CQ_D1_ZR_COOH`
- **Agent driven:** True
- **Tools:** `run_competency_online, enrich_mof_table_rows`
- **Elapsed:** 37960 ms
- **Status:** **READY**

### Natural language answer

**222** MOF(s) match the **metal / linker** chemistry filters (sample):
By source in sample: **MOFx-DB Tobacco** (185), **QMOF_2025** (22), **CSD MOF Collection** (14), **CoRE MOF 2025** (1).
- **WNdZr · nan · FSR** — CoRE MOF 2025
- **BEPVAW** — CSD MOF Collection
- **FIPBAK** — CSD MOF Collection
- **HEWKAZ** — CSD MOF Collection
- **IXEGIE** — CSD MOF Collection

### Tables

#### Table 1 (222 rows in payload)
| MOF | Source database |
| --- | --- |
| WNdZr · nan · FSR | CoRE MOF 2025 |
| BEPVAW | CSD MOF Collection |
| FIPBAK | CSD MOF Collection |
| HEWKAZ | CSD MOF Collection |
| IXEGIE | CSD MOF Collection |
| JOQXOG | CSD MOF Collection |
| JUQLAM | CSD MOF Collection |
| JUQLEQ | CSD MOF Collection |

_Showing 8 of 222 rows._

---

## 7. How is pcu topology distributed across MOF source databases?

- **Workflow:** `CQ_D2_PCU_ALL`
- **Agent driven:** True
- **Tools:** `run_competency_online, enrich_mof_table_rows`
- **Elapsed:** 74520 ms
- **Status:** **READY**

### Natural language answer

**272,711** MOF(s) with **pcu** topology appear in this sample; **5** source database(s):
- **Tobassco**: **205,361**
- **ARC_MOF 2025**: **64,393**
- **QMOF_2025**: **1,899**
- **CoRE MOF 2025**: **747**
- **CoRE MOF 2019**: **311**

### Tables

#### Table 1 (254 rows in payload)
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

_Showing 8 of 254 rows._

---

## 8. Which ZIF-8 refcodes have matching synthesis records?

- **Workflow:** `CQ_D3_ZIF8_REFCODES_SYNTH`
- **Agent driven:** True
- **Tools:** `run_competency_online`
- **Elapsed:** 9781 ms
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

#### Table 1 (54 rows in payload)
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

_Showing 8 of 54 rows._

---

## 9. Which MOFs have aqueous low-temperature synthesis routes?

- **Workflow:** `CQ_D4_AQUEOUS`
- **Agent driven:** True
- **Tools:** `run_competency_online, enrich_mof_table_rows, lookup_mof_identity_by_entries`
- **Elapsed:** 29386 ms
- **Status:** **READY**

### Natural language answer

**1,188** synthesis record(s) match **aqueous / low-temperature** filters (sample):
- `18728 park syn mof` at **293.15** Kelvin, **Mechanochemical**; solvents: acetic acid; hydrochloric acid; water (Park_Syn)
- `24522 park syn mof` at **293.15** Kelvin; solvents: water; dry ethyl ether (Park_Syn)
- `29059 park syn mof` at **293.15** Kelvin; solvents: water; NaHCO3; NaNO2; concentrated hydrochloric acid; methylene chloride (Park_Syn)
- `25938 park syn mof` at **293.15** Kelvin, **Conventional solvothermal**; solvents: NaOH; water (Park_Syn)
- `19737 park syn mof` at **293.15** Kelvin, **Conventional solvothermal**; solvents: THF; chloroform; water; dry THF (Park_Syn)

### Tables

#### Table 1 (500 rows in payload)
| MOF | Synthesis method | Solvents | Synthesis temperature | Temperature unit | Source database | At a glance |
| --- | --- | --- | --- | --- | --- | --- |
| 18728 park syn mof | Mechanochemical | acetic acid; hydrochloric acid; water | 293.15 | Kelvin | Park_Syn | Mechanochemical · 293.15 Kelvin · solvents: acetic acid; hydrochloric acid; w... |
| 24522 park syn mof |  | water; dry ethyl ether | 293.15 | Kelvin | Park_Syn | 293.15 Kelvin · solvents: water; dry ethyl ether |
| 29059 park syn mof |  | water; NaHCO3; NaNO2; concentrated hydrochloric acid; methylene chloride | 293.15 | Kelvin | Park_Syn | 293.15 Kelvin · solvents: water; NaHCO3; NaNO2; concentrated hydrochloric aci... |
| 25938 park syn mof | Conventional solvothermal | NaOH; water | 293.15 | Kelvin | Park_Syn | Conventional solvothermal · 293.15 Kelvin · solvents: NaOH; water |
| 19737 park syn mof | Conventional solvothermal | THF; chloroform; water; dry THF | 293.15 | Kelvin | Park_Syn | Conventional solvothermal · 293.15 Kelvin · solvents: THF; chloroform; water;... |
| 10666 park syn mof | Conventional solvothermal | water | 293.15 | Kelvin | Park_Syn | Conventional solvothermal · 293.15 Kelvin · solvents: water |
| 21238 park syn mof |  | water | 293.15 | Kelvin | Park_Syn | 293.15 Kelvin · solvents: water |
| 36696 park syn mof |  | water; ethanol | 295.15 | Kelvin | Park_Syn | 295.15 Kelvin · solvents: water; ethanol |

_Showing 8 of 500 rows._

---

## 10. Which MOFs are reported as water-stable?

- **Workflow:** `CQ_D5_WATER_STABLE`
- **Agent driven:** True
- **Tools:** `run_competency_online, enrich_mof_table_rows`
- **Elapsed:** 32529 ms
- **Status:** **READY**

### Natural language answer

**7,222** MOF(s) carry a reported **water-stability** signal in the KG (top sample):
- **YOYQOU** — predicted **1** (CoRE MOF 2025)
- **YOYQOU** — predicted **1** (CoRE MOF 2025)
- **YOYRIP** — predicted **1** (CoRE MOF 2025)
- **YOYRIP** — predicted **1** (CoRE MOF 2025)
- **GOQSIQ** — predicted **0.99** (CoRE MOF 2025)
See the table for **7,222** rows.

### Tables

#### Table 1 (500 rows in payload)
| MOF | MOF name | CSD refcode | Predicted water stability | Source database | At a glance |
| --- | --- | --- | --- | --- | --- |
| YOYQOU | - | YOYQOU | 1 | CoRE MOF 2025 | CoRE MOF 2025 |
| YOYQOU | - | YOYQOU | 1 | CoRE MOF 2025 | CoRE MOF 2025 |
| YOYRIP | - | YOYRIP | 1 | CoRE MOF 2025 | CoRE MOF 2025 |
| YOYRIP | - | YOYRIP | 1 | CoRE MOF 2025 | CoRE MOF 2025 |
| GOQSIQ | - | GOQSIQ | 0.99 | CoRE MOF 2025 | CoRE MOF 2025 |
| GOQSIQ | - | GOQSIQ | 0.99 | CoRE MOF 2025 | CoRE MOF 2025 |
| UKUBUY | - | UKUBUY | 0.99 | CoRE MOF 2025 | CoRE MOF 2025 |
| UKUBUY | - | UKUBUY | 0.99 | CoRE MOF 2025 | CoRE MOF 2025 |

_Showing 8 of 500 rows._

---

## 11. How many experimental Cu-containing MOFs are recorded?

- **Workflow:** `CQ03_CU_EXPERIMENTAL`
- **Agent driven:** True
- **Tools:** `run_competency_online, enrich_mof_table_rows`
- **Elapsed:** 20089 ms
- **Status:** **READY**

### Natural language answer

The knowledge graph records **9,325** experimental Cu-containing MOFs.

### Tables

#### Table 1 (1 rows in payload)
| Number of matching MOFs |
| --- |
| 9325 |

---

## 12. How many experimental MOFs have pcu topology?

- **Workflow:** `CQ10_EXP_PCU`
- **Agent driven:** True
- **Tools:** `run_competency_online`
- **Elapsed:** 5944 ms
- **Status:** **READY**

### Natural language answer

The knowledge graph records **1,778** experimental MOFs have pcu topology.

### Tables

#### Table 1 (1 rows in payload)
| Number of matching MOFs |
| --- |
| 1778 |

---
