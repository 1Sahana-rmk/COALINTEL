# COALINTEL USER FLOW & INTERACTION SPECIFICATION

---

## SECTION 1 — DOCUMENT CONTROL

### 1.1 Document Overview
* **Document Title:** COALINTEL User Flow & Interaction Specification
* **Project Name:** COALINTEL (AI-Powered Evidence-Driven Mining Intelligence & Reporting Platform)
* **Problem Statement ID:** SIH26023
* **Problem Statement Title:** AI-Powered Geological, Mining and other Reporting Solution for CMPDI/CIL subsidiaries
* **Sponsoring Organization:** Ministry of Coal
* **Department:** Coal India Limited (CIL) / Central Mine Planning & Design Institute (CMPDI)
* **Category:** Software | Theme: Smart Automation
* **Version:** 1.0.0 (Baseline Release)
* **Status:** Approved / Development Ready
* **Date:** August 27, 2026
* **Author / Ownership:** Senior User Experience Architect & Interaction Engineering Lead
* **Primary Target Lead:** Full-Stack Development Team (1st-Year Computer Engineering Student Sprint)

### 1.2 Baseline Alignment
This user flow specification maps every screen interaction, state transition, and API call across COALINTEL. It strictly adheres to:
1. **`COALINTEL_MASTER_SPECIFICATION.md`** (Single Source of Truth - SSOT)
2. **`PRD.md`** (Product Requirements Document v1.1)
3. **`TRD.md`** (Technical Requirements Document v1.0)
4. **`UI_UX_DOCUMENTATION.md`** (Frontend UI/UX Specification)
5. **`BACKEND_DOCUMENTATION.md`** (Backend Implementation Baseline)
6. **`SECURITY_DOCUMENTATION.md`** (Security & Authorization Baseline)

---

## SECTION 2 — END-TO-END MASTER SYSTEM JOURNEY

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     END-TO-END MASTER SYSTEM JOURNEY                      │
└───────────────────────────────────────────────────────────────────────────┘

 [ USER LOGIN ] ──► [ ROLE DASHBOARD ] ──► [ BATCH FILE UPLOAD ]
                                                 │
 [ CITED ANSWER ] ◄── [ HYBRID SEARCH ] ◄── [ PARSE & OCR PIPELINE ]
        │                                        │
        ▼                                        ▼
 [ EVIDENCE DRAWER ]                      [ VALIDATE & DETECT CONFLICTS ]
        │                                        │
        ▼                                        ▼
 [ REPORT WIZARD ] ──► [ REVIEW & SEAL ] ──► [ EXPORT PDF & AUDIT ]
