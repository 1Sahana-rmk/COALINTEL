# COALINTEL PRODUCT REQUIREMENTS DOCUMENT (PRD)

---

## SECTION 1 — DOCUMENT CONTROL

### 1.1 Document Overview
* **Document Title:** COALINTEL Product Requirements Document (PRD)
* **Project Name:** COALINTEL (AI-Powered Evidence-Driven Mining Intelligence & Reporting Platform)
* **Problem Statement ID:** SIH26023
* **Problem Statement Title:** AI-Powered Geological, Mining and other Reporting Solution for CMPDI/CIL subsidiaries
* **Sponsoring Organization:** Ministry of Coal
* **Department:** Coal India Limited (CIL) / Central Mine Planning & Design Institute (CMPDI)
* **Category:** Software
* **Theme:** Smart Automation
* **Version:** 1.1.0 (Targeted Quality Revision)
* **Status:** Approved / Development Ready
* **Date:** August 27, 2026
* **Author / Ownership:** Senior Product Architect & Technical Documentation Lead
* **Primary Target Engineering Lead:** 1st-Year, 1st-Semester Computer Engineering Student Development Team
* **Development Sprint Window:** 8 Calendar Days (SIH Hackathon Sprint)

### 1.2 Relationship to Master Specification (SSOT)
This document is derived directly from the **COALINTEL Master Project Specification (`COALINTEL_MASTER_SPECIFICATION.md`)**, which serves as the preeminent Single Source of Truth (SSOT). All functional, user-facing, and operational requirements specified herein adhere strictly to the boundaries, architecture, and technology direction established in the Master Specification.

### 1.3 Document Revision History

| Version | Date | Description of Changes | Author | Status |
| :--- | :--- | :--- | :--- | :--- |
| **1.0.0** | Aug 27, 2026 | Initial Complete PRD Baseline for SIH 2026 Sprint | Senior Product Architect | Approved |
| **1.1.0** | Aug 27, 2026 | Targeted Revision: Removed unsupported claims, strengthened Given-When-Then ACs, role-based personas, 4-level Dashboard IA, measurement-based metrics, MVP priorities. | Senior Product Architect | Approved |

---

## SECTION 2 — EXECUTIVE SUMMARY

### 2.1 Product Brief
**COALINTEL** is an enterprise-grade, AI-powered evidence-driven mining intelligence and reporting platform designed specifically for Coal India Limited (CIL) and the Central Mine Planning & Design Institute (CMPDI). The platform ingests heterogeneous organizational records—including scanned PDFs, digital PDFs, Word documents, Excel spreadsheets, CSVs, and map images—and converts them into structured, validated, and searchable organizational knowledge.

### 2.2 Core Product Innovation
Unlike generic document assistants or basic "Chat-with-PDF" UIs, COALINTEL is built around a central **Mining Intelligence Dashboard** backed by an **Evidence-First Architecture**. The system combines hybrid search, deterministic numeric validation, cross-document conflict detection, topic intelligence, and template-based report assembly. Every extracted metric and AI-generated narrative maintains an unbroken lineage trail back to its original document, page, table, and cell coordinates.

### 2.3 Key Value Objectives
* **Inquiry Latency Reduction Objective:** Significantly accelerates response preparation for Ministry and Parliamentary Questions (PQs) compared to manual paper/PDF search baselines.
* **Validation-Gated Accuracy:** Utilizes deterministic unit standardization and arithmetic verification to prevent numeric hallucinations.
* **Source Attribution Objective:** Provides automated source citations for generated report claims, linking directly to source document pages and tables.

---

## SECTION 3 — PRODUCT OVERVIEW

### 3.1 Product Identity & Vision
* **Product Name:** COALINTEL
* **Tagline:** "Transforming Unstructured Mining Records into Auditable, Decision-Ready Intelligence."
* **Core Value Proposition:** COALINTEL unifies fragmented geological, mining, operational, and administrative documents into a single operational command dashboard, empowering CIL/CMPDI officers to query historical archives, track production KPIs, detect data discrepancies, and generate review-ready official reports with high confidence.

### 3.2 Product Positioning Statement
For CIL and CMPDI reporting officers, analysts, and executive decision-makers who currently spend days manually compiling, verifying, and drafting reports from heterogeneous paper and digital records, **COALINTEL** is an evidence-driven intelligence platform that automatically extracts structured metrics, validates numerical consistency, flags cross-document discrepancies, and drafts institutional reports. Unlike unvalidated AI chatbots or basic OCR tools, COALINTEL prioritizes data accuracy, mathematical integrity, page-level traceability, and human-in-the-loop governance.

---

