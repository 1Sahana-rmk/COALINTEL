# COALINTEL — Production Environment Variables Matrix

This document provides a comprehensive inventory of all environment variables required for deploying the COALINTEL platform to cloud services (Render Backend + Vercel Frontend + Supabase PostgreSQL).

## Environment Variable Matrix

| Variable Name | Component | Required? | Is Secret? | Local Default | Production Source / Value Example | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| `DATABASE_URL` | Backend | **YES** | **YES** | `postgresql://coalintel:...@localhost:5432/coalintel_db` | Supabase Dashboard → Settings → Database → Connection String | Production PostgreSQL connection URI (Direct port 5432 or Pooler port 6543) |
| `SECRET_KEY` | Backend | **YES** | **YES** | `coalintel-super-secret...` | Generated 64-character random string | Secret key for signing JWT authentication tokens |
| `LLM_PROVIDER` | Backend | **YES** | NO | `gemini` | `gemini` (or `openai` / `degraded`) | LLM provider abstraction choice |
| `LLM_API_KEY` | Backend | **YES** | **YES** | `your-api-key-here` | Google AI Studio / OpenAI Dashboard | API Key for evidence-grounded RAG & LLM processing |
| `LLM_MODEL_NAME` | Backend | NO | NO | `gemini-1.5-flash` | `gemini-1.5-flash` | LLM model identifier |
| `ENVIRONMENT` | Backend | **YES** | NO | `development` | `production` | Enables production security & fail-fast database checks |
| `DEBUG` | Backend | NO | NO | `True` | `False` | Disables verbose debug logging in production |
| `FRONTEND_URL` | Backend | **YES** | NO | `http://localhost:3000` | `https://<your-vercel-app>.vercel.app` | Production frontend origin for CORS policies |
| `ALLOWED_ORIGINS` | Backend | NO | NO | (computed) | `https://<your-vercel-app>.vercel.app` | Comma-separated list of allowed CORS origin URLs |
| `PORT` | Backend | NO | NO | `8000` | Set automatically by Render / Cloud Host | Dynamic HTTP port for Uvicorn ASGI server |
| `UPLOAD_DIR` | Backend | NO | NO | `./storage/uploads` | `/var/data/storage/uploads` (or mounted volume) | Directory path for stored uploaded documents |
| `CHROMA_DB_DIR` | Backend | NO | NO | `./storage/chroma_db` | `/var/data/storage/chroma_db` (or mounted volume) | Persistent directory path for ChromaDB vector index |
| `REPORT_DIR` | Backend | NO | NO | `./storage/reports` | `/var/data/storage/reports` (or mounted volume) | Directory path for generated PDF reports |
| `VITE_API_BASE_URL` | Frontend | **YES** | NO | `/api/v1` | `https://<your-render-backend>.onrender.com/api/v1` | Base URL for API requests sent from React client |

---

## Security Guidelines for Environment Variables
1. **Never Commit Secrets**: Secrets (`DATABASE_URL`, `SECRET_KEY`, `LLM_API_KEY`) MUST ONLY be entered in cloud provider dashboards (Render / Vercel / Supabase).
2. **Vite Public Prefix**: `VITE_API_BASE_URL` is bundled into client-side JS. It MUST NOT contain any secret keys.
3. **CORS Alignment**: `FRONTEND_URL` on Render must match your exact Vercel deployment domain (e.g. `https://coalintel.vercel.app`).
