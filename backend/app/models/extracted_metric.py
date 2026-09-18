from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class ExtractedMetric(Base):
    __tablename__ = "extracted_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=True)
    mine_name = Column(String(100), nullable=False, index=True)
    subsidiary = Column(String(100), nullable=True, index=True)
    metric_name = Column(String(100), nullable=False, index=True)  # 'Production', 'Dispatch', 'Overburden', etc.
    numeric_value = Column(Numeric(16, 4), nullable=False)
    unit = Column(String(30), nullable=False)  # Raw extracted unit (e.g. 'Lakh Tonnes', 'MT', 'MCuM')
    raw_unit = Column(String(30), nullable=True)
    standard_value = Column(Numeric(16, 6), nullable=True)  # Standardized value in Million Tonnes (MT) (up to 6 decimals)
    standard_unit = Column(String(10), default="MT", nullable=True)
    fiscal_year = Column(String(20), nullable=False, index=True)
    confidence_score = Column(Numeric(4, 3), nullable=True)  # 0.000 to 1.000
    validation_status = Column(
        String(30),
        nullable=False,
        default="VALIDATED",
        index=True
    )  # 'VALIDATED', 'WARNING_ARITHMETIC', 'CONFLICT_DETECTED', 'UNVERIFIED'
    raw_snippet = Column(Text, nullable=True)
    data_origin = Column(
        String(30),
        default="UNKNOWN",
        nullable=True,
        index=True
    )  # 'OFFICIAL', 'SYNTHETIC_TEST', 'INTERNAL', 'UNKNOWN'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    document = relationship("Document", back_populates="extracted_metrics")

    def __repr__(self):
        return (
            f"<ExtractedMetric(id={self.id}, mine='{self.mine_name}', "
            f"metric='{self.metric_name}', val={self.numeric_value} {self.unit})>"
        )
