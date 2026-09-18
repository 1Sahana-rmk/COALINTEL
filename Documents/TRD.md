# COALINTEL TECHNICAL REQUIREMENTS DOCUMENT (TRD)

---

## SECTION 1 — DOCUMENT CONTROL

### 1.1 Document Overview
* **Document Title:** COALINTEL Technical Requirements Document (TRD)
* **Project Name:** COALINTEL (AI-Powered Evidence-Driven Mining Intelligence & Reporting Platform)
* **Problem Statement ID:** SIH26023
* **Problem Statement Title:** AI-Powered Geological, Mining and other Reporting Solution for CMPDI/CIL subsidiaries
* **Sponsoring Organization:** Ministry of Coal
* **Department:** Coal India Limited (CIL) / Central Mine Planning & Design Institute (CMPDI)
* **Category:** Software
* **Theme:** Smart Automation
* **Version:** 1.0.0 (Baseline TRD Release)
* **Status:** Approved / Development Ready
* **Date:** August 27, 2026
* **Author / Ownership:** Lead Systems Architect & Technical Documentation Team
* **Primary Target Engineering Lead:** 1st-Year, 1st-Semester Computer Engineering Student Development Team
* **Development Sprint Window:** 8 Calendar Days (SIH Hackathon Sprint)

### 1.2 Governance & Source Documents
This Technical Requirements Document (TRD) serves as the primary engineering specification for COALINTEL. It is strictly derived from and governed by:
1. **`COALINTEL_MASTER_SPECIFICATION.md`** (Preeminent Single Source of Truth - SSOT)
2. **`PRD.md`** (Product Requirements Document v1.1)
3. **`Research_cum_summary.docx`** (Authoritative Mining & Technical Research context)

In the event of any technical ambiguity, the decisions recorded in this TRD prioritize developer feasibility, implementation simplicity, and system stability within the 8-day hackathon sprint.

---

## SECTION 2 — TECHNICAL OBJECTIVES

1. **Heterogeneous Ingestion:** Ingest and parse `.pdf` (digital and scanned), `.docx`, `.xlsx`, and `.csv` files up to 100MB per file.
2. **OCR & Layout Extraction:** Extract text, headings, layout metadata, and table structures using PyMuPDF and Tesseract OCR 5.0 (300 DPI).
3. **Structured Metric Structuring:** Isolate domain tuples `(Mine, Subsidiary, Period, Metric, Value, Unit)` and store in PostgreSQL.
4. **Deterministic Validation:** Perform unit standardization (converting legacy units to standard **MT**) and arithmetic checks ($\sum \text{Mines} = \text{Subsidiary Total}$).
5. **Cross-Document Conflict Detection:** Automatically query and flag numerical discrepancies across documents for identical `(Mine, Metric, Year)` triplets.
6. **Vector & Metadata Indexing:** Store 500-token text chunks in ChromaDB vector store (`all-MiniLM-L6-v2`) and metadata in PostgreSQL.
7. **Hybrid Search Retrieval:** Execute parallel vector similarity search and PostgreSQL BM25 text search fused via Reciprocal Rank Fusion (RRF).
8. **Evidence-Backed Q&A:** Generate natural language answers with mandatory page/table citation cards `[Doc_Name.pdf, Page X]`.
9. **Dashboard Analytics Feed:** Provide backend REST APIs serving 4-level dashboard analytics (KPI cards, Recharts visualizers, TF-IDF Word Cloud, Conflict Feed).
10. **Automated Report Assembly:** Draft structured institutional reports (Parliamentary Queries, Performance Reviews) using pre-built templates.
11. **Human-in-the-Loop Review:** Provide side-by-side conflict resolution tools and inline draft report editing.
12. **Multi-Format Export & Audit:** Export finalized reports to PDF/DOCX, metric tables to CSV, and log actions to an immutable audit trail.
13. **Modular Monolith Deployment:** Orchestrate frontend, backend, database, and vector index using a single Docker Compose specification.

---

## SECTION 3 — SYSTEM ARCHITECTURE

COALINTEL follows a **Single-Host Modular Monolith Architecture** designed for zero network complexity and high developer velocity.

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       COALINTEL TOPOLOGY DIAGRAM                          │
└───────────────────────────────────────────────────────────────────────────┘

 [ USER BROWSER ] ─── (HTTP / REST APIs on Port 3000) ───► [ REACT + VITE UI ]
                                                                 │
                                                                 ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ FASTAPI BACKEND (Python 3.11 Monolith - Port 8000)                      │
 │ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ │
 │ │ Auth Service  │ │ Ingest Engine │ │ OCR Parser    │ │ Extractor     │ │
 │ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ │
 │ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ │
 │ │ Validator     │ │ Hybrid RAG    │ │ Report Engine │ │ Audit Logger  │ │
 │ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ │
 └─────────┬─────────────────────┬─────────────────────┬───────────────────┘
           │                     │                     │
           ▼                     ▼                     ▼
 ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────────────┐
 │ POSTGRESQL 15     │ │ CHROMADB Persistent│ │ LOCAL STORAGE MOUNT       │
 │ • Relational DB   │ │ • Vector Index    │ │ • /uploads (Raw Files)    │
 │ • Full-Text BM25  │ │ • 384-d MiniLM    │ │ • /exports (PDFs/DOCX)    │
 └───────────────────┘ └───────────────────┘ └───────────────────────────┘
```

---

## SECTION 4 — COMPONENT ARCHITECTURE

### 4.1 Frontend Component Layer
* **React 18 + Vite:** SPA client handling visual rendering, state management, and user interaction.
* **Tailwind CSS + Lucide Icons:** Government dark-mode design system (`#0F172A` Coal Slate, `#10B981` Emerald, `#F59E0B` Warning Amber).
* **Recharts Engine:** Declarative charting library rendering Target vs. Actual Bar Charts, Subsidiary Donut Charts, and Multi-Year Trend Lines.
* **Evidence Drawer Component:** Side-panel displaying page text snippets and PDF page canvas rendering.

### 4.2 Backend Layer (FastAPI)
* **API Gateway & Router:** FastAPI routing handling REST requests, input validation (Pydantic v2), and JWT security verification.
* **Document Processing Subsystem:** PyMuPDF text parser, Tesseract 5.0 OCR wrapper, and OpenPyXL / Pandas table extractor.
* **Validation Subsystem:** Deterministic unit converter, arithmetic checker, and SQL conflict detector.
* **Retrieval & RAG Subsystem:** ChromaDB vector query engine, PostgreSQL BM25 keyword search, RRF reranker, and LLM prompt builder.