## SECTION 4 — SIH PROBLEM STATEMENT ALIGNMENT (SIH26023)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    SIH26023 PROBLEM STATEMENT ALIGNMENT                   │
├───────────────────────────────────┬───────────────────────────────────────┤
│ OFFICIAL SIH REQUIREMENT          │ COALINTEL PRODUCT CAPABILITY          │
├───────────────────────────────────┼───────────────────────────────────────┤
│ 1. Automated Report Generation    │ Template-Based Report Assembly Engine │
│ 2. Word Cloud & Topic ID          │ Interactive 2D Word Cloud & TF-IDF    │
│ 3. AI Query and Response          │ Evidence-Grounded Cited Query Assist. │
│ 4. Structured Document Processing │ OCR + PyMuPDF Layout & Table Parser   │
│ 5. Data Validation & Consistency  │ Deterministic Validation Engine       │
│ 6. Historical Information Retrieval│ Hybrid Vector-BM25 Knowledge Search  │
│ 7. Traceability & Lineage         │ Clickable Page & Table Evidence Cards │
│ 8. Rapid Inquiry Response         │ Parliamentary Question Draft Template │
└───────────────────────────────────┴───────────────────────────────────────┘
```

---

## SECTION 5 — PROBLEM ANALYSIS & OPERATIONAL CONTEXT

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ FRAGMENTED DOCS │ ───>  │ MANUAL SEARCH & │ ───>  │ HIGH ERROR RATE │
│ • Scanned PDFs  │       │ COPY-PASTE      │       │ & 48-HR LATENCY │
│ • Excel Sheets  │       │ • Sifting PDFs  │       │ • Unit Mismatch │
│ • Word Archives │       │ • Manual Math   │       │ • Lost History  │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

### 5.1 Legacy Operational Friction Points
1. **Institutional Memory Loss:** Critical geological and mine planning context resides in static physical or PDF archives. When experienced officers transfer, historical knowledge becomes inaccessible.
2. **High Copy-Paste Latency:** Preparing answers for Ministry/Parliamentary Inquiries requires manually opening 20–50 large PDFs, searching for mine names, and copy-pasting numbers into working drafts.
3. **Transcription & Unit Errors:** Human errors frequently occur when transcribing figures between documents using different units (e.g., mixing Tonnes, Lakh Tonnes, and Million Tonnes).
4. **Silent Data Discrepancies:** Different departments or annual reports often report slightly different figures for the same mine in the same fiscal year, leading to discrepancies during official audits.
5. **Zero Evidence Traceability:** Final executive briefings rarely indicate the exact page or table cell from which a specific figure was sourced, making audit verification extremely difficult.

---

## SECTION 6 — PRODUCT VISION

To establish **COALINTEL** as a reliable intelligence operating platform across Coal India Limited and its subsidiaries, seamlessly converting legacy document fragmentation into continuous, structured, and auditable organizational knowledge.

---

## SECTION 7 — PRODUCT MISSION

To provide CIL and CMPDI personnel with an intelligent, reliable, and evidence-grounded reporting copilot that automates document parsing, structured metric extraction, numerical reconciliation, and draft report assembly—ensuring that decisions, answers, and reports are backed by verifiable source evidence.

---

## SECTION 8 — PRODUCT POSITIONING & PHILOSOPHY

### 8.1 What COALINTEL IS NOT
* **NOT** a generic chatbot or conversational wrapper around an unvalidated LLM.
* **NOT** a simple "Chat-with-PDF" web page.
* **NOT** standard standalone OCR software.
* **NOT** an ungrounded narrative text generator.

### 8.2 What COALINTEL IS
An **enterprise-grade, evidence-driven mining intelligence platform** centered around an interactive **Mining Intelligence Dashboard**, backed by hybrid search, deterministic numeric validation, topic intelligence, and auditable report generation.

### 8.3 Core Operational Philosophy
$$\text{EVIDENCE} \longrightarrow \text{VALIDATION} \longrightarrow \text{INTELLIGENCE} \longrightarrow \text{REPORT}$$

```
   ┌───────────┐      ┌────────────┐      ┌──────────────┐      ┌──────────┐
   │ DOCUMENTS │ ───> │ EXTRACTION │ ───> │  STRUCTURING │ ───> │ VALIDATE │
   └───────────┘      └────────────┘      └──────────────┘      └──────────┘
                                                                     │
   ┌───────────┐      ┌────────────┐      ┌──────────────┐           ▼
   │  REPORTS  │ <─── │   QUERY    │ <─── │  DASHBOARD   │ <─── ┌──────────┐
   └───────────┘      └────────────┘      └──────────────┘      │ KNOWLEDGE│
                                                                └──────────┘
```

---

## SECTION 9 — PRODUCT PRINCIPLES

1. **Evidence First:** No answer or report claim is presented without a direct link to source document, page, and table coordinates.
2. **Validation-Gated Numbers:** Extracted numeric figures must pass unit standardization and arithmetic verification before appearing on executive dashboards.
3. **Human-in-the-Loop Governance:** AI drafts narrative reports and flags discrepancies; human domain experts review, edit, approve, and seal official outputs.
4. **Dashboard-Centric Experience:** Operational metrics, KPI cards, target trends, and validation warnings take visual priority over free-form chat.
5. **Practical Developer Feasibility:** Designed specifically for rapid execution within an 8-day hackathon window by a first-year engineering team.

---

## SECTION 10 — TARGET USERS & PERSONA MATRIX

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          TARGET USER PERSONAS                             │
├─────────────────┬───────────────────────────────┬─────────────────────────┤
│ PERSONA         │ PRIMARY ROLE                  │ SYSTEM USER LEVEL       │
├─────────────────┼───────────────────────────────┼─────────────────────────┤
│ Nodal Officer   │ HQ Administrative Inquiries   │ Analyst User            │
│ Mining Analyst  │ Mine Planning & Performance   │ Analyst User            │
│ Executive Dir.  │ Strategic Operations Oversight│ Executive Viewer        │
│ Domain Reviewer │ Quality Assurance & Approval  │ Reviewer / Approver     │
│ System Admin    │ System Management & Audit     │ System Administrator    │
└─────────────────┴───────────────────────────────┴─────────────────────────┘
```

---

## SECTION 11 — DETAILED USER PERSONAS (ROLE-BASED)

### Persona 1: Nodal / Reporting Officer
* **Role Overview:** Responsible for HQ Administrative & Ministry Inquiries.
* **Core Responsibilities:** Responds to urgent Parliamentary Questions (PQs) and Ministry of Coal audit queries within tight 2-to-4 hour deadlines.
* **Pain Points:** Sifting through 50+ scanned PDFs to find specific mine production or environmental figures under extreme time pressure.
* **Goals:** Rapidly retrieve exact, evidence-backed figures with clear page citations to draft official response briefings.
* **Required Capabilities:** Document search, evidence query assistant, template report generator.
* **Permissions:** `Analyst` (Upload documents, run queries, generate draft reports).

### Persona 2: Mining / Reporting Analyst
* **Role Overview:** Responsible for Mine Planning & Operational Performance Analysis.
* **Core Responsibilities:** Compares target vs. actual production, overburden removal, and capex across opencast mines and subsidiaries over multi-year periods.
* **Pain Points:** Manually copying data from scanned tables into Excel spreadsheets; dealing with unit inconsistencies (Lakh Tonnes vs. MT).
* **Goals:** View visual target vs. actual trends on an interactive dashboard; detect cross-document data conflicts automatically.
* **Required Capabilities:** Metric visualization, unit converter, conflict detector, CSV data export.
* **Permissions:** `Analyst` (Upload documents, view metrics, export data).

### Persona 3: Executive / Decision Maker
* **Role Overview:** Responsible for Strategic Operations & Subsidiary Oversight.
* **Core Responsibilities:** Oversees strategic coalfield operations, reviews macro trends, and monitors key operational issues across active mines.
* **Pain Points:** Lack of consolidated high-level visual dashboards summarizing document corpora; difficulty spotting emerging operational themes.
* **Goals:** Inspect executive KPI cards, subsidiary production share charts, and topic word clouds at a glance.
* **Required Capabilities:** Executive Dashboard, KPI cards, Word Cloud analytics, executive report viewing.
* **Permissions:** `Viewer` / `Analyst` (Read-only dashboard, executive view, high-level reports).

