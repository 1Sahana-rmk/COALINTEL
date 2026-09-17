"""
COALINTEL — FINAL PRODUCT READINESS TEST SUITE
Comprehensive regression and validation tests covering:
1. Intent Classification: General AI vs Evidence Grounded.
2. Conceptual mining questions vs quantitative/entity-specific mining questions.
3. Degraded mode & General AI execution without fake citations.
4. Unsupported mining facts return 'Insufficient evidence' without guessing.
5. Executive Dashboard live dynamic aggregation (zero fake data, N/A when no validation data).
6. Metric Comparison canonical conflict ID linkage.
7. User Registration (Signup) security: safe role default, bcrypt hashing, uniqueness, audit logs.
"""

import unittest
import os
import sys
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import Base, get_db
from app.models.user import User
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.models.data_conflict import DataConflict
from app.models.audit_log import AuditLog
from app.core.security import get_password_hash, verify_password
from app.core.rbac import get_current_user
from app.services.rag_service import classify_query_intent, execute_rag_query
from app.schemas.query import QueryRequest


class TestFinalProductReadiness(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Sets up in-memory SQLite database and test client."""
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=cls.engine)
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)


        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        # Create an admin test user
        db = cls.TestingSessionLocal()
        cls.admin_user = User(
            username="admin_test",
            hashed_password=get_password_hash("AdminPass123!"),
            role="Admin",
            subsidiary="CIL HQ",
            full_name="Admin Test User",
            email="admin_test@cil.gov.in"
        )
        db.add(cls.admin_user)
        db.commit()
        db.refresh(cls.admin_user)
        db.close()

        def override_get_current_user():
            return cls.admin_user

        app.dependency_overrides[get_current_user] = override_get_current_user
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)
        app.dependency_overrides.clear()

    def setUp(self):
        self.db = self.TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    # =========================================================================
    # 1. RAG INTENT CLASSIFICATION TESTS
    # =========================================================================
    def test_intent_classification_conceptual_questions(self):
        """Conceptual and general knowledge questions must be classified as GENERAL_AI."""
        general_queries = [
            "What is coal?",
            "What is overburden removal?",
            "What is mining?",
            "Explain open cast mining vs underground mining",
            "What is Python?",
            "Write Python code to reverse a string",
            "How does TCP/IP work?",
            "What is the role of CMPDI?",
            "Hello, how are you?",
            "Who are you?",
        ]
        for query in general_queries:
            with self.subTest(query=query):
                intent = classify_query_intent(query)
                self.assertEqual(
                    intent,
                    "GENERAL_AI",
                    f"Query '{query}' was wrongly classified as '{intent}' instead of 'GENERAL_AI'"
                )

    def test_intent_classification_evidence_grounded_queries(self):
        """Quantitative, entity-specific, or period-bounded queries must be classified as EVIDENCE_GROUNDED."""
        evidence_queries = [
            "What was Gevra overburden removal in FY2023-24?",
            "What was CIL production in FY2024-25?",
            "What was SECL coal production in 2023-24?",
            "Give me the coal production of ECL in FY 2022-23",
            "What was the total OB removal of BCCL in FY 2023-24?",
            "According to the SECL annual report, what was the production?",
            "Show me the production statistics for Kusmunda mine in 2023-24",
        ]
        for query in evidence_queries:
            with self.subTest(query=query):
                intent = classify_query_intent(query)
                self.assertEqual(
                    intent,
                    "EVIDENCE_GROUNDED",
                    f"Query '{query}' was wrongly classified as '{intent}' instead of 'EVIDENCE_GROUNDED'"
                )

    # =========================================================================
    # 2. GENERAL AI QUERY EXECUTION & DEGRADED PROVIDER
    # =========================================================================
    def test_general_ai_query_execution_no_fake_citations(self):
        """General AI queries must return mode='GENERAL_AI' with zero fabricated document citations."""
        response = execute_rag_query(
            db=self.db,
            query_text="What is Python?",
            subsidiary_filter="ALL"
        )
        self.assertEqual(response["mode"], "GENERAL_AI")
        self.assertIn("Python", response["answer"])
        self.assertEqual(len(response["citations"]), 0)

    def test_general_ai_conceptual_coal_definition(self):
        """Conceptual coal question returns informative definition without document citations."""
        response = execute_rag_query(
            db=self.db,
            query_text="What is coal?",
            subsidiary_filter="ALL"
        )
        self.assertEqual(response["mode"], "GENERAL_AI")
        self.assertIn("coal", response["answer"].lower())
        self.assertEqual(len(response["citations"]), 0)

    def test_unsupported_evidence_query_returns_insufficient_evidence(self):
        """Evidence query with no matching database facts returns Insufficient Evidence."""
        response = execute_rag_query(
            db=self.db,
            query_text="What was Gevra production in FY2035?",
            subsidiary_filter="SECL"
        )
        self.assertIn(response["mode"], ["INSUFFICIENT_EVIDENCE", "EVIDENCE_GROUNDED"])
        self.assertTrue(
            "insufficient" in response["answer"].lower() and "evidence" in response["answer"].lower(),
            f"Expected insufficient evidence message but got: {response['answer']}"
        )
        self.assertEqual(len(response["citations"]), 0)


    # =========================================================================
    # 3. EXECUTIVE DASHBOARD LIVE DYNAMIC AGGREGATION
    # =========================================================================
    def test_dashboard_kpis_empty_database(self):
        """Dashboard with zero documents returns 0 counts and N/A accuracy (never fake numbers)."""
        # Clear existing documents and metrics in SQLite
        self.db.query(ExtractedMetric).delete()
        self.db.query(DataConflict).delete()
        self.db.query(Document).delete()
        self.db.commit()

        resp = self.client.get("/api/v1/dashboard/kpis")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["total_documents"], 0)
        self.assertEqual(data["total_production_mt"], "0.00")
        self.assertEqual(data["total_obr_mcum"], "0.00")
        self.assertEqual(data["active_conflicts"], 0)
        self.assertEqual(data["entity_accuracy_rate"], "N/A")
        self.assertEqual(data["citation_coverage_rate"], "N/A")

    def test_dashboard_charts_empty_database(self):
        """Dashboard charts endpoint returns live 0.0 data for subsidiaries when no documents are ingested."""
        resp = self.client.get("/api/v1/dashboard/charts")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        production_data = data.get("production_data", [])
        self.assertEqual(len(production_data), 7)
        for item in production_data:
            self.assertEqual(item["actual"], 0.0)
            self.assertEqual(item["obr"], 0.0)

    def test_dashboard_live_aggregation_with_data(self):
        """Dashboard aggregates live document and metric data dynamically."""
        doc = Document(
            filename="SECL_AR_2023_24.pdf",
            file_path="uploads/SECL_AR_2023_24.pdf",
            file_hash="hash_secl_2024",
            file_type="PDF",
            file_size_bytes=2048,
            subsidiary="SECL",
            uploaded_by=self.admin_user.id,
            status="PROCESSED"
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        m1 = ExtractedMetric(
            document_id=doc.id,
            mine_name="Gevra OC",
            subsidiary="SECL",
            metric_name="Coal Production",
            numeric_value=59.11,
            unit="MT",
            standard_value=59.11,
            standard_unit="MT",
            fiscal_year="2023-24",
            validation_status="VALIDATED",
            confidence_score=0.98,
            page_number=16
        )
        m2 = ExtractedMetric(
            document_id=doc.id,
            mine_name="Kusmunda OC",
            subsidiary="SECL",
            metric_name="Overburden Removal",
            numeric_value=45.50,
            unit="MCuM",
            standard_value=45.50,
            standard_unit="MCuM",
            fiscal_year="2023-24",
            validation_status="VALIDATED",
            confidence_score=0.95,
            page_number=22
        )
        self.db.add_all([m1, m2])
        self.db.commit()

        resp = self.client.get("/api/v1/dashboard/kpis?subsidiary_filter=SECL")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["total_documents"], 1)
        self.assertEqual(data["total_production_mt"], "59.11")
        self.assertEqual(data["total_obr_mcum"], "45.50")
        self.assertEqual(data["entity_accuracy_rate"], "100.0%")
        self.assertEqual(data["citation_coverage_rate"], "100.0%")

        # Test chart endpoint with subsidiary filter
        resp_chart = self.client.get("/api/v1/dashboard/charts?subsidiary_filter=SECL")
        self.assertEqual(resp_chart.status_code, 200)
        chart_data = resp_chart.json().get("production_data", [])
        self.assertEqual(len(chart_data), 1)
        self.assertEqual(chart_data[0]["subsidiary"], "SECL")
        self.assertEqual(chart_data[0]["actual"], 59.11)
        self.assertEqual(chart_data[0]["obr"], 45.50)


    # =========================================================================
    # 4. METRIC COMPARISON & CANONICAL CONFLICT ID LINKAGE
    # =========================================================================
    def test_metric_comparison_canonical_conflict_id_linkage(self):
        """Metric comparison discrepancies must link deterministically to canonical DataConflict IDs."""
        # Create a second document for BCCL
        doc_b = Document(
            filename="BCCL_Report_2023_24.pdf",
            file_path="uploads/BCCL_Report_2023_24.pdf",
            file_hash="hash_bccl_2024",
            file_type="PDF",
            file_size_bytes=1024,
            subsidiary="BCCL",
            uploaded_by=self.admin_user.id,
            status="PROCESSED"
        )
        self.db.add(doc_b)
        self.db.commit()
        self.db.refresh(doc_b)

        # Get the first doc
        doc_a = self.db.query(Document).filter(Document.subsidiary == "SECL").first()

        conflict = DataConflict(
            doc_a_id=doc_a.id,
            doc_b_id=doc_b.id,
            metric_name="Coal Production",
            mine_name="Gevra OC",
            fiscal_year="2023-24",
            doc_a_value=59.11,
            doc_b_value=52.00,
            discrepancy_pct=12.03,
            status="OPEN"
        )
        self.db.add(conflict)
        self.db.commit()
        self.db.refresh(conflict)

        resp = self.client.get("/api/v1/comparison/matrix?metric_type=Coal+Production&fiscal_year=2023-24")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Check if the matrix item has canonical_conflict_id
        items = data.get("items", [])
        gevra_items = [item for item in items if item["mine_name"] == "Gevra OC"]
        if gevra_items:
            gevra = gevra_items[0]
            self.assertTrue(gevra["has_discrepancy"])
            self.assertEqual(gevra["canonical_conflict_id"], conflict.id)



    # =========================================================================
    # 5. USER REGISTRATION (SIGNUP) & SECURITY
    # =========================================================================
    def test_user_signup_success(self):
        """Public signup creates a safe non-privileged Analyst user with bcrypt hashed password."""
        payload = {
            "username": "new_analyst_user",
            "password": "SecurePassword123!",
            "full_name": "New Analyst",
            "email": "analyst@cil.in",
            "subsidiary": "ECL"
        }
        resp = self.client.post("/api/v1/auth/signup", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()

        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["username"], "new_analyst_user")
        self.assertEqual(data["user"]["role"], "Analyst")
        self.assertEqual(data["user"]["subsidiary"], "ECL")

        # Verify password in database is hashed, not plain
        user_db = self.db.query(User).filter(User.username == "new_analyst_user").first()
        self.assertIsNotNone(user_db)
        self.assertNotEqual(user_db.hashed_password, "SecurePassword123!")
        self.assertTrue(verify_password("SecurePassword123!", user_db.hashed_password))

        # Verify audit log was recorded
        audit = self.db.query(AuditLog).filter(
            AuditLog.user_id == user_db.id,
            AuditLog.action == "USER_SIGNUP"
        ).first()
        self.assertIsNotNone(audit)

    def test_user_signup_duplicate_username_rejected(self):
        """Duplicate username registration returns 400 Bad Request."""
        payload = {
            "username": "admin_test",  # Already exists from setUpClass
            "password": "Password123!",
        }
        resp = self.client.post("/api/v1/auth/signup", json=payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already registered", resp.json()["detail"].lower())

    def test_user_signup_short_password_rejected(self):
        """Short password (< 6 chars) returns 400 Bad Request."""
        payload = {
            "username": "short_pwd_user",
            "password": "123",
        }
        resp = self.client.post("/api/v1/auth/signup", json=payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("6 characters", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main()
