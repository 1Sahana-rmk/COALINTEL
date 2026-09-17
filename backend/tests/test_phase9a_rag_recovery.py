"""
COALINTEL V2 — PHASE 9A REGRESSION TESTS
Focused test suite covering P0 RAG / AI Query recovery:
A. ALL CIL scope returns evidence across subsidiaries / normalizes cleanly.
B. Specific subsidiary scope still filters correctly.
C. Gevra query retrieves 59.11 MT from SECL Annual Report Page 16.
D. Coal Production -> Production semantic mapping works.
E. Overburden Removal does not retrieve Production.
F. RRF merges identical physical chunks (document_id, page_number, chunk_index).
G. Degraded provider does not generate [Document.pdf, Page 1] unless such evidence exists.
H. Citation Gate accepts valid citation originating from retrieved evidence.
I. Citation Gate rejects fabricated/nonexistent citations.
J. Missing scope does not force Admin/global query into CIL HQ.
"""

import unittest
import os
import sys
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import Base, get_db
from database_seed import init_db
from app.core.rbac import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.services.normalization_service import (
    normalize_subsidiary_scope,
    detect_query_metric_domain,
    METRIC_DOMAINS
)
from app.services.hybrid_search_service import (
    execute_hybrid_search,
    detect_query_entities,
    RRF_K_CONSTANT
)
from app.services.rag_service import (
    execute_rag_query,
    extract_and_validate_citations,
    build_isolated_prompt
)
from app.services.llm_provider import DegradedLLMProvider
from app.schemas.query import QueryRequest


