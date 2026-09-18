import os
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Database
    POSTGRES_USER: str = "coalintel"
    POSTGRES_PASSWORD: str = "TestCoal123!"
    POSTGRES_DB: str = "coalintel_db"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql://coalintel:TestCoal123!@127.0.0.1:5432/coalintel_db"
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
