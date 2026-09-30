from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="Viewer")  # 'Admin', 'Analyst', 'Reviewer', 'Viewer'
    subsidiary = Column(String(100), nullable=True, default="CIL HQ")
    full_name = Column(String(150), nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    documents = relationship("Document", back_populates="uploader")
    created_reports = relationship("Report", foreign_keys="Report.created_by", back_populates="creator")
    approved_reports = relationship("Report", foreign_keys="Report.approved_by", back_populates="approver")
    audit_logs = relationship("AuditLog", back_populates="user")
    resolved_conflicts = relationship("DataConflict", foreign_keys="DataConflict.resolved_by", back_populates="resolver")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
