import re
from typing import Optional, Sequence
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


def _fiscal_year_sort_key(value: Optional[str]) -> tuple[int, int, str]:
    """Sort fiscal-year labels by their represented year, without inventing a default year."""
    text = (value or "").strip()
    match = re.search(r"(20\d{2})\s*[-/]\s*(\d{2,4})", text)
    if not match:
        return (-1, -1, text)
    start = int(match.group(1))
    end_text = match.group(2)
    end = int(end_text if len(end_text) == 4 else f"{start // 100}{end_text}")
    return (start, end, text)


def _is_provisional_observation(metric: ExtractedMetric) -> bool:
    """Use persisted period/document metadata to label YTD/provisional observations honestly."""
    document = getattr(metric, "document", None)
    metadata = getattr(document, "metadata_json", None) if document else None
    metadata_text = " ".join(str(value) for value in metadata.values()) if isinstance(metadata, dict) else str(metadata or "")
    evidence = " ".join(
        str(value or "")
        for value in (
            getattr(metric, "raw_snippet", None),
            getattr(document, "reporting_period", None) if document else None,
            getattr(document, "title", None) if document else None,
            getattr(document, "filename", None) if document else None,
            metadata_text,
        )
    ).lower()
    # 2026-27 is already defined as YTD/provisional by the existing dashboard
    # fiscal-year catalogue/chart semantics; this does not select it as latest.
    return bool(re.search(r"\b(?:ytd|year\s*to\s*date|provisional|q[1-4])\b", evidence)) or (
        (getattr(metric, "fiscal_year", "") or "").strip() == "2026-27"
    )


def _latest_metric_observation(
    metrics: Sequence[ExtractedMetric],
) -> tuple[Optional[str], Optional[float], Optional[str]]:
    """Return the latest fiscal-year bucket and its sum, never a cross-year sum."""
    usable = [metric for metric in metrics if metric.fiscal_year and metric.standard_value is not None]
    if not usable:
        return None, None, None
    latest_year = max((metric.fiscal_year for metric in usable), key=_fiscal_year_sort_key)
    latest_metrics = [metric for metric in usable if metric.fiscal_year == latest_year]
    total = sum(float(metric.standard_value) for metric in latest_metrics)
    is_provisional = any(_is_provisional_observation(metric) for metric in latest_metrics)
    period_label = f"FY {latest_year}" + (" (YTD Provisional)" if is_provisional else "")
    return latest_year, total, period_label


