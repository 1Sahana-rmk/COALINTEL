# COALINTEL UI/UX DOCUMENTATION & FRONTEND DESIGN SPECIFICATION

---

## SECTION 1 — DOCUMENT CONTROL

### 1.1 Document Overview
* **Document Title:** COALINTEL UI/UX Documentation & Frontend Design Specification
* **Project Name:** COALINTEL (AI-Powered Evidence-Driven Mining Intelligence & Reporting Platform)
* **Problem Statement ID:** SIH26023
* **Problem Statement Title:** AI-Powered Geological, Mining and other Reporting Solution for CMPDI/CIL subsidiaries
* **Sponsoring Organization:** Ministry of Coal
* **Department:** Coal India Limited (CIL) / Central Mine Planning & Design Institute (CMPDI)
* **Category:** Software | Theme: Smart Automation
* **Version:** 1.0.0 (Baseline Release)
* **Status:** Approved / Development Ready for Day 2 Sprint
* **Date:** August 27, 2026
* **Author / Ownership:** Senior Product Architect & UI/UX Strategy Lead
* **Primary Target Lead:** Day 2 Frontend Engineering Lead (1st-Year Computer Engineering Student Team)

### 1.2 Governance & Baseline Alignment
This specification defines the complete user interface, interaction model, visual layout system, and component contracts for COALINTEL. It strictly adheres to:
1. **`COALINTEL_MASTER_SPECIFICATION.md`** (Single Source of Truth - SSOT)
2. **`PRD.md`** (Product Requirements Document v1.1)
3. **`TRD.md`** (Technical Requirements Document v1.0)

---

## SECTION 2 — UI/UX OBJECTIVES

1. **Evidence-First Visual Hierarchy:** Position source document citations, page badges, and raw snippet evidence at the core of every query answer and report view.
2. **4-Level Dashboard Command Center:** Render a clean, non-cluttered operational dashboard providing high-level KPIs, analytical charts, topic intelligence, and data validation feeds.
3. **Deterministic Data Trust:** Surface validation warning badges (`VALIDATED`, `WARNING_ARITHMETIC`, `CONFLICT_DETECTED`) prominently so human reviewers instantly identify discrepancies.
4. **Desktop-First Institutional Aesthetics:** Implement a dark-mode government intelligence design theme using slate, emerald, amber, and cyan accents.
5. **Day 2 Development Velocity:** Use standard React 18 + Vite + Tailwind CSS + Lucide Icons + Recharts primitives to ensure single-developer execution within an 8-day sprint.

---

## SECTION 3 — UX PRINCIPLES & PRODUCT PHILOSOPHY

### 3.1 What COALINTEL UI IS NOT
* **NOT** a generic ChatGPT box with a small PDF upload icon.
* **NOT** a basic document viewer with raw text dumps.
* **NOT** an unvalidated BI tool displaying arbitrary frontend numbers.

### 3.2 Core UI Philosophy
$$\text{EVIDENCE} \longrightarrow \text{VALIDATION} \longrightarrow \text{INTELLIGENCE} \longrightarrow \text{REPORT}$$

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        COALINTEL CORE UX LAYOUT                           │
├───────────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────┐  ┌─────────────────────────────────────────────┐ │
│ │                      │  │ 4-LEVEL MINING INTELLIGENCE DASHBOARD       │ │
│ │  APP NAVIGATION      │  │ • Executive KPI Cards                       │ │
│ │  (Sidebar Router)    │  │ • Production vs Target Visualizers (Recharts)│ │
│ │                      │  │ • Topic Cloud & Validation Feed             │ │
│ └──────────────────────┘  └─────────────────────────────────────────────┘ │
│ ┌───────────────────────────────────────────────────────────────────────┐ │
│ │ EVIDENCE SIDE-DRAWER: Page Canvas | Source Text Chunk | Cell Bounding │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## SECTION 4 — TARGET USERS & PERMISSION PROFILES

```
┌───────────────────────────────────────────────────────────────────────────┐
│                      TARGET USER PERMISSION PROFILES                      │
├─────────────────┬───────────────────────────────┬─────────────────────────┤
│ ROLE            │ PRIMARY INTERACTION           │ ACCESSIBLE SCREENS      │
├─────────────────┼───────────────────────────────┼─────────────────────────┤
│ Admin           │ User management & system audit│ All 23 Screens          │
│ Analyst         │ Upload docs, query, draft reps│ Dashboard, Upload, Q&A  │
│ Reviewer        │ Resolve conflicts, approve    │ Review Queue, Conflicts │
│ Viewer          │ Executive read-only analytics │ Dashboard, Analytics    │
└─────────────────┴───────────────────────────────┴─────────────────────────┘
```

