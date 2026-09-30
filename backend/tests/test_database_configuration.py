from config import Settings, build_database_url


def test_explicit_database_url_takes_precedence():
    configured = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://postgres@127.0.0.1:5432/coalintel_step1_acceptance",
        POSTGRES_USER="wrong-user",
        POSTGRES_DB="wrong-db",
    )

    assert build_database_url(configured) == configured.DATABASE_URL


def test_component_configuration_supports_pgpass_without_password():
    configured = Settings(
        _env_file=None,
        DATABASE_URL="",
        POSTGRES_USER="postgres",
        POSTGRES_PASSWORD="",
        POSTGRES_DB="coalintel_step1_acceptance",
        POSTGRES_HOST="127.0.0.1",
        POSTGRES_PORT=5432,
    )

    assert build_database_url(configured) == "postgresql://postgres@127.0.0.1:5432/coalintel_step1_acceptance"


def test_component_configuration_quotes_credentials():
    configured = Settings(
        _env_file=None,
        DATABASE_URL="",
        POSTGRES_USER="coal user",
        POSTGRES_PASSWORD="secret/pass",
        POSTGRES_DB="coalintel_db",
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5432,
    )

    assert build_database_url(configured) == "postgresql://coal%20user:secret%2Fpass@localhost:5432/coalintel_db"


def test_empty_database_configuration_preserves_sqlite_fallback():
    configured = Settings(_env_file=None, DATABASE_URL="", POSTGRES_USER="", POSTGRES_DB="")

    assert build_database_url(configured) == "sqlite:///./storage/coalintel_db.sqlite"