### Persona 4: Reviewer / Domain Expert
* **Role Overview:** Responsible for Quality Assurance & Institutional Sign-off.
* **Core Responsibilities:** Reviews and validates draft reports generated by junior staff or automated systems before formal submission to Ministry authorities.
* **Pain Points:** Risk of unverified numbers or incorrect figures slipping into official government documents.
* **Goals:** Review flagged data conflicts side-by-side; inline-edit draft reports; click "Approve & Seal Report" to generate final PDF/DOCX.
* **Required Capabilities:** Reviewer queue, side-by-side conflict resolver, inline document editor, approval action.
* **Permissions:** `Reviewer` (Approve/edit draft reports, resolve conflicts).

### Persona 5: System Administrator
* **Role Overview:** Responsible for Platform Health, Security & Compliance.
* **Core Responsibilities:** Manages user accounts, monitors document batch ingestion queues, and reviews system audit logs for security compliance.
* **Pain Points:** Tracking user activities and ensuring sensitive document access is audited.
* **Goals:** Manage user roles, monitor system processing health, inspect immutable audit logs.
* **Required Capabilities:** User management UI, ingestion status monitor, audit log viewer.
* **Permissions:** `Admin` (User management, system health, audit logs).

---

## SECTION 12 — USER PAIN POINTS & PRODUCT RESOLUTION MATRIX

| User Pain Point | Existing Workaround | COALINTEL Resolution | Targeted Impact |
| :--- | :--- | :--- | :--- |
| **Manual PDF Sifting** | Opening 30 PDFs and pressing Ctrl+F | **Hybrid Vector + BM25 Search** | Significant reduction in search effort |
| **Unit Confusion** | Manual conversion on calculator | **Deterministic Unit Converter** | Standardized unit normalization |
| **Silent Discrepancies**| Discovered during Ministry audits | **Cross-Document Conflict Detector** | Automated conflict detection |
| **Unbacked Statements**| Double-checking every AI line | **Citation Gate + Evidence Cards** | Evidence-grounded response generation |
| **Manual Report Assembly**| Copy-pasting text into MS Word | **Template-Based Report Engine** | Rapid automated report drafting |

---

## SECTION 13 — CURRENT VS. PROPOSED WORKFLOW

### Current Manual Workflow
```
[ PDF Archive ] ──> [ Manual Ctrl+F Search ] ──> [ Calculator Math ] ──> [ MS Word Copy-Paste ] ──> [ Manual Verification ]
```

### Proposed COALINTEL Workflow
```
[ Ingest Files ] ──> [ Auto Parse & Validate ] ──> [ Dashboard & Query ] ──> [ Auto Draft Report ] ──> [ Review & Approve ]
```

---

## SECTION 14 — PRODUCT SCOPE BOUNDARIES

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       COALINTEL SCOPE BOUNDARIES                          │
├───────────────────────────────────┬───────────────────────────────────────┤
│ MVP SCOPE (MUST HAVE - DAYS 1-8)  │ POST-MVP SCOPE (FUTURE ROADMAP)       │
├───────────────────────────────────┼───────────────────────────────────────┤
│ • Heterogeneous Upload (PDF/XLSX) │ • GraphRAG Knowledge Graphs           │
│ • OCR & Layout Table Parser       │ • Multilingual Voice Query Interface  │
│ • Metric Structuring & Storage    │ • Fine-Tuned Custom Mining Model      │
│ • Deterministic Unit Validator    │ • Enterprise NIC SSO Integration      │
│ • Cross-Document Conflict Engine  │ • Direct SAP / ERP Database Sync      │
│ • Interactive Mining Dashboard    │ • Geospatial GIS Mining Overlays      │
│ • Evidence-Backed Cited Query     │ • Mobile iOS/Android Applications     │
│ • Template-Based Report Generator │ • Fully Autonomous Submission Workflows│
│ • Human-in-the-Loop Review Queue  │ • Multi-Tenant Cloud Architecture     │
│ • PDF / DOCX Formatted Export     │ • Autonomous Multi-Agent Systems      │
└───────────────────────────────────┴───────────────────────────────────────┘
```

---

## SECTION 15 — MVP PRIORITIZATION & SCOPE DEFINITION

To protect the 1st-year student development team from scope creep during the 8-day sprint while ensuring a complete SIH demonstration, product capabilities are explicitly structured into three implementation tiers:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                      MVP PRIORITIZATION STRUCTURE                         │
├───────────────────────────────────────────────────────────────────────────┤
│ A. CORE DEMO MVP (MUST WORK RELIABLY END-TO-END)                          │
│ • User Authentication (JWT + Role Security)                               │
│ • PDF File Upload & Processing State Feedback                             │
│ • Digital PDF Text Extraction (PyMuPDF)                                   │
│ • OCR for Scanned PDFs (Tesseract 5.0) where feasible                     │
│ • Basic Structured Metric Extraction (Mine, Year, Production, Target)     │
│ • PostgreSQL Data Persistence                                             │
│ • Deterministic Unit Validation (Lakh Tonnes -> MT)                       │
│ • Cross-Document Conflict Flagging                                        │
│ • 4-Level Mining Intelligence Dashboard                                   │
│ • Evidence-Backed Natural Language Query Assistant                        │
│ • Page-Level Source Citations & Evidence Side-Drawer                      │
│ • Basic Template Report Generation (Parliamentary Inquiry)                │
│ • PDF Report Export                                                       │
│ • Immutable System Audit Trail                                            │
├───────────────────────────────────────────────────────────────────────────┤
│ B. SECONDARY MVP (IMPLEMENT IF TIME & STABILITY PERMIT)                   │
│ • DOCX Ingestion & Deep Table Parsing                                     │
│ • XLSX / CSV Spreadsheet Parsing                                          │
│ • TF-IDF Word Cloud & Topic Identification Widget                         │
│ • Multi-Year Historical Comparison Views                                  │
│ • Reviewer Approval Queue Interface                                       │
│ • DOCX Formatted Report Export                                            │
├───────────────────────────────────────────────────────────────────────────┤
│ C. FUTURE / OUT OF SCOPE (POST-HACKATHON RELEASE)                         │
│ • Microsoft GraphRAG Knowledge Graphs                                     │
│ • Custom Foundation Model Training / Fine-tuning                          │
│ • Multilingual Voice Query Recognition                                    │
│ • Enterprise NIC Single Sign-On (SSO) Integration                         │
│ • Direct SAP / ERP Database Connectors                                    │
└───────────────────────────────────────────────────────────────────────────┘
```

