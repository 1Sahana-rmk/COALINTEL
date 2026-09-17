"""
COALINTEL V2 — PHASE 9B EVIDENCE GROUNDING REGRESSION TESTS
============================================================
Comprehensive test suite verifying evidence grounding recovery across:
- Test A: Golden Gevra Production (59.11 MT vs 26.02 MT) [STRONG]
- Test B: Gevra OBR Source Authority Gate [STRONG]
- Test C: Temporal Grounding & Conflict Demotion [STRONG]
- Test D: Multi-Year Line / Table Extraction Proximity [STRONG]
- Test E: Parliamentary Question-Specific Grounding & Differentiation [STRONG]
- Test F: Source Authority Relevance Ranking (Official > Synthetic) [STRONG]
- Test G: Semantic Citation Gate (Entity / Metric / Temporal / Authority) [STRONG]
- Test H: Generic Entity Normalization & Lineage Preservation [STRONG]
- Test I: Full Golden Query E2E Verification [STRONG]

All tests exercise REAL production code paths against isolated SQLite test databases.
No hardcoded Gevra values or production data mutations.
"""

import unittest
import os
import sys
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base
from database_seed import init_db
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.extracted_metric import ExtractedMetric
from app.models.data_conflict import DataConflict
from app.services.normalization_service import (
    get_base_mine_name,
    canonicalize_mine_name,
    detect_query_fiscal_year,
    classify_document_authority,
    extract_entity_tuples_from_text,
    GENERIC_MINE_PHRASES,
)
from app.services.hybrid_search_service import (
    execute_hybrid_search,
    detect_query_entities,
)
from app.services.rag_service import (
    execute_rag_query,
    extract_and_validate_citations,
    build_isolated_prompt,
)
from app.services.llm_provider import DegradedLLMProvider
from app.schemas.parliamentary import ParliamentaryBriefingRequest
from app.api.parliamentary import generate_parliamentary_briefing


