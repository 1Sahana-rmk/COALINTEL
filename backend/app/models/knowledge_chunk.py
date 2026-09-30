"""PostgreSQL-backed, evidence-linked semantic chunk storage.

The table is migration-managed because PostgreSQL must have the pgvector
extension before it can be created.  SQLite remains usable for unit tests via
the JSON fallback type below; it is never used as the production vector
representation.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, TypeDecorator
from sqlalchemy.orm import relationship

from database import Base

try:  # pgvector is an explicit Step 3 dependency, not a silent fallback.
    from pgvector.sqlalchemy import Vector as PGVector
except ImportError:  # pragma: no cover - exercised by the blocked local env
    PGVector = None


class EmbeddingVector(TypeDecorator):
    """384-dimensional pgvector on PostgreSQL, JSON only for SQLite tests."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            if PGVector is None:
                raise RuntimeError(
                    "The pgvector Python package is required for PostgreSQL knowledge chunks."
                )
            return dialect.type_descriptor(PGVector(384))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        values = list(value)
        if len(values) != 384:
            raise ValueError(f"Embedding must have 384 dimensions, received {len(values)}")
        return values

    def process_result_value(self, value, dialect):
        return list(value) if value is not None else None


class KnowledgeChunk(Base):
    """Canonical evidence chunk indexed by the Step 3 retrieval layer."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("ix_knowledge_chunks_document_page", "document_id", "page_number"),
        Index("ix_knowledge_chunks_type", "chunk_type"),
        Index("ix_knowledge_chunks_embedding_status", "embedding_status"),
        Index("ix_knowledge_chunks_content_hash", "content_hash"),
        {"info": {"requires_step3_migration": True}},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_key = Column(String(64), nullable=False, unique=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    document_page_id = Column(Integer, ForeignKey("document_pages.id", ondelete="SET NULL"), nullable=True, index=True)
    document_table_id = Column(Integer, ForeignKey("document_tables.id", ondelete="SET NULL"), nullable=True, index=True)
    page_number = Column(Integer, nullable=True, index=True)
    chunk_index = Column(Integer, nullable=False, default=0)
    chunk_type = Column(String(40), nullable=False)
    chunk_text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    embedding = Column(EmbeddingVector(), nullable=True)
    embedding_provider = Column(String(60), nullable=True)
    embedding_model = Column(String(200), nullable=True)
    embedding_status = Column(String(30), nullable=False, default="UNAVAILABLE")
    content_hash = Column(String(64), nullable=False)
    source_locator_json = Column(JSON, nullable=False, default=dict)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="knowledge_chunks")

    def __repr__(self):
        return f"<KnowledgeChunk(id={self.id}, document_id={self.document_id}, page={self.page_number}, type={self.chunk_type})>"
