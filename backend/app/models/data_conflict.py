from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class DataConflict(Base):
    __tablename__ = "data_conflicts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    metric_name = Column(String(100), nullable=False, index=True)
    mine_name = Column(String(100), nullable=False, index=True)
    fiscal_year = Column(String(20), nullable=False, index=True)
    doc_a_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    doc_a_value = Column(Numeric(14, 2), nullable=True)
    doc_b_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    doc_b_value = Column(Numeric(14, 2), nullable=True)
    discrepancy_pct = Column(Numeric(8, 4), nullable=True)  # Discrepancy > 1%
    status = Column(String(20), nullable=False, default="OPEN", index=True)  # 'OPEN', 'RESOLVED', 'IGNORED'
    resolved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    doc_a = relationship("Document", foreign_keys=[doc_a_id], back_populates="conflicts_as_doc_a")
    doc_b = relationship("Document", foreign_keys=[doc_b_id], back_populates="conflicts_as_doc_b")
    resolver = relationship("User", foreign_keys=[resolved_by], back_populates="resolved_conflicts")

    def __repr__(self):
        return f"<DataConflict(id={self.id}, mine='{self.mine_name}', metric='{self.metric_name}', status='{self.status}')>"
