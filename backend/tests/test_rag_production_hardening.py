import unittest
import os
import sys
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base
from database_seed import init_db
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.models.document_chunk import DocumentChunk
from app.services.hybrid_search_service import detect_query_entities, execute_hybrid_search
from app.services.rag_service import (
    classify_query_intent,
    execute_rag_query,
    build_insufficient_evidence_response,
    handle_structured_analytical_query
)


class TestRAGProductionHardening(unittest.TestCase):
    """
    Regression Test Suite for the 10 Accepted Forensic Audit Test Cases (TC-RAG-01 through TC-RAG-10).
    Verifies query entity parsing, intent classification, corpus-wide retrieval, structured analytical
    query processing, authority gate behavior, and citation preservation across official reports.
    """

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=cls.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        cls.db = TestingSessionLocal()

        # Seed standard DB
        init_db(cls.db)

        # Seed representation of the 5 Ministry of Coal Monthly Statistical Reports
        cls._seed_ministry_reports(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    @classmethod
    def _seed_ministry_reports(cls, db):
        """Seeds official Ministry of Coal monthly reports (Nov 2024, Dec 2024, Jan 2025, Feb 2025, Mar 2025)."""
        reports = [
            ("srn-november-2024.pdf", "2024-25", "November", "2024"),
            ("srn-december-2024.pdf", "2024-25", "December", "2024"),
            ("srn-january-2025.pdf", "2024-25", "January", "2025"),
            ("srn-february-2025.pdf", "2024-25", "February", "2025"),
            ("srn-march-2025.pdf", "2024-25", "March", "2025"),
        ]

        # In production March 2025 Page 5:
        # Table 1: Subsidiary-wise Coal Production (Fig. in MT)
        # MCL: 22.38, SECL: 20.30, NCL: 13.97, CCL: 10.42, WCL: 8.35, ECL: 5.76, BCCL: 4.58, Total CIL: 85.76
        subsidiary_prod_march = [
            ("MCL", Decimal("22.38")),
            ("SECL", Decimal("20.30")),
            ("NCL", Decimal("13.97")),
            ("CCL", Decimal("10.42")),
            ("WCL", Decimal("8.35")),
            ("ECL", Decimal("5.76")),
            ("BCCL", Decimal("4.58")),
            ("CIL Corporate", Decimal("85.76")),
        ]

        # Nov 2024 Page 5
        subsidiary_prod_nov = [
            ("MCL", Decimal("18.50")),
            ("SECL", Decimal("16.80")),
            ("NCL", Decimal("11.50")),
            ("CCL", Decimal("8.20")),
            ("WCL", Decimal("6.90")),
            ("ECL", Decimal("4.30")),
            ("BCCL", Decimal("3.80")),
            ("CIL Corporate", Decimal("70.00")),
        ]

        for fname, fy, month, year in reports:
            doc = Document(
                filename=fname,
                file_path=f"storage/uploads/{fname}",
                file_hash=f"hash_{fname.replace('.', '_')}",
                file_type="PDF",
                file_size_bytes=500000,
                subsidiary="CIL",
                fiscal_year=fy,
                status="INDEXED",
                total_pages=128
            )
            db.add(doc)
            db.flush()

            # Seed Page 5 chunk
            sub_prod = subsidiary_prod_march if month == "March" else subsidiary_prod_nov
            sub_lines = "\n".join(f"{sub}: {val} MT" for sub, val in sub_prod)
            chunk_p5_text = (
                f"Ministry of Coal Provisional Monthly Statistics for {month} {year}.\n"
                f"Table 1: Subsidiary-Wise Coal Production (Fig. in MT):\n"
                f"{sub_lines}\n"
                f"Total Overburden Removal (OBR) for {month} {year} was 10.0 M.Cu.M."
            )
            c5 = DocumentChunk(
                document_id=doc.id,
                chunk_index=5,
                chunk_text=chunk_p5_text,
                page_number=5,
                token_count=180
            )
            db.add(c5)

            # Seed Page 5 metrics
            for sub, val in sub_prod:
                mine_label = "CIL Corporate" if sub == "CIL Corporate" else f"{sub} Total"
                sub_label = "CIL" if sub == "CIL Corporate" else sub
                m = ExtractedMetric(
                    document_id=doc.id,
                    page_number=5,
                    mine_name=mine_label,
                    subsidiary=sub_label,
                    metric_name="Coal Production",
                    numeric_value=val,
                    unit="MT",
                    standard_value=val,
                    standard_unit="MT",
                    fiscal_year=fy,
                    confidence_score=Decimal("0.98"),
                    validation_status="VALIDATED",
                    raw_snippet=f"{sub}: {val} MT (Table 1: Subsidiary-Wise Coal Production for {month} {year})",
                    data_origin="OFFICIAL"
                )
                db.add(m)

            # Seed an OBR metric for this report (e.g. 10.0 M.Cu.M.)
            obr_m = ExtractedMetric(
                document_id=doc.id,
                page_number=5,
                mine_name="CIL Total OBR",
                subsidiary="CIL",
                metric_name="Overburden Removal",
                numeric_value=Decimal("10.00"),
                unit="M.Cu.M.",
                standard_value=Decimal("10.00"),
                standard_unit="MCuM",
                fiscal_year=fy,
                confidence_score=Decimal("0.95"),
                validation_status="VALIDATED",
                raw_snippet=f"Total Overburden Removal for {month} {year} was 10.0 M.Cu.M.",
                data_origin="OFFICIAL"
            )
            db.add(obr_m)

        db.commit()

    # =========================================================================
    # TC-RAG-01: "What is the overburden removal in the ingested documents?"
    # =========================================================================
    def test_tc_rag_01_overburden_in_ingested_documents(self):
        """TC-RAG-01: Corpus-wide document inquiry on OBR must route to EVIDENCE_GROUNDED and retrieve evidence."""
        query = "What is the overburden removal in the ingested documents?"
        intent = classify_query_intent(query)
        self.assertEqual(intent, "EVIDENCE_GROUNDED", f"Expected EVIDENCE_GROUNDED, got {intent}")

        res = execute_rag_query(self.db, query, top_k=5)
        self.assertEqual(res["mode"], "EVIDENCE_GROUNDED")
        self.assertGreater(len(res["citations"]), 0)
        self.assertNotIn("configure a valid LLM API key", res["answer"])
        self.assertTrue(
            any("srn-" in c["document_name"] or "SECL" in c["document_name"] or "ECL" in c["document_name"]
                for c in res["citations"])
        )

    # =========================================================================
    # TC-RAG-02: "What was the coal production reported in the ingested documents?"
    # =========================================================================
    def test_tc_rag_02_coal_production_reported_in_ingested_documents(self):
        """TC-RAG-02: Plural 'ingested documents' coal production inquiry routes to EVIDENCE_GROUNDED."""
        query = "What was the coal production reported in the ingested documents?"
        intent = classify_query_intent(query)
        self.assertEqual(intent, "EVIDENCE_GROUNDED", f"Expected EVIDENCE_GROUNDED, got {intent}")

        res = execute_rag_query(self.db, query, top_k=5)
        self.assertEqual(res["mode"], "EVIDENCE_GROUNDED")
        self.assertGreater(len(res["citations"]), 0)
        self.assertNotIn("configure a valid LLM API key", res["answer"])

    # =========================================================================
    # TC-RAG-03: "What was the coal production in March 2025?"
    # =========================================================================
    def test_tc_rag_03_coal_production_march_2025(self):
        """TC-RAG-03: Calendar month 'March' must NEVER be parsed as a mine. Retrieves March 2025 evidence."""
        query = "What was the coal production in March 2025?"

        # 1. Entity parsing check
        entities = detect_query_entities(query)
        self.assertEqual(entities["mines"], [], "March must NEVER be parsed as a mine entity!")
        self.assertEqual(entities["metric"], "Coal Production")
        t_scope = entities.get("temporal_scope", {})
        self.assertEqual(t_scope.get("primary_month"), "March")
        self.assertEqual(t_scope.get("primary_year"), "2025")

        # 2. Intent check
        intent = classify_query_intent(query)
        self.assertEqual(intent, "EVIDENCE_GROUNDED")

        # 3. Execution check
        res = execute_rag_query(self.db, query, top_k=5)
        self.assertEqual(res["mode"], "EVIDENCE_GROUNDED")
        self.assertNotIn("for mine 'March'", res["answer"])
        self.assertGreater(len(res["citations"]), 0)
        self.assertTrue(any("srn-march-2025.pdf" in c["document_name"] for c in res["citations"]))

    # =========================================================================
    # TC-RAG-04: "Compare coal production between November 2024 and March 2025."
    # =========================================================================
    def test_tc_rag_04_compare_nov_2024_and_mar_2025(self):
        """TC-RAG-04: Neither November nor March may be parsed as a mine. Both periods retrieved."""
        query = "Compare coal production between November 2024 and March 2025."

        # 1. Entity parsing check
        entities = detect_query_entities(query)
        self.assertEqual(entities["mines"], [], "Months must NEVER be parsed as mines!")
        t_scope = entities.get("temporal_scope", {})
        self.assertEqual(len(t_scope.get("periods", [])), 2)
        months_found = {p["month"] for p in t_scope["periods"]}
        self.assertIn("November", months_found)
        self.assertIn("March", months_found)

        # 2. Intent check
        intent = classify_query_intent(query)
        self.assertEqual(intent, "EVIDENCE_GROUNDED")

        # 3. Execution check
        res = execute_rag_query(self.db, query, top_k=5)
        self.assertEqual(res["mode"], "EVIDENCE_GROUNDED")
        self.assertNotIn("for mine 'November'", res["answer"])
        self.assertNotIn("for mine 'March'", res["answer"])
        doc_names = [c["document_name"] for c in res["citations"]]
        self.assertTrue(any("srn-november-2024.pdf" in d for d in doc_names))
        self.assertTrue(any("srn-march-2025.pdf" in d for d in doc_names))

    # =========================================================================
    # TC-RAG-05: "Which CIL subsidiary had the highest coal production in the ingested reports?"
    # =========================================================================
    def test_tc_rag_05_highest_subsidiary_coal_production(self):
        """TC-RAG-05: Structured aggregation for subsidiary comparison with evidence citations."""
        query = "Which CIL subsidiary had the highest coal production in the ingested reports?"

        # 1. Intent check
        intent = classify_query_intent(query)
        self.assertEqual(intent, "EVIDENCE_GROUNDED")

        # 2. Execution check
        res = execute_rag_query(self.db, query, top_k=5)
        self.assertEqual(res["mode"], "EVIDENCE_GROUNDED")
        self.assertIn("highest", res["answer"].lower())
        # MCL has highest production (22.38 MT in March, or 193.30 MT in seed)
        self.assertTrue("MCL" in res["answer"] or "SECL" in res["answer"])
        self.assertGreater(len(res["citations"]), 0)
        # Must retain document filename and page number
        for c in res["citations"]:
            self.assertTrue(c["document_name"].endswith(".pdf") or c["document_name"].endswith(".xlsx"))
            self.assertIsInstance(c["page_number"], int)

    # =========================================================================
    # TC-RAG-06: "List all projects/mines with overburden removal exceeding 100 M.Cu.M."
    # =========================================================================
    def test_tc_rag_06_overburden_exceeding_100_numeric_filter(self):
        """
        TC-RAG-06: 'Cu' is NOT a mine. Structured numeric filter.
        If no values exceed 100, clearly state:
        'No indexed project/mine exceeds 100 M.Cu.M. in the available evidence.'
        Do NOT prepend 'Insufficient evidence'.
        """
        query = "List all projects/mines with overburden removal exceeding 100 M.Cu.M."

        # 1. Entity parsing check
        entities = detect_query_entities(query)
        self.assertEqual(entities["mines"], [], "'Cu' must NEVER be parsed as a mine entity!")
        self.assertEqual(entities["metric"], "Overburden Removal")

        # 2. Intent check
        intent = classify_query_intent(query)
        self.assertEqual(intent, "EVIDENCE_GROUNDED")

        # 3. Execution check
        res = execute_rag_query(self.db, query, top_k=5)
        self.assertEqual(res["mode"], "EVIDENCE_GROUNDED")
        self.assertNotIn("mine 'Cu'", res["answer"])
        # Either list projects exceeding 100 or clearly state none exceeds 100 without prepending "Insufficient evidence"
        if "No indexed project/mine exceeds 100" in res["answer"]:
            self.assertFalse(res["answer"].startswith("Insufficient evidence"))
            self.assertIn("No indexed project/mine exceeds 100", res["answer"])
            self.assertGreater(len(res["citations"]), 0)
        else:
            # If standard seed has Rajmahal OC (120.40 M.Cu.M.), it should be listed
            self.assertIn("100", res["answer"])
            self.assertGreater(len(res["citations"]), 0)

    # =========================================================================
    # TC-RAG-07: "Give the source document and page number for the overburden removal figures."
    # =========================================================================
    def test_tc_rag_07_source_doc_and_page_number_citations(self):
        """TC-RAG-07: Grounded inquiry asking for source document and page number provides verified citations."""
        query = "Give the source document and page number for the overburden removal figures."
        intent = classify_query_intent(query)
        self.assertEqual(intent, "EVIDENCE_GROUNDED")

        res = execute_rag_query(self.db, query, top_k=5)
        self.assertEqual(res["mode"], "EVIDENCE_GROUNDED")
        self.assertGreater(len(res["citations"]), 0)
        for c in res["citations"]:
            self.assertTrue(any(c["document_name"].endswith(ext) for ext in [".pdf", ".csv", ".xlsx"]))
            self.assertGreaterEqual(c["page_number"], 1)

    # =========================================================================
    # TC-RAG-08: "What is opencast mining?"
    # =========================================================================
    def test_tc_rag_08_what_is_opencast_mining_general_ai(self):
        """TC-RAG-08: Pure conceptual question must route to GENERAL_AI with no document retrieval."""
        query = "What is opencast mining?"
        intent = classify_query_intent(query)
        self.assertEqual(intent, "GENERAL_AI", f"Expected GENERAL_AI for conceptual query, got {intent}")

        res = execute_rag_query(self.db, query, top_k=5)
        self.assertEqual(res["mode"], "GENERAL_AI")
        self.assertEqual(len(res["citations"]), 0, "GENERAL_AI queries must never have fake citations.")
        self.assertIn("opencast", res["answer"].lower())

    # =========================================================================
    # TC-RAG-09: "What is overburden?"
    # =========================================================================
    def test_tc_rag_09_what_is_overburden_general_ai(self):
        """TC-RAG-09: Pure conceptual definition of overburden must route to GENERAL_AI."""
        query = "What is overburden?"
        intent = classify_query_intent(query)
        self.assertEqual(intent, "GENERAL_AI", f"Expected GENERAL_AI for conceptual query, got {intent}")

        res = execute_rag_query(self.db, query, top_k=5)
        self.assertEqual(res["mode"], "GENERAL_AI")
        self.assertEqual(len(res["citations"]), 0)
        self.assertIn("overburden", res["answer"].lower())

    # =========================================================================
    # TC-RAG-10: "What was production in an unindexed mine XYZ?"
    # =========================================================================
    def test_tc_rag_10_unindexed_mine_xyz_insufficient_evidence(self):
        """TC-RAG-10: Query targeting unindexed mine XYZ must return safe insufficient-evidence refusal without hallucination."""
        query = "What was production in an unindexed mine XYZ?"

        # 1. Entity parsing check
        entities = detect_query_entities(query)
        self.assertIn("XYZ", entities["mines"])

        # 2. Intent check
        intent = classify_query_intent(query)
        self.assertEqual(intent, "EVIDENCE_GROUNDED")

        # 3. Execution check: Authority Gate must reject unindexed entity
        res = execute_rag_query(self.db, query, top_k=5)
        self.assertEqual(res["mode"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(len(res["citations"]), 0)
        self.assertIn("Insufficient evidence found for this query", res["answer"])
        self.assertIn("XYZ", res["answer"])
        # No hallucination of fake production numbers
        self.assertNotIn("42.50 MT", res["answer"])
        self.assertNotIn("85.76 MT", res["answer"])


if __name__ == "__main__":
    unittest.main()
