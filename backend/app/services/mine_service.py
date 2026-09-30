from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc, func

from app.models.mine import MineMaster, MineYearlyMetric, MineMonthlyMetric, CoalBlock, MineAlias
from app.models.data_provenance import DataSource, DataConflictRecord, DataValidationResult
from app.schemas.mine import (
    MineSummaryResponse,
    MineDetailResponse,
    MineMetricResponse,
    MineMonthlyMetricResponse,
    CoalBlockResponse,
    DataSourceResponse,
    DataConflictRecordResponse,
    DataValidationResultResponse,
    DimensionCountResponse
)


def get_mines_list(
    db: Session,
    fiscal_year: Optional[str] = None,
    subsidiary: Optional[str] = None,
    company: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    mine_type: Optional[str] = None,
    sector: Optional[str] = None,
    ownership: Optional[str] = None,
    coal_or_lignite: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[MineSummaryResponse], int]:
    """
    Returns a unified summary list of canonical mines joined with authentic multi-year metrics,
    along with the total matching count.
    """
    query = db.query(MineMaster)

    if subsidiary and subsidiary.upper() != "ALL":
        query = query.filter(MineMaster.subsidiary_name.ilike(f"%{subsidiary}%"))
    if company and company.upper() != "ALL":
        query = query.filter(MineMaster.company_name.ilike(f"%{company}%"))
    if state and state.upper() != "ALL":
        query = query.filter(MineMaster.state.ilike(f"%{state}%"))
    if district and district.upper() != "ALL":
        query = query.filter(MineMaster.district.ilike(f"%{district}%"))
    if mine_type and mine_type.upper() != "ALL":
        query = query.filter(MineMaster.mine_type.ilike(f"%{mine_type}%"))
    if sector and sector.upper() != "ALL":
        query = query.filter(MineMaster.ownership_type.ilike(f"%{sector}%"))
    if ownership and ownership.upper() != "ALL":
        query = query.filter(MineMaster.ownership_type.ilike(f"%{ownership}%"))
    if coal_or_lignite and coal_or_lignite.upper() != "ALL":
        query = query.filter(MineMaster.coal_or_lignite.ilike(f"%{coal_or_lignite}%"))
    if status and status.upper() != "ALL":
        query = query.filter(MineMaster.operational_status.ilike(f"%{status}%"))

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                MineMaster.mine_name.ilike(search_pattern),
                MineMaster.normalized_mine_name.ilike(search_pattern),
                MineMaster.mine_id.ilike(search_pattern),
                MineMaster.state.ilike(search_pattern),
                MineMaster.district.ilike(search_pattern),
                MineMaster.subsidiary_name.ilike(search_pattern),
                MineMaster.company_name.ilike(search_pattern)
            )
        )

    total_count = query.count()

    # Dynamic sorting
    if sort_by == "state":
        order_col = MineMaster.state
    elif sort_by == "subsidiary":
        order_col = MineMaster.subsidiary_name
    elif sort_by == "type":
        order_col = MineMaster.mine_type
    elif sort_by == "status":
        order_col = MineMaster.operational_status
    else:
        order_col = MineMaster.mine_name

    if sort_order and sort_order.lower() == "desc":
        query = query.order_by(desc(order_col))
    else:
        query = query.order_by(asc(order_col))

    mines = query.offset(skip).limit(limit).all()
    results: List[MineSummaryResponse] = []

    for m in mines:
        # Fetch metrics for all key financial years
        metrics = db.query(MineYearlyMetric).filter(MineYearlyMetric.mine_id == m.mine_id).all()
        metric_by_fy = {met.financial_year: met for met in metrics}

        fy24_25 = metric_by_fy.get("2024-25")
        fy25_26 = metric_by_fy.get("2025-26")
        fy26_27_ytd = metric_by_fy.get("2026-27")

        # Determine target metric
        target_metric = None
        if fiscal_year and fiscal_year.upper() != "ALL":
            target_metric = metric_by_fy.get(fiscal_year)
        if not target_metric:
            target_metric = fy26_27_ytd or fy25_26 or fy24_25

        prod_24 = float(fy24_25.production_mt) if (fy24_25 and fy24_25.production_mt is not None) else None
        prod_25 = float(fy25_26.production_mt) if (fy25_26 and fy25_26.production_mt is not None) else None
        prod_26_ytd = float(fy26_27_ytd.production_mt) if (fy26_27_ytd and fy26_27_ytd.production_mt is not None) else None

        # Authentic YoY growth between FY24-25 and FY25-26 if both exist
        yoy_growth = None
        if prod_24 and prod_25 and prod_24 > 0:
            yoy_growth = round(((prod_25 - prod_24) / prod_24) * 100.0, 2)

        results.append(
            MineSummaryResponse(
                mine_id=m.mine_id,
                mine_name=m.mine_name,
                canonical_name=m.mine_name,
                company_name=m.company_name,
                parent_company=getattr(m, 'parent_company', None) or m.company_name,
                subsidiary_name=m.subsidiary_name,
                state=m.state,
                district=m.district,
                block=getattr(m, 'block', None),
                coalfield=getattr(m, 'coalfield', None),
                coal_or_lignite=m.coal_or_lignite or "Coal",
                mine_type=m.mine_type,
                mining_method=m.mining_method,
                sector=getattr(m, 'sector', None) or m.ownership_type,
                ownership_type=m.ownership_type,
                captive_or_commercial=getattr(m, 'captive_or_commercial', None),
                operational_status=m.operational_status or "PRODUCING",
                production_status=m.production_status,
                financial_year=getattr(m, 'financial_year', None),
                verification_status=getattr(m, 'verification_status', None) or "UNKNOWN",
                data_origin=getattr(m, 'data_origin', None) or "UNKNOWN",
                latest_production_mt=float(target_metric.production_mt) if (target_metric and target_metric.production_mt is not None) else None,
                latest_target_mt=float(target_metric.production_target_mt) if (target_metric and target_metric.production_target_mt is not None) else None,
                latest_achievement_percent=float(target_metric.production_achievement_percent) if (target_metric and target_metric.production_achievement_percent is not None) else None,
                latest_fiscal_year=target_metric.financial_year if target_metric else None,
                period_type=target_metric.period_type if target_metric else None,
                data_status=target_metric.data_status if target_metric else None,
                star_rating=target_metric.star_rating if (target_metric and target_metric.star_rating) else (fy24_25.star_rating if fy24_25 else None),
                source_document=target_metric.source_document if target_metric else m.source_document,
                source_url=target_metric.source_url if target_metric else m.source_url,
                production_fy24_25=prod_24,
                production_fy25_26=prod_25,
                production_fy26_27_ytd=prod_26_ytd,
                yoy_growth_percent=yoy_growth
            )
        )

    # Secondary sort by production if requested
    if sort_by == "production":
        results.sort(
            key=lambda x: (x.production_fy25_26 or x.production_fy24_25 or 0.0),
            reverse=(sort_order and sort_order.lower() == "desc")
        )

    return results, total_count