---

## SECTION 5 — DETAILED USER PERSONAS (ROLE-BASED)

### Persona 1: Nodal / Reporting Officer (Analyst)
* **Primary Task:** Draft official Parliamentary Inquiry (PQ) responses under tight 2-hour deadlines.
* **Key UI Needs:** Rapid document query tool ("Ask COALINTEL"), instant page citation drawer, template-driven report assembly wizard.

### Persona 2: Mining / Performance Analyst (Analyst)
* **Primary Task:** Evaluate Target vs. Actual production trends across opencast mines over multi-year periods.
* **Key UI Needs:** 4-Level Dashboard KPI cards, Recharts trend visualizers, unit-standardized metric data tables, CSV exports.

### Persona 3: Executive / Decision Maker (Viewer)
* **Primary Task:** Macro operational oversight across CIL subsidiaries.
* **Key UI Needs:** Clean high-level KPI overview, subsidiary production distribution donut chart, TF-IDF Word Cloud.

### Persona 4: Reviewer / Domain Expert (Reviewer)
* **Primary Task:** Verification of draft reports and resolution of cross-document numerical conflicts.
* **Key UI Needs:** Side-by-side conflict resolution drawer, inline markdown report editor, "Approve & Seal Report" action button.

### Persona 5: System Administrator (Admin)
* **Primary Task:** User management and system health monitoring.
* **Key UI Needs:** User role assignment table, real-time background ingestion queue status, immutable audit log view.

---

## SECTION 6 — INFORMATION ARCHITECTURE (IA)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    COALINTEL INFORMATION ARCHITECTURE                     │
├───────────────────────────────────────────────────────────────────────────┤
│ MAIN NAVIGATION                                                           │
│ ├── Dashboard (Overview / 4-Level IA)                                     │
│ ├── Document Management                                                   │
│ │   ├── Library (Grid/List View)                                          │
│ │   ├── Ingestion Hub (Dropzone)                                          │
│ │   ├── Processing Status (Queue Tracker)                                 │
│ │   └── Document Detail View (Page Canvas & Extracted Metrics)            │
│ ├── Mining Intelligence                                                   │
│ │   ├── Ask COALINTEL (Cited Natural Language Q&A)                        │
│ │   ├── Evidence Panel (Lineage Side-Drawer)                              │
│ │   ├── Historical Comparison (Multi-Year Matrix)                         │
│ │   └── Topic Intelligence (TF-IDF & Interactive Word Cloud)              │
│ ├── Data Quality & Validation                                             │
│ │   ├── Validation Feed (Arithmetic Warnings)                             │
│ │   └── Conflict Resolver (Side-by-Side Discrepancy View)                 │
│ ├── Reporting Hub                                                         │
│ │   ├── Report Assembly Wizard (Step-by-step Generator)                   │
│ │   ├── Draft Review Queue (Inline Editor)                                │
│ │   └── Approved Reports Library (PDF/DOCX Export)                        │
│ └── Administration                                                        │
│     ├── User Management                                                   │
│     ├── Audit Trail                                                       │
│     └── System Settings                                                   │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## SECTION 7 — NAVIGATION ARCHITECTURE & APPSHELL

The application utilizes an **AppShell Layout** featuring a fixed left sidebar navigation (`256px` width), a top fixed navbar (`64px` height), a dynamic breadcrumb bar, and a main fluid content viewport.

```
┌───────────────────────────────────────────────────────────────────────────┐
│                             APPSHELL LAYOUT                               │
├──────────────────┬────────────────────────────────────────────────────────┤
│ BRAND HEADER     │ NAVBAR: Global Search | Active Role Badge | User Menu  │
├──────────────────┼────────────────────────────────────────────────────────┤
│ SIDEBAR ROUTER   │ BREADCRUMBS: Home / Documents / Details                │
│ • Dashboard      ├────────────────────────────────────────────────────────┤
│ • Documents      │                                                        │
│ • Intelligence   │ MAIN CONTENT VIEWPORT (Scrollable)                     │
│ • Validation     │                                                        │
│ • Reports        │                                                        │
│ • Administration │                                                        │
├──────────────────┼────────────────────────────────────────────────────────┤
│ SYSTEM STATUS    │ FOOTER: API Status: Connected | Version 1.0.0          │
└──────────────────┴────────────────────────────────────────────────────────┘
```

---

## SECTION 8 — APPLICATION SHELL SPECIFICATION

