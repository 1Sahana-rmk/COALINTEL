# Pull Request: Implement COALINTEL — Professional Industrial UI Palette

**Source Branch:** `the-color-pallet`  
**Target Branch:** `main`  
**PR Creation URL:** `https://github.com/HenilLol/coalintel/compare/main...the-color-pallet?expand=1`

---

## 1. Executive Summary

This pull request implements the new **COALINTEL — Professional Industrial UI Palette** across the entire Next.js frontend application. The visual redesign elevates CoalIntel from generic dark mode / glowing teal cyber aesthetics into a mission-critical, control-room industrial workspace specifically tailored for Coal India Limited (CIL), its operational subsidiaries (ECL, BCCL, CCL, WCL, SECL, NCL, MCL), CMPDI, and the Ministry of Coal.

All neon glows, cyan/purple gradients, excessive glassmorphic blurs, and oversized circular elements have been stripped away and replaced with crisp, flat, dark-charcoal slate surfaces, thin 1px borders (`#30383D`), tight 8–10px radii (`rounded-lg`), and high-contrast amber (`#C58B3A`) reserved exclusively for primary actions, active navigation, and key callouts.

---

## 2. Industrial Palette Mapping

| Semantic Token | Hex Code | UI Role & Usage |
| :--- | :--- | :--- |
| **PRIMARY BACKGROUND** | `#0E1113` | Deep mine charcoal canvas (`app/globals.css`, root shell, reader workspace) |
| **SIDEBAR / NAVIGATION** | `#151A1D` | Navigation sidebar background, modal backgrounds, input surface background |
| **CARDS** | `#1C2226` | Primary dashboard metric cards, data tables, modular analytics cards |
| **CARD HOVER** | `#242C30` | Hover states, elevated sub-elements, table header rows, icon containers |
| **BORDERS** | `#30383D` | Crisp 1px borders on cards, inputs, tables, dividers, and drawer containers |
| **PRIMARY TEXT** | `#E8ECEB` | High-contrast industrial bone white for primary headings, values, and titles |
| **SECONDARY TEXT** | `#9BA5A8` | Muted cool-grey for metadata, timestamps, units, labels, and table subtext |
| **PRIMARY BRAND / ACCENT** | `#C58B3A` | Coal amber for primary action buttons, active navigation indicator, brand logo |
| **ACCENT HOVER** | `#D6A052` | Warm amber hover state for interactive buttons and links |
| **SUCCESS** | `#4F8A62` | Positive production variances, verified validations, official provenance tags |
| **INFO** | `#54788A` | Target production benchmark lines, informational badges, secondary metrics |
| **WARNING** | `#D6A23A` | Moderate discrepancies, pending validations, seeded test anomaly indicators |
| **ERROR / CRITICAL** | `#C94B45` | Critical discrepancies (> 5%), arithmetic anomalies, failed ingestions |

---

## 3. Design System Directives Applied

- **Border Radius Clamped to 8–10px**: Replaced all `rounded-xl`, `rounded-2xl`, and `rounded-3xl` across cards, modals, and tables with `rounded-lg` (8px). Icon badges now use crisp `rounded-lg` containers instead of generic `rounded-full`.
- **Flat Industrial Surfaces**: Removed all `backdrop-blur-xl`, semi-transparent gradients, and floating decorative shapes.
- **Thin 1px Borders**: Consistent `#30383D` 1px borders applied systematically across cards, data tables, header dividers, and modals.
- **Subtle Industrial Shadows**: Removed all neon glow shadows (`shadow-glow-teal`, `shadow-glow-red`, `shadow-glow-emerald`, `shadow-glow-amber`) in favor of minimal, flat industrial elevation (`shadow-sm` / `shadow-md`).
- **Restricted Amber Accent**: `#C58B3A` is used deliberately for primary CTAs, active route indicators, active document tabs, and key operational totals rather than splashed generically across elements.
- **Dense, High-Readability Data Tables**: Refreshed all monospace numeric tables (Production, Comparison Matrix, Conflicts, Validation, Audit) with alternating hover states (`#242C30/50`) and legible secondary text (`#9BA5A8`).

---

## 4. Modified Files & Component Manifest

### Core Design System & Configuration
- `frontend/tailwind.config.ts`: Added semantic industrial palette (`mine.*`, `industrial.*`, `amber`, `success`, `info`, `warning`, `danger`), mapped legacy aliases to avoid breakages, clamped border radii to 8–10px, and cleaned shadows.
- `frontend/app/globals.css`: Updated CSS custom properties, scrollbars, and selection colors to the industrial palette.
- `frontend/app/layout.tsx`: Updated root layout background and text selection styling.
- `frontend/app/page.tsx`: Updated loading splash screen.