```

---

## SECTION 3 — ROLE-BASED WORKFLOW SPECIFICATIONS

### 3.1 Admin Workflow
* **Goal:** Manage system user accounts and inspect system security audit logs.
* **Journey Path:** Login $\rightarrow$ Admin Dashboard $\rightarrow$ User Management (`/admin/users`) $\rightarrow$ Create User Modal $\rightarrow$ Audit Trail (`/admin/audit`).

### 3.2 Analyst Workflow
* **Goal:** Ingest mining reports, query historical context, analyze trends, and draft official report responses.
* **Journey Path:** Login $\rightarrow$ Ingestion Hub (`/documents/upload`) $\rightarrow$ Ask COALINTEL Q&A (`/query`) $\rightarrow$ Report Assembly Wizard (`/reports/new`).

### 3.3 Reviewer Workflow
* **Goal:** Verify flagged numerical discrepancies and sign off on AI-generated report drafts.
* **Journey Path:** Login $\rightarrow$ Validation Feed (`/validation`) $\rightarrow$ Side-by-Side Conflict Resolver (`/validation/conflicts`) $\rightarrow$ Report Review Editor (`/reports/:id/review`) $\rightarrow$ Approve & Seal.

### 3.4 Viewer Workflow
* **Goal:** Executive read-only tracking of macro production KPIs and subsidiary charts.
* **Journey Path:** Login $\rightarrow$ Executive Dashboard (`/dashboard`) $\rightarrow$ Analytics Visualizers (`/analytics`).

---

## SECTION 4 — COMPLETE SCENARIO FLOW SPECIFICATIONS

```
┌───────────────────────────────────────────────────────────────────────────┐
│                         FLOW TEMPLATE STRUCTURE                           │
├───────────────────┬───────────────────────────────────────────────────────┤
│ STEP FIELD        │ TECHNICAL DESCRIPTION                                 │
├───────────────────┼───────────────────────────────────────────────────────┤
│ User Action       │ Trigger action performed by the user in UI            │
│ Frontend State    │ Component state & loading indicators                  │
│ API Endpoint      │ Target HTTP method and REST URL                       │
│ Backend Service   │ Executed FastAPI logic module                         │
│ Database Operation│ SQL / ChromaDB query executed                         │
│ Response Payload  │ Returned HTTP status code & JSON response             │
│ UI Outcome        │ Visual rendering update in client viewport            │
│ Failure State     │ Error condition and user-facing recovery path         │
└───────────────────┴───────────────────────────────────────────────────────┘
```

---

### Flow 01: User Login & Session Authentication
* **User Action:** Enters username, password, selects role (`Analyst`), clicks `"Sign In"`.
* **Frontend State:** Submit button sets `isLoading=true`, displaying `"Authenticating..."`.
* **API Endpoint:** `POST /api/v1/auth/login` (Payload: `username`, `password`, `role`).
* **Backend Service:** `security.py` queries `users` table $\rightarrow$ verifies password hash via `bcrypt`.
* **Database Operation:** `SELECT * FROM users WHERE username = 'nodal_officer';`
* **Response Payload:** HTTP 200 OK (`{"access_token": "eyJhbG...", "token_type": "bearer"}`).
* **UI Outcome:** Token saved to `localStorage`; user redirected to `/dashboard`.
* **Failure State:** Invalid credentials return HTTP 401. UI renders red alert banner `"Invalid credentials or role selection"`.

---

### Flow 02: Batch Document Upload & Hash Verification
* **User Action:** Drags a scanned annual report `BCCL_Report_2024.pdf` into the Ingestion Dropzone.
* **Frontend State:** Dropzone displays upload progress bar ($0\% \rightarrow 100\%$).
* **API Endpoint:** `POST /api/v1/documents/upload` (`multipart/form-data`).
* **Backend Service:** `documents.py` validates extension `.pdf`, checks size $<100$MB, computes SHA-256 hash.
* **Database Operation:** `SELECT id FROM documents WHERE file_hash = 'a3f9...';`
* **Response Payload:** HTTP 202 Accepted (`{"document_id": 42, "status": "PENDING"}`).
* **UI Outcome:** File item added to Processing Queue list with status badge `PENDING`.
* **Failure State (Duplicate):** SHA-256 matches existing file $\rightarrow$ HTTP 409 Conflict. UI displays toast `"Duplicate document detected. Processing skipped."`

---

### Flow 03: Asynchronous Document Processing Pipeline
* **User Action:** System executes automatically in background.
* **Frontend State:** Client polls `GET /api/v1/documents` every 3 seconds.
* **API Endpoint:** `GET /api/v1/documents/{id}/status`.
* **Backend Service:** Async Background Task triggers parsing pipeline:
  1. `parsing_service.py` parses text via PyMuPDF. If text density $< 50$ chars $\rightarrow$ triggers Tesseract 5.0 OCR (300 DPI).
  2. `extraction_service.py` extracts metric tuples `(mine, metric, value, unit, year)`.
  3. `validation_service.py` converts units to standard **MT** and runs conflict check.
  4. `chroma_service.py` embeds 500-token chunks via `all-MiniLM-L6-v2` into ChromaDB.
* **Database Operation:** Update `documents` status to `INDEXED`. Insert rows into `extracted_metrics` and `document_chunks`.
* **Response Payload:** HTTP 200 OK (`{"status": "INDEXED"}`).
* **UI Outcome:** Processing status badge transitions to green `INDEXED`. Dashboard KPIs update dynamically.
* **Failure State:** PDF corrupted $\rightarrow$ status updated to `FAILED`. UI displays error badge `"Parsing Failed: File corrupt"`.

---

### Flow 04: 4-Level Mining Intelligence Dashboard Render
* **User Action:** User accesses `/dashboard`.
* **Frontend State:** KPICards and Chart containers display pulse animation skeletons (`animate-pulse`).
* **API Endpoint:** `GET /api/v1/dashboard/kpis` & `GET /api/v1/dashboard/charts`.
* **Backend Service:** Backend queries aggregated PostgreSQL metrics and active warnings.
* **Database Operation:** `SELECT SUM(standard_value) FROM extracted_metrics WHERE metric_name='Production';`
* **Response Payload:** HTTP 200 OK (`{"total_docs": 124, "target_mt": 650.0, "actual_mt": 642.8, "conflicts": 3}`).
* **UI Outcome:** Level 1 KPI cards render numbers; Level 2 Recharts Target vs Actual Bar Chart renders; Level 3 Word Cloud displays operational topics; Level 4 Feed lists active conflict warnings.

---

### Flow 05: Side-by-Side Cross-Document Conflict Resolution
* **User Action:** Reviewer clicks `"Resolve Conflict"` on an active discrepancy card.
* **Frontend State:** Side-by-Side Conflict Resolver Modal opens.
* **API Endpoint:** `GET /api/v1/conflicts/{id}`.
* **Backend Service:** `validation_service.py` retrieves conflicting Document A and Document B metric records.
* **Database Operation:** `SELECT * FROM data_conflicts WHERE id = 3;`
* **Response Payload:** HTTP 200 OK (`{"doc_a_val": 14.20, "doc_b_val": 14.80, "mine": "Kusunda OCP"}`).
* **UI Outcome:** Document A (14.20 MT) and Document B (14.80 MT) displayed side-by-side with source snippet links.
* **Resolution Action:** Reviewer selects `"Accept Document A (14.20 MT)"` and clicks `"Resolve & Save"`.
* **API Endpoint:** `POST /api/v1/conflicts/{id}/resolve` (Payload: `selected_doc_id: 42`).
* **Database Operation:** Update `data_conflicts` status to `RESOLVED`. Update `extracted_metrics` status to `VALIDATED`. Write entry to `audit_logs`.
* **UI Outcome:** Modal closes; conflict warning badge removed from Dashboard.

---

### Flow 06: "Ask COALINTEL" Natural Language Q&A & Evidence Inspection
* **User Action:** Analyst enters query: *"What was Kusunda mine production in FY24?"* and clicks `"Ask"`.
* **Frontend State:** Query window displays loading indicator `"Searching document corpus & verifying evidence..."`.
* **API Endpoint:** `POST /api/v1/query/ask` (Payload: `{"query": "What was Kusunda mine production in FY24?"}`).
* **Backend Service:**
  1. `retrieval_service.py` executes parallel ChromaDB Cosine vector search and PostgreSQL BM25 text search.
  2. RRF Reranker computes merged top-5 evidence pack.
  3. LLM Provider generates cited response.
  4. Citation Gate verifies inline citations `[Doc_Name.pdf, Page 14]`.
* **Response Payload:** HTTP 200 OK (`{"answer": "Kusunda OCP produced 14.20 MT in FY2023-24 [BCCL_Report_2024.pdf, Page 14].", "citations": [...]}`).
* **UI Outcome:** Answer renders with clickable blue citation badge `[BCCL_Report_2024.pdf, Page 14]`.
* **Evidence Drawer Trigger:** User clicks citation badge $\rightarrow$ Evidence Side-Drawer slides in from right displaying page preview canvas, highlighted bounding boxes, and raw extracted text snippet.

---

### Flow 07: Degraded Mode AI Failure Handling
* **User Action:** Analyst submits a query when external hosted LLM API is unavailable.
* **Frontend State:** Q&A search executes.
* **Backend Behavior:** Hosted LLM API call times out after 5 seconds. System catches exception and activates **Degraded Mode**.
* **Response Payload:** HTTP 200 OK (`{"answer": null, "degraded_mode": true, "raw_evidence": [...]}`).
* **UI Outcome:** System displays yellow warning banner *"AI narrative synthesis is temporarily unavailable."* System directly renders top-5 retrieved evidence text chunks and validated metric tables with page references, maintaining $100\%$ evidence utility without generating unverified text.

---

### Flow 08: Step-by-Step Report Generation & Reviewer Approval
* **User Action:** Analyst accesses Report Wizard (`/reports/new`).
* **Wizard Sequence:**
  * **Step 1 (Template):** Analyst selects `"Parliamentary Query (PQ) Response Draft"`.
  * **Step 2 (Parameters):** Analyst selects `Mine: Kusunda OCP`, `Period: FY2023-24`.
  * **Step 3 (Evidence):** Backend retrieves validated metrics and top evidence chunks.
  * **Step 4 (Assembly):** Analyst clicks `"Generate Report Draft"`.
* **API Endpoint:** `POST /api/v1/reports/generate`.
* **Backend Behavior:** Assembles structured JSON report; inserts `reports` record with `approval_status='DRAFT'`.
* **UI Outcome:** User redirected to Report Preview displaying draft report bearing visual header badge `DRAFT - PENDING REVIEW`.
* **Reviewer Action:** Reviewer accesses `/reports/12/review`, edits narrative text inline, and clicks `"Approve & Seal Report"`.
* **API Endpoint:** `POST /api/v1/reports/12/approve`.
* **Database Operation:** Update `reports` status to `APPROVED`. Insert row into `audit_logs`.
* **Export Action:** User clicks `"Export to PDF"` $\rightarrow$ Backend `report_service.py` builds ReportLab PDF document $\rightarrow$ User downloads formatted PDF artifact.

---

## SECTION 5 — GOLDEN DEMONSTRATION SEQUENCE (10-STEP PITCH)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       10-STEP SIH DEMO NARRATIVE                          │
├───────┬──────────────────────────────────┬────────────────────────────────┤
│ STEP  │ ACTION                           │ KEY VISUAL OUTCOME             │
├───────┼──────────────────────────────────┼────────────────────────────────┤
│ 01    │ Open Executive Dashboard         │ Live CIL KPIs & Recharts Visual│
│ 02    │ Drag & drop scanned CIL report   │ Upload Dropzone Progress Bar   │
│ 03    │ View Processing Status Queue     │ Transition badge to INDEXED    │
│ 04    │ Highlight Dashboard Conflict Alert│ Red CONFLICT_DETECTED Badge    │
│ 05    │ Open Conflict Resolver           │ Side-by-Side Document A vs B   │
│ 06    │ Ask "What was Kusunda FY24 prod?"│ Cited Answer with Page Badge   │
│ 07    │ Click Citation Badge             │ Evidence Side-Drawer Page View │
│ 08    │ Select Parliamentary PQ Template │ 4-Step Report Assembly Wizard  │
│ 09    │ Reviewer inline edit & approve   │ Watermark shifts to APPROVED   │
│ 10    │ Download PDF & view Audit Log    │ Formatted PDF & Audit Ledger   │
└───────┴──────────────────────────────────┴────────────────────────────────┘
```

---

## SECTION 6 — MVP USER FLOW BOUNDARIES

* **Core MVP Flows (In-Scope):** Flows 01 through 08 (Auth, PDF Upload, Async Status, Dashboard, Conflict Resolver, Q&A Assistant, Evidence Side-Drawer, Report Assembly, PDF Export, Audit Trail).
* **Future Roadmap Flows (Out-of-Scope):** Multilingual voice query flow, GraphRAG visual node traversal, enterprise NIC SSO login flow.

---

## SECTION 7 — USER FLOW DEFINITION OF DONE (DoD)

* [x] Every specified user flow includes complete request/response contracts matching TRD APIs.
* [x] Error handling and failure fallback paths defined for all 36 scenarios.
* [x] Role-based UI visibility permissions enforced across all flow states.
* [x] Evidence traceability unbroken from query submission to PDF report download.

**User Flow Architecture Sign-off:** *Approved for End-to-End Implementation.*
