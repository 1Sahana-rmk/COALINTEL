import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

logger = logging.getLogger("COALINTEL-DATABASE")

db_url = settings.DATABASE_URL.strip()

# Standardize postgres:// to postgresql:// for SQLAlchemy compatibility (e.g. Supabase connection URIs)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

is_postgres = db_url.startswith("postgresql://")
is_production = settings.ENVIRONMENT.lower() == "production"

try:
    if is_postgres:
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
        logger.info(f"Database connection verified successfully ({'PostgreSQL' if is_postgres else 'SQLite'}).")

except Exception as e:
    # If explicitly in production or user specified a non-localhost PostgreSQL, FAIL FAST
    if is_production or (is_postgres and "localhost" not in db_url and "127.0.0.1" not in db_url):
        logger.error(f"CRITICAL: Failed to connect to production database: {e}")
        raise RuntimeError(
            f"Production database connection failure. Could not connect to target database: {e}"
        ) from e

    # Development mode fallback to local SQLite when local PostgreSQL is not running
    logger.warning(f"PostgreSQL connection unavailable ({e}). Falling back to local SQLite for development.")
    project_root = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(project_root) == "backend":
        project_root = os.path.dirname(project_root)
    db_file = os.path.join(project_root, "storage", "coalintel_db.sqlite")
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    sqlite_url = f"sqlite:///{db_file}"
    engine = create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False},
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

