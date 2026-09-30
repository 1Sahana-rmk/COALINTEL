from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from database import Base


class OfficialSource(Base):
    __tablename__ = "official_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    organization = Column(String(200), nullable=False)
    base_url = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=False, default="OFFICIAL_WEBSITE")
    enabled = Column(Boolean, nullable=False, default=True)
    sync_frequency = Column(String(30), nullable=False, default="24h")
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), nullable=False, default="CONNECTED")
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    documents = relationship("OfficialDocument", back_populates="source", cascade="all, delete-orphan")


class OfficialDocument(Base):
    __tablename__ = "official_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("official_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    document_url = Column(Text, nullable=False)
    title = Column(String(500), nullable=True)
    category = Column(String(200), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    checksum = Column(String(64), nullable=True, index=True)
    download_status = Column(String(40), nullable=False, default="DISCOVERED")
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    is_current = Column(Boolean, nullable=False, default=True)
    last_error = Column(Text, nullable=True)
    source_metadata = Column(Text, nullable=True)
    source = relationship("OfficialSource", back_populates="documents")

    __table_args__ = (Index("ix_official_document_url_version", "source_id", "document_url", "version"),)