### 4.3 Data Storage Layer
* **PostgreSQL 15:** Primary database storing users, document metadata, metric tuples, conflicts, reports, and immutable audit logs.
* **ChromaDB:** Persistent vector store managing 384-dimensional embeddings generated by `SentenceTransformers (all-MiniLM-L6-v2)`.
* **Local Volume Mount:** Persistent directory storing uploaded raw files, extracted page images, and exported PDF/DOCX files.

---

## SECTION 5 — TECHNOLOGY STACK & JUSTIFICATION

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        COALINTEL TECHNOLOGY STACK                         │
├───────────────────┬──────────────────────────────┬────────────────────────┤
│ SUBSYSTEM         │ SELECTION                    │ RATIONALE FOR 8-DAY MVP│
├───────────────────┼──────────────────────────────┼────────────────────────┤
│ Frontend          │ React 18 + Vite + Tailwind   │ Fast HMR, zero SSR overhead, student friendly│
│ UI Icons & Charts │ Lucide React + Recharts      │ Native React integration, dark-mode visualizers│
│ Backend Framework │ Python 3.11 + FastAPI        │ Async performance, automatic Swagger OpenAPI docs│
│ Primary Database  │ PostgreSQL 15                │ Rigid relational schema for metric verification│
│ Vector Store      │ ChromaDB (Local Persistent)  │ Lightweight, zero external infrastructure required│
│ Document Parsing  │ PyMuPDF (fitz) + python-docx │ Fast PDF text & layout extraction      │
│ Spreadsheet Parsing│ Pandas + OpenPyXL           │ Robust tabular grid handling           │
│ OCR Engine        │ Tesseract 5.0 (PyTesseract)  │ Local execution, 300 DPI image OCR     │
│ Embeddings Model  │ SentenceTransformers MiniLM  │ 384-d lightweight CPU embedding model  │
│ AI LLM Integration│ Hosted LLM API / Ollama      │ Fast reasoning, structured JSON output │
│ Containerization  │ Docker Compose               │ Single-command reproducible setup      │
└───────────────────┴──────────────────────────────┴────────────────────────┘
```

---

## SECTION 6 — FRONTEND TECHNICAL ARCHITECTURE

```
frontend/
├── public/
├── src/
│   ├── assets/             # Brand SVGs and static images
│   ├── components/         # Reusable UI components
│   │   ├── common/         # Buttons, Badges, Modal, Spinner
│   │   ├── dashboard/      # KPICards, TargetVsActualChart, ConflictFeed
│   │   ├── document/       # FileDropzone, StatusBadge, DocumentList
│   │   ├── query/          # ChatWindow, CitationBadge, EvidenceDrawer
│   │   └── report/         # TemplateSelector, ReportViewer, InlineEditor
│   ├── context/            # AuthContext, ToastContext
│   ├── hooks/              # useAuth, useDocuments, useQuery, useDashboard
│   ├── layouts/            # MainLayout, Sidebar, Navbar
│   ├── pages/              # LoginPage, DashboardPage, UploadPage, QueryPage, ReportsPage, AuditPage
│   ├── services/           # api.js (Axios instance), authService, docService, queryService
│   ├── types/              # JSDoc type definitions
│   └── utils/              # formatters.js, constants.js
├── index.html
├── package.json
├── tailwind.config.js
└── vite.config.js
```

---

## SECTION 7 — BACKEND ARCHITECTURE (FASTAPI)

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/  # auth.py, documents.py, dashboard.py, query.py, reports.py, audit.py
│   │       └── router.py   # Master API Router v1
│   ├── core/
│   │   ├── config.py       # Pydantic Settings & Env vars
│   │   ├── database.py     # SQLAlchemy Engine & SessionLocal
│   │   └── security.py     # Password hashing & JWT helper functions
│   ├── db/
│   │   ├── base.py         # SQLAlchemy Base
│   │   └── init_db.py      # Database seed & table initialization
│   ├── models/             # SQLAlchemy ORM models
│   ├── schemas/            # Pydantic request/response schemas
│   ├── services/           # Business logic modules
│   │   ├── parsing_service.py   # PyMuPDF & Tesseract OCR pipeline
│   │   ├── extraction_service.py# Domain metric extraction
│   │   ├── validation_service.py# Unit converter & conflict detector
│   │   ├── retrieval_service.py # Hybrid Vector + BM25 search
│   │   ├── rag_service.py       # LLM prompt synthesis & citation gate
│   │   └── report_service.py    # Template generator & PDF builder
│   └── utils/              # File helpers, logging, text cleaners
├── storage/                # Mounted storage directory
│   ├── uploads/
│   └── exports/
├── Dockerfile
├── requirements.txt
└── main.py                 # FastAPI Application Entrypoint
```

---

## SECTION 8 — DATABASE ARCHITECTURE (POSTGRESQL SCHEMAS)

