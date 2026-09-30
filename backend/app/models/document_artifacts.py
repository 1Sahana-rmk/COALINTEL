from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from database import Base


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False, default="")
    extraction_method = Column(String(30), nullable=False, default="NATIVE")
    extraction_confidence = Column(Float, nullable=True)
    classification = Column(String(20), nullable=True)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    blocks_json = Column(JSON, nullable=True, default=list)
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    document = relationship("Document", back_populates="pages")


class DocumentTable(Base):
    __tablename__ = "document_tables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    table_number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=True)
    headers_json = Column(JSON, nullable=True, default=list)
    rows_json = Column(JSON, nullable=True, default=list)
    bounding_box_json = Column(JSON, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    extraction_method = Column(String(30), nullable=False, default="NATIVE")
    sheet_name = Column(String(255), nullable=True)
    cells_json = Column(JSON, nullable=True, default=list)
    merged_cells_json = Column(JSON, nullable=True, default=list)
    formulas_json = Column(JSON, nullable=True, default=dict)
    displayed_values_json = Column(JSON, nullable=True, default=dict)
    warnings_json = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    document = relationship("Document", back_populates="tables")


class DocumentImage(Base):
    __tablename__ = "document_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=True)
    image_number = Column(Integer, nullable=False)
    source = Column(String(30), nullable=False, default="embedded")
    mime_type = Column(String(100), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    text = Column(Text, nullable=True)
    bounding_box_json = Column(JSON, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    document = relationship("Document", back_populates="images")
