import unittest
import os
import sys
from decimal import Decimal
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base
from app.models.user import User
from app.models.document import Document
from app.models.data_conflict import DataConflict
from app.models.data_provenance import DataSource, DataObservation, DataConflictRecord
from app.models.mine import MineMaster, MineYearlyMetric
from app.models.audit_log import AuditLog
from app.models.extracted_metric import ExtractedMetric

from app.services.ingestion_service import validate_file_upload, MAX_FILE_SIZE_BYTES
from app.services.rag_service import (
    classify_query_intent,
    build_insufficient_evidence_response,
    execute_rag_query,
)
from app.api.validation import list_conflicts, get_conflict_by_id, resolve_conflict_endpoint
from app.api.comparison import get_comparison_matrix
from app.schemas.validation import ConflictResolveRequest


class TestProductionHardeningRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()
        self.test_user = User(
            id=1,
            username="admin_test",
            email="admin@coalintel.gov.in",
            hashed_password="fakehash1234567890",
            role="Admin",
            subsidiary="CIL HQ"
        )
        self.db.query(DataConflict).delete()
        self.db.query(DataConflictRecord).delete()
        self.db.query(MineMaster).delete()
        self.db.query(MineYearlyMetric).delete()
        self.db.query(Document).delete()
        self.db.query(AuditLog).delete()
        self.db.commit()

    def tearDown(self):
        self.db.close()

    # =========================================================================
    # PROBLEM 1: METRIC COMPARISON & CONFLICT RESOLVER CONSISTENCY TESTS
    # =========================================================================

    def test_01_conflict_resolver_lists_both_document_and_government_conflicts(self):
        """Verify list_conflicts includes both DataConflict and DataConflictRecord consistently."""
        # 1. Seed a Document and a DataConflict
        doc1 = Document(id=1, filename="Doc1.pdf", file_path="uploads/Doc1.pdf", file_hash="hash1", subsidiary="ECL", file_type="pdf", status="INDEXED")
        doc2 = Document(id=2, filename="Doc2.pdf", file_path="uploads/Doc2.pdf", file_hash="hash2", subsidiary="ECL", file_type="pdf", status="INDEXED")
        self.db.add_all([doc1, doc2])
        self.db.commit()

        dc = DataConflict(
            id=1,
            doc_a_id=1,
            doc_b_id=2,
            mine_name="Rajmahal OpenCast",
            metric_name="Coal Production",
            fiscal_year="2023-24",
            doc_a_value=42.5,
            doc_b_value=41.8,
            discrepancy_pct=1.65,
            status="OPEN"
        )
        self.db.add(dc)

        # 2. Seed a MineMaster and a DataConflictRecord (Official Gov record)
        mine = MineMaster(
            mine_id="MINE-SECL-GEVRA",
            mine_name="Gevra OpenCast",
            normalized_mine_name="gevra opencast",
            subsidiary_name="SECL",
            company_name="South Eastern Coalfields Limited",
            state="Chhattisgarh",
            operational_status="PRODUCING"
        )
        self.db.add(mine)

        gov_cr = DataConflictRecord(
            conflict_id=1,
            entity_type="mine",
            entity_id="MINE-SECL-GEVRA",
            metric="production",
            financial_year="2024-25",
            source_a="MOC-CD-2024-25 (Table 3.2)",
            value_a=Decimal("59.32"),
            source_b="MOC-MS-2024-25 (Provisional Flash)",
            value_b=Decimal("59.10"),
            difference=Decimal("0.22"),
            difference_percent=Decimal("0.37"),
            possible_reason="provisional_vs_final",
            resolution_status="OPEN"
        )
        self.db.add(gov_cr)
        self.db.commit()

        conflicts = list_conflicts(db=self.db, current_user=self.test_user)
        self.assertEqual(len(conflicts), 2)

        mine_names = [c.mine_name for c in conflicts]
        self.assertIn("Rajmahal OpenCast", mine_names)
        self.assertIn("Gevra OpenCast", mine_names)

        gevra_item = next(c for c in conflicts if c.mine_name == "Gevra OpenCast")
        self.assertEqual(gevra_item.id, 10001)
        self.assertEqual(gevra_item.subsidiary, "SECL")
        self.assertEqual(gevra_item.document_a_filename, "MOC-CD-2024-25 (Table 3.2)")
        self.assertEqual(gevra_item.document_b_filename, "MOC-MS-2024-25 (Provisional Flash)")

    def test_02_get_conflict_by_id_and_resolve_government_record(self):
        """Verify resolving a DataConflictRecord via Conflict Resolver endpoint works and writes audit log."""
        mine = MineMaster(
            mine_id="MINE-SECL-GEVRA",
            mine_name="Gevra OpenCast",
            normalized_mine_name="gevra opencast",
            subsidiary_name="SECL",
            company_name="South Eastern Coalfields Limited",
            state="Chhattisgarh",
            operational_status="PRODUCING"
        )
        self.db.add(mine)

        gov_cr = DataConflictRecord(
            conflict_id=5,
            entity_type="mine",
            entity_id="MINE-SECL-GEVRA",
            metric="production",
            financial_year="2024-25",
            source_a="MOC-CD-2024-25",
            value_a=Decimal("59.32"),
            source_b="MOC-MS-2024-25",
            value_b=Decimal("59.10"),
            difference=Decimal("0.22"),
            difference_percent=Decimal("0.37"),
            possible_reason="provisional_vs_final",
            resolution_status="OPEN"
        )
        self.db.add(gov_cr)
        self.db.commit()

        # Direct fetch by unified ID
        item = get_conflict_by_id(id=10005, db=self.db, current_user=self.test_user)
        self.assertEqual(item.id, 10005)
        self.assertEqual(item.mine_name, "Gevra OpenCast")
        self.assertEqual(item.status, "OPEN")

        # Resolve
        payload = ConflictResolveRequest(
            resolution_action="ACCEPT_DOC_A",
            notes="Adopted official Coal Directory figure"
        )
        resolved = resolve_conflict_endpoint(
            id=10005,
            payload=payload,
            db=self.db,
            current_user=self.test_user
        )
        self.assertEqual(resolved.status, "RESOLVED")

        # Verify DB state & audit log
        cr_in_db = self.db.query(DataConflictRecord).filter(DataConflictRecord.conflict_id == 5).first()
        self.assertEqual(cr_in_db.resolution_status, "RESOLVED")
        self.assertEqual(float(cr_in_db.resolved_value), 59.32)

        audit = self.db.query(AuditLog).filter(
            AuditLog.resource_type == "DataConflictRecord",
            AuditLog.resource_id == 5
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.action, "CONFLICT_RESOLVE")

    def test_03_comparison_matrix_links_canonical_conflict_id(self):
        """Verify comparison matrix returns canonical_conflict_id for both gov and document discrepancies."""
        mine = MineMaster(
            mine_id="MINE-SECL-GEVRA",
            mine_name="Gevra OpenCast",
            normalized_mine_name="gevra opencast",
            subsidiary_name="SECL",
            company_name="South Eastern Coalfields Limited",
            state="Chhattisgarh",
            operational_status="PRODUCING"
        )
        self.db.add(mine)

        gov_cr = DataConflictRecord(
            conflict_id=9,
            entity_type="mine",
            entity_id="MINE-SECL-GEVRA",
            metric="production",
            financial_year="2024-25",
            source_a="MOC-CD-2024-25",
            value_a=Decimal("59.32"),
            source_b="MOC-MS-2024-25",
            value_b=Decimal("59.10"),
            difference=Decimal("0.22"),
            difference_percent=Decimal("0.37"),
            possible_reason="provisional_vs_final",
            resolution_status="OPEN"
        )
        self.db.add(gov_cr)
        self.db.commit()

        matrix_res = get_comparison_matrix(
            metric_name="Coal Production",
            fiscal_year="2024-25",
            entity_filter="Gevra",
            db=self.db,
            current_user=self.test_user
        )
        self.assertGreaterEqual(len(matrix_res["matrices"]), 1)
        gevra_matrix = matrix_res["matrices"][0]
        self.assertTrue(gevra_matrix["has_discrepancy"] or gevra_matrix["has_conflict"])
        self.assertEqual(gevra_matrix["canonical_conflict_id"], 10009)

    # =========================================================================
    # PROBLEM 2: RAG SAFE GROUNDED FALLBACK TESTS
    # =========================================================================

    def test_04_rag_classification_and_informative_fallback_when_no_evidence(self):
        """Verify queries for unindexed mines return informative grounded refusal without numbers."""
        q = "How much production did Kusmunda produce in FY 2023-24?"
        mode = classify_query_intent(q)
        self.assertEqual(mode, "EVIDENCE_GROUNDED")

        # Mock execute_hybrid_search returning empty list
        with patch("app.services.rag_service.execute_hybrid_search", return_value=[]):
            res = execute_rag_query(db=self.db, query_text=q)
            self.assertEqual(res["mode"], "INSUFFICIENT_EVIDENCE")
            self.assertEqual(len(res["citations"]), 0)
            self.assertIn("Insufficient evidence", res["answer"])
            self.assertIn("Kusmunda", res["answer"])
            self.assertIn("2023-24", res["answer"])
            # Ensure zero hallucinated numbers in answer
            import re
            numbers = re.findall(r"\b\d+\.\d+\b", res["answer"])
            self.assertEqual(len(numbers), 0, f"Found hallucinated float numbers: {numbers}")

    def test_05_rag_conceptual_query_routes_to_general_ai(self):
        """Verify general conceptual questions route to GENERAL_AI without requiring documents."""
        q = "What is overburden removal in opencast mining?"
        mode = classify_query_intent(q)
        self.assertEqual(mode, "GENERAL_AI")

    # =========================================================================
    # PROBLEM 3: 50 MB UPLOAD CEILING TESTS
    # =========================================================================

    def test_06_ingestion_50mb_validation_limit(self):
        """Verify ingestion service strictly enforces 50 MB upload ceiling."""
        self.assertEqual(MAX_FILE_SIZE_BYTES, 50 * 1024 * 1024)

        # 50 MB exactly should be valid
        self.assertEqual(validate_file_upload("valid_report.pdf", 50 * 1024 * 1024), "PDF")
        self.assertEqual(validate_file_upload("valid_data.xlsx", 10 * 1024 * 1024), "XLSX")

        # 50 MB + 1 byte should raise HTTP 400
        with self.assertRaises(HTTPException) as ctx:
            validate_file_upload("oversized.pdf", (50 * 1024 * 1024) + 1)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("exceeds maximum allowed limit of 50 MB", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
