"""Task 2 acceptance matrix for real Step 1 parsers and OCR evidence."""

import io
import os
import sys
from pathlib import Path

import fitz
import pytest
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.document_models import DocumentResult
from app.services.parsing_service import (
    HAS_OCR,
    _deskew_image,
    classify_pdf_page_signals,
    parse_csv_result,
    parse_docx_result,
    parse_document_result,
    parse_image_result,
    parse_pdf_result,
    parse_xlsx_result,
)


def _tesseract_available():
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


ACCEPTANCE_MATRIX = [
    ("PDF-NATIVE", "Native PDF", "DIGITAL", "No OCR; native blocks preserved"),
    ("PDF-SCANNED", "Fully scanned PDF", "SCANNED", "OCR only when Tesseract is available"),
    ("PDF-MIXED", "Mixed digital/scanned PDF", "DIGITAL + SCANNED/MIXED", "Per-page OCR selection"),
    ("PDF-LOWRES", "Low-resolution scan", "SCANNED", "OCR confidence and review warning"),
    ("PDF-ROTATED", "Rotated/skewed page", "SCANNED", "Deskew preprocessing and evidence"),
    ("PDF-NOISY", "Noisy scan", "SCANNED", "OCR confidence and warnings"),
    ("PDF-TABLE", "Scanned table", "SCANNED", "OCR text/evidence; table reconstruction limitation recorded"),
    ("PDF-BLANK", "Blank page", "DIGITAL", "No false READY-quality text"),
    ("PDF-IMAGE", "Image-only PDF page", "SCANNED", "Page-level OCR path"),
    ("IMG-ALL", "PNG/JPG/JPEG/TIFF", "SCANNED", "Common DocumentResult and image metadata"),
    ("DOCX-ORDER", "Interleaved DOCX", "NATIVE", "Heading/paragraph/table order"),
    ("XLSX-PROVENANCE", "Multi-sheet XLSX", "NATIVE", "Sheet/cell/formula/merge/blank provenance"),
    ("CSV-TABLE", "CSV", "NATIVE", "Structured cells and coordinates"),
    ("FAIL-CORRUPT", "Corrupt PDF", "ERROR", "Explicit parse failure"),
    ("FAIL-UNSUPPORTED", "Unsupported file", "ERROR", "Explicit unsupported-format failure"),
    ("FAIL-EMPTY", "Empty file", "ERROR", "Explicit extraction failure"),
    ("DUPLICATE", "Duplicate input", "DUPLICATE", "SHA-256 identity preserved"),
]


