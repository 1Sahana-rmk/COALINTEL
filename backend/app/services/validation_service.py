import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.extracted_metric import ExtractedMetric
from app.models.document import Document

logger = logging.getLogger(__name__)

ARITHMETIC_TOLERANCE_PERCENT = 5.0  # Frozen 5.0% threshold


def validate_metric_arithmetic(
    reported_value: float,
    calculated_value: float
) -> Tuple[float, str]:
    """
    Deterministically computes percentage difference and checks against > 5.0% threshold.
    Returns (percentage_difference, status_string).
    """
    if reported_value == 0:
        if calculated_value == 0:
            return 0.0, "VALIDATED"
        return 100.0, "WARNING_ARITHMETIC"

    diff = abs(calculated_value - reported_value)
    pct_diff = round((diff / abs(reported_value)) * 100.0, 2)

    status = "WARNING_ARITHMETIC" if pct_diff > ARITHMETIC_TOLERANCE_PERCENT else "VALIDATED"
    return pct_diff, status


def run_deterministic_validation_feed(
    db: Session,
    subsidiary_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Executes deterministic arithmetic validation across extracted_metrics:
    Computes mine-level totals vs subsidiary aggregates, checks against > 5% threshold,
    and returns detailed validation items.
    """
    query = db.query(ExtractedMetric, Document.filename).\
        join(Document, ExtractedMetric.document_id == Document.id)

    if subsidiary_filter and subsidiary_filter != "ALL":
        query = query.filter(ExtractedMetric.subsidiary == subsidiary_filter)

    metrics = query.all()
    feed_items = []

    for m, filename in metrics:
        pct_diff = None
        discrepancy_available = False
        # The feed status describes this feed's deterministic arithmetic check,
        # not the extraction status persisted on the metric.  A metric can be
        # extracted with high confidence while still having no supported
        # arithmetic operands to validate.
        val_status = "UNVERIFIED"
        msg = "Arithmetic discrepancy unavailable: no supported unit-conversion check for this metric."

        # Perform arithmetic check if raw vs standard conversion exists
        if m.raw_unit and "lakh" in m.raw_unit.lower():
            if m.numeric_value is not None and m.standard_value is not None:
                expected_std = round(float(m.numeric_value) * 0.1, 4)
                pct_diff, calc_status = validate_metric_arithmetic(
                    float(m.standard_value), expected_std
                )
                discrepancy_available = True
                val_status = calc_status
                if calc_status == "WARNING_ARITHMETIC":
                    msg = f"Arithmetic discrepancy > 5% detected: Extracted standard value {m.standard_value} MT differs from calculated {expected_std} MT ({pct_diff}% diff)."
                else:
                    msg = "Deterministic unit conversion and arithmetic check passed."
            else:
                msg = "Arithmetic discrepancy unavailable: conversion operands are incomplete."
        else:
            # A zero here would falsely imply that a comparison was performed.
            # Non-conversion metrics do not have a deterministic arithmetic
            # discrepancy check in this feed.
            msg = "Arithmetic discrepancy unavailable: no supported unit-conversion check for this metric."

        feed_items.append({
            "id": m.id,
            "mine_name": m.mine_name,
            "subsidiary": m.subsidiary,
            "metric_name": m.metric_name,
            "fiscal_year": m.fiscal_year,
            "reported_value": m.standard_value,
            "calculated_value": (
                round(float(m.numeric_value) * 0.1, 4)
                if discrepancy_available
                else None
            ),
            "standard_unit": m.standard_unit,
            "percentage_difference": pct_diff,
            "discrepancy_available": discrepancy_available,
            "validation_status": val_status,
            "message": msg,
            "document_id": m.document_id,
            "filename": filename,
            # Preserve the persisted extraction score as a separate field.
            # ``validation_status`` above describes the deterministic
            # arithmetic check and must not be represented as OCR confidence.
            "extraction_confidence": (
                float(m.confidence_score)
                if m.confidence_score is not None
                else None
            ),
            "page_number": m.page_number,
            "data_origin": m.data_origin,
        })

    return feed_items