```sql
-- 1. Users Table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('Admin', 'Analyst', 'Reviewer', 'Viewer')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Documents Master Table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA-256
    file_type VARCHAR(20) NOT NULL,
    subsidiary VARCHAR(100),
    fiscal_year VARCHAR(20),
    status VARCHAR(30) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'INDEXED', 'FAILED')),
    uploaded_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Extracted Metrics Table (Core Knowledge Store)
CREATE TABLE extracted_metrics (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER,
    mine_name VARCHAR(100) NOT NULL,
    subsidiary VARCHAR(100),
    metric_name VARCHAR(100) NOT NULL, -- 'Production', 'Dispatch', 'Overburden'
    numeric_value NUMERIC(14, 2) NOT NULL,
    raw_unit VARCHAR(30) NOT NULL,
    standard_value NUMERIC(14, 2) NOT NULL, -- Converted to MT
    standard_unit VARCHAR(10) DEFAULT 'MT',
    fiscal_year VARCHAR(20) NOT NULL,
    confidence_score NUMERIC(4, 3),
    validation_status VARCHAR(30) DEFAULT 'VALIDATED' CHECK (validation_status IN ('VALIDATED', 'WARNING_ARITHMETIC', 'CONFLICT_DETECTED', 'UNVERIFIED')),
    raw_snippet TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Document Chunks Table
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding_id VARCHAR(128)
);

-- 5. Data Conflicts Table
CREATE TABLE data_conflicts (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    mine_name VARCHAR(100) NOT NULL,
    fiscal_year VARCHAR(20) NOT NULL,
    doc_a_id INTEGER REFERENCES documents(id),
    doc_a_value NUMERIC(14, 2),
    doc_b_id INTEGER REFERENCES documents(id),
    doc_b_value NUMERIC(14, 2),
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'RESOLVED', 'IGNORED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Generated Reports Table
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    fiscal_year VARCHAR(20),
    subsidiary VARCHAR(100),
    content_json JSONB NOT NULL,
    approval_status VARCHAR(30) DEFAULT 'DRAFT' CHECK (approval_status IN ('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED')),
    created_by INTEGER REFERENCES users(id),
    approved_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Audit Log Table
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## SECTION 9 — DATABASE RELATIONSHIPS & ER DIAGRAM

```
  ┌─────────────┐            ┌─────────────┐            ┌────────────────┐
  │    users    │1          *│  documents  │1          *│ document_pages │
  ├─────────────┤────────────├─────────────┤────────────├────────────────┤
  │ id (PK)     │            │ id (PK)     │            │ id (PK)        │
  │ username    │            │ uploaded_by │            │ document_id(FK)│
  └─────────────┘            └─────────────┘            └────────────────┘
         │                          │                           │
         │1                         │1                          │1
         ▼*                         ▼*                          ▼*
  ┌─────────────┐            ┌─────────────┐            ┌────────────────┐
  │ audit_logs  │            │extracted_m. │            │document_chunks │
  ├─────────────┤            ├─────────────┤            ├────────────────┤
  │ id (PK)     │            │ id (PK)     │            │ id (PK)        │
  │ user_id(FK) │            │document_id  │            │ document_id(FK)│
  └─────────────┘            └─────────────┘            └────────────────┘
```

---

## SECTION 10 — END-TO-END DOCUMENT INGESTION PIPELINE

```
 ┌──────────┐    ┌────────────┐    ┌─────────────┐    ┌─────────────────┐
 │ FILE     │───>│ HASH CHECK │───>│ PARSER ROUTE│───>│ METRIC EXTRACT  │
 │ UPLOAD   │    │ SHA-256    │    │ PyMuPDF/OCR │    │ Entity Tuples   │
 └──────────┘    └────────────┘    └─────────────┘    └─────────────────┘
                                                               │
 ┌──────────┐    ┌────────────┐    ┌─────────────┐             ▼
 │ READ FOR │<───│ VECTOR DB  │<───│ CHUNKING &  │<─── ┌─────────────────┐
 │ DASHBOARD│    │ ChromaDB   │    │ EMBEDDING   │     │ VALIDATION ENG. │
 └──────────┘    └────────────┘    └─────────────┘     │ Unit & Conflict │
                                                       └─────────────────┘
```

1. **Ingestion & Validation:** Compute SHA-256 hash; store file in `/storage/uploads/`; insert metadata record with status `PROCESSING`.
2. **Text & Table Parsing:** 
   * PyMuPDF extracts text, headings, and visual tables from digital PDFs.
   * Image-only pages trigger Tesseract OCR (300 DPI) to generate text with bounding boxes.
3. **Structured Extraction:** Extract entity tuples `(mine, metric, value, unit, year)` into `extracted_metrics`.
4. **Deterministic Validation:** Convert units to standard **MT**; execute arithmetic checks and cross-document discrepancy queries.
5. **Chunking & Indexing:** Split text into 500-token chunks (50 overlap); generate embeddings via `all-MiniLM-L6-v2`; persist to ChromaDB.
6. **Completion:** Update document status to `INDEXED` and trigger Dashboard UI notification.

---

## SECTION 11 — FILE VALIDATION & ERROR HANDLING

* **Supported Extensions:** `.pdf`, `.docx`, `.xlsx`, `.csv`, `.png`, `.jpg`.
* **File Size Limit:** 100MB per file.
* **Validation Rules:**
  * If file extension is unsupported $\rightarrow$ return HTTP 400 (`UNSUPPORTED_FILE_TYPE`).
  * If SHA-256 hash exists in `documents` $\rightarrow$ return HTTP 409 (`DUPLICATE_DOCUMENT`).
  * If PDF page reading raises Exception $\rightarrow$ set document status to `FAILED`, log error, and surface friendly UI alert.

---

## SECTION 12 — PDF PROCESSING SPECIFICATION

```python
# Conceptual PyMuPDF Extraction Routine
import fitz  # PyMuPDF

def extract_pdf_pages(file_path):
    doc = fitz.open(file_path)
    pages_data = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        # Check if page is scanned image (low text density)
        if len(text.strip()) < 50:
            pix = page.get_pixmap(dpi=300)
            text = run_tesseract_ocr(pix)
        pages_data.append({"page_number": page_num + 1, "text": text})
    return pages_data
