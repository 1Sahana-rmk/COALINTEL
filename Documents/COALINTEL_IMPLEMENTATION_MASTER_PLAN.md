# COALINTEL IMPLEMENTATION MASTER PLAN
## Engineering Execution Roadmap (Day 0 → Day 8)

---

## SECTION 1 — EXECUTIVE OVERVIEW

### 1.1 Project Vision & Problem Context
**COALINTEL** is an AI-powered, evidence-driven geological, mining, and reporting intelligence platform engineered for **Coal India Limited (CIL)**, its 8 subsidiaries, and the **Central Mine Planning & Design Institute (CMPDI)** under the **Ministry of Coal** (Problem Statement ID: **SIH26023**).

The system replaces manual, error-prone, and fragmented document workflows with a unified, auditable intelligence solution that ingests heterogeneous documents (scanned/digital PDFs, DOCX, XLSX, CSV), extracts numerical metrics, performs unit normalization, validates arithmetic consistency, resolves cross-document data conflicts, powers cited Q&A search via Hybrid RAG, and generates template-driven official reports.

### 1.2 Status Summary
* **Documentation Phase:** **COMPLETE (100% Frozen Baseline, 98.5% Consistency Rating)**
* **Source Code Phase:** **0% IMPLEMENTED / READY TO BEGIN DAY 0**

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             PROJECT STATUS DASHBOARD                             │
├──────────────────────────┬─────────────────────────┬─────────────────────────────┤
│ PHASE                    │ STATUS                  │ COMPLETION                  │
├──────────────────────────┼─────────────────────────┼─────────────────────────────┤
│ 1. Documentation & Architecture │ ✅ FROZEN                │ 100% Complete               │
│ 2. Implementation Master Plan   │ ✅ COMPLETE (This Doc)   │ 100% Complete               │
│ 3. Day 0 Infrastructure Setup   │ 🟡 READY TO START       │ 0% Code Written             │
│ 4. Day 1-8 Development Sprint   │ ⏳ PENDING DAY 0 EXEC    │ 0% Code Written             │
└──────────────────────────┴─────────────────────────┴─────────────────────────────┘
```

### 1.3 System Architecture Overview
COALINTEL is designed as a high-velocity **Modular Monolith** using containerized Docker services:
1. **Frontend SPA:** React 18 + Vite + Tailwind CSS + Recharts + Lucide Icons.
2. **Backend API:** FastAPI (Python 3.11) managing async endpoints, document processing background tasks, ORM transactions, and validation engines.
3. **Relational Database:** PostgreSQL 15 storing core application data across 7 relational tables.
4. **Vector Store & Retrieval:** ChromaDB local vector store (`all-MiniLM-L6-v2` embeddings, 384d) + PostgreSQL Full-Text BM25 Keyword Search, fused using Reciprocal Rank Fusion (RRF, $k=60$).
5. **Document Ingestion:** PyMuPDF + Tesseract OCR fallback + Regex entity parsing + deterministic unit normalization engine.
6. **Reporting Engine:** ReportLab template-driven document generation and PDF export.

### 1.4 Development Philosophy & Guidelines
* **Deterministic Trust First:** LLMs never perform arithmetic or unit conversion. All numbers are normalized ($1 \text{ Lakh Tonnes} = 0.1 \text{ MT}$) and validated in Python/SQL before LLM invocation.
* **Citation Gating:** Zero uncited LLM outputs. Every generated answer must include clickable page-level citations (`[Document_Name.pdf, Page X]`).
* **Zero Scope Creep:** Build strictly what is documented for MVP. Out-of-scope features (GraphRAG, fine-tuning, voice UI, NIC SSO, Kubernetes) are explicitly barred.

---

## SECTION 2 — FROZEN ENGINEERING BASELINE

The engineering stack is strictly frozen as defined in `COALINTEL_MASTER_SPECIFICATION.md` and `TRD.md`:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            FROZEN TECHNOLOGY STACK                               │
├──────────────────┬───────────────────────────────────────────────────────────────┤
│ LAYER            │ APPROVED TECHNOLOGIES                                         │
├──────────────────┼───────────────────────────────────────────────────────────────┤
│ Frontend         │ React 18, Vite, Tailwind CSS, Recharts, Lucide Icons         │
│ Backend          │ Python 3.11, FastAPI, SQLAlchemy 2.0 (ORM), Pydantic v2       │
│ Database         │ PostgreSQL 15 (Relational Store + Full-Text Search)           │
│ Vector Search    │ ChromaDB (Local persistent), SentenceTransformers             │
│ Embedding Model  │ `all-MiniLM-L6-v2` (384 Dimensions, Cosine Distance)          │
│ Ingestion/OCR    │ PyMuPDF (fitz), Tesseract OCR (pytesseract), Python-docx, openpyxl │
│ Reporting Engine │ ReportLab (PDF Assembly), Jinja2                             │
│ Containerization │ Docker Compose (3 containers: `frontend`, `backend`, `db`)   │
└──────────────────┴───────────────────────────────────────────────────────────────┘
```

---

## SECTION 3 — SOURCE OF TRUTH & DECISION RULES

### 3.1 Specification Authority Hierarchy
When interpreting specifications or resolving implementation ambiguities, engineers MUST strictly enforce the following 8-tier hierarchy:

1. **`COALINTEL_MASTER_SPECIFICATION.md`** $\longrightarrow$ **LEVEL 1 — PREEMINENT SSOT**
2. **`TRD.md`** $\longrightarrow$ LEVEL 2 — Technical Architecture & Stack Authority
3. **`PRD.md`** $\longrightarrow$ LEVEL 3 — Product Scope & Feature Boundary Authority
4. **`UI_UX_DOCUMENTATION.md`** $\longrightarrow$ LEVEL 4 — Frontend UI Layouts & Data Contract Authority
5. **`BACKEND_DOCUMENTATION.md`** $\longrightarrow$ LEVEL 5 — Backend Controller & REST API Contract Authority
6. **`SECURITY_DOCUMENTATION.md`** $\longrightarrow$ LEVEL 6 — Security, Authentication & Audit Authority
7. **`USER_FLOW_DOCUMENTATION.md`** $\longrightarrow$ LEVEL 7 — Interaction Sequence & Workflow Authority
8. **`extracted_doc_text.txt`** $\longrightarrow$ LEVEL 8 — Domain Research Context & Entity Reference

