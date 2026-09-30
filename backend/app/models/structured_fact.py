from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import relationship

from database import Base


class StructuredFact(Base):
    """Evidence-linked Step 2C fact candidate.

    This is deliberately separate from ``extracted_metrics``.  The legacy
    table remains the compatibility surface for existing dashboards and
    validation consumers; this table carries the richer fact and provenance
    contract needed by evidence-linked extraction.
    """

    __tablename__ = "structured_facts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    document_page_id = Column(Integer, ForeignKey("document_pages.id", ondelete="SET NULL"), nullable=True, index=True)
    page_number = Column(Integer, nullable=True, index=True)
    document_table_id = Column(Integer, ForeignKey("document_tables.id", ondelete="SET NULL"), nullable=True, index=True)
    source_metric_id = Column(Integer, ForeignKey("extracted_metrics.id", ondelete="SET NULL"), nullable=True, index=True)

    entity_type = Column(String(40), nullable=False, default="UNKNOWN")
    entity_id = Column(String(120), nullable=True)
    entity_name_raw = Column(Text, nullable=True)
    entity_name_canonical = Column(String(200), nullable=True, index=True)
    entity_resolution_method = Column(String(60), nullable=False, default="UNRESOLVED")
    entity_resolution_confidence = Column(Numeric(5, 4), nullable=True)

    metric_type = Column(String(60), nullable=False, default="UNCLASSIFIED", index=True)
    metric_name_raw = Column(Text, nullable=True)
    metric_name_canonical = Column(String(100), nullable=True, index=True)
    metric_resolution_method = Column(String(60), nullable=False, default="UNRESOLVED")
    metric_resolution_confidence = Column(Numeric(5, 4), nullable=True)

    raw_value_text = Column(Text, nullable=True)
    raw_value_numeric = Column(Numeric(24, 10), nullable=True)
    normalized_value = Column(Numeric(24, 10), nullable=True)
    raw_unit = Column(String(80), nullable=True)
    normalized_unit = Column(String(40), nullable=True)
    period_raw = Column(String(120), nullable=True)
    period_normalized = Column(String(120), nullable=True, index=True)
    period_type = Column(String(30), nullable=True)
    qualifiers_json = Column(JSON, nullable=True, default=dict)

    extraction_method = Column(String(40), nullable=False, default="RULE_BASED")
    extraction_confidence = Column(Numeric(5, 4), nullable=True)
    evidence_type = Column(String(30), nullable=False, default="PAGE")
    evidence_locator_json = Column(JSON, nullable=True, default=dict)
    validation_status = Column(String(40), nullable=False, default="REVIEW_REQUIRED", index=True)
    validation_warnings_json = Column(JSON, nullable=True, default=list)
    fact_status = Column(String(30), nullable=False, default="CANDIDATE", index=True)

    # Stable identity for idempotent persistence and separate semantic groups
    # for repeated facts across source documents.
    fact_key = Column(String(64), nullable=False, unique=True, index=True)
    duplicate_group_key = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="structured_facts")

    __table_args__ = (
        Index("ix_structured_facts_document_period_metric", "document_id", "period_normalized", "metric_name_canonical"),
        Index("ix_structured_facts_entity_metric_period", "entity_name_canonical", "metric_name_canonical", "period_normalized"),
    )

    def __repr__(self):
        return (
            f"<StructuredFact(id={self.id}, entity='{self.entity_name_canonical or self.entity_name_raw}', "
            f"metric='{self.metric_name_canonical or self.metric_name_raw}', status='{self.validation_status}')>"
        )
