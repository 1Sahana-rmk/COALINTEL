import os
import sys
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.services.rag_service import execute_rag_query


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


def test_production_targets_use_structured_evidence_without_vector_retrieval():
    engine, db = _session()
    try:
        doc = Document(
            filename="srn-may-2023.pdf",
            file_path="storage/uploads/srn-may-2023.pdf",
            file_hash="target-test-hash",
            file_type="PDF",
            subsidiary="MCL",
            fiscal_year="2023-24",
            status="PARSED",
        )
        db.add(doc)
        db.flush()
        db.add_all([
            ExtractedMetric(
                document_id=doc.id,
                page_number=8,
                mine_name="MCL",
                subsidiary="MCL",
                metric_name="Monthly Production Target",
                numeric_value=Decimal("10.00"),
                standard_value=Decimal("10.00"),
                standard_unit="MT",
                unit="MT",
                fiscal_year="2023-24",
                raw_snippet="Coal Production Table | MCL | Monthly Target (May 2023-24): 10.0 MT",
            ),
            ExtractedMetric(
                document_id=doc.id,
                page_number=8,
                mine_name="MCL",
                subsidiary="MCL",
                metric_name="Coal Production",
                numeric_value=Decimal("8.00"),
                standard_value=Decimal("8.00"),
                standard_unit="MT",
                unit="MT",
                fiscal_year="2023-24",
                raw_snippet="Coal Production Table | MCL | Monthly Production (May 2023-24): 8.0 MT",
            ),
        ])
        db.commit()

        with patch("app.services.rag_service.execute_hybrid_search", side_effect=AssertionError("vector retrieval must not run")):
            result = execute_rag_query(
                db,
                "What is the subsidiary-wise coal production achievement and target variance for FY2023-24?",
                question_type="TARGETS",
            )

        assert result["provider"] == "structured_analytics"
        assert "achievement 80.00%" in result["answer"]
        assert "target variance -20.00%" in result["answer"]
        assert len(result["evidence_chunks"]) == 2
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_production_targets_do_not_invent_unaligned_annual_variance():
    engine, db = _session()
    try:
        doc = Document(
            filename="annual-production.pdf",
            file_path="storage/uploads/annual-production.pdf",
            file_hash="target-unmatched-hash",
            file_type="PDF",
            subsidiary="MCL",
            fiscal_year="2023-24",
            status="PARSED",
        )
        db.add(doc)
        db.flush()
        db.add(ExtractedMetric(
            document_id=doc.id,
            page_number=1,
            mine_name="MCL",
            subsidiary="MCL",
            metric_name="Coal Production",
            numeric_value=Decimal("100.00"),
            standard_value=Decimal("100.00"),
            standard_unit="MT",
            unit="MT",
            fiscal_year="2023-24",
            raw_snippet="Annual production total: 100 MT",
        ))
        db.commit()

        with patch("app.services.rag_service.execute_hybrid_search", side_effect=AssertionError("vector retrieval must not run")):
            result = execute_rag_query(
                db,
                "What is the subsidiary-wise coal production achievement and target variance for FY2023-24?",
                question_type="TARGETS",
            )

        assert "variance are therefore unavailable" in result["answer"]
        assert result["evidence_chunks"] == []
    finally:
        db.close()
        Base.metadata.drop_all(engine)