### 3.2 Non-Negotiable Decision Rules
* **Rule A (Master Specification Dominance):** If any subordinate document conflicts with `COALINTEL_MASTER_SPECIFICATION.md`, the Master Specification prevails.
* **Rule B (Security Primacy):** `SECURITY_DOCUMENTATION.md` governs all auth, RBAC, input sanitization, and context isolation rules.
* **Rule C (Backend Contract Primacy):** `BACKEND_DOCUMENTATION.md` governs backend service boundaries, request/response DTOs, and status codes.
* **Rule D (UI Data Contract Primacy):** `UI_UX_DOCUMENTATION.md` governs state management, screen layout hierarchies, and API integration payloads.
* **Rule E (User Flow Primacy):** `USER_FLOW_DOCUMENTATION.md` governs multi-step interaction logic and status transition guards.
* **Rule F (Domain Context Boundary):** `extracted_doc_text.txt` supplies coal mining terminology and sample metrics; it cannot override architectural choices.
* **Rule G (Explicit Contradiction Logging):** Never silently fix or bypass a documentation contradiction. Identify, quote, reference the hierarchy, resolve according to hierarchy, and log in Section 23.

---

## SECTION 4 — CURRENT IMPLEMENTATION STATUS

| Module / System Component | Documentation Status | Source Code Status | Engineering Readiness |
| :--- | :--- | :--- | :--- |
| **Product Scope & Requirements** | Complete (100%) | 0% Implemented | ✅ Ready for Sprint |
| **Architecture Topology & Docker** | Complete (100%) | 0% Implemented | ✅ Ready for Day 0 Setup |
| **PostgreSQL Database Schema (7 Tables)** | Complete (100%) | 0% Implemented | ✅ Ready for Day 1 DDL |
| **REST API Contracts (11 Resource Groups)** | Complete (100%) | 0% Implemented | ✅ Ready for Day 1 FastAPI |
| **Security, RBAC & Prompt Isolation** | Complete (100%) | 0% Implemented | ✅ Ready for Day 1 Auth |
| **Frontend UI Layouts (23 Screens)** | Complete (100%) | 0% Implemented | ✅ Ready for Day 2 React |
| **Ingestion, Parser & OCR Engine** | Complete (100%) | 0% Implemented | ✅ Ready for Day 3-4 |
| **ChromaDB Vector & Hybrid RAG Engine** | Complete (100%) | 0% Implemented | ⚠️ Ready (LLM API Key set in `.env`) |
| **Validation, Conflict & Report Engine** | Complete (100%) | 0% Implemented | ✅ Ready for Day 6 |
| **Automated Testing & Golden Dataset** | Complete (100%) | 0% Implemented | ✅ Ready for Day 8 |

> **CRITICAL REMINDER:** Documentation readiness ($100\%$) $\neq$ Code readiness ($0\%$). The code implementation sprint begins at Day 0 following approval of this Master Plan.

---

## SECTION 5 — PROJECT DIRECTORY / CODEBASE STRUCTURE

The project directory structure is derived directly from `TRD.md` and `BACKEND_DOCUMENTATION.md`:

```
COALINTEL/
├── Documents/                           # Frozen Documentation Suite (SSOT)
│   ├── COALINTEL_MASTER_SPECIFICATION.md
│   ├── TRD.md
│   ├── PRD.md
│   ├── UI_UX_DOCUMENTATION.md
│   ├── BACKEND_DOCUMENTATION.md
│   ├── SECURITY_DOCUMENTATION.md
│   ├── USER_FLOW_DOCUMENTATION.md
│   ├── extracted_doc_text.txt
│   ├── COALINTEL_DOCUMENTATION_CROSS_CHECK_REPORT.md
│   ├── COALINTEL_FINAL_DOCUMENTATION_FREEZE_AUDIT.md
│   └── COALINTEL_IMPLEMENTATION_MASTER_PLAN.md  # THIS MASTER EXECUTION PLAN
├── docker-compose.yml                   # Docker Orchestration Configuration
├── .env.example                         # Environment Variables Template
├── README.md                            # Setup & Operations Guide
├── backend/                             # Python 3.11 FastAPI Application
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                          # FastAPI Entrypoint & Middleware
│   ├── config.py                        # Pydantic Settings & Env Vars
│   ├── database.py                      # SQLAlchemy Engine & Session Setup
│   ├── app/
│   │   ├── api/                         # REST API Route Controllers
│   │   │   ├── auth.py                  # POST /api/v1/auth/login
│   │   │   ├── documents.py             # Upload, List, Page Details APIs
│   │   │   ├── dashboard.py             # KPIs, Charts, WordCloud APIs
│   │   │   ├── query.py                 # Hybrid RAG & Q&A Assistant API
│   │   │   ├── validation.py            # Feed, Conflict Resolution APIs
│   │   │   └── reports.py               # Report Generation & Export APIs
│   │   ├── core/                        # Core Utilities & Security
│   │   │   ├── security.py              # JWT, Bcrypt, OAuth2 Scheme
│   │   │   ├── rbac.py                  # Role-based Access Control Guards
│   │   │   └── exceptions.py            # Custom HTTP Error Handlers
│   │   ├── models/                      # SQLAlchemy Database ORM Models
│   │   │   ├── user.py                  # `users` table
│   │   │   ├── document.py              # `documents` table
│   │   │   ├── metric.py                # `extracted_metrics` table
│   │   │   ├── chunk.py                 # `document_chunks` table
│   │   │   ├── conflict.py              # `data_conflicts` table
│   │   │   ├── report.py                # `reports` table
│   │   │   └── audit.py                 # `audit_logs` table
│   │   ├── schemas/                     # Pydantic Request/Response DTOs
│   │   │   ├── auth.py
│   │   │   ├── document.py
│   │   │   ├── query.py
│   │   │   ├── validation.py
│   │   │   └── report.py
│   │   ├── services/                    # Business Logic Engines
│   │   │   ├── ingestion_service.py     # Hash check, File Storage, MIME validation
│   │   │   ├── parsing_service.py       # PyMuPDF, Tesseract OCR, Table Extractor
│   │   │   ├── normalization_service.py # Unit Multipliers (Lakh Tonnes -> MT)
│   │   │   ├── validation_engine.py     # Arithmetic & Cross-Doc Conflict Check
│   │   │   ├── embedding_service.py     # SentenceTransformers Vectorization
│   │   │   ├── retrieval_service.py     # ChromaDB + PG BM25 + RRF (k=60)
│   │   │   ├── llm_provider.py          # LLM Provider Abstraction & Prompts
│   │   │   └── report_service.py        # ReportLab PDF Generation
│   │   └── storage/                     # Local Volume Storage Mounts
│   │       ├── uploads/                 # Original Raw Documents
│   │       ├── chroma_db/               # Persistent ChromaDB Vector Index
│   │       └── generated_reports/       # Exported ReportLab PDFs
│   └── tests/                           # Backend Pytest Suite
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_ingestion.py
│       ├── test_normalization.py
│       ├── test_validation.py
│       └── test_rag.py
└── frontend/                            # React 18 + Vite SPA
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── main.jsx                     # React Entrypoint
        ├── App.jsx                      # App Shell & Router
        ├── api/                         # Axios API Client & Interceptors
        │   ├── client.js
        │   ├── authApi.js
        │   ├── documentApi.js
        │   ├── dashboardApi.js
        │   ├── queryApi.js
        │   ├── validationApi.js
        │   └── reportApi.js
        ├── components/                  # Reusable Design System Tokens & Widgets
        │   ├── common/                  # Buttons, Cards, Modals, Badges, Loaders
        │   ├── layout/                  # Sidebar, Header, AppShell, Footer
        │   ├── dashboard/               # KPI Cards, Recharts, WordCloud, Feed
        │   ├── documents/               # Dropzone Upload, File Table, PDF Viewer
        │   ├── query/                   # Q&A Box, Citation Cards, Degraded Alert
        │   ├── validation/              # Conflict Cards, Resolution Modal
        │   └── reports/                 # Template Selector, PDF Previewer
        ├── context/                     # Global State (AuthContext, ToastContext)
        │   ├── AuthContext.jsx
        │   └── ToastContext.jsx
        └── pages/                       # Screen Views (23 Documented Layouts)
            ├── LoginPage.jsx
            ├── DashboardPage.jsx
            ├── DocumentsPage.jsx
            ├── DocumentDetailPage.jsx
            ├── QueryAssistantPage.jsx
            ├── ConflictResolverPage.jsx
            ├── ReportWizardPage.jsx
            └── AuditLogsPage.jsx
```