* **Sidebar Behavior:** Collapsible to icon-only mode (`64px`) on laptop screens; auto-hidden on mobile screens with hamburger menu toggle.
* **Top Navbar Elements:**
  * **Brand Title:** `COALINTEL` (with emerald intelligence badge).
  * **Global Search Input:** Quick filtering across documents and extracted metrics (`Ctrl + K`).
  * **User Profile Pill:** Displays username, active role badge (`ANALYST`, `REVIEWER`), and dropdown menu (Settings, Logout).

---

## SECTION 9 — DESIGN SYSTEM SPECIFICATION

```
┌───────────────────────────────────────────────────────────────────────────┐
│                      DESIGN SYSTEM TOKEN GUIDELINES                       │
├───────────────────┬───────────────────────────────────────────────────────┤
│ DESIGN TOKEN      │ TECHNICAL SPECIFICATION                               │
├───────────────────┼───────────────────────────────────────────────────────┤
│ Primary Background│ Dark Slate (`#0F172A` / Tailwind `bg-slate-900`)     │
│ Surface Cards     │ Deep Slate (`#1E293B` / Tailwind `bg-slate-800`)     │
│ Border Dividers   │ Slate Border (`#334155` / Tailwind `border-slate-700`)│
│ Text Primary      │ High-Contrast White (`#F8FAFC` / `text-slate-50`)     │
│ Text Muted        │ Slate Muted (`#94A3B8` / `text-slate-400`)            │
│ Primary Brand     │ Coal Emerald (`#10B981` / `emerald-500`)              │
│ Primary Hover     │ Emerald Dark (`#059669` / `emerald-600`)              │
│ Status Success    │ Validated Green (`#22C55E` / `green-500`)             │
│ Status Warning    │ Warning Amber (`#F59E0B` / `amber-500`)               │
│ Status Danger     │ Conflict Red (`#EF4444` / `red-500`)                  │
│ Status Info       │ Cyan Info (`#06B6D4` / `cyan-500`)                    │
└───────────────────┴───────────────────────────────────────────────────────┘
```

---

## SECTION 10 — TYPOGRAPHY SYSTEM

* **Primary Font Family:** Inter, system-ui, -apple-system, sans-serif.
* **Monospace Font Family:** JetBrains Mono, Fira Code, monospace (used for source code snippets, hash values, and table coordinates).
* **Font Scale:**
  * `H1` (Page Title): `24px` (`1.5rem`), SemiBold (`font-semibold`).
  * `H2` (Section Title): `20px` (`1.25rem`), Medium (`font-medium`).
  * `H3` (Card Header): `16px` (`1.0rem`), Medium (`font-medium`).
  * `Body Regular`: `14px` (`0.875rem`), Regular (`font-normal`).
  * `Caption / Badge`: `12px` (`0.75rem`), Medium (`font-medium`).

---

## SECTION 11 — COLOR SYSTEM & SEMANTIC INTENT

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       SEMANTIC COLOR INTENT MAP                           │
├───────────────┬──────────────┬────────────────────────────────────────────┤
│ COLOR         │ HEX CODE     │ SEMANTIC APPLICATION                       │
├───────────────┼──────────────┼────────────────────────────────────────────┤
│ Emerald Green │ `#10B981`    │ Primary buttons, active states, verified   │
│ Amber Yellow  │ `#F59E0B`    │ Arithmetic warnings, unverified metrics    │
│ Crimson Red   │ `#EF4444`    │ Cross-document conflict badges, error alerts│
│ Cyan Blue     │ `#06B6D4`    │ Information links, page citation badges    │
│ Slate Gray    │ `#64748B`    │ Neutral borders, secondary text, metadata  │
└───────────────┴──────────────┴────────────────────────────────────────────┘
```

---

## SECTION 12 — SPACING, ELEVATION & SHADOWS

* **Spacing Grid:** 4px base multiplier (`p-2` = 8px, `p-4` = 16px, `p-6` = 24px, `gap-4` = 16px).
* **Card Elevation:** Flat surface with 1px border (`border border-slate-700/60 bg-slate-800/80 rounded-lg shadow-sm`).
* **Modal Overlay:** Semi-transparent slate backdrop (`bg-slate-950/70 backdrop-blur-sm`).

---

## SECTION 13 — ICONOGRAPHY SYSTEM (LUCIDE ICONS)

* **Document Management:** `FileText`, `UploadCloud`, `CheckCircle2`, `AlertTriangle`, `FileSpreadsheet`.
* **Mining & Analytics:** `BarChart3`, `PieChart`, `TrendingUp`, `Layers`, `Layers2`.
* **Intelligence & Evidence:** `Search`, `MessageSquare`, `Bookmark`, `ExternalLink`, `ShieldCheck`.
* **System & Users:** `Users`, `Settings`, `Lock`, `ShieldAlert`, `LogOut`, `Clock`.

---

## SECTION 14 — CORE REUSABLE COMPONENTS

### 1. KPICard Component
Renders top-level summary metrics with label, numeric value, unit, percentage change badge, and visual icon.

### 2. StatusBadge Component
Displays validation and processing states with standardized colors (`VALIDATED` $\rightarrow$ Green, `WARNING` $\rightarrow$ Amber, `CONFLICT` $\rightarrow$ Red, `PENDING` $\rightarrow$ Slate).

### 3. FileDropzone Component
Interactive drag-and-drop file upload target supporting single and batch uploads with real-time format validation.

### 4. CitationBadge Component
Clickable inline tag `[Doc_Name.pdf, Page X]` that triggers the Evidence Side-Drawer.

### 5. EvidenceDrawer Component
Slide-over side drawer displaying page canvas rendering, highlighted bounding boxes, and raw extracted text.

---

## SECTION 15 — SCREEN SPECIFICATION: LOGIN PAGE

* **Route:** `/login`
* **Purpose:** User authentication and role assignment.
* **Layout:** Centered dark-slate card featuring COALINTEL branding header.
* **Components:** Username input, Password input, Role Selector dropdown (`Analyst`, `Reviewer`, `Admin`, `Viewer`), Submit Button.
* **States:**
  * **Default:** Clean input fields with role preset to `Analyst`.
  * **Loading:** Submit button displays spinner and text `"Authenticating..."`.
  * **Error:** Red alert banner `"Invalid credentials or role selection"`.

---

## SECTION 16 — SCREEN SPECIFICATION: MAIN DASHBOARD (4-LEVEL IA)

* **Route:** `/dashboard`
* **Purpose:** Central operational command center providing consolidated CIL/CMPDI intelligence.

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     4-LEVEL DASHBOARD SCREEN LAYOUT                       │
├───────────────────────────────────────────────────────────────────────────┤
│ LEVEL 1: EXECUTIVE KPI CARDS                                              │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│ │ TOTAL DOCS   │ │ TARGET MT    │ │ ACTUAL MT    │ │ CONFLICTS    │       │
│ │ 124 Files    │ │ 650.0 MT     │ │ 642.8 MT     │ │ 3 Flagged    │       │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
├───────────────────────────────────────────────────────────────────────────┤
│ LEVEL 2: ANALYTICS VISUALIZERS (RECHARTS)                                 │
│ ┌──────────────────────────────────┐ ┌──────────────────────────────────┐ │
│ │ Target vs Actual Production Bar  │ │ Subsidiary Production Share      │ │
│ │ (Recharts BarChart Component)    │ │ (Recharts PieChart Component)    │ │
│ └──────────────────────────────────┘ └──────────────────────────────────┘ │
├───────────────────────────────────────────────────────────────────────────┤
│ LEVEL 3: INTELLIGENCE & TOPIC CLOUD                                       │
│ ┌───────────────────────────────────────────────────────────────────────┐ │
│ │ Interactive TF-IDF Word Cloud (Topic Terms: Overburden, Capex, etc.)  │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
├───────────────────────────────────────────────────────────────────────────┤
│ LEVEL 4: TRUST & EVIDENCE FEED                                            │
│ ┌───────────────────────────────────────────────────────────────────────┐ │
│ │ Active Validation Warnings & Cross-Document Conflict Alerts           │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## SECTION 17 — SCREEN SPECIFICATION: DOCUMENT LIBRARY

* **Route:** `/documents`
* **Purpose:** View, search, filter, and manage all ingested organizational files.
* **Layout:** Top filter bar (Search input, Subsidiary filter dropdown, Fiscal Year filter dropdown), followed by a data table.
* **Table Columns:** File Name, Subsidiary, Fiscal Year, Pages, Upload Date, Processing Status, Actions (View Details, Re-parse, Delete).

---

## SECTION 18 — SCREEN SPECIFICATION: DOCUMENT UPLOAD DROPZONE

* **Route:** `/documents/upload`
* **Purpose:** Drag-and-drop batch ingestion hub.
* **Interactions:** User drops files into dashed container; system computes SHA-256 hash client-side preview; displays upload queue list with progress bars.

---

## SECTION 19 — SCREEN SPECIFICATION: PROCESSING STATUS QUEUE

* **Route:** `/documents/processing`
* **Purpose:** Real-time visual tracking of asynchronous document parsing, OCR, and vector indexing.
* **Queue Item Fields:** Filename, File Size, Parsing Step (`PARSING` $\rightarrow$ `OCR` $\rightarrow$ `STRUCTURING` $\rightarrow$ `INDEXED`), Progress Bar %, Status Badge.

---

## SECTION 20 — SCREEN SPECIFICATION: DOCUMENT DETAILS PAGE

* **Route:** `/documents/:id`
* **Purpose:** Inspect page-by-page text, table extraction grids, and metadata for a specific file.
* **Layout:** Split-screen layout. Left side: PDF page canvas viewer with zoom controls. Right side: Tabbed panel (Extracted Text, Extracted Tables, Metric Tuples, Metadata).

---

## SECTION 21 — SCREEN SPECIFICATION: EXTRACTED DATA VIEW

* **Route:** `/data/extracted`
* **Purpose:** Complete tabular view of all isolated domain metric tuples stored in PostgreSQL.
* **Table Columns:** Mine Name, Subsidiary, Metric Name, Raw Value & Unit, Standardized MT Value, Fiscal Year, Source Doc Badge, Validation Status.

---

## SECTION 22 — SCREEN SPECIFICATION: VALIDATION & DATA QUALITY VIEW

* **Route:** `/validation`
* **Purpose:** Quality control hub displaying arithmetic warnings and unverified metric records.
* **UI Features:** Summary counter cards (Valid Metrics vs. Flagged Metrics), filterable warning table, manual edit modal trigger.

---

## SECTION 23 — SCREEN SPECIFICATION: CONFLICT RESOLUTION VIEW

* **Route:** `/validation/conflicts`
* **Purpose:** Side-by-side discrepancy resolver for conflicting cross-document values.

```
┌───────────────────────────────────────────────────────────────────────────┐
│                   SIDE-BY-SIDE CONFLICT RESOLVER VIEW                     │
├───────────────────────────────────────────────────────────────────────────┤
│ DISCREPANCY DETECTED: Kusunda OCP - FY2023-24 Production                  │
├─────────────────────────────────────┬─────────────────────────────────────┤
│ DOCUMENT A: Annual_Report_2024.pdf  │ DOCUMENT B: Mining_Log_FY24.xlsx    │
│ • Page: 14                          │ • Sheet: Production_Summary         │
│ • Value: 14.20 MT                   │ • Value: 14.80 MT                   │
│ • Snippet: "...actual 14.20 MT..."  │ • Snippet: "...total 14.80 MT..."   │
│ [ View Source Page Canvas ]         │ [ View Source Spreadsheet ]         │
├─────────────────────────────────────┴─────────────────────────────────────┤
│ RESOLUTION ACTION:                                                        │
│ (o) Accept Document A (14.20 MT)   ( ) Accept Document B (14.80 MT)      │
│ [ RESOLVE & SAVE OFFICIAL METRIC ]                                        │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## SECTION 24 — SCREEN SPECIFICATION: "ASK COALINTEL" AI QUERY INTERFACE