class TestPhase9ARAGRecovery(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Sets up in-memory SQLite database seeded with domain metrics & documents."""
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=cls.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        cls.db = TestingSessionLocal()
        init_db(cls.db)

        # Ensure SECL Gevra 59.11 MT record exists for Golden Query verification
        secl_doc = cls.db.query(Document).filter(Document.filename == "SECL_Annual_Report_2023-24.pdf").first()
        if not secl_doc:
            secl_doc = Document(
                filename="SECL_Annual_Report_2023-24.pdf",
                file_path="uploads/SECL_Annual_Report_2023-24.pdf",
                file_hash="mock_secl_hash_9a",
                file_type="pdf",
                file_size_bytes=1048576,
                subsidiary="SECL",
                fiscal_year="2023-24",
                status="PARSED",
                total_pages=20
            )
            cls.db.add(secl_doc)
            cls.db.commit()
            cls.db.refresh(secl_doc)
        cls.secl_doc = secl_doc

        gevra_metric = cls.db.query(ExtractedMetric).filter(
            ExtractedMetric.document_id == secl_doc.id,
            ExtractedMetric.mine_name.ilike("%Gevra%"),
            ExtractedMetric.metric_name == "Production"
        ).first()

        if not gevra_metric:
            gevra_metric = ExtractedMetric(
                document_id=secl_doc.id,
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
                confidence_score=0.990,
                validation_status="VALIDATED",
                raw_snippet="Gevra OC achieved annual coal production of 59.11 MT in FY2023-24."
            )
            cls.db.add(gevra_metric)
            cls.db.commit()

        # Ensure ECL Document and metric exist for isolated scope testing (Task 1)
        ecl_doc = cls.db.query(Document).filter(Document.filename == "ECL_Test_Mining_Report.pdf").first()
        if not ecl_doc:
            ecl_doc = Document(
                filename="ECL_Test_Mining_Report.pdf",
                file_path="uploads/ECL_Test_Mining_Report.pdf",
                file_hash="mock_ecl_hash_9a",
                file_type="pdf",
                file_size_bytes=1048576,
                subsidiary="ECL",
                fiscal_year="2023-24",
                status="PARSED",
                total_pages=20
            )
            cls.db.add(ecl_doc)
            cls.db.commit()
            cls.db.refresh(ecl_doc)
        cls.ecl_doc = ecl_doc

        ecl_metric = cls.db.query(ExtractedMetric).filter(
            ExtractedMetric.document_id == ecl_doc.id,
            ExtractedMetric.mine_name.ilike("%Rajmahal%"),
            ExtractedMetric.metric_name == "Production"
        ).first()
        if not ecl_metric:
            ecl_metric = ExtractedMetric(
                document_id=ecl_doc.id,
                page_number=14,
                mine_name="Rajmahal OC",
                subsidiary="ECL",
                metric_name="Production",
                numeric_value=4.25,
                unit="MT",
                raw_unit="MT",
                standard_value=4.25,
                standard_unit="MT",
                fiscal_year="2023-24",
                confidence_score=0.990,
                validation_status="VALIDATED",
                raw_snippet="Rajmahal OC achieved coal production of 4.25 MT in FY2023-24."
            )
            cls.db.add(ecl_metric)
            cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # --- Test A: Scope Normalization ---
    def test_a_all_cil_scope_normalization(self):
        """BUG-01: 'ALL CIL', 'ALL', '', None must normalize to None (unrestricted global scope)."""
        self.assertIsNone(normalize_subsidiary_scope("ALL CIL"))
        self.assertIsNone(normalize_subsidiary_scope("ALL"))
        self.assertIsNone(normalize_subsidiary_scope(""))
        self.assertIsNone(normalize_subsidiary_scope("   "))
        self.assertIsNone(normalize_subsidiary_scope(None))
        self.assertIsNone(normalize_subsidiary_scope("null"))
        self.assertIsNone(normalize_subsidiary_scope("NONE"))

        # Specific subsidiary must be preserved
        self.assertEqual(normalize_subsidiary_scope("ECL"), "ECL")
        self.assertEqual(normalize_subsidiary_scope("SECL"), "SECL")
        self.assertEqual(normalize_subsidiary_scope("WCL"), "WCL")

    # --- Test B: Specific Subsidiary Scope Filtering ---
    def test_b_specific_subsidiary_scope_filters(self):
        """Explicit subsidiary filter restricts hybrid search strictly to that subsidiary."""
        def mock_vector_search(query_text, top_k=10, subsidiary_filter=None):
            all_chunks = [
                {
                    "chunk_id": None,
                    "document_id": self.ecl_doc.id,
                    "filename": self.ecl_doc.filename,
                    "page_number": 14,
                    "chunk_index": 0,
                    "text": "Rajmahal OC coal production was 4.25 MT in FY 2023-24.",
                    "vector_score": 0.90,
                    "subsidiary": "ECL"
                },
                {
                    "chunk_id": None,
                    "document_id": self.secl_doc.id,
                    "filename": self.secl_doc.filename,
                    "page_number": 16,
                    "chunk_index": 0,
                    "text": "Gevra OC coal production was 59.11 MT in FY 2023-24.",
                    "vector_score": 0.92,
                    "subsidiary": "SECL"
                }
            ]
            if subsidiary_filter:
                return [c for c in all_chunks if c.get("subsidiary") == subsidiary_filter][:top_k]
            return all_chunks[:top_k]

        with patch("app.services.hybrid_search_service.search_vector_store", side_effect=mock_vector_search):
            results = execute_hybrid_search(
                db=self.db,
                query_text="What was the coal production in FY 2023-24?",
                top_k=5,
                subsidiary_filter="ECL"
            )

        self.assertGreater(len(results), 0)
        for item in results:
            doc = self.db.query(Document).filter(Document.id == item["document_id"]).first()
            self.assertIsNotNone(doc)
            self.assertEqual(doc.subsidiary, "ECL", f"Expected ECL subsidiary, got {doc.subsidiary} for doc {doc.id}")
            self.assertNotEqual(doc.id, self.secl_doc.id, "SECL document must not appear in ECL-scoped search")

    # --- Test C: Golden Gevra RAG Query ---
    def test_c_gevra_golden_rag_query(self):
        """Golden Query: Gevra OC coal production in FY2023-24 retrieves 59.11 MT grounded in SECL report."""
        res = execute_rag_query(
            db=self.db,
            query_text="What was Gevra OC's coal production in FY2023-24?",
            top_k=5,
            subsidiary_filter="ALL CIL"
        )
        answer = res["answer"]
        self.assertIn("59.11", answer)
        self.assertTrue(len(res["citations"]) > 0)
        citation = res["citations"][0]
        self.assertEqual(citation["document_name"], "SECL_Annual_Report_2023-24.pdf")
        self.assertEqual(citation["page_number"], 16)
        self.assertIn("[SECL_Annual_Report_2023-24.pdf, Page 16]", citation["citation_tag"])

    # --- Test D: Semantic Metric Domain Mapping ---
    def test_d_semantic_metric_domain_mapping(self):
        """BUG-05: 'Coal Production' maps to 'Production' and 'Coal Output' in COAL_PRODUCTION domain."""
        dom = detect_query_metric_domain("What was Gevra OC's coal production in FY2023-24?")
        self.assertIsNotNone(dom)
        self.assertEqual(dom["domain_key"], "COAL_PRODUCTION")
        self.assertIn("Production", dom["db_metric_names"])
        self.assertIn("Coal Production", dom["db_metric_names"])
        self.assertIn("Coal Output", dom["db_metric_names"])

    # --- Test E: Metric Specificity Distinction ---
    def test_e_overburden_removal_does_not_match_production(self):
        """Specificity-first: 'overburden removal' must NOT resolve to Coal Production domain."""
        dom_obr = detect_query_metric_domain("What was Gevra OC's overburden removal?")
        self.assertIsNotNone(dom_obr)
        self.assertEqual(dom_obr["domain_key"], "OVERBURDEN_REMOVAL")
        self.assertNotIn("Production", dom_obr["db_metric_names"])

        dom_sr = detect_query_metric_domain("What was the stripping ratio for Gevra mine?")
        self.assertIsNotNone(dom_sr)
        self.assertEqual(dom_sr["domain_key"], "STRIPPING_RATIO")

        # Querying overburden removal must retrieve OBR record (310.50 M.Cu.M), not production
        res = execute_rag_query(
            db=self.db,
            query_text="What was Gevra OC's overburden removal in FY 2023-24?",
            top_k=5
        )
        self.assertIn("310.5", res["answer"])
        self.assertNotIn("59.11", res["answer"])

    # --- Test F: RRF Candidate Identity Fusion ---
    def test_f_rrf_merges_identical_physical_chunks(self):
        """BUG-06: Chunks with same (document_id, page_number, chunk_index) fuse into one candidate via execute_hybrid_search."""
        mock_vec = [{
            "chunk_id": None,
            "document_id": 9,
            "filename": "chap8AnnualReport2024en2.pdf",
            "page_number": 16,
            "chunk_index": 3,
            "text": "Gevra OC produced 59.11 MT coal in FY 2023-24.",
            "vector_score": 0.88
        }]
        mock_kw = [{
            "chunk_id": 646,
            "document_id": 9,
            "filename": "chap8AnnualReport2024en2.pdf",
            "page_number": 16,
            "chunk_index": 3,
            "text": "Gevra OC produced 59.11 MT coal in FY 2023-24.",
            "keyword_score": 0.75
        }]

        with patch("app.services.hybrid_search_service.search_vector_store", return_value=mock_vec), \
             patch("app.services.hybrid_search_service.search_keyword_store", return_value=mock_kw):
            results = execute_hybrid_search(
                db=self.db,
                query_text="What was Gevra OC coal production in FY 2023-24?",
                top_k=5
            )

        matching = [
            r for r in results
            if r["document_id"] == 9 and r["page_number"] == 16 and r["chunk_index"] == 3
        ]

        # Verify exactly ONE fused candidate exists (not two duplicated candidates)
        self.assertEqual(len(matching), 1, "Duplicate physical chunks were not merged into single candidate")
        fused = matching[0]

        # Verify preserved chunk_id from keyword source
        self.assertEqual(fused["chunk_id"], 646)

        # Verify both vector_score and keyword_score are populated
        self.assertEqual(fused["vector_score"], 0.88)
        self.assertEqual(fused["keyword_score"], 0.75)

        # Verify canonical identity preserved
        self.assertEqual(fused["document_id"], 9)
        self.assertEqual(fused["page_number"], 16)
        self.assertEqual(fused["chunk_index"], 3)

    # --- Test G: Degraded LLM Citation Regex Collision Prevention ---
    def test_g_degraded_provider_no_instruction_collision(self):
        """BUG-02: Prompt instructions mention <untrusted_document_context>; parser must not capture them."""
        provider = DegradedLLMProvider()

        # Prompt with instructions containing the literal tag but NO evidence chunks
        prompt_empty = build_isolated_prompt("What is the coal production of Gevra OC?", [])
        answer_empty = provider.generate(prompt_empty)
        self.assertIn("Insufficient evidence", answer_empty)
        self.assertNotIn("[Document.pdf, Page 1]", answer_empty)

        # Prompt with valid evidence
        evidence = [{
            "filename": "SECL_Annual_Report_2023-24.pdf",
            "page_number": 16,
            "text": "Gevra OC achieved coal production of 59.11 MT in FY2023-24."
        }]
        prompt_with_doc = build_isolated_prompt("What was Gevra OC's coal production in FY2023-24?", evidence)
        answer_valid = provider.generate(prompt_with_doc)
        self.assertIn("59.11 MT", answer_valid)
        self.assertIn("[SECL_Annual_Report_2023-24.pdf, Page 16]", answer_valid)
        self.assertNotIn("Document.pdf", answer_valid)

    # --- Test H & I: Citation Gate ---
    def test_h_citation_gate_accepts_valid_citation(self):
        """Citation Gate: Accepts citation that exactly matches retrieved evidence."""
        text = "Gevra OC produced 59.11 MT in FY2023-24 [SECL_Annual_Report_2023-24.pdf, Page 16]."
        evidence_chunks = [{
            "filename": "SECL_Annual_Report_2023-24.pdf",
            "page_number": 16,
            "text": "Gevra OC achieved 59.11 MT."
        }]
        citations, is_valid = extract_and_validate_citations(text, evidence_chunks)
        self.assertTrue(is_valid)
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["document_name"], "SECL_Annual_Report_2023-24.pdf")
        self.assertEqual(citations[0]["page_number"], 16)

    def test_i_citation_gate_rejects_fabricated_citation(self):
        """Citation Gate: Rejects fabricated citation [Document.pdf, Page 1] not in evidence."""
        text = "According to records [Document.pdf, Page 1], production was 59.11 MT."
        evidence_chunks = [{
            "filename": "SECL_Annual_Report_2023-24.pdf",
            "page_number": 16,
            "text": "Gevra OC achieved 59.11 MT."
        }]
        citations, is_valid = extract_and_validate_citations(text, evidence_chunks)
        self.assertFalse(is_valid)
        self.assertEqual(len(citations), 0)

    # --- Test J: Missing Scope RBAC Resolution via FastAPI Route ---
    def test_j_missing_scope_rbac_admin_global(self):
        """BUG-07: FastAPI route /api/v1/query/ask authoritative RBAC scope resolution."""
        client = TestClient(app)

        cases = [
            # (user_role, user_sub, payload_sub, expected_effective_sub)
            ("Admin", "CIL HQ", None, None),            # CASE A: Admin + missing scope -> global
            ("Admin", "CIL HQ", "ALL CIL", None),        # CASE B: Admin + ALL CIL -> global
            ("Admin", "CIL HQ", "SECL", "SECL"),         # CASE C: Admin + explicit SECL -> SECL
            ("Reviewer", "ECL", "ALL CIL", "ECL"),       # CASE D: Reviewer ECL + ALL CIL -> remains ECL
            ("Reviewer", "ECL", "SECL", "ECL"),          # CASE E: Reviewer ECL + explicit SECL -> remains ECL
            ("Reviewer", "ECL", None, "ECL"),            # CASE F: Reviewer ECL + missing scope -> remains ECL
        ]

        for role, u_sub, p_sub, exp_sub in cases:
            mock_user = MagicMock(spec=User)
            mock_user.id = 1
            mock_user.username = f"{role.lower()}_user"
            mock_user.role = role
            mock_user.subsidiary = u_sub

            app.dependency_overrides[get_current_user] = lambda u=mock_user: u
            app.dependency_overrides[get_db] = lambda: self.db

            try:
                with patch("app.api.query.execute_rag_query") as mock_rag:
                    mock_rag.return_value = {
                        "query": "What is the coal production in FY 2023-24?",
                        "answer": "According to evidence [Doc.pdf, Page 1], production was 59.11 MT.",
                        "citations": [{"document_name": "Doc.pdf", "page_number": 1, "citation_tag": "[Doc.pdf, Page 1]"}],
                        "evidence_chunks": [],
                        "provider": "degraded",
                        "degraded_mode": True
                    }

                    payload = {"query": "What is the coal production in FY 2023-24?"}
                    if p_sub is not None:
                        payload["subsidiary_filter"] = p_sub

                    response = client.post("/api/v1/query/ask", json=payload)
                    self.assertEqual(response.status_code, 200, f"Route returned status {response.status_code} for role={role}")
                    self.assertTrue(mock_rag.called, "execute_rag_query was not invoked by the route")

                    actual_sub = mock_rag.call_args.kwargs.get("subsidiary_filter")
                    self.assertEqual(
                        actual_sub, exp_sub,
                        f"RBAC failed for {role} (sub={u_sub}) with payload_sub='{p_sub}': expected '{exp_sub}', got '{actual_sub}'"
                    )
            finally:
                app.dependency_overrides.clear()

    # --- Test K: Generic Degraded Provider Synthetic Evidence Synthesis (TASK 5) ---
    def test_k_generic_degraded_provider_synthetic_evidence(self):
        """TASK 5: Generic DegradedLLMProvider dynamically synthesizes structured evidence without hardcoding."""
        provider = DegradedLLMProvider()

        # Synthetic generic evidence block
        synthetic_evidence = [{
            "filename": "Example_Mining_Report.pdf",
            "page_number": 12,
            "text": (
                "Mine Entity: Example Mine | Metric: Production | "
                "Raw Extracted Value: 42.5 MT | Normalized Value: 42.5 MT | Fiscal Year: FY2023-24\n"
                "Raw Evidence Snippet: Example Mine achieved production of 42.5 MT in FY2023-24."
            )
        }]

        prompt = build_isolated_prompt("What was Example Mine's production in FY2023-24?", synthetic_evidence)
        answer = provider.generate(prompt)

        # Verify dynamic extraction from evidence
        self.assertIn("Example Mine", answer)
        self.assertIn("42.5 MT", answer)
        self.assertIn("[Example_Mining_Report.pdf, Page 12]", answer)
        self.assertNotIn("Gevra", answer)
        self.assertNotIn("Rajmahal", answer)
        self.assertNotIn("59.11", answer)

        # Verify citation extraction and gate acceptance
        citations, is_valid = extract_and_validate_citations(answer, synthetic_evidence)
        self.assertTrue(is_valid)
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["document_name"], "Example_Mining_Report.pdf")
        self.assertEqual(citations[0]["page_number"], 12)

        # Negative test 1: Empty evidence -> Insufficient evidence
        prompt_empty = build_isolated_prompt("What was Example Mine's production in FY2023-24?", [])
        answer_empty = provider.generate(prompt_empty)
        self.assertIn("Insufficient evidence", answer_empty)
        self.assertNotIn("Document.pdf", answer_empty)

        # Negative test 2: Malformed evidence without citation headers -> No fabricated citations
        malformed_prompt = (
            "<untrusted_document_context>\n"
            "Just some unformatted text without page citations.\n"
            "</untrusted_document_context>\n\n"
            "USER QUESTION: What was production?\n\nCITED ANSWER:"
        )
        answer_malformed = provider.generate(malformed_prompt)
        self.assertIn("Insufficient evidence", answer_malformed)
        self.assertNotIn("Document.pdf", answer_malformed)


if __name__ == "__main__":
    unittest.main()