```

---

## SECTION 13 — OCR ARCHITECTURE (TESSERACT 5.0)

* **Engine:** Tesseract 5.0 with PyTesseract Python wrapper.
* **Preprocessing Pipeline:** Image converted to grayscale $\rightarrow$ Otsu binarization thresholding $\rightarrow$ Noise removal.
* **Execution Strategy:** Render target page to 300 DPI PNG image byte stream $\rightarrow$ pass to Tesseract engine with `--psm 6` (Assume a single uniform block of text).
* **Confidence Handling:** Calculate mean word confidence. If confidence score $< 50\%$, flag extracted metrics as `UNVERIFIED` and route to Review Queue.

---

## SECTION 14 — DOCX PROCESSING SPECIFICATION

* **Engine:** `python-docx` library.
* **Extraction Strategy:** Iterate over paragraphs preserving heading tags (`Heading 1`, `Heading 2`). Extract tables cell-by-cell into HTML-like JSON matrices: `{"rows": [["Mine", "Target", "Actual"], ["Kusunda", "10.0", "9.8"]]}`.

---

## SECTION 15 — XLSX / CSV SPREADSHEET PROCESSING

* **Engine:** Pandas + OpenPyXL engine.
* **Parsing Routine:**
  1. Inspect sheet headers for target keywords (`Mine`, `Subsidiary`, `Production`, `Year`).
  2. Drop completely empty rows and columns.
  3. Parse row tuples into structured numeric records.
  4. Standardize column header synonyms (`"Coal Prod"`, `"Actual Production"`, `"Qty (MT)"` $\rightarrow$ `"Production"`).

---

## SECTION 16 — DOCUMENT METADATA TAXONOMY

| Metadata Category | Attribute Fields | Source / Origin |
| :--- | :--- | :--- |
| **System Metadata** | `file_hash`, `file_path`, `upload_date`, `status` | Auto-generated by Ingestion Engine |
| **Extracted Metadata**| `subsidiary`, `fiscal_year`, `document_type`, `page_count` | Parsed via Regex & Header Rules |
| **User Metadata** | `department_owner`, `access_level` | Specified by Analyst during upload |

---

## SECTION 17 — STRUCTURED EXTRACTION SCHEMA

Every extracted operational figure is stored as a standardized JSON/SQL record:

```json
{
  "document_id": 42,
  "page_number": 14,
  "mine_name": "Kusunda OCP",
  "subsidiary": "BCCL",
  "metric_name": "Production",
  "raw_value": 142.0,
  "raw_unit": "Lakh Tonnes",
  "standard_value": 14.20,
  "standard_unit": "MT",
  "fiscal_year": "FY2023-24",
  "confidence_score": 0.965,
  "raw_snippet": "Kusunda OCP recorded actual coal production of 142.0 Lakh Tonnes in FY24."
}
```

---

## SECTION 18 — NUMERIC NORMALIZATION ENGINE

### Conversion Rules Table
* $1 \text{ Lakh Tonnes} \times 0.1 \longrightarrow \text{Value in MT}$
* $1 \text{ Million Tonnes} \times 1.0 \longrightarrow \text{Value in MT}$
* $1 \text{ Ton} \times 0.000001 \longrightarrow \text{Value in MT}$
* $1 \text{ Thousand Tonnes} \times 0.001 \longrightarrow \text{Value in MT}$

---

## SECTION 19 — DETERMINISTIC VALIDATION ENGINE

```python
# Conceptual Validation Logic
def validate_metric_tuple(raw_val, unit, expected_sum, mine_values):
    # 1. Standardize Unit
    std_val = convert_to_mt(raw_val, unit)
    
    # 2. Arithmetic Check
    actual_sum = sum(mine_values)
    arithmetic_status = "VALIDATED"
    if abs(actual_sum - std_val) > (0.05 * std_val):
        arithmetic_status = "WARNING_ARITHMETIC"
        
    return std_val, arithmetic_status
```

---

## SECTION 20 — CROSS-DOCUMENT CONFLICT DETECTION ALGORITHM

```sql
-- SQL Query to Detect Numerical Conflicts Across Documents
SELECT 
    mine_name, metric_name, fiscal_year,
    COUNT(DISTINCT standard_value) AS distinct_values,
    ARRAY_AGG(document_id) AS conflicting_doc_ids,
    ARRAY_AGG(standard_value) AS conflicting_values
FROM extracted_metrics
GROUP BY mine_name, metric_name, fiscal_year
HAVING COUNT(DISTINCT standard_value) > 1 
   AND (MAX(standard_value) - MIN(standard_value)) / MAX(standard_value) > 0.01;
```

---

## SECTION 21 — EVIDENCE LINEAGE DATA STRUCTURE

```json
{
  "claim_id": "CLM-104",
  "claim_text": "Kusunda mine produced 14.20 MT in FY2023-24.",
  "source_document": "BCCL_Annual_Report_2024.pdf",
  "document_id": 42,
  "page_number": 14,
  "chunk_id": 1042,
  "table_coordinate": {"row": 4, "col": 2},
  "bounding_box": [120, 340, 480, 390],
  "verification_status": "VALIDATED"
}
```

---

## SECTION 22 — DOCUMENT CHUNKING SPECIFICATION

* **Strategy:** Structure-Aware Section Chunking.
* **Chunk Size:** 500 tokens ($\approx 2000$ characters).
* **Chunk Overlap:** 50 tokens ($\approx 200$ characters).
* **Boundary Rules:** Chunks never split across table boundaries or heading tags. Table rows remain intact within a single chunk containing the parent table title and column headers.

---

## SECTION 23 — EMBEDDINGS ARCHITECTURE

* **Embedding Model:** `SentenceTransformers (all-MiniLM-L6-v2)`.
* **Dimensions:** 384-dimensional dense vectors.
* **Execution:** Runs locally on CPU via PyTorch / ONNX runtime.
* **Batching:** Chunks processed in mini-batches of 32 for memory efficiency.

---

## SECTION 24 — VECTOR DATABASE SPECIFICATION (CHROMADB)

* **Database Engine:** ChromaDB (Local Persistent Storage).
* **Collection Name:** `coalintel_chunks`.
* **Persistence Location:** `/storage/chroma_db/`.
* **Metadata Fields Stored:** `document_id`, `page_number`, `subsidiary`, `fiscal_year`, `mine_name`.
* **Distance Metric:** Cosine Similarity ($1 - \text{cosine\_distance}$).

---

## SECTION 25 — HYBRID RETRIEVAL ENGINE (BM25 + VECTOR)

```
                         ┌──────────────────────┐
                         │   USER SEARCH QUERY  │
                         └──────────────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
      ┌──────────────────────┐            ┌──────────────────────┐
      │  VECTOR RETRIEVAL    │            │  POSTGRES BM25 SEARCH│
      │  (ChromaDB Cosine)   │            │  (Full-Text Index)   │
      └──────────────────────┘            └──────────────────────┘
                  │                                   │
                  └─────────────────┬─────────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ RECIPROCAL RANK      │
                         │ FUSION (RRF RERANK)  │
                         └──────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ TOP-5 EVIDENCE PACK  │
                         └──────────────────────┘
```

---

## SECTION 26 — RAG PIPELINE & CITATION GATE

```
[ User Query ] ──► [ Hybrid Retrieve ] ──► [ Assemble Evidence Pack ] ──► [ Prompt LLM API ]
                                                                                │
