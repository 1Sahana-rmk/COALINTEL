import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base
from config import settings
from app.models.user import User
from app.models.document import Document
from app.models.report import Report
from app.models.audit_log import AuditLog
from app.services.storage_service import (
    StorageError,
    StorageNotFoundError,
    StorageAuthenticationError,
    StoragePermissionError,
    StorageConnectionError,
    SupabaseStorageProvider,
    read_document_binary,
    read_report_binary,
)
from app.services.storage_migration_service import (
    MigrationStatus,
    ReconciliationStatus,
    migrate_document,
    migrate_report,
    migrate_all_documents,
    migrate_all_reports,
    reconcile_document,
    reconcile_report,
    reconcile_all,
)


class TestStorageMigrationReconciliation(unittest.TestCase):

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

        cls.temp_storage_dir = tempfile.mkdtemp(prefix="coalintel_mig_test_")
        cls.uploads_dir = os.path.join(cls.temp_storage_dir, "uploads")
        cls.reports_dir = os.path.join(cls.temp_storage_dir, "reports")
        os.makedirs(cls.uploads_dir, exist_ok=True)
        os.makedirs(cls.reports_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)
        if os.path.exists(cls.test_db_file.name):
            try:
                os.remove(cls.test_db_file.name)
            except Exception:
                pass

        import shutil
        if os.path.exists(cls.temp_storage_dir):
            try:
                shutil.rmtree(cls.temp_storage_dir)
            except Exception:
                pass

    def setUp(self):
        self.db = self.TestingSessionLocal()
        self.stored_objects = {}

    def tearDown(self):
        self.db.rollback()
        self.db.close()
        self.stored_objects.clear()

    def _create_mock_supabase_provider(self) -> SupabaseStorageProvider:
        """Helper creating in-memory mock Supabase Storage provider."""
        stored = self.stored_objects

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)

            # POST /storage/v1/object/{bucket}/{path}
            if request.method == "POST" and "/storage/v1/object/" in url_str:
                parts = url_str.split("/storage/v1/object/")[1].split("/", 1)
                bucket = parts[0]
                obj_path = parts[1] if len(parts) > 1 else ""
                stored[f"{bucket}/{obj_path}"] = request.content
                return httpx.Response(200, json={"Key": f"{bucket}/{obj_path}"})

            # GET info (existence check) /storage/v1/object/info/authenticated/{bucket}/{path}
            if request.method == "GET" and "/storage/v1/object/info/authenticated/" in url_str:
                parts = url_str.split("/storage/v1/object/info/authenticated/")[1].split("/", 1)
                bucket = parts[0]
                obj_path = parts[1] if len(parts) > 1 else ""
                key = f"{bucket}/{obj_path}"
                if key in stored:
                    return httpx.Response(200, json={"metadata": {"size": len(stored[key])}})
                return httpx.Response(404, json={"error": "Not Found"})

            # GET data /storage/v1/object/authenticated/{bucket}/{path}
            if request.method == "GET" and "/storage/v1/object/authenticated/" in url_str:
                parts = url_str.split("/storage/v1/object/authenticated/")[1].split("/", 1)
                bucket = parts[0]
                obj_path = parts[1] if len(parts) > 1 else ""
                key = f"{bucket}/{obj_path}"
                if key in stored:
                    return httpx.Response(200, content=stored[key])
                return httpx.Response(404, json={"error": "Not Found"})

            # DELETE /storage/v1/object/{bucket}/{path}
            if request.method == "DELETE" and "/storage/v1/object/" in url_str:
                parts = url_str.split("/storage/v1/object/")[1].split("/", 1)
                bucket = parts[0]
                obj_path = parts[1] if len(parts) > 1 else ""
                key = f"{bucket}/{obj_path}"
                stored.pop(key, None)
                return httpx.Response(200, json={"message": "Deleted"})

            return httpx.Response(404, json={"error": "Not Found"})

        client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        return SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-service-role-key-test",
            http_client=client
        )

    # ==========================================================================
    # 1. Successful Document Migration
    # ==========================================================================

    def test_migrate_local_document_success(self):
        """Verify successful migration of local document to Supabase without deleting local source."""
        # 1. Create local file
        doc_bytes = b"%PDF-1.4 Official Coal Production Record ECL"
        import hashlib
        doc_hash = hashlib.sha256(doc_bytes).hexdigest()
        local_path = os.path.join(self.uploads_dir, f"{doc_hash}_annual_ecl.pdf")
        with open(local_path, "wb") as f:
            f.write(doc_bytes)

        # 2. Insert DB record
        doc = Document(
            id=101,
            filename="annual_ecl.pdf",
            file_path=local_path,
            file_hash=doc_hash,
            file_type="PDF",
            file_size_bytes=len(doc_bytes),
            subsidiary="ECL",
            fiscal_year="2023-24",
            status="PARSED"
        )
        self.db.add(doc)
        self.db.commit()

        provider = self._create_mock_supabase_provider()
        res = migrate_document(db=self.db, document_id=101, dry_run=False, provider=provider)

        # Assertions
        self.assertEqual(res.status, MigrationStatus.MIGRATED)
        self.assertEqual(res.new_file_path, "documents/101/annual_ecl.pdf")
        self.assertEqual(res.old_file_path, local_path)

        # Confirm DB updated
        refreshed = self.db.query(Document).filter(Document.id == 101).first()
        self.assertEqual(refreshed.file_path, "documents/101/annual_ecl.pdf")

        # Confirm uploaded object exists in Supabase
        self.assertIn("documents/101/annual_ecl.pdf", self.stored_objects)
        self.assertEqual(self.stored_objects["documents/101/annual_ecl.pdf"], doc_bytes)

        # Rule 1: Local file is NEVER deleted
        self.assertTrue(os.path.exists(local_path))

    # ==========================================================================
    # 2. Successful Report Migration
    # ==========================================================================

    def test_migrate_local_report_success(self):
        """Verify successful migration of local report PDF to Supabase."""
        rep_bytes = b"%PDF-1.4 Generated Institutional Report Content BCCL"
        local_path = os.path.join(self.reports_dir, "Report_ANNUAL_BCCL_102.pdf")
        with open(local_path, "wb") as f:
            f.write(rep_bytes)

        report = Report(
            id=201,
            title="Institutional Annual BCCL",
            report_type="ANNUAL_SUMMARY",
            subsidiary="BCCL",
            fiscal_year="2023-24",
            file_path=local_path,
            approval_status="APPROVED"
        )
        self.db.add(report)
        self.db.commit()

        provider = self._create_mock_supabase_provider()
        res = migrate_report(db=self.db, report_id=201, dry_run=False, provider=provider)

        self.assertEqual(res.status, MigrationStatus.MIGRATED)
        self.assertEqual(res.new_file_path, "reports/201/Report_ANNUAL_BCCL_102.pdf")

        refreshed = self.db.query(Report).filter(Report.id == 201).first()
        self.assertEqual(refreshed.file_path, "reports/201/Report_ANNUAL_BCCL_102.pdf")

        self.assertIn("reports/201/Report_ANNUAL_BCCL_102.pdf", self.stored_objects)
        self.assertTrue(os.path.exists(local_path))

    # ==========================================================================
    # 3 & 4. Dry-Run Mode for Document & Report
    # ==========================================================================

    def test_dry_run_makes_no_changes_document(self):
        """Verify dry-run mode inspects document but makes NO upload and NO DB mutation."""
        doc_bytes = b"%PDF-1.4 Dry Run Document Content"
        import hashlib
        doc_hash = hashlib.sha256(doc_bytes).hexdigest()
        local_path = os.path.join(self.uploads_dir, f"{doc_hash}_dryrun.pdf")
        with open(local_path, "wb") as f:
            f.write(doc_bytes)

        doc = Document(
            id=102,
            filename="dryrun.pdf",
            file_path=local_path,
            file_hash=doc_hash,
            file_type="PDF",
            file_size_bytes=len(doc_bytes),
            subsidiary="SECL"
        )
        self.db.add(doc)
        self.db.commit()

        provider = self._create_mock_supabase_provider()
        res = migrate_document(db=self.db, document_id=102, dry_run=True, provider=provider)

        self.assertEqual(res.status, MigrationStatus.DRY_RUN_ELIGIBLE)
        self.assertEqual(res.new_file_path, "documents/102/dryrun.pdf")

        # Zero uploads
        self.assertEqual(len(self.stored_objects), 0)

        # DB unchanged
        refreshed = self.db.query(Document).filter(Document.id == 102).first()
        self.assertEqual(refreshed.file_path, local_path)

    def test_dry_run_makes_no_changes_report(self):
        """Verify dry-run mode for reports makes NO upload and NO DB change."""
        rep_bytes = b"%PDF-1.4 Dry Run Report Content"
        local_path = os.path.join(self.reports_dir, "Report_DRYRUN_103.pdf")
        with open(local_path, "wb") as f:
            f.write(rep_bytes)

        report = Report(
            id=202,
            title="Dry Run Report",
            report_type="PARLIAMENTARY_REPLY",
            subsidiary="WCL",
            file_path=local_path
        )
        self.db.add(report)
        self.db.commit()

        provider = self._create_mock_supabase_provider()
        res = migrate_report(db=self.db, report_id=202, dry_run=True, provider=provider)

        self.assertEqual(res.status, MigrationStatus.DRY_RUN_ELIGIBLE)
        self.assertEqual(len(self.stored_objects), 0)
        refreshed = self.db.query(Report).filter(Report.id == 202).first()
        self.assertEqual(refreshed.file_path, local_path)

    # ==========================================================================
    # 5 & 6. Idempotency (Already-Migrated Records)
    # ==========================================================================

    def test_already_migrated_document_is_idempotent(self):
        """Verify already-migrated document is detected and not re-uploaded."""
        self.stored_objects["documents/103/already.pdf"] = b"Pre-existing Supabase Document"

        doc = Document(
            id=103,
            filename="already.pdf",
            file_path="documents/103/already.pdf",
            file_hash="hash103",
            file_type="PDF"
        )
        self.db.add(doc)
        self.db.commit()

        provider = self._create_mock_supabase_provider()
        res = migrate_document(db=self.db, document_id=103, dry_run=False, provider=provider)

        self.assertEqual(res.status, MigrationStatus.ALREADY_MIGRATED)
        self.assertEqual(res.new_file_path, "documents/103/already.pdf")

    def test_already_migrated_report_is_idempotent(self):
        """Verify already-migrated report is detected and not re-uploaded."""
        self.stored_objects["reports/203/report_already.pdf"] = b"Pre-existing Supabase Report"

        report = Report(
            id=203,
            title="Pre-existing Report",
            report_type="ANNUAL_SUMMARY",
            file_path="reports/203/report_already.pdf"
        )
        self.db.add(report)
        self.db.commit()

        provider = self._create_mock_supabase_provider()
        res = migrate_report(db=self.db, report_id=203, dry_run=False, provider=provider)

        self.assertEqual(res.status, MigrationStatus.ALREADY_MIGRATED)

    # ==========================================================================
    # 7 & 8. Missing Local Source Binaries
    # ==========================================================================

    def test_missing_local_document_binary_does_not_alter_db(self):
        """Verify that if local document file is missing, migration aborts without mutating DB."""
        doc = Document(
            id=104,
            filename="missing_local.pdf",
            file_path="./storage/uploads/nonexistent_file_104.pdf",
            file_hash="hash104",
            file_type="PDF"
        )
        self.db.add(doc)
        self.db.commit()

        provider = self._create_mock_supabase_provider()
        res = migrate_document(db=self.db, document_id=104, dry_run=False, provider=provider)

        self.assertEqual(res.status, MigrationStatus.MISSING_SOURCE_BINARY)
        # Confirm DB reference untouched
        refreshed = self.db.query(Document).filter(Document.id == 104).first()
        self.assertEqual(refreshed.file_path, "./storage/uploads/nonexistent_file_104.pdf")

    def test_missing_local_report_binary_does_not_alter_db(self):
        """Verify that if local report file is missing, migration aborts without mutating DB."""
        report = Report(
            id=204,
            title="Missing Report",
            report_type="PRODUCTION_AUDIT",
            file_path="./storage/reports/nonexistent_report_204.pdf"
        )
        self.db.add(report)
        self.db.commit()

        provider = self._create_mock_supabase_provider()
        res = migrate_report(db=self.db, report_id=204, dry_run=False, provider=provider)

        self.assertEqual(res.status, MigrationStatus.MISSING_SOURCE_BINARY)
        refreshed = self.db.query(Report).filter(Report.id == 204).first()
        self.assertEqual(refreshed.file_path, "./storage/reports/nonexistent_report_204.pdf")

    # ==========================================================================
    # 9. SHA-256 Hash Integrity Check
    # ==========================================================================

    def test_document_sha256_hash_mismatch_aborts_migration(self):
        """Verify migration halts if local file hash differs from Document.file_hash."""
        tampered_bytes = b"%PDF-1.4 Corrupted or tampered content"
        local_path = os.path.join(self.uploads_dir, "tampered_105.pdf")
        with open(local_path, "wb") as f:
            f.write(tampered_bytes)

        doc = Document(
            id=105,
            filename="tampered_105.pdf",
            file_path=local_path,
            file_hash="expected_authentic_sha256_hash_different_from_disk",
            file_type="PDF"
        )
        self.db.add(doc)
        self.db.commit()

        provider = self._create_mock_supabase_provider()
        res = migrate_document(db=self.db, document_id=105, dry_run=False, provider=provider)

        self.assertEqual(res.status, MigrationStatus.INTEGRITY_HASH_MISMATCH)
        self.assertIn("SHA-256 mismatch", res.message)
        self.assertEqual(len(self.stored_objects), 0)

        # DB untouched
        refreshed = self.db.query(Document).filter(Document.id == 105).first()
        self.assertEqual(refreshed.file_path, local_path)

    # ==========================================================================
    # 10, 11, 12. Supabase Upload, Auth, and Timeout Failures
    # ==========================================================================

    def test_supabase_upload_failure_preserves_db_and_local(self):
        """Verify network upload error leaves DB and local file completely untouched."""
        doc_bytes = b"%PDF-1.4 Upload Failure Test"
        import hashlib
        doc_hash = hashlib.sha256(doc_bytes).hexdigest()
        local_path = os.path.join(self.uploads_dir, f"{doc_hash}_upfail.pdf")
        with open(local_path, "wb") as f:
            f.write(doc_bytes)

        doc = Document(
            id=106,
            filename="upfail.pdf",
            file_path=local_path,
            file_hash=doc_hash,
            file_type="PDF"
        )
        self.db.add(doc)
        self.db.commit()

        def mock_failing_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"message": "Internal Supabase Upload Error"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_failing_handler))
        failing_provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key="mock-key",
            http_client=mock_client
        )

        res = migrate_document(db=self.db, document_id=106, dry_run=False, provider=failing_provider)

        self.assertEqual(res.status, MigrationStatus.UPLOAD_FAILED)
        refreshed = self.db.query(Document).filter(Document.id == 106).first()
        self.assertEqual(refreshed.file_path, local_path)
        self.assertTrue(os.path.exists(local_path))

    def test_supabase_authentication_failure_handled(self):
        """Verify HTTP 401/403 from Supabase surfaces cleanly as UPLOAD_FAILED."""
        doc_bytes = b"%PDF-1.4 Auth Failure Test"
        import hashlib
        doc_hash = hashlib.sha256(doc_bytes).hexdigest()
        local_path = os.path.join(self.uploads_dir, f"{doc_hash}_authfail.pdf")
        with open(local_path, "wb") as f:
            f.write(doc_bytes)

        doc = Document(id=107, filename="authfail.pdf", file_path=local_path, file_hash=doc_hash, file_type="PDF")
        self.db.add(doc)
        self.db.commit()

        def mock_auth_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"message": "Invalid JWT API Key"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_auth_handler))
        auth_provider = SupabaseStorageProvider(supabase_url="https://mock-supabase.co", service_role_key="invalid-key", http_client=mock_client)

        res = migrate_document(db=self.db, document_id=107, dry_run=False, provider=auth_provider)
        self.assertEqual(res.status, MigrationStatus.UPLOAD_FAILED)

    def test_supabase_timeout_failure_handled(self):
        """Verify read/connect timeout from Supabase is caught and reported."""
        doc_bytes = b"%PDF-1.4 Timeout Test"
        import hashlib
        doc_hash = hashlib.sha256(doc_bytes).hexdigest()
        local_path = os.path.join(self.uploads_dir, f"{doc_hash}_timeout.pdf")
        with open(local_path, "wb") as f:
            f.write(doc_bytes)

        doc = Document(id=108, filename="timeout.pdf", file_path=local_path, file_hash=doc_hash, file_type="PDF")
        self.db.add(doc)
        self.db.commit()

        def mock_timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Supabase request timed out")

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_timeout_handler))
        timeout_provider = SupabaseStorageProvider(supabase_url="https://mock-supabase.co", service_role_key="mock-key", http_client=mock_client)

        res = migrate_document(db=self.db, document_id=108, dry_run=False, provider=timeout_provider)
        self.assertEqual(res.status, MigrationStatus.UPLOAD_FAILED)

    # ==========================================================================
    # 13 & 14. DB Update Failure & Compensating Storage Deletion
    # ==========================================================================

    def test_db_update_failure_triggers_compensating_storage_delete(self):
        """Verify that if DB commit fails after upload, compensating delete removes the uploaded object."""
        doc_bytes = b"%PDF-1.4 Compensating Delete Test"
        import hashlib
        doc_hash = hashlib.sha256(doc_bytes).hexdigest()
        local_path = os.path.join(self.uploads_dir, f"{doc_hash}_comp.pdf")
        with open(local_path, "wb") as f:
            f.write(doc_bytes)

        doc = Document(id=109, filename="comp.pdf", file_path=local_path, file_hash=doc_hash, file_type="PDF")
        self.db.add(doc)
        self.db.commit()

        provider = self._create_mock_supabase_provider()

        # Mock DB commit failure
        with patch.object(self.db, "commit", side_effect=Exception("Simulated PostgreSQL commit error")):
            res = migrate_document(db=self.db, document_id=109, dry_run=False, provider=provider)

        self.assertEqual(res.status, MigrationStatus.DB_COMMIT_FAILED)

        # Compensating delete removed the object from Supabase
        self.assertNotIn("documents/109/comp.pdf", self.stored_objects)

        # Local source intact
        self.assertTrue(os.path.exists(local_path))

    def test_compensating_delete_failure_logged_gracefully(self):
        """Verify that if compensating delete also times out, it is logged without crashing."""
        rep_bytes = b"%PDF-1.4 Compensation Failure Test"
        local_path = os.path.join(self.reports_dir, "Report_COMPFAIL_205.pdf")
        with open(local_path, "wb") as f:
            f.write(rep_bytes)

        report = Report(id=205, title="Comp Fail", report_type="ANNUAL_SUMMARY", file_path=local_path)
        self.db.add(report)
        self.db.commit()

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if request.method == "POST":
                return httpx.Response(200, json={"Key": "reports/205/Report_COMPFAIL_205.pdf"})
            if request.method == "GET":
                return httpx.Response(200, json={"metadata": {"size": 100}})
            if request.method == "DELETE":
                raise httpx.ConnectTimeout("Compensation delete timeout")
            return httpx.Response(404)

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        provider = SupabaseStorageProvider(supabase_url="https://mock-supabase.co", service_role_key="mock-key", http_client=mock_client)

        with patch.object(self.db, "commit", side_effect=Exception("Simulated commit error")):
            res = migrate_report(db=self.db, report_id=205, dry_run=False, provider=provider)

        self.assertEqual(res.status, MigrationStatus.DB_COMMIT_FAILED)

    # ==========================================================================
    # 15, 16, 17, 18. Reconciliation Checks
    # ==========================================================================

    def test_reconciliation_healthy_local_reference(self):
        """Verify reconciliation identifies healthy local document."""
        data = b"Healthy local doc content"
        import hashlib
        h = hashlib.sha256(data).hexdigest()
        p = os.path.join(self.uploads_dir, f"{h}_reconcile_healthy.pdf")
        with open(p, "wb") as f:
            f.write(data)

        doc = Document(id=110, filename="reconcile_healthy.pdf", file_path=p, file_hash=h, file_type="PDF")
        self.db.add(doc)
        self.db.commit()

        res = reconcile_document(db=self.db, document_id=110)
        self.assertEqual(res.status, ReconciliationStatus.HEALTHY_LOCAL)
        self.assertTrue(res.exists_in_storage)
        self.assertEqual(res.provider_type, "local")

    def test_reconciliation_missing_local_binary(self):
        """Verify reconciliation flags missing local file."""
        doc = Document(id=111, filename="missing.pdf", file_path="./storage/uploads/missing_111.pdf", file_hash="h111", file_type="PDF")
        self.db.add(doc)
        self.db.commit()

        res = reconcile_document(db=self.db, document_id=111)
        self.assertEqual(res.status, ReconciliationStatus.MISSING_LOCAL_BINARY)
        self.assertFalse(res.exists_in_storage)

    def test_reconciliation_healthy_supabase_reference(self):
        """Verify reconciliation identifies healthy Supabase document."""
        self.stored_objects["documents/112/remote.pdf"] = b"Remote PDF content"
        doc = Document(id=112, filename="remote.pdf", file_path="documents/112/remote.pdf", file_hash="h112", file_type="PDF")
        self.db.add(doc)
        self.db.commit()

        provider = self._create_mock_supabase_provider()
        res = reconcile_document(db=self.db, document_id=112, provider=provider)
        self.assertEqual(res.status, ReconciliationStatus.HEALTHY_SUPABASE)
        self.assertTrue(res.exists_in_storage)

    def test_reconciliation_missing_supabase_object(self):
        """Verify reconciliation flags missing Supabase object."""
        doc = Document(id=113, filename="ghost.pdf", file_path="documents/113/ghost.pdf", file_hash="h113", file_type="PDF")
        self.db.add(doc)
        self.db.commit()

        provider = self._create_mock_supabase_provider()
        res = reconcile_document(db=self.db, document_id=113, provider=provider)
        self.assertEqual(res.status, ReconciliationStatus.MISSING_SUPABASE_OBJECT)
        self.assertFalse(res.exists_in_storage)

    # ==========================================================================
    # 19. Batch Migration Resilience & Audit Logging
    # ==========================================================================

    def test_batch_migration_and_audit_logging(self):
        """Verify batch migration processes records and logs AuditLog events."""
        # Record 1: valid
        data1 = b"Doc 1 Content"
        import hashlib
        h1 = hashlib.sha256(data1).hexdigest()
        p1 = os.path.join(self.uploads_dir, f"{h1}_batch1.pdf")
        with open(p1, "wb") as f:
            f.write(data1)
        d1 = Document(id=114, filename="batch1.pdf", file_path=p1, file_hash=h1, file_type="PDF", subsidiary="ECL")

        # Record 2: missing file
        d2 = Document(id=115, filename="batch2.pdf", file_path="./storage/uploads/missing_batch2.pdf", file_hash="h2", file_type="PDF", subsidiary="ECL")

        self.db.add_all([d1, d2])
        self.db.commit()

        provider = self._create_mock_supabase_provider()
        summary = migrate_all_documents(db=self.db, dry_run=False, provider=provider, subsidiary="ECL")

        self.assertEqual(summary.total_inspected, 2)
        self.assertEqual(summary.migrated, 1)
        self.assertEqual(summary.missing_source, 1)

        # AuditLog verification
        audit = self.db.query(AuditLog).filter(
            AuditLog.action == "DOCUMENT_STORAGE_MIGRATE",
            AuditLog.resource_id == 114
        ).first()
        self.assertIsNotNone(audit)
        self.assertIn("documents/114/batch1.pdf", audit.details)

    # ==========================================================================
    # 20. Security: No Credential Leakage
    # ==========================================================================

    def test_no_credential_leakage_in_migration_logs(self):
        """Verify secret tokens and service-role keys are never logged during migration operations."""
        secret_key = "super-secret-service-role-migration-key-123"

        doc_bytes = b"Leak Check Data"
        import hashlib
        doc_hash = hashlib.sha256(doc_bytes).hexdigest()
        p = os.path.join(self.uploads_dir, f"{doc_hash}_leak.pdf")
        with open(p, "wb") as f:
            f.write(doc_bytes)

        doc = Document(id=116, filename="leak.pdf", file_path=p, file_hash=doc_hash, file_type="PDF")
        self.db.add(doc)
        self.db.commit()

        def mock_error_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "Database error"})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_error_handler))
        provider = SupabaseStorageProvider(
            supabase_url="https://mock-supabase.co",
            service_role_key=secret_key,
            http_client=mock_client
        )

        with self.assertLogs("app.services.storage_migration_service", level="INFO") as cm:
            migrate_document(db=self.db, document_id=116, dry_run=False, provider=provider)

        for msg in cm.output:
            self.assertNotIn(secret_key, msg)
            self.assertNotIn(f"Bearer {secret_key}", msg)


if __name__ == "__main__":
    unittest.main()