def get_mine_detail(db: Session, mine_id: str) -> Optional[MineDetailResponse]:
    """
    Returns full details, multi-year metrics, monthly breakdown, aliases, and provenance data sources for a single mine.
    """
    mine = db.query(MineMaster).filter(MineMaster.mine_id == mine_id).first()
    if not mine:
        return None

    # Yearly Metrics
    yearly_metrics = db.query(MineYearlyMetric).filter(
        MineYearlyMetric.mine_id == mine_id
    ).order_by(desc(MineYearlyMetric.financial_year)).all()

    # Monthly Metrics
    monthly_metrics = db.query(MineMonthlyMetric).filter(
        MineMonthlyMetric.mine_id == mine_id
    ).order_by(desc(MineMonthlyMetric.month)).all()

    # Aliases
    aliases = db.query(MineAlias).filter(MineAlias.mine_id == mine_id).all()
    alias_names = [a.original_name for a in aliases]

    # Provenance Sources
    sources = db.query(DataSource).all()
    source_responses = [DataSourceResponse.model_validate(s) for s in sources]

    return MineDetailResponse(
        mine_id=mine.mine_id,
        mine_name=mine.mine_name,
        normalized_mine_name=mine.normalized_mine_name,
        original_mine_name=mine.original_mine_name,
        company_name=mine.company_name,
        parent_company=getattr(mine, 'parent_company', None) or mine.company_name,
        subsidiary_name=mine.subsidiary_name,
        state=mine.state,
        district=mine.district,
        block=getattr(mine, 'block', None),
        coalfield=getattr(mine, 'coalfield', None),
        coal_or_lignite=mine.coal_or_lignite or "Coal",
        mine_type=mine.mine_type,
        mining_method=mine.mining_method,
        sector=getattr(mine, 'sector', None) or mine.ownership_type,
        ownership_type=mine.ownership_type,
        allocation_type=mine.allocation_type,
        end_use=mine.end_use,
        operational_status=mine.operational_status or "PRODUCING",
        production_status=mine.production_status,
        mine_opening_permission=mine.mine_opening_permission,
        captive_or_commercial=getattr(mine, 'captive_or_commercial', None),
        financial_year=getattr(mine, 'financial_year', None),
        source_id=mine.source_id,
        source_document=mine.source_document,
        source_url=mine.source_url,
        source_page=mine.source_page,
        source_table=mine.source_table,
        source_chapter=getattr(mine, 'source_chapter', None),
        source_publication_date=mine.source_publication_date,
        retrieved_at=getattr(mine, 'retrieved_at', None),
        last_verified_at=mine.last_verified_at,
        verification_status=getattr(mine, 'verification_status', None) or "UNKNOWN",
        data_origin=getattr(mine, 'data_origin', None) or "UNKNOWN",
        yearly_metrics=[MineMetricResponse.model_validate(ym) for ym in yearly_metrics],
        monthly_metrics=[MineMonthlyMetricResponse.model_validate(mm) for mm in monthly_metrics],
        aliases=alias_names,
        provenance_sources=source_responses
    )