---

## SECTION 6 — DAY 0 IMPLEMENTATION: ENVIRONMENT & DEPLOYMENT FOUNDATION

### 6.1 Deliverables & Execution Tasks
1. **Environment Config (`.env.example` & `.env`):**
   ```env
   # Application Configuration
   PROJECT_NAME="COALINTEL"
   ENVIRONMENT="development"
   SECRET_KEY="coalintel-super-secret-jwt-signing-key-change-in-production"
   ALGORITHM="HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES=480

   # Database Configuration
   POSTGRES_USER=coalintel
   POSTGRES_PASSWORD=coalintel_secure_pass
   POSTGRES_DB=coalintel_db
   POSTGRES_HOST=postgres
   POSTGRES_PORT=5432
   DATABASE_URL=postgresql://coalintel:coalintel_secure_pass@postgres:5432/coalintel_db

   # Storage Paths
   UPLOAD_DIR="/storage/uploads"
   CHROMA_DB_DIR="/storage/chroma_db"
   REPORT_DIR="/storage/generated_reports"

   # LLM Provider Abstraction Config
   LLM_PROVIDER="gemini" # Options: "gemini", "openai", "degraded"
   LLM_API_KEY="your-api-key-here"
   LLM_MODEL_NAME="gemini-1.5-flash"
   LLM_TIMEOUT_SECONDS=10.0

   # Retrieval Hyperparameters
   EMBEDDING_MODEL="all-MiniLM-L6-v2"
   RRF_K_CONSTANT=60
   CHUNK_SIZE_TOKENS=500
   CHUNK_OVERLAP_TOKENS=50
   ```

2. **Docker Compose Foundation (`docker-compose.yml`):**
   * Configure 3 containerized services: `postgres` (PostgreSQL 15 image), `backend` (FastAPI Dockerfile), `frontend` (Vite/Node Dockerfile).
   * Persist volumes: `postgres_data`, `/storage/uploads`, `/storage/chroma_db`, `/storage/generated_reports`.
   * Configure internal network bridge: `coalintel_network`.

3. **LLM Provider Abstraction (`llm_provider.py`):**
   * Abstract interface `BaseLLMProvider` with methods `generate_completion(prompt, context)` and fallback to `DegradedProvider` on API timeout ($>10$s) or missing API key.

4. **Repository Initialization:**
   * Create `.gitignore` ignoring `.env`, `node_modules/`, `venv/`, `__pycache__/`, `/storage/uploads/*`, `/storage/chroma_db/*`.
   * Create base setup script `setup.sh` / `setup.ps1` for directory creation.

---

## SECTION 7 — DAY 1: SYSTEM FOUNDATION + DATABASE SCHEMAS

### 7.1 PostgreSQL DDL & ORM Configuration (All 7 Tables)
Implement SQLAlchemy models (`backend/app/models/`) and automatic DDL migration script representing the 7 documented tables:

```sql
-- 1. USERS TABLE
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('Admin', 'Analyst', 'Reviewer', 'Auditor')),
    subsidiary VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. DOCUMENTS TABLE
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA-256 Digest
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(20) NOT NULL CHECK (file_type IN ('PDF', 'DOCX', 'XLSX', 'CSV')),
    file_size_bytes BIGINT NOT NULL,
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    uploaded_by INTEGER REFERENCES users(id),
    status VARCHAR(50) NOT NULL CHECK (status IN ('PENDING', 'PARSING', 'PARSED', 'FAILED')),
    total_pages INTEGER DEFAULT 0,
    fiscal_year VARCHAR(20),
    subsidiary VARCHAR(100),
    error_message TEXT
);

-- 3. EXTRACTED METRICS TABLE
CREATE TABLE extracted_metrics (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    subsidiary VARCHAR(100) NOT NULL,
    mine VARCHAR(150) NOT NULL,
    metric_name VARCHAR(150) NOT NULL,
    raw_value NUMERIC(15, 4) NOT NULL,
    raw_unit VARCHAR(50) NOT NULL,
    normalized_value_mt NUMERIC(15, 4) NOT NULL, -- Normalized to Million Tonnes (MT)
    normalized_unit VARCHAR(20) DEFAULT 'MT',
    fiscal_year VARCHAR(20) NOT NULL,
    page_number INTEGER NOT NULL,
    text_snippet TEXT NOT NULL,
    confidence_score NUMERIC(5, 4) NOT NULL,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. DOCUMENT CHUNKS TABLE
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    embedding_id VARCHAR(100) NOT NULL, -- Vector UUID in ChromaDB
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. DATA CONFLICTS TABLE
CREATE TABLE data_conflicts (
    id SERIAL PRIMARY KEY,
    entity_name VARCHAR(150) NOT NULL,
    metric_name VARCHAR(150) NOT NULL,
    fiscal_year VARCHAR(20) NOT NULL,
    doc_a_id INTEGER NOT NULL REFERENCES documents(id),
    doc_a_value_mt NUMERIC(15, 4) NOT NULL,
    doc_b_id INTEGER NOT NULL REFERENCES documents(id),
    doc_b_value_mt NUMERIC(15, 4) NOT NULL,
    discrepancy_pct NUMERIC(8, 4) NOT NULL, -- Calculated discrepancy > 1%
    status VARCHAR(50) DEFAULT 'UNRESOLVED' CHECK (status IN ('UNRESOLVED', 'RESOLVED', 'IGNORED')),
    resolved_by INTEGER REFERENCES users(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. REPORTS TABLE
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    report_type VARCHAR(100) NOT NULL CHECK (report_type IN ('PARLIAMENTARY_REPLY', 'ANNUAL_SUMMARY', 'SUBSIDIARY_COMPARISON', 'PRODUCTION_AUDIT')),
    generated_by INTEGER NOT NULL REFERENCES users(id),
    fiscal_year VARCHAR(20) NOT NULL,
    subsidiary VARCHAR(100),
    content_json JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'APPROVED', 'EXPORTED')),
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    file_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. AUDIT LOGS TABLE
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id INTEGER,
    details_json JSONB,
    ip_address VARCHAR(45),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- INDEXES FOR RETRIEVAL & PERFORMANCE
CREATE INDEX idx_documents_file_hash ON documents(file_hash);
CREATE INDEX idx_extracted_metrics_search ON extracted_metrics(subsidiary, mine, metric_name, fiscal_year);
CREATE INDEX idx_document_chunks_doc_id ON document_chunks(doc_id);
CREATE INDEX idx_data_conflicts_status ON data_conflicts(status);
```