* **Core Scope Policy:** The development team MUST complete and polish Tier A (Core Demo MVP) into a single, rock-solid vertical slice before attempting Tier B features.

---

## SECTION 16 — FUTURE SCOPE (POST-HACKATHON ROADMAP)

* **Phase 2 (Months 1–3):** Microsoft GraphRAG integration for cross-document entity graph traversal; Hindi/regional language query translation; direct SAP ERP database connectors.
* **Phase 3 (Months 6+):** Enterprise NIC Single Sign-On (SSO) integration; STQC security certification; air-gapped on-premise deployment at CIL HQ Kolkata.

---

## SECTION 17 — PRODUCT MODULE ARCHITECTURE

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       COALINTEL CORE MODULE MAP                           │
├───────────────────┬───────────────────────────────────────────────────────┤
│ MODULE            │ RESPONSIBILITY & PRODUCT CAPABILITIES                 │
├───────────────────┼───────────────────────────────────────────────────────┤
│ MOD-01: Auth      │ User Authentication, JWT Tokens, RBAC Security        │
│ MOD-02: Ingestion │ File Upload, SHA-256 Deduplication, Status Tracking   │
│ MOD-03: Parsing   │ Layout Parser, Tesseract OCR, Table Grid Extractor    │
│ MOD-04: Extractor │ Domain Entity & Operational Metric Extraction Engine  │
│ MOD-05: Validator │ Deterministic Unit Standardization & Conflict Detector│
│ MOD-06: Indexer   │ PostgreSQL Relational Store + ChromaDB Vector Index   │
│ MOD-07: Dashboard │ Executive Command Center, 4-Level Dashboard Visuals   │
│ MOD-08: Query AI  │ Hybrid Retrieval Search & Evidence-Backed Q&A Assistant│
│ MOD-09: WordCloud │ TF-IDF Term Extraction & Interactive Topic Cloud      │
│ MOD-10: Reporting │ Template-Based Draft Assembly & Citation Injection    │
│ MOD-11: Review    │ Human-in-the-Loop Queue, Conflict Resolver, Approver  │
│ MOD-12: Export    │ Formatted PDF/DOCX Document Exporter & Audit Logging  │
└───────────────────┴───────────────────────────────────────────────────────┘
```

---

## SECTION 18 — FEATURE REQUIREMENTS SPECIFICATION

### Module 1: Document Ingestion Hub
* **REQ-ING-001 (Supported Formats):** System shall accept `.pdf` (digital & scanned), `.docx`, `.xlsx`, `.csv`, `.png`, and `.jpg` file uploads up to 100MB per file.
* **REQ-ING-002 (Batch Handling):** System shall support drag-and-drop batch upload of up to 10 files simultaneously.
* **REQ-ING-003 (Deduplication):** System shall compute SHA-256 file hashes upon receipt and prevent duplicate document parsing.
* **REQ-ING-004 (Status Tracking):** System shall display real-time visual progress status badges: `UPLOADED` $\rightarrow$ `PARSING` $\rightarrow$ `INDEXED` $\rightarrow$ `FAILED`.

### Module 2: Document Processing & OCR
* **REQ-OCR-001 (Digital Parsing):** System shall extract clean text, headers, and metadata from digital PDFs using PyMuPDF.
* **REQ-OCR-002 (Scanned Page OCR):** System shall automatically detect image-only pages and trigger Tesseract 5.0 OCR at 300 DPI.
* **REQ-OCR-003 (Table Extraction):** System shall preserve tabular structures, extracting cells, row headers, and column headers into structured JSON representations.

### Module 3: Structured Data Extraction
* **REQ-EXT-001 (Entity Isolation):** System shall extract standard mining entities: Mine Name, Coalfield, Subsidiary (BCCL, ECL, SECL, etc.), Fiscal Year, Month, Project Type.
* **REQ-EXT-002 (Operational Metrics):** System shall extract key numeric metrics: Target Production, Actual Production, Target Dispatch, Actual Dispatch, Overburden Removal, Capex, Safety Accidents.
* **REQ-EXT-003 (Metric Tuples):** System shall store extracted metrics in standard schema: `(mine_name, metric_name, numeric_value, unit, fiscal_year, source_doc, page_number)`.

### Module 4: Deterministic Validation Engine
* **REQ-VAL-001 (Unit Standardization):** System shall automatically convert legacy units ("Lakh Tonnes", "Tons", "Million Tonnes") into standard **Million Tonnes (MT)**.
* **REQ-VAL-002 (Arithmetic Verification):** System shall verify that subsidiary sums equal individual mine totals ($\sum \text{Mines} = \text{Subsidiary Total}$). Trigger flag `WARNING_ARITHMETIC` on mismatch $>5\%$.
* **REQ-VAL-003 (Cross-Document Conflict Detection):** System shall query database for duplicate metric triplets `(Mine, Metric, Year)`. If two documents report values differing by $>1\%$, system shall generate a `CONFLICT_DETECTED` badge.

### Module 5: Evidence & Source Traceability
* **REQ-TRC-001 (Evidence Lineage):** System shall maintain an immutable lineage trail mapping every UI claim $\rightarrow$ metric record $\rightarrow$ text chunk $\rightarrow$ page number $\rightarrow$ original source file.
* **REQ-TRC-002 (Citation Cards):** System shall display hyperlinked source citation badges `[Doc_Name.pdf, Page X]` next to generated answers and report claims.
* **REQ-TRC-003 (Snippet Preview):** Clicking a citation badge shall open a side-drawer displaying the raw source text chunk and page image preview.

### Module 6: Search & Hybrid Retrieval
* **REQ-SRCH-001 (Hybrid Search):** Query engine shall execute parallel vector similarity search (ChromaDB `all-MiniLM-L6-v2`) and keyword search (PostgreSQL full-text BM25).
* **REQ-SRCH-002 (Reranking):** System shall merge search results using Reciprocal Rank Fusion (RRF) to generate a top-5 evidence pack.
* **REQ-SRCH-003 (Metadata Filtering):** Search interface shall support filtering by Subsidiary, Fiscal Year, Document Type, and Mine Name.

### Module 7: AI Query & Answer Assistant
* **REQ-AI-001 (Natural Language Q&A):** Assistant shall accept natural language queries (e.g., *"What was Kusunda mine production in FY24?"*) and return concise evidence-backed answers.
* **REQ-AI-002 (Comparative Queries):** System shall answer cross-year comparison queries (e.g., *"Compare BCCL production between FY23 and FY24"*), rendering structured markdown comparison tables.
* **REQ-AI-003 (Empty Context Fallback):** If retrieved context similarity score is below threshold, assistant shall return standard response: `"Insufficient evidence found in uploaded records."` with zero text hallucination.

### Module 8: Mining Intelligence Dashboard (4-Level Information Architecture)
* **REQ-DASH-LEVEL-1 (Executive KPIs):** Display top overview cards: Total Documents, Documents Processed, Records Extracted, Total Target Production, Total Actual Production, Active Conflicts Flagged.
* **REQ-DASH-LEVEL-2 (Analytics):** Render interactive Recharts visualizations: Target vs Actual Production Bar Chart, Subsidiary Share Donut Chart, Multi-Year Trend Lines (*What is happening?*).
* **REQ-DASH-LEVEL-3 (Intelligence):** Render interactive TF-IDF Word Cloud and Topic Identification widgets highlighting recurring operational themes (*What should I notice?*).
* **REQ-DASH-LEVEL-4 (Trust & Evidence):** Surface active validation warning feed, flagged cross-document conflict badges, and source evidence links (*Can I trust it? / What should I do?*).

### Module 9: Topic Identification & Word Cloud
* **REQ-TOP-001 (Word Cloud Widget):** Dashboard shall feature an interactive 2D Word Cloud rendering top operational keywords derived via TF-IDF analysis.
* **REQ-TOP-002 (Click-to-Filter):** Clicking any word inside the Word Cloud shall filter the document repository and surface related files and metric records.

### Module 10: Automated Report Generation Engine
* **REQ-REP-001 (Template Selection):** System shall provide pre-built institutional templates: Parliamentary Query Response, Annual Mine Performance Review, Executive Briefing.
* **REQ-REP-002 (Draft Assembly):** System shall automatically fetch validated metrics, generate structured narrative sections, inject citation tables, and draft a complete report.
* **REQ-REP-003 (Draft Watermarking):** All newly generated reports shall bear a visual header badge: `DRAFT - PENDING DOMAIN REVIEW`.

### Module 11: Human-in-the-Loop Review Queue
* **REQ-REV-001 (Reviewer Queue):** System shall provide a dedicated Reviewer Dashboard listing unverified metrics, data conflicts, and draft reports pending approval.
* **REQ-REV-002 (Conflict Resolver):** Reviewers shall be able to view conflicting figures side-by-side with original document previews and manually select or edit the official verified value.
* **REQ-REV-003 (Report Sealing):** Reviewers shall be able to edit report text inline and click "Approve & Seal Report", advancing status to `APPROVED`.

### Module 12: Export & Audit Trail Manager
* **REQ-EXP-001 (Export Formats):** System shall support exporting: (a) Dashboard/Analytics $\rightarrow$ PDF snapshot, (b) Extracted Metrics $\rightarrow$ CSV/XLSX, (c) Approved Reports $\rightarrow$ PDF/DOCX with citation appendices retained.
* **REQ-AUD-001 (Immutable Logging):** System shall record all user actions (login, upload, query, report generation, approval) in an immutable `audit_logs` database table.

---

## SECTION 19 — FUNCTIONAL REQUIREMENTS & ACCEPTANCE CRITERIA MATRIX

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     FUNCTIONAL REQUIREMENTS MATRIX                        │
├──────────────┬───────────────────────────────┬──────────┬─────────────────┤
│ REQ ID       │ FEATURE TITLE                 │ PRIORITY │ TARGET MVP      │
├──────────────┼───────────────────────────────┼──────────┼─────────────────┤
│ FR-AUTH-001  │ User Login & JWT Token        │ P1       │ Day 1 (Core)    │
│ FR-AUTH-002  │ Role-Based Access Control     │ P1       │ Day 1 (Core)    │
│ FR-ING-001   │ Heterogeneous File Upload     │ P1       │ Day 3 (Core)    │
│ FR-ING-002   │ SHA-256 Deduplication Check   │ P1       │ Day 3 (Core)    │
│ FR-OCR-001   │ Digital PDF Layout Extractor  │ P1       │ Day 4 (Core)    │
│ FR-OCR-002   │ Tesseract OCR Scanned Parser  │ P1       │ Day 4 (Core)    │
│ FR-OCR-003   │ Structured Table Cell Parser  │ P1       │ Day 4 (Core)    │
│ FR-EXT-001   │ Mining Entity Tuple Extractor │ P1       │ Day 4 (Core)    │
│ FR-VAL-001   │ Unit Standardization Engine   │ P1       │ Day 6 (Core)    │
│ FR-VAL-002   │ Arithmetic Sum Checker        │ P1       │ Day 6 (Core)    │
│ FR-VAL-003   │ Cross-Document Conflict Flag  │ P1       │ Day 6 (Core)    │
│ FR-SRCH-001  │ Hybrid Vector-BM25 Search Engine│ P1     │ Day 5 (Core)    │
│ FR-AI-001    │ Cited Natural Language Q&A    │ P1       │ Day 5 (Core)    │
│ FR-AI-002    │ Empty Context Fallback Guard  │ P1       │ Day 5 (Core)    │
│ FR-DASH-001  │ Executive KPI Cards Render    │ P1       │ Day 2 (Core)    │
│ FR-DASH-002  │ Target vs Actual Charts Render│ P1       │ Day 2 (Core)    │
│ FR-TOP-001   │ TF-IDF Term Word Cloud Widget │ P2       │ Day 6 (Second)  │
│ FR-REP-001   │ Template Report Generator     │ P1       │ Day 6 (Core)    │
│ FR-REV-001   │ Human-in-the-Loop Review Queue│ P2       │ Day 7 (Second)  │
│ FR-EXP-001   │ Formatted PDF / DOCX Exporter │ P1       │ Day 7 (Core)    │
│ FR-AUD-001   │ Immutable Audit Logging       │ P1       │ Day 3 (Core)    │
└──────────────┴───────────────────────────────┴──────────┴─────────────────┘
```