* **Route:** `/query`
* **Purpose:** Natural language evidence-backed Q&A assistant.
* **UI Layout:** Top query search bar with sample prompt suggestions (*"What was Kusunda production in FY24?"*). Below: Answer container featuring direct numeric answer, narrative paragraph, hyperlinked citation badges `[Doc_Name, Page X]`, and source evidence summary cards.

---

## SECTION 25 — SCREEN SPECIFICATION: EVIDENCE SIDE-DRAWER PANEL

* **Trigger:** Click any citation badge `[Doc_Name.pdf, Page X]`.
* **Drawer Panel (`450px` width):** Slides in from right screen border. Displays document title, page number, confidence score, raw extracted text chunk, bounding box coordinate tag, and a button `"Open Full Document Page"`.

---

## SECTION 26 — SCREEN SPECIFICATION: ANALYTICS DASHBOARD

* **Route:** `/analytics`
* **Purpose:** Deep-dive operational trend visualizations.
* **Visualizers:** Recharts Target vs Actual Bar Chart, Multi-Year Subsidiary Line Charts, Overburden Removal Area Charts. Includes export options (Download Chart PNG / Export Data CSV).

---

## SECTION 27 — SCREEN SPECIFICATION: TOPIC INTELLIGENCE

* **Route:** `/analytics/topics`
* **Purpose:** Frequency analysis of recurring geological and administrative terms across the document corpus.
* **Layout:** Ranked topic table showing term name, document frequency, category tag (`Operations`, `Environment`, `Exploration`), and clickable filter link.

