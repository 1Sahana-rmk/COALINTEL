"""Focused Step 2B routing, fallback, and provenance tests."""

import io
import os
import sys

import fitz
import pytest
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.document_ai_client import DocumentAIError
from app.services.parsing_service import parse_image_result, parse_pdf_result
from config import settings


def _image_bytes(text: str = "OCR 781.05", *, blank: bool = False) -> bytes:
    image = Image.new("RGB", (900, 700), "white")
    if not blank:
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 42)
        for index, line in enumerate(text.split("\n")):
            draw.text((50, 80 + index * 90), line, fill="black", font=font)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _pdf(*builders) -> bytes:
    document = fitz.open()
    for builder in builders:
        page = document.new_page(width=612, height=792)
        builder(page)
    raw = document.tobytes()
    document.close()
    return raw


def _native(page):
    page.insert_text((40, 60), "Reliable native digital evidence retained exactly once on this page.")


def _scanned(page, raw=None):
    page.insert_image(page.rect, stream=raw or _image_bytes())


class FakeDocumentAI:
    def __init__(self, *, response=None, error=None, structure=None):
        self.response = response or {
            "status": "OK",
            "text": "Paddle raster value 781.05",
            "blocks": [{"text": "Paddle raster value 781.05", "bbox": [10, 20, 300, 70], "confidence": 0.96, "method": "paddle_ppocrv6", "metadata": {}}],
            "confidence": 0.96,
            "engine": "paddle_ppocrv6",
            "model": "PP-OCRv6_medium_det + PP-OCRv6_medium_rec",
            "version": "3.7.0",
            "source_raster": {"kind": "rendered_page"},
        }
        self.error = error
        self.structure_response = structure
        self.ocr_calls = []
        self.structure_calls = []

    def ocr(self, image_bytes, **kwargs):
        self.ocr_calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response

    def structure(self, image_bytes, **kwargs):
        self.structure_calls.append(kwargs)
        if self.error:
            raise self.error
        return self.structure_response or {"status": "OK", "tables": [], "warnings": []}


@pytest.fixture
def enable_document_ai(monkeypatch):
    monkeypatch.setattr(settings, "DOCUMENT_AI_ENABLED", True)
    monkeypatch.setattr(settings, "DOCUMENT_AI_FALLBACK_TO_TESSERACT", True)
    monkeypatch.setattr(settings, "DOCUMENT_AI_STRUCTURE_MODE", "table_hint")
    monkeypatch.setattr(settings, "DOCUMENT_AI_ENABLE_STRUCTURE", True)


def test_digital_page_stays_native_and_never_calls_document_ai(monkeypatch, enable_document_ai):
    client = FakeDocumentAI()
    monkeypatch.setattr("app.services.parsing_service.get_document_ai_client", lambda: client)
    result = parse_pdf_result("digital.pdf", _pdf(_native))
    assert result.pages[0].classification == "DIGITAL"
    assert result.pages[0].extraction_method == "NATIVE"
    assert not client.ocr_calls
    assert "Reliable native digital evidence" in result.pages[0].text


def test_multi_page_native_text_layer_over_full_page_images_never_routes_ai(monkeypatch, enable_document_ai):
    """Regression for digital PDFs with decorative/background image layers."""
    client = FakeDocumentAI()
    monkeypatch.setattr("app.services.parsing_service.get_document_ai_client", lambda: client)
    document = fitz.open()
    background_output = io.BytesIO()
    Image.new("RGB", (612, 792), "white").save(background_output, format="PNG")
    background = background_output.getvalue()
    for page_number in range(65):
        page = document.new_page(width=612, height=792)
        page.insert_image(page.rect, stream=background)
        page.insert_text((40, 60), f"Native page {page_number + 1} heading")
        page.insert_text((40, 90), "Native text layer remains the authoritative extraction source.")
    raw = document.tobytes()
    document.close()

    result = parse_pdf_result("digital_with_background_layers.pdf", raw)

    assert len(result.pages) == 65
    assert all(page.classification == "DIGITAL" for page in result.pages)
    assert all(page.extraction_method == "NATIVE" for page in result.pages)
    assert not client.ocr_calls
    assert not client.structure_calls
    assert len(result.metadata["timings_ms"]["pages"]) == 65
    assert all(not item["ocr_requested"] for item in result.metadata["timings_ms"]["pages"])


def test_scanned_page_routes_to_paddle_and_persists_provenance(monkeypatch, enable_document_ai):
    client = FakeDocumentAI()
    monkeypatch.setattr("app.services.parsing_service.get_document_ai_client", lambda: client)
    monkeypatch.setattr("app.services.parsing_service._ocr_image", lambda image: pytest.fail("Tesseract should not run after successful Paddle OCR"))
    result = parse_pdf_result("scanned.pdf", _pdf(lambda page: _scanned(page, _image_bytes("Paddle 781.05"))))
    page = result.pages[0]
    assert page.classification == "SCANNED"
    assert "Paddle raster" in page.text
    assert page.metadata["ocr_engine"] == "paddle_ppocrv6"
    assert page.metadata["ocr_model"].startswith("PP-OCRv6")
    assert page.blocks[0].method == "paddle_ppocrv6"
    assert page.blocks[0].bbox == [10, 20, 300, 70]
    assert client.ocr_calls[0]["page_number"] == 1


