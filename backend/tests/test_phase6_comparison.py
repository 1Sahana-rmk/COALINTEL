import sys
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import SessionLocal, get_db
from app.models.user import User
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.core.security import create_access_token
from app.services.conflict_service import (
    get_metric_domain,
    are_units_compatible,
    is_generic_mine_name,
)

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield db
    finally:
        app.dependency_overrides.clear()
        db.close()


@pytest.fixture
def auth_headers(db_session: Session):
    user = db_session.query(User).filter(User.username == "admin").first()
    if not user:
        user = User(
            username="admin",
            hashed_password="hashed_pwd_placeholder",
            role="Admin",
            subsidiary="CMPDI"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token(subject=user.username, role=user.role, subsidiary=user.subsidiary)
    return {"Authorization": f"Bearer {token}"}


def test_comparison_options_endpoint(auth_headers):
    """
    Verifies /api/v1/comparison/options returns dynamic options for entities, metrics, and fiscal years.
    """
    res = client.get("/api/v1/comparison/options", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "subsidiaries" in data
    assert "metrics" in data
    assert "fiscal_years" in data
    assert "entities" in data
    assert "ALL CIL" in data["subsidiaries"]


def test_comparison_matrix_consistent(db_session: Session, auth_headers):
    """
    Tests cross-document comparison with consistent sources (variance <= 1.0%).
    """
    uid = uuid.uuid4().hex[:8]
    doc1 = Document(
        filename=f"SECL_AR_Test_{uid}.pdf",
        file_path=f"/storage/uploads/SECL_AR_Test_{uid}.pdf",
        file_hash=f"hash_secl_{uid}",
        file_type="pdf",
        subsidiary="SECL",
        fiscal_year="2023-24",
        status="INDEXED"
    )
    doc2 = Document(
        filename=f"CIL_AR_Test_{uid}.pdf",
        file_path=f"/storage/uploads/CIL_AR_Test_{uid}.pdf",
        file_hash=f"hash_cil_{uid}",
        file_type="pdf",
        subsidiary="CIL HQ",
        fiscal_year="2023-24",
        status="INDEXED"
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    # Create matching metrics for Gevra OpenCast
    m1 = ExtractedMetric(
        document_id=doc1.id,
        mine_name=f"Gevra OpenCast {uid}",
        metric_name="Coal Production",
        numeric_value=50.0,
        unit="MT",
        standard_value=50.0,
        standard_unit="MT",
        fiscal_year="2023-24",
        page_number=5
    )
    m2 = ExtractedMetric(
        document_id=doc2.id,
        mine_name=f"Gevra OpenCast {uid}",
        metric_name="Coal Production",
        numeric_value=50.0,
        unit="MT",
        standard_value=50.0,
        standard_unit="MT",
        fiscal_year="2023-24",
        page_number=12
    )
    db_session.add_all([m1, m2])
    db_session.commit()

    res = client.get(
        f"/api/v1/comparison/matrix?metric_name=Coal%20Production&fiscal_year=2023-24&entity_filter=Gevra%20OpenCast%20{uid}",
        headers=auth_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_entities_compared"] >= 1

    gevra_matrix = next((m for m in data["matrices"] if uid in m["entity"]), None)
    assert gevra_matrix is not None
    assert gevra_matrix["status"] == "CONSISTENT"
    assert gevra_matrix["variance_percentage"] == 0.0
    assert gevra_matrix["has_discrepancy"] is False
    assert len(gevra_matrix["sources"]) == 2


def test_comparison_matrix_seeded_discrepancy(db_session: Session, auth_headers):
    """
    Verifies that a synthetic fixture (e.g. BCCL_Production_Audit_Q4.pdf) triggers
    DISCREPANCY DETECTED and is explicitly labeled as 'Seeded Mine-Level Discrepancy'.
    """
    uid = uuid.uuid4().hex[:8]
    doc_a = Document(
        filename=f"ECL_Report_{uid}.pdf",
        file_path=f"/storage/uploads/ECL_Report_{uid}.pdf",
        file_hash=f"hash_ecl_{uid}",
        file_type="pdf",
        subsidiary="ECL",
        fiscal_year="2023-24",
        status="INDEXED"
    )
    doc_b = Document(
        filename=f"BCCL_Production_Audit_Q4_{uid}.pdf",
        file_path=f"/storage/uploads/BCCL_Production_Audit_Q4_{uid}.pdf",
        file_hash=f"hash_bccl_audit_{uid}",
        file_type="pdf",
        subsidiary="BCCL",
        fiscal_year="2023-24",
        status="INDEXED"
    )
    db_session.add_all([doc_a, doc_b])
    db_session.commit()

    m_a = ExtractedMetric(
        document_id=doc_a.id,
        mine_name=f"Rajmahal OpenCast {uid}",
        metric_name="Coal Production",
        numeric_value=42.50,
        unit="MT",
        standard_value=42.50,
        standard_unit="MT",
        fiscal_year="2023-24",
        page_number=10
    )
    m_b = ExtractedMetric(
        document_id=doc_b.id,
        mine_name=f"Rajmahal OpenCast {uid}",
        metric_name="Coal Production",
        numeric_value=41.80,
        unit="MT",
        standard_value=41.80,
        standard_unit="MT",
        fiscal_year="2023-24",
        page_number=4
    )
    db_session.add_all([m_a, m_b])
    db_session.commit()

    res = client.get(
        f"/api/v1/comparison/matrix?metric_name=Coal%20Production&fiscal_year=2023-24&entity_filter=Rajmahal%20OpenCast%20{uid}",
        headers=auth_headers
    )
    assert res.status_code == 200
    data = res.json()
    
    rajmahal = next((m for m in data["matrices"] if uid in m["entity"]), None)
    assert rajmahal is not None
    assert rajmahal["status"] == "DISCREPANCY DETECTED"
    assert rajmahal["has_discrepancy"] is True
    assert rajmahal["variance_percentage"] == 1.65
    assert rajmahal["is_seeded_demo"] is True
    
    # Check source provenance labeling
    seeded_src = next((s for s in rajmahal["sources"] if f"BCCL_Production_Audit_Q4_{uid}.pdf" in s["filename"]), None)
    assert seeded_src is not None
    assert seeded_src["is_seeded_demo"] is True
    assert seeded_src["provenance_label"] == "Seeded Mine-Level Discrepancy"


def test_phase5b_semantic_logic_reuse():
    """
    Verifies that Phase 5B helper functions remain intact and are correctly reused.
    """
    assert get_metric_domain("Coal Production") == "PRODUCTION"
    assert get_metric_domain("Overburden Removal") == "OVERBURDEN"
    assert are_units_compatible("MT", "MT") is True
    assert are_units_compatible("MT", "M.Cu.M") is False
    assert is_generic_mine_name("SECL Mine") is True
    assert is_generic_mine_name("Rajmahal OpenCast") is False


def test_analytics_all_cil_scope(auth_headers):
    """
    Verifies ALL CIL analytics scope returns aggregate topics.
    """
    res = client.get("/api/v1/analytics/wordcloud?subsidiary_filter=ALL%20CIL", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "topics" in data
    assert len(data["topics"]) > 0


def test_analytics_specific_subsidiary_scope(db_session: Session, auth_headers):
    """
    Verifies specific subsidiary filter queries database records belonging ONLY to that subsidiary.
    """
    uid = uuid.uuid4().hex[:8]
    sub_name = f"SUB_{uid}"
    doc = Document(
        filename=f"Report_{uid}.pdf",
        file_path=f"/storage/uploads/Report_{uid}.pdf",
        file_hash=f"hash_analytics_{uid}",
        file_type="pdf",
        subsidiary=sub_name,
        fiscal_year="2023-24",
        status="INDEXED"
    )
    db_session.add(doc)
    db_session.commit()

    metric_name = f"Unique Metric {uid}"
    m = ExtractedMetric(
        document_id=doc.id,
        mine_name=f"Mine_{uid}",
        metric_name=metric_name,
        numeric_value=100.0,
        unit="MT",
        standard_value=100.0,
        standard_unit="MT",
        fiscal_year="2023-24"
    )
    db_session.add(m)
    db_session.commit()

    res = client.get(f"/api/v1/analytics/wordcloud?subsidiary_filter={sub_name}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "topics" in data
    topic_words = [t["word"] for t in data["topics"]]
    assert metric_name in topic_words


def test_analytics_unknown_subsidiary_scope(auth_headers):
    """
    Verifies an unknown/nonexistent subsidiary returns a valid empty response without fabricating fake data.
    """
    res = client.get("/api/v1/analytics/wordcloud?subsidiary_filter=NONEXISTENT_SUB_9999", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "topics" in data
    assert data["topics"] == []

