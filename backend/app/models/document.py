from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Text
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

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"
