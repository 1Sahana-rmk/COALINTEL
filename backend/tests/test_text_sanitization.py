import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base
from app.models.document import Document
from app.models.document_artifacts import DocumentPage, DocumentTable, DocumentImage
from app.models.document_chunk import DocumentChunk
from app.services.document_models import DocumentResult, EvidenceBlock, ImageResult, PageResult, TableResult
from app.services.processing_pipeline import execute_document_processing_pipeline
from app.services.storage_service import delete_uploaded_file, save_uploaded_file
from app.services.text_sanitization import sanitize_document_result


def test_sanitizer_preserves_unicode_whitespace_numbers_and_provenance_offsets():
    result = DocumentResult(
        document_id=None,
        filename="nul-ocr.pdf",
        file_type="PDF",
        pages=[PageResult(
            page_number=7,
            text="Native ₹ text\n781.05 MT\x00 -14.82 97.45% BH-27",
            extraction_method="NATIVE+OCR",
            blocks=[
                EvidenceBlock(text="Paddle OCR 143.20 m\x00", method="paddle_ppocrv6", bbox=[1, 2, 3, 4]),
                EvidenceBlock(text="Tesseract G8\x00", method="tesseract", bbox=[5, 6, 7, 8]),
            ],
        )],
        tables=[TableResult(
            page_number=7,
            table_number=1,
            headers=["Value", "Unit\x00"],
            rows=[["4.60", "m"], ["12,345.67\x00", "MT"]],
            cells=[{"coordinate": "B2", "value": "G8\x00", "bounding_box": [10, 10, 20, 20]}],
        )],
        images=[ImageResult(image_number=1, page_number=7, text="Image OCR\x00")],
    )

    sanitized = sanitize_document_result(result)

    assert "\x00" not in sanitized.pages[0].text
    assert "₹" in sanitized.pages[0].text
    assert "781.05" in sanitized.pages[0].text
    assert "-14.82" in sanitized.pages[0].text
    assert "97.45%" in sanitized.pages[0].text
    assert "BH-27" in sanitized.pages[0].text
    assert sanitized.pages[0].blocks[0].text == "Paddle OCR 143.20 m"
    assert sanitized.pages[0].blocks[0].bbox == [1, 2, 3, 4]
    assert sanitized.tables[0].headers[1] == "Unit"
    assert sanitized.tables[0].rows[1][0] == "12,345.67"
    assert sanitized.tables[0].cells[0]["value"] == "G8"
    assert sanitized.images[0].text == "Image OCR"
    assert sanitized.metadata["text_sanitization"]["warning_code"] == "TEXT_SANITIZED_INVALID_CONTROL_CHARACTER"
    assert sanitized.pages[0].metadata["text_sanitization"]["fields"][0]["original_offsets"]
    assert any("TEXT_SANITIZED_INVALID_CONTROL_CHARACTER" in warning for warning in sanitized.warnings)


def test_nul_text_is_sanitized_before_sqlite_artifact_chunk_and_metric_persistence(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    file_path = save_uploaded_file(b"synthetic parser input", "nul-pipeline-test", "nul-pipeline.csv")

    result = DocumentResult(
        document_id=None,
        filename="nul-pipeline.csv",
        file_type="CSV",
        pages=[PageResult(
            page_number=1,
            text="ECL Rajmahal Open Cast Mine Coal Production 781.05 MT\x00 in FY 2023-24",
            extraction_method="OCR",
            classification="SCANNED",
            blocks=[EvidenceBlock(text="781.05 MT\x00", method="tesseract")],
        )],
        tables=[TableResult(page_number=1, table_number=1, headers=["Metric\x00"], rows=[["781.05\x00"]])],
        warnings=[],
    )
    # Emulate a parser/OCR adapter returning unsafe text while exercising the
    # real common parse_document_result sanitization boundary.
    monkeypatch.setattr("app.services.parsing_service.parse_csv_result", lambda *args, **kwargs: result)
    monkeypatch.setattr("app.services.processing_pipeline.delete_document_vectors", lambda document_id: None)
    monkeypatch.setattr("app.services.processing_pipeline.add_chunks_to_vector_store", lambda *args, **kwargs: False)

    document = Document(
        filename="nul-pipeline.csv",
        file_path=file_path,
        file_hash="nul-pipeline-hash",
        file_type="CSV",
        file_size_bytes=21,
        status="PENDING",
        processing_status="DOWNLOADED",
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    try:
        assert execute_document_processing_pipeline(session, document.id) is True
        session.refresh(document)
        assert document.status == "PARSED"
        assert document.processing_status == "REVIEW_RECOMMENDED"
        assert any("TEXT_SANITIZED_INVALID_CONTROL_CHARACTER" in warning for warning in document.processing_warnings)

        page = session.query(DocumentPage).filter_by(document_id=document.id).one()
        assert "\x00" not in page.text
        assert "781.05" in page.text
        assert "2023-24" in page.text
        assert "\x00" not in (page.blocks_json or [])[0]["text"]

        table = session.query(DocumentTable).filter_by(document_id=document.id).one()
        assert "\x00" not in str(table.headers_json)
        assert "781.05" in str(table.rows_json)
        assert session.query(DocumentImage).filter_by(document_id=document.id).count() == 0
        assert all("\x00" not in chunk.chunk_text for chunk in session.query(DocumentChunk).filter_by(document_id=document.id).all())
    finally:
        session.close()
        delete_uploaded_file(file_path)