### Detailed Given-When-Then Acceptance Criteria

#### AC-FR-AUTH-001 (User Authentication)
* **Given:** A user navigates to the COALINTEL login screen,
* **When:** The user enters valid credentials and selects an assigned role (`Analyst` or `Reviewer`),
* **Then:** The system issues a signed JWT token, updates user session state, and redirects the user to the Mining Intelligence Dashboard,
* **And:** Access to protected API routes is granted based on the assigned role permissions.

#### AC-FR-ING-001 (Document Upload)
* **Given:** An Analyst user accesses the Document Ingestion Hub,
* **When:** The user drops a valid PDF file (digital or scanned) up to 100MB into the upload area,
* **Then:** The system accepts the file, computes its SHA-256 hash, creates a database record, and displays an active progress bar with status `UPLOADED`,
* **And:** If a file with an identical SHA-256 hash already exists, the system notifies the user `"Duplicate document detected; existing index preserved."`

#### AC-FR-OCR-001 & AC-FR-OCR-002 (Document Parsing & OCR)
* **Given:** An uploaded PDF file is queued for processing,
* **When:** The ingestion pipeline executes,
* **Then:** Digital pages are parsed directly via PyMuPDF, while image-only scanned pages automatically trigger Tesseract 5.0 OCR,
* **And:** Extracted text chunks, table structures, and page bounding boxes are persisted to the database and indexed into ChromaDB.