---

## SECTION 28 — SCREEN SPECIFICATION: INTERACTIVE WORD CLOUD

* **Route:** `/analytics/wordcloud`
* **Purpose:** Visual 2D cloud rendering top TF-IDF extracted operational terms.
* **Interaction:** Term font size scaled by term frequency. Hovering displays occurrence count; clicking a word filters the Document Library to display related files.

---

## SECTION 29 — SCREEN SPECIFICATION: HISTORICAL COMPARISON INTERFACE

* **Route:** `/analytics/compare`
* **Purpose:** Multi-year side-by-side metric comparison matrix.
* **Layout:** Parameter selector (Mine Name, Years: FY22 vs FY23 vs FY24). Renders comparison matrix with color-coded variance indicators ($\uparrow +12.4\%$ Green, $\downarrow -3.2\%$ Amber).

---

## SECTION 30 — SCREEN SPECIFICATION: STEP-BY-STEP REPORT WIZARD

* **Route:** `/reports/new`
* **Purpose:** 4-Step wizard for assembling official reports.

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    REPORT ASSEMBLY STEP-BY-STEP WIZARD                    │
├───────────────────────────────────────────────────────────────────────────┤
│ STEP 1: Template     │ STEP 2: Parameters   │ STEP 3: Evidence │ STEP 4: Draft│
│ [x] Parliamentary PQ │ Mine: Kusunda OCP    │ Retrieve 5 Docs  │ Assemble    │
│ [ ] Annual Review    │ Fiscal Year: FY24    │ Validated        │ Draft       │
├──────────────────────┴──────────────────────┴──────────────────┴─────────────┤
│ PROGRESS: [=============================================>        ] 75%      │
│ [ BACK ]                                                     [ NEXT STEP ]│
└───────────────────────────────────────────────────────────────────────────┘
```

---

## SECTION 31 — SCREEN SPECIFICATION: REPORT PREVIEW PAGE

* **Route:** `/reports/:id`
* **Purpose:** Formatted view of generated draft report displaying executive header, narrative sections, metric tables, and citation appendices. Includes banner: `DRAFT - PENDING DOMAIN REVIEW`.

---

## SECTION 32 — SCREEN SPECIFICATION: REPORT REVIEW & INLINE EDITOR

* **Route:** `/reports/:id/review`
* **Purpose:** Reviewer workspace for editing text inline and signing off on official reports.
* **UI Features:** Rich text markdown editor, side-by-side evidence checker, action buttons (`Approve & Seal Report`, `Reject Draft`).

---

## SECTION 33 — SCREEN SPECIFICATION: SYSTEM AUDIT TRAIL

* **Route:** `/admin/audit`
* **Purpose:** Security compliance log displaying immutable system activity records.
* **Table Columns:** Timestamp, Username, User Role, Action Executed (`LOGIN`, `UPLOAD`, `REPORT_APPROVED`), Resource ID, IP Address.

---

## SECTION 34 — SCREEN SPECIFICATION: USER MANAGEMENT (ADMIN ONLY)

* **Route:** `/admin/users`
* **Purpose:** User account management and role assignment UI.
* **Features:** User list table, "Add New User" modal, role toggle dropdown (`Analyst`, `Reviewer`, `Viewer`).

---

## SECTION 35 — SCREEN SPECIFICATION: SETTINGS & SYSTEM CONFIG

* **Route:** `/admin/settings`
* **Purpose:** Platform configuration panel.
* **Fields:** Storage path display, Vector DB index stats, API connection status toggle, OCR confidence threshold slider.

---

## SECTION 36 — SCREEN SPECIFICATION: NOTIFICATIONS & TOAST FEED

* **UI Component:** Floating toast notification feed (bottom-right screen anchor).
* **Toast Types:**
  * **Success:** Green toast `"Document parsed & indexed successfully."`
  * **Warning:** Amber toast `"1 Data conflict flagged during ingestion."`
  * **Error:** Red toast `"Upload failed: File size exceeds 100MB."`

---

## SECTION 37 — ROLE-BASED ACCESS CONTROL (RBAC VISIBILITY MATRIX)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        RBAC UI VISIBILITY MATRIX                          │
├─────────────────────────┬───────────┬──────────────┬───────────┬──────────┤
│ UI ELEMENT / ROUTE      │ ADMIN     │ ANALYST      │ REVIEWER  │ VIEWER   │
├─────────────────────────┼───────────┼──────────────┼───────────┼──────────┤
│ Dashboard Page          │ Visible   │ Visible      │ Visible   │ Visible  │
│ Upload Button & Page    │ Visible   │ Visible      │ Hidden    │ Hidden   │
│ Conflict Resolver Page  │ Visible   │ Read-Only    │ Actionable│ Read-Only│
│ Generate Report Button  │ Visible   │ Actionable   │ Actionable│ Hidden   │
│ Approve Report Button   │ Visible   │ Hidden       │ Actionable│ Hidden   │
│ User Management Route   │ Visible   │ Hidden       │ Hidden    │ Hidden   │
│ Audit Trail Route       │ Visible   │ Hidden       │ Hidden    │ Hidden   │
└─────────────────────────┴───────────┴──────────────┴───────────┴──────────┘
```