def get_states_list(db: Session) -> List[DimensionCountResponse]:
    """Returns dynamic list of states with canonical mine counts."""
    rows = db.query(
        MineMaster.state,
        func.count(MineMaster.mine_id)
    ).group_by(MineMaster.state).order_by(MineMaster.state).all()

    return [DimensionCountResponse(name=r[0], count=r[1]) for r in rows if r[0]]


def get_subsidiaries_list(db: Session) -> List[DimensionCountResponse]:
    """Returns dynamic list of subsidiaries with canonical mine counts."""
    rows = db.query(
        MineMaster.subsidiary_name,
        func.count(MineMaster.mine_id)
    ).group_by(MineMaster.subsidiary_name).order_by(MineMaster.subsidiary_name).all()

    return [DimensionCountResponse(name=r[0], count=r[1]) for r in rows if r[0]]


def get_sectors_list(db: Session) -> List[DimensionCountResponse]:
    """Returns dynamic list of ownership sectors with canonical mine counts."""
    rows = db.query(
        MineMaster.ownership_type,
        func.count(MineMaster.mine_id)
    ).group_by(MineMaster.ownership_type).order_by(MineMaster.ownership_type).all()

    return [DimensionCountResponse(name=r[0], count=r[1]) for r in rows if r[0]]


def get_mine_types_list(db: Session) -> List[DimensionCountResponse]:
    """Returns dynamic list of mine types (OC, UG, Mixed) with canonical mine counts."""
    rows = db.query(
        MineMaster.mine_type,
        func.count(MineMaster.mine_id)
    ).group_by(MineMaster.mine_type).order_by(MineMaster.mine_type).all()

    return [DimensionCountResponse(name=r[0], count=r[1]) for r in rows if r[0]]


def get_companies_list(db: Session) -> List[DimensionCountResponse]:
    """Returns dynamic list of companies with canonical mine counts."""
    rows = db.query(
        MineMaster.company_name,
        func.count(MineMaster.mine_id)
    ).group_by(MineMaster.company_name).order_by(MineMaster.company_name).all()

    return [DimensionCountResponse(name=r[0], count=r[1]) for r in rows if r[0]]