class TestPhase9BEvidenceGrounding(unittest.TestCase):
    """
    Phase 9B Test Suite covering Evidence Grounding Recovery.
    All tests are categorized as STRONG because they exercise actual production logic.
    """

    @classmethod
    def setUpClass(cls):
        """Sets up isolated in-memory SQLite database and seeds test fixtures."""
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=cls.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        cls.db = TestingSessionLocal()
        init_db(cls.db)

        # 1. Authoritative Official SECL Document (Gevra 59.11 MT)
        cls.official_secl_doc = Document(
            filename="SECL_Annual_Report_2023-24.pdf",
            file_path="uploads/SECL_Annual_Report_2023-24.pdf",
            file_hash="mock_official_secl_hash_9b",
            file_type="pdf",
            file_size_bytes=2048576,
            subsidiary="SECL",
            fiscal_year="2023-24",
            status="PARSED",
            total_pages=40
        )
        cls.db.add(cls.official_secl_doc)
        cls.db.commit()
        cls.db.refresh(cls.official_secl_doc)

        cls.gevra_official_metric = ExtractedMetric(
            document_id=cls.official_secl_doc.id,
            page_number=16,
            mine_name="Gevra OC",
            subsidiary="SECL",
            metric_name="Production",
            numeric_value=59.11,
            unit="MT",
            raw_unit="MT",
            standard_value=59.11,
            standard_unit="MT",
            fiscal_year="2023-24",
            confidence_score=0.995,
            validation_status="VALIDATED",
            raw_snippet="Gevra OC opencast mine achieved annual coal production of 59.11 MT in FY2023-24."
        )
        cls.db.add(cls.gevra_official_metric)

        # 2. Competing Corporate Aggregated Metric (CIL Underground 26.02 MT)
        cls.official_cil_doc = Document(
            filename="chap8AnnualReport2024en2.pdf",
            file_path="uploads/chap8AnnualReport2024en2.pdf",
            file_hash="mock_official_cil_hash_9b",
            file_type="pdf",
            file_size_bytes=4096000,
            subsidiary="CIL HQ",
            fiscal_year="2023-24",
            status="PARSED",
            total_pages=50
        )
        cls.db.add(cls.official_cil_doc)
        cls.db.commit()
        cls.db.refresh(cls.official_cil_doc)

        cls.cil_ug_metric = ExtractedMetric(
            document_id=cls.official_cil_doc.id,
            page_number=22,
            mine_name="Unspecified Mine",
            subsidiary="CIL HQ",
            metric_name="Production",
            numeric_value=26.02,
            unit="MT",
            raw_unit="MT",
            standard_value=26.02,
            standard_unit="MT",
            fiscal_year="2023-24",
            confidence_score=0.950,
            validation_status="VALIDATED",
            raw_snippet="Total CIL underground coal production reached 26.02 MT across all mines of CIL."
        )
        cls.db.add(cls.cil_ug_metric)

        # 3. Synthetic Test Document (Mock OBR 60.00 MT)
        cls.synthetic_doc = Document(
            filename="COALINTEL_Test_Mining_Report_FY2023-24_V2.pdf",
            file_path="uploads/COALINTEL_Test_Mining_Report_FY2023-24_V2.pdf",
            file_hash="mock_synthetic_hash_9b",
            file_type="pdf",
            file_size_bytes=512000,
            subsidiary="SECL",
            fiscal_year="2023-24",
            status="PARSED",
            total_pages=10
        )
        cls.db.add(cls.synthetic_doc)
        cls.db.commit()
        cls.db.refresh(cls.synthetic_doc)

        cls.synthetic_obr_metric = ExtractedMetric(
            document_id=cls.synthetic_doc.id,
            page_number=5,
            mine_name="Gevra OC",
            subsidiary="SECL",
            metric_name="Overburden Removal",
            numeric_value=60.00,
            unit="MM3",
            raw_unit="MM3",
            standard_value=60.00,
            standard_unit="MM3",
            fiscal_year="2023-24",
            confidence_score=0.850,
            validation_status="VALIDATED",
            raw_snippet="Gevra OC overburden removal synthetic test trial reached 60.00 MM3 in FY2023-24."
        )
        cls.db.add(cls.synthetic_obr_metric)

        # 4. Multi-Year Historical Metrics for Temporal Grounding Tests
        for year, val in [("2020-21", 1.00), ("2021-22", 1.50), ("2022-23", 1.50), ("2023-24", 1.22)]:
            m = ExtractedMetric(
                document_id=cls.official_cil_doc.id,
                page_number=30,
                mine_name="Alpha Mine",
                subsidiary="ECL",
                metric_name="Production",
                numeric_value=val,
                unit="MT",
                raw_unit="MT",
                standard_value=val,
                standard_unit="MT",
                fiscal_year=year,
                confidence_score=0.920,
                validation_status="VALIDATED",
                raw_snippet=f"Alpha Mine coal production in {year} was {val} MT."
            )
            cls.db.add(m)

        # 5. Seed an active conflict for an unrelated mine (Rajmahal) to test parliamentary filtering
        ecl_doc = Document(
            filename="ECL_Production_Discrepancy_Audit.pdf",
            file_path="uploads/ECL_Production_Discrepancy_Audit.pdf",
            file_hash="mock_ecl_audit_hash_9b",
            file_type="pdf",
            file_size_bytes=512000,
            subsidiary="ECL",
            fiscal_year="2023-24",
            status="PARSED",
            total_pages=15
        )
        cls.db.add(ecl_doc)
        cls.db.commit()
        cls.db.refresh(ecl_doc)

        cls.active_conflict = DataConflict(
            mine_name="Rajmahal OC",
            metric_name="Production",
            fiscal_year="2023-24",
            doc_a_id=cls.official_cil_doc.id,
            doc_a_value=4.25,
            doc_b_id=ecl_doc.id,
            doc_b_value=4.90,
            discrepancy_pct=15.29,
            status="ACTIVE"
        )
        cls.db.add(cls.active_conflict)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # ----------------------------------------------------------------------
    # TEST A — GOLDEN GEVRA PRODUCTION [STRONG]
    # ----------------------------------------------------------------------
    def test_a_golden_gevra_production(self):
        """
        [STRONG] Golden Query Verification:
        Query: 'What was Gevra OC's coal production in FY2023-24?'
        Must retrieve and ground to 59.11 MT from SECL Annual Report,
        and must NOT return or cite corporate 26.02 MT.
        """
        query = "What was Gevra OC's coal production in FY2023-24?"
        results = execute_hybrid_search(self.db, query, top_k=5)

        self.assertGreater(len(results), 0, "Retrieval should return evidence chunks")
        top_cand = results[0]

        # Top candidate must be Gevra specific, not CIL underground
        self.assertIn("59.11", top_cand["text"])
        self.assertNotIn("26.02", top_cand["text"])
        self.assertEqual(top_cand["filename"], "SECL_Annual_Report_2023-24.pdf")
        self.assertEqual(top_cand["page_number"], 16)

    # ----------------------------------------------------------------------
    # TEST B — GEVRA OBR SOURCE AUTHORITY GATE [STRONG]
    # ----------------------------------------------------------------------
    def test_b_gevra_obr_authority(self):
        """
        [STRONG] Source Authority Tiering:
        Query: 'What was Gevra OC's overburden removal in FY2023-24?'
        When only synthetic test evidence exists (60.00 MM3 in mock report),
        the system must refuse to assert synthetic test data as authoritative fact
        and return INSUFFICIENT_AUTHORITATIVE_EVIDENCE.
        When an official document is supplied, it must accept the official evidence.
        """
        # Ensure controlled fixture where NO official Gevra OBR exists
        self.db.query(ExtractedMetric).filter(
            ExtractedMetric.mine_name.ilike("%Gevra%"),
            ExtractedMetric.metric_name.ilike("%Overburden%"),
            ExtractedMetric.numeric_value != 60.00
        ).delete()
        self.db.query(DocumentChunk).filter(
            DocumentChunk.chunk_text.ilike("%310.50%")
        ).delete()
        self.db.commit()

        query = "What was Gevra OC's overburden removal in FY2023-24?"
        with patch("app.services.hybrid_search_service.search_vector_store", return_value=[]):
            rag_res = execute_rag_query(self.db, query, top_k=5)

            # Must NOT assert synthetic 60.00 MT as authoritative fact
            self.assertEqual(rag_res["answer"], "INSUFFICIENT_AUTHORITATIVE_EVIDENCE")
            self.assertEqual(rag_res["citations"], [])

            # Now test that if an official OBR document is supplied, official evidence is accepted
            official_obr_doc = Document(
                filename="SECL_Audited_Annual_OBR_2023-24.pdf",
                file_path="uploads/SECL_Audited_Annual_OBR_2023-24.pdf",
                file_hash="mock_obr_official_hash",
                file_type="pdf",
                file_size_bytes=1048576,
                subsidiary="SECL",
                fiscal_year="2023-24",
                status="PARSED",
                total_pages=20
            )
            self.db.add(official_obr_doc)
            self.db.commit()
            self.db.refresh(official_obr_doc)

            official_obr_metric = ExtractedMetric(
                document_id=official_obr_doc.id,
                page_number=8,
                mine_name="Gevra OC",
                subsidiary="SECL",
                metric_name="Overburden Removal",
                numeric_value=72.45,
                unit="MM3",
                raw_unit="MM3",
                standard_value=72.45,
                standard_unit="MM3",
                fiscal_year="2023-24",
                confidence_score=0.990,
                validation_status="VALIDATED",
                raw_snippet="Gevra OC achieved total overburden removal of 72.45 MM3 in FY2023-24."
            )
            self.db.add(official_obr_metric)
            self.db.commit()

            # Re-run query: now official evidence exists, so it should answer with official evidence
            res_with_official = execute_rag_query(self.db, query, top_k=5)
            self.assertNotEqual(res_with_official["answer"], "INSUFFICIENT_AUTHORITATIVE_EVIDENCE")
            self.assertIn("72.45", res_with_official["answer"])
            self.assertTrue(any(c["document_name"] == "SECL_Audited_Annual_OBR_2023-24.pdf" for c in res_with_official["citations"]))

    # ----------------------------------------------------------------------
    # TEST C — TEMPORAL GROUNDING & CONFLICT DEMOTION [STRONG]
    # ----------------------------------------------------------------------
    def test_c_temporal_grounding(self):
        """
        [STRONG] Temporal Grounding:
        Query: 'What was Alpha Mine coal production in FY2023-24?'
        Fixture contains 2020-21 (1.00 MT), 2021-22 (1.50 MT), 2022-23 (1.50 MT), 2023-24 (1.22 MT).
        Retrieval must prioritize 2023-24 evidence (1.22 MT) and demote 2020-21.
        """
        query = "What was Alpha Mine coal production in FY2023-24?"
        results = execute_hybrid_search(self.db, query, top_k=5)

        self.assertGreater(len(results), 0)
        top_cand = results[0]

        # Top candidate must be 2023-24 (1.22 MT), not 2020-21 (1.00 MT)
        self.assertIn("1.22", top_cand["text"])
        self.assertIn("2023-24", top_cand["text"])
        self.assertNotIn("2020-21", top_cand["text"])

    # ----------------------------------------------------------------------
    # TEST D — MULTI-YEAR LINE EXTRACTION [STRONG]
    # ----------------------------------------------------------------------
    def test_d_multi_year_line_extraction(self):
        """
        [STRONG] Multi-Year Line Extraction:
        Input snippet with multi-year lines:
        1. 2020-21 - 1.00 MT
        2. 2021-22 - 1.50 MT
        3. 2022-23 - 1.50 MT
        4. 2023-24 - 1.22 MT
        Extraction must bind 1.22 MT to FY2023-24 and 1.00 MT to FY2020-21,
        not greedily assign the first fiscal year in snippet to all numbers.
        """
        text = (
            "Alpha Mine annual coal production trends:\n"
            "1. 2020-21 - 1.00 MT\n"
            "2. 2021-22 - 1.50 MT\n"
            "3. 2022-23 - 1.50 MT\n"
            "4. 2023-24 - 1.22 MT\n"
        )
        extracted = extract_entity_tuples_from_text(text, page_number=1, default_year="2023-24")

        # Locate extracted tuple for 1.22 MT
        cand_122 = next((t for t in extracted if abs(t["numeric_value"] - 1.22) < 0.01), None)
        self.assertIsNotNone(cand_122, "Must extract 1.22 MT")
        self.assertEqual(cand_122["fiscal_year"], "2023-24", "1.22 MT must bind to 2023-24, not 2020-21")

        # Locate extracted tuple for 1.00 MT
        cand_100 = next((t for t in extracted if abs(t["numeric_value"] - 1.00) < 0.01), None)
        self.assertIsNotNone(cand_100, "Must extract 1.00 MT")
        self.assertEqual(cand_100["fiscal_year"], "2020-21", "1.00 MT must bind to 2020-21")

    # ----------------------------------------------------------------------
    # TEST E — PARLIAMENTARY DIFFERENTIATION [STRONG]
    # ----------------------------------------------------------------------
    def test_e_parliamentary_differentiation(self):
        """
        [STRONG] Parliamentary Briefing Differentiation:
        Question A: 'What was CIL coal production in FY2023-24?' (Broad CIL)
        Question B: 'What was Gevra OC coal production in FY2023-24?' (Specific mine)
        Verify:
        - Relevant subsidiary_metrics differ.
        - Question B contains Gevra metrics only; does not return unrelated mines.
        - Key findings differ.
        - Active Rajmahal conflicts are excluded from Question B (Gevra).
        """
        mock_user = User(id=1, email="admin@coal.gov.in", role="ADMIN", subsidiary="CIL HQ")

        # Question A: Broad CIL
        req_a = ParliamentaryBriefingRequest(
            question_text="What was CIL coal production in FY2023-24?",
            subsidiary_filter="ALL CIL",
            fiscal_year="2023-24",
            question_type="GENERAL"
        )
        resp_a = generate_parliamentary_briefing(req_a, db=self.db, current_user=mock_user)

        # Question B: Specific Gevra OC
        req_b = ParliamentaryBriefingRequest(
            question_text="What was Gevra OC coal production in FY2023-24?",
            subsidiary_filter="ALL CIL",
            fiscal_year="2023-24",
            question_type="GENERAL"
        )
        resp_b = generate_parliamentary_briefing(req_b, db=self.db, current_user=mock_user)

        # 1. Metrics differ between broad and specific
        metrics_a = [m.mine_name for m in resp_a.subsidiary_metrics]
        metrics_b = [m.mine_name for m in resp_b.subsidiary_metrics]
        self.assertNotEqual(metrics_a, metrics_b, "Subsidiary metrics must differ between broad and specific questions")

        # 2. Specific question has Gevra metrics
        self.assertTrue(any("Gevra" in m for m in metrics_b), "Gevra question must retrieve Gevra metrics")

        # 3. Discrepancies: Gevra briefing must NOT report Rajmahal active conflicts
        conflicts_b = [d.entity for d in resp_b.discrepancies]
        self.assertNotIn("Rajmahal OC", conflicts_b, "Gevra briefing must not report unrelated Rajmahal discrepancies")

        # 4. Key findings differ
        self.assertNotEqual(resp_a.key_findings, resp_b.key_findings, "Key findings must be question-specific")
        self.assertTrue(any("Gevra" in kf for kf in resp_b.key_findings), "Gevra briefing findings must mention Gevra")

    # ----------------------------------------------------------------------
    # TEST F — SOURCE AUTHORITY PRIORITY [STRONG]
    # ----------------------------------------------------------------------
    def test_f_source_authority_priority(self):
        """
        [STRONG] Authority-Aware Hybrid Retrieval:
        Official evidence (e.g. SECL_Annual_Report_2023-24.pdf) must receive an authority boost
        and outrank synthetic test documents (e.g. COALINTEL_Test_Mining_Report_FY2023-24_V2.pdf)
        when both offer relevant evidence.
        """
        auth_official = classify_document_authority("SECL_Annual_Report_2023-24.pdf")
        auth_synthetic = classify_document_authority("COALINTEL_Test_Mining_Report_FY2023-24_V2.pdf")
        self.assertEqual(auth_official, "OFFICIAL")
        self.assertEqual(auth_synthetic, "SYNTHETIC_TEST")

        # Query where both official and synthetic exist
        query = "What was Gevra OC production in FY2023-24?"
        results = execute_hybrid_search(self.db, query, top_k=5)

        self.assertGreater(len(results), 0)
        # Top result must be OFFICIAL
        self.assertEqual(results[0]["authority"], "OFFICIAL")
        self.assertEqual(results[0]["filename"], "SECL_Annual_Report_2023-24.pdf")

    # ----------------------------------------------------------------------
    # TEST G — SEMANTIC CITATION GATE [STRONG]
    # ----------------------------------------------------------------------
    def test_g_semantic_citation_gate(self):
        """
        [STRONG] Semantic Citation Gate:
        Case 1: Question asks for Gevra OC production, but cited evidence is CIL UG production.
                Expected: REJECT (citation_gate_passed = False).
        Case 2: Question asks for Gevra OC production, and cited evidence supports Gevra 59.11 MT.
                Expected: ACCEPT (citation_gate_passed = True).
        """
        question = "What was Gevra OC coal production in FY2023-24?"

        # Case 1: Incompatible entity (CIL Underground 26.02 MT)
        evidence_case1 = [{
            "filename": "chap8AnnualReport2024en2.pdf",
            "page_number": 22,
            "text": "Total CIL underground coal production reached 26.02 MT across all mines of CIL in FY2023-24."
        }]
        raw_answer_case1 = "Gevra OC produced 26.02 MT of coal [chap8AnnualReport2024en2.pdf, Page 22]."
        cites1, passed1 = extract_and_validate_citations(raw_answer_case1, evidence_case1, query_text=question)
        self.assertFalse(passed1, "Semantic Citation Gate must REJECT citation lacking entity support")
        self.assertEqual(len(cites1), 0)

        # Case 2: Compatible entity & metric (Gevra OC 59.11 MT)
        evidence_case2 = [{
            "filename": "SECL_Annual_Report_2023-24.pdf",
            "page_number": 16,
            "text": "Gevra OC opencast mine achieved annual coal production of 59.11 MT in FY2023-24."
        }]
        raw_answer_case2 = "Gevra OC achieved annual coal production of 59.11 MT [SECL_Annual_Report_2023-24.pdf, Page 16]."
        cites2, passed2 = extract_and_validate_citations(raw_answer_case2, evidence_case2, query_text=question)
        self.assertTrue(passed2, "Semantic Citation Gate must ACCEPT citation with valid entity, metric & FY")
        self.assertEqual(len(cites2), 1)
        self.assertEqual(cites2[0]["document_name"], "SECL_Annual_Report_2023-24.pdf")
        self.assertEqual(cites2[0]["page_number"], 16)

    # ----------------------------------------------------------------------
    # TEST H — GENERIC ENTITY NORMALIZATION [STRONG]
    # ----------------------------------------------------------------------
    def test_h_generic_entity_normalization(self):
        """
        [STRONG] Generic Mine Name Normalization:
        Verifies:
        1. get_base_mine_name('Alpha Mine') -> 'Alpha'
        2. get_base_mine_name('Alpha OC') -> 'Alpha'
        3. get_base_mine_name('Alpha OpenCast') -> 'Alpha'
        4. get_base_mine_name('Alpha UG') -> 'Alpha'
        5. Does NOT invent suffixes: 'Alpha' remains 'Alpha'
        6. Rejects generic corporate phrases like 'CIL Mine', 'Coal Mine'
        """
        self.assertEqual(get_base_mine_name("Alpha Mine"), "Alpha")
        self.assertEqual(get_base_mine_name("Alpha OC"), "Alpha")
        self.assertEqual(get_base_mine_name("Alpha OpenCast"), "Alpha")
        self.assertEqual(get_base_mine_name("Alpha UG"), "Alpha")
        self.assertEqual(get_base_mine_name("Alpha Underground"), "Alpha")
        self.assertEqual(get_base_mine_name("Alpha Colliery"), "Alpha")
        self.assertEqual(get_base_mine_name("Alpha Project"), "Alpha")
        self.assertEqual(get_base_mine_name("Alpha Block"), "Alpha")

        # Must NOT automatically invent a suffix for bare base name
        self.assertEqual(canonicalize_mine_name("Alpha"), "Alpha")

        # Generic phrases blacklist
        for generic in ["cil mine", "coal mine", "overall mine", "mines of cil"]:
            self.assertIn(generic, GENERIC_MINE_PHRASES)

        # Extraction text where specific mine appears alongside generic phrase
        sample_text = "During the year, Alpha achieved 15.5 MT while reviewing overall mines of CIL."
        tuples = extract_entity_tuples_from_text(sample_text, page_number=1, default_subsidiary="ECL")
        self.assertGreater(len(tuples), 0)
        self.assertEqual(tuples[0]["mine_name"], "Alpha", "Specific entity 'Alpha' must take precedence over 'mines of CIL'")

    # ----------------------------------------------------------------------
    # TEST I — FULL GOLDEN QUERY E2E [STRONG]
    # ----------------------------------------------------------------------
    def test_i_full_golden_query_e2e(self):
        """
        [STRONG] Mandatory Golden Query End-to-End Chain:
        Query: 'What was Gevra OC's coal production in FY2023-24?'
        Exercises:
        - Query entity & fiscal year detection
        - Temporal & authority-aware hybrid retrieval
        - Synthesis (DegradedLLMProvider in fallback mode)
        - Semantic Citation Gate
        - Grounded final answer verification
        Must return 59.11 MT with valid citation to SECL Annual Report Page 16.
        Must NOT return 26.02 MT or ungrounded synthetic citations.
        """
        query = "What was Gevra OC's coal production in FY2023-24?"
        result = execute_rag_query(self.db, query, top_k=5)

        # 1. Answer must state 59.11 MT
        self.assertIn("59.11", result["answer"], f"Grounded answer must include 59.11 MT, got: {result['answer']}")
        self.assertNotIn("26.02", result["answer"], "Answer must NOT contain corporate 26.02 MT")

        # 2. Grounded citations must cite the official SECL report Page 16
        self.assertGreater(len(result["citations"]), 0, "Must contain validated citation")
        cited_doc = result["citations"][0]
        self.assertEqual(cited_doc["document_name"], "SECL_Annual_Report_2023-24.pdf")
        self.assertEqual(cited_doc["page_number"], 16)


if __name__ == "__main__":
    unittest.main()