---

## SECTION 38 — RESPONSIVE DESIGN & DESKTOP BREAKPOINTS

* **Target Primary Breakpoint:** Desktop 1920x1080 & 1440x900 (`lg:` / `xl:` Tailwind classes).
* **Laptop Breakpoint (1280px):** Sidebar collapses to 64px icon bar; tables enable horizontal scroll (`overflow-x-auto`).
* **Tablet Breakpoint (768px):** Main KPI cards stack into 2-column grid; evidence side-drawer takes full screen width.

---

## SECTION 39 — ACCESSIBILITY SPECIFICATION (A11Y)

* **Keyboard Navigation:** Full tab order navigation across form inputs, dropdowns, and pagination controls.
* **Focus Indicator:** Visible 2px emerald focus ring (`focus:outline-none focus:ring-2 focus:ring-emerald-500`).
* **Color Contrast:** Text contrast ratios exceed WCAG AA standards ($\ge 4.5:1$ for body text on dark slate surfaces).

---

## SECTION 40 — SYSTEM STATES: LOADING & SKELETON SCREENS

* **Data Fetching State:** Render pulse animation skeletons (`animate-pulse bg-slate-700/50 rounded`) matching exact card and table dimensions. Never display blank white screens or layout jumps.

---

## SECTION 41 — SYSTEM STATES: EMPTY STATES & PLACEHOLDERS