### 7.2 Core Database Seeding
Create seed script (`backend/app/database_seed.py`) to create initial default users:
* `admin` / `Admin@123` (Role: Admin, Subsidiary: CIL HQ)
* `analyst` / `Analyst@123` (Role: Analyst, Subsidiary: CMPDI)
* `reviewer` / `Reviewer@123` (Role: Reviewer, Subsidiary: ECL)
* `auditor` / `Auditor@123` (Role: Auditor, Subsidiary: Ministry of Coal)

---

## SECTION 8 — DAY 2: FRONTEND FOUNDATION + UI/UX COMPONENT SHELL

### 8.1 Component Architecture & Layout Assembly
Build frontend skeleton matching the 23 screens documented in `UI_UX_DOCUMENTATION.md`:
1. **Design System Tokens (`tailwind.config.js`):**
   * Colors: Primary Deep Navy (`#0F172A`), Coal Dark (`#1E293B`), Accent Amber (`#D97706`), Success Emerald (`#059669`), Warning Orange (`#EA580C`), Error Rose (`#E11D48`).
   * Typography: Inter font family.
2. **App Shell Layout (`frontend/src/components/layout/AppShell.jsx`):**
   * Persistent Sidebar with navigation links: Executive Dashboard, Document Library, Q&A Assistant, Conflict Resolver, Report Wizard, Audit Trail.
   * Top Navigation Header: System status badge, User profile menu, Subsidiary badge, Logout button.
3. **State Management (`AuthContext.jsx`):**
   * Stores JWT bearer token, user role (`Admin`, `Analyst`, `Reviewer`, `Auditor`), user full name, and subsidiary context.
   * Protects private routes (`<ProtectedRoute>`).
4. **Axios API Client (`frontend/src/api/client.js`):**
   * Pre-configured base URL (`http://localhost:8000/api/v1`).
   * Interceptor automatically attaches `Authorization: Bearer <token>` header.
   * Interceptor intercepts HTTP 401 and redirects to `/login`.

---

## SECTION 9 — DAY 3: BACKEND INGESTION & FILE MANAGEMENT APIS

### 9.1 Authentication & File Controller Endpoints
Implement REST routes (`backend/app/api/`):
1. **`POST /api/v1/auth/login`:**
   * Validates credentials against `users` table using bcrypt ($12$ rounds).
   * Generates OAuth2 JWT bearer token with user payload (`sub`, `role`, `subsidiary`, `exp` = 8 hours).
2. **`POST /api/v1/documents/upload`:**
   * Multipart file upload endpoint.
   * Validates MIME type and file extension (`.pdf`, `.docx`, `.xlsx`, `.csv`).
   * Enforces 100MB file size limit.
   * Computes SHA-256 hash of file content. Checks `documents` table for existing `file_hash`. If match found, returns HTTP 409 Conflict with duplicate status.
   * Saves file to `/storage/uploads/{file_hash}_{filename}`.
   * Inserts row in `documents` with status `PENDING`.
   * Triggers async processing task.
3. **`GET /api/v1/documents`:**
   * Returns paginated list of uploaded documents with status filters (`PENDING`, `PARSING`, `PARSED`, `FAILED`).
4. **`GET /api/v1/documents/{id}/pages`:**
   * Returns page breakdown, metadata, and extracted text for document viewing.

---

## SECTION 10 — DAY 4: DOCUMENT EXTRACTION & OCR PIPELINE

### 10.1 Multi-Stage Ingestion Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           DOCUMENT EXTRACTION FLOW                               │
│                                                                                  │
│ [ RAW FILE ] ──> [ PDF / EXT VALIDATOR ] ──> [ PyMuPDF PARSER ]                 │
│                                                     │                            │
│                                                     ▼                            │
│                                          [ TEXT LEN < 100 CHARS? ]               │
│                                            ├── YES ──> [ TESSERACT OCR ]         │
│                                            └── NO  ──> [ DIRECT TEXT ]           │
│                                                             │                    │
│                                                             ▼                    │
│ [ REGEX ENTITY EXTRACTOR ] <────────────────────────────────┘                    │
│        │                                                                         │
│        ▼                                                                         │
│ [ STRUCTURED TUPLE: (Mine, Metric, Raw Value, Unit, Year, Page) ]                 │
│        │                                                                         │
│        ▼                                                                         │
│ [ DETERMINISTIC UNIT NORMALIZER (-> MT) ]                                        │
│        │                                                                         │
│        ▼                                                                         │
│ [ DB PERSISTENCE: `extracted_metrics` & `document_chunks` ]                      │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Implementation Details (`parsing_service.py` & `normalization_service.py`)
1. **PyMuPDF Parsing:**
   * Extracts text, page numbers, and structural bounding boxes per page.
   * If extracted page text is $< 100$ characters, invokes Tesseract OCR (`pytesseract.image_to_string`).
