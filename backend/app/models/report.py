from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    report_type = Column(String(50), nullable=False, index=True)  # 'PARLIAMENTARY_REPLY', 'ANNUAL_SUMMARY', 'SUBSIDIARY_COMPARISON', 'PRODUCTION_AUDIT'
    fiscal_year = Column(String(20), nullable=True, index=True)
    subsidiary = Column(String(100), nullable=True, index=True)
    content_json = Column(JSON, nullable=True, default=dict)
    approval_status = Column(String(30), nullable=False, default="DRAFT", index=True)  # 'DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED'
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    file_path = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_reports")
    approver = relationship("User", foreign_keys=[approved_by], back_populates="approved_reports")

    def __repr__(self):
        return f"<Report(id={self.id}, title='{self.title}', type='{self.report_type}', status='{self.approval_status}')>"
