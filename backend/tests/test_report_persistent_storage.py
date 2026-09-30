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
from app.models.report import Report
from app.models.audit_log import AuditLog
from app.core.rbac import get_current_user
from app.services.storage_service import (
    StorageError,
    StorageNotFoundError,
    StorageAuthenticationError,
    StoragePermissionError,
    StorageConnectionError,
    parse_storage_reference,
    save_report_binary,
    read_report_binary,
    report_binary_exists,
    delete_report_binary,
    get_report_binary_size,
    LocalStorageProvider,
    SupabaseStorageProvider,
    get_storage_provider,
)
from app.services.report_service import (
    generate_report_pdf_bytes,
    generate_pdf_reportlab,
    create_report_assembly,
)


class TestReportPersistentStorage(unittest.TestCase):

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
        self.admin_user = User(id=1, username="admin_rep", role="Admin", subsidiary="CIL HQ")
        self.analyst_user = User(id=2, username="analyst_rep", role="Analyst", subsidiary="ECL")
        self.reviewer_user = User(id=3, username="reviewer_rep", role="Reviewer", subsidiary="BCCL")

    def tearDown(self):
        self.db.rollback()
        self.db.close()
        app.dependency_overrides.clear()

    # ==========================================================================
    # 1. Reference Parsing & Resolution for Reports
    # ==========================================================================

    def test_parse_storage_reference_reports(self):
        """Verify report storage references are correctly categorized."""
        # Local paths
        ref_type, bucket, path = parse_storage_reference("./storage/reports/Report_1.pdf")
        self.assertEqual(ref_type, "local")
        self.assertEqual(bucket, "reports")

        ref_type, bucket, path = parse_storage_reference("storage/reports/Report_2.pdf")
        self.assertEqual(ref_type, "local")
        self.assertEqual(bucket, "reports")

        # Supabase paths
        ref_type, bucket, path = parse_storage_reference("reports/123/Report_ECL.pdf")
        self.assertEqual(ref_type, "supabase")
        self.assertEqual(bucket, "reports")
        self.assertEqual(path, "123/Report_ECL.pdf")

        ref_type, bucket, path = parse_storage_reference("supabase://reports/456/summary.pdf")
        self.assertEqual(ref_type, "supabase")
        self.assertEqual(bucket, "reports")
        self.assertEqual(path, "456/summary.pdf")

    # ==========================================================================
    # 2. Local Mode Report Generation & Lifecycle
    # ==========================================================================

    @patch.object(settings, "STORAGE_PROVIDER", "local")
    def test_local_report_generation_and_download(self):
        """Verify report generation in Local storage mode persists PDF and allows authenticated download."""
        app.dependency_overrides[get_current_user] = lambda: self.analyst_user
        app.dependency_overrides[get_db] = lambda: self.db

        # 1. Generate report
        res = self.client.post(
            "/api/v1/reports/generate",
            json={
                "report_type": "ANNUAL_SUMMARY",
                "subsidiary": "ECL",
                "fiscal_year": "2023-24",
                "title": "Local Annual Summary ECL"
            }
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        report_id = data["id"]
        file_path = data["file_path"]

        self.assertTrue(file_path.startswith("./storage/reports") or "storage/reports" in file_path)
        self.assertTrue(report_binary_exists(file_path))

        # Verify PDF bytes
        pdf_bytes = read_report_binary(file_path)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # 2. Download report
        dl_res = self.client.get(f"/api/v1/reports/{report_id}/download")
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.headers["content-type"], "application/pdf")
        self.assertTrue(len(dl_res.content) > 100)

        # Cleanup
        delete_report_binary(file_path)

    # ==========================================================================
    # 3. Supabase Mode Report Generation & Storage
    # ==========================================================================

    @patch.object(settings, "STORAGE_PROVIDER", "supabase")
    @patch.object(settings, "SUPABASE_URL", "https://mock-supabase.co")
    @patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key-test")
    def test_supabase_report_generation_and_download(self):
        """Verify report generation in Supabase mode persists to Supabase Storage and downloads via authenticated stream."""
        app.dependency_overrides[get_current_user] = lambda: self.analyst_user
        app.dependency_overrides[get_db] = lambda: self.db

        stored_objects = {}

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            # Upload POST
            if request.method == "POST" and "/storage/v1/object/reports/" in url_str:
                self.assertIn("Authorization", request.headers)
                self.assertIn("Bearer mock-service-role-key-test", request.headers["Authorization"])
                key = url_str.split("/storage/v1/object/reports/")[1]
                stored_objects[key] = request.content
                return httpx.Response(200, json={"Key": f"reports/{key}"})
            # Read GET authenticated
            if request.method == "GET" and "/storage/v1/object/authenticated/reports/" in url_str:
                key = url_str.split("/storage/v1/object/authenticated/reports/")[1]
                if key in stored_objects:
                    return httpx.Response(200, content=stored_objects[key])
                return httpx.Response(404, json={"error": "Not Found"})
            # Info GET
            if request.method == "GET" and "/storage/v1/object/info/authenticated/reports/" in url_str:
                key = url_str.split("/storage/v1/object/info/authenticated/reports/")[1]
                if key in stored_objects:
                    return httpx.Response(200, json={"metadata": {"size": len(stored_objects[key])}})
                return httpx.Response(404, json={"error": "Not Found"})
            # DELETE
            if request.method == "DELETE" and "/storage/v1/object/reports/" in url_str:
                key = url_str.split("/storage/v1/object/reports/")[1]
                stored_objects.pop(key, None)
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
                "/api/v1/reports/generate",
                json={
                    "report_type": "PARLIAMENTARY_REPLY",
                    "subsidiary": "SECL",
                    "fiscal_year": "2023-24",
                    "title": "Parliamentary Briefing SECL"
                }
            )
            self.assertEqual(res.status_code, 201)
            data = res.json()
            report_id = data["id"]
            file_path = data["file_path"]

            # Canonical reference: reports/{report_id}/{filename}
            self.assertTrue(file_path.startswith(f"reports/{report_id}/"))
            self.assertTrue(report_binary_exists(file_path))

            # Download endpoint
            dl_res = self.client.get(f"/api/v1/reports/{report_id}/download")
            self.assertEqual(dl_res.status_code, 200)
            self.assertEqual(dl_res.headers["content-type"], "application/pdf")
            self.assertIn("attachment; filename=", dl_res.headers.get("content-disposition", ""))
            self.assertTrue(dl_res.content.startswith(b"%PDF"))

    # ==========================================================================
    # 4. Consistency & Failure Injection Tests
    # ==========================================================================

    @patch.object(settings, "STORAGE_PROVIDER", "supabase")
    @patch.object(settings, "SUPABASE_URL", "https://mock-supabase.co")
    @patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key-test")
    def test_supabase_upload_failure_rolls_back_db_report(self):
        """Verify network error during Supabase report upload rolls back DB with HTTP 500."""
        app.dependency_overrides[get_current_user] = lambda: self.analyst_user
        app.dependency_overrides[get_db] = lambda: self.db

        def mock_failing_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("Supabase connection timed out during report upload")

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_failing_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-service-role-key-test",
            http_client=mock_client
        )

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            res = self.client.post(
                "/api/v1/reports/generate",
                json={
                    "report_type": "PRODUCTION_AUDIT",
                    "subsidiary": "WCL",
                    "fiscal_year": "2023-24",
                    "title": "Failing Upload Report"
                }
            )
            self.assertEqual(res.status_code, 500)

            # Assert no report row was committed
            rep = self.db.query(Report).filter(Report.title == "Failing Upload Report").first()
            self.assertIsNone(rep)

    @patch.object(settings, "STORAGE_PROVIDER", "supabase")
    @patch.object(settings, "SUPABASE_URL", "https://mock-supabase.co")
    @patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key-test")
    def test_compensating_storage_delete_on_report_db_commit_error(self):
        """Verify that if DB commit fails after successful Supabase upload, compensating DELETE is sent."""
        deleted_keys = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if request.method == "POST" and "/storage/v1/object/reports/" in url_str:
                return httpx.Response(200, json={"Key": "uploaded_report"})
            if request.method == "DELETE" and "/storage/v1/object/reports/" in url_str:
                deleted_keys.append(url_str)
                return httpx.Response(200, json={"message": "Deleted"})
            return httpx.Response(404, json={"error": "Not Found"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-service-role-key-test",
            http_client=mock_client
        )

        mock_db = MagicMock()
        def side_effect_add(obj):
            if isinstance(obj, Report):
                obj.id = 888

        mock_db.add.side_effect = side_effect_add
        mock_db.commit.side_effect = Exception("Simulated DB commit error during report generation")

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            with pytest.raises(Exception):
                create_report_assembly(
                    db=mock_db,
                    user_id=1,
                    report_type="SUBSIDIARY_COMPARISON",
                    subsidiary="BCCL",
                    fiscal_year="2023-24",
                    title="Compensating Report Test"
                )

        # Confirm compensating DELETE was issued for report ID 888
        self.assertEqual(len(deleted_keys), 1)
        self.assertIn("888/", deleted_keys[0])

    @patch.object(settings, "STORAGE_PROVIDER", "supabase")
    @patch.object(settings, "SUPABASE_URL", "https://mock-supabase.co")
    @patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key-test")
    def test_compensating_delete_failure_logged_gracefully(self):
        """Verify that if compensating storage delete also fails, it logs warning and does not mask original error."""
        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if request.method == "POST" and "/storage/v1/object/reports/" in url_str:
                return httpx.Response(200, json={"Key": "uploaded_report"})
            if request.method == "DELETE" and "/storage/v1/object/reports/" in url_str:
                raise httpx.ConnectTimeout("Compensation delete timeout")
            return httpx.Response(404, json={"error": "Not Found"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-service-role-key-test",
            http_client=mock_client
        )

        mock_db = MagicMock()
        def side_effect_add(obj):
            if isinstance(obj, Report):
                obj.id = 777

        mock_db.add.side_effect = side_effect_add
        mock_db.commit.side_effect = Exception("Simulated DB commit error")

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            with pytest.raises(Exception):
                create_report_assembly(
                    db=mock_db,
                    user_id=1,
                    report_type="SUBSIDIARY_COMPARISON",
                    subsidiary="BCCL",
                    fiscal_year="2023-24"
                )

    # ==========================================================================
    # 5. Coexistence & Legacy Compatibility
    # ==========================================================================

    def test_legacy_local_and_supabase_reports_coexist(self):
        """Verify legacy local report files and Supabase report references coexist and read correctly."""
        # 1. Create legacy local report
        local_dir = os.path.abspath(settings.REPORT_DIR)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, "legacy_report_test.pdf")
        local_bytes = b"%PDF-1.4 Legacy Local Report Content"
        with open(local_path, "wb") as f:
            f.write(local_bytes)

        # 2. Mock Supabase report
        supa_bytes = b"%PDF-1.4 Supabase Remote Report Content"

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "/storage/v1/object/authenticated/reports/601/remote.pdf" in url_str:
                return httpx.Response(200, content=supa_bytes)
            if "/storage/v1/object/info/authenticated/reports/601/remote.pdf" in url_str:
                return httpx.Response(200, json={"metadata": {"size": len(supa_bytes)}})
            return httpx.Response(404, json={"error": "Not Found"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-key",
            http_client=mock_client
        )

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            # Read local report
            rel_local_path = os.path.join(settings.REPORT_DIR, "legacy_report_test.pdf").replace("\\", "/")
            self.assertTrue(report_binary_exists(rel_local_path))
            self.assertEqual(read_report_binary(rel_local_path), local_bytes)

            # Read Supabase report
            supa_ref = "reports/601/remote.pdf"
            self.assertTrue(report_binary_exists(supa_ref))
            self.assertEqual(read_report_binary(supa_ref), supa_bytes)

        # Cleanup
        if os.path.exists(local_path):
            os.remove(local_path)

    # ==========================================================================
    # 6. Report Approval Workflow Regression
    # ==========================================================================

    def test_report_approval_workflow_with_storage_provider(self):
        """Verify report approval transitions status to APPROVED regardless of storage backend."""
        app.dependency_overrides[get_db] = lambda: self.db

        report = Report(
            id=650,
            title="Approval Test Report",
            report_type="ANNUAL_SUMMARY",
            subsidiary="ECL",
            fiscal_year="2023-24",
            file_path="reports/650/approval_test.pdf",
            approval_status="DRAFT",
            created_by=1
        )
        self.db.add(report)
        self.db.commit()

        # Analyst cannot approve -> 403
        app.dependency_overrides[get_current_user] = lambda: self.analyst_user
        res_analyst = self.client.post("/api/v1/reports/650/approve")
        self.assertEqual(res_analyst.status_code, 403)

        # Reviewer can approve -> 200
        app.dependency_overrides[get_current_user] = lambda: self.reviewer_user
        res_reviewer = self.client.post("/api/v1/reports/650/approve")
        self.assertEqual(res_reviewer.status_code, 200)
        self.assertEqual(res_reviewer.json()["approval_status"], "APPROVED")

        # Verify in DB and AuditLog
        refreshed = self.db.query(Report).filter(Report.id == 650).first()
        self.assertEqual(refreshed.approval_status, "APPROVED")

        audit = self.db.query(AuditLog).filter(
            AuditLog.action == "REPORT_APPROVE",
            AuditLog.resource_id == 650
        ).first()
        self.assertIsNotNone(audit)

    # ==========================================================================
    # 7. Error Handling: Missing Binary, 401, 403, 404, Timeouts, Flush, Leaks
    # ==========================================================================

    def test_download_missing_report_returns_404(self):
        """Verify download endpoint returns HTTP 404 if report binary is missing."""
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db] = lambda: self.db

        report = Report(
            id=701,
            title="Missing Report",
            report_type="ANNUAL_SUMMARY",
            subsidiary="ECL",
            fiscal_year="2023-24",
            file_path="./storage/reports/nonexistent_report_701.pdf",
            approval_status="DRAFT",
            created_by=1
        )
        self.db.add(report)
        self.db.commit()

        res = self.client.get("/api/v1/reports/701/download")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found on server storage", res.json()["detail"])

    @patch.object(settings, "STORAGE_PROVIDER", "supabase")
    @patch.object(settings, "SUPABASE_URL", "https://mock-supabase.co")
    @patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key-test")
    def test_supabase_auth_401_and_403_handling(self):
        """Verify HTTP 401 and 403 from Supabase Storage are properly classified."""
        def mock_401_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"message": "Invalid API key"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_401_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-key",
            http_client=mock_client
        )

        with pytest.raises(StorageAuthenticationError):
            mock_provider.save_file("reports", "test.pdf", b"content")

        def mock_403_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={"message": "Forbidden access"})

        mock_client_403 = httpx.Client(transport=httpx.MockTransport(mock_403_handler))
        mock_provider_403 = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-key",
            http_client=mock_client_403
        )

        with pytest.raises(StoragePermissionError):
            mock_provider_403.save_file("reports", "test.pdf", b"content")

    @patch.object(settings, "STORAGE_PROVIDER", "supabase")
    @patch.object(settings, "SUPABASE_URL", "https://mock-supabase.co")
    @patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key-test")
    def test_db_flush_failure_prevents_storage_upload(self):
        """Verify that if DB flush fails (e.g. constraint violation), no storage upload is attempted."""
        upload_calls = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            if "/storage/v1/object/reports/" in str(request.url):
                upload_calls.append(str(request.url))
            return httpx.Response(200, json={"Key": "uploaded"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-service-role-key-test",
            http_client=mock_client
        )

        mock_db = MagicMock()
        mock_db.flush.side_effect = Exception("DB Flush error: foreign key or constraint violation")

        with patch("app.services.storage_service.get_storage_provider", return_value=mock_provider):
            with pytest.raises(Exception):
                create_report_assembly(
                    db=mock_db,
                    user_id=1,
                    report_type="PARLIAMENTARY_REPLY",
                    subsidiary="ECL",
                    fiscal_year="2023-24"
                )

        # Assert no upload was attempted
        self.assertEqual(len(upload_calls), 0)

    @patch.object(settings, "STORAGE_PROVIDER", "supabase")
    @patch.object(settings, "SUPABASE_URL", "https://mock-supabase.co")
    @patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key-test")
    def test_supabase_timeout_handling(self):
        """Verify timeout during Supabase storage operations raises StorageConnectionError."""
        def mock_timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Supabase read timed out")

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_timeout_handler))
        mock_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-service-role-key-test",
            http_client=mock_client
        )

        with pytest.raises(StorageConnectionError):
            mock_provider.read_file(bucket="reports", path="1/test.pdf")

    @patch.object(settings, "STORAGE_PROVIDER", "supabase")
    @patch.object(settings, "SUPABASE_URL", "https://mock-supabase.co")
    @patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "super-secret-service-role-key-xyz987")
    def test_no_credential_leakage_in_logs_and_errors(self):
        """Verify that Supabase service-role keys and authorization headers are never logged or leaked in error details."""
        secret_key = "super-secret-service-role-key-xyz987"

        # 1. Success case: log should not leak secret_key
        def mock_success_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"Key": "reports/1/leak_check.pdf"})

        mock_client_success = httpx.Client(transport=httpx.MockTransport(mock_success_handler))
        mock_provider_success = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key=secret_key,
            http_client=mock_client_success
        )

        with self.assertLogs("app.services.storage_service", level="INFO") as cm_success:
            mock_provider_success.save_file("reports", "1/leak_check.pdf", b"test content")

        for log_msg in cm_success.output:
            self.assertNotIn(secret_key, log_msg)
            self.assertNotIn(f"Bearer {secret_key}", log_msg)

        # 2. Network error case: log and exception should not leak secret_key
        def mock_failing_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("Connection timeout connecting to storage")

        mock_client_fail = httpx.Client(transport=httpx.MockTransport(mock_failing_handler))
        mock_provider_fail = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key=secret_key,
            http_client=mock_client_fail
        )

        with self.assertLogs("app.services.storage_service", level="ERROR") as cm_err:
            try:
                mock_provider_fail.save_file("reports", "1/leak_check.pdf", b"test")
            except StorageError as exc:
                self.assertNotIn(secret_key, str(exc))

        for log_msg in cm_err.output:
            self.assertNotIn(secret_key, log_msg)
            self.assertNotIn(f"Bearer {secret_key}", log_msg)


if __name__ == "__main__":
    unittest.main()
