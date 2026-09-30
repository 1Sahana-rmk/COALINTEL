import hashlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base, get_db
from main import app
from app.core.rbac import get_current_user
from app.models.document import Document
from app.models.user import User
from config import settings


@pytest.fixture()
def source_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'source.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    user = User(id=1, username="source_reader", hashed_password="test-hash", role="Viewer", subsidiary="CIL HQ")
    db.add(user)
    db.commit()

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        yield client, db, tmp_path
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.mark.parametrize(
    ("filename", "file_type", "content_type", "content"),
    [
        ("original.pdf", "PDF", "application/pdf", b"%PDF-original-bytes%"),
        ("original.docx", "DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04docx"),
        ("original.xlsx", "XLSX", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"PK\x03\x04xlsx"),
        ("original.csv", "CSV", "text/csv", b"mine,value\nMCL,781.05\n"),
        ("original.png", "PNG", "image/png", b"\x89PNG\r\n\x1a\noriginal-image-bytes"),
    ],
)
def test_source_endpoint_returns_exact_original_bytes(source_client, filename, file_type, content_type, content):
    client, db, tmp_path = source_client
    path = tmp_path / filename
    path.write_bytes(content)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
        doc = Document(
            id=101,
            filename=filename,
            file_path=str(path),
            file_hash=hashlib.sha256(content).hexdigest(),
            file_type=file_type,
            status="PARSED",
        )
        db.add(doc)
        db.commit()
        response = client.get("/api/v1/documents/101/source")
    assert response.status_code == 200
    assert response.content == content
    assert hashlib.sha256(response.content).hexdigest() == doc.file_hash
    assert response.headers["content-type"].split(";")[0] == content_type
    assert filename in response.headers["content-disposition"]


def test_source_endpoint_missing_file_is_not_success(source_client):
    client, db, tmp_path = source_client
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
        doc = Document(
            id=102,
            filename="missing.pdf",
            file_path=str(tmp_path / "missing.pdf"),
            file_hash="a" * 64,
            file_type="PDF",
            status="PARSED",
        )
        db.add(doc)
        db.commit()
        response = client.get("/api/v1/documents/102/source")
    assert response.status_code == 404


def test_source_endpoint_rejects_local_path_outside_upload_root(source_client):
    client, db, tmp_path = source_client
    outside = tmp_path.parent / "outside.pdf"
    outside.write_bytes(b"must-not-leak")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
        doc = Document(
            id=103,
            filename="outside.pdf",
            file_path=str(outside),
            file_hash="b" * 64,
            file_type="PDF",
            status="PARSED",
        )
        db.add(doc)
        db.commit()
        response = client.get("/api/v1/documents/103/source")
    assert response.status_code == 404


def test_source_endpoint_requires_authentication(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'unauth.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).get("/api/v1/documents/999/source")
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)
    assert response.status_code == 401