[ Render Cited Response ] ◄── [ Citation Gate: Verify Links ] ◄── [ Raw LLM Output ]
```

---

## SECTION 27 — QUERY CLASSIFICATION ROUTER

* **Rule-Based Routing:**
  * Query contains `"compare"` or `"vs"` $\rightarrow$ Route to **Comparison Engine**.
  * Query contains `"trend"` or `"over years"` $\rightarrow$ Route to **Time-Series Analytics Engine**.
  * Query contains `"production"` or `"target"` $\rightarrow$ Route to **SQL Metric Lookup + RAG**.
  * General query $\rightarrow$ Route to **Hybrid RAG Pipeline**.

---

## SECTION 28 — LLM INTEGRATION & PROVIDER ABSTRACTION

```python
# Provider Abstraction Interface
class LLMProvider:
    def generate_answer(self, prompt: str, context: list) -> str:
        raise NotImplementedError

class HostedAPIProvider(LLMProvider):
    # Connects to hosted API endpoint (Gemini / OpenAI API)
    pass

class LocalOllamaProvider(LLMProvider):
    # Connects to local Ollama instance if offline required
    pass
```

---

## SECTION 29 — HALLUCINATION CONTROL & FALLBACK POLICY

* **Strict System Prompt Policy:** *"Answer the question using ONLY the provided evidence pack. If the answer cannot be determined from the evidence, state: 'Insufficient evidence found in uploaded records.'"*
* **Citation Gate:** Post-process generated response. Ensure every claim tag `[Doc, Page]` matches a real retrieved chunk ID. If context similarity $< 0.4$, return fallback response immediately.

---

## SECTION 30 — PROMPT INJECTION SAFEGUARDS

* **Data Isolation:** User documents are wrapped in strict XML boundary tags (`<untrusted_document_context>...</untrusted_document_context>`).
* **System Prompt Barrier:** System instructions instruct LLM to ignore any command or instruction contained within the context block.

---

## SECTION 31 — DASHBOARD DATA ARCHITECTURE (4-LEVEL IA)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    DASHBOARD API RESPONSE STRUCTURE                       │
├───────────────────────────────────────────────────────────────────────────┤
│ LEVEL 1: EXECUTIVE KPIs                                                   │
│ { "total_docs": 124, "target_mt": 650.0, "actual_mt": 642.8, "conflicts": 3}│
│                                                                           │
│ LEVEL 2: ANALYTICS                                                        │
│ { "target_vs_actual": [...], "subsidiary_share": [...] }                  │
│                                                                           │
│ LEVEL 3: INTELLIGENCE                                                     │
│ { "top_topics": ["Overburden", "Drilling", "Safety"], "wordcloud": [...] } │
│                                                                           │
│ LEVEL 4: TRUST & EVIDENCE                                                 │
│ { "active_warnings": [...], "conflict_feed": [...] }                      │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## SECTION 32 — ANALYTICS ENGINE

Backend computes SQL aggregated analytics:
* `SUM(standard_value) GROUP BY subsidiary`
* `SUM(standard_value) GROUP BY fiscal_year`
* `(SUM(actual) - SUM(target)) / SUM(target) * 100` (Variance %)

---

## SECTION 33 — TOPIC IDENTIFICATION PIPELINE

* **Engine:** Scikit-Learn TF-IDF Vectorizer.
* **Pipeline:** Extract document text $\rightarrow$ strip NLTK English stop words + domain stop words (*"coal", "india", "limited", "report", "page"*) $\rightarrow$ calculate top-30 TF-IDF terms $\rightarrow$ return term frequency matrix for Word Cloud rendering.

---

## SECTION 34 — WORD CLOUD DATA SPECIFICATION

```json
[
  {"text": "Overburden", "value": 84, "category": "operations"},
  {"text": "Drilling", "value": 62, "category": "exploration"},
  {"text": "Capex", "value": 45, "category": "finance"},
  {"text": "Environmental Clearence", "value": 38, "category": "compliance"}
]
```

---

## SECTION 35 — REPORT GENERATION ENGINE

1. User selects Report Type (`Parliamentary Query Response`) + Parameters (`Mine: Kusunda`, `Year: FY24`).
2. Engine queries `extracted_metrics` for validated figures.
3. Engine retrieves relevant text context via Hybrid Search.
4. Engine populates JSON report template: `{ "title": "...", "executive_summary": "...", "metrics_table": [...], "citations": [...] }`.
5. Engine converts JSON report structure into formatted PDF/DOCX export artifact.

---

## SECTION 36 — SUPPORTED REPORT TEMPLATES

1. **Parliamentary Query (PQ) Response Draft**
2. **Annual Mine Production & Target Review**
3. **Geological & Exploration Status Briefing**
4. **Subsidiary Performance Comparison Summary**

---

## SECTION 37 — EXPORT ENGINE ARCHITECTURE

* **PDF Export Engine:** `ReportLab` Python library generating structured PDF documents with headers, tables, and page numbers.
* **DOCX Export Engine:** `python-docx` generating editable MS Word documents.
* **CSV Export Engine:** Pandas `.to_csv()` exporting raw tabular metrics.

---

## SECTION 38 — AUTHENTICATION SPECIFICATION

* **Algorithm:** Password hashing via `bcrypt`.
* **Token Standard:** OAuth2 Password Bearer flow with JWT (JSON Web Tokens).
* **Token Payload:** `{"sub": "username", "role": "Analyst", "exp": 1756350000}`.
* **Header:** `Authorization: Bearer <jwt_token>`.

---

## SECTION 39 — ROLE-BASED ACCESS CONTROL (RBAC) MATRIX

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           RBAC PERMISSION MATRIX                          │
├─────────────────────────┬───────────┬──────────────┬───────────┬──────────┤
│ ACTION / RESOURCE       │ ADMIN     │ ANALYST      │ REVIEWER  │ VIEWER   │
├─────────────────────────┼───────────┼──────────────┼───────────┼──────────┤
│ Manage Users            │ ✅ Allowed│ ❌ Denied    │ ❌ Denied │ ❌ Denied│
│ Upload Documents        │ ✅ Allowed│ ✅ Allowed   │ ❌ Denied │ ❌ Denied│
│ View Dashboard Visuals  │ ✅ Allowed│ ✅ Allowed   │ ✅ Allowed│ ✅ Allowed│
│ Execute AI Queries      │ ✅ Allowed│ ✅ Allowed   │ ✅ Allowed│ ✅ Allowed│
│ Generate Draft Reports  │ ✅ Allowed│ ✅ Allowed   │ ✅ Allowed│ ❌ Denied│
│ Approve & Seal Reports  │ ✅ Allowed│ ❌ Denied    │ ✅ Allowed│ ❌ Denied│
│ View Audit Logs         │ ✅ Allowed│ ❌ Denied    │ ❌ Denied │ ❌ Denied│
└─────────────────────────┴───────────┴──────────────┴───────────┴──────────┘
```

