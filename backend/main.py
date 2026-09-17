import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("COALINTEL")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup & shutdown lifespan events.
    Verifies storage directory structures and initializes PostgreSQL tables on startup.
    """
    logger.info("Initializing COALINTEL Backend Foundation...")
    
    # Ensure local storage directories exist
    for storage_path in [settings.UPLOAD_DIR, settings.CHROMA_DB_DIR, settings.REPORT_DIR]:
        os.makedirs(storage_path, exist_ok=True)
        logger.info(f"Storage path verified: {storage_path}")

    # Initialize PostgreSQL Tables (Day 1 Persistence Foundation)
    try:
        from database import engine, Base
        import app.models  # Registers all 7 models with Base metadata
        Base.metadata.create_all(bind=engine)
        logger.info("PostgreSQL database tables verified and created successfully.")

        # Read-Only Database Schema Compatibility Check (Phase 9C & Phase 11 Production Hardening)
        # Note: Startup MUST NOT execute DDL or mutate existing database schemas.
        try:
            from sqlalchemy import inspect
            inspector = inspect(engine)
            existing_tables = set(inspector.get_table_names())
            if "extracted_metrics" in existing_tables:
                existing_cols = {c["name"] for c in inspector.get_columns("extracted_metrics")}
                if "data_origin" not in existing_cols:
                    logger.warning(
                        "DATABASE COMPATIBILITY NOTICE: 'data_origin' column is missing from 'extracted_metrics' table. "
                        "The application will operate in backward-compatibility mode. To reconcile production database schema, "
                        "execute backend/migrations/001_add_data_origin_to_extracted_metrics.sql via authorized DBA workflow."
                    )
                else:
                    logger.info("Schema compatibility verified: 'extracted_metrics.data_origin' column is present.")

            # Phase 11: Check mine_master and data_sources columns
            if "mine_master" in existing_tables:
                mine_cols = {c["name"] for c in inspector.get_columns("mine_master")}
                missing_mine_cols = {"parent_company", "block", "coalfield", "sector", "captive_or_commercial", "financial_year", "source_chapter", "retrieved_at", "verification_status", "data_origin"} - mine_cols
                if missing_mine_cols:
                    logger.warning(
                        f"DATABASE COMPATIBILITY NOTICE: Columns {missing_mine_cols} missing from 'mine_master' table. "
                        "Execute backend/migrations/002_add_missing_mine_master_and_provenance_columns.sql via authorized DBA workflow."
                    )
                else:
                    logger.info("Schema compatibility verified: 'mine_master' columns are complete.")

            if "data_sources" in existing_tables:
                ds_cols = {c["name"] for c in inspector.get_columns("data_sources")}
                if "chapter" not in ds_cols:
                    logger.warning(
                        "DATABASE COMPATIBILITY NOTICE: 'chapter' column is missing from 'data_sources' table. "
                        "Execute backend/migrations/002_add_missing_mine_master_and_provenance_columns.sql via authorized DBA workflow."
                    )
                else:
                    logger.info("Schema compatibility verified: 'data_sources' columns are complete.")
        except Exception as schema_check_err:
            logger.warning(f"Schema compatibility check note: {schema_check_err}")

        # Idempotent default users bootstrap & Stale processing recovery
        from database import SessionLocal
        from app.models.user import User
        from database_seed import seed_default_users
        from app.services.processing_pipeline import recover_stale_processing_documents

        db_bootstrap = SessionLocal()
        try:
            user_count = db_bootstrap.query(User).count()
            if user_count == 0:
                logger.info("No users found; bootstrapping default users.")
                seed_default_users(db_bootstrap)
                logger.info("Default users bootstrapped successfully.")
            else:
                logger.info("Existing users detected; skipping user bootstrap.")

            # Recover any orphaned processing documents from prior crashes/restarts
            recover_stale_processing_documents(db_bootstrap, stale_minutes=15)

            # Idempotent Government of India Mine Master bootstrap
            try:
                from app.models.mine import MineMaster
                from data.government_mine_data_seed import run_seed as seed_government_data

                # Check column presence before querying MineMaster to prevent UndefinedColumn crash
                inspector = inspect(engine)
                mine_cols = {c["name"] for c in inspector.get_columns("mine_master")} if "mine_master" in inspector.get_table_names() else set()
                if "parent_company" in mine_cols or not mine_cols:
                    mine_count = db_bootstrap.query(MineMaster).count()
                    if mine_count == 0:
                        logger.info("No canonical mines detected; bootstrapping authentic Government data.")
                        seed_government_data(db_bootstrap)
                        logger.info("Government of India mine data bootstrapped successfully.")
                    else:
                        logger.info(f"Existing canonical mines detected ({mine_count} mines); skipping government data seed.")
                else:
                    logger.warning(
                        "DATABASE COMPATIBILITY NOTICE: 'mine_master' table is missing required columns. "
                        "Skipping startup seed until migration 002 is applied."
                    )
            except Exception as seed_err:
                db_bootstrap.rollback()
                logger.error(
                    f"GOVERNMENT DATA BOOTSTRAP FAILED during application startup: {type(seed_err).__name__}: {seed_err}",
                    exc_info=True
                )
        except Exception as startup_err:
            db_bootstrap.rollback()
            logger.error(f"Error during startup bootstrap / recovery: {startup_err}")
        finally:
            db_bootstrap.close()
    except Exception as e:
        logger.warning(f"PostgreSQL connection note during startup: {e}")

    logger.info(f"COALINTEL Backend initialized successfully in {settings.ENVIRONMENT} mode.")
    yield
    logger.info("COALINTEL Backend shut down cleanly.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Powered Evidence-Driven Mining Intelligence & Reporting Platform (SIH26023)",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Configure CORS Middleware
origins_list = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
if settings.FRONTEND_URL and settings.FRONTEND_URL not in origins_list:
    origins_list.append(settings.FRONTEND_URL.strip())
if settings.ENVIRONMENT.lower() != "production":
    for dev_origin in ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"]:
        if dev_origin not in origins_list:
            origins_list.append(dev_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Routers
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.query import router as query_router
from app.api.validation import router as validation_router
from app.api.reports import router as reports_router
from app.api.dashboard import router as dashboard_router
from app.api.analytics import router as analytics_router
from app.api.audit import router as audit_router
from app.api.comparison import router as comparison_router
from app.api.parliamentary import router as parliamentary_router
from app.api.mines import router as mines_router

app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(query_router, prefix=settings.API_V1_STR)
app.include_router(validation_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(comparison_router, prefix=settings.API_V1_STR)
app.include_router(parliamentary_router, prefix=settings.API_V1_STR)
app.include_router(mines_router, prefix=settings.API_V1_STR)


@app.get("/", status_code=status.HTTP_200_OK, tags=["Root"])
async def root_landing():
    """Root Landing Endpoint providing API Metadata and navigation links."""
    return {
        "project": settings.PROJECT_NAME,
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health"
    }


@app.get("/docs", include_in_schema=False)
async def redirect_docs():
    """Redirect /docs to /api/v1/docs."""
    return RedirectResponse(url=f"{settings.API_V1_STR}/docs")


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """System Health Check Endpoint."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=(settings.ENVIRONMENT.lower() != "production"))
