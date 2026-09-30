"""Optional COALINTEL domain adapter kept outside generic ingestion."""

from app.services.normalization_service import extract_entity_tuples_from_text, extract_entity_tuples_from_tables, classify_document_authority

__all__ = ["extract_entity_tuples_from_text", "extract_entity_tuples_from_tables", "classify_document_authority"]