2. **Regex & Entity Parsing Engine:**
   * Scans text snippets for mining entities (Opencast Mine names, Coalfield names, Subsidiary names like ECL, BCCL, CCL, WCL, SECL, NCL, MCL, NEC).
   * Extracts target metrics: Coal Production, Overburden Removal (OBR), Despatch, Washing Capacity, Stripping Ratio.
3. **Deterministic Unit Normalization Engine:**
   * Converts all extracted raw units into Million Tonnes (MT) using explicit Python multipliers:
     * $1 \text{ Lakh Tonnes} \times 0.1 \longrightarrow \text{MT}$
     * $1 \text{ Million Tonnes} \times 1.0 \longrightarrow \text{MT}$
     * $1 \text{ Thousand Tonnes} \times 0.001 \longrightarrow \text{MT}$
     * $1 \text{ Ton} \times 0.000001 \longrightarrow \text{MT}$
     * $1 \text{ Million Cu.M (OBR)} \times 1.0 \longrightarrow \text{M.Cu.M}$
4. **Chunking & Storage:**
   * Splits document text into 500-token chunks with 50-token overlap.
   * Inserts extracted metrics into `extracted_metrics`.
   * Inserts text chunks into `document_chunks`. Updates `documents.status` = `PARSED`.

---

## SECTION 11 — DAY 5: HYBRID VECTOR SEARCH ENGINE & RAG ASSISTANT

### 11.1 Hybrid Retrieval Engine Architecture (`retrieval_service.py`)
Combines dense vector retrieval with sparse keyword search using Reciprocal Rank Fusion (RRF):

```
                       ┌──> [ ChromaDB Cosine Search ] ──────┐
                       │    (SentenceTransformers 384d)      │
[ QUERY: "ECL OBR" ] ──┤                                     ├──> [ RRF FUSION (k=60) ] ──> [ TOP K CONTEXT ]
                       │                                     │
                       └──> [ PG Full-Text Search (BM25) ] ──┘
```

1. **ChromaDB Vector Store (`embedding_service.py`):**
   * Embeds chunks using `SentenceTransformers (all-MiniLM-L6-v2)`.
   * Queries top-20 chunks using Cosine Distance.
2. **PostgreSQL BM25 Full-Text Search:**
   * Queries `document_chunks` using `to_tsquery('english', query)` matching mine names and fiscal years.
3. **Reciprocal Rank Fusion (RRF, $k=60$):**
   * Combines rank position $R(d)$ from vector and BM25 search:
     $$\text{RRF\_Score}(d) = \frac{1}{60 + R_{\text{vector}}(d)} + \frac{1}{60 + R_{\text{bm25}}(d)}$$
   * Ranks documents by $\text{RRF\_Score}$ and extracts top 5 chunks.

### 11.2 Cited Q&A Controller (`POST /api/v1/query/ask`) & Prompt Guard
* **Prompt Isolation:** Embeds retrieved text inside `<untrusted_document_context>` XML tags.
* **System Prompt Constraint:**
  > "You are the COALINTEL Mining Intelligence Assistant. Answer the question STRICTLY using the provided context. Every statement of fact or number MUST be followed by an exact citation tag in the format `[Document_Name.pdf, Page X]`. If the answer cannot be determined from the context, state 'Information not found in ingested documents'."
* **Citation Verification Gate (`citation_service.py`):**
  * Parses LLM output. Verifies that every numeric claim contains a valid citation tag matching retrieved chunks.
  * If citation tag is missing or invalid, modifies output to append verified source metadata.
* **Degraded Mode Fallback:**
  * If LLM API call times out ($>10.0$ seconds) or returns HTTP error, system enters Degraded Mode: returns raw retrieved document snippets with explicit flag `degraded_mode: true`.

---

## SECTION 12 — DAY 6: VALIDATION, CONFLICT ENGINE & REPORT GENERATION

### 12.1 Deterministic Validation Engine (`validation_engine.py`)
1. **Arithmetic Verification:**
   * Sums child mine metrics for a given subsidiary and fiscal year:
     $$\text{Sum\_Mines} = \sum \text{Normalized\_Value\_MT}_{\text{Mine\_i}}$$
   * Compares against extracted subsidiary total.
   * If discrepancy $> 5\%$, logs warning in `validation_feed`.
2. **Cross-Document Conflict Detection Engine:**
   * Queries `extracted_metrics` for identical `(Subsidiary/Mine, Metric_Name, Fiscal_Year)` tuples originating from different document IDs (`doc_a_id`, `doc_b_id`).
   * Calculates percentage discrepancy:
     $$\text{Discrepancy\_Pct} = \frac{|\text{Value\_A} - \text{Value\_B}|}{\min(\text{Value\_A}, \text{Value\_B})} \times 100$$
   * If $\text{Discrepancy\_Pct} > 1.0\%$, inserts a row into `data_conflicts` with status `UNRESOLVED`.

### 12.2 Conflict Resolver Controller (`POST /api/v1/conflicts/{id}/resolve`)
* Requires `Reviewer` or `Admin` role.
* Accepts resolution action (`SELECT_DOC_A`, `SELECT_DOC_B`, `MANUAL_OVERRIDE`), updates `data_conflicts` status to `RESOLVED`, records `resolved_by`, timestamp, and inserts immutable entry in `audit_logs`.

### 12.3 Report Generator Engine (`report_service.py`)
1. **`POST /api/v1/reports/generate`:**
   * Accepts report parameters (`report_type`, `fiscal_year`, `subsidiary`).
   * Pulls verified metrics from `extracted_metrics` and resolved data from `data_conflicts`.
   * Assembles JSON structure containing executive summary, production tables, conflict resolution log, and citation list.
   * Compiles JSON into professional PDF document using ReportLab template. Saves file to `/storage/generated_reports/{report_id}.pdf`.

---

## SECTION 13 — DAY 7: FULL-STACK INTEGRATION & END-TO-END PIPELINES

