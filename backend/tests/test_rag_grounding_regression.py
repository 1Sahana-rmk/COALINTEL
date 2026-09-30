import unittest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base
from database_seed import init_db
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.models.document_chunk import DocumentChunk
from app.services.normalization_service import normalize_unit_to_mt
from app.services.hybrid_search_service import execute_hybrid_search
from app.services.rag_service import execute_rag_query, build_isolated_prompt, extract_and_validate_citations


class TestRAGGroundingRegression(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Sets up in-memory SQLite database seeded with domain metrics & document data."""
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=cls.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        cls.db = TestingSessionLocal()
        
        # Seed test database
        init_db(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_unit_normalization_deterministic(self):
        """Task 11D: Verify 42.50 Lakh Tonnes is deterministically normalized to 4.25 MT (not 42.50 MT)."""
        std_val, std_unit = normalize_unit_to_mt(42.50, "Lakh Tonnes")
        self.assertEqual(std_val, 4.25)
        self.assertEqual(std_unit, "MT")

        # Additional unit checks
        val_mt, unit_mt = normalize_unit_to_mt(42.50, "MT")
        self.assertEqual(val_mt, 42.50)
        self.assertEqual(unit_mt, "MT")

    def test_retrieval_priority_exact_mine_entity(self):
        """Retrieval-Level Test: Verify hybrid search ranks Rajmahal OC entity metric/chunk ahead of ECL total."""
        results = execute_hybrid_search(
            db=self.db,
            query_text="What was the coal production of Rajmahal OC specifically in FY 2023-24?",
            top_k=5
        )

        self.assertGreater(len(results), 0)
        top_item = results[0]

        # Top item text must reference Rajmahal OC and metric value 4.25 MT (or 4.18 MT / Lakh Tonnes)
        self.assertIn("Rajmahal", top_item["text"])
        self.assertTrue(any(val in top_item["text"] for val in ["4.25", "42.50", "4.18", "41.80"]))
        self.assertNotIn("42.50 MT", top_item["text"])  # Must not use 42.50 MT for Rajmahal

    def test_rag_query_rajmahal_mine_specific(self):
        """Task 11A: Query for Rajmahal OC specifically returns Rajmahal entity value (4.25 MT / 42.50 Lakh Tonnes)."""
        res = execute_rag_query(
            db=self.db,
            query_text="What was the coal production of Rajmahal OC specifically in FY 2023-24?",
            top_k=5
        )

        answer = res["answer"]
        self.assertTrue("4.25" in answer or "42.50 Lakh" in answer)
        # Verify ECL aggregate 42.50 MT is not presented as Rajmahal OC's production
        self.assertNotIn("Rajmahal OC recorded 42.50 MT", answer)
        self.assertNotIn("Rajmahal OC total coal production reached 42.50 MT", answer)

    def test_rag_query_ecl_total(self):
        """Task 11B: Query for ECL total production returns ECL aggregate value (42.50 MT)."""
        res = execute_rag_query(
            db=self.db,
            query_text="What was ECL's total coal production in FY 2023-24?",
            top_k=5
        )

        answer = res["answer"]
        self.assertIn("42.50", answer)
        self.assertIn("ECL", answer)

    def test_rag_query_comparison(self):
        """Task 11C: Compare Rajmahal OC production with ECL total production in FY 2023-24."""
        res = execute_rag_query(
            db=self.db,
            query_text="Compare Rajmahal OC production with ECL total production in FY 2023-24.",
            top_k=5
        )

        answer = res["answer"]
        self.assertGreaterEqual(len(res["evidence_chunks"]), 2)

    def test_citations_validity(self):
        """Task 11E: Verify citations point to actual retrieved chunks/pages."""
        res = execute_rag_query(
            db=self.db,
            query_text="What was the coal production of Rajmahal OC specifically in FY 2023-24?",
            top_k=5
        )

        self.assertGreater(len(res["citations"]), 0)
        citation = res["citations"][0]
        self.assertIn("ECL_Annual_Report_2023-24.pdf", citation["document_name"])
        self.assertIn("Page", citation["citation_tag"])

    def test_insufficient_evidence_response(self):
        """Task 10 & 11F: Verify non-existent entity query returns 'Insufficient evidence found for this query.'"""
        res = execute_rag_query(
            db=self.db,
            query_text="What was the coal production of Atlantis OC in FY 2023-24?",
            top_k=5
        )

        self.assertIn("Insufficient evidence", res["answer"])


if __name__ == "__main__":
    unittest.main()