#### AC-FR-VAL-001 (Unit Standardization)
* **Given:** Extracted numerical metric records contain legacy units such as `"Lakh Tonnes"` or `"Tons"`,
* **When:** The validation engine processes the extracted record,
* **Then:** The numeric value is automatically converted to standard **Million Tonnes (MT)** using standard multiplier rules ($1 \text{ Lakh Tonnes} = 0.1 \text{ MT}$),
* **And:** Both raw unit and standardized MT value are retained for evidence lineage.

#### AC-FR-VAL-003 (Cross-Document Conflict Detection)
* **Given:** Two separate uploaded documents contain production metrics for the same mine, metric name, and fiscal year,
* **When:** The extracted values differ by more than $1\%$,
* **Then:** The system creates a `data_conflicts` record and renders a visual `CONFLICT_DETECTED` warning badge on the Dashboard,
* **And:** The system allows reviewers to inspect both source documents side-by-side without silently overwriting either value.

#### AC-FR-AI-001 (Cited Query Assistant)
* **Given:** An authorized user enters a natural language query in the Query Assistant,
* **When:** The hybrid search engine retrieves relevant context chunks,
* **Then:** The system generates an evidence-backed answer where every numerical or factual statement carries an inline hyperlinked citation badge `[Doc_Name.pdf, Page X]`,
* **And:** Clicking the citation badge opens the evidence side-drawer displaying the raw source text snippet and page image preview.

#### AC-FR-AI-002 (Empty Context Fallback)
* **Given:** A user enters a query regarding an unindexed mine or missing topic,
* **When:** The top retrieved context chunk similarity score falls below the confidence threshold,
* **Then:** The assistant responds `"Insufficient evidence found in uploaded records."`,
* **And:** Zero text or numerical figures are generated by the model.

#### AC-FR-REP-001 (Automated Report Generation)
* **Given:** A user selects the "Parliamentary Query Response" report template and specifies target entity parameters,
* **When:** The user clicks "Generate Report Draft",
* **Then:** The system retrieves validated metrics, populates executive summary sections, injects source citation tables, and displays the draft report with a `DRAFT - PENDING REVIEW` header within seconds.

#### AC-FR-EXP-001 (Formatted Report Export)
* **Given:** An approved report draft is displayed in the Report Viewer,
* **When:** The user selects "Export to PDF",
* **Then:** The system generates a formatted PDF document incorporating cover headers, metric tables, narrative text, and complete source citation appendices.

---

## SECTION 20 — USER STORIES & WORKFLOWS

### US-001: User Login & Role Initialization
* **As a** Nodal / Reporting Officer,  
* **I want to** log into COALINTEL using my official credentials,  
* **So that** I can access my assigned subsidiary workspace and role permissions securely.

### US-002: Heterogeneous Document Ingestion
* **As a** Mining / Reporting Analyst,  
* **I want to** drag and drop a folder containing scanned PDFs, Excel logs, and Word reports,  
* **So that** COALINTEL can automatically extract and index operational figures into unified knowledge.

### US-003: Executive Dashboard Visual Tracking
* **As an** Executive / Decision Maker,  
* **I want to** view overall CIL production KPIs, target achievement charts, and word clouds on a central dashboard,  
* **So that** I can assess coalfield performance without digging through paper files.

### US-004: Evidence-Backed Natural Language Query
* **As a** Nodal / Reporting Officer,  
* **I want to** ask *"What was Mine X production in FY2024?"*,  
* **So that** I receive a direct answer accompanied by clickable page citations linking to original PDF evidence.

### US-005: Cross-Document Conflict Flagging
* **As a** Reviewer / Domain Expert,  
* **I want to** receive an automatic warning badge when two reports list conflicting numbers for the same mine,  
* **So that** I can resolve the discrepancy before drafting official government responses.

### US-006: Automated Report Assembly
* **As a** Mining / Reporting Analyst,  
* **I want to** select a "Parliamentary Query Response" template and specify a target mine and fiscal year,  
* **So that** COALINTEL drafts a complete, cited response briefing rapidly.

### US-007: Human-in-the-Loop Review & Approval
* **As a** Reviewer / Domain Expert,  
* **I want to** review AI-generated report drafts, make inline text edits, and click "Approve & Seal",  
* **So that** official reports remain 100% human-verified and auditable.

### US-008: Polished Document Export
* **As a** Nodal / Reporting Officer,  
* **I want to** export approved reports to formatted PDF and DOCX files,  
* **So that** I can submit them immediately to Ministry authorities.

---

