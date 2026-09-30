# COALINTEL — Production Cloud Deployment Guide

This runbook provides a step-by-step guide to deploying the COALINTEL platform to production using **Supabase** (PostgreSQL Database), **Render** (FastAPI Backend Container), and **Vercel** (React Frontend).

---

## Architecture Overview

```text
               ┌──────────────────────────┐
               │          VERCEL          │
               │   React + Vite Frontend  │
               └────────────┬─────────────┘
                            │ HTTPS API Calls
                            ▼
               ┌──────────────────────────┐
               │     RENDER WEB HOST      │
               │       FastAPI API        │
               │   (Docker / PyMuPDF)     │
               └────────────┬─────────────┘
                            │
            ┌───────────────┴────────────────┐
            │                                │
            ▼                                ▼
  ┌────────────────────┐          ┌────────────────────┐
  │      SUPABASE      │          │ PERSISTENT STORAGE │
  │     PostgreSQL     │          │ Uploads / Reports  │
  │     Database       │          │ / ChromaDB Index   │
  └────────────────────┘          └────────────────────┘
```

---

## 15-Step Production Deployment Sequence

### STEP 1 — Prepare Supabase PostgreSQL Database
1. Log in to [Supabase Console](https://supabase.com/dashboard).
2. Create a new project named `coalintel-prod`.
3. Under **Project Settings** → **Database**, locate your connection strings:
   - **Direct Connection (Port 5432)**: `postgresql://postgres.[PROJECT_REF]:[YOUR_PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres`
   - **Transaction Pooler (Port 6543)**: `postgresql://postgres.[PROJECT_REF]:[YOUR_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
4. Copy your PostgreSQL connection string for Step 4.

### STEP 2 — Deploy Backend Web Service on Render
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Connect your GitHub repository `https://github.com/HenilLol/coalintel.git`.
4. Select **Docker** environment (Render will automatically detect `render.yaml` or `backend/Dockerfile`).
5. Set Root Directory to `backend` (or leave empty if using `render.yaml`).

### STEP 3 — Configure Backend Environment Variables
In the Render Web Service Environment settings, configure:
- `ENVIRONMENT`: `production`
- `DEBUG`: `false`
- `DATABASE_URL`: `<YOUR_SUPABASE_POSTGRESQL_CONNECTION_STRING>`
- `SECRET_KEY`: `<GENERATE_RANDOM_64_CHAR_STRING>`
- `LLM_PROVIDER`: `gemini`
- `LLM_API_KEY`: `<YOUR_GEMINI_API_KEY>`
- `LLM_MODEL_NAME`: `gemini-1.5-flash`
- `FRONTEND_URL`: `https://coalintel.vercel.app` *(update after Step 6)*

### STEP 4 — Trigger Database Initialization & Table Creation
1. Once the Render service deploys, FastAPI startup lifespan automatically runs `Base.metadata.create_all(bind=engine)`.
2. All 7 COALINTEL PostgreSQL tables (`users`, `documents`, `document_chunks`, `extracted_metrics`, `data_conflicts`, `reports`, `audit_logs`) will be created automatically.

### STEP 5 — Perform Backend Health Check
Open your browser or run:
```bash
curl -f https://<YOUR_RENDER_BACKEND>.onrender.com/api/v1/health
```
Verify the JSON response returns `"status": "healthy"`.

### STEP 6 — Deploy Frontend on Vercel
1. Log in to [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** → **Project**.
3. Import GitHub repository `HenilLol/coalintel`.
4. Set **Framework Preset**: `Vite`.
5. Set **Root Directory**: `frontend`.

### STEP 7 — Configure Frontend Environment Variable
In Vercel Project Settings → Environment Variables, add:
- `VITE_API_BASE_URL`: `https://<YOUR_RENDER_BACKEND>.onrender.com/api/v1`

### STEP 8 — Align Production CORS
Go back to your **Render Backend Dashboard** → **Environment Variables** and update `FRONTEND_URL` to match your exact Vercel URL:
```text
FRONTEND_URL = https://<YOUR_VERCEL_APP>.vercel.app
```
Re-deploy Render service to apply CORS origin updates.

### STEP 9 — Production Login Verification
1. Open `https://<YOUR_VERCEL_APP>.vercel.app`.
2. Log in using seeded default credentials or newly registered user credentials.
3. Verify JWT token authentication succeeds.

### STEP 10 — Document Upload Smoke Test
1. Navigate to **Documents** page.
2. Upload a sample annual report PDF or mining metrics spreadsheet.
3. Verify status transitions from `PENDING` → `PROCESSING` → `INDEXED`.

### STEP 11 — Evidence-Grounded RAG Query Test
1. Navigate to **Query Assistant** page.
2. Ask: `"What was the raw coal production for ECL in FY 2023-24?"`.
3. Confirm response returns evidence-grounded answer with source citations.

### STEP 12 — Validation & Conflict Detection Test
1. Navigate to **Data Validation** / **Conflict Resolver** page.
2. Verify extracted metrics and cross-document conflict calculations display correctly.

### STEP 13 — Report Generation Test
1. Navigate to **Report Wizard** page.
2. Generate an **Annual Summary Report**.
3. Verify report generation and PDF preview functions cleanly.

### STEP 14 — Final Smoke Test & Audit Log Check
1. Navigate to **Audit Logs** page.
2. Confirm all test actions are recorded in system audit logs.

### STEP 15 — Final Production Sign-Off
Verify that working tree remains clean and production services are operating reliably.
