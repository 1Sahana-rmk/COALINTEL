from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
import app.models  # noqa: F401
from main import app
from app.core.security import create_access_token
from app.models.document import Document
from app.models.structured_fact import StructuredFact
from app.models.user import User
from app.services.report_grounding_service import (
    build_report_spec,
    collect_evidence_packet,
    deterministic_narrative,
    validate_evidence_packet,
)
from app.services.report_service import generate_report_pdf_bytes


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()


def _fact(session, fact_id=1, *, accepted=False, value="16"):
    document = Document(
        id=fact_id,
        filename=f"evidence-{fact_id}.pdf",
        file_path=f"/safe/evidence-{fact_id}.pdf",
        file_hash=f"{fact_id:064d}",
        file_type="PDF",
        subsidiary="MCL",
        fiscal_year="2023-24",
        status="INDEXED",
    )
    session.add(document)
    session.flush()
    fact = StructuredFact(
        id=fact_id,
        document_id=document.id,
        page_number=8,
        entity_type="SUBSIDIARY",
        entity_name_raw="MCL",
        entity_name_canonical="MCL",
        entity_resolution_method="TEST",
        metric_type="COAL_PRODUCTION",
        metric_name_raw="Coal Production",
        metric_name_canonical="COAL_PRODUCTION",
        metric_resolution_method="TEST",
        raw_value_text=f"{value} MT",
        raw_value_numeric=Decimal(value),
        normalized_value=Decimal(value),
        raw_unit="MT",
        normalized_unit="MT",
        period_raw="FY 2023-24",
        period_normalized="FY 2023-24",
        period_type="FISCAL_YEAR",
        extraction_method="NATIVE_TABLE",
        extraction_confidence=Decimal("0.9000"),
        evidence_type="TABLE_CELL",
        evidence_locator_json={"document_table_id": 4, "row_index": 1, "column_index": 2},
        validation_status="ACCEPTED" if accepted else "REVIEW_REQUIRED",
        fact_status="ACCEPTED" if accepted else "CANDIDATE",
        fact_key=f"{fact_id:064d}",
        duplicate_group_key=f"{fact_id + 100:064d}",
    )
    session.add(fact)
    session.commit()
    return fact


def test_report_packet_preserves_review_state_and_source(session):
    fact = _fact(session, accepted=False)
    packet = collect_evidence_packet(session, spec=build_report_spec(report_type="ANNUAL_SUMMARY", subsidiary="MCL", fiscal_year="2023-24"))
    validation = validate_evidence_packet(packet)
    assert packet["structured_facts"][0]["fact_id"] == fact.id
    assert packet["structured_facts"][0]["source"]["page_number"] == 8
    assert validation["state"] == "REVIEW_REQUIRED"
    narrative = deterministic_narrative(packet, validation)
    assert narrative["narrative_provider"] == "DETERMINISTIC_EVIDENCE_ONLY"


def test_accepted_packet_is_supported_and_no_cross_year_calculation(session):
    _fact(session, accepted=True)
    packet = collect_evidence_packet(session, spec=build_report_spec(report_type="ANNUAL_SUMMARY", subsidiary="MCL", fiscal_year="2023-24"))
    assert validate_evidence_packet(packet)["state"] == "SUPPORTED"
    assert len(packet["structured_facts"]) == 1


def test_pdf_has_no_hardcoded_fallback_metrics():
    pdf = generate_report_pdf_bytes(
        title="Empty evidence report", report_type="ANNUAL_SUMMARY", subsidiary="MCL", fiscal_year="2023-24",
        metrics_summary=[], validation_state="INSUFFICIENT_EVIDENCE",
    )
    assert pdf.startswith(b"%PDF")
    assert b"Rajmahal" not in pdf


def test_briefing_job_is_authenticated_and_duplicate_safe(session):
    user = User(id=1, username="step4d-admin", hashed_password="x", role="Admin", subsidiary="CIL HQ")
    session.add(user)
    session.commit()
    token = create_access_token(subject=user.username, role=user.role, subsidiary=user.subsidiary)
    app.dependency_overrides[get_db] = lambda: session
    try:
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {token}"}
        with patch("app.api.parliamentary._BRIEFING_EXECUTOR.submit"):
            payload = {"question_text": "What was coal production?", "fiscal_year": "2023-24", "subsidiary_filter": "MCL"}
            first = client.post("/api/v1/parliamentary/briefing/jobs", json=payload, headers=headers)
            second = client.post("/api/v1/parliamentary/briefing/jobs", json=payload, headers=headers)
        assert first.status_code == 202
        assert second.status_code == 202
        assert first.json()["job_id"] == second.json()["job_id"]
        assert client.post("/api/v1/parliamentary/briefing/jobs", json=payload).status_code == 401
    finally:
        app.dependency_overrides.clear()