def normalize_dashboard_fiscal_year(value: Optional[str]) -> Optional[str]:
    """Treat the explicit all-years UI value as an omitted API filter."""
    if not value or value.strip().upper() in {"ALL", "ALL FISCAL YEARS"}:
        return None
    return value.strip()

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
    fiscal_year = normalize_dashboard_fiscal_year(fiscal_year)

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

    # 3. Production & OBR aggregations from extracted_metrics.
    # Specific FY behavior remains the historical sum for that selected year.
    prod_query = db.query(func.sum(ExtractedMetric.standard_value)).filter(
        ExtractedMetric.metric_name.ilike("%production%"),
        ~ExtractedMetric.metric_name.ilike("%target%")
    )
    obr_query = db.query(func.sum(ExtractedMetric.standard_value)).filter(
        ExtractedMetric.metric_name.ilike("%overburden%")
    )
    prod_metrics_query = db.query(ExtractedMetric).filter(
        ExtractedMetric.metric_name.ilike("%production%"),
        ~ExtractedMetric.metric_name.ilike("%target%"),
        ExtractedMetric.standard_value.isnot(None),
    )
    obr_metrics_query = db.query(ExtractedMetric).filter(
        ExtractedMetric.metric_name.ilike("%overburden%"),
        ExtractedMetric.standard_value.isnot(None),
    )

    if fiscal_year:
        prod_query = prod_query.filter(ExtractedMetric.fiscal_year == fiscal_year)
        obr_query = obr_query.filter(ExtractedMetric.fiscal_year == fiscal_year)
        prod_metrics_query = prod_metrics_query.filter(ExtractedMetric.fiscal_year == fiscal_year)
        obr_metrics_query = obr_metrics_query.filter(ExtractedMetric.fiscal_year == fiscal_year)

    if norm_sub:
        prod_query = prod_query.filter(ExtractedMetric.subsidiary == norm_sub)
        obr_query = obr_query.filter(ExtractedMetric.subsidiary == norm_sub)
        prod_metrics_query = prod_metrics_query.filter(ExtractedMetric.subsidiary == norm_sub)
        obr_metrics_query = obr_metrics_query.filter(ExtractedMetric.subsidiary == norm_sub)

    db_prod_sum = prod_query.scalar()
    db_obr_sum = obr_query.scalar()

    production_period = f"FY {fiscal_year}" if fiscal_year else None
    obr_period = f"FY {fiscal_year}" if fiscal_year else None

    if fiscal_year is None:
        # All Fiscal Years is an intentional view. Select the latest persisted
        # observation bucket, but never add unlike fiscal years together.
        prod_metrics = prod_metrics_query.all()
        obr_metrics = obr_metrics_query.all()
        _, latest_prod, production_period = _latest_metric_observation(prod_metrics)
        _, latest_obr, obr_period = _latest_metric_observation(obr_metrics)
        total_prod_mt = f"{latest_prod:,.2f}" if latest_prod is not None else "N/A"
        total_obr_mcum = f"{latest_obr:,.2f}" if latest_obr is not None else "N/A"
    else:
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
        total_production_period=production_period,
        total_obr_period=obr_period,
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
    fiscal_year = normalize_dashboard_fiscal_year(fiscal_year)
    subsidiaries = ["ECL", "BCCL", "CCL", "WCL", "SECL", "NCL", "MCL"]
    if norm_sub:
        subsidiaries = [norm_sub]

    available_years_query = db.query(ExtractedMetric.fiscal_year).filter(
        ExtractedMetric.fiscal_year.isnot(None),
        ExtractedMetric.subsidiary.in_(subsidiaries),
    )
    available_fiscal_years = sorted({
        row[0] for row in available_years_query.distinct().all() if row[0]
    }, reverse=True)

    if fiscal_year is None:
        # For all-years scope, return a time series: one row per fiscal year.
        # This preserves the annual dimension and avoids adding unlike years.
        scope_query = db.query(ExtractedMetric.fiscal_year).filter(
            ExtractedMetric.fiscal_year.isnot(None),
            ExtractedMetric.subsidiary.in_(subsidiaries),
        )
        fiscal_years = sorted({row[0] for row in scope_query.distinct().all() if row[0]})
        if fiscal_years:
            for year in fiscal_years:
                def grouped_value(pattern: str, exclude_target: bool = False):
                    query = db.query(func.sum(ExtractedMetric.standard_value)).filter(
                        ExtractedMetric.subsidiary.in_(subsidiaries),
                        ExtractedMetric.fiscal_year == year,
                        ExtractedMetric.metric_name.ilike(pattern),
                        ExtractedMetric.validation_status == "VALIDATED",
                    )
                    if exclude_target:
                        query = query.filter(~ExtractedMetric.metric_name.ilike("%target%"))
                    return query.scalar()

                actual = grouped_value("%production%", exclude_target=True)
                target = grouped_value("%target%")
                obr = grouped_value("%overburden%")
                chart_items.append(ProductionChartItem(
                    subsidiary=norm_sub or "All CIL",
                    fiscal_year=year,
                    actual=round(float(actual), 2) if actual is not None else 0.0,
                    target=round(float(target), 2) if target is not None else None,
                    obr=round(float(obr), 2) if obr is not None else 0.0,
                ))
            return DashboardChartsResponse(
                production_data=chart_items,
                available_fiscal_years=available_fiscal_years,
            )

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

    return DashboardChartsResponse(
        production_data=chart_items,
        available_fiscal_years=available_fiscal_years,
    )