## SECTION 21 — NON-FUNCTIONAL REQUIREMENTS (NFRs)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     NON-FUNCTIONAL REQUIREMENTS (NFRs)                    │
├───────────────────────────┬───────────────────────────────────────────────┤
│ NFR CATEGORY              │ PRODUCT REQUIREMENT SPECIFICATION             │
├───────────────────────────┼───────────────────────────────────────────────┤
│ Performance Latency       │ • Dashboard initial render: < 1.5s target     │
│ Target Objectives         │ • Hybrid search + Q&A response: < 3.0s target │
│                           │ • 20-page document parsing: < 45s target      │
│ System Reliability        │ • System availability: 99.0% local demo target│
│                           │ • Graceful fallback to keyword search on API  │
│ Security & Access         │ • Password hashing using bcrypt               │
│                           │ • Role-Based Access Control (RBAC) enforced   │
│ Usability & Theme         │ • Professional dark-mode government UI        │
│                           │ • Desktop high-contrast resolution support    │
│ Maintainability           │ • Monolithic FastAPI architecture             │
│                           │ • Single-command Docker Compose orchestration │
└───────────────────────────┴───────────────────────────────────────────────┘
```

---

## SECTION 22 — MEASUREMENT-BASED SUCCESS METRICS

The platform success will be evaluated using formal measurement formulas executed against a curated benchmark test dataset:

### 1. Extraction Accuracy Rate ($EAR$)
$$\text{Formula: } EAR = \left( \frac{\text{Correctly Extracted Tabular Metrics}}{\text{Total Ground Truth Benchmark Metrics}} \right) \times 100\% \quad [\text{Target: } \ge 95\%]$$
* **Evaluation Method:** Compare extracted metric tuples against a manually verified 50-field benchmark dataset.

### 2. Citation Coverage Rate ($CCR$)
$$\text{Formula: } CCR = \left( \frac{\text{Generated Factual Claims with Valid Source Citations}}{\text{Total Generated Claims}} \right) \times 100\% \quad [\text{Target: } 100\%]$$
* **Evaluation Method:** Inspect generated report drafts and query outputs for unbroken page/document link attribution.

### 3. Cross-Document Discrepancy Detection Rate ($DDR$)
$$\text{Formula: } DDR = \left( \frac{\text{Flagged Numerical Discrepancies}}{\text{Total Injected Discrepancies}} \right) \times 100\% \quad [\text{Target: } 100\%]$$
* **Evaluation Method:** Test against a benchmark corpus containing 5 synthetic cross-document numerical conflicts.

### 4. Query Success Rate ($QSR$)
$$\text{Formula: } QSR = \left( \frac{\text{Queries Returning Correct Evidence-Backed Answers}}{\text{Total Benchmark Queries}} \right) \times 100\% \quad [\text{Target: } \ge 90\%]$$
* **Evaluation Method:** Run 20 curated test queries across historical CIL documents.

---

## SECTION 23 — COMPETITIVE POSITIONING & LANDSCAPE

```
┌───────────────────────────────────────────────────────────────────────────┐
│                      COMPETITIVE LANDSCAPE MATRIX                         │
├──────────────────────────┬────────────────────┬─────────────────────────┤
│ FEATURE CAPABILITY       │ GENERIC RAG / CHAT │ COALINTEL PLATFORM      │
├──────────────────────────┼────────────────────┼─────────────────────────┤
│ Multi-format Ingestion   │ Text PDFs only     │ PDF, Scan, DOCX, XLSX   │
│ Primary User Interface   │ Basic Chat Box     │ 4-Level Mining Dashboard│
│ Numerical Accuracy       │ Unvalidated LLM    │ Deterministic Validation│
│ Discrepancy Detection    │ Silent Failure     │ Flagged Conflict Engine │
│ Output Artifact          │ Free-form Text     │ Structured Report + PDF │
│ Traceability Lineage     │ None or Simple Link│ Cell & Page Level Trail │
└──────────────────────────┴────────────────────┴─────────────────────────┘
```

* **Differentiation Positioning:** Commercial products (Azure Document Intelligence, AWS Textract, UiPath, generic RAG frameworks) provide excellent individual primitives for OCR or retrieval. COALINTEL differentiates through **domain-specific integration**: combining mining entity structures, deterministic unit conversion, cross-document conflict detection, page-level evidence cards, executive dashboard visualizers, and institutional report assembly.

---

## SECTION 24 — UNIQUE SELLING PROPOSITIONS (USPs)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CORE RANKED USPs                              │
├───────┬───────────────────────────────┬─────────────────────────────────┤
│ RANK  │ USP TITLE                     │ CORE DIFFERENTIATOR             │
├───────┼───────────────────────────────┼─────────────────────────────────┤
│ 1 🏆  │ Evidence-First Lineage        │ Every number links to exact page│
│ 2 ⚡  │ Deterministic Validation Engine│ Zero unvalidated numeric output │
│ 3 🔍  │ Cross-Document Conflict Flag  │ Automatic discrepancy detection │
│ 4 📊  │ 4-Level Mining Intel Dashboard│ Visual operational command CTR  │
│ 5 📄  │ Template-Based Report Assembly│ Drafts institutional reports    │
└───────┴───────────────────────────────┴─────────────────────────────────┘
```

---

## SECTION 25 — SIH DEMONSTRATION REQUIREMENTS

### 10-Step Narrative Pitch for SIH Judges
1. **Step 1 (0:00 - 0:45):** Present the **Mining Intelligence Dashboard** showing live extracted CIL KPIs, production vs. target charts, and word clouds.
2. **Step 2 (0:45 - 1:15):** Drag-and-drop a scanned CIL annual report. Show real-time background parsing status changing to `INDEXED`.
3. **Step 3 (1:15 - 1:45):** Highlight the **Conflict Detector Badge** flagging a target mismatch between two documents.
4. **Step 4 (1:45 - 2:30):** Ask natural language query: *"What was Mine X production in FY24?"* Show cited answer with clickable page badges.
5. **Step 5 (2:30 - 3:15):** Ask comparison query: *"Compare FY23 vs FY24 production."* Show auto-generated comparison table.
6. **Step 6 (3:15 - 4:00):** Select "Parliamentary Query Response" template. Show COALINTEL draft complete briefing with citation appendix.
7. **Step 7 (4:00 - 4:30):** Open Reviewer Queue, edit report text inline, click "Approve & Seal".
8. **Step 8 (4:30 - 5:00):** Export report to polished PDF/DOCX and display immutable audit log.

---

## SECTION 26 — EDGE CASES & PRODUCT HANDLING RULES

| Edge Case | Trigger / Condition | User-Facing Behavior | System Behavior | Recovery / Fallback |
| :--- | :--- | :--- | :--- | :--- |
| **EC-001** | Unsupported / Corrupted File | Display badge: `"File unreadable or unsupported format."` | Reject file from parsing queue; log error event. | Prompt user to upload valid PDF/DOCX/XLSX. |
| **EC-002** | Poor OCR Quality ($<50\%$ Conf.) | Display warning badge: `"Low OCR confidence; routed to Review."` | Store raw OCR text; mark metrics `UNVERIFIED`. | Route to Human Review Queue for manual verification. |
| **EC-003** | Conflicting Numbers Detected | Display warning badge: `CONFLICT_DETECTED` on Dashboard. | Flag database conflict record; link both source docs. | Surface side-by-side side-drawer for reviewer sign-off. |
| **EC-004** | Insufficient Search Evidence | Output text: `"Insufficient evidence found in uploaded records."` | Block LLM text generation when context score $<0.4$. | Prompt user to upload additional historical reports. |
| **EC-005** | External LLM API Timeout | Display notification: `"API timeout; displaying raw evidence."` | Fall back to hybrid BM25 search result rendering. | Render raw top text chunks with page citations. |