### 13.1 End-to-End User Flow Integration
Connect all React SPA views with FastAPI controllers:
1. **Login & Session Flow:** `LoginPage.jsx` $\rightarrow$ `POST /api/v1/auth/login` $\rightarrow$ JWT saved in AuthContext $\rightarrow$ Navigation to Dashboard.
2. **Ingestion & Processing Flow:** `DocumentsPage.jsx` Dropzone $\rightarrow$ `POST /api/v1/documents/upload` $\rightarrow$ Ingestion Pipeline $\rightarrow$ Status polling $\rightarrow$ `extracted_metrics` populated.
3. **Dashboard Analytics Flow:** `DashboardPage.jsx` $\rightarrow$ `GET /api/v1/dashboard/kpis` & `charts` & `wordcloud` & `validation/feed` $\rightarrow$ Recharts rendering.
4. **Q&A Assistant Flow:** `QueryAssistantPage.jsx` $\rightarrow$ `POST /api/v1/query/ask` $\rightarrow$ RRF Hybrid Search $\rightarrow$ LLM Generation $\rightarrow$ Citation Gate $\rightarrow$ Interactive cited response with page links.
5. **Conflict Resolution Flow:** `ConflictResolverPage.jsx` $\rightarrow$ `GET /api/v1/validation/feed` $\rightarrow$ Reviewer clicks Resolve $\rightarrow$ `POST /api/v1/conflicts/{id}/resolve` $\rightarrow$ Audit Log entry.
6. **Report Assembly & Export Flow:** `ReportWizardPage.jsx` $\rightarrow$ Select Parliamentary Reply Template $\rightarrow$ `POST /api/v1/reports/generate` $\rightarrow$ ReportLab PDF generation $\rightarrow$ Download PDF preview.

---

## SECTION 14 — DAY 8: TESTING & DEMO HARDENING

### 14.1 Golden Dataset Testing Harness (`tests/test_golden_dataset.py`)
Validate system against the official **Golden Dataset**:
* **Input Data:** 5 curated CIL & CMPDI Annual Reports / RTI disclosures containing scanned tables, 20 complex mining queries, 5 synthetic cross-document numeric conflicts.
* **Automated Evaluation Metrics Targets:**
  * **EAR (Entity Accuracy Rate):** Target $\ge 95\%$ (Correct extraction of Mine, Metric, Raw Unit, Fiscal Year).
  * **CCR (Citation Coverage Rate):** Target $= 100\%$ (Every answer statement contains valid `[Doc, Page]` tag).
  * **DDR (Duplicate Detection Rate):** Target $= 100\%$ (Exact SHA-256 matches blocked with 409 Conflict).
  * **QSR (Query Satisfaction Rate):** Target $\ge 90\%$ (Evaluation against ground-truth answer key).

### 14.2 Empirical Performance Benchmarking (Targets)
* **Dashboard SLA:** $< 1.5$ seconds page load.
* **Query Response SLA:** $< 3.0$ seconds total turnaround.
* **Ingestion Throughput SLA:** $< 45$ seconds for a 20-page document.

---

## SECTION 15 — REST API IMPLEMENTATION SEQUENCE & DEPENDENCIES

Implementation of the 11 REST API endpoints MUST follow this exact dependency sequence:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           API IMPLEMENTATION SEQUENCE                            │
│                                                                                  │
│ [ 1. POST /auth/login ] ───────────> [ 2. POST /documents/upload ]               │
│          │                                        │                              │
│          ▼                                        ▼                              │
│ [ 5. GET /dashboard/kpis ]          [ 3. GET /documents ]                        │
│ [ 6. GET /dashboard/charts ]        [ 4. GET /documents/{id}/pages ]             │
│ [ 8. GET /analytics/wordcloud ]                   │                              │
│          │                                        ▼                              │
│          │                          [ 7. POST /query/ask ]                       │
│          │                                        │                              │
│          ▼                                        ▼                              │
│ [ 9. GET /validation/feed ] ───────> [ 10. POST /conflicts/{id}/resolve ]        │
│                                                   │                              │
│                                                   ▼                              │
│                                     [ 11. POST /reports/generate ]               │
└──────────────────────────────────────────────────────────────────────────────────┘
```

1. **`POST /api/v1/auth/login`** (Prerequisite for all protected routes)
2. **`POST /api/v1/documents/upload`** (Ingest raw documents)
3. **`GET /api/v1/documents`** (List uploaded files and processing statuses)
4. **`GET /api/v1/documents/{id}/pages`** (Fetch page details and text snippets)
5. **`GET /api/v1/dashboard/kpis`** (Fetch aggregate KPI metrics)
6. **`GET /api/v1/dashboard/charts`** (Fetch production time-series chart data)
7. **`POST /api/v1/query/ask`** (Execute cited Q&A via Hybrid RAG)
8. **`GET /api/v1/analytics/wordcloud`** (Fetch TF-IDF topic word cloud data)
9. **`GET /api/v1/validation/feed`** (Fetch cross-document conflicts & arithmetic warnings)
10. **`POST /api/v1/conflicts/{id}/resolve`** (Submit conflict resolution decisions)
11. **`POST /api/v1/reports/generate`** (Assemble and export ReportLab PDF)

---

## SECTION 16 — DATABASE → BACKEND → API → UI TRACEABILITY MATRIX

| Core Feature | DB Tables Involved | Backend Service / Controller | REST API Endpoint | Frontend Component / Screen | Security & Role Guard |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Authentication & RBAC** | `users` | `security.py`, `auth.py` | `POST /api/v1/auth/login` | `LoginPage.jsx` | All roles (`Admin`, `Analyst`, `Reviewer`, `Auditor`) |
| **Document Ingestion** | `documents` | `ingestion_service.py`, `documents.py` | `POST /api/v1/documents/upload` | `DocumentsPage.jsx` Dropzone | Admin, Analyst |
| **Parsing & OCR Pipeline** | `documents`, `extracted_metrics`, `document_chunks` | `parsing_service.py`, `normalization_service.py` | Internal Async Service | `DocumentsPage.jsx` Status Badge | System Internal |
| **Executive Dashboard** | `documents`, `extracted_metrics` | `dashboard.py` | `GET /api/v1/dashboard/kpis`, `/charts` | `DashboardPage.jsx` KPI Cards & Recharts | All Roles |
| **Word Cloud Analytics** | `document_chunks` | `dashboard.py` | `GET /api/v1/analytics/wordcloud` | `DashboardPage.jsx` WordCloud | All Roles |
| **Cited Hybrid RAG Q&A** | `document_chunks`, `documents` | `retrieval_service.py`, `llm_provider.py`, `query.py` | `POST /api/v1/query/ask` | `QueryAssistantPage.jsx` Q&A Box | All Roles |
| **Conflict Detection & Resolver** | `extracted_metrics`, `data_conflicts`, `audit_logs` | `validation_engine.py`, `validation.py` | `GET /validation/feed`, `POST /conflicts/{id}/resolve` | `ConflictResolverPage.jsx` | Reviewer, Admin |
| **Report Generation & Export** | `reports`, `extracted_metrics`, `audit_logs` | `report_service.py`, `reports.py` | `POST /api/v1/reports/generate` | `ReportWizardPage.jsx` | Analyst, Reviewer, Admin |
| **Audit Ledger** | `audit_logs` | `rbac.py` | `GET /api/v1/audit/logs` | `AuditLogsPage.jsx` | Auditor, Admin |

---

## SECTION 17 — SECURITY IMPLEMENTATION CHECKLIST

- [ ] **Password Security:** Hashing using `passlib` with `bcrypt` ($12$ rounds). Zero plaintext passwords stored.
- [ ] **JWT Bearer Token:** Standard OAuth2 HTTP Bearer flow with `PyJWT` HS256 algorithm and $8$-hour expiry (`ACCESS_TOKEN_EXPIRE_MINUTES=480`).
- [ ] **Role-Based Access Control (RBAC):** Custom FastAPI dependency (`RoleChecker(["Admin", "Reviewer"])`) enforcing permission boundaries per route.
- [ ] **Upload Validation:** Strict MIME type and file extension check (`.pdf`, `.docx`, `.xlsx`, `.csv`). Enforce maximum payload size limit of $100\text{MB}$.
- [ ] **Duplicate File Blocking:** Calculate SHA-256 digest on incoming stream prior to file saving; return HTTP 409 Conflict if digest exists in `documents.file_hash`.
- [ ] **Path Traversal Protection:** Sanitize user-provided file names (`werkzeug.utils.secure_filename`). Direct storage to encapsulated docker volume paths `/storage/uploads/{file_hash}_{filename}`.
- [ ] **Prompt Injection Isolation:** Isolate retrieved chunk context inside `<untrusted_document_context>` XML tags within LLM prompt templates.
- [ ] **Audit Trail Integrity:** Append-only database triggers/service calls inserting rows into `audit_logs` for login, document upload, conflict resolution, and report generation events.

---

## SECTION 18 — FILE FORMAT IMPLEMENTATION PRIORITY

To ensure maximum deliverable value under hackathon execution constraints, file format parsing is prioritized as follows:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        FILE FORMAT IMPLEMENTATION PRIORITY                       │
├──────────┬─────────────┬───────────────────────────────┬─────────────────────────┤
│ PRIORITY │ FORMAT      │ PARSER / ENGINE               │ MVP SCOPE               │
├──────────┼─────────────┼───────────────────────────────┼─────────────────────────┤
│ P0       │ Digital PDF │ PyMuPDF (`fitz`)              │ Mandatory Core MVP      │
│ P0       │ Scanned PDF │ Tesseract OCR (`pytesseract`) │ Mandatory Core MVP      │
│ P1       │ DOCX        │ `python-docx`                 │ Secondary Priority      │
│ P1       │ XLSX        │ `openpyxl` / `pandas`         │ Secondary Priority      │
│ P1       │ CSV         │ `pandas`                      │ Secondary Priority      │
└──────────┴─────────────┴───────────────────────────────┴─────────────────────────┘
```

