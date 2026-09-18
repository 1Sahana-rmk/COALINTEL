import logging
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from starlette import status as http_status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError

from database import get_db
from app.schemas.mine import (
    MineSummaryResponse,
    MineDetailResponse,
    CoalBlockResponse,
    DataSourceResponse,
    DataConflictRecordResponse,
    DataValidationResultResponse,
    DimensionCountResponse
)
from app.services import mine_service

logger = logging.getLogger("COALINTEL-MINES-API")
router = APIRouter(tags=["Government Mine Intelligence"])


@router.get("/mines", response_model=List[MineSummaryResponse])
def get_mines(
    response: Response,
    fiscal_year: Optional[str] = Query(None, description="Fiscal year filter, e.g. '2024-25', '2025-26', '2026-27'"),
    subsidiary: Optional[str] = Query(None, description="Subsidiary filter, e.g. 'SECL', 'MCL', 'NCL'"),
    company: Optional[str] = Query(None, description="Company filter, e.g. 'Coal India Limited', 'NTPC'"),
    state: Optional[str] = Query(None, description="State filter, e.g. 'Chhattisgarh', 'Odisha', 'Tamil Nadu'"),
    district: Optional[str] = Query(None, description="District filter"),
    mine_type: Optional[str] = Query(None, description="Mine type, e.g. 'OC', 'UG', 'Mixed'"),
    sector: Optional[str] = Query(None, description="Sector/Ownership filter, e.g. 'CIL', 'Captive', 'Commercial'"),
    ownership: Optional[str] = Query(None, description="Ownership filter"),
    coal_or_lignite: Optional[str] = Query(None, description="Fuel filter, e.g. 'Coal', 'Lignite'"),
    status: Optional[str] = Query(None, description="Operational status, e.g. 'PRODUCING', 'UNDER_DEVELOPMENT'"),
    search: Optional[str] = Query(None, description="Search term for mine name, ID, state, district, or company"),
    sort_by: Optional[str] = Query("name", description="Sort by 'name', 'production', 'state', 'subsidiary', 'type', 'status'"),
    sort_order: Optional[str] = Query("asc", description="Sort order 'asc' or 'desc'"),
    page: Optional[int] = Query(None, ge=1, description="1-indexed page number"),
    page_size: Optional[int] = Query(None, ge=1, le=500, description="Items per page"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Returns authentic Government of India canonical mines data.
    Supports search, multi-field filtering, sorting, and pagination.
    Emits X-Total-Count header for pagination awareness.
    """
    actual_skip = skip
    actual_limit = limit
    if page is not None and page_size is not None:
        actual_skip = (page - 1) * page_size
        actual_limit = page_size
    elif page_size is not None:
        actual_limit = page_size

    try:
        items, total_count = mine_service.get_mines_list(
            db=db,
            fiscal_year=fiscal_year,
            subsidiary=subsidiary,
            company=company,
            state=state,
            district=district,
            mine_type=mine_type,
            sector=sector,
            ownership=ownership,
            coal_or_lignite=coal_or_lignite,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=actual_skip,
            limit=actual_limit
        )
        response.headers["X-Total-Count"] = str(total_count)
        return items
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_mines: {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mine Intelligence registry is temporarily unavailable. Database migration or synchronization in progress."
        )


@router.get("/mines/stats")
def get_mines_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns comprehensive summary statistics and dimensional breakdowns
    across canonical mines, fuel types, mine types, states, and sectors.
    """
    try:
        return mine_service.get_mines_stats_data(db=db)
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_mines_stats: {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mine Intelligence statistics service is temporarily unavailable."
        )


@router.get("/mines-summary-stats")
def get_mines_summary_stats_alias(db: Session = Depends(get_db)):
    """Backward-compatible alias for /mines/stats."""
    try:
        return mine_service.get_mines_stats_data(db=db)
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_mines_summary_stats_alias: {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mine Intelligence statistics service is temporarily unavailable."
        )


@router.get("/mines/states", response_model=List[DimensionCountResponse])
def get_mines_states(db: Session = Depends(get_db)):
    """Returns dynamic list of all represented states with canonical mine counts."""
    try:
        return mine_service.get_states_list(db=db)
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_mines_states: {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mine Intelligence states service is temporarily unavailable."
        )


@router.get("/mines/subsidiaries", response_model=List[DimensionCountResponse])
def get_mines_subsidiaries(db: Session = Depends(get_db)):
    """Returns dynamic list of all operating subsidiaries with canonical mine counts."""
    try:
        return mine_service.get_subsidiaries_list(db=db)
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_mines_subsidiaries: {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mine Intelligence subsidiaries service is temporarily unavailable."
        )


@router.get("/mines/sectors", response_model=List[DimensionCountResponse])
def get_mines_sectors(db: Session = Depends(get_db)):
    """Returns dynamic list of ownership sectors with canonical mine counts."""
    try:
        return mine_service.get_sectors_list(db=db)
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_mines_sectors: {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mine Intelligence sectors service is temporarily unavailable."
        )


@router.get("/mines/types", response_model=List[DimensionCountResponse])
@router.get("/mines/mine-types", response_model=List[DimensionCountResponse])
def get_mines_types(db: Session = Depends(get_db)):
    """Returns dynamic list of mine types (OC, UG, Mixed) with canonical mine counts."""
    try:
        return mine_service.get_mine_types_list(db=db)
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_mines_types: {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mine Intelligence mine types service is temporarily unavailable."
        )


@router.get("/mines/companies", response_model=List[DimensionCountResponse])
def get_mines_companies(db: Session = Depends(get_db)):
    """Returns dynamic list of operating companies with canonical mine counts."""
    try:
        return mine_service.get_companies_list(db=db)
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_mines_companies: {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mine Intelligence companies service is temporarily unavailable."
        )


@router.get("/coal-blocks", response_model=List[CoalBlockResponse])
@router.get("/mines/coal-blocks", response_model=List[CoalBlockResponse])
def get_coal_blocks(
    search: Optional[str] = Query(None, description="Search term for block name, allottee, or coalfield"),
    state: Optional[str] = Query(None, description="State filter"),
    allocation_status: Optional[str] = Query(None, description="Allocation status, e.g. 'Operational', 'Under Development'"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Returns captive and commercial coal blocks allocated by the Nominated Authority, Ministry of Coal.
    Supported under both /coal-blocks and /mines/coal-blocks.
    """
    try:
        return mine_service.get_coal_blocks_list(
            db=db,
            search=search,
            state=state,
            allocation_status=allocation_status,
            skip=skip,
            limit=limit
        )
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_coal_blocks: {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coal blocks registry service is temporarily unavailable."
        )


@router.get("/data-sources", response_model=List[DataSourceResponse])
@router.get("/mines/data-sources", response_model=List[DataSourceResponse])
def get_data_sources(db: Session = Depends(get_db)):
    """
    Returns the authoritative Government of India data source catalog (Tiers 1-6)
    with publication dates, document titles, reference numbers, and verification statuses.
    Supported under both /data-sources and /mines/data-sources.
    """
    try:
        return mine_service.get_data_sources_list(db=db)
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_data_sources: {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data sources catalog is temporarily unavailable."
        )


@router.get("/data-conflicts", response_model=List[DataConflictRecordResponse])
@router.get("/mines/conflicts", response_model=List[DataConflictRecordResponse])
@router.get("/mines/data-conflicts", response_model=List[DataConflictRecordResponse])
def get_data_conflicts(
    resolution_status: Optional[str] = Query(None, description="Filter by resolution status, e.g. 'RESOLVED', 'OPEN'"),
    db: Session = Depends(get_db)
):
    """
    Returns cross-document discrepancy records identified between official publications.
    """
    try:
        return mine_service.get_data_conflicts_list(db=db, resolution_status=resolution_status)
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_data_conflicts: {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data conflicts service is temporarily unavailable."
        )


@router.get("/data-validations", response_model=List[DataValidationResultResponse])
@router.get("/mines/validations", response_model=List[DataValidationResultResponse])
@router.get("/mines/data-validations", response_model=List[DataValidationResultResponse])
def get_data_validations(
    status_filter: Optional[str] = Query(None, description="Filter by status, e.g. 'VERIFIED_EXACT', 'WITHIN_TOLERANCE', 'DISCREPANCY_NOTED'"),
    db: Session = Depends(get_db)
):
    """
    Returns arithmetic verification checks (sum of mines vs company/state/national benchmarks).
    """
    try:
        return mine_service.get_data_validations_list(db=db, status_filter=status_filter)
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_data_validations: {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data validations service is temporarily unavailable."
        )


# IMPORTANT: Parameterized route /{mine_id} placed AFTER all specific static subpaths
@router.get("/mines/{mine_id}", response_model=MineDetailResponse)
def get_mine_details(
    mine_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves full canonical details, yearly metrics, monthly metrics, aliases,
    and authoritative source citations for a single mine.
    """
    try:
        mine = mine_service.get_mine_detail(db=db, mine_id=mine_id)
    except (OperationalError, ProgrammingError) as db_err:
        logger.error(f"Database error in get_mine_details for '{mine_id}': {db_err}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mine registry service is temporarily unavailable."
        )

    if not mine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Mine with ID '{mine_id}' not found in canonical registry."
        )
    return mine
