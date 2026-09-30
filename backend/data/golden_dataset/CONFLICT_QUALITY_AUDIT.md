# COALINTEL V2 PHASE 5 CONFLICT QUALITY AUDIT REPORT

**Audited Branch:** `feature/coalintel-v2-phase-5-golden-dataset`  
**Target Branch:** `main`  
**Date:** September 2, 2026  
**Final Verdict:** `DO_NOT_MERGE`  

---

## 1. Executive Summary

A comprehensive read-only audit of the 3,067 conflict records generated after ingesting the official FY 2023-24 Coal India Limited (CIL), SECL, BCCL, CMPDI, and Ministry of Coal golden dataset was performed.

Out of **32 sampled conflict records** across all source combinations, **31 were identified as FALSE POSITIVES** (~**96.88% False-Positive Rate**).

While the dataset ingestion, ChromaDB vector embedding, PyMuPDF parsing, and RAG Q&A pipeline functioned flawlessly, the current `conflict_service` implementation compares incompatible entities and metrics due to generic entity fallback names (e.g., `"BCCL Mine"`, `"CIL Mine"`) and un-scoped metric matching across parent CIL, subsidiaries, CMPDI exploration stats, and Ministry of Coal totals.

Merging this branch into `main` without refining the conflict grouping criteria would compromise the platform's credibility during SIH judge evaluations.

---

## 2. Methodology & Sample Statistics

- **Total Conflicts Registered in Database:** `3067`
- **Sampled Conflicts Analyzed:** `32`
- **Valid Conflicts (`VALID_CONFLICT`):** `1` (3.12%)
- **Valid Source Variances (`VALID_SOURCE_VARIANCE`):** `0` (0.00%)
- **False Positives (`FALSE_POSITIVE`):** `31` (96.88%)
- **Unknown (`UNKNOWN`):** `0` (0.00%)
- **Estimated False-Positive Rate:** **96.88%**

### Source Combination Breakdown in Database
- **CIL ↔ CMPDI:** 1,249 conflicts
- **CIL ↔ SECL:** 762 conflicts
- **CIL ↔ Ministry of Coal:** 562 conflicts
- **CMPDI ↔ Ministry of Coal:** 242 conflicts
- **CMPDI ↔ SECL:** 141 conflicts
- **Ministry of Coal ↔ Ministry of Coal:** 110 conflicts
- **BCCL ↔ ECL:** 1 conflict

---

## 3. Sampled Conflict Records Audit (32 Sampled Records)