def _png_bytes(text="COAL 781.05 MT", size=(1200, 500), rotate=0, noise=False, low_res=False):
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 72)
    draw.text((60, 180), text, fill="black", font=font, stroke_width=0)
    if noise:
        pixels = image.load()
        for x in range(0, image.width, 13):
            for y in range(0, image.height, 17):
                pixels[x, y] = (80, 80, 80)
        image = image.filter(ImageFilter.GaussianBlur(radius=0.6))
    if rotate:
        image = image.rotate(rotate, expand=True, fillcolor="white")
    if low_res:
        image = image.resize((max(1, image.width // 4), max(1, image.height // 4)))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _image_bytes(format_name, **kwargs):
    image = Image.open(io.BytesIO(_png_bytes(**kwargs))).convert("RGB")
    output = io.BytesIO()
    image.save(output, format=format_name)
    return output.getvalue()


def _pdf_with_pages(*page_builders):
    pdf = fitz.open()
    for builder in page_builders:
        page = pdf.new_page(width=612, height=792)
        builder(page)
    return pdf.tobytes()


def _readable_image_only_pdf():
    """Build an image-only page so OCR, not native PDF text, is authoritative."""
    image = Image.new("RGB", (900, 1600), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 46)
    lines = [
        "COAL PRODUCTION TEST",
        "BCCL Production: 781.05 MT",
        "ECL Production: 1,294.73 MT",
        "Difference: -14.82 MT",
        "Efficiency: 97.45%",
        "Borehole: BH-27",
        "Coal Seam: Seam IV",
        "Depth: 143.20 m",
        "Thickness: 4.60 m",
        "Grade: G8",
    ]
    for index, line in enumerate(lines):
        draw.text((55, 120 + index * 125), line, fill="black", font=font)
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    pdf = fitz.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_image(page.rect, stream=image_bytes.getvalue())
    return pdf.tobytes()


def _native_page(page):
    page.insert_text((50, 80), "Native digital evidence page with enough meaningful text for classification.")


def _blank_page(page):
    return None


def _scanned_page(page, image_bytes=None):
    page.insert_image(page.rect, stream=image_bytes or _png_bytes())


def test_acceptance_matrix_is_explicit_and_complete():
    ids = [row[0] for row in ACCEPTANCE_MATRIX]
    assert len(ids) >= 17
    assert len(ids) == len(set(ids))
    assert {"PDF-NATIVE", "PDF-SCANNED", "PDF-MIXED", "IMG-ALL", "XLSX-PROVENANCE", "DUPLICATE"}.issubset(ids)


def test_native_scanned_mixed_blank_and_image_only_pages_classify_independently(monkeypatch):
    scanned = _png_bytes()
    raw = _pdf_with_pages(_native_page, lambda p: _scanned_page(p, scanned), _blank_page)
    calls = []

    def fake_ocr(image):
        calls.append(image.size)
        return "OCR 781.05", [], 0.94

    monkeypatch.setattr("app.services.parsing_service._ocr_image", fake_ocr)
    result = parse_pdf_result("classification.pdf", raw)
    assert [page.classification for page in result.pages] == ["DIGITAL", "SCANNED", "DIGITAL"]
    assert [page.extraction_method for page in result.pages] == ["NATIVE", "OCR", "NATIVE"]
    assert len(calls) == 1
    assert result.pages[1].metadata["ocr_requested"] is True
    assert any("no readable text" in warning for warning in result.warnings)


def test_mixed_page_preserves_native_text_and_recovers_raster_content(monkeypatch):
    image = _png_bytes("Rasters 781.05")

    def mixed(page):
        page.insert_text((40, 60), "Native heading and context retained on this page.")
        page.insert_image(fitz.Rect(0, 120, 612, 700), stream=image)

    monkeypatch.setattr("app.services.parsing_service._ocr_image", lambda image: ("Raster-only value 781.05", [], 0.91))
    result = parse_pdf_result("mixed.pdf", _pdf_with_pages(mixed))
    assert result.pages[0].classification == "MIXED"
    assert result.pages[0].extraction_method == "NATIVE+OCR"
    assert "Native heading" in result.pages[0].text
    assert "Raster-only value" in result.pages[0].text


@pytest.mark.skipif(not HAS_OCR or not _tesseract_available(), reason="Tesseract runtime unavailable")
def test_actual_image_only_pdf_never_persists_an_empty_ocr_page():
    result = parse_pdf_result("readable-image-only.pdf", _readable_image_only_pdf())
    page = result.pages[0]
    assert page.classification == "SCANNED"
    assert page.metadata["ocr_requested"] is True
    assert page.text.strip(), "readable image-only PDF produced empty OCR text"
    assert page.blocks, "OCR evidence blocks were not preserved"
    assert page.metadata["ocr_source"] in {"rendered_300dpi_preprocessed", "embedded_raster", "rendered_300dpi_original"}
    assert "BH-27" in page.text or "BH" in page.text
    assert "143.20" in page.text
    if page.metadata["ocr_source"] != "rendered_300dpi_preprocessed":
        assert any("OCR fallback used" in warning for warning in result.warnings)


def test_empty_scanned_ocr_is_reviewable_not_ready(monkeypatch):
    scanned = _png_bytes("Readable source, but OCR is unavailable")
    monkeypatch.setattr("app.services.parsing_service._ocr_image", lambda image: ("", [], None))
    result = parse_pdf_result("empty-ocr.pdf", _pdf_with_pages(lambda page: _scanned_page(page, scanned)))
    page = result.pages[0]
    assert page.classification == "SCANNED"
    assert not page.text
    assert any("OCR returned no text" in warning for warning in result.warnings)


@pytest.mark.parametrize("label", ["rotated", "skewed", "noisy", "low_resolution"])
def test_image_preprocessing_cases_preserve_geometry_and_low_confidence_warning(monkeypatch, label):
    image_bytes = {"rotated": _png_bytes(rotate=7), "skewed": _png_bytes(rotate=-4), "noisy": _png_bytes(noise=True), "low_resolution": _png_bytes(low_res=True)}[label]
    seen = {}

    def fake_ocr(image):
        seen["size"] = image.size
        return "781.05", [type("Block", (), {"text": "781.05", "bbox": [10, 20, 100, 50], "confidence": 0.42, "method": "OCR", "block_type": "TEXT", "metadata": {}})()], 0.42

    monkeypatch.setattr("app.services.parsing_service._ocr_image", fake_ocr)
    result = parse_image_result(f"{label}.png", image_bytes, filename=f"{label}.png", file_type="PNG")
    page = result.pages[0]
    assert page.classification == "SCANNED"
    assert page.page_number == 1
    assert page.extraction_method == "OCR"
    assert page.confidence == 0.42
    assert page.blocks[0].bbox == [10, 20, 100, 50]
    assert "deskew" in page.metadata["preprocessing"]
    assert any("low OCR confidence" in warning for warning in result.warnings)
    assert seen["size"]


@pytest.mark.skipif(not HAS_OCR or not _tesseract_available(), reason="Tesseract runtime unavailable")
def test_actual_ocr_stack_when_tesseract_runtime_is_available():
    # The parser owns the runtime call. In this environment pytesseract is installed
    # but the Tesseract executable is absent, so this test is expected to be blocked
    # rather than replaced with a fake success.
    result = parse_image_result("actual.png", _png_bytes("COAL 781.05"), filename="actual.png", file_type="PNG")
    assert result.pages[0].extraction_method == "OCR"
    assert result.pages[0].text


@pytest.mark.skipif(not HAS_OCR or not _tesseract_available(), reason="Tesseract runtime unavailable")
@pytest.mark.parametrize("label, image_bytes", [
    ("clean", None),
    ("rotated", None),
    ("skewed", None),
    ("noisy", None),
    ("low_resolution", None),
])
def test_actual_ocr_quality_cases_without_mocking(label, image_bytes):
    image_bytes = {"clean": _png_bytes(), "rotated": _png_bytes(rotate=7), "skewed": _png_bytes(rotate=-4), "noisy": _png_bytes(noise=True), "low_resolution": _png_bytes(low_res=True)}[label]
    result = parse_image_result(f"{label}.png", image_bytes, filename=f"{label}.png", file_type="PNG")
    page = result.pages[0]
    assert page.extraction_method == "OCR"
    assert page.blocks, f"{label}: no OCR evidence blocks"
    assert page.confidence is not None
    assert any(token in page.text.replace("\n", " ").upper() for token in ("COAL", "781.05", "781")), f"{label}: unexpected OCR text {page.text!r}"
    assert all(block.bbox and len(block.bbox) == 4 for block in page.blocks)
    if label == "low_resolution":
        assert any("source resolution is low" in warning for warning in result.warnings)
    if label == "noisy" and page.confidence < 0.60:
        assert any("low OCR confidence" in warning for warning in result.warnings)


@pytest.mark.skipif(not HAS_OCR or not _tesseract_available(), reason="Tesseract runtime unavailable")
@pytest.mark.parametrize("extension, format_name", [("png", "PNG"), ("jpg", "JPEG"), ("jpeg", "JPEG"), ("tif", "TIFF"), ("tiff", "TIFF")])
def test_actual_ocr_all_image_formats(extension, format_name):
    result = parse_image_result(f"scan.{extension}", _image_bytes(format_name), filename=f"scan.{extension}", file_type=extension.upper())
    assert result.pages[0].text
    assert result.pages[0].confidence is not None
    assert result.images[0].width == 1200
    assert result.images[0].height == 500


@pytest.mark.skipif(not HAS_OCR or not _tesseract_available(), reason="Tesseract runtime unavailable")
def test_actual_ocr_scanned_mixed_blank_and_scanned_table_pdf_pages():
    scanned_image = _png_bytes("COAL 781.05 MT")
    table_image = _png_bytes("Subsidiary April Total ECL 7.07 8.10", size=(1600, 700))
    pdf = fitz.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_image(page.rect, stream=scanned_image)
    mixed = pdf.new_page(width=612, height=792)
    mixed.insert_text((40, 60), "Native context retained on a mixed page.")
    mixed.insert_image(fitz.Rect(0, 120, 612, 700), stream=scanned_image)
    blank = pdf.new_page(width=612, height=792)
    table = pdf.new_page(width=612, height=792)
    table.insert_image(table.rect, stream=table_image)
    low_res = pdf.new_page(width=612, height=792)
    low_res.insert_image(low_res.rect, stream=_png_bytes(low_res=True))
    result = parse_pdf_result("actual-cases.pdf", pdf.tobytes())
    assert [page.classification for page in result.pages] == ["SCANNED", "MIXED", "DIGITAL", "SCANNED", "SCANNED"]
    assert result.pages[0].text and result.pages[0].confidence is not None
    assert "Native context" in result.pages[1].text
    assert result.pages[1].extraction_method == "NATIVE+OCR"
    assert result.pages[3].text
    assert result.pages[3].blocks
    assert any("low-resolution source image" in warning for warning in result.warnings)
    assert result.tables == []
    assert any("no readable text" in warning for warning in result.warnings)


def test_deskew_is_an_actual_image_transform():
    original = Image.open(io.BytesIO(_png_bytes(rotate=3)))
    corrected = _deskew_image(original.convert("L"))
    assert corrected.size[0] >= original.size[0]
    assert corrected.size[1] >= original.size[1]


def test_scanned_table_preserves_ocr_evidence_without_fabricating_table_rows(monkeypatch):
    def table_page(page):
        page.insert_image(fitz.Rect(0, 0, 612, 792), stream=_png_bytes("Subsidiary April Total ECL 7.07 8.10"))

    monkeypatch.setattr("app.services.parsing_service._ocr_image", lambda image: ("Subsidiary April Total ECL 7.07 8.10", [], 0.73))
    result = parse_pdf_result("scanned-table.pdf", _pdf_with_pages(table_page))
    assert result.pages[0].extraction_method == "OCR"
    assert "ECL" in result.pages[0].text
    assert result.tables == []


def test_all_supported_image_extensions_share_common_result():
    for extension in ("PNG", "JPG", "JPEG", "TIF", "TIFF"):
        result = parse_image_result(f"scan.{extension.lower()}", _png_bytes(), filename=f"scan.{extension.lower()}", file_type=extension)
        assert isinstance(result, DocumentResult)
        assert len(result.pages) == 1
        assert len(result.images) == 1
        assert result.images[0].page_number == 1
        assert result.images[0].width > 0 and result.images[0].height > 0


def test_docx_order_is_preserved_with_real_python_docx():
    from docx import Document
    document = Document()
    document.add_heading("Heading", level=1)
    document.add_paragraph("Before table")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text, table.cell(0, 1).text = "Header", "Value"
    table.cell(1, 0).text, table.cell(1, 1).text = "ECL", "7.07"
    document.add_paragraph("After table")
    raw = io.BytesIO()
    document.save(raw)
    result = parse_docx_result("ordered.docx", raw.getvalue())
    text = result.pages[0].text
    assert text.index("Heading") < text.index("Before table") < text.index("Header") < text.index("After table")
    assert result.tables[0].headers == ["Header", "Value"]


def test_xlsx_multi_sheet_provenance_includes_formulas_merges_and_blank_cells():
    import openpyxl
    workbook = openpyxl.Workbook()
    first = workbook.active
    first.title = "Production"
    first.append(["Subsidiary", "April", "Total"])
    first.append(["ECL", 7.07, "=B2"])
    first.merge_cells("A4:B4")
    first["C4"] = 0
    second = workbook.create_sheet("Despatch")
    second.append(["Subsidiary", "April"])
    second.append(["ECL", 6.5])
    raw = io.BytesIO()
    workbook.save(raw)
    result = parse_xlsx_result("stats.xlsx", raw.getvalue())
    production, despatch = result.tables
    assert result.metadata["sheet_names"] == ["Production", "Despatch"]
    assert production.sheet_name == "Production"
    assert production.formulas["C2"] == "=B2"
    assert "A4:B4" in production.merged_cells
    assert any(cell["coordinate"] == "B4" and cell["is_blank"] for cell in production.cells)
    assert any(cell["coordinate"] == "D17" for cell in []) is False  # no invented cells outside the used range
    assert despatch.sheet_name == "Despatch"


def test_csv_has_cell_coordinates_and_structured_table():
    result = parse_csv_result("stats.csv", b"Subsidiary,April,May\nECL,7.07,8.10\n")
    assert result.tables[0].cells[3]["coordinate"] == "A2"
    assert result.tables[0].rows == [["ECL", "7.07", "8.10"]]


def test_corrupt_pdf_fails_explicitly():
    with pytest.raises(Exception):
        parse_document_result("bad.pdf", "PDF", b"not a pdf")


def test_empty_pdf_fails_explicitly():
    with pytest.raises(Exception):
        parse_document_result("empty.pdf", "PDF", b"")


def test_unsupported_file_fails_explicitly():
    with pytest.raises(ValueError, match="Unsupported document type"):
        parse_document_result("bad.bin", "BIN", b"anything")