* **Empty Library:** Render muted file icon + text *"No documents uploaded yet. Click 'Upload Files' to ingest mining records."*
* **Empty Search Results:** Render search icon + text *"No evidence matching your query was found."*

---

## SECTION 42 — SYSTEM STATES: ERROR HANDLING & TOASTS

* **API Network Failure:** Render top amber alert bar *"Server connection lost. Retrying in 5 seconds..."*
* **Validation Error:** Render inline red helper text below specific form fields.

---

## SECTION 43 — UX FOR AI FAILURE & DEGRADED MODE

If the LLM API fails or times out:
1. Do **NOT** render fake or ungrounded text.
2. Display warning card: *"AI narrative synthesis is temporarily unavailable."*
3. Render raw retrieved evidence text chunks, source document citations, and validated metric tables directly.

---

## SECTION 44 — SECURITY UX & SESSION EXPIRY

* **Session Timeout Warning:** Display modal 5 minutes prior to JWT expiration: *"Your session will expire soon. Click 'Extend Session' to stay logged in."*
* **Unauthorized Access:** Redirect to `/login` with toast error `"Insufficient permissions for target route."`

---

## SECTION 45 — FRONTEND DATA CONTRACTS (API MATCHING)

```typescript
// TypeScript Contract Interfaces matching TRD APIs
interface KPICardData {
  total_documents: number;
  target_production_mt: number;
  actual_production_mt: number;
  active_conflicts: number;
}

interface CitationItem {
  document_id: number;
  filename: string;
  page_number: number;
  snippet_text: string;
  confidence_score: number;
}
```

---

## SECTION 46 — REACT COMPONENT ARCHITECTURE TREE

```
src/
├── App.jsx
├── layouts/
│   └── AppShell.jsx (Navbar, Sidebar, Footer)
├── components/
│   ├── common/
│   │   ├── Button.jsx, Badge.jsx, Modal.jsx, Toast.jsx
│   ├── dashboard/
│   │   ├── KPICard.jsx, ProductionChart.jsx, TopicCloud.jsx
│   ├── document/
│   │   ├── Dropzone.jsx, DocumentTable.jsx, PageCanvas.jsx
│   ├── query/
│   │   ├── ChatWindow.jsx, CitationBadge.jsx, EvidenceDrawer.jsx
│   └── report/
│       ├── WizardStep.jsx, MarkdownEditor.jsx, ExportBar.jsx
└── pages/
    ├── DashboardPage.jsx, DocumentsPage.jsx, QueryPage.jsx, ReportsPage.jsx
```

---

## SECTION 47 — USER FLOW DIAGRAMS

```
[ LOGIN ] ──► [ DASHBOARD ] ──► [ UPLOAD PDF ] ──► [ PROCESSING QUEUE ]
                                                         │
[ EXPORT PDF ] ◄── [ APPROVE ] ◄── [ DRAFT REPORT ] ◄── [ ASK QUERY & CITE ]
```

---

## SECTION 48 — SIH DEMONSTRATION FLOW (10-STEP PITCH)

