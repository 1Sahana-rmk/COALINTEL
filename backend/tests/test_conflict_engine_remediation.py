import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.models.data_conflict import DataConflict
from app.services.conflict_service import (
    is_generic_mine_name,
    get_metric_domain,
    are_units_compatible,
    detect_and_register_cross_document_conflicts
)

# In-memory SQLite for clean unit testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


# Test 1: Generic fallback entity -> no conflict
def test_1_generic_fallback_entity_no_conflict(setup_db):
    db = setup_db
    assert is_generic_mine_name("CIL Mine") is True
    assert is_generic_mine_name("ECL Mine") is True
    assert is_generic_mine_name("CMPDI Mine") is True
    assert is_generic_mine_name("Rajmahal OpenCast") is False

    doc1 = Document(filename="Doc1.pdf", subsidiary="CIL", file_type="PDF", file_path="/tmp/1", file_hash="h1", uploaded_by=1)
    doc2 = Document(filename="Doc2.pdf", subsidiary="SECL", file_type="PDF", file_path="/tmp/2", file_hash="h2", uploaded_by=1)
    db.add_all([doc1, doc2])
    db.commit()

    m1 = ExtractedMetric(document_id=doc1.id, mine_name="CIL Mine", metric_name="Coal Production", numeric_value=700.0, unit="MT", standard_value=700.0, standard_unit="MT", fiscal_year="2023-24")
    m2 = ExtractedMetric(document_id=doc2.id, mine_name="CIL Mine", metric_name="Coal Production", numeric_value=500.0, unit="MT", standard_value=500.0, standard_unit="MT", fiscal_year="2023-24")
    db.add_all([m1, m2])
    db.commit()

    res = detect_and_register_cross_document_conflicts(db)
    assert res["new_conflicts_count"] == 0
    assert res["generic_entity_exclusions"] >= 2


# Test 2: Different organizations -> no conflict unless specific named mine
def test_2_different_organizations_no_conflict(setup_db):
    db = setup_db
    doc1 = Document(filename="CIL_Report.pdf", subsidiary="CIL", file_type="PDF", file_path="/tmp/1", file_hash="h1", uploaded_by=1)
    doc2 = Document(filename="SECL_Report.pdf", subsidiary="SECL", file_type="PDF", file_path="/tmp/2", file_hash="h2", uploaded_by=1)
    db.add_all([doc1, doc2])
    db.commit()

    m1 = ExtractedMetric(document_id=doc1.id, mine_name="SECL Mine", metric_name="Coal Production", numeric_value=773.0, unit="MT", standard_value=773.0, standard_unit="MT", fiscal_year="2023-24")
    m2 = ExtractedMetric(document_id=doc2.id, mine_name="SECL Mine", metric_name="Coal Production", numeric_value=187.0, unit="MT", standard_value=187.0, standard_unit="MT", fiscal_year="2023-24")
    db.add_all([m1, m2])
    db.commit()

    res = detect_and_register_cross_document_conflicts(db)
    assert res["new_conflicts_count"] == 0


# Test 3: CIL total production vs SECL production -> no conflict
def test_3_cil_total_vs_secl_production_no_conflict(setup_db):
    db = setup_db
    doc1 = Document(filename="CIL_AR.pdf", subsidiary="CIL", file_type="PDF", file_path="/tmp/1", file_hash="h1", uploaded_by=1)
    doc2 = Document(filename="SECL_AR.pdf", subsidiary="SECL", file_type="PDF", file_path="/tmp/2", file_hash="h2", uploaded_by=1)
    db.add_all([doc1, doc2])
    db.commit()

    m1 = ExtractedMetric(document_id=doc1.id, mine_name="CIL Mine", metric_name="Production", numeric_value=773.65, unit="MT", standard_value=773.65, standard_unit="MT", fiscal_year="2023-24")
    m2 = ExtractedMetric(document_id=doc2.id, mine_name="SECL Mine", metric_name="Production", numeric_value=187.38, unit="MT", standard_value=187.38, standard_unit="MT", fiscal_year="2023-24")
    db.add_all([m1, m2])
    db.commit()

    res = detect_and_register_cross_document_conflicts(db)
    assert res["new_conflicts_count"] == 0