def test_mixed_page_preserves_native_text_and_uses_paddle_for_raster_region(monkeypatch, enable_document_ai):
    client = FakeDocumentAI()
    monkeypatch.setattr("app.services.parsing_service.get_document_ai_client", lambda: client)
    result = parse_pdf_result("mixed.pdf", _pdf(lambda page: (page.insert_text((40, 60), "Native heading retained."), page.insert_image(fitz.Rect(0, 120, 612, 700), stream=_image_bytes("Raster 781.05")))))
    page = result.pages[0]
    assert page.classification == "MIXED"
    assert page.extraction_method == "NATIVE+OCR"
    assert page.text.count("Native heading retained.") == 1
    assert "Paddle raster value" in page.text
    assert page.metadata["ocr_engine"] == "paddle_ppocrv6"
    assert len(client.ocr_calls) == 1


@pytest.mark.parametrize("failure", [DocumentAIError("timeout"), DocumentAIError("inference failed")])
def test_paddle_failure_uses_tesseract_with_explicit_fallback_provenance(monkeypatch, enable_document_ai, failure):
    client = FakeDocumentAI(error=failure)
    monkeypatch.setattr("app.services.parsing_service.get_document_ai_client", lambda: client)
    monkeypatch.setattr("app.services.parsing_service._ocr_image", lambda image: ("Tesseract recovery 781.05", [type("Block", (), {"text": "Tesseract", "bbox": [1, 2, 3, 4], "confidence": 0.88, "method": "OCR", "block_type": "TEXT", "metadata": {}})()], 0.88))
    result = parse_pdf_result("fallback.pdf", _pdf(lambda page: _scanned(page, _image_bytes("fallback"))))
    page = result.pages[0]
    assert page.text == "Tesseract recovery 781.05"
    assert page.metadata["ocr_engine"] == "tesseract"
    assert page.metadata["ocr_fallback_from"] == "paddle_ppocrv6"
    assert page.blocks[0].method == "tesseract"
    assert any("Paddle OCR failed" in warning for warning in result.warnings)


def test_blank_raster_is_empty_not_engine_failure(monkeypatch, enable_document_ai):
    client = FakeDocumentAI(response={"status": "EMPTY", "text": "", "blocks": [], "confidence": None, "engine": "paddle_ppocrv6", "model": "PP-OCRv6", "version": "3.7.0", "source_raster": {}})
    monkeypatch.setattr("app.services.parsing_service.get_document_ai_client", lambda: client)
    monkeypatch.setattr("app.services.parsing_service._ocr_image", lambda image: pytest.fail("blank successful Paddle result must not invoke fallback"))
    result = parse_image_result("blank.png", _image_bytes(blank=True), filename="blank.png", file_type="PNG")
    assert result.pages[0].text == ""
    assert result.pages[0].metadata["ocr_service_status"] == "EMPTY"
    assert result.pages[0].metadata["ocr_fallback_from"] is None
    assert not any("Paddle OCR failed" in warning for warning in result.warnings)


def test_low_confidence_paddle_result_remains_reviewable(monkeypatch, enable_document_ai):
    response = FakeDocumentAI().response
    response["confidence"] = 0.42
    response["blocks"][0]["confidence"] = 0.42
    client = FakeDocumentAI(response=response)
    monkeypatch.setattr("app.services.parsing_service.get_document_ai_client", lambda: client)
    result = parse_image_result("low.png", _image_bytes(), filename="low.png", file_type="PNG")
    assert result.pages[0].confidence == 0.42
    assert any("low OCR confidence" in warning for warning in result.warnings)


def test_structure_routing_persists_generic_cells_and_provenance(monkeypatch, enable_document_ai):
    response = FakeDocumentAI().response
    response["blocks"] = [{"text": value, "bbox": [10 + (index % 2) * 120, (index // 2) * 30, 100 + (index % 2) * 120, (index // 2) * 30 + 20], "confidence": 0.95, "method": "paddle_ppocrv6", "metadata": {}} for index, value in enumerate(["Subsidiary", "April", "ECL", "781.05", "BCCL", "0.781"])]
    client = FakeDocumentAI(response=response, structure={"status": "OK", "engine": "paddle_ppstructurev3", "tables": [{"page_number": 1, "table_number": 1, "headers": ["Subsidiary", "April"], "rows": [["ECL", "781.05"], ["BCCL", ""]], "bounding_box": [5, 5, 500, 300], "extraction_confidence": 0.91, "extraction_method": "paddle_ppstructurev3", "cells": [{"row_index": 1, "column_index": 1, "value": "781.05", "bbox": [110, 60, 200, 80]}], "warnings": []}], "warnings": []})
    monkeypatch.setattr("app.services.parsing_service.get_document_ai_client", lambda: client)
    result = parse_pdf_result("table.pdf", _pdf(lambda page: _scanned(page, _image_bytes("table"))))
    assert len(result.tables) == 1
    table = result.tables[0]
    assert table.extraction_method == "paddle_ppstructurev3"
    assert table.headers == ["Subsidiary", "April"]
    assert table.rows[0][1] == "781.05"
    assert table.bounding_box == [5, 5, 500, 300]
    assert client.structure_calls


def test_structure_is_not_called_for_non_table_like_ocr(monkeypatch, enable_document_ai):
    response = FakeDocumentAI().response
    response["blocks"] = [{"text": "One prose line", "bbox": [10, 20, 200, 50], "confidence": 0.96, "method": "paddle_ppocrv6", "metadata": {}}]
    client = FakeDocumentAI(response=response)
    monkeypatch.setattr("app.services.parsing_service.get_document_ai_client", lambda: client)
    result = parse_pdf_result("prose.pdf", _pdf(lambda page: _scanned(page, _image_bytes("prose"))))
    assert result.tables == []
    assert client.structure_calls == []