---

## SECTION 19 — PERFORMANCE TARGETS & BENCHMARKING PLAN

> **IMPORTANT:** The following metrics represent **Target SLAs** to be empirically benchmarked and validated during Day 8 testing:

1. **Dashboard Latency:** $\le 1.5$ seconds for full initial page load (`GET /kpis`, `/charts`, `/wordcloud`, `/feed`).
2. **Hybrid RAG Query Latency:** $\le 3.0$ seconds from query submission to cited output rendering (including ChromaDB + BM25 search + RRF + LLM completion).
3. **Ingestion Throughput:** $\le 45$ seconds for parsing, OCR, metric extraction, unit normalization, chunking, and vector indexing of a standard 20-page mining report.

---

## SECTION 20 — TESTING STRATEGY & EVALUATION HARNESS

### 20.1 Test Suite Breakdown
* **Unit Tests (`pytest tests/unit/`):**
  * Test unit normalization engine ($1 \text{ Lakh Tonnes} \rightarrow 0.1 \text{ MT}$).
  * Test SHA-256 hash generator.
  * Test arithmetic sum validator.
  * Test cross-document conflict percentage formula.
* **Integration Tests (`pytest tests/integration/`):**
  * Test FastAPI route responses and status codes.
  * Test JWT authentication and HTTP 401/403 guards.
  * Test PostgreSQL database transaction rollbacks.
* **Evaluation Harness (`pytest tests/test_golden_dataset.py`):**
  * Execute end-to-end processing against Golden Dataset (5 CIL reports, 20 queries, 5 synthetic conflicts).
  * Compute empirical EAR, CCR, DDR, and QSR scores.

---

## SECTION 21 — SYSTEM IMPLEMENTATION DEPENDENCY GRAPH

```
[ Day 0: Environment & Docker Setup ]
                  │
                  ▼
[ Day 1: PostgreSQL DDL & FastAPI Shell ]
                  │
                  ▼
[ Day 2: React SPA & AppShell Layout ] ───┐
                  │                       │
                  ▼                       │
[ Day 3: File Upload & Auth APIs ]        │ (Parallel UI Shell Setup)
                  │                       │
                  ▼                       │
[ Day 4: Parsing & OCR Pipeline ] <───────┘
                  │
                  ▼
[ Day 5: ChromaDB RAG & Q&A Assistant ]
                  │
                  ▼
[ Day 6: Validation, Conflict & Report Engine ]
                  │
                  ▼
[ Day 7: Full-Stack E2E Integration ]
                  │
                  ▼
[ Day 8: Golden Testing & Hardening ]
```

---

## SECTION 22 — DAILY ACCEPTANCE CRITERIA & CHECKPOINTS (DAY 0 – DAY 8)

### Day 0: Environment & Docker Foundation
* **Expected Files:** `.env.example`, `.env`, `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.gitignore`, `README.md`.
* **Acceptance Criteria:** `docker-compose up` builds and starts `frontend`, `backend`, and `postgres` containers cleanly without errors. Healthcheck `/health` returns HTTP 200 OK.

### Day 1: System Foundation + Database Schemas
* **Expected Files:** `backend/app/models/*.py`, `backend/app/database.py`, `backend/app/database_seed.py`.
* **Acceptance Criteria:** Database migration executes successfully. All 7 tables (`users`, `documents`, `extracted_metrics`, `document_chunks`, `data_conflicts`, `reports`, `audit_logs`) created with foreign keys and indexes. Seed script creates default admin/analyst users.

