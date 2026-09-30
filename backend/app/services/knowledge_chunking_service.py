"""Evidence-aware Step 3 chunk generation and persistence."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models.document_artifacts import DocumentPage, DocumentTable
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.structured_fact import StructuredFact
from app.services.chunking_service import chunk_text_by_tokens


@dataclass(frozen=True)
class KnowledgeChunkSpec:
    chunk_key: str
    document_id: int
    document_page_id: Optional[int]
    document_table_id: Optional[int]
    page_number: Optional[int]
    chunk_index: int
    chunk_type: str
    chunk_text: str
    token_count: int
    content_hash: str
    source_locator: Dict[str, Any]
    metadata: Dict[str, Any]


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _key(document_id: int, chunk_type: str, locator: Dict[str, Any], text: str) -> str:
    payload = json.dumps({"document_id": document_id, "chunk_type": chunk_type, "locator": locator, "text": text}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _looks_like_navigation(text: str, headers: Iterable[Any] = ()) -> bool:
    """Conservative TOC/index filter; ordinary sparse tables remain eligible."""
    combined = " ".join([text, *(_clean(item) for item in headers)]).lower()
    if not any(signal in combined for signal in ("table of contents", "contents", "index", "chapter", "section")):
        return False
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    page_like = sum(bool(re.fullmatch(r"\d{1,4}(?:\s*[-–]\s*\d{1,4})?", line)) for line in lines)
    return page_like >= 1 or any("page" in _clean(header).lower() for header in headers)


def _looks_like_figure(table: DocumentTable) -> bool:
    marker = " ".join(_clean(value) for value in (table.extraction_method, table.title, *(table.warnings_json or []))).lower()
    return any(token in marker for token in ("chart", "figure", "bar graph", "plot"))


def _rows(table: DocumentTable) -> List[List[str]]:
    result: List[List[str]] = []
    for row in table.rows_json or []:
        if isinstance(row, dict):
            values = row.get("values") or row.get("cells") or list(row.values())
        else:
            values = row if isinstance(row, (list, tuple)) else [row]
        result.append([_clean(value) for value in values])
    return result


def _table_context(table: DocumentTable, row: List[str]) -> str:
    title = _clean(table.title)
    headers = [_clean(value) for value in (table.headers_json or [])]
    pairs = [f"{headers[index] if index < len(headers) else f'column_{index + 1}'}: {value}" for index, value in enumerate(row) if value]
    prefix = f"Table {table.table_number}"
    if title:
        prefix += f" — {title}"
    if headers:
        prefix += f" | headers: {' | '.join(headers)}"
    return f"{prefix} | {' | '.join(pairs)}" if pairs else prefix


def _spec(*, document_id: int, page_id: Optional[int], table_id: Optional[int], page_number: Optional[int], chunk_index: int, chunk_type: str, text: str, locator: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Optional[KnowledgeChunkSpec]:
    text = text.strip()
    if not text:
        return None
    content_hash = _content_hash(text)
    return KnowledgeChunkSpec(_key(document_id, chunk_type, locator, text), document_id, page_id, table_id, page_number, chunk_index, chunk_type, text, len(text.split()), content_hash, locator, metadata or {})


def build_knowledge_chunk_specs(db: Session, document_id: int, *, include_fact_candidates: bool = False) -> List[KnowledgeChunkSpec]:
    """Build deterministic chunks from persisted canonical artifacts."""
    specs: List[KnowledgeChunkSpec] = []
    pages = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number).all()
    page_ids = {page.page_number: page.id for page in pages}
    for page in pages:
        page_text = page.text or ""
        if not page_text.strip() or _looks_like_navigation(page_text):
            continue
        blocks = page.blocks_json if isinstance(page.blocks_json, list) else []
        block_texts = [_clean(block.get("text")) for block in blocks if isinstance(block, dict) and _clean(block.get("text"))]
        if block_texts:
            iterable = [(index, text, "TEXT_BLOCK") for index, text in enumerate(block_texts)]
        else:
            iterable = [(int(item.get("chunk_index", 0)), item.get("chunk_text", ""), "PAGE_TEXT") for item in chunk_text_by_tokens(page_text, page_number=page.page_number)]
        for index, text, chunk_type in iterable:
            candidate = _spec(document_id=document_id, page_id=page.id, table_id=None, page_number=page.page_number, chunk_index=index, chunk_type=chunk_type, text=text, locator={"document_page_id": page.id, "page_number": page.page_number, "chunk_index": index}, metadata={"extraction_method": page.extraction_method, "classification": page.classification})
            if candidate:
                specs.append(candidate)

    tables = db.query(DocumentTable).filter(DocumentTable.document_id == document_id).order_by(DocumentTable.page_number, DocumentTable.table_number).all()
    for table in tables:
        headers = [_clean(value) for value in (table.headers_json or [])]
        rows = _rows(table)
        title = _clean(table.title)
        if _looks_like_navigation(f"{title} {' '.join(' '.join(row) for row in rows)}", headers):
            continue
        figure = _looks_like_figure(table)
        table_type = "FIGURE_TEXT" if figure else "TABLE"
        header_text = " | ".join(part for part in [title, " | ".join(headers)] if part)
        candidate = _spec(document_id=table.document_id, page_id=page_ids.get(table.page_number), table_id=table.id, page_number=table.page_number, chunk_index=0, chunk_type=table_type, text=header_text, locator={"document_table_id": table.id, "page_number": table.page_number, "table_number": table.table_number}, metadata={"extraction_method": table.extraction_method, "extraction_confidence": table.extraction_confidence, "structure": "figure" if figure else "table"})
        if candidate:
            specs.append(candidate)
        for row_index, row in enumerate(rows):
            candidate = _spec(document_id=table.document_id, page_id=page_ids.get(table.page_number), table_id=table.id, page_number=table.page_number, chunk_index=row_index + 1, chunk_type="FIGURE_ROW_TEXT" if figure else "TABLE_ROW", text=_table_context(table, row), locator={"document_table_id": table.id, "page_number": table.page_number, "table_number": table.table_number, "row_index": row_index, "column_indices": [i for i, value in enumerate(row) if value]}, metadata={"headers": headers, "structure": "figure" if figure else "table"})
            if candidate:
                specs.append(candidate)

    facts_query = db.query(StructuredFact).filter(StructuredFact.document_id == document_id)
    if not include_fact_candidates:
        facts_query = facts_query.filter(StructuredFact.fact_status == "ACCEPTED")
    for fact in facts_query.order_by(StructuredFact.id):
        value = _clean(fact.raw_value_text or fact.raw_value_numeric or fact.normalized_value)
        text = " | ".join(item for item in (_clean(v) for v in (fact.entity_name_canonical or fact.entity_name_raw, fact.metric_name_canonical or fact.metric_name_raw, value, fact.normalized_unit, fact.period_normalized)) if item)
        candidate = _spec(document_id=fact.document_id, page_id=fact.document_page_id, table_id=fact.document_table_id, page_number=fact.page_number, chunk_index=fact.id, chunk_type="STRUCTURED_FACT", text=text, locator={"structured_fact_id": fact.id, **(fact.evidence_locator_json or {})}, metadata={"fact_status": fact.fact_status, "validation_status": fact.validation_status, "extraction_method": fact.extraction_method})
        if candidate:
            specs.append(candidate)
    return specs


def persist_knowledge_chunks(db: Session, specs: Iterable[KnowledgeChunkSpec], *, replace_document_id: Optional[int] = None) -> Dict[str, int]:
    """Upsert chunks without duplicating stable evidence identities."""
    specs = list(specs)
    if replace_document_id is not None:
        db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == replace_document_id).delete(synchronize_session=False)
    existing = {row.chunk_key: row for row in db.query(KnowledgeChunk).filter(KnowledgeChunk.chunk_key.in_([s.chunk_key for s in specs])).all()} if specs else {}
    inserted = updated = 0
    for spec in specs:
        row = existing.get(spec.chunk_key)
        if row is None:
            row = KnowledgeChunk(chunk_key=spec.chunk_key)
            db.add(row)
            inserted += 1
        else:
            updated += 1
        row.document_id = spec.document_id
        row.document_page_id = spec.document_page_id
        row.document_table_id = spec.document_table_id
        row.page_number = spec.page_number
        row.chunk_index = spec.chunk_index
        row.chunk_type = spec.chunk_type
        row.chunk_text = spec.chunk_text
        row.token_count = spec.token_count
        row.content_hash = spec.content_hash
        row.source_locator_json = spec.source_locator
        row.metadata_json = spec.metadata
        if row.embedding_status is None:
            row.embedding_status = "UNAVAILABLE"
    db.commit()
    return {"generated": len(specs), "inserted": inserted, "updated": updated}