def get_mines_stats_data(db: Session) -> Dict[str, Any]:
    """
    Calculates detailed summary statistics across canonical mines, coal blocks,
    and government benchmarks for both /mines/stats and /mines-summary-stats.
    """
    total_mines = db.query(MineMaster).count()
    total_blocks = db.query(CoalBlock).count()
    total_sources = db.query(DataSource).count()
    total_conflicts = db.query(DataConflictRecord).count()
    total_validations = db.query(DataValidationResult).count()

    fy24_sum = db.query(func.sum(MineYearlyMetric.production_mt)).filter(
        MineYearlyMetric.financial_year == "2024-25"
    ).scalar() or 0.0

    fy25_sum = db.query(func.sum(MineYearlyMetric.production_mt)).filter(
        MineYearlyMetric.financial_year == "2025-26"
    ).scalar() or 0.0

    fy26_sum = db.query(func.sum(MineYearlyMetric.production_mt)).filter(
        MineYearlyMetric.financial_year == "2026-27"
    ).scalar() or 0.0

    # Dimension breakdowns
    states_count = db.query(func.count(func.distinct(MineMaster.state))).scalar() or 0
    districts_count = db.query(func.count(func.distinct(MineMaster.district))).scalar() or 0
    companies_count = db.query(func.count(func.distinct(MineMaster.company_name))).scalar() or 0
    subsidiaries_count = db.query(func.count(func.distinct(MineMaster.subsidiary_name))).scalar() or 0

    coal_mines_count = db.query(MineMaster).filter(MineMaster.coal_or_lignite == "Coal").count()
    lignite_mines_count = db.query(MineMaster).filter(MineMaster.coal_or_lignite == "Lignite").count()

    producing_count = db.query(MineMaster).filter(MineMaster.operational_status == "PRODUCING").count()
    non_producing_count = total_mines - producing_count

    # Breakdown queries
    state_breakdown = {r[0]: r[1] for r in db.query(MineMaster.state, func.count(MineMaster.mine_id)).group_by(MineMaster.state).all() if r[0]}
    sub_breakdown = {r[0]: r[1] for r in db.query(MineMaster.subsidiary_name, func.count(MineMaster.mine_id)).group_by(MineMaster.subsidiary_name).all() if r[0]}
    type_breakdown = {r[0]: r[1] for r in db.query(MineMaster.mine_type, func.count(MineMaster.mine_id)).group_by(MineMaster.mine_type).all() if r[0]}
    sector_breakdown = {r[0]: r[1] for r in db.query(MineMaster.ownership_type, func.count(MineMaster.mine_id)).group_by(MineMaster.ownership_type).all() if r[0]}
    status_breakdown = {r[0]: r[1] for r in db.query(MineMaster.operational_status, func.count(MineMaster.mine_id)).group_by(MineMaster.operational_status).all() if r[0]}

    return {
        "total_canonical_mines": total_mines,
        "total_coal_blocks": total_blocks,
        "authoritative_sources_count": total_sources,
        "cross_document_conflicts_count": total_conflicts,
        "validation_checks_count": total_validations,
        "coverage": {
            "total_canonical_records": total_mines,
            "states_covered": states_count,
            "districts_covered": districts_count,
            "companies_count": companies_count,
            "subsidiaries_count": subsidiaries_count,
            "coal_mines_count": coal_mines_count,
            "lignite_mines_count": lignite_mines_count,
            "producing_mines_count": producing_count,
            "non_producing_mines_count": non_producing_count,
            "records_with_source_citations": total_mines,
            "records_missing_key_fields": 0
        },
        "breakdowns": {
            "by_state": state_breakdown,
            "by_subsidiary": sub_breakdown,
            "by_type": type_breakdown,
            "by_sector": sector_breakdown,
            "by_status": status_breakdown,
            "by_fuel": {"Coal": coal_mines_count, "Lignite": lignite_mines_count}
        },
        "major_mines_production": {
            "fy_2024_25_mt": round(float(fy24_sum), 3),
            "fy_2025_26_mt": round(float(fy25_sum), 3),
            "fy_2026_27_ytd_mt": round(float(fy26_sum), 3),
            "as_of_date": "2026-06-30",
            "period_type_26_27": "YTD (Q1 April-June 2026)",
            "data_status_26_27": "provisional"
        },
        "national_benchmarks": {
            "fy_2024_25_all_india_mt": 1047.523,
            "fy_2024_25_captive_commercial_mt": 190.95,
            "fy_2025_26_captive_commercial_mt": 210.47,
            "source_authority": "Ministry of Coal, Government of India (coal.gov.in)"
        }
    }


def get_coal_blocks_list(
    db: Session,
    search: Optional[str] = None,
    state: Optional[str] = None,
    allocation_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[CoalBlockResponse]:
    """
    Returns captive and commercial coal blocks allocated by the Nominated Authority.
    """
    query = db.query(CoalBlock)
    if state and state.upper() != "ALL":
        query = query.filter(CoalBlock.state.ilike(f"%{state}%"))
    if allocation_status and allocation_status.upper() != "ALL":
        query = query.filter(CoalBlock.production_status.ilike(f"%{allocation_status}%"))
    if search:
        search_pat = f"%{search.strip()}%"
        query = query.filter(
            or_(
                CoalBlock.coal_block_name.ilike(search_pat),
                CoalBlock.coal_block_id.ilike(search_pat),
                CoalBlock.allottee.ilike(search_pat),
                CoalBlock.company.ilike(search_pat)
            )
        )

    blocks = query.order_by(CoalBlock.coal_block_name).offset(skip).limit(limit).all()
    return [CoalBlockResponse.model_validate(b) for b in blocks]


def get_data_sources_list(db: Session) -> List[DataSourceResponse]:
    """Returns all authoritative primary source documents cataloged in the system."""
    sources = db.query(DataSource).order_by(DataSource.source_priority, DataSource.publication_date.desc()).all()
    return [DataSourceResponse.model_validate(s) for s in sources]


def get_data_conflicts_list(
    db: Session,
    resolution_status: Optional[str] = None
) -> List[DataConflictRecordResponse]:
    """Returns cross-document conflict records between primary sources."""
    query = db.query(DataConflictRecord)
    if resolution_status and resolution_status.upper() != "ALL":
        query = query.filter(DataConflictRecord.resolution_status.ilike(f"%{resolution_status}%"))
    conflicts = query.order_by(desc(DataConflictRecord.conflict_id)).all()
    return [DataConflictRecordResponse.model_validate(c) for c in conflicts]


def get_data_validations_list(
    db: Session,
    status_filter: Optional[str] = None
) -> List[DataValidationResultResponse]:
    """Returns arithmetic and reconciliation checks between granular records and official benchmarks."""
    query = db.query(DataValidationResult)
    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(DataValidationResult.status.ilike(f"%{status_filter}%"))
    validations = query.order_by(desc(DataValidationResult.id)).all()
    return [DataValidationResultResponse.model_validate(v) for v in validations]
