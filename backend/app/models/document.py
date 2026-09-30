from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Text, JSON, Float
from sqlalchemy.orm import relationship
from database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 Digest
    file_type = Column(String(20), nullable=False)  # 'PDF', 'DOCX', 'XLSX', 'CSV'
    file_size_bytes = Column(BigInteger, nullable=True, default=0)
    subsidiary = Column(String(100), nullable=True, index=True)
    fiscal_year = Column(String(20), nullable=True, index=True)
    status = Column(String(30), nullable=False, default="PENDING", index=True)  # 'PENDING', 'PROCESSING', 'PARSED', 'INDEXED', 'FAILED'
    # Step 1 canonical state.  ``status`` remains for backwards compatibility
    # with the existing UI and downstream metric/RAG code.
    processing_status = Column(String(40), nullable=False, default="DISCOVERED", index=True)
    source_type = Column(String(30), nullable=False, default="MANUAL", index=True)
    source_url = Column(Text, nullable=True, index=True)
    source_organization = Column(String(200), nullable=True)
    title = Column(String(500), nullable=True)
    reporting_period = Column(String(100), nullable=True)
    publication_date = Column(DateTime(timezone=True), nullable=True)
    language = Column(String(30), nullable=True)
    extraction_method = Column(String(40), nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    metadata_json = Column(JSON, nullable=True, default=dict)
    processing_warnings = Column(JSON, nullable=True, default=list)
    document_version = Column(Integer, nullable=False, default=1)
    # Registry linkage is enforced by the migration in deployed databases;
    # keeping this column non-FK in the ORM avoids a circular create/drop
    # dependency between documents and versioned official_documents.
    source_document_id = Column(Integer, nullable=True, index=True)
    total_pages = Column(Integer, nullable=True, default=0)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    uploader = relationship("User", back_populates="documents")
    extracted_metrics = relationship("ExtractedMetric", back_populates="document", cascade="all, delete-orphan")
    document_chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    conflicts_as_doc_a = relationship("DataConflict", foreign_keys="DataConflict.doc_a_id", back_populates="doc_a")
    conflicts_as_doc_b = relationship("DataConflict", foreign_keys="DataConflict.doc_b_id", back_populates="doc_b")
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    tables = relationship("DocumentTable", back_populates="document", cascade="all, delete-orphan")
    images = relationship("DocumentImage", back_populates="document", cascade="all, delete-orphan")
    structured_facts = relationship("StructuredFact", back_populates="document", cascade="all, delete-orphan")
    knowledge_chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"
