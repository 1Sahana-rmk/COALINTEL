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
from app.models.data_conflict import DataConflict
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


def test_parliamentary_briefing_valid_request(db_session: Session, auth_headers):
    """
    Verifies valid Parliamentary Briefing request returns structured briefing data.
    """
    uid = uuid.uuid4().hex[:8]
    doc = Document(
        filename=f"SECL_Report_{uid}.pdf",
        file_path=f"/storage/uploads/SECL_Report_{uid}.pdf",
        file_hash=f"hash_parl_{uid}",
        file_type="pdf",
        subsidiary="SECL",
        fiscal_year="2023-24",
        status="INDEXED"
    )
    db_session.add(doc)
    db_session.commit()

    m = ExtractedMetric(
        document_id=doc.id,
        mine_name=f"Gevra_{uid}",
        metric_name="Coal Production",
        numeric_value=55.0,
        unit="MT",
        standard_value=55.0,
        standard_unit="MT",
        fiscal_year="2023-24"
    )
    db_session.add(m)
    db_session.commit()

    payload = {
        "question_text": "What is the coal production for SECL in FY2023-24?",
        "fiscal_year": "2023-24",
        "subsidiary_filter": "SECL",
        "question_type": "TARGETS"
    }

    res = client.post("/api/v1/parliamentary/briefing", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["question"] == payload["question_text"]
    assert data["selected_scope"] == "SECL"
    assert data["has_sufficient_evidence"] is True
    assert len(data["subsidiary_metrics"]) >= 1
    mine_names = [m["mine_name"] for m in data["subsidiary_metrics"]]
    assert f"Gevra_{uid}" in mine_names


def test_parliamentary_briefing_auth_required():
    """
    Verifies unauthenticated request returns HTTP 401.
    """
    payload = {
        "question_text": "What is the production target?",
        "fiscal_year": "2023-24",
        "subsidiary_filter": "ALL CIL"
    }
    res = client.post("/api/v1/parliamentary/briefing", json=payload)
    assert res.status_code == 401


def test_parliamentary_briefing_insufficient_evidence(auth_headers):
    """
    Verifies request for non-existent scope returns insufficient evidence state without fabricating data.
    """
    payload = {
        "question_text": "What is the production target for NONEXISTENT_SUB?",
        "fiscal_year": "2099-00",
        "subsidiary_filter": "NONEXISTENT_SUB_999"
    }
    res = client.post("/api/v1/parliamentary/briefing", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_sufficient_evidence"] is False
    assert data["confidence_rating"] == "INSUFFICIENT_EVIDENCE"
    assert data["confidence"] == 0.0
    assert data["subsidiary_metrics"] == []


def test_parliamentary_briefing_seeded_discrepancy_provenance(db_session: Session, auth_headers):
    """
    Verifies synthetic fixture (BCCL_Production_Audit_Q4.pdf) retains 'Seeded Mine-Level Discrepancy' label.
    """
    uid = uuid.uuid4().hex[:8]
    doc_a = Document(
        filename=f"ECL_Report_{uid}.pdf",
        file_path=f"/storage/uploads/ECL_{uid}.pdf",
        file_hash=f"hash_ecl_p7_{uid}",
        file_type="pdf",
        subsidiary="ECL",
        fiscal_year="2023-24",
        status="INDEXED"
    )
    doc_b = Document(
        filename=f"BCCL_Production_Audit_Q4_{uid}.pdf",
        file_path=f"/storage/uploads/BCCL_{uid}.pdf",
        file_hash=f"hash_bccl_p7_{uid}",
        file_type="pdf",
        subsidiary="BCCL",
        fiscal_year="2023-24",
        status="INDEXED"
    )
    # Re-use exact filename matching string for seeded check
    doc_b.filename = "BCCL_Production_Audit_Q4.pdf"
    doc_b.file_hash = f"hash_bccl_exact_{uid}"

    db_session.add_all([doc_a, doc_b])
    db_session.commit()

    conflict = DataConflict(
        mine_name=f"Rajmahal OpenCast {uid}",
        metric_name="Coal Production",
        fiscal_year="2023-24",
        doc_a_id=doc_a.id,
        doc_b_id=doc_b.id,
        doc_a_value=42.50,
        doc_b_value=41.80,
        discrepancy_pct=1.65,
        status="OPEN"
    )
    db_session.add(conflict)
    db_session.commit()

    payload = {
        "question_text": "Identify any discrepancies in Rajmahal OpenCast production",
        "fiscal_year": "2023-24",
        "subsidiary_filter": "ALL CIL",
        "question_type": "DISCREPANCIES"
    }
    res = client.post("/api/v1/parliamentary/briefing", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "discrepancies" in data
    rajmahal_disc = next((d for d in data["discrepancies"] if uid in d["entity"]), None)
    assert rajmahal_disc is not None
    assert rajmahal_disc["is_seeded_demo"] is True
    assert rajmahal_disc["provenance_label"] == "Seeded Mine-Level Discrepancy"


def test_parliamentary_pdf_export(auth_headers):
    """
    Verifies PDF export endpoint returns valid PDF binary.
    """
    briefing_payload = {
        "question": "What is the FY2023-24 production target?",
        "question_type": "TARGETS",
        "fiscal_year": "2023-24",
        "selected_scope": "ALL CIL",
        "executive_summary": "Test briefing summary for PDF export.",
        "key_findings": ["Finding 1: Production on target.", "Finding 2: No critical variance."],
        "subsidiary_metrics": [
            {
                "mine_name": "Gevra OC",
                "subsidiary": "SECL",
                "metric_name": "Coal Production",
                "numeric_value": 50.0,
                "unit": "MT",
                "standard_value": 50.0,
                "standard_unit": "MT",
                "fiscal_year": "2023-24"
            }
        ],
        "discrepancies": [],
        "evidence": [],
        "confidence": 0.95,
        "confidence_rating": "HIGH",
        "has_sufficient_evidence": True,
        "limitations": ["Test limitation"],
        "generated_at": "2026-09-03 12:00:00 UTC"
    }

    res = client.post("/api/v1/parliamentary/export-pdf", json=briefing_payload, headers=auth_headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert len(res.content) > 100


def test_phase5b_conflict_and_phase6_comparison_regression():
    """
    Verifies helper functions from Phase 5B remain intact and functional.
    """
    assert get_metric_domain("Coal Production") == "PRODUCTION"
    assert get_metric_domain("Overburden Removal") == "OVERBURDEN"
    assert are_units_compatible("MT", "MT") is True
    assert are_units_compatible("MT", "M.Cu.M") is False
    assert is_generic_mine_name("SECL Mine") is True
    assert is_generic_mine_name("Rajmahal OpenCast") is False