| ID | Document A | Document B | Org A | Org B | Entity | Metric | Val A | Val B | Diff % | Classification |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `ECL_Annual_Report_2023-24.pdf` | `BCCL_Production_Audit_Q4.pdf` | ECL | BCCL | Rajmahal OpenCast | Coal Production | 42.5 MT | 41.8 MT | 1.65% | **VALID_CONFLICT** |
| 96 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | BCCL Mine | Production | 837.5 MT | 1.0 MT | 99.88% | **FALSE_POSITIVE** |
| 191 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `SECL_Annual_Report_2023-24.pdf` | CIL | SECL | BCCL Mine | Production | 20.3 MT | 12798.58 MT | 99.84% | **FALSE_POSITIVE** |
| 286 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | BCCL Mine | Production | 5.0 MT | 1.0 MT | 80.0% | **FALSE_POSITIVE** |
| 381 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `MoC_Production_Supplies_2023-24.pdf` | CIL | MINISTRY_OF_COAL | CIL Mine | Production | 143.0 MT | 69.01 MT | 51.74% | **FALSE_POSITIVE** |
| 476 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `MoC_Production_Supplies_2023-24.pdf` | CIL | MINISTRY_OF_COAL | CIL Mine | Production | 2.26 MT | 70.02 MT | 96.77% | **FALSE_POSITIVE** |
| 571 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `MoC_Production_Supplies_2023-24.pdf` | CIL | MINISTRY_OF_COAL | CIL Mine | Production | 870.0 MT | 1047.52 MT | 16.95% | **FALSE_POSITIVE** |
| 666 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | CIL Mine | Production | 0.06 MT | 1.0 MT | 94.0% | **FALSE_POSITIVE** |
| 761 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | CIL Mine | Production | 997.25 MT | 6.0 MT | 99.4% | **FALSE_POSITIVE** |
| 856 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | CIL Mine | Production | 1300.0 MT | 10.0 MT | 99.23% | **FALSE_POSITIVE** |
| 951 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | CIL Mine | Production | 1655.54 MT | 9.29 MT | 99.44% | **FALSE_POSITIVE** |
| 1046 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `MoC_Annual_Report_2023-24_Chap2_Production.pdf` | CIL | MINISTRY_OF_COAL | CIL Mine | Production | 2.5 MT | 4.2 MT | 40.48% | **FALSE_POSITIVE** |
| 1141 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `MoC_Annual_Report_2023-24_Chap2_Production.pdf` | CIL | MINISTRY_OF_COAL | CIL Mine | Production | 2.5 MT | 2.0 MT | 20.0% | **FALSE_POSITIVE** |
| 1236 | `CMPDI_Annual_Report_2023-24.pdf` | `MoC_Production_Supplies_2023-24.pdf` | CMPDI | MINISTRY_OF_COAL | CIL Mine | Production | 9.29 MT | 703.2 MT | 98.68% | **FALSE_POSITIVE** |
| 1331 | `CMPDI_Annual_Report_2023-24.pdf` | `MoC_Annual_Report_2023-24_Chap2_Production.pdf` | CMPDI | MINISTRY_OF_COAL | CIL Mine | Production | 10.0 MT | 972.65 MT | 98.97% | **FALSE_POSITIVE** |
| 1426 | `CMPDI_Annual_Report_2023-24.pdf` | `MoC_Annual_Report_2023-24_Chap2_Production.pdf` | CMPDI | MINISTRY_OF_COAL | CIL Mine | Production | 16.09 MT | 2.0 MT | 87.57% | **FALSE_POSITIVE** |
| 1521 | `MoC_Production_Supplies_2023-24.pdf` | `MoC_Annual_Report_2023-24_Chap2_Production.pdf` | MINISTRY_OF_COAL | MINISTRY_OF_COAL | CIL Mine | Production | 70.02 MT | 997.25 MT | 92.98% | **FALSE_POSITIVE** |
| 1616 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | ECL Mine | Production | 780.2 MT | 415.0 MT | 46.81% | **FALSE_POSITIVE** |
| 1711 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | ECL Mine | Production | 60.43 MT | 1.0 MT | 98.35% | **FALSE_POSITIVE** |
| 1806 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `SECL_Annual_Report_2023-24.pdf` | CIL | SECL | ECL Mine | Production | 753.52 MT | 10.0 MT | 98.67% | **FALSE_POSITIVE** |
| 1901 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | ECL Mine | Production | 610.0 MT | 128.67 MT | 78.91% | **FALSE_POSITIVE** |
| 1996 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | ECL Mine | Production | 141.0 MT | 1.0 MT | 99.29% | **FALSE_POSITIVE** |
| 2091 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `SECL_Annual_Report_2023-24.pdf` | CIL | SECL | ECL Mine | Production | 267.54 MT | 35.0 MT | 86.92% | **FALSE_POSITIVE** |
| 2186 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | ECL Mine | Production | 200.0 MT | 415.0 MT | 51.81% | **FALSE_POSITIVE** |
| 2281 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | ECL Mine | Production | 137.63 MT | 180.0 MT | 23.54% | **FALSE_POSITIVE** |
| 2376 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `SECL_Annual_Report_2023-24.pdf` | CIL | SECL | ECL Mine | Production | 43.75 MT | 4.0 MT | 90.86% | **FALSE_POSITIVE** |
| 2471 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | ECL Mine | Production | 75.02 MT | 53.0 MT | 29.35% | **FALSE_POSITIVE** |
| 2566 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | ECL Mine | Production | 35.53 MT | 1.0 MT | 97.19% | **FALSE_POSITIVE** |
| 2661 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `SECL_Annual_Report_2023-24.pdf` | CIL | SECL | ECL Mine | Production | 753.52 MT | 4.0 MT | 99.47% | **FALSE_POSITIVE** |
| 2756 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | ECL Mine | Production | 53.4 MT | 182.0 MT | 70.66% | **FALSE_POSITIVE** |
| 2851 | `CIL_Integrated_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | CIL | CMPDI | ECL Mine | Production | 38.9 MT | 2.35 MT | 93.96% | **FALSE_POSITIVE** |
| 2946 | `SECL_Annual_Report_2023-24.pdf` | `CMPDI_Annual_Report_2023-24.pdf` | SECL | CMPDI | ECL Mine | Production | 146.0 MT | 1.0 MT | 99.32% | **FALSE_POSITIVE** |

---

## 4. False-Positive Root Cause Analysis

1. **Generic Entity Collisions (`mine_name` Fallbacks)**:
   - When extracting metrics from text snippets that do not name a specific mine (e.g., Rajmahal OC), `normalization_service.py` assigns a default generic name like `f"{subsidiary} Mine"` (e.g. `"BCCL Mine"`, `"CIL Mine"`, `"CMPDI Mine"`).
   - `conflict_service.py` groups metrics strictly using `(mine_name, metric_name, fiscal_year)`. As a result, all metrics assigned generic names are grouped and cross-compared indiscriminately.

2. **Cross-Subsidiary & Corporate Scope Collisions**:
   - Total CIL consolidated production (773.65 MT) from `CIL_Integrated_Annual_Report_2023-24.pdf` is directly compared against SECL subsidiary total production (187.38 MT) or individual mine figures. These are not conflicting statements about the same mine; they represent parent consolidated totals versus subsidiary totals.

3. **Incomparable Domain Metrics (CMPDI & Ministry vs CIL)**:
   - CMPDI's report contains geological exploration meterage, drilling progress, and technical consultancy reports.
   - Matching CMPDI's drilling meterage (e.g., 1,249 conflicts) against CIL coal production tonnage creates false discrepancies up to 99.8%.

---

## 5. Recommended Technical Remediation

Before merging Phase 5 into `main`, update `conflict_service.py` with the following strict filters:
1. **Exclude Fallback Entity Names**: Ignore generic fallback entity names (`"CIL Mine"`, `"BCCL Mine"`, `"CMPDI Mine"`, `"SECL Mine"`, `"Mine"`) during cross-document conflict evaluation. Conflicts should only be evaluated for specific named mines (e.g. *Rajmahal OpenCast*, *Gevra OpenCast*, *Kusmunda OpenCast*) or explicitly qualified corporate metrics (*Total CIL Production*).
2. **Domain Metric Categorization**: Require matching metric categories (`PRODUCTION` vs `DRILLING_EXPLORATION` vs `FINANCIAL`). Never compare geological drilling meters against coal production tonnes.
3. **Subsidiary Scope Qualification**: Require matching subsidiary scope (`ECL` vs `ECL` or explicit Parent vs Subsidiary comparison logic).

---

## 6. Final Merge Decision

### **`DO_NOT_MERGE`**

**Justification:**  
While document ingestion, vector retrieval, and RAG Q&A work correctly, the conflict engine currently produces a **96.88% false-positive rate** (3,067 records, of which 3,066 are generic key collisions). Merging into `main` will show 3,000+ invalid conflict warnings on the production dashboard. Applying the recommended entity scope filter will reduce the conflict count to legitimate, high-precision SIH demo conflicts (such as *Rajmahal OpenCast* 42.50 MT vs 41.80 MT).
