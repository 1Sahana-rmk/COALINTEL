import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import Base, get_db
from app.models import User, Document, ExtractedMetric, DataConflict
from database_seed import seed_default_users
from app.services.llm_provider import DegradedLLMProvider, get_llm_provider
from app.services.normalization_service import normalize_subsidiary_scope
from app.core.security import create_access_token


@pytest.fixture
def isolated_client():
    """Creates a temporary isolated SQLite database and TestClient for testing."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    db = TestSessionLocal()
    seed_default_users(db)

    # Seed sample metrics across subsidiaries
    doc1 = Document(
        filename="ECL_Doc.pdf",
        file_path="/tmp/ecl.pdf",
        file_hash="hash1",
        file_type="PDF",
        subsidiary="ECL",
        fiscal_year="2023-24",
        status="PARSED",
    )
    doc2 = Document(
        filename="SECL_Doc.pdf",
        file_path="/tmp/secl.pdf",
        file_hash="hash2",
        file_type="PDF",
        subsidiary="SECL",
        fiscal_year="2023-24",
        status="PARSED",
    )
    db.add_all([doc1, doc2])
    db.commit()
    db.refresh(doc1)
    db.refresh(doc2)

    m1 = ExtractedMetric(
        document_id=doc1.id,
        mine_name="Rajmahal OpenCast",
        subsidiary="ECL",
        metric_name="Coal Production",
        numeric_value=42.50,
        unit="MT",
        standard_value=42.50,
        standard_unit="MT",
        fiscal_year="2023-24",
        validation_status="VALIDATED",
        confidence_score=0.99,
    )
    m2 = ExtractedMetric(
        document_id=doc1.id,
        mine_name="Rajmahal OpenCast",
        subsidiary="ECL",
        metric_name="Overburden Removal",
        numeric_value=120.40,
        unit="M.Cu.M",
        standard_value=120.40,
        standard_unit="M.Cu.M",
        fiscal_year="2023-24",
        validation_status="VALIDATED",
        confidence_score=0.99,
    )
    m3 = ExtractedMetric(
        document_id=doc2.id,
        mine_name="Gevra OpenCast",
        subsidiary="SECL",
        metric_name="Overburden Removal",
        numeric_value=310.50,
        unit="M.Cu.M",
        standard_value=310.50,
        standard_unit="M.Cu.M",
        fiscal_year="2023-24",
        validation_status="VALIDATED",
        confidence_score=0.99,
    )
    m4 = ExtractedMetric(
        document_id=doc2.id,
        mine_name="Gevra OpenCast",
        subsidiary="SECL",
        metric_name="Coal Production",
        numeric_value=59.11,
        unit="MT",
        standard_value=59.11,
        standard_unit="MT",
        fiscal_year="2023-24",
        validation_status="VALIDATED",
        confidence_score=0.99,
    )
    db.add_all([m1, m2, m3, m4])

    conflict = DataConflict(
        mine_name="Rajmahal OpenCast",
        metric_name="Coal Production",
        fiscal_year="2023-24",
        doc_a_id=doc1.id,
        doc_a_value=42.50,
        doc_b_id=doc2.id,
        doc_b_value=41.80,
        discrepancy_pct=1.67,
        status="OPEN",
    )
    db.add(conflict)
    db.commit()

    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, db
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=test_engine)


def test_auth_signup_flow(isolated_client):
    client, db = isolated_client

    # 1. Successful signup
    payload = {
        "username": "new_analyst",
        "password": "Password@123",
        "full_name": "Test Analyst",
        "email": "analyst@test.cil.in",
        "subsidiary": "ECL",
    }
    res = client.post("/api/v1/auth/signup", json=payload)
    assert res.status_code in [200, 201]
    data = res.json()
    assert "access_token" in data
    assert data["user"]["username"] == "new_analyst"
    # Role must default to Analyst
    assert data["user"]["role"] == "Analyst"

    # 2. Duplicate username rejected
    dup_res = client.post("/api/v1/auth/signup", json=payload)
    assert dup_res.status_code == 400
    assert "already registered" in dup_res.json()["detail"].lower()


def test_quick_login_shortcuts(isolated_client):
    client, db = isolated_client

    # Admin quick login credentials
    admin_res = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin@123"},
    )
    assert admin_res.status_code == 200
    admin_data = admin_res.json()
    assert admin_data["user"]["role"] == "Admin"
    assert "access_token" in admin_data

    # Analyst quick login credentials
    analyst_res = client.post(
        "/api/v1/auth/login",
        json={"username": "analyst", "password": "Analyst@123"},
    )
    assert analyst_res.status_code == 200
    analyst_data = analyst_res.json()
    assert analyst_data["user"]["role"] == "Analyst"
    assert "access_token" in analyst_data


def test_dashboard_all_subsidiaries_aggregation(isolated_client):
    client, db = isolated_client

    token = create_access_token(subject="admin", role="Admin", subsidiary="CIL HQ")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Global / All Subsidiaries aggregation
    for filter_val in ["ALL", "All Subsidiaries", "ALL CIL", "ALL_SUBSIDIARIES", ""]:
        params = {"subsidiary_filter": filter_val} if filter_val else {}
        res = client.get("/api/v1/dashboard/kpis", params=params, headers=headers)
        assert res.status_code == 200
        data = res.json()
        # Sum of ECL (42.50) + SECL (59.11) = 101.61 MT
        assert float(data["total_production_mt"]) == pytest.approx(101.61, 0.01)
        # Sum of ECL OBR (120.40) + SECL OBR (310.50) = 430.90 M.Cu.M
        assert float(data["total_obr_mcum"]) == pytest.approx(430.90, 0.01)

    # 2. Specific Subsidiary: ECL
    ecl_res = client.get("/api/v1/dashboard/kpis", params={"subsidiary_filter": "ECL"}, headers=headers)
    assert ecl_res.status_code == 200
    ecl_data = ecl_res.json()
    assert float(ecl_data["total_production_mt"]) == pytest.approx(42.50, 0.01)
    assert float(ecl_data["total_obr_mcum"]) == pytest.approx(120.40, 0.01)

    # 3. Specific Subsidiary: SECL
    secl_res = client.get("/api/v1/dashboard/kpis", params={"subsidiary_filter": "SECL"}, headers=headers)
    assert secl_res.status_code == 200
    secl_data = secl_res.json()
    assert float(secl_data["total_production_mt"]) == pytest.approx(59.11, 0.01)
    assert float(secl_data["total_obr_mcum"]) == pytest.approx(310.50, 0.01)

    # 4. Nonexistent Subsidiary
    none_res = client.get("/api/v1/dashboard/kpis", params={"subsidiary_filter": "NONEXISTENT_SUB"}, headers=headers)
    assert none_res.status_code == 200
    none_data = none_res.json()
    assert float(none_data["total_production_mt"]) == 0.0
    assert float(none_data["total_obr_mcum"]) == 0.0


def test_normalization_service_subsidiary_scope():
    assert normalize_subsidiary_scope(None) is None
    assert normalize_subsidiary_scope("") is None
    assert normalize_subsidiary_scope("ALL") is None
    assert normalize_subsidiary_scope("All Subsidiaries") is None
    assert normalize_subsidiary_scope("ALL CIL") is None
    assert normalize_subsidiary_scope("ALL_CIL") is None
    assert normalize_subsidiary_scope("ALL_SUBSIDIARIES") is None
    assert normalize_subsidiary_scope("ECL") == "ECL"
    assert normalize_subsidiary_scope("SECL") == "SECL"


def test_degraded_llm_general_ai_code_generation():
    provider = DegradedLLMProvider()

    calc_res = provider.generate_general_ai("give me the python code for a calculator")
    assert "def" in calc_res["answer"] or "class" in calc_res["answer"]
    assert calc_res["mode"] == "GENERAL_AI"
    assert len(calc_res["citations"]) == 0

    fact_res = provider.generate_general_ai("write Python code for factorial")
    assert "def factorial" in fact_res["answer"]
    assert fact_res["mode"] == "GENERAL_AI"
    assert len(fact_res["citations"]) == 0

    btree_res = provider.generate_general_ai("what is a binary tree?")
    assert "Binary Tree" in btree_res["answer"] or "tree" in btree_res["answer"].lower()
    assert btree_res["mode"] == "GENERAL_AI"


def test_conflicts_api_detail_and_status_filter(isolated_client):
    client, db = isolated_client

    token = create_access_token(subject="admin", role="Admin", subsidiary="CIL HQ")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List conflicts with status_filter="ALL"
    res = client.get("/api/v1/conflicts", params={"status_filter": "ALL"}, headers=headers)
    assert res.status_code == 200
    conflicts = res.json()
    assert len(conflicts) >= 1
    conflict_id = conflicts[0]["id"]

    # 2. Get conflict by ID
    detail_res = client.get(f"/api/v1/conflicts/{conflict_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == conflict_id
    assert detail["mine_name"] == "Rajmahal OpenCast"

    # 3. Nonexistent conflict ID
    not_found = client.get("/api/v1/conflicts/99999", headers=headers)
    assert not_found.status_code == 404


def test_gemini_http_failure_logging_and_secret_sanitization(caplog):
    """Verifies that Gemini HTTP failure is logged at WARNING and secret API key is redacted."""
    import logging
    from unittest.mock import patch, MagicMock
    from app.services.llm_provider import GeminiLLMProvider

    secret_key = "AIzaSySecretKey9988776655"
    provider = GeminiLLMProvider(api_key=secret_key, model_name="gemini-3.6-flash")

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = f'{{"error": {{"code": 400, "message": "API key not valid: {secret_key}", "status": "INVALID_ARGUMENT"}}}}'

    with caplog.at_level(logging.WARNING):
        with patch("requests.post", return_value=mock_resp):
            res = provider.generate_general_ai("give me the python code")

    # 1. Degraded fallback occurred
    assert res["provider"] == "degraded"
    assert res["degraded_mode"] is True
    assert "def execute_task" in res["answer"]

    # 2. Warning log emitted
    warning_logs = [r for r in caplog.records if r.levelno >= logging.WARNING and "provider=gemini" in r.message]
    assert len(warning_logs) >= 1
    log_text = " ".join(r.message for r in warning_logs)

    # 3. Secret API key MUST NOT appear anywhere in the log text
    assert secret_key not in log_text
    assert "[REDACTED]" in log_text
    assert "status=400" in log_text


def test_gemini_network_exception_logging_and_secret_sanitization(caplog):
    """Verifies that Gemini connection/network exceptions are logged at WARNING with URL query keys redacted."""
    import logging
    from unittest.mock import patch
    import requests
    from app.services.llm_provider import GeminiLLMProvider

    secret_key = "AIzaSyNetworkSecret112233"
    provider = GeminiLLMProvider(api_key=secret_key, model_name="gemini-3.6-flash")

    exc_msg = f"Connection refused to https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={secret_key}"

    with caplog.at_level(logging.WARNING):
        with patch("requests.post", side_effect=requests.exceptions.ConnectionError(exc_msg)):
            res = provider.generate_general_ai("how does coal form?")

    # 1. Degraded fallback occurred
    assert res["provider"] == "degraded"
    assert res["degraded_mode"] is True

    # 2. Warning log emitted
    warning_logs = [r for r in caplog.records if r.levelno >= logging.WARNING and "provider=gemini" in r.message]
    assert len(warning_logs) >= 1
    log_text = " ".join(r.message for r in warning_logs)

    # 3. Secret key must NOT appear in log text
    assert secret_key not in log_text
    assert "[REDACTED]" in log_text
    assert "ConnectionError" in log_text


def test_gemini_successful_execution():
    """Verifies that successful Gemini response returns provider='gemini' and degraded_mode=False."""
    from unittest.mock import patch, MagicMock
    from app.services.llm_provider import GeminiLLMProvider

    provider = GeminiLLMProvider(api_key="valid-mock-key", model_name="gemini-3.6-flash")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "```python\ndef calculate_density():\n    return 1.35\n```"}]
                }
            }
        ]
    }

    with patch("requests.post", return_value=mock_resp):
        res = provider.generate_general_ai("give me the python code")

    assert res["provider"] == "gemini"
    assert res["degraded_mode"] is False
    assert "calculate_density" in res["answer"]


def test_degraded_response_supports_llm_api_key_wording():
    """Verifies that degraded general AI responses mention LLM_API_KEY / GEMINI_API_KEY neutrality."""
    provider = DegradedLLMProvider()

    code_res = provider.generate_general_ai("give me the python code")
    assert "LLM_API_KEY" in code_res["answer"]
    assert "GEMINI_API_KEY" in code_res["answer"]
    assert "configure a valid LLM API key" in code_res["answer"]

    concept_res = provider.generate_general_ai("unusual prompt xyz123")
    assert "LLM_API_KEY" in concept_res["answer"]
    assert "GEMINI_API_KEY" in concept_res["answer"]

