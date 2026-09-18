from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.models.data_conflict import DataConflict
from app.core.rbac import get_current_user
from app.schemas.dashboard import KpiResponse, DashboardChartsResponse, ProductionChartItem
from app.services.normalization_service import normalize_subsidiary_scope

router = APIRouter(tags=["Dashboard Analytics"])

@router.get("/dashboard/kpis", response_model=KpiResponse)
def get_dashboard_kpis(
    fiscal_year: Optional[str] = None,
    subsidiary_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Computes Executive Command Center KPIs from PostgreSQL tables:
    - Total Production (MT)
    - Total OBR (M.Cu.M)
    - Ingested Documents Count
    - Active Cross-Document Conflicts
    - Calculated Entity Accuracy & Citation Coverage Rates
    """
    norm_sub = normalize_subsidiary_scope(subsidiary_filter)

    # 1. Total Documents (filtered by subsidiary when specific, otherwise global)
    doc_query = db.query(Document)
    if norm_sub:
        doc_query = doc_query.filter(Document.subsidiary == norm_sub)
    total_docs = doc_query.count()

    # 2. Active Conflicts (filtered by subsidiary through related documents and status='OPEN')
    conflict_query = db.query(DataConflict).filter(DataConflict.status == "OPEN")
    if norm_sub:
        conflict_query = conflict_query.join(Document, DataConflict.doc_a_id == Document.id).filter(
            Document.subsidiary == norm_sub
        )
    if fiscal_year:
        conflict_query = conflict_query.filter(DataConflict.fiscal_year == fiscal_year)
    active_conflicts = conflict_query.count()

    # 3. Production & OBR Aggregations from extracted_metrics
    prod_query = db.query(func.sum(ExtractedMetric.standard_value)).filter(
        ExtractedMetric.metric_name.ilike("%production%"),
        ~ExtractedMetric.metric_name.ilike("%target%")
    )
    obr_query = db.query(func.sum(ExtractedMetric.standard_value)).filter(
        ExtractedMetric.metric_name.ilike("%overburden%")
    )

    if fiscal_year:
        prod_query = prod_query.filter(ExtractedMetric.fiscal_year == fiscal_year)
        obr_query = obr_query.filter(ExtractedMetric.fiscal_year == fiscal_year)

    if norm_sub:
        prod_query = prod_query.filter(ExtractedMetric.subsidiary == norm_sub)
        obr_query = obr_query.filter(ExtractedMetric.subsidiary == norm_sub)

    db_prod_sum = prod_query.scalar()
    db_obr_sum = obr_query.scalar()

    total_prod_mt = f"{float(db_prod_sum):,.2f}" if db_prod_sum is not None else "0.00"
    total_obr_mcum = f"{float(db_obr_sum):,.2f}" if db_obr_sum is not None else "0.00"

    # 4. Calculated Entity Accuracy & Citation Coverage (from extracted_metrics)
    metrics_query = db.query(ExtractedMetric)
    if fiscal_year:
        metrics_query = metrics_query.filter(ExtractedMetric.fiscal_year == fiscal_year)
    if norm_sub:
        metrics_query = metrics_query.filter(ExtractedMetric.subsidiary == norm_sub)

    total_metrics = metrics_query.count()
    if total_metrics > 0:
        validated_metrics = metrics_query.filter(ExtractedMetric.validation_status == "VALIDATED").count()
        accuracy_pct = round((validated_metrics / total_metrics) * 100.0, 1)
        accuracy_rate_str = f"{accuracy_pct}%"

        cited_metrics = metrics_query.filter(
            ExtractedMetric.page_number.isnot(None),
            ExtractedMetric.page_number > 0
        ).count()
        coverage_pct = round((cited_metrics / total_metrics) * 100.0, 1)
        citation_coverage_str = f"{coverage_pct}%"
    else:
        accuracy_rate_str = "N/A"
        citation_coverage_str = "N/A"

    return KpiResponse(
        total_production_mt=total_prod_mt,
        total_obr_mcum=total_obr_mcum,
        total_documents=total_docs,
        active_conflicts=active_conflicts,
        entity_accuracy_rate=accuracy_rate_str,
        citation_coverage_rate=citation_coverage_str
    )


@router.get("/dashboard/charts", response_model=DashboardChartsResponse)
def get_dashboard_charts(
    fiscal_year: Optional[str] = None,
    subsidiary_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns live chart data for Production vs Target and OBR removal grouped by subsidiary from extracted_metrics.
    """
    chart_items = []
    
    norm_sub = normalize_subsidiary_scope(subsidiary_filter)
    subsidiaries = ["ECL", "BCCL", "CCL", "WCL", "SECL", "NCL", "MCL"]
    if norm_sub:
        subsidiaries = [norm_sub]

    for sub in subsidiaries:
        prod_query = db.query(func.sum(ExtractedMetric.standard_value)).filter(
            ExtractedMetric.subsidiary == sub,
            ExtractedMetric.metric_name.ilike("%production%"),
            ~ExtractedMetric.metric_name.ilike("%target%"),
            ExtractedMetric.validation_status == "VALIDATED",

        )
        target_query = db.query(func.sum(ExtractedMetric.standard_value)).filter(
            ExtractedMetric.subsidiary == sub,
            ExtractedMetric.metric_name.ilike("%target%"),
            ExtractedMetric.validation_status == "VALIDATED",

        )
        obr_query = db.query(func.sum(ExtractedMetric.standard_value)).filter(
            ExtractedMetric.subsidiary == sub,
            ExtractedMetric.metric_name.ilike("%overburden%"),
            ExtractedMetric.validation_status == "VALIDATED",

        )

        if fiscal_year:
            prod_query = prod_query.filter(ExtractedMetric.fiscal_year == fiscal_year)
            target_query = target_query.filter(ExtractedMetric.fiscal_year == fiscal_year)
            obr_query = obr_query.filter(ExtractedMetric.fiscal_year == fiscal_year)

        prod_val = prod_query.scalar()
        target_val = target_query.scalar()
        obr_val = obr_query.scalar()

        actual = float(prod_val) if prod_val is not None else 0.0
        target = float(target_val) if target_val is not None else None       
        obr = float(obr_val) if obr_val is not None else 0.0

        chart_items.append(ProductionChartItem(
            subsidiary=sub,
            actual=round(actual, 2),
            target=round(target, 2) if target is not None else None,
            obr=round(obr, 2)
            ))
        return DashboardChartsResponse(production_data=chart_items)