---

## SECTION 27 — ERROR HANDLING & USER FEEDBACK

* **User Feedback Principle:** Technical stack trace errors (e.g., `VectorStoreException`, `PydanticValidationError`) must **NEVER** be shown to end users.
* **Friendly Error Messages:**
  * File size exceeded: *"File exceeds maximum limit of 100MB. Please select a smaller file."*
  * Unsupported format: *"Unsupported format. Please upload a PDF, DOCX, XLSX, CSV, or Image file."*
  * Session expired: *"Your session has expired. Please log in again to continue."*

---

## SECTION 28 — SYSTEM DEPENDENCIES & TECH DIRECTION

* **Input Data:** Sample CIL annual reports, CMPDI geological summaries, production logs.
* **Open Source Libraries:** PyMuPDF, Tesseract OCR 5.0, Pandas, `python-docx`, `openpyxl`, SentenceTransformers (`all-MiniLM-L6-v2`), ChromaDB.
* **Runtime Stack:** Python 3.11 FastAPI, React 18 + Vite, Tailwind CSS, Recharts, PostgreSQL 15, Docker Compose.

---

## SECTION 29 — ASSUMPTIONS REGISTER

* **ASM-001:** Sample public CIL annual reports are representative of actual production document structures.
* **ASM-002:** Internet connectivity is available during hackathon judging for hosted API calls (with local fallback prepared).
* **ASM-003:** First-year student engineering lead is familiar with basic React component structures and Python FastAPI endpoint definitions.

---

## SECTION 30 — RISK & MITIGATION REGISTER

| Risk ID | Risk Description | Prob. | Impact | Mitigation Strategy | Contingency Plan |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **RSK-001** | OCR fails on low-quality scanned historical PDF | Med | High | Image thresholding & grayscale preprocessing | Manual inline edit in Review Queue |
| **RSK-002** | LLM API timeout during live judge demo | Low | High | Retry logic & streaming responses | Cached API response fallback |
| **RSK-003** | Table structure flattened into incorrect columns | Med | Med | Bounding-box visual cell detection | Surface source page image preview |
| **RSK-004** | Student dev hits integration roadblock | Med | Med | Modular API contracts & service boundaries| Tech Lead assists with API wiring |

---

## SECTION 31 — EXPLICIT OUT-OF-SCOPE DECLARATIONS

To protect the student development team from scope creep during the 8-day sprint, the following features are **STRICTLY EXCLUDED** from the MVP:
1. Training custom foundation AI models from scratch.
2. Implementing complex microservice or Kubernetes infrastructure.
3. Microsoft GraphRAG knowledge graph implementations.
4. Live voice assistant or regional language speech recognition.
5. Production NIC SSO authentication integration.
6. Direct SAP / ERP enterprise database integrations.

---

## SECTION 32 — SIH OBJECTIVE TRACEABILITY MATRIX

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    SIH OBJECTIVE TRACEABILITY MATRIX                      │
├──────────────────────────┬───────────────────────┬────────────────────────┤
│ SIH26023 REQUIREMENT     │ PRODUCT MODULE        │ MVP FUNCTIONAL REQ ID  │
├──────────────────────────┼───────────────────────┼────────────────────────┤
│ Automated Report Gen     │ MOD-10: Reporting     │ FR-REP-001             │
│ Word Cloud & Topic ID    │ MOD-09: WordCloud     │ FR-TOP-001             │
│ AI Query & Response      │ MOD-08: Query AI      │ FR-AI-001              │
│ Document Processing      │ MOD-03: Parsing       │ FR-OCR-001, FR-OCR-002 │
│ Data Validation          │ MOD-05: Validator     │ FR-VAL-001, FR-VAL-002 │
│ Conflict Detection       │ MOD-05: Validator     │ FR-VAL-003             │
│ Historical Retrieval     │ MOD-06: Indexer       │ FR-SRCH-001            │
│ Traceability Lineage     │ MOD-05: Validator     │ FR-TRC-001             │
└──────────────────────────┴───────────────────────┴────────────────────────┘
```

---

## SECTION 33 — PRODUCT ROADMAP

```
[ MVP: 8-DAY SPRINT ] ──> [ PHASE 2: MONTH 1-3 ] ──> [ PHASE 3: MONTH 6+ ]
• Core Ingestion         • GraphRAG Integration   • Full Enterprise NIC SSO
• Deterministic Validation• Multilingual Support  • Direct Sap/ERP Connector
• Dashboard & Q&A        • Custom Mining Model    • Multi-tenant Cloud Infra
• Report Generator       • Voice Query Interface  • Geospatial GIS Mapping
```

---

## SECTION 34 — FINAL MVP CHECKLIST & SIGN-OFF

### MVP Readiness Verification Checklist
* [x] **Authentication:** JWT Login for Analyst and Reviewer roles.
* [x] **Ingestion:** Drag-and-drop batch upload for PDF files.
* [x] **Parsing:** PyMuPDF text parser + Tesseract OCR table extractor.
* [x] **Structuring:** PostgreSQL storage of metric tuples `(Mine, Year, Metric, Value, Unit)`.
* [x] **Validation:** Deterministic unit converter & cross-document conflict detector.
* [x] **Dashboard:** 4-Level Executive Dashboard (KPIs, Charts, Word Cloud, Evidence Feed).
* [x] **Query Assistant:** Hybrid vector-BM25 search with clickable citation badges.
* [x] **Reporting:** Template-driven report assembly for Parliamentary Questions.
* [x] **Review:** Human-in-the-Loop review queue & inline text editor.
* [x] **Export:** Formatted PDF export and immutable audit logging.

### Document Sign-off
* **Senior Product Architect:** *Approved for Technical & Functional Handoff.*
* **Lead System Architect:** *Architecture Aligned with Master Specification.*
* **Engineering Team Lead:** *Implementation Feasible for 8-Day Sprint.*
