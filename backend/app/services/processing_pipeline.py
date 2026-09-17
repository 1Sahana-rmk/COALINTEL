import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.extracted_metric import ExtractedMetric
from app.services.storage_service import document_binary_exists, read_document_binary, file_exists
from app.services.parsing_service import parse_document_file
from app.services.chunking_service import chunk_text_by_tokens
from app.services.normalization_service import (
    extract_entity_tuples_from_text,
    extract_entity_tuples_from_tables,
    classify_document_authority,
)
from app.services.vector_store_service import add_chunks_to_vector_store, delete_document_vectors

logger = logging.getLogger(__name__)


def execute_document_processing_pipeline(db: Session, document_id: int) -> bool:
    """
    Orchestrates the Document Ingestion & Extraction Pipeline with low-memory safety:
    1. Validates document existence and storage binary presence.
    2. Updates status -> 'PROCESSING' and commits initial state.
    3. Retrieves document binary and executes PyMuPDF / OCR page parsing.
    4. Persists total_pages immediately.
    5. Idempotently clears previous derived chunks, metrics, and Chroma vectors for this document.
    6. Splits page text into 500-token chunks and persists to document_chunks.
    7. Extracts entity metrics tuples, applies deterministic unit normalization (-> MT),
       and persists to extracted_metrics.
    8. Indexes chunk vectors into persistent ChromaDB using low-memory ONNX embeddings.
    9. Marks document status -> 'PARSED' and commits final state.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        logger.error(f"Processing pipeline failed: Document ID #{document_id} not found.")
        return False

    # Check storage binary existence before starting processing
    if not document_binary_exists(doc.file_path):
        logger.error(f"Cannot process Document #{doc.id}: source binary missing at '{doc.file_path}'.")
        doc.status = "FAILED"
        doc.error_message = "Source document file is missing from storage. Please re-upload the document."
        db.commit()
        return False

    try:
        logger.info(f"Document #{doc.id} background processing started ('{doc.filename}').")
        doc.status = "PROCESSING"
        doc.error_message = None
        db.commit()

        # Step 1: Retrieve Document Binary & Parse Document Pages (PyMuPDF / OCR)
        logger.info(f"Document #{doc.id} parsing started from storage reference '{doc.file_path}'.")
        try:
            file_bytes = read_document_binary(doc.file_path)
        except Exception as read_err:
            logger.error(f"Failed to read storage binary for Document #{doc.id}: {read_err}")
            doc.status = "FAILED"
            doc.error_message = f"Failed to retrieve document binary from storage: {str(read_err)[:300]}"
            db.commit()
            return False

        pages_data = parse_document_file(doc.file_path, doc.file_type, file_bytes=file_bytes)
        total_pages = len(pages_data)

        if total_pages == 0:
            logger.warning(f"No pages or text extracted from Document #{doc.id}.")
            doc.status = "FAILED"
            doc.error_message = "Document parser could not extract any readable pages or text from file."
            db.commit()
            return False

        # Incremental progress persistence: persist total_pages immediately after parsing
        doc.total_pages = total_pages
        db.commit()
        logger.info(f"Document #{doc.id} parsing completed ({total_pages} pages).")

        # Step 2: Idempotent Cleanup of existing derived records and Chroma vectors
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
        db.query(ExtractedMetric).filter(ExtractedMetric.document_id == doc.id).delete()
        db.flush()
        delete_document_vectors(doc.id)

        all_chunks = []
        all_metrics = []

        # Step 3: Iterate pages -> Chunking & Metric Extraction
        doc_origin = getattr(doc, "data_origin", None) or getattr(doc, "authority", None)
        if not doc_origin:
            doc_origin = classify_document_authority(doc.filename)

        for page_info in pages_data:
            page_num = page_info["page_number"]
            page_text = page_info["text"]

            # Chunking (500 tokens, 50 overlap)
            chunks = chunk_text_by_tokens(page_text, page_number=page_num)
            for c in chunks:
                all_chunks.append(DocumentChunk(
                    document_id=doc.id,
                    page_number=c["page_number"],
                    chunk_index=c["chunk_index"],
                    chunk_text=c["chunk_text"],
                    token_count=c["token_count"],
                    embedding_id=f"chunk_{doc.id}_{c['page_number']}_{c['chunk_index']}"
                ))

            # Entity Metric Extraction from text
            text_metrics = extract_entity_tuples_from_text(
                text=page_text,
                page_number=page_num,
                default_subsidiary=doc.subsidiary or "CIL HQ",
                default_year=doc.fiscal_year
            )

            # Table-aware Metric Extraction from structured tables (additive)
            page_tables = page_info.get("tables", [])
            table_metrics = []
            if page_tables:
                try:
                    table_metrics = extract_entity_tuples_from_tables(
                        tables=page_tables,
                        page_number=page_num,
                        page_text=page_text,
                        default_subsidiary=doc.subsidiary or "CIL HQ",
                        default_year=doc.fiscal_year
                    )
                except Exception as tab_ext_err:
                    logger.warning(f"Table metric extraction note on page {page_num}: {tab_ext_err}")

            # Merge and deduplicate: table metrics take precedence for matching (page, entity, metric, year, value)
            seen_page_keys = set()
            combined_page_metrics = []

            for tm in table_metrics:
                key = (
                    tm["page_number"],
                    (tm.get("subsidiary") or "").upper(),
                    (tm.get("mine_name") or "").upper(),
                    (tm.get("metric_name") or "").upper(),
                    str(tm.get("fiscal_year", "")).strip(),
                    round(float(tm["numeric_value"]), 4)
                )
                seen_page_keys.add(key)
                combined_page_metrics.append(tm)

            for m in text_metrics:
                key = (
                    m["page_number"],
                    (m.get("subsidiary") or "").upper(),
                    (m.get("mine_name") or "").upper(),
                    (m.get("metric_name") or "").upper(),
                    str(m.get("fiscal_year", "")).strip(),
                    round(float(m["numeric_value"]), 4)
                )
                if key not in seen_page_keys:
                    seen_page_keys.add(key)
                    combined_page_metrics.append(m)

            for m in combined_page_metrics:
                all_metrics.append(ExtractedMetric(
                    document_id=doc.id,
                    page_number=m["page_number"],
                    mine_name=m["mine_name"],
                    subsidiary=m["subsidiary"],
                    metric_name=m["metric_name"],
                    numeric_value=m["numeric_value"],
                    unit=m["unit"],
                    raw_unit=m["unit"],
                    standard_value=m["standard_value"],
                    standard_unit=m["standard_unit"],
                    fiscal_year=m["fiscal_year"],
                    confidence_score=m["confidence_score"],
                    validation_status=m.get("validation_status", "VALIDATED"),
                    raw_snippet=m["raw_snippet"],
                    data_origin=doc_origin
                ))

        logger.info(f"Document #{doc.id} chunking completed ({len(all_chunks)} chunks).")
        logger.info(f"Document #{doc.id} normalization completed ({len(all_metrics)} metrics).")

        # Step 4: Bulk Persist to Database & ChromaDB Vector Store
                # Step 5: Persist authoritative extracted data first.
        # PostgreSQL is the source of truth for extracted Ministry of Coal metrics.

        if all_chunks:
            db.bulk_save_objects(all_chunks)
            logger.info(
                f"Document #{doc.id} chunks persisted to PostgreSQL "
                f"({len(all_chunks)} chunks)."
            )

        if all_metrics:
            db.bulk_save_objects(all_metrics)
            logger.info(
                f"Document #{doc.id} extracted metrics persisted to PostgreSQL "
                f"({len(all_metrics)} metrics)."
            )

        # Commit the authoritative extraction before attempting optional
        # vector/embedding operations.
        doc.status = "PARSED"
        doc.error_message = None
        db.commit()

        logger.info(
            f"Document #{doc.id} authoritative extraction committed successfully. "
            f"Status -> PARSED ({len(all_chunks)} chunks, {len(all_metrics)} metrics stored)."
        )

        # Step 6: Optional semantic vector indexing.
        # Failure here must never invalidate the authoritative PostgreSQL data.

        if all_chunks:
            logger.info(
                f"Document #{doc.id} optional embedding/indexing started."
            )

            try:
                vector_success = add_chunks_to_vector_store(
                    all_chunks,
                    filename=doc.filename,
                    subsidiary=doc.subsidiary
                )

                if vector_success:
                    doc.status = "INDEXED"
                    doc.error_message = None
                    db.commit()

                    logger.info(
                        f"Document #{doc.id} vector indexing completed. "
                        f"Status -> INDEXED."
                )
                else:
                    logger.warning(
                    f"Document #{doc.id} vector indexing was unavailable. "
                    f"PostgreSQL extraction remains valid. Status -> PARSED."
                    )

            except Exception as vec_err:
                logger.warning(
                    f"Document #{doc.id} optional vector indexing failed: "
                    f"{type(vec_err).__name__} - {str(vec_err)[:300]}. "
                    f"PostgreSQL extraction remains valid."
                )

        logger.info(
            f"Document #{doc.id} processing completed successfully. "
            f"Status -> PARSED ({len(all_chunks)} chunks, {len(all_metrics)} metrics stored)."
        )

        return True
    except Exception as e:
        db.rollback()
        sanitized_err = str(e)[:450]
        logger.error(f"Document #{document_id} processing failed: {type(e).__name__} - {sanitized_err}")
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "FAILED"
                doc.error_message = f"Processing failed: {sanitized_err}"
                db.commit()
        except Exception as fail_err:
            logger.error(f"Failed to record failure status for Document #{document_id}: {fail_err}")
        return False


def recover_stale_processing_documents(db: Session, stale_minutes: int = 15) -> int:
    """
    Startup and on-demand recovery mechanism for orphaned PROCESSING records.
    Transitions documents that are stale (> stale_minutes) AND have lost storage binaries.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=stale_minutes)

    stale_docs = db.query(Document).filter(Document.status == "PROCESSING").all()
    recovered_count = 0

    for doc in stale_docs:
        doc_time = doc.created_at
        if doc_time is not None and doc_time.tzinfo is None:
            doc_time = doc_time.replace(tzinfo=timezone.utc)

        is_stale = (doc_time is None) or (doc_time < cutoff)

        if is_stale:
            if not document_binary_exists(doc.file_path):
                logger.warning(
                    f"Recovering stale Document #{doc.id} ('{doc.filename}'): "
                    f"Created at {doc.created_at}, storage binary missing. Marking FAILED."
                )
                doc.status = "FAILED"
                doc.error_message = "Processing was interrupted during server restart and source file is unavailable in storage. Please re-upload the document."
                recovered_count += 1
            else:
                logger.info(
                    f"Stale Document #{doc.id} detected and storage binary exists. "
                    f"Starting reprocessing."
                    )
                success = execute_document_processing_pipeline(db, doc.id)
                if success:
                    recovered_count += 1
                    logger.info(f"Successfully reprocessed stale Document #{doc.id}.")
                else:
                    logger.error(f"Failed to reprocess stale Document #{doc.id}.")

    if recovered_count > 0:
        db.commit()
        logger.info(f"Recovered {recovered_count} stale PROCESSING document(s).")

    return recovered_count
