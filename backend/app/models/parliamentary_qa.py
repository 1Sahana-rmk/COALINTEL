from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Index
from database import Base


class ParliamentaryQA(Base):
    __tablename__ = "parliamentary_qa"

    question_id = Column(String(100), primary_key=True, index=True)
    question_number = Column(String(50), nullable=True)
    house = Column(String(50), nullable=False, index=True)  # 'Lok Sabha', 'Rajya Sabha'
    date = Column(String(50), nullable=False, index=True)
    ministry = Column(String(100), default="Ministry of Coal", nullable=False)
    subject = Column(String(250), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    source_document = Column(String(200), nullable=True)
    related_mine_id = Column(String(100), nullable=True, index=True)
    related_state = Column(String(100), nullable=True, index=True)
    related_company = Column(String(150), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_parliamentary_house_date", "house", "date"),
    )

    def __repr__(self):
        return f"<ParliamentaryQA(id='{self.question_id}', house='{self.house}', subject='{self.subject[:30]}...')>"
