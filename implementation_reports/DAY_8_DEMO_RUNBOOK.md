# DAY 8 DEMO RUNBOOK & OPERATOR MANUAL
## COALINTEL — AI-Powered Evidence-Driven Mining Intelligence Platform

---

### 1. SYSTEM STARTUP COMMANDS

#### Option A: Docker Compose Orchestration (Recommended)
```bash
# Start PostgreSQL, FastAPI Backend, and React Frontend containers
docker-compose up --build
```
* **Frontend SPA:** http://localhost:3000
* **Backend REST API:** http://localhost:8000
* **API Documentation:** http://localhost:8000/api/v1/docs

#### Option B: Local Developer Mode
```bash
# 1. Initialize Database & Seed Default Accounts
python backend/database_seed.py

# 2. Start FastAPI Server
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. Start React Frontend SPA (in separate terminal)
cd frontend
npm run dev
```

---

### 2. PRE-SEEDED DEMONSTRATION ACCOUNTS

```
┌─────────────────┬───────────────────┬──────────────┬────────────────────────────┐
│ USERNAME        │ PASSWORD          │ ROLE         │ PERMITTED ACTIONS          │
├─────────────────┼───────────────────┼──────────────┼────────────────────────────┤
│ admin           │ admin123          │ Admin        │ Full system management     │
│ analyst         │ analyst123        │ Analyst      │ Upload, Query, Draft Report│
│ reviewer        │ reviewer123       │ Reviewer     │ Resolve Conflict, Approve  │
│ auditor         │ auditor123        │ Viewer       │ Read-only View, Audit Logs │
└─────────────────┴───────────────────┴──────────────┴────────────────────────────┘
```

---

### 3. STEP-BY-STEP OPERATOR DEMONSTRATION FLOW

1. **Login Screen (`/login`):**
   * Select a quick-login pill (`analyst` or `admin`).
   * Click **Sign In to COALINTEL Platform**.
2. **Executive Command Center (`/dashboard`):**
   * View Level 1 KPIs (Total Mined Coal 42.50 MT, OBR 120.40 M.Cu.M, Active Conflicts).
   * Inspect Level 2 Recharts target vs actual bar/line charts.
   * View Level 3 TF-IDF Mining Word Cloud.
3. **Document Ingestion Hub (`/documents`):**
   * Drag & drop `ECL_Annual_Report_2023-24.pdf` into the upload zone.
   * Observe instant SHA-256 duplicate digest verification.
4. **Document Lineage Inspector (`/documents/1`):**
   * Inspect page-by-page extracted metrics (`Rajmahal OC`, `42.50 Lakh Tonnes` normalized to `4.25 MT`).
5. **Cited Q&A Assistant (`/query`):**
   * Ask query: *"What was the total coal production for ECL in FY 2023-24?"*
   * Observe answer generated inside `<untrusted_document_context>` XML boundary.
   * Click citation tag `[ECL_Annual_Report_2023-24.pdf, Page 14]` to inspect source evidence drawer.
6. **Data Quality & Validation Feed (`/validation`):**
   * Inspect arithmetic consistency warnings ($> 5.0\%$ discrepancy).
7. **Cross-Document Conflict Resolver (`/conflicts`):**
   * Switch user role to `reviewer`.
   * Open conflict case for `Rajmahal OC` (1.67% discrepancy $> 1.0\%$).
   * Click **Resolve Conflict** and accept Document A (`42.50 MT`).
8. **Report Assembly Wizard (`/reports`):**
   * Select template `Parliamentary Inquiry Reply`.
   * Click **Assemble Report Draft** to compile ReportLab PDF document.
   * Click **Approve Report** to transition status to `APPROVED`.
9. **System Security Audit Trail (`/audit`):**
   * Inspect append-only event ledger tracking `LOGIN_SUCCESS`, `DOCUMENT_UPLOAD`, `CONFLICT_RESOLVE`, `REPORT_GENERATE`, and `REPORT_APPROVE`.