### Day 2: Frontend Foundation + UI/UX Shell
* **Expected Files:** `frontend/src/App.jsx`, `frontend/src/components/layout/*`, `frontend/src/pages/*` (23 screen shells), `AuthContext.jsx`.
* **Acceptance Criteria:** React SPA renders AppShell, Sidebar navigation, Header, and page view placeholders. Route protection redirects unauthenticated users to `/login`.

### Day 3: Backend Ingestion & File Management APIs
* **Expected Files:** `backend/app/api/auth.py`, `backend/app/api/documents.py`, `backend/app/services/ingestion_service.py`.
* **Acceptance Criteria:** Login endpoint returns valid JWT bearer token. Upload endpoint accepts PDF, verifies SHA-256 hash, blocks exact duplicates with HTTP 409, and saves file to `/storage/uploads`.

### Day 4: Document Extraction & OCR Pipeline
* **Expected Files:** `backend/app/services/parsing_service.py`, `backend/app/services/normalization_service.py`.
* **Acceptance Criteria:** PyMuPDF extracts page text; Tesseract OCR triggers automatically for low-text pages. Extracted metrics are normalized to MT and persisted in `extracted_metrics`. Chunks persisted in `document_chunks`.

### Day 5: Hybrid Vector Search Engine & RAG Assistant
* **Expected Files:** `backend/app/services/embedding_service.py`, `backend/app/services/retrieval_service.py`, `backend/app/services/llm_provider.py`, `backend/app/api/query.py`.
* **Acceptance Criteria:** Sentences vectorized in ChromaDB. Query endpoint executes RRF ($k=60$) search across ChromaDB + PG BM25, passes context to LLM in `<untrusted_document_context>` tags, and enforces page citation tags `[Doc, Page]`. Degraded mode works if LLM fails.

### Day 6: Validation, Conflict Engine & Report Generation
* **Expected Files:** `backend/app/services/validation_engine.py`, `backend/app/services/report_service.py`, `backend/app/api/validation.py`, `backend/app/api/reports.py`.
* **Acceptance Criteria:** Cross-document discrepancy $>1\%$ creates unresolved `data_conflicts` row. Resolve API updates conflict status and writes to `audit_logs`. Report generator produces downloadable ReportLab PDF.

### Day 7: Full-Stack Integration
* **Expected Files:** Connected frontend components in `frontend/src/components/*` wired to Axios client calls.
* **Acceptance Criteria:** Complete user journey works seamlessly in browser from login $\rightarrow$ upload document $\rightarrow$ view dashboard KPIs $\rightarrow$ ask cited question $\rightarrow$ resolve conflict $\rightarrow$ generate report.

### Day 8: Testing & Demo Hardening
* **Expected Files:** `backend/tests/test_golden_dataset.py`, `walkthrough.md`.
* **Acceptance Criteria:** Automated test harness passes across Golden Dataset. Verified performance targets benchmarked. System hardened for pitch presentation demo.

---

## SECTION 26 — FINAL IMPLEMENTATION MASTER CHECKLIST

### Day 0 — Infrastructure & Environment
- [ ] Create `.env.example` and `.env` with required application keys.
- [ ] Create `docker-compose.yml` for `frontend`, `backend`, and `postgres`.
- [ ] Initialize repository `.gitignore` and storage directories `/storage/uploads`, `/storage/chroma_db`, `/storage/generated_reports`.
- [ ] Implement `backend/app/services/llm_provider.py` provider abstraction and degraded fallback mode.

### Day 1 — Database & Core Backend
- [ ] Write SQLAlchemy models for all 7 tables (`users`, `documents`, `extracted_metrics`, `document_chunks`, `data_conflicts`, `reports`, `audit_logs`).
- [ ] Execute database DDL migrations and index creation.
- [ ] Execute `database_seed.py` creating default Admin, Analyst, Reviewer, and Auditor user accounts.

### Day 2 — Frontend AppShell & Navigation
- [ ] Initialize React 18 + Vite project with Tailwind CSS configuration.
- [ ] Build `AppShell`, persistent Sidebar, Header, and Footer layout.
- [ ] Implement `AuthContext` and Axios API client with JWT bearer token interceptors.
- [ ] Create 23 screen view placeholder files matching `UI_UX_DOCUMENTATION.md`.

### Day 3 — Ingestion & Auth REST APIs
- [ ] Implement `POST /api/v1/auth/login` endpoint with bcrypt password check and JWT generation.
- [ ] Implement `POST /api/v1/documents/upload` with MIME check, SHA-256 duplicate detection, and file storage.
- [ ] Implement `GET /api/v1/documents` listing and status APIs.

### Day 4 — Extraction, OCR & Normalization Pipeline
- [ ] Implement `parsing_service.py` integrating PyMuPDF text extraction and Tesseract OCR fallback.
- [ ] Implement regex entity extractor for coal mine names, subsidiaries, and target metrics.
- [ ] Implement `normalization_service.py` applying deterministic unit multipliers ($\rightarrow \text{MT}$).
- [ ] Persist normalized records to `extracted_metrics` and 500-token chunks to `document_chunks`.

### Day 5 — ChromaDB Vector Store & Hybrid RAG Engine
- [ ] Implement `embedding_service.py` using `SentenceTransformers (all-MiniLM-L6-v2)`.
- [ ] Implement `retrieval_service.py` performing ChromaDB Cosine + PG BM25 search merged via RRF ($k=60$).
- [ ] Implement `POST /api/v1/query/ask` API with `<untrusted_document_context>` XML prompt isolation and citation verification gate `[Doc, Page]`.

### Day 6 — Validation, Conflict Resolver & Report Engine
- [ ] Implement `validation_engine.py` evaluating sum totals ($>5\%$) and cross-doc discrepancies ($>1\%$).
- [ ] Implement `POST /api/v1/conflicts/{id}/resolve` endpoint with immutable `audit_logs` persistence.
- [ ] Implement `report_service.py` with ReportLab PDF compilation and export API `POST /api/v1/reports/generate`.

### Day 7 — Full-Stack Integration
- [ ] Wire React frontend components to FastAPI REST endpoints across all 23 screens.
- [ ] Test complete user journey end-to-end: Login $\rightarrow$ Ingest $\rightarrow$ Dashboard $\rightarrow$ Q&A $\rightarrow$ Resolve Conflicts $\rightarrow$ Export Report.

### Day 8 — Testing, Hardening & Pitch Preparation
- [ ] Run `pytest tests/test_golden_dataset.py` against 5 CIL reports, 20 queries, and 5 synthetic conflicts.
- [ ] Benchmark empirical SLAs (Dashboard $<1.5$s, Query $<3.0$s, Ingestion $<45$s).
- [ ] Perform demo hardening and prepare pitch walkthrough documentation.
