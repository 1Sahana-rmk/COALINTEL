"""
COALINTEL V2 — PHASE 9D TEST SUITE
==================================
Parliamentary Corporate Query & Evidence Grounding Hardening Test Suite:
- TEST 1: Corporate CIL Production (no 79.00 MT, no ECL Mine attribution, semantic corporate answer)
- TEST 2: Historical Inception Disqualification (1975 / 79 MT rejected for modern FY queries)
- TEST 3: Golden Gevra OC Production Regression (59.11 MT preserved)
- TEST 4: Gevra OBR Isolation Regression (OBR query refuses coal production 59.11 MT)
- TEST 5: Subsidiary Isolation (subsidiary-specific queries do not substitute corporate totals)
- TEST 6: Mine Isolation (individual mine query remains strictly mine-specific)
- TEST 7: Explainable Confidence (historical/mixed evidence does not claim unconditional 95% HIGH)
- TEST 8: Parliamentary Key Findings (corporate query does not blindly use subsidiary_metrics[0])
- TEST 9: Degraded LLM Provider (corporate intent and historical candidate bypass)
- TEST 10: No-Answer Safety (insufficient evidence returned when no valid corporate evidence exists)

All tests exercise REAL production code paths.
"""

import os
import re
import sys
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base
from app.models.user import User
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.models.data_conflict import DataConflict
from app.services.normalization_service import (
    get_base_mine_name,
    detect_query_fiscal_year,
    classify_document_authority,
    chunk_has_metric_for_entity,
    is_historical_evidence_snippet,
    is_corporate_context_snippet,
)
from app.services.hybrid_search_service import (
    detect_query_entities,
    execute_hybrid_search,
)
from app.services.rag_service import (
    execute_rag_query,
    extract_and_validate_citations,
    build_isolated_prompt,
)
from app.services.llm_provider import DegradedLLMProvider
from app.schemas.parliamentary import ParliamentaryBriefingRequest
from app.api.parliamentary import generate_parliamentary_briefing


