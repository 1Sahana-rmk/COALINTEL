import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import Base, get_db
from config import settings
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.extracted_metric import ExtractedMetric
from app.models.data_conflict import DataConflict
from app.models.audit_log import AuditLog
from app.core.rbac import get_current_user
from app.services.storage_service import (
    StorageError,
    StorageNotFoundError,
    StorageAuthenticationError,
    StoragePermissionError,
    StorageConnectionError,
    parse_storage_reference,
    save_document_binary,
    read_document_binary,
    document_binary_exists,
    delete_document_binary,
    get_document_binary_size,
    save_uploaded_file,
    read_uploaded_file,
    file_exists,
    delete_uploaded_file,
    get_file_size,
    LocalStorageProvider,
    SupabaseStorageProvider,
    get_storage_provider,
)
from app.services.ingestion_service import process_file_ingestion, calculate_sha256
from app.services.processing_pipeline import (
    execute_document_processing_pipeline,
    recover_stale_processing_documents,
)


class TestDocumentPersistentStorage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.test_db_file.close()
        cls.engine = create_engine(
            f"sqlite:///{cls.test_db_file.name}",
            connect_args={"check_same_thread": False}
        )
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)
        if os.path.exists(cls.test_db_file.name):
            try:
                os.remove(cls.test_db_file.name)
            except Exception:
                pass

    def setUp(self):
        self.db = self.TestingSessionLocal()
        self.client = TestClient(app)

        # Test users
        self.admin_user = User(id=1, username="admin_storage", role="Admin", subsidiary="CIL HQ")
        self.analyst_user = User(id=2, username="analyst_storage", role="Analyst", subsidiary="ECL")
        self.reviewer_user = User(id=3, username="reviewer_storage", role="Reviewer", subsidiary="BCCL")

    def tearDown(self):
        self.db.rollback()
        self.db.close()
        app.dependency_overrides.clear()

    # ==========================================================================
    # 1. Reference Parsing & Resolution Tests
    # ==========================================================================

    def test_parse_storage_reference_legacy_local_paths(self):
        """Verify legacy local filesystem paths resolve as ('local', 'uploads', file_path)."""
        paths = [
            "./storage/uploads/abc123_report.pdf",
            "storage/uploads/abc123_report.pdf",
            "/absolute/path/to/storage/uploads/doc.pdf",
            "C:/coalintel/storage/uploads/file.pdf",
            "../relative/storage/uploads/file.pdf",
        ]
        for p in paths:
            ref_type, bucket, path = parse_storage_reference(p)
            self.assertEqual(ref_type, "local")
            self.assertEqual(bucket, "uploads")
            self.assertEqual(path, p)

    def test_parse_storage_reference_supabase_paths(self):
        """Verify Supabase canonical keys and URI schemes resolve as ('supabase', bucket, object_path)."""
        ref_type, bucket, path = parse_storage_reference("documents/101/report.pdf")
        self.assertEqual(ref_type, "supabase")
        self.assertEqual(bucket, "documents")
        self.assertEqual(path, "101/report.pdf")

        ref_type, bucket, path = parse_storage_reference("supabase://documents/202/data.csv")
        self.assertEqual(ref_type, "supabase")
        self.assertEqual(bucket, "documents")
        self.assertEqual(path, "202/data.csv")

        ref_type, bucket, path = parse_storage_reference("reports/303/briefing.pdf")
        self.assertEqual(ref_type, "supabase")
        self.assertEqual(bucket, "reports")
        self.assertEqual(path, "303/briefing.pdf")

    def test_parse_storage_reference_empty_and_unknown(self):
        self.assertEqual(parse_storage_reference(""), ("unknown", "", ""))
        self.assertEqual(parse_storage_reference(None), ("unknown", "", ""))

    # ==========================================================================
    # 2. Local Mode End-to-End Lifecycle Tests
    # ==========================================================================

    @patch.object(settings, "STORAGE_PROVIDER", "local")
    def test_local_mode_upload_processing_read_and_delete(self):
        """Verify full document lifecycle in Local storage mode."""
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db] = lambda: self.db

        csv_content = b"mine_name,fiscal_year,production_mt\nRajmahal OCP,2023-24,17.5\n"
        response = self.client.post(
            "/api/v1/documents/upload",
            files={"file": ("test_local_cycle.csv", csv_content, "text/csv")},
            data={"subsidiary": "ECL", "fiscal_year": "2023-24"}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        doc_id = data["id"]
        file_path = data["file_path"]

        # Verify storage reference is a local path
        self.assertTrue(file_path.startswith("./storage/uploads") or "storage/uploads" in file_path)
        self.assertTrue(document_binary_exists(file_path))
        self.assertEqual(read_document_binary(file_path), csv_content)

        # Run pipeline
        success = execute_document_processing_pipeline(self.db, doc_id)
        self.assertTrue(success)

        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        self.assertEqual(doc.status, "PARSED")
        chunks_count = self.db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).count()
        self.assertGreater(chunks_count, 0)

        # Delete document
        del_response = self.client.delete(f"/api/v1/documents/{doc_id}")
        self.assertEqual(del_response.status_code, 200)

        # Verify binary deleted
        self.assertFalse(document_binary_exists(file_path))
        self.assertIsNone(self.db.query(Document).filter(Document.id == doc_id).first())

    @patch.object(settings, "STORAGE_PROVIDER", "local")
    def test_local_mode_duplicate_detection(self):
        """Verify identical SHA-256 binary upload triggers HTTP 409 Conflict."""
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db] = lambda: self.db

        content = b"Gevra OCP Annual Report FY 2023-24 Content"
        res1 = self.client.post(
            "/api/v1/documents/upload",
            files={"file": ("gevra_doc.pdf", content, "application/pdf")},
            data={"subsidiary": "SECL", "fiscal_year": "2023-24"}
        )
        self.assertEqual(res1.status_code, 201)
        doc1_id = res1.json()["id"]

        # Second upload with same binary content
        res2 = self.client.post(
            "/api/v1/documents/upload",
            files={"file": ("gevra_doc_copy.pdf", content, "application/pdf")},
            data={"subsidiary": "SECL", "fiscal_year": "2023-24"}
        )
        self.assertEqual(res2.status_code, 409)
        self.assertIn("Duplicate document detected", res2.json()["detail"])

        # Cleanup
        self.client.delete(f"/api/v1/documents/{doc1_id}")

    # ==========================================================================
    # 3. Supabase Mode Lifecycle Tests (Mocked Transport)
    # ==========================================================================

    @patch.object(settings, "STORAGE_PROVIDER", "supabase")
    @patch.object(settings, "SUPABASE_URL", "https://mock-supabase.co")
    @patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key-test")
    def test_supabase_mode_upload_and_storage_reference(self):
        """Verify upload in Supabase mode persists to Supabase Storage and records canonical object key."""
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db] = lambda: self.db

        content = b"Dipka Production Target 2023-24 40.0 MT"

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            # POST upload: /storage/v1/object/documents/...
            if request.method == "POST" and "/storage/v1/object/documents/" in url_str:
                self.assertIn("Authorization", request.headers)
                self.assertIn("Bearer mock-service-role-key-test", request.headers["Authorization"])
                return httpx.Response(200, json={"Key": "documents/mock"})
            # GET read: /storage/v1/object/authenticated/documents/...
            if request.method == "GET" and "/storage/v1/object/authenticated/documents/" in url_str:
                return httpx.Response(200, content=content)
            # GET info: /storage/v1/object/info/authenticated/documents/...
            if request.method == "GET" and "/storage/v1/object/info/authenticated/documents/" in url_str:
                return httpx.Response(200, json={"metadata": {"size": len(content)}})
            # DELETE: /storage/v1/object/documents/...
            if request.method == "DELETE" and "/storage/v1/object/documents/" in url_str:
                return httpx.Response(200, json={"message": "Deleted"})
            return httpx.Response(404, json={"error": "Not Found"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-service-role-key-test",
            http_client=mock_client
        )

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            res = self.client.post(
                "/api/v1/documents/upload",
                files={"file": ("dipka_report.csv", content, "text/csv")},
                data={"subsidiary": "SECL", "fiscal_year": "2023-24"}
            )
            self.assertEqual(res.status_code, 201)
            doc_data = res.json()
            doc_id = doc_data["id"]
            file_path = doc_data["file_path"]

            # Canonical storage key: documents/{doc_id}/dipka_report.csv
            self.assertEqual(file_path, f"documents/{doc_id}/dipka_report.csv")

            # Verify read_document_binary retrieves from Supabase provider
            retrieved_bytes = read_document_binary(file_path)
            self.assertEqual(retrieved_bytes, content)

            # Verify existence check
            self.assertTrue(document_binary_exists(file_path))

            # Run processing pipeline
            proc_success = execute_document_processing_pipeline(self.db, doc_id)
            self.assertTrue(proc_success)

            doc = self.db.query(Document).filter(Document.id == doc_id).first()
            self.assertEqual(doc.status, "PARSED")

            # Delete document
            del_res = self.client.delete(f"/api/v1/documents/{doc_id}")
            self.assertEqual(del_res.status_code, 200)
            self.assertIsNone(self.db.query(Document).filter(Document.id == doc_id).first())

    # ==========================================================================
    # 4. Consistency & Failure Injection Tests
    # ==========================================================================

    @patch.object(settings, "STORAGE_PROVIDER", "supabase")
    @patch.object(settings, "SUPABASE_URL", "https://mock-supabase.co")
    @patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key-test")
    def test_supabase_upload_connection_failure_rolls_back_db(self):
        """Verify network error during Supabase upload rolls back DB Document row with HTTP 500."""
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db] = lambda: self.db

        content = b"Connection Failure Test Content"

        def mock_failing_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("Supabase connection timed out")

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_failing_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-service-role-key-test",
            http_client=mock_client
        )

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            res = self.client.post(
                "/api/v1/documents/upload",
                files={"file": ("fail_doc.pdf", content, "application/pdf")},
                data={"subsidiary": "WCL", "fiscal_year": "2023-24"}
            )
            self.assertEqual(res.status_code, 500)

            # Verify no orphaned document was left in database
            hash_val = calculate_sha256(content)
            doc_in_db = self.db.query(Document).filter(Document.file_hash == hash_val).first()
            self.assertIsNone(doc_in_db)

    @patch.object(settings, "STORAGE_PROVIDER", "supabase")
    @patch.object(settings, "SUPABASE_URL", "https://mock-supabase.co")
    @patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key-test")
    def test_supabase_upload_auth_failure_401_rolls_back_db(self):
        """Verify HTTP 401 from Supabase rolls back DB with HTTP 500."""
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db] = lambda: self.db

        content = b"Auth Failure 401 Test Content"

        def mock_auth_fail_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"message": "Invalid API key"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_auth_fail_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-service-role-key-test",
            http_client=mock_client
        )

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            res = self.client.post(
                "/api/v1/documents/upload",
                files={"file": ("auth_fail.pdf", content, "application/pdf")},
                data={"subsidiary": "BCCL", "fiscal_year": "2023-24"}
            )
            self.assertEqual(res.status_code, 500)
            hash_val = calculate_sha256(content)
            self.assertIsNone(self.db.query(Document).filter(Document.file_hash == hash_val).first())

    @patch.object(settings, "STORAGE_PROVIDER", "supabase")
    @patch.object(settings, "SUPABASE_URL", "https://mock-supabase.co")
    @patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key-test")
    def test_compensating_storage_delete_on_db_commit_error(self):
        """Verify that if DB commit fails after successful Supabase upload, compensating DELETE is sent."""
        app.dependency_overrides[get_current_user] = lambda: self.admin_user

        content = b"Compensating Cleanup Test Content"
        deleted_keys = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if request.method == "POST" and "/storage/v1/object/documents/" in url_str:
                return httpx.Response(200, json={"Key": "uploaded"})
            if request.method == "DELETE" and "/storage/v1/object/documents/" in url_str:
                deleted_keys.append(url_str)
                return httpx.Response(200, json={"message": "Deleted"})
            return httpx.Response(404, json={"error": "Not Found"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-service-role-key-test",
            http_client=mock_client
        )

        # Mock db.commit to raise an exception after flush
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        def side_effect_add(obj):
            if isinstance(obj, Document):
                obj.id = 999

        mock_db.add.side_effect = side_effect_add
        mock_db.commit.side_effect = Exception("Simulated DB commit error")

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            with pytest.raises(Exception):
                process_file_ingestion(
                    db=mock_db,
                    file_bytes=content,
                    original_filename="comp_test.pdf",
                    user_id=1,
                    subsidiary="NCL",
                    fiscal_year="2023-24"
                )

        # Confirm compensating DELETE was called for documents/999/comp_test.pdf
        self.assertEqual(len(deleted_keys), 1)
        self.assertIn("999/comp_test.pdf", deleted_keys[0])

    # ==========================================================================
    # 5. Coexistence & Legacy Compatibility Tests
    # ==========================================================================

    def test_legacy_local_and_supabase_documents_coexist(self):
        """Verify that a legacy local document and a Supabase document coexist and read correctly."""
        # 1. Create legacy local file
        legacy_bytes = b"Legacy Local File Content 2022-23"
        legacy_path = save_uploaded_file(legacy_bytes, "legacy_hash_001", "legacy.pdf")

        # 2. Mock Supabase document
        supabase_bytes = b"Supabase Object Content 2023-24"

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "/storage/v1/object/authenticated/documents/501/supa.pdf" in url_str:
                return httpx.Response(200, content=supabase_bytes)
            if "/storage/v1/object/info/authenticated/documents/501/supa.pdf" in url_str:
                return httpx.Response(200, json={"metadata": {"size": len(supabase_bytes)}})
            return httpx.Response(404, json={"error": "Not Found"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-key",
            http_client=mock_client
        )

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            # Read legacy local file
            self.assertEqual(read_document_binary(legacy_path), legacy_bytes)
            self.assertTrue(document_binary_exists(legacy_path))

            # Read Supabase file
            supa_ref = "documents/501/supa.pdf"
            self.assertEqual(read_document_binary(supa_ref), supabase_bytes)
            self.assertTrue(document_binary_exists(supa_ref))

        # Cleanup local file
        delete_uploaded_file(legacy_path)

    # ==========================================================================
    # 6. PR #44 Deletion Safety Regression Test
    # ==========================================================================

    def test_pr44_deletion_safety_with_storage_provider(self):
        """Verify document deletion disassociates DataConflict records without deleting them."""
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db] = lambda: self.db

        content_a = b"Conflict Document A Content"
        content_b = b"Conflict Document B Content"
        path_a = save_uploaded_file(content_a, "hash_conf_a", "doc_a.pdf")
        path_b = save_uploaded_file(content_b, "hash_conf_b", "doc_b.pdf")

        doc_a = Document(
            id=701,
            filename="doc_a.pdf",
            file_path=path_a,
            file_hash="hash_conf_a",
            file_type="PDF",
            file_size_bytes=len(content_a),
            subsidiary="ECL",
            fiscal_year="2023-24",
            status="PARSED",
            uploaded_by=1
        )
        doc_b = Document(
            id=702,
            filename="doc_b.pdf",
            file_path=path_b,
            file_hash="hash_conf_b",
            file_type="PDF",
            file_size_bytes=len(content_b),
            subsidiary="ECL",
            fiscal_year="2023-24",
            status="PARSED",
            uploaded_by=1
        )
        self.db.add_all([doc_a, doc_b])
        self.db.flush()

        # Add chunk and metric
        chunk = DocumentChunk(
            document_id=701,
            page_number=1,
            chunk_index=0,
            chunk_text="Sample chunk text",
            token_count=10,
            embedding_id="chunk_701_1_0"
        )
        metric = ExtractedMetric(
            document_id=701,
            page_number=1,
            mine_name="Rajmahal OCP",
            subsidiary="ECL",
            metric_name="coal_production",
            numeric_value=12.5,
            unit="MT",
            standard_value=12.5,
            standard_unit="MT",
            fiscal_year="2023-24",
            confidence_score=0.98,
            validation_status="VALIDATED"
        )
        conflict = DataConflict(
            id=901,
            doc_a_id=701,
            doc_b_id=702,
            mine_name="Rajmahal OCP",
            metric_name="coal_production",
            fiscal_year="2023-24",
            doc_a_value=12.5,
            doc_b_value=15.0,
            discrepancy_pct=20.0,
            status="OPEN"
        )
        self.db.add_all([chunk, metric, conflict])
        self.db.commit()

        # Delete doc_a via admin endpoint
        res = self.client.delete("/api/v1/documents/701")
        self.assertEqual(res.status_code, 200)

        # Verify doc_a is deleted, its binary deleted
        self.assertIsNone(self.db.query(Document).filter(Document.id == 701).first())
        self.assertFalse(file_exists(path_a))

        # Verify chunks and metrics for doc_a are deleted
        self.assertEqual(self.db.query(DocumentChunk).filter(DocumentChunk.document_id == 701).count(), 0)
        self.assertEqual(self.db.query(ExtractedMetric).filter(ExtractedMetric.document_id == 701).count(), 0)

        # Verify conflict record 901 still exists and doc_a_id is disassociated (None)
        conf_record = self.db.query(DataConflict).filter(DataConflict.id == 901).first()
        self.assertIsNotNone(conf_record)
        self.assertIsNone(conf_record.doc_a_id)
        self.assertEqual(conf_record.doc_b_id, 702)

        # Verify Audit Log entry created
        audit = self.db.query(AuditLog).filter(
            AuditLog.action == "DOCUMENT_DELETED",
            AuditLog.resource_id == 701
        ).first()
        self.assertIsNotNone(audit)

        # Cleanup doc_b
        self.client.delete("/api/v1/documents/702")

    # ==========================================================================
    # 7. Stale Processing Recovery Tests
    # ==========================================================================

    def test_recover_stale_processing_documents_local_and_supabase(self):
        """Verify stale document recovery handles both local and Supabase storage binaries."""
        from datetime import datetime, timezone, timedelta
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=30)

        # 1. Local doc with existing file
        loc_bytes = b"Local file still present"
        loc_path = save_uploaded_file(loc_bytes, "stale_hash_1", "stale_present.pdf")
        doc_loc_present = Document(
            id=801,
            filename="stale_present.pdf",
            file_path=loc_path,
            file_hash="stale_hash_1",
            file_type="PDF",
            file_size_bytes=len(loc_bytes),
            subsidiary="ECL",
            fiscal_year="2023-24",
            status="PROCESSING",
            created_at=stale_time,
            uploaded_by=1
        )

        # 2. Local doc with missing file
        doc_loc_missing = Document(
            id=802,
            filename="stale_missing.pdf",
            file_path="./storage/uploads/nonexistent_file_802.pdf",
            file_hash="stale_hash_2",
            file_type="PDF",
            file_size_bytes=100,
            subsidiary="ECL",
            fiscal_year="2023-24",
            status="PROCESSING",
            created_at=stale_time,
            uploaded_by=1
        )

        # 3. Supabase doc with existing object
        doc_supa_present = Document(
            id=803,
            filename="supa_present.pdf",
            file_path="documents/803/supa_present.pdf",
            file_hash="stale_hash_3",
            file_type="PDF",
            file_size_bytes=200,
            subsidiary="SECL",
            fiscal_year="2023-24",
            status="PROCESSING",
            created_at=stale_time,
            uploaded_by=1
        )

        # 4. Supabase doc with missing object
        doc_supa_missing = Document(
            id=804,
            filename="supa_missing.pdf",
            file_path="documents/804/supa_missing.pdf",
            file_hash="stale_hash_4",
            file_type="PDF",
            file_size_bytes=200,
            subsidiary="SECL",
            fiscal_year="2023-24",
            status="PROCESSING",
            created_at=stale_time,
            uploaded_by=1
        )

        self.db.add_all([doc_loc_present, doc_loc_missing, doc_supa_present, doc_supa_missing])
        self.db.commit()

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "documents/803/supa_present.pdf" in url_str:
                return httpx.Response(200, json={"metadata": {"size": 200}})
            return httpx.Response(404, json={"error": "Not Found"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-key",
            http_client=mock_client
        )

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            recovered = recover_stale_processing_documents(self.db, stale_minutes=15)
            self.assertEqual(recovered, 2)  # doc 802 and doc 804

            # Verify statuses
            d801 = self.db.query(Document).filter(Document.id == 801).first()
            d802 = self.db.query(Document).filter(Document.id == 802).first()
            d803 = self.db.query(Document).filter(Document.id == 803).first()
            d804 = self.db.query(Document).filter(Document.id == 804).first()

            self.assertEqual(d801.status, "PROCESSING")  # binary exists -> eligible
            self.assertEqual(d802.status, "FAILED")      # local missing -> FAILED
            self.assertEqual(d803.status, "PROCESSING")  # Supabase exists -> eligible
            self.assertEqual(d804.status, "FAILED")      # Supabase missing -> FAILED

        # Cleanup
        delete_uploaded_file(loc_path)

    # ==========================================================================
    # 8. Pipeline Failure Injection Tests
    # ==========================================================================

    def test_pipeline_supabase_read_network_failure_marks_failed(self):
        """Verify pipeline handles Supabase network failure during binary read gracefully without crash."""
        doc = Document(
            id=850,
            filename="net_fail.pdf",
            file_path="documents/850/net_fail.pdf",
            file_hash="net_fail_hash",
            file_type="PDF",
            file_size_bytes=500,
            subsidiary="WCL",
            fiscal_year="2023-24",
            status="PENDING",
            uploaded_by=1
        )
        self.db.add(doc)
        self.db.commit()

        def mock_failing_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            # file_exists succeeds
            if request.method == "GET" and "/object/info/" in url_str:
                return httpx.Response(200, json={"metadata": {"size": 500}})
            # binary read fails with network error
            raise httpx.ReadTimeout("Supabase read timed out")

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_failing_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-key",
            http_client=mock_client
        )

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            success = execute_document_processing_pipeline(self.db, 850)
            self.assertFalse(success)

            refreshed = self.db.query(Document).filter(Document.id == 850).first()
            self.assertEqual(refreshed.status, "FAILED")
            self.assertIn("Failed to retrieve document binary", refreshed.error_message)

    # ==========================================================================
    # 9. Legacy Helper Routing Tests
    # ==========================================================================

    def test_legacy_helpers_route_supabase_references(self):
        """Verify legacy helper functions (read_uploaded_file, file_exists, etc.) delegate to Supabase for remote keys."""
        test_bytes = b"Legacy Helper Routing Test Bytes"

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if request.method == "GET" and "/object/authenticated/documents/899/test.pdf" in url_str:
                return httpx.Response(200, content=test_bytes)
            if request.method == "GET" and "/object/info/authenticated/documents/899/test.pdf" in url_str:
                return httpx.Response(200, json={"metadata": {"size": len(test_bytes)}})
            if request.method == "DELETE" and "/object/documents/899/test.pdf" in url_str:
                return httpx.Response(200, json={"message": "Deleted"})
            return httpx.Response(404, json={"error": "Not Found"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-key",
            http_client=mock_client
        )

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            supa_ref = "documents/899/test.pdf"
            self.assertTrue(file_exists(supa_ref))
            self.assertEqual(read_uploaded_file(supa_ref), test_bytes)
            self.assertEqual(get_file_size(supa_ref), len(test_bytes))
            self.assertTrue(delete_uploaded_file(supa_ref))

    # ==========================================================================
    # 10. Non-Admin Deletion RBAC Tests
    # ==========================================================================

    def test_delete_document_rbac_forbidden_for_analyst_and_reviewer(self):
        """Verify non-Admin roles receive HTTP 403 Forbidden when attempting document deletion."""
        app.dependency_overrides[get_db] = lambda: self.db

        doc = Document(
            id=950,
            filename="rbac_test.pdf",
            file_path="./storage/uploads/rbac_test.pdf",
            file_hash="rbac_hash_950",
            file_type="PDF",
            file_size_bytes=100,
            subsidiary="ECL",
            fiscal_year="2023-24",
            status="PARSED",
            uploaded_by=1
        )
        self.db.add(doc)
        self.db.commit()

        # Analyst role -> 403
        app.dependency_overrides[get_current_user] = lambda: self.analyst_user
        res_analyst = self.client.delete("/api/v1/documents/950")
        self.assertEqual(res_analyst.status_code, 403)

        # Reviewer role -> 403
        app.dependency_overrides[get_current_user] = lambda: self.reviewer_user
        res_reviewer = self.client.delete("/api/v1/documents/950")
        self.assertEqual(res_reviewer.status_code, 403)

        # Document still exists
        self.assertIsNotNone(self.db.query(Document).filter(Document.id == 950).first())


if __name__ == "__main__":
    unittest.main()