---

## SECTION 40 — REST API SPECIFICATION OVERVIEW

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        CORE REST API ENDPOINTS                            │
├──────────────┬──────────────────────────────┬─────────────────────────────┤
│ METHOD       │ ENDPOINT                     │ PURPOSE                     │
├──────────────┼──────────────────────────────┼─────────────────────────────┤
│ POST         │ /api/v1/auth/login           │ User Authentication & JWT   │
│ POST         │ /api/v1/documents/upload     │ Batch Document Ingestion    │
│ GET          │ /api/v1/documents            │ List Ingested Documents     │
│ GET          │ /api/v1/documents/{id}/pages │ View Page Images & OCR Text │
│ GET          │ /api/v1/dashboard/kpis       │ Fetch 4-Level Dashboard Data│
│ POST         │ /api/v1/query/ask            │ Cited Natural Language Q&A  │
│ GET          │ /api/v1/analytics/wordcloud  │ Fetch Word Cloud Term Array │
│ POST         │ /api/v1/reports/generate     │ Assemble Draft Report       │
│ POST         │ /api/v1/reports/{id}/approve │ Reviewer Report Approval    │
│ GET          │ /api/v1/reports/{id}/export  │ Export PDF/DOCX Artifact    │
│ GET          │ /api/v1/audit/logs           │ Retrieve System Audit Logs  │
└──────────────┴──────────────────────────────┴─────────────────────────────┘
```

---

## SECTION 41 — API RESPONSE STANDARD SCHEMA

### Success Response Format (HTTP 200/201)
```json
{
  "success": true,
  "message": "Operation executed successfully",
  "data": {},
  "request_id": "req-94021"
}
```

### Error Response Format (HTTP 400/404/500)
```json
{
  "success": false,
  "error_code": "DOCUMENT_PROCESSING_FAILED",
  "message": "Failed to parse target PDF file due to corruption.",
  "details": null,
  "request_id": "req-94022"
}
```

---

## SECTION 42 — ASYNCHRONOUS JOB PROCESSING

To avoid blocking main HTTP worker threads, document parsing tasks run asynchronously using FastAPI `BackgroundTasks`. The client polls GET `/api/v1/documents` to track status transitions (`PENDING` $\rightarrow$ `PROCESSING` $\rightarrow$ `INDEXED`).

---

## SECTION 43 — GLOBAL ERROR HANDLING POLICY

All unhandled Python exceptions are trapped by a global FastAPI exception handler, logging full stack traces internally while returning sanitized HTTP 500 JSON payloads to the frontend.

---

## SECTION 44 — LOGGING INFRASTRUCTURE

* **Library:** Standard Python `logging` module configured with JSON formatting.
* **Log Levels:** `INFO` for operational tasks, `WARNING` for validation flags, `ERROR` for system failures.
* **Privacy Policy:** API tokens, passwords, and sensitive credentials are sanitized before log output.

---

## SECTION 45 — IMMUTABLE AUDIT TRAIL LOGGING

Every security-sensitive event automatically triggers an entry into `audit_logs`:
`INSERT INTO audit_logs (user_id, action, details, ip_address) VALUES (user_id, 'REPORT_APPROVED', 'Approved Report ID 12', '192.168.1.50');`

---

## SECTION 46 — SECURITY ARCHITECTURE (PROTOTYPE VS PRODUCTION)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                      SECURITY ARCHITECTURE MATRIX                         │
├───────────────────────────────────┬─────────────────────────────────────┤
│ 8-DAY PROTOTYPE SECURITY (IN-SCOPE)│ PRODUCTION GOVT SECURITY (FUTURE)   │
├───────────────────────────────────┼─────────────────────────────────────┤
│ • Password hashing using bcrypt   │ • National Informatics Centre (NIC) │
│ • JWT Token Authentication        │   Single Sign-On (SSO) Integration  │
│ • Role-Based Access Control (RBAC)│ • Hardware Security Module (HSM)    │
│ • Strict File Extension Whitelist │ • Full Enterprise DLP & Antivirus   │
│ • Prompt Injection Barrier Tags   │ • Air-gapped On-Premise Deployment  │
│ • Local File System Encapsulation │ • ISO 27001 & STQC Audit Compliance │
└───────────────────────────────────┴─────────────────────────────────────┘
```

---

## SECTION 47 — FILE STORAGE STRATEGY

* **Directory Topology:** Storage mounted at `/storage/` with subdirectories `/uploads/` and `/exports/`.
* **File Naming Convention:** `/storage/uploads/{file_hash}_{original_filename}`.

---

## SECTION 48 — CONFIGURATION & ENVIRONMENT VARIABLES

```env
# Application Settings
PROJECT_NAME="COALINTEL"
ENV="development"
SECRET_KEY="super-secret-jwt-key-change-in-prod"

# Database Settings
POSTGRES_USER="coalintel_user"
POSTGRES_PASSWORD="coalintel_password"
POSTGRES_DB="coalintel_db"
DATABASE_URL="postgresql://coalintel_user:coalintel_password@postgres:5432/coalintel_db"

# Storage Settings
STORAGE_PATH="/storage"

# AI & LLM Settings
CHROMADB_PATH="/storage/chroma_db"
LLM_API_KEY="your-api-key-here"
```

---

