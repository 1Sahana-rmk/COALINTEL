from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, Index
from database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    source_id = Column(String(100), primary_key=True, index=True)
    organization = Column(String(150), nullable=False, index=True)
    document_title = Column(String(250), nullable=False)
    document_type = Column(String(100), nullable=False, index=True)  # 'Coal Directory', 'Annual Report', 'Monthly Statistics', 'PIB Release', etc.
    publication_date = Column(String(50), nullable=True)
    financial_year = Column(String(20), nullable=False, index=True)
    url = Column(Text, nullable=True)
    page_number = Column(Integer, nullable=True)
    table_number = Column(String(100), nullable=True)
    chapter = Column(String(100), nullable=True)
    section_name = Column(String(200), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    source_priority = Column(Integer, default=1, nullable=False)  # Tier 1 to 6
    verification_status = Column(String(50), default="verified", nullable=False)

    def __repr__(self):
        return f"<DataSource(id='{self.source_id}', org='{self.organization}', doc='{self.document_title}')>"


class DataObservation(Base):
    __tablename__ = "data_observations"

    observation_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False, index=True)  # 'mine', 'company', 'subsidiary', 'state', 'national'
    entity_id = Column(String(100), nullable=False, index=True)
    metric = Column(String(100), nullable=False, index=True)  # 'production', 'dispatch', 'target', 'obr'
    value = Column(Numeric(16, 6), nullable=False)  # Normalized MT value
    unit = Column(String(30), default="MT", nullable=False)
    original_value = Column(Numeric(16, 4), nullable=True)
    original_unit = Column(String(50), nullable=True)
    financial_year = Column(String(20), nullable=False, index=True)
    period_type = Column(String(20), default="annual", nullable=False)  # 'annual', 'YTD', 'monthly'
    data_status = Column(String(30), default="final", nullable=False)  # 'final', 'provisional'
    granularity = Column(String(30), nullable=False, index=True)  # 'mine', 'company', 'state', 'national'
    source_id = Column(String(100), nullable=False, index=True)
    source_page = Column(Integer, nullable=True)
    source_table = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_data_obs_entity_fy_metric", "entity_id", "financial_year", "metric"),
        Index("ix_data_obs_granularity_fy", "granularity", "financial_year"),
    )

    def __repr__(self):
        return f"<DataObservation(entity='{self.entity_id}', metric='{self.metric}', val={self.value} {self.unit})>"


class DataConflictRecord(Base):
    __tablename__ = "data_conflict_records"

    conflict_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)
    metric = Column(String(100), nullable=False, index=True)
    financial_year = Column(String(20), nullable=False, index=True)
    source_a = Column(String(100), nullable=False)
    value_a = Column(Numeric(14, 4), nullable=False)
    source_b = Column(String(100), nullable=False)
    value_b = Column(Numeric(14, 4), nullable=False)
    difference = Column(Numeric(14, 4), nullable=False)
    difference_percent = Column(Numeric(8, 4), nullable=False)
    possible_reason = Column(String(100), nullable=False)  # 'provisional_vs_final', 'rounding', 'reporting_period_difference', 'revised_data', 'different_definition', 'extraction_error', 'source_error', 'unresolved'
    resolution_status = Column(String(30), default="OPEN", nullable=False, index=True)  # 'OPEN', 'RESOLVED', 'NEEDS_REVIEW'
    resolved_value = Column(Numeric(14, 4), nullable=True)
    resolution_method = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<DataConflictRecord(id={self.conflict_id}, entity='{self.entity_id}', diff={self.difference_percent}%)>"


class DataValidationResult(Base):
    __tablename__ = "data_validation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    validation_type = Column(String(100), nullable=False, index=True)  # 'SUM_OF_MINES_VS_COMPANY', 'SUM_OF_COMPANIES_VS_STATE', 'STATE_TOTALS_VS_NATIONAL', 'ACTUAL_VS_TARGET'
    entity_id = Column(String(100), nullable=False, index=True)
    financial_year = Column(String(20), nullable=False, index=True)
    calculated_value = Column(Numeric(16, 4), nullable=False)
    reported_value = Column(Numeric(16, 4), nullable=False)
    variance = Column(Numeric(16, 4), nullable=False)
    variance_percent = Column(Numeric(8, 4), nullable=False)
    status = Column(String(30), nullable=False, index=True)  # 'PASSED', 'WARNING', 'FAILED'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<DataValidationResult(type='{self.validation_type}', entity='{self.entity_id}', status='{self.status}')>"


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    run_id = Column(String(100), primary_key=True, index=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    source = Column(String(150), nullable=False)
    document = Column(String(250), nullable=False)
    records_found = Column(Integer, default=0, nullable=False)
    records_inserted = Column(Integer, default=0, nullable=False)
    records_updated = Column(Integer, default=0, nullable=False)
    records_rejected = Column(Integer, default=0, nullable=False)
    conflicts_found = Column(Integer, default=0, nullable=False)
    missing_values = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="RUNNING", nullable=False)  # 'COMPLETED', 'FAILED', 'PARTIAL'
    error_log = Column(Text, nullable=True)

    def __repr__(self):
        return f"<IngestionRun(id='{self.run_id}', status='{self.status}', inserted={self.records_inserted})>"