# Test 4: CMPDI drilling vs CIL production -> no conflict
def test_4_cmpdi_drilling_vs_cil_production_no_conflict(setup_db):
    db = setup_db
    assert get_metric_domain("Drilling Meterage") == "DRILLING"
    assert get_metric_domain("Coal Production") == "PRODUCTION"

    doc1 = Document(filename="CMPDI_AR.pdf", subsidiary="CMPDI", file_type="PDF", file_path="/tmp/1", file_hash="h1", uploaded_by=1)
    doc2 = Document(filename="CIL_AR.pdf", subsidiary="CIL", file_type="PDF", file_path="/tmp/2", file_hash="h2", uploaded_by=1)
    db.add_all([doc1, doc2])
    db.commit()

    m1 = ExtractedMetric(document_id=doc1.id, mine_name="Rajmahal OpenCast", metric_name="Production", numeric_value=450.0, unit="Metres", standard_value=450.0, standard_unit="Metres", fiscal_year="2023-24", raw_snippet="Drilling meterage for Rajmahal OC")
    m2 = ExtractedMetric(document_id=doc2.id, mine_name="Rajmahal OpenCast", metric_name="Production", numeric_value=4.25, unit="MT", standard_value=4.25, standard_unit="MT", fiscal_year="2023-24", raw_snippet="Coal production at Rajmahal OC")
    db.add_all([m1, m2])
    db.commit()

    res = detect_and_register_cross_document_conflicts(db)
    assert res["new_conflicts_count"] == 0
    assert res["domain_incompatibility_exclusions"] >= 1


# Test 5: CMPDI exploration vs Ministry production -> no conflict
def test_5_cmpdi_exploration_vs_ministry_production_no_conflict(setup_db):
    db = setup_db
    doc1 = Document(filename="CMPDI_AR.pdf", subsidiary="CMPDI", file_type="PDF", file_path="/tmp/1", file_hash="h1", uploaded_by=1)
    doc2 = Document(filename="MoC_Report.pdf", subsidiary="MINISTRY_OF_COAL", file_type="PDF", file_path="/tmp/2", file_hash="h2", uploaded_by=1)
    db.add_all([doc1, doc2])
    db.commit()

    m1 = ExtractedMetric(document_id=doc1.id, mine_name="Gevra OC", metric_name="Geological Exploration", numeric_value=120.0, unit="Reports", standard_value=120.0, standard_unit="Reports", fiscal_year="2023-24")
    m2 = ExtractedMetric(document_id=doc2.id, mine_name="Gevra OC", metric_name="Coal Production", numeric_value=52.5, unit="MT", standard_value=52.5, standard_unit="MT", fiscal_year="2023-24")
    db.add_all([m1, m2])
    db.commit()

    res = detect_and_register_cross_document_conflicts(db)
    assert res["new_conflicts_count"] == 0


# Test 6: Same mine + same metric + same FY + compatible units + >1% -> CONFLICT REGISTERED
def test_6_valid_mine_discrepancy_creates_conflict(setup_db):
    db = setup_db
    doc1 = Document(filename="ECL_Report.pdf", subsidiary="ECL", file_type="PDF", file_path="/tmp/1", file_hash="h1", uploaded_by=1)
    doc2 = Document(filename="BCCL_Audit.pdf", subsidiary="BCCL", file_type="PDF", file_path="/tmp/2", file_hash="h2", uploaded_by=1)
    db.add_all([doc1, doc2])
    db.commit()

    m1 = ExtractedMetric(document_id=doc1.id, mine_name="Rajmahal OpenCast", metric_name="Coal Production", numeric_value=42.50, unit="MT", standard_value=42.50, standard_unit="MT", fiscal_year="2023-24")
    m2 = ExtractedMetric(document_id=doc2.id, mine_name="Rajmahal OpenCast", metric_name="Coal Production", numeric_value=41.80, unit="MT", standard_value=41.80, standard_unit="MT", fiscal_year="2023-24")
    db.add_all([m1, m2])
    db.commit()

    res = detect_and_register_cross_document_conflicts(db)
    assert res["new_conflicts_count"] == 1
    conflicts = db.query(DataConflict).all()
    assert len(conflicts) == 1
    assert conflicts[0].mine_name == "Rajmahal OpenCast"
    assert float(conflicts[0].discrepancy_pct) == 1.65