## SECTION 49 — PERFORMANCE TARGETS & BENCHMARKS

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     PERFORMANCE TARGET OBJECTIVES                         │
├───────────────────────────────┬───────────────────┬───────────────────────┤
│ OPERATION                     │ TARGET LATENCY    │ PROCESSING PARADIGM   │
├───────────────────────────────┼───────────────────┼───────────────────────┤
│ Initial Dashboard Render      │ < 1.5 seconds     │ Synchronous REST API  │
│ Document Ingestion & Parse    │ 15 - 45 seconds   │ Asynchronous Task     │
│ Hybrid Search Retrieval       │ < 800 ms          │ Parallel Vector+SQL   │
│ LLM Cited Response Synthesize │ < 3.0 seconds     │ REST API Stream       │
│ Report Generation (5-page)    │ < 4.0 seconds     │ Asynchronous Task     │
└───────────────────────────────┴───────────────────┴───────────────────────┘
```

---

## SECTION 50 — CACHING ARCHITECTURE

* **Strategy:** In-Memory dictionary caching for heavy SQL aggregate queries (`GET /api/v1/dashboard/kpis`) with a 60-second Time-To-Live (TTL). Cache invalidates automatically upon new document upload.

---

## SECTION 51 — SCALABILITY ROADMAP

* **Prototype:** Single-host Docker Compose deployment.
* **Production:** Scale FastAPI workers behind NGINX reverse proxy; migrate ChromaDB to managed vector service; utilize PostgreSQL connection pooling (PgBouncer).

---

## SECTION 52 — DEPLOYMENT ARCHITECTURE (DOCKER COMPOSE)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: coalintel_postgres
    environment:
      POSTGRES_USER: coalintel_user
      POSTGRES_PASSWORD: coalintel_password
      POSTGRES_DB: coalintel_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    container_name: coalintel_backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://coalintel_user:coalintel_password@postgres:5432/coalintel_db
      - STORAGE_PATH=/storage
    volumes:
      - ./storage:/storage
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    container_name: coalintel_frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

---

## SECTION 53 — DEVELOPMENT ENVIRONMENT SETUP

* **Python:** 3.11+
* **Node.js:** 18.0+
* **Database:** PostgreSQL 15.0+
* **Container Tooling:** Docker Desktop with Docker Compose v2.

---

## SECTION 54 — CI/CD & SOURCE CONTROL

* **Git Workflow:** Main branch development for 8-day sprint. Feature branches for backend/frontend separation (`feature/backend-api`, `feature/frontend-ui`).
* **Pre-commit Verification:** Automated linting via `flake8` and `eslint`.

---

## SECTION 55 — TESTING STRATEGY & GOLDEN DATASET

### Golden Dataset Specifications
* **Input Corpus:** 5 curated public CIL/CMPDI reports (2 scanned PDFs, 2 digital PDFs, 1 XLSX spreadsheet).
* **Test Suite:**
  * 20 Factual extraction test cases.
  * 5 Injected numerical conflict test cases.
  * 3 Parliamentary Query report assembly tests.

---

## SECTION 56 — AI EVALUATION FORMULAS

* **Extraction Accuracy Rate ($EAR$):**  
  $$EAR = \left( \frac{\text{Correct Extracted Metrics}}{\text{Total Verified Benchmark Metrics}} \right) \times 100\% \quad [\text{Target: } \ge 95\%]$$
* **Citation Coverage Rate ($CCR$):**  
  $$CCR = \left( \frac{\text{Claims with Valid Citations}}{\text{Total Claims Generated}} \right) \times 100\% \quad [\text{Target: } 100\%]$$
* **Discrepancy Detection Rate ($DDR$):**  
  $$DDR = \left( \frac{\text{Detected Numerical Conflicts}}{\text{Total Injected Conflicts}} \right) \times 100\% \quad [\text{Target: } 100\%]$$

---

## SECTION 57 — DATA QUALITY GOVERNANCE

* **Completeness:** Ensure required metric attributes `(mine, metric, value, unit, year)` are populated.
* **Consistency:** Flag records violating range bounds or cross-document rules.
* **Traceability:** Reject any unverified data entry lacking source file lineage.

---

## SECTION 58 — OBSERVABILITY & SYSTEM HEALTH

Basic health check endpoint `GET /api/v1/health` returning database connection state, disk storage availability, and vector store status.

---

## SECTION 59 — BACKUP & RECOVERY PROCEDURES

Automated script dumping PostgreSQL database state daily: `pg_dump -U coalintel_user coalintel_db > /storage/backups/db_backup.sql`.

---

## SECTION 60 — TECHNICAL FAILURE FALLBACK MATRIX

| System Failure Event | Immediate Technical Fallback Behavior |
| :--- | :--- |
| **OCR Failure on Page** | Log warning, extract raw text stream, flag metric as `UNVERIFIED`. |
| **External LLM API Timeout** | Fall back to returning top hybrid BM25 text chunks directly. |
| **Vector DB Crash** | Fall back to executing SQL full-text search against PostgreSQL. |
| **PDF Generation Error** | Fall back to exporting raw metric tables in CSV format. |

---

## SECTION 61 — THREAT MODEL & MITIGATIONS

* **Prompt Injection:** Wrap context in XML boundary tags; enforce strict system prompt instructions.
* **Unauthorized File Access:** Enforce JWT token verification on `/storage/uploads/` access routes.
* **SQL Injection:** Utilize SQLAlchemy parameterized ORM queries exclusively.

---

## SECTION 62 — DATA PRIVACY & COMPLIANCE

All processing executes locally within the container topology. Zero document contents are transmitted to external third parties beyond authorized LLM API synthesis calls.

---

## SECTION 63 — TECHNICAL TRADE-OFFS & JUSTIFICATIONS

* **React + Vite vs. Next.js:** React + Vite chosen to eliminate SSR complexity and build errors for 1st-year student dev lead.
* **FastAPI vs. Express:** FastAPI chosen for native Python AI library integration (PyMuPDF, SentenceTransformers, Pandas).
* **PostgreSQL vs. MongoDB:** PostgreSQL chosen for rigid schema enforcement required for numeric validation queries.
* **ChromaDB vs. Pinecone:** ChromaDB chosen for zero cost and local persistent volume mounting.

---

## SECTION 64 — EXISTING TECHNOLOGY VS COALINTEL

Commercial tools (Azure Document Intelligence, AWS Textract, UiPath) provide building-block primitives. **COALINTEL** builds the domain integration layer: custom mining metric schemas, unit standardization rules, cross-document conflict detection, page-level evidence tracing, 4-level dashboard visualizers, and institutional report templates.

---

## SECTION 65 — REPOSITORY FOLDER STRUCTURE

```
coalintel/
├── backend/
│   ├── app/
│   ├── storage/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── Dockerfile
│   └── vite.config.js
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## SECTION 66 — DAY-BY-DAY IMPLEMENTATION SCHEDULE

