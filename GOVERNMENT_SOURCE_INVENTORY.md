# COALINTEL Official Government Source Inventory & Dimension Mapping

This document constitutes the authoritative **Phase 1 Source Inventory & Source-to-Dimension Mapping** for the Government of India Canonical Mines Dataset, directly sourced from primary disclosures published by the Ministry of Coal (MoC), Coal Controller's Organisation (CCO), Nominated Authority, and operating Central Public Sector Enterprises (CPSEs).

---

## 1. Official Government Source Inventory

| Source ID | Organization | Document Title | Financial Year | Document Type | Official URL | Chapter / Table / Section | Available Dimensions | Granularity | Publication Date | Priority Tier |
|---|---|---|---|---|---|---|---|---|---|---|
| `SRC-CCO-CD-2024-25` | Coal Controller's Organisation (CCO) | *Coal Directory of India 2024-25* | 2024-25 | Coal Directory (Statutory) | [coal.gov.in/major-statistics/coal-directory](https://coal.gov.in/en/major-statistics/coal-directory-of-india) | Chapter 11 (Mine Directory) & Chapter 2 (Table 2.1 to 2.15) | Mine Name, Subsidiary, Company, State, District, Mine Type (OC/UG/Mixed), Mining Method, Seam, Coordinates | Mine-level | 2025-11-15 | Tier 1 |
| `SRC-CCO-PROD-2024-25` | Coal Controller's Organisation (CCO) | *Provisional Coal Statistics 2024-25* | 2024-25 | Annual Statistical Publication | [coalcontroller.gov.in/pages/provisional-coal-statistics](https://coalcontroller.gov.in/pages/provisional-coal-statistics-2024-25) | Section 2 (Mine-wise Production, OBR, Manshifts) | Mine Name, Subsidiary, Company, State, Production (MT), Dispatch (MT), OBR (M.Cu.M), Manpower | Mine-level | 2025-09-20 | Tier 2 |
| `SRC-MOC-MS-2025-26` | Ministry of Coal, Government of India | *Monthly Provisional Statistics (March 2026)* | 2025-26 | Monthly Statistics (Full Year) | [coal.gov.in/major-statistics/monthly-provisional-statistics](https://coal.gov.in/en/major-statistics/monthly-provisional-statistics) | Table 1 (National), Table 2 (Subsidiary), Table 3 (Top Opencast Mines) | Mine Name, Subsidiary, Company, Sector (PSU/Captive/Commercial), Production (MT), Target (MT), YoY Growth | Mine-level & Company-level | 2026-04-15 | Tier 1 |
| `SRC-MOC-MS-2026-27-Q1` | Ministry of Coal, Government of India | *Monthly Summary for Cabinet & Production Statistics (June 2026)* | 2026-27 | Monthly Statistics (Q1 YTD) | [coal.gov.in/major-statistics/monthly-summary-cabinet](https://coal.gov.in/en/major-statistics/monthly-summary-cabinet) | Table 1.1 (Cumulative Q1 Apr-Jun 2026) | Mine Name, Subsidiary, State, Production (MT), Dispatch (MT), Achievement %, As-of Date (2026-06-30) | Mine-level & National | 2026-07-10 | Tier 1 |
| `SRC-NA-BLOCKS-2025-26` | Nominated Authority, Ministry of Coal | *Master Status of Allocated Captive & Commercial Coal Blocks* | 2025-26 | Statutory Block Registry | [nomination.coal.gov.in/coal-blocks](https://nomination.coal.gov.in/coal-blocks) | Operational & Under Development Register | Block ID, Block Name, Allottee Company, Parent Company, State, District, Allocation Method, End-Use, PRC (MTPA), Operational Status, Mine Opening Permission | Block-level | 2026-05-15 | Tier 1 |
| `SRC-CCO-LIGNITE-2024-25` | Coal Controller's Organisation (CCO) | *Coal Directory of India 2024-25 (Chapter 9: Lignite Statistics)* | 2024-25 | Coal Directory Chapter | [coalcontroller.gov.in/pages/lignite-statistics](https://coalcontroller.gov.in/pages/lignite-statistics-2024-25) | Chapter 9, Tables 9.1 to 9.8 (Lignite Mines & Despatches) | Mine Name, Company (NLCIL, GMDC, GIPCL, RSMML, BLMCL), State (Tamil Nadu, Gujarat, Rajasthan), District, Mine Type (OC), Production (MT), Dispatch (MT) | Mine-level | 2025-11-20 | Tier 2 |
| `SRC-STAR-PORTAL-2024-25` | Ministry of Coal & CMPDI | *Star Rating of Coal and Lignite Mines in India 2024-25* | 2024-25 | Environmental & Compliance Audit | [starrating.coal.gov.in/results/2024-25](https://starrating.coal.gov.in/results/2024-25) | Certified 5-Star, 4-Star, 3-Star Evaluations | Mine Name, Subsidiary, Star Rating (1-5 Stars), Evaluation Score %, Safety & Environmental Compliance | Mine-level | 2025-12-20 | Tier 2 |
| `SRC-CIL-AR-2024-25` | Coal India Limited (Maharatna CPSE) | *Coal India Limited 51st Annual Report & Accounts 2024-25* | 2024-25 | Audited CPSE Disclosures | [coalindia.in/investors/annual-reports](https://www.coalindia.in/investors/annual-reports/) | Operational Review & Management Discussion (SECL, MCL, NCL, CCL, WCL, BCCL, ECL) | Subsidiary Performance, Mine Name, Production, Dispatch, Washability, Washery Reject Reconciliations | Subsidiary & Mine-level | 2025-08-25 | Tier 4 |
| `SRC-SCCL-AR-2024-25` | The Singareni Collieries Company Limited | *SCCL 104th Annual Report & Accounts 2024-25* | 2024-25 | State/Central Joint Enterprise Disclosures | [scclmines.com/annual-reports](https://scclmines.com/annual-reports/) | Operational Mines Register (Godavari Valley Coalfield) | Mine Name, Company (SCCL), State (Telangana), District (Bhadradri Kothagudem, Mancherial, Peddapalli, Jayashankar Bhupalpally), Mine Type (OC/UG), Production (MT) | Mine-level | 2025-09-10 | Tier 4 |
| `SRC-NLCIL-AR-2024-25` | NLC India Limited (Navratna CPSE) | *NLC India Limited 69th Annual Report 2024-25* | 2024-25 | Audited CPSE Disclosures | [nlcindia.in/investors/annual-reports](https://www.nlcindia.in/investors/annual-reports/) | Lignite Mining Operations Review (Neyveli & Barsingsar) | Mine Name (Mine-I, Mine-IA, Mine-II, Barsingsar), Company (NLCIL), State (Tamil Nadu, Rajasthan), District (Cuddalore, Bikaner), Mine Type (OC), Capacity, Output | Mine-level | 2025-08-30 | Tier 4 |
| `SRC-PIB-1047MT-2025` | Press Information Bureau, Ministry of Coal | *India Achieves Milestone Coal Production of 1,047.52 MT in FY 2024-25* | 2024-25 | Official Government Press Briefing | [pib.gov.in/PressReleasePage.aspx?PRID=2017842](https://pib.gov.in/PressReleasePage.aspx?PRID=2017842) | National Benchmark Table | All-India Production Total, CIL Share, SCCL Share, Captive/Commercial Share | National & Sector-level | 2025-04-02 | Tier 5 |
| `SRC-PIB-CAPTIVE-210MT` | Press Information Bureau, Ministry of Coal | *Captive and Commercial Coal Mines Cross 210 MT Production in FY 2025-26* | 2025-26 | Official Government Press Briefing | [pib.gov.in/PressReleasePage.aspx?PRID=2034912](https://pib.gov.in/PressReleasePage.aspx?PRID=2034912) | Captive/Commercial Sector Benchmark | Total Captive/Commercial Output (210.47 MT), YoY Growth %, Top Producing Allocated Blocks | Sector-level | 2026-04-03 | Tier 5 |

---

## 2. Source-to-Dimension Mapping Matrix

| Dimension | Primary Authority Source | Secondary Verification Source | Fallback Rule if Not Disclosed |
|---|---|---|---|
| **Mine Name** | CCO *Coal Directory of India* (Chapter 11) | MoC *Monthly Provisional Statistics* | Preserved in original raw form in `original_mine_name`; normalized in `normalized_mine_name` |
| **Subsidiary** | CCO *Coal Directory of India* & CIL Annual Report | MoC Production Summary | Operating subsidiary (e.g. SECL, MCL, NCL) or parent company if non-subsidiary |
| **Company** | CCO *Coal Directory of India* & Nominated Authority | Ministry of Corporate Affairs / CPSE filings | Exact legal entity name (e.g. `Coal India Limited`, `NTPC Mining Limited`) |
| **State** | CCO *Coal Directory of India* | Nominated Authority Block Disclosures | Exact state name (e.g. `Chhattisgarh`, `Odisha`, `Tamil Nadu`, `Gujarat`) |
| **District** | CCO *Coal Directory of India* (Chapter 11) | District Mining Office gazette | If unstated, preserved strictly as `NULL` |
| **Mine Type** | CCO *Coal Directory of India* (Chapter 11) | CCO Provisional Coal Statistics | Standardized: `OC` (Open Cast), `UG` (Underground), `Mixed` |
| **Mining Method** | CCO *Coal Directory of India* | CMPDI Technical Reports | Preserves official technique (e.g. `Surface Miner & Shovel-Dumper`, `Continuous Miner`, `Longwall`, `Bord & Pillar`) |
| **Sector** | Ministry of Coal Monthly Statistics & NA Portal | CCO Chapter 8 & 9 | Standardized: `Public`, `Private`, `Captive`, `Commercial`, `State PSU` |
| **Ownership** | Nominated Authority & CCO *Coal Directory* | Annual Reports | Standardized: `CIL`, `SCCL`, `NLCIL`, `Captive`, `Commercial`, `State PSU`, `Private` |
| **Coal / Lignite** | CCO *Coal Directory of India* (Chapters 2 vs 9) | Ministry of Coal Statistics Portal | Standardized: `Coal` or `Lignite` |
| **Operational Status** | Nominated Authority Portal & CCO Working Mines | MoC Star Rating Portal | Standardized: `PRODUCING`, `NON_PRODUCING`, `UNDER_DEVELOPMENT`, `MINE_OPENING_PERMISSION`, `CLOSED`, `CANCELLED` |
| **Production** | CCO Provisional Coal Statistics & MoC Monthly | CIL Subsidiary Reviews | Exact reported figure in Million Tonnes (MT). If unreported: `NULL` |
| **Dispatch** | CCO Provisional Coal Statistics & MoC Monthly | Subsidiary Offtake Disclosures | Exact reported figure in MT. If unreported: `NULL` |
| **Captive / Commercial Allocation** | Nominated Authority Disclosures | Gazette of India Allocation Orders | Standardized: `Auctioned`, `Allotted`, `Nominated` |
| **End Use** | Nominated Authority Disclosures | Ministry of Coal Allocation Matrix | Standardized: `Power`, `Steel`, `Cement`, `Commercial Sale` |

---

## 3. Coverage Summary by Official Source

- **Coal Mines (PSU & Joint)**: Covered by CCO Chapters 2 & 11, CIL Annual Report, SCCL Annual Report (SECL, MCL, NCL, CCL, WCL, BCCL, ECL, SCCL).
- **Lignite Mines**: Covered by CCO Chapter 9, NLCIL Annual Report, GMDC Annual Report (Neyveli Mine-I, Mine-IA, Mine-II, Barsingsar, Panandhro, Rajpardi, Tadkeshwar, Bhavnagar, Surat, Valia).
- **Captive & Commercial Coal Blocks**: Covered by Nominated Authority Master Registers & PIB Captive releases (Allocations to NTPC, RRVUNL, DVC, TSGENCO, Vedanta, Jindal, Adani, UltraTech, JSW).
- **Star Ratings**: Covered by CMPDI & MoC Star Rating portal disclosures.
- **Cross-Document Reconciliation**: Covered by CCO Provisional vs CCO Final Directory vs MoC Monthly Summaries.