# Test 7: Same mine + same metric + same FY + <1% -> no conflict
def test_7_minor_discrepancy_under_1_percent_no_conflict(setup_db):
    db = setup_db
    doc1 = Document(filename="DocA.pdf", subsidiary="ECL", file_type="PDF", file_path="/tmp/1", file_hash="h1", uploaded_by=1)
    doc2 = Document(filename="DocB.pdf", subsidiary="ECL", file_type="PDF", file_path="/tmp/2", file_hash="h2", uploaded_by=1)
    db.add_all([doc1, doc2])
    db.commit()

    m1 = ExtractedMetric(document_id=doc1.id, mine_name="Gevra OC", metric_name="Coal Production", numeric_value=100.0, unit="MT", standard_value=100.0, standard_unit="MT", fiscal_year="2023-24")
    m2 = ExtractedMetric(document_id=doc2.id, mine_name="Gevra OC", metric_name="Coal Production", numeric_value=100.5, unit="MT", standard_value=100.5, standard_unit="MT", fiscal_year="2023-24")
    db.add_all([m1, m2])
    db.commit()

    res = detect_and_register_cross_document_conflicts(db)
    assert res["new_conflicts_count"] == 0
    assert res["threshold_exclusions"] >= 1


# Test 8: Same metric but incompatible units -> no conflict
def test_8_incompatible_units_no_conflict(setup_db):
    db = setup_db
    assert are_units_compatible("Metres", "MT") is False

    doc1 = Document(filename="DocA.pdf", subsidiary="SECL", file_type="PDF", file_path="/tmp/1", file_hash="h1", uploaded_by=1)
    doc2 = Document(filename="DocB.pdf", subsidiary="SECL", file_type="PDF", file_path="/tmp/2", file_hash="h2", uploaded_by=1)
    db.add_all([doc1, doc2])
    db.commit()

    m1 = ExtractedMetric(document_id=doc1.id, mine_name="Dipka OC", metric_name="Overburden Removal", numeric_value=120.0, unit="Metres", standard_value=120.0, standard_unit="Metres", fiscal_year="2023-24")
    m2 = ExtractedMetric(document_id=doc2.id, mine_name="Dipka OC", metric_name="Overburden Removal", numeric_value=120.0, unit="MT", standard_value=120.0, standard_unit="MT", fiscal_year="2023-24")
    db.add_all([m1, m2])
    db.commit()

    res = detect_and_register_cross_document_conflicts(db)
    assert res["new_conflicts_count"] == 0
    assert res["unit_incompatibility_exclusions"] >= 1


# Test 9: Same mine + same metric + different FY -> no conflict
def test_9_different_fiscal_years_no_conflict(setup_db):
    db = setup_db
    doc1 = Document(filename="Doc2023.pdf", subsidiary="ECL", file_type="PDF", file_path="/tmp/1", file_hash="h1", uploaded_by=1)
    doc2 = Document(filename="Doc2024.pdf", subsidiary="ECL", file_type="PDF", file_path="/tmp/2", file_hash="h2", uploaded_by=1)
    db.add_all([doc1, doc2])
    db.commit()

    m1 = ExtractedMetric(document_id=doc1.id, mine_name="Rajmahal OpenCast", metric_name="Coal Production", numeric_value=40.80, unit="MT", standard_value=40.80, standard_unit="MT", fiscal_year="2022-23")
    m2 = ExtractedMetric(document_id=doc2.id, mine_name="Rajmahal OpenCast", metric_name="Coal Production", numeric_value=42.50, unit="MT", standard_value=42.50, standard_unit="MT", fiscal_year="2023-24")
    db.add_all([m1, m2])
    db.commit()

    res = detect_and_register_cross_document_conflicts(db)
    assert res["new_conflicts_count"] == 0


# Test 10: Same mine + same metric + same FY + source variance semantics
def test_10_valid_source_variance_semantics(setup_db):
    db = setup_db
    doc1 = Document(filename="ECL_Annual_Report_2023-24.pdf", subsidiary="ECL", file_type="PDF", file_path="/tmp/1", file_hash="h1", uploaded_by=1)
    doc2 = Document(filename="CIL_Production_Bulletin.pdf", subsidiary="CIL", file_type="PDF", file_path="/tmp/2", file_hash="h2", uploaded_by=1)
    db.add_all([doc1, doc2])
    db.commit()

    m1 = ExtractedMetric(document_id=doc1.id, mine_name="Rajmahal OpenCast", metric_name="Coal Production", numeric_value=42.50, unit="MT", standard_value=42.50, standard_unit="MT", fiscal_year="2023-24")
    m2 = ExtractedMetric(document_id=doc2.id, mine_name="Rajmahal OpenCast", metric_name="Coal Production", numeric_value=41.80, unit="MT", standard_value=41.80, standard_unit="MT", fiscal_year="2023-24")
    db.add_all([m1, m2])
    db.commit()

    res = detect_and_register_cross_document_conflicts(db)
    assert res["new_conflicts_count"] == 1
    c = db.query(DataConflict).first()
    assert c.status == "OPEN"
    assert c.mine_name == "Rajmahal OpenCast"
    assert float(c.discrepancy_pct) == 1.65