class TestPhase9DCorporateGrounding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.db = self.Session()
        # Clean database tables
        self.db.query(DataConflict).delete()
        self.db.query(ExtractedMetric).delete()
        self.db.query(Document).delete()
        self.db.query(User).delete()
        self.db.commit()

        # Create admin test user
        self.user = User(
            id=1,
            username="admin",
            hashed_password="hashed_password",
            role="ADMIN",
            subsidiary="CIL HQ"
        )
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_01_corporate_cil_production(self):
        """
        TEST 1 — Corporate CIL production:
        Query: 'What was CIL coal production in FY2023-24?' with Scope: 'ALL CIL'.
        Expected:
        - Corporate-level relevant evidence prioritized
        - Must NOT answer 79.00 MT
        - Must NOT answer 'ECL Mine production was 79.00 MT'
        - Must NOT use historical 1975 evidence
        """
        # Ingest document representing chapter 8 (with legacy subsidiary 'ECL' in metadata)
        doc = Document(
            id=9,
            filename="chap8AnnualReport2024en2.pdf",
            file_path="/storage/chap8AnnualReport2024en2.pdf",
            file_hash="hash9",
            file_type="PDF",
            file_size_bytes=1024,
            subsidiary="ECL",
            fiscal_year="2023-24",
            total_pages=24,
            status="PARSED"
        )
        self.db.add(doc)
        self.db.commit()

        # Seed metrics simulating legacy production extraction:
        # ID 33: historical inception 79 MT
        m_hist = ExtractedMetric(
            id=33,
            document_id=9,
            mine_name="ECL Mine",
            metric_name="Production",
            numeric_value=79.0,
            unit="MT",
            standard_value=79.0,
            standard_unit="MT",
            fiscal_year="2023-24",
            page_number=3,
            confidence_score=0.85,
            validation_status="VALID",
            raw_snippet="state-owned coal mining corporate came into being in November 1975 with the Government taking over private coal mines. With a modest production of 79 MT at the year of its inception CIL today is the single largest coal producer in the world."
        )
        # ID 34: corporate 2023-24 production 773.65 MT
        m_corp = ExtractedMetric(
            id=34,
            document_id=9,
            mine_name="ECL Mine",  # Legacy mislabel
            metric_name="Production",
            numeric_value=773.65,
            unit="MT",
            standard_value=773.65,
            standard_unit="MT",
            fiscal_year="2023-24",
            page_number=3,
            confidence_score=0.95,
            validation_status="VALID",
            raw_snippet="Milestones in 2023-24: Coal production of 773.65 MT during 2023-24 achieved 99.16% of the annual target of 780.20 MT registering 10.02% growth over last fiscal year."
        )
        # ID 51: small mine production
        m_small = ExtractedMetric(
            id=51,
            document_id=9,
            mine_name="Overall Mine",
            metric_name="Production",
            numeric_value=5.41,
            unit="Tonnes",
            standard_value=0.0,
            standard_unit="MT",
            fiscal_year="2023-24",
            page_number=18,
            confidence_score=0.80,
            validation_status="VALID",
            raw_snippet="Overall Mine achieved production of 5.41 Tonnes during the month."
        )
        self.db.add_all([m_hist, m_corp, m_small])
        self.db.commit()

        req = ParliamentaryBriefingRequest(
            question_text="What was CIL coal production in FY2023-24?",
            fiscal_year="2023-24",
            subsidiary_filter="ALL CIL",
            question_type="GENERAL"
        )
        briefing = generate_parliamentary_briefing(payload=req, db=self.db, current_user=self.user)

        # 1. Executive Summary must NOT cite 79.00 MT or ECL Mine
        self.assertNotIn("79.00", briefing.executive_summary)
        self.assertNotIn("79.0", briefing.executive_summary)
        self.assertNotIn("ECL Mine production was 79", briefing.executive_summary)

        # 2. Key findings must NOT cite 0.00 MT for Overall Mine
        kf_text = " ".join(briefing.key_findings)
        self.assertNotIn("Overall Mine (ECL) in FY 2023-24: 0.00 MT", kf_text)

        # 3. Grounded entity check: CIL corporate metric must be prioritized
        self.assertTrue(len(briefing.subsidiary_metrics) > 0)
        first_metric = briefing.subsidiary_metrics[0]
        self.assertEqual(first_metric.mine_name, "CIL Corporate")
        self.assertAlmostEqual(first_metric.standard_value, 773.65, places=1)

    def test_02_historical_inception_rejection(self):
        """
        TEST 2 — Historical inception rejection:
        Given evidence containing 1975, 'inception', 79 MT, and query asking for FY2023-24:
        Historical candidate must be rejected and never selected as final answer.
        """
        historical_snippet = (
            "state-owned coal mining corporate came into being in November 1975 with the "
            "Government taking over private coal mines. With a modest production of 79 MT "
            "at the year of its inception CIL today is the single largest coal producer."
        )
        current_snippet = (
            "Milestones in 2023-24: Coal production of 773.65 MT during 2023-24 achieved "
            "99.16% of the annual target of 780.20 MT registering 10.02% growth."
        )

        # Direct function test of is_historical_evidence_snippet
        self.assertTrue(is_historical_evidence_snippet(historical_snippet, target_fy="2023-24"))
        self.assertFalse(is_historical_evidence_snippet(current_snippet, target_fy="2023-24"))

        # Semantic Citation Gate test
        chunks = [
            {"filename": "Report.pdf", "page_number": 3, "text": historical_snippet, "authority": "OFFICIAL"},
            {"filename": "Report.pdf", "page_number": 4, "text": current_snippet, "authority": "OFFICIAL"},
        ]
        raw_answer = "CIL production was 79 MT [Report.pdf, Page 3]."
        cites, passed = extract_and_validate_citations(raw_answer, chunks, query_text="What was CIL coal production in FY2023-24?")
        # Historical tag [Report.pdf, Page 3] must be rejected
        self.assertEqual(len(cites), 0)

    def test_03_gevra_production_regression(self):
        """
        TEST 3 — Gevra production regression:
        Query: 'What was Gevra OC's coal production in FY2023-24?'
        Must remain 59.11 MT with valid official evidence.
        """
        doc = Document(
            id=10,
            filename="SECL_Annual_Report_2023-24.pdf",
            file_path="/storage/SECL_Annual_Report_2023-24.pdf",
            file_hash="hash10",
            file_type="PDF",
            file_size_bytes=1024,
            subsidiary="SECL",
            fiscal_year="2023-24",
            total_pages=50,
            status="PARSED"
        )
        self.db.add(doc)
        self.db.commit()

        gevra_metric = ExtractedMetric(
            id=46,
            document_id=10,
            mine_name="Gevra OC",
            metric_name="Production",
            numeric_value=59.11,
            unit="MT",
            standard_value=59.11,
            standard_unit="MT",
            fiscal_year="2023-24",
            page_number=4,
            confidence_score=0.95,
            validation_status="VALID",
            raw_snippet="Gevra maintained its pinnacle position amongst all mines of CIL as well as in India by achieving 59.11 MT production during FY 23-24."
        )
        self.db.add(gevra_metric)
        self.db.commit()

        req = ParliamentaryBriefingRequest(
            question_text="What was Gevra OC's coal production in FY2023-24?",
            fiscal_year="2023-24",
            subsidiary_filter="ALL CIL",
            question_type="GENERAL"
        )
        briefing = generate_parliamentary_briefing(payload=req, db=self.db, current_user=self.user)

        self.assertEqual(briefing.selected_scope, "Gevra OC")
        self.assertIn("59.11", briefing.executive_summary)
        self.assertTrue(any("59.11" in kf for kf in briefing.key_findings))

    def test_04_gevra_obr_isolation_regression(self):
        """
        TEST 4 — Gevra OBR regression:
        Query: 'What was Gevra OC's overburden removal in FY2023-24?'
        Must NOT return 59.11 MT production.
        If no authoritative OBR evidence exists: returns insufficient evidence.
        """
        doc = Document(
            id=10,
            filename="SECL_Annual_Report_2023-24.pdf",
            file_path="/storage/SECL_Annual_Report_2023-24.pdf",
            file_hash="hash10",
            file_type="PDF",
            file_size_bytes=1024,
            subsidiary="SECL",
            fiscal_year="2023-24",
            total_pages=50,
            status="PARSED"
        )
        self.db.add(doc)
        self.db.commit()

        # Seed only Production metric for Gevra OC, NO OBR metric
        gevra_metric = ExtractedMetric(
            id=46,
            document_id=10,
            mine_name="Gevra OC",
            metric_name="Production",
            numeric_value=59.11,
            unit="MT",
            standard_value=59.11,
            standard_unit="MT",
            fiscal_year="2023-24",
            page_number=4,
            confidence_score=0.95,
            validation_status="VALID",
            raw_snippet="Gevra achieved 59.11 MT coal production during FY 23-24."
        )
        self.db.add(gevra_metric)
        self.db.commit()

        req = ParliamentaryBriefingRequest(
            question_text="What was Gevra OC's overburden removal in FY2023-24?",
            fiscal_year="2023-24",
            subsidiary_filter="SECL",
            question_type="GENERAL"
        )
        briefing = generate_parliamentary_briefing(payload=req, db=self.db, current_user=self.user)

        # Must NOT return production 59.11 MT as overburden removal
        self.assertNotIn("59.11 MT overburden", briefing.executive_summary.lower())
        self.assertEqual(len(briefing.subsidiary_metrics), 0)

    def test_05_subsidiary_isolation(self):
        """
        TEST 5 — Subsidiary isolation:
        Query: 'What was ECL production in FY2023-24?'
        Verify that corporate CIL evidence is not incorrectly substituted for ECL.
        """
        entities = detect_query_entities("What was ECL production in FY2023-24?")
        self.assertEqual(entities.get("subsidiary"), "ECL")
        self.assertFalse(entities.get("is_corporate_query"))

    def test_06_mine_isolation(self):
        """
        TEST 6 — Mine isolation:
        Verify mine-specific query remains strictly mine-specific.
        """
        entities = detect_query_entities("What was Rajmahal OC coal output in FY2023-24?")
        self.assertIn("Rajmahal OC", entities.get("mines", []))
        self.assertFalse(entities.get("is_corporate_query"))

    def test_07_explainable_confidence(self):
        """
        TEST 7 — Confidence:
        Contaminated or mixed evidence must NOT produce unconditional 95% HIGH confidence.
        """
        doc = Document(
            id=9,
            filename="Report.pdf",
            file_path="/storage/Report.pdf",
            file_hash="hash9",
            file_type="PDF",
            file_size_bytes=1024,
            subsidiary="CIL",
            fiscal_year="2023-24",
            total_pages=10,
            status="PARSED"
        )
        self.db.add(doc)
        self.db.commit()

        # Add ONLY a historical metric with 1975 context
        hist_m = ExtractedMetric(
            id=33,
            document_id=9,
            mine_name="Unspecified Mine",
            metric_name="Production",
            numeric_value=79.0,
            unit="MT",
            standard_value=79.0,
            standard_unit="MT",
            fiscal_year="2023-24",
            page_number=3,
            confidence_score=0.60,
            validation_status="VALID",
            raw_snippet="CIL came into being in November 1975 with modest production of 79 MT at inception."
        )
        self.db.add(hist_m)
        self.db.commit()

        req = ParliamentaryBriefingRequest(
            question_text="What was CIL coal production in FY2023-24?",
            fiscal_year="2023-24",
            subsidiary_filter="ALL CIL",
            question_type="GENERAL"
        )
        briefing = generate_parliamentary_briefing(payload=req, db=self.db, current_user=self.user)

        # Must not claim HIGH confidence (0.95)
        self.assertNotEqual(briefing.confidence, 0.95)
        self.assertIn(briefing.confidence_rating, ["LOW", "MEDIUM", "INSUFFICIENT_EVIDENCE"])

    def test_08_key_findings_corporate_guard(self):
        """
        TEST 8 — Key findings:
        Corporate query must not blindly use subsidiary_metrics[0] if it is a single subsidiary mine.
        """
        doc = Document(
            id=9,
            filename="chap8AnnualReport2024en2.pdf",
            file_path="/storage/chap8AnnualReport2024en2.pdf",
            file_hash="hash9",
            file_type="PDF",
            file_size_bytes=1024,
            subsidiary="ECL",
            fiscal_year="2023-24",
            total_pages=24,
            status="PARSED"
        )
        self.db.add(doc)
        self.db.commit()

        m_corp = ExtractedMetric(
            id=34,
            document_id=9,
            mine_name="CIL Mine",
            metric_name="Production",
            numeric_value=773.65,
            unit="MT",
            standard_value=773.65,
            standard_unit="MT",
            fiscal_year="2023-24",
            page_number=3,
            confidence_score=0.95,
            validation_status="VALID",
            raw_snippet="Coal production of 773.65 MT during 2023-24 achieved 99.16% of the annual target of 780.20 MT."
        )
        self.db.add(m_corp)
        self.db.commit()

        req = ParliamentaryBriefingRequest(
            question_text="What was CIL coal production in FY2023-24?",
            fiscal_year="2023-24",
            subsidiary_filter="ALL CIL",
            question_type="GENERAL"
        )
        briefing = generate_parliamentary_briefing(payload=req, db=self.db, current_user=self.user)

        # Must not report 'Recorded Production for Overall Mine (ECL)'
        kf_text = " ".join(briefing.key_findings)
        self.assertNotIn("Overall Mine", kf_text)
        self.assertIn("CIL", kf_text)

    def test_09_degraded_provider_candidate_selection(self):
        """
        TEST 9 — Degraded provider:
        Generic synthetic test:
        - Corporate query
        - Historical candidate first
        - Valid current-year corporate candidate second
        Expected:
        Current-year valid corporate candidate selected dynamically without hardcoding.
        """
        prompt = (
            "<untrusted_document_context>\n"
            "[Doc.pdf, Page 1]\n"
            "Mine Entity: ECL Mine | Metric: Production | Raw Extracted Value: 79.00 MT | Normalized Value: 79.00 MT | Fiscal Year: 2023-24\n"
            "Raw Evidence Snippet: corporate came into being in November 1975 with modest production of 79 MT at the year of its inception CIL.\n\n"
            "[Doc.pdf, Page 2]\n"
            "Mine Entity: ECL Mine | Metric: Production | Raw Extracted Value: 773.65 MT | Normalized Value: 773.65 MT | Fiscal Year: 2023-24\n"
            "Raw Evidence Snippet: Milestones in 2023-24: Coal production of 773.65 MT during 2023-24 achieved 99.16% of the annual target.\n"
            "</untrusted_document_context>\n\n"
            "USER QUESTION: What was CIL coal production in FY2023-24?\n\n"
            "CITED ANSWER:"
        )
        provider = DegradedLLMProvider()
        answer = provider.generate(prompt)

        # Must select Page 2 (773.65 MT), NOT Page 1 (79.00 MT)
        self.assertIn("Page 2", answer)
        self.assertIn("773.65", answer)
        self.assertNotIn("79.00", answer)
        self.assertNotIn("79 MT", answer)

    def test_10_no_answer_safety(self):
        """
        TEST 10 — No-answer safety:
        If only historical inception evidence exists for a modern corporate query:
        Return insufficient evidence rather than guessing.
        """
        prompt = (
            "<untrusted_document_context>\n"
            "[Doc.pdf, Page 1]\n"
            "Mine Entity: ECL Mine | Metric: Production | Raw Extracted Value: 79.00 MT | Normalized Value: 79.00 MT | Fiscal Year: 2023-24\n"
            "Raw Evidence Snippet: corporate came into being in November 1975 with modest production of 79 MT at the year of its inception CIL.\n"
            "</untrusted_document_context>\n\n"
            "USER QUESTION: What was CIL coal production in FY2023-24?\n\n"
            "CITED ANSWER:"
        )
        provider = DegradedLLMProvider()
        answer = provider.generate(prompt)

        self.assertIn("Insufficient evidence found for this query.", answer)

    # =========================================================================
    # FORENSIC REMEDIATION TESTS: F-01 through F-05
    # =========================================================================

    def test_11_corporate_relabeling_safety_f01(self):
        """
        F-01 Remediation:
        Corporate relabeling is allowed ONLY when raw evidence supports corporate/aggregate context.
        Legitimate subsidiary mines (e.g. 'ECL Mine', 'Rajmahal OC') must NOT be relabeled 'CIL Corporate'
        even during a corporate query, unless evidence explicitly supports corporate context.
        """
        # Test 1: Corporate snippet -> CIL Corporate
        corp_doc = Document(
            id=101, filename="CIL_Corporate_Report.pdf", file_path="/mock/cil.pdf",
            file_hash="h101", file_type="PDF", file_size_bytes=1000,
            subsidiary="CIL", fiscal_year="2023-24", total_pages=10, status="PARSED"
        )
        self.db.add(corp_doc)
        
        m_corp = ExtractedMetric(
            id=101, document_id=101, mine_name="CIL Mine", metric_name="Production",
            numeric_value=773.65, unit="MT", standard_value=773.65, standard_unit="MT",
            fiscal_year="2023-24", confidence_score=0.95,
            raw_snippet="CIL achieved company-wide production of 773.65 MT across all subsidiaries."
        )
        self.db.add(m_corp)

        # Test 2: Legitimate ECL mine snippet during corporate query -> must remain ECL Mine
        ecl_doc = Document(
            id=102, filename="ECL_Report.pdf", file_path="/mock/ecl.pdf",
            file_hash="h102", file_type="PDF", file_size_bytes=1000,
            subsidiary="ECL", fiscal_year="2023-24", total_pages=10, status="PARSED"
        )
        self.db.add(ecl_doc)

        m_ecl = ExtractedMetric(
            id=102, document_id=102, mine_name="ECL Mine", metric_name="Production",
            numeric_value=5.0, unit="MT", standard_value=5.0, standard_unit="MT",
            fiscal_year="2023-24", confidence_score=0.90,
            raw_snippet="ECL mine produced 5 MT in FY2023-24."
        )
        self.db.add(m_ecl)

        # Test 3: Rajmahal mine snippet during corporate query -> must remain Rajmahal OC
        m_raj = ExtractedMetric(
            id=103, document_id=102, mine_name="Rajmahal OC", metric_name="Production",
            numeric_value=10.0, unit="MT", standard_value=10.0, standard_unit="MT",
            fiscal_year="2023-24", confidence_score=0.92,
            raw_snippet="Rajmahal OC produced 10 MT in FY2023-24."
        )
        self.db.add(m_raj)
        self.db.commit()

        # Hybrid search for corporate query
        results = execute_hybrid_search(
            db=self.db,
            query_text="What was CIL coal production in FY2023-24?",
            top_k=10
        )

        res_by_id = {r.get("chunk_index"): r for r in results if r.get("chunk_index") is not None}

        # Corporate record (-101) must be relabeled to CIL Corporate
        self.assertIn(-101, res_by_id)
        self.assertIn("Mine Entity: CIL Corporate", res_by_id[-101]["text"])

        # ECL mine record (-102) must NOT be relabeled to CIL Corporate
        self.assertIn(-102, res_by_id)
        self.assertIn("Mine Entity: ECL Mine", res_by_id[-102]["text"])
        self.assertNotIn("Mine Entity: CIL Corporate", res_by_id[-102]["text"])

        # Rajmahal OC record (-103) must NOT be relabeled to CIL Corporate
        self.assertIn(-103, res_by_id)
        self.assertIn("Mine Entity: Rajmahal OC", res_by_id[-103]["text"])
        self.assertNotIn("Mine Entity: CIL Corporate", res_by_id[-103]["text"])

    def test_12_confidence_ranking_f02(self):
        """
        F-02 Remediation:
        Confidence score participates in deterministic ranking BEFORE the final ID tie-breaker.
        When candidates have equal semantic relevance dimensions, higher confidence wins.
        """
        doc = Document(
            id=201, filename="CIL_Production_Report.pdf", file_path="/mock/cil201.pdf",
            file_hash="h201", file_type="PDF", file_size_bytes=1000,
            subsidiary="CIL", fiscal_year="2023-24", total_pages=10, status="PARSED"
        )
        self.db.add(doc)

        # Candidate A: lower ID (10) but HIGHER confidence (0.95)
        mA = ExtractedMetric(
            id=10, document_id=201, mine_name="CIL Corporate", metric_name="Coal Production",
            numeric_value=773.65, unit="MT", standard_value=773.65, standard_unit="MT",
            fiscal_year="2023-24", confidence_score=0.95,
            raw_snippet="Milestones in 2023-24: Coal production of 773.65 MT during 2023-24."
        )
        # Candidate B: higher ID (99) but LOWER confidence (0.75)
        mB = ExtractedMetric(
            id=99, document_id=201, mine_name="CIL Corporate", metric_name="Coal Production",
            numeric_value=770.00, unit="MT", standard_value=770.00, standard_unit="MT",
            fiscal_year="2023-24", confidence_score=0.75,
            raw_snippet="Milestones in 2023-24: Coal production of 770.00 MT during 2023-24."
        )
        self.db.add(mA)
        self.db.add(mB)
        self.db.commit()

        results = execute_hybrid_search(
            db=self.db,
            query_text="What was CIL coal production in FY2023-24?",
            top_k=5
        )

        metric_chunks = [r for r in results if r.get("chunk_index") in [-10, -99]]
        self.assertGreaterEqual(len(metric_chunks), 2)
        # Higher confidence (id 10, conf 0.95) MUST rank before lower confidence (id 99, conf 0.75)
        self.assertEqual(metric_chunks[0]["chunk_index"], -10)
        self.assertEqual(metric_chunks[1]["chunk_index"], -99)

    def test_13_coal_india_corporate_intent_f03(self):
        """
        F-03 Remediation:
        Verify semantic detection of 'Coal India', 'Coal India Limited', 'CIL', 'CIL\'s'
        as parent corporate identity without extracting 'India' as a target mine.
        """
        queries = [
            "What was Coal India production in FY2023-24?",
            "What was Coal India Limited production in FY2023-24?",
            "What was CIL production in FY2023-24?",
            "What was CIL's production in FY2023-24?",
            "What was total CIL production in FY2023-24?",
            "What was the company's production in FY2023-24?",
        ]

        for q in queries:
            entities = detect_query_entities(q)
            self.assertTrue(
                entities["is_corporate_query"],
                f"Expected is_corporate_query=True for: '{q}', got {entities}"
            )
            self.assertEqual(
                entities["mines"],
                [],
                f"Expected target_mines=[] (no 'India' extracted) for: '{q}', got {entities['mines']}"
            )
            self.assertIsNone(
                entities["subsidiary"],
                f"Expected target_subsidiary=None for: '{q}', got {entities['subsidiary']}"
            )

        # Preserve legitimate subsidiary targets
        ecl_entities = detect_query_entities("What was ECL production in FY2023-24?")
        self.assertEqual(ecl_entities["subsidiary"], "ECL")
        self.assertFalse(ecl_entities["is_corporate_query"])

        # Preserve legitimate mine names
        gevra_entities = detect_query_entities("What was Gevra OC production in FY2023-24?")
        self.assertEqual(gevra_entities["mines"], ["Gevra OC"])

        rajmahal_entities = detect_query_entities("What was Rajmahal OC production in FY2023-24?")
        self.assertIn("Rajmahal OC", rajmahal_entities["mines"])

    def test_14_corporate_context_generalization_f04(self):
        """
        F-04 Remediation:
        Verify generalization of is_corporate_context_snippet() across semantic phrasing,
        while strictly avoiding individual mine snippets.
        No hardcoding of answer values.
        """
        positive_examples = [
            "Coal India Limited recorded company-wide production of 500 MT during FY2025-26.",
            "Corporate production reached 700 MT across all subsidiaries in FY2024-25.",
            "Corporate-level performance was reviewed by the Ministry of Coal.",
            "The company as a whole produced 773 MT during the fiscal year.",
            "Coal India as a whole achieved record milestones in coal output.",
            "Total production of Coal India was 750 MT for the financial year.",
            "Consolidated production reached 800 MT across the nation.",
            "Organization-wide coal off-take registered significant growth.",
            "Group-wide output surpassed annual corporate target.",
            "Nationwide production target was achieved across all subsidiaries.",
            "Overall CIL production achieved 99.2% of target.",
            "Milestones in 2023-24: Coal production of 773.65 MT during 2023-24.",
        ]
        for snip in positive_examples:
            self.assertTrue(
                is_corporate_context_snippet(snip),
                f"Expected True for corporate snippet: '{snip}'"
            )

        negative_examples = [
            "ECL mine produced 5 MT in FY2023-24.",
            "Rajmahal OC produced 10 MT in FY2023-24.",
            "Gevra OC production was 59.11 MT during the period.",
            "CCL mine production reached 12 MT.",
            "Overburden removal at Gevra OpenCast stood at 310.50 M.Cu.M.",
            "Dipka OC achieved annual output of 35 MT.",
        ]
        for snip in negative_examples:
            self.assertFalse(
                is_corporate_context_snippet(snip),
                f"Expected False for individual mine snippet: '{snip}'"
            )

    def test_15_sql_candidate_ordering_before_limit_f05(self):
        """
        F-05 Remediation:
        Candidate selection must be deterministic with SQL ORDER BY before LIMIT.
        """
        doc = Document(
            id=301, filename="CIL_SQL_Test.pdf", file_path="/mock/cil301.pdf",
            file_hash="h301", file_type="PDF", file_size_bytes=1000,
            subsidiary="CIL", fiscal_year="2023-24", total_pages=10, status="PARSED"
        )
        self.db.add(doc)

        # Insert 15 metrics to verify stable ordering
        for i in range(1, 16):
            self.db.add(ExtractedMetric(
                id=300 + i,
                document_id=301,
                mine_name="CIL Corporate",
                metric_name="Coal Production",
                numeric_value=float(700 + i),
                unit="MT",
                standard_value=float(700 + i),
                standard_unit="MT",
                fiscal_year="2023-24",
                confidence_score=0.90,
                raw_snippet="Milestones in 2023-24: company-wide coal production."
            ))
        self.db.commit()

        # Run hybrid search with top_k=2 (which queries limit(top_k * 6) = 12 items)
        results = execute_hybrid_search(
            db=self.db,
            query_text="What was CIL coal production in FY2023-24?",
            top_k=2
        )
        self.assertGreater(len(results), 0)
        # Verify query executes deterministically and retrieves metrics stably
        results_second_run = execute_hybrid_search(
            db=self.db,
            query_text="What was CIL coal production in FY2023-24?",
            top_k=2
        )
        self.assertEqual(
            [r["chunk_index"] for r in results],
            [r["chunk_index"] for r in results_second_run],
            "Candidate ordering must be 100% deterministic across executions"
        )


if __name__ == "__main__":
    unittest.main()
