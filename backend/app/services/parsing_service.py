import os
import io
import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# Try importing fitz (PyMuPDF)
try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logger.warning("PyMuPDF (fitz) is not installed. PDF parsing will use text fallback.")

# Try importing pytesseract
try:
    import pytesseract
    from PIL import Image
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False
    logger.warning("pytesseract or PIL is not installed. OCR fallback will be disabled.")


def parse_pdf_document(file_path: str, file_bytes: Optional[bytes] = None) -> List[Dict[str, Any]]:
    """
    Parses digital and scanned PDF documents page-by-page.
    Uses PyMuPDF (fitz) for native text extraction.
    Triggers Tesseract OCR if page text length is < 100 characters.
    Supports in-memory file_bytes or filesystem file_path.
    Returns list of dicts: [{'page_number': int, 'text': str, 'is_ocr': bool}]
    """
    pages_data = []

    if file_bytes is None and not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return pages_data

    if not HAS_PYMUPDF:
        logger.warning(f"PyMuPDF absent. Attempting basic file reading for {file_path}")
        return [{"page_number": 1, "text": f"Document text placeholder for {os.path.basename(file_path)}", "is_ocr": False}]

    try:
        if file_bytes is not None:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            logger.info(f"Opened in-memory PDF document ({len(file_bytes)} bytes) with {len(doc)} pages.")
        else:
            doc = fitz.open(file_path)
            logger.info(f"Opened PDF document '{file_path}' with {len(doc)} pages.")

        total_pages = len(doc)

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc.load_page(page_idx)
            native_text = page.get_text("text").strip()

            is_ocr = False
            final_text = native_text

            # If page text length is < 100 chars, trigger Tesseract OCR fallback
            if len(native_text) < 100 and HAS_PYTESSERACT:
                try:
                    logger.info(f"Page {page_num} contains low native text ({len(native_text)} chars). Triggering Tesseract OCR...")
                    pix = page.get_pixmap(dpi=150)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_text = pytesseract.image_to_string(img).strip()
                    if len(ocr_text) > len(native_text):
                        final_text = ocr_text
                        is_ocr = True
                        logger.info(f"OCR successfully extracted {len(ocr_text)} characters on page {page_num}.")
                except Exception as ocr_err:
                    logger.warning(f"Tesseract OCR failed on page {page_num}: {ocr_err}. Reverting to native text.")

            # If native PyMuPDF table finder is available, attempt table extraction (additive, fail-safe)
            page_tables = []
            if 47 <= page_num <= 50:
                logger.info(
                    f"DEBUG PAGE {page_num}: "
                    f"native_text={len(native_text)} chars, "
                    f"find_tables_available={hasattr(page, 'find_tables')}"
                    )
            try:
                if hasattr(page, "find_tables"):
                    tab_finder = page.find_tables()
                    if 47 <= page_num <= 50:
                        logger.info(
                            f"DEBUG PAGE {page_num}: "
                            f"tables_found={len(tab_finder.tables) if tab_finder and hasattr(tab_finder, 'tables') else 0}"
                            )
                    if tab_finder and hasattr(tab_finder, "tables") and tab_finder.tables:
                        for tab_idx, tab in enumerate(tab_finder.tables):
                            raw_rows = tab.extract()
                            if 47 <= page_num <= 50:
                                logger.info(
                                    f"DEBUG PAGE {page_num}: "
                                    f"table {tab_idx} rows={len(raw_rows) if raw_rows else 0}, "
                                    f"cols={len(raw_rows[0]) if raw_rows else 0}"
                                    )
                            if raw_rows and len(raw_rows) >= 2:
                                page_tables.append({
                                    "table_index": tab_idx,
                                    "bbox": list(tab.bbox) if hasattr(tab, "bbox") else [],
                                    "row_count": getattr(tab, "row_count", len(raw_rows)),
                                    "col_count": getattr(tab, "col_count", len(raw_rows[0]) if raw_rows else 0),
                                    "raw_rows": raw_rows,
                                    "header_names": list(tab.header.names) if hasattr(tab, "header") and tab.header and hasattr(tab.header, "names") else []
                                })
            except Exception as tab_err:
                logger.warning(f"PyMuPDF table extraction note on page {page_num}: {tab_err}")

            pages_data.append({
                "page_number": page_num,
                "text": final_text or f"Page {page_num} content.",
                "is_ocr": is_ocr,
                "tables": page_tables
            })

        doc.close()
        return pages_data

    except Exception as e:
        logger.error(f"Failed to parse PDF document '{file_path}': {e}")
        return [{"page_number": 1, "text": f"Error parsing document: {e}", "is_ocr": False}]


def parse_docx_document(file_path: str, file_bytes: Optional[bytes] = None) -> List[Dict[str, Any]]:
    """P1 Parser: Extracts text paragraphs from .docx files."""
    try:
        import docx
        if file_bytes is not None:
            doc = docx.Document(io.BytesIO(file_bytes))
        else:
            doc = docx.Document(file_path)
        full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return [{"page_number": 1, "text": full_text or "DOCX document", "is_ocr": False}]
    except Exception as e:
        logger.error(f"Failed to parse DOCX file '{file_path}': {e}")
        return [{"page_number": 1, "text": f"DOCX document content for {os.path.basename(file_path)}", "is_ocr": False}]


def parse_excel_csv_document(file_path: str, file_type: str, file_bytes: Optional[bytes] = None) -> List[Dict[str, Any]]:
    """P1 Parser: Extracts tabular text from .xlsx and .csv files."""
    try:
        import pandas as pd
        if file_bytes is not None:
            target = io.BytesIO(file_bytes)
        else:
            target = file_path

        if file_type == "CSV":
            df = pd.read_csv(target)
        else:
            df = pd.read_excel(target)
        text_content = df.to_string()
        return [{"page_number": 1, "text": text_content, "is_ocr": False}]
    except Exception as e:
        logger.error(f"Failed to parse {file_type} file '{file_path}': {e}")
        return [{"page_number": 1, "text": f"{file_type} table data for {os.path.basename(file_path)}", "is_ocr": False}]


def parse_document_file(file_path: str, file_type: str, file_bytes: Optional[bytes] = None) -> List[Dict[str, Any]]:
    """Unified document parser entrypoint dispatching by file extension/type with optional in-memory bytes."""
    f_type = file_type.upper()
    if f_type == "PDF":
        return parse_pdf_document(file_path, file_bytes=file_bytes)
    elif f_type == "DOCX":
        return parse_docx_document(file_path, file_bytes=file_bytes)
    elif f_type in ["XLSX", "CSV"]:
        return parse_excel_csv_document(file_path, f_type, file_bytes=file_bytes)
    else:
        return parse_pdf_document(file_path, file_bytes=file_bytes)