### Layout & Navigation Primitives
- `frontend/components/layout/AppShell.tsx`: Background `#0E1113`, clean layout shell.
- `frontend/components/layout/Sidebar.tsx`: Sidebar background `#151A1D`, active nav item highlighted with amber `#C58B3A` and 8px radius.
- `frontend/components/layout/Header.tsx`: Background `#151A1D`, thin border `#30383D`, subsidiary scope selector, search trigger.

### UI Primitives (`components/ui/`)
- `Card.tsx`: Background `#1C2226`, border `#30383D`, radius `rounded-lg`.
- `Button.tsx`: Primary amber (`#C58B3A` -> `#D6A052`), secondary, outline, ghost, and danger variants.
- `Badge.tsx`: Exact semantic badge colors for `success` (`#4F8A62`), `warning` (`#D6A23A`), `danger` (`#C94B45`), `info` (`#54788A`), and `amber` (`#C58B3A`).
- `Input.tsx` & `Select.tsx`: Surface `#151A1D`, border `#30383D`, focus `#C58B3A`, text `#E8ECEB`.
- `StatCard.tsx`: Card surface `#1C2226`, amber / success / warning / danger indicator styling.
- `Logo.tsx`: Industrial vector coal insignia with amber badge `#C58B3A`.
- `PageHeader.tsx`, `Breadcrumbs.tsx`, `EmptyState.tsx`, `LoadingState.tsx`, `ErrorState.tsx`.

### Operational Dashboard & Domain Modules
- `frontend/components/dashboard/FilterBar.tsx`
- `frontend/components/dashboard/KpiGrid.tsx`
- `frontend/components/dashboard/ProductionChart.tsx`: Actual production bars `#C58B3A`, Target production line `#54788A`, custom industrial tooltip.
- `frontend/components/dashboard/ValidationFeedWidget.tsx`
- `frontend/components/documents/DocumentHeaderCard.tsx`
- `frontend/components/documents/DocumentPageReader.tsx`
- `frontend/components/documents/DocumentTable.tsx`
- `frontend/components/documents/ExtractedMetricsTable.tsx`
- `frontend/components/documents/MetricLineageDrawer.tsx`
- `frontend/components/documents/UploadModal.tsx`
- `frontend/components/query/QueryInput.tsx`
- `frontend/components/query/CitedAnswerCard.tsx`
- `frontend/components/query/CitationDrawer.tsx`
- `frontend/components/validation/ConflictResolveModal.tsx`
- `frontend/components/validation/ValidationFeedTable.tsx`
- `frontend/components/reports/ReportWizardForm.tsx`
- `frontend/components/reports/ReportPreviewCard.tsx`
- `frontend/components/reports/ReportHistoryTable.tsx`
- `frontend/components/analytics/WordCloudTagCloud.tsx`
- `frontend/components/analytics/TfidfMatrixTable.tsx`
- `frontend/components/audit/AuditLogsTable.tsx`

### Application Routes (`app/(dashboard)/` & `app/(auth)/`)
- `frontend/app/(auth)/login/page.tsx`
- `frontend/app/(dashboard)/layout.tsx`
- `frontend/app/(dashboard)/dashboard/page.tsx`
- `frontend/app/(dashboard)/comparison/page.tsx`
- `frontend/app/(dashboard)/conflicts/page.tsx`
- `frontend/app/(dashboard)/parliamentary/page.tsx`
- `frontend/app/(dashboard)/audit/page.tsx`
- `frontend/app/(dashboard)/analytics/page.tsx`
- `frontend/app/(dashboard)/documents/page.tsx`
- `frontend/app/(dashboard)/documents/[id]/page.tsx`
- `frontend/app/(dashboard)/query/page.tsx`
- `frontend/app/(dashboard)/reports/page.tsx`
- `frontend/app/(dashboard)/validation/page.tsx`

---

## 5. Verification & Testing

- **Static Analysis & Type Checking**: Passed cleanly with TypeScript 5 (`tsc --noEmit`).
- **Next.js Production Build**: `npm run build` completed with status `0` across all 15 static/dynamic routes:
  ```
  Route (app)                              Size     First Load JS
  ┌ ○ /                                    562 B          88.1 kB
  ├ ○ /_not-found                          876 B          88.4 kB
  ├ ○ /analytics                           5.22 kB         137 kB
  ├ ○ /audit                               4.19 kB         136 kB
  ├ ○ /comparison                          4.28 kB         131 kB
  ├ ○ /conflicts                           3.8 kB          140 kB
  ├ ○ /dashboard                           106 kB          229 kB
  ├ ○ /documents                           9.47 kB         141 kB
  ├ ƒ /documents/[id]                      9.69 kB         141 kB
  ├ ○ /login                               5.18 kB         119 kB
  ├ ○ /parliamentary                       5.84 kB         133 kB
  ├ ○ /query                               5.19 kB         132 kB
  ├ ○ /reports                             4.9 kB          142 kB
  └ ○ /validation                          5.03 kB         137 kB
  ```
- **Constraint Compliance**:
  - Committed strictly locally to `frontend` branch.
  - **No `git push` executed** to remote repository.