1. **Step 1:** Open Dashboard showing live CIL production KPIs and Recharts visualizers.
2. **Step 2:** Drag and drop a scanned annual report into the Upload Dropzone.
3. **Step 3:** Show Processing Status transition to `INDEXED`.
4. **Step 4:** Highlight Conflict Alert badge flagging a target discrepancy.
5. **Step 5:** Open Conflict Resolver side-by-side view.
6. **Step 6:** Navigate to "Ask COALINTEL" and submit query: *"What was Kusunda production in FY24?"*
7. **Step 7:** Click inline citation badge to open Evidence Side-Drawer with page preview.
8. **Step 8:** Open Report Wizard, select Parliamentary Inquiry template, click "Generate Draft".
9. **Step 9:** Open Reviewer Queue, edit report text inline, click "Approve & Seal".
10. **Step 10:** Export approved report to formatted PDF artifact.

---

## SECTION 49 — MVP CLASSIFICATION MATRIX

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       MVP CLASSIFICATION MATRIX                           │
├───────────────────────────────────┬───────────────────────────────────────┤
│ CORE DEMO MVP (DAY 2-7 MUST HAVE) │ SECONDARY MVP & FUTURE ROADMAP        │
├───────────────────────────────────┼───────────────────────────────────────┤
│ • Login Page & Auth State         │ • Interactive 2D Word Cloud Widget    │
│ • 4-Level Mining Dashboard        │ • DOCX / XLSX Spreadsheet Upload      │
│ • Drag-and-Drop PDF Upload        │ • Multi-Year Comparison Matrix        │
│ • Processing Queue Status Tracker │ • Reviewer Approval Queue Interface   │
│ • Document Details & Page Canvas  │ • DOCX Export Formatting              │
│ • "Ask COALINTEL" Q&A View        │ • Multilingual UI Translations        │
│ • Evidence Side-Drawer            │ • Voice Query Input Interface         │
│ • Conflict Resolver Interface     │ • GraphRAG Visual Graph Inspector     │
│ • Report Generation Wizard        │ • Mobile Tablet App Adaptation        │
│ • PDF Formatted Export            │ • Enterprise NIC SSO Integration      │
└───────────────────────────────────┴───────────────────────────────────────┘
```

---

## SECTION 50 — FRONTEND DEVELOPER IMPLEMENTATION GUIDANCE

### Day 2 Sprint Checklist for Frontend Lead
* [ ] Initialize React 18 + Vite project structure with Tailwind CSS.
* [ ] Implement `AppShell.jsx` layout with fixed sidebar and dark slate theme (`#0F172A`).
* [ ] Create reusable `KPICard.jsx`, `Badge.jsx`, and `Button.jsx` components.
* [ ] Build `DashboardPage.jsx` with static mock data matching 4-level IA.
* [ ] Connect Recharts `<BarChart />` and `<PieChart />` components.
* [ ] Implement `Dropzone.jsx` file upload dropzone interface.
* [ ] Build `QueryPage.jsx` chat view with clickable `CitationBadge.jsx`.
* [ ] Implement `EvidenceDrawer.jsx` slide-over side panel.

---

## SECTION 51 — UX TESTING & USABILITY CRITERIA

* **Target SLA:** User can locate specific mine production evidence in $< 3$ clicks.
* **Usability Verification:** 100% of generated report claims carry clickable page citation badges. Zero blank white loading screens permitted.

---

## SECTION 52 — USABILITY SUCCESS METRICS

* **Task Completion Rate ($TCR$):** $> 95\%$ across test users completing report generation.
* **System Usability Scale ($SUS$):** Target score $> 85/100$ evaluated on visual clarity, readability, and speed.

---

## SECTION 53 — FUTURE UX ROADMAP

* **Phase 2:** GraphRAG visual node graph inspector; Hindi regional UI translation mode.
* **Phase 3:** Mobile tablet supervisor view; voice-activated query microphone input.

---

## SECTION 54 — FINAL UI/UX READINESS CHECKLIST

* [x] Design system tokens (colors, typography, spacing) defined for Tailwind CSS.
* [x] 23 major screens fully specified with layout diagrams and component trees.
* [x] 4-Level Dashboard Information Architecture fully detailed.
* [x] Evidence-First side drawer component specified with citation linkages.
* [x] Given-When-Then UI state transitions defined for loading, error, empty, and conflict states.
* [x] RBAC visibility matrix aligned with TRD security permissions.
* [x] 16 End-to-end user flows and 10-step SIH demo narrative mapped.

**UI/UX Strategy Sign-off:** *Approved for Day 2 Frontend Engineering Implementation.*
