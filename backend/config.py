from pathlib import Path
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "COALINTEL"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # CORS & Production Origins
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

    # Security & Auth
    SECRET_KEY: str = "coalintel-super-secret-jwt-signing-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 Hours

    # Database. DATABASE_URL takes precedence when supplied. Otherwise the
    # POSTGRES_* values are composed into a URL when POSTGRES_DB and
    # POSTGRES_USER are configured. An empty component configuration preserves
    # the local SQLite development fallback.
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = ""
    # Storage Provider & Paths
    STORAGE_PROVIDER: str = "local"  # "local" or "supabase"
    UPLOAD_DIR: str = "./storage/uploads"
    CHROMA_DB_DIR: str = "./storage/chroma_db"
    REPORT_DIR: str = "./storage/reports"

    # Supabase Storage Configuration (Backend-only credentials)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_DOCUMENTS_BUCKET: str = "documents"
    SUPABASE_REPORTS_BUCKET: str = "reports"
    STORAGE_HTTP_CONNECT_TIMEOUT: float = 15.0
    STORAGE_HTTP_READ_TIMEOUT: float = 60.0

    # LLM Configuration (Provider Abstraction)
    LLM_PROVIDER: str = "gemini"  # "gemini", "openai", or "degraded"
    LLM_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gemini-3.6-flash"
    LLM_TIMEOUT_SECONDS: float = 10.0

    # RAG & Retrieval Hyperparameters
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    RRF_K_CONSTANT: int = 60
    CHUNK_SIZE_TOKENS: int = 500
    CHUNK_OVERLAP_TOKENS: int = 50

    # Validation Thresholds
    ARITHMETIC_WARNING_THRESHOLD_PCT: float = 5.0
    CROSS_DOC_CONFLICT_THRESHOLD_PCT: float = 1.0

    # Step 2B Document AI boundary. PaddleOCR is intentionally kept out of
    # the Python 3.14 backend; these settings address an isolated service.
    DOCUMENT_AI_ENABLED: bool = True
    DOCUMENT_AI_URL: str = "http://127.0.0.1:8765"
    DOCUMENT_AI_CONNECT_TIMEOUT_SECONDS: float = 0.5
    DOCUMENT_AI_OCR_TIMEOUT_SECONDS: float = 120.0
    DOCUMENT_AI_STRUCTURE_TIMEOUT_SECONDS: float = 180.0
    DOCUMENT_AI_ENABLE_STRUCTURE: bool = True
    DOCUMENT_AI_STRUCTURE_MODE: str = "table_hint"  # table_hint|always|disabled
    DOCUMENT_AI_FALLBACK_TO_TESSERACT: bool = True
    DOCUMENT_AI_DEVICE: str = "cpu"

    model_config = SettingsConfigDict(
        # Support repository-root .env and backend/.env regardless of the
        # process working directory. Environment variables take precedence.
        env_file=(
            str(REPOSITORY_ROOT / ".env"),
            str(REPOSITORY_ROOT / "backend" / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()


def build_database_url(config: Settings) -> str:
    """Resolve the configured database target without embedding credentials."""
    explicit_url = config.DATABASE_URL.strip()
    if explicit_url:
        return explicit_url

    if config.POSTGRES_USER.strip() and config.POSTGRES_DB.strip():
        user = quote(config.POSTGRES_USER.strip(), safe="")
        password = quote(config.POSTGRES_PASSWORD, safe="")
        auth = f"{user}:{password}@" if password else f"{user}@"
        database = quote(config.POSTGRES_DB.strip(), safe="")
        return f"postgresql://{auth}{config.POSTGRES_HOST.strip()}:{config.POSTGRES_PORT}/{database}"

    return "sqlite:///./storage/coalintel_db.sqlite"
