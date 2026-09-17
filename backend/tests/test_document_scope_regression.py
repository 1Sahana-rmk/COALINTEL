import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import Base, get_db
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.models.user import User
from app.core.rbac import get_current_user


@pytest.fixture
def test_db_session():
    """Provides an isolated SQLite in-memory database with test documents across subsidiaries."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    # Create mock admin user
    test_user = User(
        id=1,
        username="admin",
        hashed_password="hashed_pw",
        role="Admin",
        subsidiary="CIL HQ",
        email="admin@coalintel.cil.in"
    )
    db.add(test_user)
    
    # Create sample documents with diverse subsidiaries and statuses
    docs = [
        Document(
            id=1,
            filename="ECL_Production_Report.pdf",
            file_path="/tmp/ecl.pdf",
            file_hash="1111111111111111111111111111111111111111111111111111111111111111",
            file_type="PDF",
            file_size_bytes=10000,
            subsidiary="ECL",
            fiscal_year="2023-24",
            status="PARSED",
            uploaded_by=1
        ),
        Document(
            id=2,
            filename="SECL_Despatch_Summary.csv",
            file_path="/tmp/secl.csv",
            file_hash="2222222222222222222222222222222222222222222222222222222222222222",
            file_type="CSV",
            file_size_bytes=20000,
            subsidiary="SECL",
            fiscal_year="2023-24",
            status="PARSED",
            uploaded_by=1
        ),
        Document(
            id=3,
            filename="BCCL_Audit_Q4.pdf",
            file_path="/tmp/bccl.pdf",
            file_hash="3333333333333333333333333333333333333333333333333333333333333333",
            file_type="PDF",
            file_size_bytes=30000,
            subsidiary="BCCL",
            fiscal_year="2023-24",
            status="PROCESSING",
            uploaded_by=1
        ),
        Document(
            id=4,
            filename="CIL_HQ_Corporate_Plan.xlsx",
            file_path="/tmp/cil.xlsx",
            file_hash="4444444444444444444444444444444444444444444444444444444444444444",
            file_type="XLSX",
            file_size_bytes=40000,
            subsidiary="CIL HQ",
            fiscal_year="2023-24",
            status="INDEXED",
            uploaded_by=1
        ),
    ]
    db.add_all(docs)
    db.commit()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db_session):
    """Overrides FastAPI dependencies with isolated test session and authenticated admin user."""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    def override_get_current_user():
        return test_db_session.query(User).filter(User.username == "admin").first()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as test_client:
        yield test_client
        
    app.dependency_overrides.clear()


def test_documents_unrestricted_when_no_filter(client):
    """GET /api/v1/documents with no parameters returns all unrestricted documents."""
    res = client.get("/api/v1/documents")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 4
    assert len(data["items"]) == 4


def test_documents_unrestricted_when_subsidiary_filter_is_all(client):
    """GET /api/v1/documents with subsidiary_filter='ALL' returns all unrestricted documents."""
    res = client.get("/api/v1/documents?subsidiary_filter=ALL")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 4
    assert len(data["items"]) == 4


def test_documents_unrestricted_when_subsidiary_filter_is_all_cil(client):
    """GET /api/v1/documents with subsidiary_filter='ALL CIL' returns all unrestricted documents."""
    res = client.get("/api/v1/documents?subsidiary_filter=ALL%20CIL")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 4
    assert len(data["items"]) == 4
    # All 4 subsidiaries should be present in the returned list
    subs = {item["subsidiary"] for item in data["items"]}
    assert subs == {"ECL", "SECL", "BCCL", "CIL HQ"}


def test_documents_filtered_to_specific_subsidiary_ecl(client):
    """GET /api/v1/documents with subsidiary_filter='ECL' filters precisely to ECL."""
    res = client.get("/api/v1/documents?subsidiary_filter=ECL")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["subsidiary"] == "ECL"
    assert data["items"][0]["filename"] == "ECL_Production_Report.pdf"


def test_documents_filtered_to_specific_subsidiary_secl(client):
    """GET /api/v1/documents with subsidiary_filter='SECL' filters precisely to SECL."""
    res = client.get("/api/v1/documents?subsidiary_filter=SECL")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["subsidiary"] == "SECL"
    assert data["items"][0]["filename"] == "SECL_Despatch_Summary.csv"


def test_documents_filtered_by_status(client):
    """GET /api/v1/documents filters by status when specified and remains unrestricted for status_filter='ALL'."""
    # status_filter='ALL' -> returns all 4
    res_all = client.get("/api/v1/documents?status_filter=ALL")
    assert res_all.status_code == 200
    assert res_all.json()["total"] == 4

    # status_filter='PARSED' -> returns 2 (ECL and SECL)
    res_parsed = client.get("/api/v1/documents?status_filter=PARSED")
    assert res_parsed.status_code == 200
    assert res_parsed.json()["total"] == 2
    for item in res_parsed.json()["items"]:
        assert item["status"] == "PARSED"


def test_document_by_id_detail(client):
    """GET /api/v1/documents/{id} returns document metadata."""
    res = client.get("/api/v1/documents/1")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 1
    assert data["filename"] == "ECL_Production_Report.pdf"
    assert data["subsidiary"] == "ECL"


def test_document_pages_endpoint(client):
    """GET /api/v1/documents/{id}/pages returns pages structure."""
    res = client.get("/api/v1/documents/1/pages")
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == 1
    assert data["filename"] == "ECL_Production_Report.pdf"


def test_document_lineage_endpoint_with_extracted_metric(client, test_db_session):
    """GET /api/v1/documents/{id}/lineage queries ExtractedMetric without NameError."""
    metric = ExtractedMetric(
        id=1,
        document_id=1,
        page_number=14,
        mine_name="Rajmahal OC",
        subsidiary="ECL",
        metric_name="Coal Production",
        numeric_value=42.50,
        unit="Lakh Tonnes",
        raw_unit="Lakh Tonnes",
        standard_value=4.25,
        standard_unit="MT",
        fiscal_year="2023-24",
        confidence_score=0.98,
        validation_status="VALIDATED",
        raw_snippet="Total production reached 42.50 Lakh Tonnes."
    )
    test_db_session.add(metric)
    test_db_session.commit()

    res = client.get("/api/v1/documents/1/lineage")
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == 1
    assert len(data["metrics"]) == 1
    assert data["metrics"][0]["mine_name"] == "Rajmahal OC"
    assert data["metrics"][0]["standard_value"] == 4.25
    assert data["metrics"][0]["standard_unit"] == "MT"

