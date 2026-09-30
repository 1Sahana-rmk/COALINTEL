from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class DataSourceResponse(BaseModel):
    source_id: str
    organization: str
    document_title: str
    document_type: str
    publication_date: Optional[str] = None
    financial_year: str
    url: Optional[str] = None
    page_number: Optional[int] = None
    table_number: Optional[str] = None
    section_name: Optional[str] = None
    source_priority: int
    verification_status: str

    model_config = ConfigDict(from_attributes=True)


class MineMetricResponse(BaseModel):
    id: int
    mine_id: str
    financial_year: str
    period_type: str
    data_status: str
    production_mt: Optional[float] = None
    production_target_mt: Optional[float] = None
    production_achievement_percent: Optional[float] = None
    dispatch_mt: Optional[float] = None
    dispatch_target_mt: Optional[float] = None
    dispatch_achievement_percent: Optional[float] = None
    star_rating: Optional[int] = None
    obr_mcum: Optional[float] = None
    manpower: Optional[int] = None
    source_id: str
    source_document: Optional[str] = None
    source_url: Optional[str] = None
    source_page: Optional[int] = None
    source_table: Optional[str] = None
    source_published_date: Optional[str] = None
    verification_status: str
    quality_status: str
    data_origin: str

    model_config = ConfigDict(from_attributes=True)


class MineMonthlyMetricResponse(BaseModel):
    id: int
    mine_id: str
    financial_year: str
    month: str
    period_type: str
    production_mt: Optional[float] = None
    dispatch_mt: Optional[float] = None
    target_mt: Optional[float] = None
    achievement_percent: Optional[float] = None
    data_status: str
    as_of_date: Optional[str] = None
    source_id: str
    source_document: Optional[str] = None
    source_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DimensionCountResponse(BaseModel):
    name: str
    count: int
    code: Optional[str] = None


class MineSummaryResponse(BaseModel):
    mine_id: str
    mine_name: str
    canonical_name: str
    company_name: str
    parent_company: Optional[str] = None
    subsidiary_name: Optional[str] = None
    state: str
    district: Optional[str] = None
    block: Optional[str] = None
    coalfield: Optional[str] = None
    coal_or_lignite: str = "Coal"
    mine_type: Optional[str] = None
    mining_method: Optional[str] = None
    sector: Optional[str] = None
    ownership_type: Optional[str] = None
    captive_or_commercial: Optional[str] = None
    operational_status: str = "PRODUCING"
    production_status: Optional[str] = None
    financial_year: Optional[str] = None
    verification_status: Optional[str] = "UNKNOWN"
    data_origin: Optional[str] = "UNKNOWN"
    
    # Latest/Filtered metric view
    latest_production_mt: Optional[float] = None
    latest_target_mt: Optional[float] = None
    latest_achievement_percent: Optional[float] = None
    latest_fiscal_year: Optional[str] = None
    period_type: Optional[str] = None
    data_status: Optional[str] = None
    star_rating: Optional[int] = None
    source_document: Optional[str] = None
    source_url: Optional[str] = None

    # Multi-year trajectory (2024-25, 2025-26, 2026-27 YTD)
    production_fy24_25: Optional[float] = None
    production_fy25_26: Optional[float] = None
    production_fy26_27_ytd: Optional[float] = None
    yoy_growth_percent: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class MineDetailResponse(BaseModel):
    mine_id: str
    mine_name: str
    normalized_mine_name: str
    original_mine_name: Optional[str] = None
    company_name: str
    parent_company: Optional[str] = None
    subsidiary_name: Optional[str] = None
    state: str
    district: Optional[str] = None
    block: Optional[str] = None
    coalfield: Optional[str] = None
    coal_or_lignite: str
    mine_type: Optional[str] = None
    mining_method: Optional[str] = None
    sector: Optional[str] = None
    ownership_type: Optional[str] = None
    allocation_type: Optional[str] = None
    end_use: Optional[str] = None
    operational_status: str
    production_status: Optional[str] = None
    mine_opening_permission: Optional[str] = None
    captive_or_commercial: Optional[str] = None
    financial_year: Optional[str] = None
    source_id: Optional[str] = None
    source_document: Optional[str] = None
    source_url: Optional[str] = None
    source_page: Optional[int] = None
    source_table: Optional[str] = None
    source_chapter: Optional[str] = None
    source_publication_date: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    verification_status: Optional[str] = "UNKNOWN"
    data_origin: Optional[str] = "UNKNOWN"

    # Relationships
    yearly_metrics: List[MineMetricResponse] = []
    monthly_metrics: List[MineMonthlyMetricResponse] = []
    aliases: List[str] = []
    provenance_sources: List[DataSourceResponse] = []

    model_config = ConfigDict(from_attributes=True)



class CoalBlockResponse(BaseModel):
    coal_block_id: str
    coal_block_name: str
    mine_name: Optional[str] = None
    mine_id: Optional[str] = None
    allottee: str
    company: str
    state: str
    district: Optional[str] = None
    allocation_method: Optional[str] = None
    end_use: Optional[str] = None
    sale_of_coal: Optional[str] = None
    production_status: Optional[str] = None
    production_mt: Optional[float] = None
    target_production_mt: Optional[float] = None
    peak_rated_capacity_mtpa: Optional[float] = None
    source_id: str

    model_config = ConfigDict(from_attributes=True)


class DataConflictRecordResponse(BaseModel):
    conflict_id: int
    entity_type: str
    entity_id: str
    metric: str
    financial_year: str
    source_a: str
    value_a: float
    source_b: str
    value_b: float
    difference: float
    difference_percent: float
    possible_reason: str
    resolution_status: str
    resolved_value: Optional[float] = None
    resolution_method: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DataValidationResultResponse(BaseModel):
    id: int
    validation_type: str
    entity_id: str
    financial_year: str
    calculated_value: float
    reported_value: float
    variance: float
    variance_percent: float
    status: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
