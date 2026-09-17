# COALINTEL — AI-Powered Evidence-Driven Mining Intelligence & Reporting Platform

> **Problem Statement ID:** SIH26023  
> **Problem Statement Title:** AI-Powered Geological, Mining and other Reporting Solution for CMPDI/CIL subsidiaries  
> **Sponsoring Organization:** Ministry of Coal | Department: Coal India Limited (CIL) / Central Mine Planning & Design Institute (CMPDI)  

---

## 1. Executive Summary
**COALINTEL** is a unified, auditable mining intelligence platform designed to eliminate document fragmentation, manual transcription errors, and prolonged inquiry turnaround times across CIL subsidiaries and CMPDI. It integrates multi-format document ingestion (scanned/digital PDFs, DOCX, XLSX, CSV), deterministic metric extraction and unit normalization, automated cross-document conflict detection, cited hybrid RAG Q&A search, and template-driven official report assembly.

---

## 2. Architecture & Technology Stack
COALINTEL is engineered as a containerized **Modular Monolith**:

* **Frontend:** React 18, Vite, Tailwind CSS, Recharts, Lucide Icons
* **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0 ORM, Pydantic v2, PyMuPDF, Tesseract OCR
* **Database:** PostgreSQL 15 (Relational Store + Full-Text BM25 Search)
* **Vector Store & RAG:** ChromaDB (`all-MiniLM-L6-v2`, 384d), Reciprocal Rank Fusion (RRF $k=60$)
* **Reporting:** ReportLab PDF compilation engine
* **Containerization:** Docker Compose (`frontend`, `backend`, `postgres`)

---

## 3. Directory Layout
```text
COALINTEL/
├── Documents/                           # Frozen Engineering Specification (SSOT)
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
│   └── COALINTEL_IMPLEMENTATION_MASTER_PLAN.md
├── backend/                             # FastAPI Python 3.11 Application
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   └── app/
│       ├── api/
│       ├── core/
│       ├── models/
│       ├── schemas/
│       └── services/
│           └── llm_provider.py          # LLM Provider Abstraction & Degraded Fallback
├── frontend/                            # React 18 + Vite SPA Application
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── src/
├── storage/                             # Persistent Volume Storage Mounts
│   ├── uploads/
│   ├── reports/
│   └── chroma_db/
├── docker-compose.yml                   # Docker Multi-Container Orchestration
├── .env.example                         # Environment Variables Template
├── .gitignore                           # Repository Ignore Rules
└── README.md                            # System Guide
```

---

## 4. Quick Start & Local Execution

### Prerequisites
* Docker & Docker Compose
* Python 3.11+ (for local host backend running)
* Node.js 18+ (for local host frontend running)

### Running with Docker Compose
```bash
# 1. Clone repository & copy environment configuration
cp .env.example .env

# 2. Build and launch all services
docker-compose up --build -d

# 3. Access Services:
# - Frontend SPA: http://localhost:3000
# - Backend API: http://localhost:8000
# - Interactive API Docs: http://localhost:8000/api/v1/docs
```

---

## 5. Development Roadmap
* **Day 0:** Project Foundation & Environment Configuration (COMPLETE)
* **Day 1:** System Foundation & Database Schemas (DDL & ORM)
* **Day 2:** Frontend React Shell & Layout Component Sprint
* **Day 3:** Backend Ingestion & File Management APIs
* **Day 4:** Document Extraction & OCR Pipeline
* **Day 5:** Hybrid Vector Search Engine & Cited RAG Assistant
* **Day 6:** Validation Engine, Conflict Resolver & Report Engine
* **Day 7:** Full-Stack End-to-End Integration
* **Day 8:** Golden Dataset Testing & Pitch Hardening
