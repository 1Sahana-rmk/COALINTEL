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
    """Provides an isolated SQLite in-memory database with test document and metrics."""
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
    
    # Create sample document
    doc = Document(
        id=11,
        filename="srn-march-2025.pdf",
        file_path="storage/uploads/srn-march-2025.pdf",
        file_hash="mockhash130pagesrn2025",
        file_type="pdf",
        file_size_bytes=1048576,
        subsidiary="SCCL",
        fiscal_year="2023-24",
        status="PARSED",
        total_pages=130,
        uploaded_by=1
    )
    db.add(doc)
    
    db.commit()
    yield db
    db.close()


@pytest.fixture
def client(test_db_session):
    """FastAPI TestClient with overridden get_db and current_user dependencies."""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    def override_current_user():
        return test_db_session.query(User).filter(User.username == "admin").first()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_lineage_serialization_exact_confidence_score(client, test_db_session):
    """
    Regression Test:
    Verifies that GET /api/v1/documents/{id}/lineage serializes the exact confidence_score
    from the database (e.g. 0.900) rather than omitting it or defaulting to 0.950.
    """
    metric = ExtractedMetric(
        id=101,
        document_id=11,
        page_number=45,
        mine_name="KTK OC",
        subsidiary="SCCL",
        metric_name="Coal Production",
        numeric_value=1.75,
        unit="MT",
        raw_unit="MT",
        standard_value=1.75,
        standard_unit="MT",
        fiscal_year="2023-24",
        confidence_score=0.900,
        validation_status="VALIDATED",
        raw_snippet="Coal Production achieved is 1.75 MT from KTK OC in FY 2023-24."
    )
    test_db_session.add(metric)
    test_db_session.commit()

    res = client.get("/api/v1/documents/11/lineage")
    assert res.status_code == 200
    data = res.json()

    assert data["document_id"] == 11
    assert data["filename"] == "srn-march-2025.pdf"
    assert len(data["metrics"]) == 1

    serialized_metric = data["metrics"][0]
    
    # Verify exact confidence score serialization
    assert "confidence_score" in serialized_metric
    assert serialized_metric["confidence_score"] == 0.900
    assert serialized_metric["confidence_score"] != 0.950

    # Verify validation status remains unchanged
    assert serialized_metric["validation_status"] == "VALIDATED"

    # Verify all other expected fields are preserved
    assert serialized_metric["mine_name"] == "KTK OC"
    assert serialized_metric["metric_name"] == "Coal Production"
    assert serialized_metric["numeric_value"] == 1.75
    assert serialized_metric["standard_value"] == 1.75
    assert serialized_metric["standard_unit"] == "MT"
    assert serialized_metric["fiscal_year"] == "2023-24"


def test_lineage_serialization_various_confidence_and_unverified(client, test_db_session):
    """
    Verifies that various dynamic confidence scores (e.g. 0.650 for UNVERIFIED,
    0.750, and None fallback to 0.95) serialize properly with validation_status.
    """
    m1 = ExtractedMetric(
        id=102,
        document_id=11,
        page_number=103,
        mine_name="IK OC",
        subsidiary="SCCL",
        metric_name="Mining Metric (Unclassified)",
        numeric_value=1.50,
        unit="MT",
        standard_value=1.50,
        standard_unit="MT",
        fiscal_year="2023-24",
        confidence_score=0.650,
        validation_status="UNVERIFIED",
        raw_snippet="Obtained for 1.50 MTPA (Peak) on 31.07.2008 for IK OC."
    )
    m2 = ExtractedMetric(
        id=103,
        document_id=11,
        page_number=104,
        mine_name="Unspecified Mine",
        subsidiary="SCCL",
        metric_name="Coal Production",
        numeric_value=5.41,
        unit="MT",
        standard_value=5.41,
        standard_unit="MT",
        fiscal_year="2023-24",
        confidence_score=None,  # Tests None fallback
        validation_status="UNVERIFIED",
        raw_snippet="Overall output reached 5.41 MT."
    )
    test_db_session.add_all([m1, m2])
    test_db_session.commit()

    res = client.get("/api/v1/documents/11/lineage")
    assert res.status_code == 200
    data = res.json()
    metrics = {m["id"]: m for m in data["metrics"]}

    # Metric 1: 0.650 UNVERIFIED
    assert metrics[102]["confidence_score"] == 0.650
    assert metrics[102]["validation_status"] == "UNVERIFIED"

    # Metric 2: None -> fallback 0.95
    assert metrics[103]["confidence_score"] == 0.95
    assert metrics[103]["validation_status"] == "UNVERIFIED"
