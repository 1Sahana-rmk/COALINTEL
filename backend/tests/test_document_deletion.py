import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import Base, get_db
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.extracted_metric import ExtractedMetric
from app.models.audit_log import AuditLog
from app.core.rbac import get_current_user
from app.services.storage_service import save_uploaded_file, file_exists, delete_uploaded_file
from app.services.ingestion_service import calculate_sha256


class TestDocumentDeletionFeature(unittest.TestCase):

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

        # Create test users
        self.admin_user = User(id=1, username="admin_tester", role="Admin", subsidiary="CIL HQ")
        self.analyst_user = User(id=2, username="analyst_tester", role="Analyst", subsidiary="ECL")
        self.reviewer_user = User(id=3, username="reviewer_tester", role="Reviewer", subsidiary="BCCL")

    def tearDown(self):
        self.db.rollback()
        self.db.close()
        app.dependency_overrides.clear()

    def _create_sample_doc(self, doc_id: int = 101, file_hash: str = "test_hash_del_1"):
        sample_bytes = b"ECL Coal Production FY2023-24 15.5 MT"
        storage_path = save_uploaded_file(sample_bytes, file_hash, f"del_test_{doc_id}.pdf")

        doc = Document(
            id=doc_id,
            filename=f"del_test_{doc_id}.pdf",
            file_path=storage_path,
            file_hash=file_hash,
            file_type="PDF",
            file_size_bytes=len(sample_bytes),
            subsidiary="ECL",
            fiscal_year="2023-24",
            status="PARSED",
            uploaded_by=1
        )
        self.db.add(doc)
        self.db.flush()

        chunk = DocumentChunk(
            document_id=doc.id,
            page_number=1,
            chunk_index=0,
            chunk_text="ECL Coal Production FY2023-24 15.5 MT",
            token_count=10,
            embedding_id=f"chunk_{doc.id}_1_0"
        )
        self.db.add(chunk)

        metric = ExtractedMetric(
            document_id=doc.id,
            page_number=1,
            mine_name="Rajmahal",
            subsidiary="ECL",
            metric_name="Coal Production",
            numeric_value=15.5,
            unit="MT",
            standard_value=15.5,
            standard_unit="MT",
            fiscal_year="2023-24",
            confidence_score=0.98,
            validation_status="VALIDATED"
        )
        self.db.add(metric)
        self.db.commit()
        return doc

    def test_01_admin_can_delete_document_and_audit_event_created(self):
        """Verify Admin successfully deletes document, chunks, metrics, files, and vectors, creating audit log."""
        doc = self._create_sample_doc(doc_id=201, file_hash="hash_admin_delete_1")
        doc_file_path = doc.file_path

        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.admin_user

        with patch("app.api.documents.delete_document_vectors") as mock_delete_vecs:
            mock_delete_vecs.return_value = True

            resp = self.client.delete(f"/api/v1/documents/{doc.id}")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["document_id"], 201)
            self.assertEqual(data["filename"], "del_test_201.pdf")

            # 1. Verify Chroma deletion was called
            mock_delete_vecs.assert_called_once_with(201)

            # 2. Verify Document is removed from DB
            deleted_doc = self.db.query(Document).filter(Document.id == 201).first()
            self.assertIsNone(deleted_doc)

            # 3. Verify DocumentChunk is removed
            chunks = self.db.query(DocumentChunk).filter(DocumentChunk.document_id == 201).all()
            self.assertEqual(len(chunks), 0)

            # 4. Verify ExtractedMetric is removed
            metrics = self.db.query(ExtractedMetric).filter(ExtractedMetric.document_id == 201).all()
            self.assertEqual(len(metrics), 0)

            # 5. Verify physical file is deleted
            self.assertFalse(file_exists(doc_file_path))

            # 6. Verify AuditLog entry was created
            audit = self.db.query(AuditLog).filter(
                AuditLog.action == "DOCUMENT_DELETED",
                AuditLog.resource_id == 201
            ).first()
            self.assertIsNotNone(audit)
            self.assertEqual(audit.user_id, self.admin_user.id)
            self.assertIn("del_test_201.pdf", audit.details)

    def test_02_analyst_receives_403_forbidden(self):
        """Verify Analyst role is forbidden from deleting documents (HTTP 403)."""
        doc = self._create_sample_doc(doc_id=202, file_hash="hash_analyst_del_403")

        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.analyst_user

        resp = self.client.delete(f"/api/v1/documents/{doc.id}")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("not authorized", resp.json()["detail"].lower())

        # Document must remain untouched
        existing = self.db.query(Document).filter(Document.id == 202).first()
        self.assertIsNotNone(existing)

    def test_03_reviewer_receives_403_forbidden(self):
        """Verify Reviewer role is forbidden from deleting documents (HTTP 403)."""
        doc = self._create_sample_doc(doc_id=203, file_hash="hash_reviewer_del_403")

        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.reviewer_user

        resp = self.client.delete(f"/api/v1/documents/{doc.id}")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("not authorized", resp.json()["detail"].lower())

        # Document must remain untouched
        existing = self.db.query(Document).filter(Document.id == 203).first()
        self.assertIsNotNone(existing)

    def test_04_unauthenticated_request_receives_401(self):
        """Verify unauthenticated requests receive HTTP 401 Unauthorized."""
        doc = self._create_sample_doc(doc_id=204, file_hash="hash_unauth_del_401")

        app.dependency_overrides[get_db] = lambda: self.db
        # Do not override get_current_user -> missing Authorization header yields 401

        resp = self.client.delete(f"/api/v1/documents/{doc.id}")
        self.assertEqual(resp.status_code, 401)

    def test_05_missing_document_receives_404(self):
        """Verify deleting nonexistent document returns HTTP 404 Not Found."""
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.admin_user

        resp = self.client.delete("/api/v1/documents/999999")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json()["detail"].lower())

    def test_06_idempotent_when_physical_file_already_missing(self):
        """Verify document deletion succeeds cleanly even if physical storage file is already missing."""
        doc = self._create_sample_doc(doc_id=206, file_hash="hash_missing_file_idempotent")
        # Explicitly remove physical file before deletion
        delete_uploaded_file(doc.file_path)
        self.assertFalse(file_exists(doc.file_path))

        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.admin_user

        with patch("app.api.documents.delete_document_vectors") as mock_vecs:
            mock_vecs.return_value = True
            resp = self.client.delete(f"/api/v1/documents/{doc.id}")
            self.assertEqual(resp.status_code, 200)

            deleted_doc = self.db.query(Document).filter(Document.id == 206).first()
            self.assertIsNone(deleted_doc)

    def test_07_duplicate_upload_re_enabled_after_deletion(self):
        """Verify re-uploading an identical file succeeds after the original document is deleted."""
        file_bytes = b"IDENTICAL MINING REPORT CONTENT FOR SHA-256 RE-UPLOAD TEST"
        file_hash = calculate_sha256(file_bytes)

        doc = Document(
            id=207,
            filename="reupload_test.pdf",
            file_path=save_uploaded_file(file_bytes, file_hash, "reupload_test.pdf"),
            file_hash=file_hash,
            file_type="PDF",
            file_size_bytes=len(file_bytes),
            subsidiary="ECL",
            fiscal_year="2023-24",
            status="PARSED",
            uploaded_by=1
        )
        self.db.add(doc)
        self.db.commit()

        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.admin_user

        # 1. Attempt upload while document exists -> Must fail with 409 Conflict
        upload_resp_1 = self.client.post(
            "/api/v1/documents/upload",
            files={"file": ("reupload_test.pdf", file_bytes, "application/pdf")},
            data={"subsidiary": "ECL", "fiscal_year": "2023-24"}
        )
        self.assertEqual(upload_resp_1.status_code, 409)
        self.assertIn("Duplicate document detected", upload_resp_1.json()["detail"])

        # 2. Delete original document
        with patch("app.api.documents.delete_document_vectors", return_value=True):
            del_resp = self.client.delete(f"/api/v1/documents/{doc.id}")
            self.assertEqual(del_resp.status_code, 200)

        # 3. Re-upload identical file after deletion -> Must succeed with 201 Created
        with patch("app.api.documents.run_background_document_processing"):
            upload_resp_2 = self.client.post(
                "/api/v1/documents/upload",
                files={"file": ("reupload_test.pdf", file_bytes, "application/pdf")},
                data={"subsidiary": "ECL", "fiscal_year": "2023-24"}
            )
            self.assertEqual(upload_resp_2.status_code, 201)
            new_doc_data = upload_resp_2.json()
            self.assertEqual(new_doc_data["file_hash"], file_hash)

    def test_08_conflict_references_safely_disassociated_on_deletion(self):
        """Verify data conflicts referencing the deleted document have doc_a_id/doc_b_id set to None while conflict record is preserved."""
        from app.models.data_conflict import DataConflict

        doc_1 = self._create_sample_doc(doc_id=301, file_hash="hash_conflict_del_1")
        doc_2 = self._create_sample_doc(doc_id=302, file_hash="hash_conflict_del_2")

        conflict_1 = DataConflict(
            id=401,
            metric_name="Coal Production",
            mine_name="Rajmahal",
            fiscal_year="2023-24",
            doc_a_id=doc_1.id,
            doc_b_id=doc_2.id,
            doc_a_value=15.5,
            doc_b_value=16.2,
            discrepancy_pct=4.5,
            status="OPEN"
        )
        self.db.add(conflict_1)

        conflict_2 = DataConflict(
            id=402,
            metric_name="Overburden Removal",
            mine_name="Rajmahal",
            fiscal_year="2023-24",
            doc_a_id=doc_2.id,
            doc_b_id=doc_1.id,
            doc_a_value=120.0,
            doc_b_value=125.0,
            discrepancy_pct=4.1,
            status="OPEN"
        )
        self.db.add(conflict_2)
        self.db.commit()

        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.admin_user

        with patch("app.api.documents.delete_document_vectors", return_value=True):
            resp = self.client.delete(f"/api/v1/documents/{doc_1.id}")
            self.assertEqual(resp.status_code, 200)

        # 1. Document 1 is deleted
        self.assertIsNone(self.db.query(Document).filter(Document.id == 301).first())

        # 2. Conflict 1 still exists, but doc_a_id is disassociated (None), doc_b_id remains doc_2.id
        c1 = self.db.query(DataConflict).filter(DataConflict.id == 401).first()
        self.assertIsNotNone(c1)
        self.assertIsNone(c1.doc_a_id)
        self.assertEqual(c1.doc_b_id, 302)

        # 3. Conflict 2 still exists, but doc_b_id is disassociated (None), doc_a_id remains doc_2.id
        c2 = self.db.query(DataConflict).filter(DataConflict.id == 402).first()
        self.assertIsNotNone(c2)
        self.assertEqual(c2.doc_a_id, 302)
        self.assertIsNone(c2.doc_b_id)

    def test_09_database_rollback_on_deletion_failure(self):
        """Verify transactional rollback if database flush fails during document deletion."""
        doc = self._create_sample_doc(doc_id=309, file_hash="hash_rollback_del_1")

        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.admin_user

        with patch("app.api.documents.delete_document_vectors", return_value=True):
            with patch.object(self.db, "flush", side_effect=Exception("Simulated DB Flush Error")):
                resp = self.client.delete(f"/api/v1/documents/{doc.id}")
                self.assertEqual(resp.status_code, 500)
                self.assertIn("Failed to delete document from database", resp.json()["detail"])

        # Document must remain in DB after rollback
        self.assertIsNotNone(self.db.query(Document).filter(Document.id == 309).first())

    def test_10_chroma_exception_gracefully_handled_without_blocking_db_deletion(self):
        """Verify vector deletion exception does not block relational database document cleanup."""
        doc = self._create_sample_doc(doc_id=310, file_hash="hash_chroma_err_del_1")

        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.admin_user

        with patch("app.api.documents.delete_document_vectors", side_effect=Exception("Chroma Connection Error")):
            resp = self.client.delete(f"/api/v1/documents/{doc.id}")
            self.assertEqual(resp.status_code, 200)

        # Document must be removed from DB despite Chroma exception
        self.assertIsNone(self.db.query(Document).filter(Document.id == 310).first())


if __name__ == "__main__":
    unittest.main()
