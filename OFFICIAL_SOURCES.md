# COALINTEL Authoritative Government Sources Catalog

This document establishes the official primary Government of India data sources catalog integrated into **COALINTEL**. All mine-level and macro coal statistics in this platform adhere strictly to the **Authoritative Source Policy**:

> **Integrity Rule**: No numbers are fabricated, synthetically generated, or algorithmically interpolated. Where official mine-level information is unavailable from primary disclosures, the value is preserved as `NULL` / Not Available (`availability_status: "not_available"`).

---

## 1. Source Hierarchy & Priority Tiers

| Tier | Issuing Authority / Body | Official Domain | Verification Authority | Primary Focus |
|---|---|---|---|---|
| **Tier 1** | **Ministry of Coal (MoC)**, Government of India | [coal.gov.in](https://coal.gov.in) | Primary Central Government Authority | Monthly Provisional Coal Statistics, Annual Reports, National Benchmarks |
| **Tier 2** | **Coal Controller's Organisation (CCO)** | [coalcontroller.gov.in](https://coalcontroller.gov.in) | Statutory Statistical Authority | Provisional Coal Statistics, Coal Directory of India |
| **Tier 3** | **Nominated Authority**, Ministry of Coal | [nomination.coal.gov.in](https://nomination.coal.gov.in) | Statutory Allocation Authority | Captive & Commercial Coal Block Allocations, PRC, Operational Tracking |
| **Tier 4** | **Coal India Limited (CIL)** & Subsidiaries | [coalindia.in](https://coalindia.in) | Operating Central Public Sector Enterprise | Subsidiary Annual Reports, Production Reviews, Mine-Level Disclosures (SECL, MCL, NCL, CCL, WCL, BCCL, ECL) |
| **Tier 5** | **Press Information Bureau (PIB)** | [pib.gov.in](https://pib.gov.in) | Official Government Press Agency | Fast-breaking provisional announcements, milestones, Minister briefings |
| **Tier 6** | **Star Rating Portal**, Ministry of Coal | [starrating.coal.gov.in](https://starrating.coal.gov.in) | Environmental & Safety Compliance | Official 1 to 5 Star ratings for sustainability, safety, and compliance |

---

## 2. Ingested Primary Publications Catalog

### Source 1: Monthly Provisional Statistics (April 2025 – March 2026)
- **Source ID**: `SRC-GOV-MOC-2025`
- **Authority**: Ministry of Coal, Government of India
- **Tier**: Tier 1
- **Document Title**: *Provisional Monthly Statistics of Coal & Lignite Production (FY 2025-26)*
- **Publication Date**: April 2026
- **Financial Year**: FY 2025-26 (Full Year Final Provisional)
- **URL**: [https://coal.gov.in/en/major-statistics/monthly-provisional-statistics](https://coal.gov.in/en/major-statistics/monthly-provisional-statistics)
- **Key Tables**: Table 1 (All-India Production), Table 2 (Subsidiary-wise breakdown), Table 3 (Top Producing Opencast Mines).

### Source 2: Monthly Provisional Statistics Q1 YTD (April – June 2026)
- **Source ID**: `SRC-GOV-MOC-2026-YTD`
- **Authority**: Ministry of Coal, Government of India
- **Tier**: Tier 1
- **Document Title**: *Monthly Coal Production Statistics for June 2026 & Q1 Cumulative Performance*
- **Publication Date**: July 2026
- **Financial Year**: FY 2026-27 (Q1 YTD Provisional)
- **As of Date**: 2026-06-30
- **URL**: [https://coal.gov.in/en/major-statistics/monthly-provisional-statistics-2026](https://coal.gov.in/en/major-statistics/monthly-provisional-statistics-2026)
- **Data Status**: `provisional`, `period_type = 'YTD'`. Not annualized.

### Source 3: Provisional Coal Statistics 2024-25
- **Source ID**: `SRC-GOV-CCO-2024`
- **Authority**: Coal Controller's Organisation (CCO), Ministry of Coal
- **Tier**: Tier 2
- **Document Title**: *Provisional Coal Statistics 2024-25*
- **Publication Date**: September 2025
- **Financial Year**: FY 2024-25
- **URL**: [https://coalcontroller.gov.in/pages/provisional-coal-statistics-2024-25](https://coalcontroller.gov.in/pages/provisional-coal-statistics-2024-25)
- **Key Tables**: Section 2 (Mine-wise Production & OBR), Section 4 (Captive Coal Mining).

### Source 4: Nominated Authority Captive & Commercial Block Disclosures
- **Source ID**: `SRC-GOV-NA-2025`
- **Authority**: Nominated Authority, Ministry of Coal
- **Tier**: Tier 3
- **Document Title**: *Status of Allocated Captive and Commercial Coal Blocks as of March 2026*
- **Publication Date**: March 2026
- **Financial Year**: FY 2024-25 & FY 2025-26
- **URL**: [https://coal.gov.in/en/nominated-authority/allocated-coal-blocks](https://coal.gov.in/en/nominated-authority/allocated-coal-blocks)
- **Key Fields**: Coal Block ID, Allottee Company, Peak Rated Capacity (PRC MTPA), Production Status, End-Use.

### Source 5: Coal India Limited 51st Annual Report & Accounts
- **Source ID**: `SRC-GOV-CIL-AR-2025`
- **Authority**: Coal India Limited (Maharatna PSU)
- **Tier**: Tier 4
- **Document Title**: *Coal India Limited 51st Annual Report & Accounts (FY 2024-25)*
- **Publication Date**: August 2025
- **Financial Year**: FY 2024-25
- **URL**: [https://www.coalindia.in/investors/annual-reports/](https://www.coalindia.in/investors/annual-reports/)
- **Key Sections**: Management Discussion & Analysis, Subsidiary Operational Reviews (SECL, MCL, NCL, CCL, WCL, BCCL, ECL).

### Source 6: Coal Directory of India 2023-24 & 2024-25
- **Source ID**: `SRC-GOV-CCO-DIR-2024`
- **Authority**: Coal Controller's Organisation
- **Tier**: Tier 2
- **Document Title**: *Coal Directory of India 2024-25*
- **Publication Date**: November 2025
- **Financial Year**: FY 2024-25
- **URL**: [https://coalcontroller.gov.in/pages/coal-directory-2024-25](https://coalcontroller.gov.in/pages/coal-directory-2024-25)
- **Key Sections**: Canonical Mine Names, Geographical Coordinates, Seam Characteristics, Geological Reserves.

### Source 7: Ministry of Coal National Production Milestone PIB Release
- **Source ID**: `SRC-GOV-PIB-1047MT`
- **Authority**: Press Information Bureau, Government of India
- **Tier**: Tier 5
- **Document Title**: *India Achieves Historic Milestone: Coal Production Crosses 1 Billion Tonnes in FY 2024-25 at 1,047.52 MT*
- **Publication Date**: 2025-04-01
- **Financial Year**: FY 2024-25
- **URL**: [https://pib.gov.in/PressReleasePage.aspx?PRID=2016842](https://pib.gov.in/PressReleasePage.aspx?PRID=2016842)
- **Key Metrics**: All-India Production: 1,047.523 MT; CIL Share: 773.6 MT; Captive/Commercial: 190.95 MT.

### Source 8: Star Rating Portal for Coal Mines
- **Source ID**: `SRC-GOV-STAR-2025`
- **Authority**: Ministry of Coal Star Rating Evaluation Committee
- **Tier**: Tier 6
- **Document Title**: *Star Rating of Coal and Lignite Mines for FY 2024-25*
- **Publication Date**: December 2025
- **Financial Year**: FY 2024-25
- **URL**: [https://starrating.coal.gov.in/results/2024-25](https://starrating.coal.gov.in/results/2024-25)
- **Key Ratings**: 5-Star (Gevra, Kusmunda, Dipka, Bhubaneswari, Jayant), 4-Star (Nigahi, Dudhichua, Amrapali, Pakri Barwadih).

---

## 3. Discrepancy Resolution Protocol

When two official publications report differing figures for the same mine and financial year:
1. **Never Silently Overwrite**: Both figures are preserved in `data_conflict_records`.
2. **Deterministic Priority**: Higher tier overrides lower tier (Tier 1 MoC > Tier 2 CCO > Tier 4 CIL > Tier 5 PIB).
3. **Audit Explanation**: The reason (e.g. provisional vs audited final, or inclusion of washery rejects) is recorded alongside the resolution note.
4. **Judge & Analyst Visibility**: All discrepancies are highlighted in the UI via the **Reconciliation & Discrepancy Register**.