```
┌───────────────────────────────────────────────────────────────────────────┐
│                      8-DAY IMPLEMENTATION TIMELINE                        │
├───────┬──────────────────────────────────┬────────────────────────────────┤
│ DAY   │ FOCUS AREA                       │ DELIVERABLE                    │
├───────┼──────────────────────────────────┼────────────────────────────────┤
│ Day 1 │ System Foundation & Specs        │ DB Migrations & API Boilerplate│
│ Day 2 │ Frontend Shell & Dashboard UI    │ React Dashboard Shell          │
│ Day 3 │ Backend Ingestion & Document APIs│ File Upload & Status APIs      │
│ Day 4 │ Document Parsing & OCR Pipeline  │ PyMuPDF + Tesseract Extractor  │
│ Day 5 │ Hybrid Vector Search Engine      │ ChromaDB RAG Retrieval         │
│ Day 6 │ Validation, Topics & Reports     │ Unit Validator & Report Engine │
│ Day 7 │ Full Stack Integration           │ Connected End-to-End System    │
│ Day 8 │ Golden Testing & Demo Hardening  │ 100% Tested Pitch Demo System  │
└───────┴──────────────────────────────────┴────────────────────────────────┘
```

---

## SECTION 67 — TECHNICAL DEFINITION OF DONE (DoD)

* **Backend DoD:** All API endpoints return valid JSON matching schemas; zero unhandled 500 crashes; DB tables properly indexed.
* **Frontend DoD:** UI renders without console errors; dark mode styling matches specification; responsive on 1920x1080 resolution.
* **Integration DoD:** File upload updates dashboard metrics automatically; query assistant returns cited evidence.

---

## SECTION 68 — MVP TECHNICAL BOUNDARY

* **Core MVP:** PDF upload, PyMuPDF parsing, Tesseract OCR, PostgreSQL persistence, Unit conversion, Conflict detection, 4-Level Dashboard, Evidence Q&A, Citation cards, Basic report generator, PDF export, Audit logging.
* **Secondary MVP:** DOCX/XLSX parsing, TF-IDF Word Cloud, Reviewer queue, DOCX export.
* **Future Scope:** GraphRAG, custom model training, voice UI, NIC SSO.

---

## SECTION 69 — TECHNICAL RISKS & MITIGATION MATRIX

| Technical Risk | Prob. | Impact | Mitigation Strategy | Contingency Plan |
| :--- | :---: | :---: | :--- | :--- |
| **OCR Quality on Bad Scans** | Med | High | Image thresholding preprocessing | Manual inline edit in Review Queue |
| **LLM API Timeout** | Low | High | Retry logic & streaming responses | Cached API response fallback |
| **Table Flattening** | Med | Med | Visual bounding-box detection | Surface source page image preview |
| **Student Integration Block**| Med | Med | Clear Pydantic API contracts | Systems Architect assists wiring |

---

## SECTION 70 — FINAL TECHNICAL ARCHITECTURE DIAGRAM

```
┌───────────────────────────────────────────────────────────────────────────┐
│                      FINAL SYSTEM ARCHITECTURE                            │
└───────────────────────────────────────────────────────────────────────────┘

  [ REACT FRONTEND ] ──► [ FASTAPI API GATEWAY ] ──► [ AUTH / AUDIT MODULE ]
                                  │
                                  ├─► [ INGESTION & PARSER (PyMuPDF / OCR) ]
                                  │
                                  ├─► [ METRIC EXTRACTOR & VALIDATOR ]
                                  │         │
                                  │         ▼
                                  │   [ POSTGRESQL DB ]
                                  │
                                  ├─► [ HYBRID RETRIEVAL (ChromaDB + BM25) ]
                                  │         │
                                  │         ▼
                                  │   [ LLM API + CITATION GATE ]
                                  │
                                  └─► [ REPORT ENGINE & EXPORTER (PDF/DOCX) ]
```

---

## SECTION 71 — FINAL DATA FLOW PIPELINE

$$\text{UPLOAD} \rightarrow \text{HASH} \rightarrow \text{PARSE} \rightarrow \text{OCR} \rightarrow \text{EXTRACT} \rightarrow \text{NORMALIZE} \rightarrow \text{VALIDATE} \rightarrow \text{INDEX} \rightarrow \text{SEARCH} \rightarrow \text{RERANK} \rightarrow \text{SYNTHESIZE} \rightarrow \text{CITE} \rightarrow \text{REPORT} \rightarrow \text{EXPORT}$$

---

## SECTION 72 — ARCHITECTURAL DECISION RECORDS (ADRs)

* **ADR-001:** Adopt Single-Host Modular Monolith over microservices.
* **ADR-002:** Use PostgreSQL as primary database and ChromaDB for vector index.
* **ADR-003:** Select React + Vite for high-velocity frontend development.
* **ADR-004:** Implement hybrid search (BM25 + Vector) with RRF reranking.
* **ADR-005:** Utilize deterministic unit standardization for numeric metrics.
* **ADR-006:** Enforce citation gate verification on generated text.
* **ADR-007:** Use Docker Compose for single-command deployment.

---

## SECTION 73 — TECHNICAL ASSUMPTIONS REGISTER

* **ASM-001:** Public CIL annual reports represent actual production document structures.
* **ASM-002:** Internet connectivity is available during hackathon demo for LLM API calls.
* **ASM-003:** 1st-year student developer is familiar with basic Python and React concepts.

---

## SECTION 74 — OPEN TECHNICAL QUESTIONS

1. **OQ-001:** Will hackathon venue internet permit outbound LLM API traffic? *(Mitigation: Local Ollama fallback prepared).*
2. **OQ-002:** Are sample XLSX production logs available in standard layouts? *(Mitigation: Flexible header matching implemented).*

---

## SECTION 75 — FINAL QUALITY AUDIT & SIGN-OFF

* [x] Technical requirements fully consistent with PRD v1.1 and Master Specification SSOT.
* [x] Modular Monolith architecture realistic for 8-day 1st-year student development sprint.
* [x] PostgreSQL schemas, ChromaDB specs, and FastAPI endpoints fully detailed.
* [x] Fallback mechanisms defined for OCR, LLM timeout, and Vector DB failure.
* [x] Single-command Docker Compose specification verified.

**Systems Architecture Sign-off:** *Approved for Engineering Handoff.*
