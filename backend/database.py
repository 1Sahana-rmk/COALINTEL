import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import build_database_url, settings

logger = logging.getLogger("COALINTEL-DATABASE")

db_url = build_database_url(settings).strip()

# Standardize postgres:// to postgresql:// for SQLAlchemy compatibility (e.g. Supabase connection URIs)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

configured_is_postgres = db_url.startswith("postgresql://")
is_postgres = configured_is_postgres
is_production = settings.ENVIRONMENT.lower() == "production"


def _database_target_log_fields(url: str) -> dict:
    """Return safe, credential-free connection fields for startup logging."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return {
        "scheme": parsed.scheme,
        "host": parsed.hostname or "",
        "port": parsed.port or "",
        "database": parsed.path.lstrip("/"),
        "user": parsed.username or "",
    }


target_fields = _database_target_log_fields(db_url)
logger.info(
    "Database target configured: scheme=%s host=%s port=%s database=%s user=%s",
    target_fields["scheme"], target_fields["host"], target_fields["port"],
    target_fields["database"], target_fields["user"],
)

try:
    if configured_is_postgres:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
    else:
        # Explicit SQLite URL or local fallback
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
            echo=False
        )

    # Test connection
    with engine.connect() as conn:
        logger.info("Database connection verified successfully (%s).", "PostgreSQL" if is_postgres else "SQLite")

except Exception as e:
    # If explicitly in production or user specified a non-localhost PostgreSQL, FAIL FAST
    if is_production or (configured_is_postgres and "localhost" not in db_url and "127.0.0.1" not in db_url):
        logger.error("CRITICAL: Failed to connect to configured production database (%s).", e.__class__.__name__)
        raise RuntimeError(
            "Production database connection failure. Could not connect to the configured database."
        ) from e

    # Development mode fallback to local SQLite when local PostgreSQL is not running
    logger.warning("PostgreSQL connection unavailable (%s). Falling back to local SQLite for development.", e.__class__.__name__)
    project_root = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(project_root) == "backend":
        project_root = os.path.dirname(project_root)
    db_file = os.path.join(project_root, "storage", "coalintel_db.sqlite")
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    sqlite_url = f"sqlite:///{db_file}"
    is_postgres = False
    engine = create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False},
        echo=False
    )
    logger.info("Database connection active (SQLite development fallback).")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
