import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.extracted_metric import ExtractedMetric
from app.models.document import Document
from app.models.data_conflict import DataConflict
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

CONFLICT_THRESHOLD_PERCENT = 1.0  # Frozen 1.0% threshold

GENERIC_MINE_NAMES = {
    "cil mine", "ecl mine", "bccl mine", "secl mine", "cmpdi mine",
    "ccl mine", "wcl mine", "ncl mine", "mcl mine", "nec mine",
    "ministry_of_coal mine", "ministry of coal mine", "mine", "unknown mine",
    "fmc project", "project", "coal project", "unspecified mine", "unspecified"
}


def is_generic_mine_name(mine_name: str) -> bool:
    """Returns True if mine_name is a generic fallback placeholder."""
    if not mine_name:
        return True
    m_clean = mine_name.strip().lower()
    if m_clean in GENERIC_MINE_NAMES or "unspecified" in m_clean:
        return True
    if re.match(r"^(?:cil|ecl|bccl|secl|cmpdi|ccl|wcl|ncl|mcl|nec|ministry_of_coal|ministry of coal|fmc)\s+(?:mine|project|\(unspecified\))$", m_clean):
        return True
    return False


def get_metric_domain(metric_name: str, raw_snippet: str = "") -> str:
    """Classifies a metric into a deterministic domain."""
    m_clean = (metric_name or "").strip().lower()
    snip_clean = (raw_snippet or "").strip().lower()
    combined = f"{m_clean} {snip_clean}"

    if any(k in combined for k in ["drill"]):
        return "DRILLING"
    if any(k in combined for k in ["explor", "geolog"]):
        return "EXPLORATION"
    if any(k in combined for k in ["overburden", "obr", "stripping"]):
        return "OVERBURDEN"
    if any(k in combined for k in ["despatch", "dispatch", "offtake", "market"]):
        return "OFFTAKE_DISPATCH"
    if any(k in combined for k in ["wash", "capacity"]):
        return "CAPACITY"
    if any(k in combined for k in ["production", "output", "mined"]):
        return "PRODUCTION"
    if any(k in combined for k in ["financial", "revenue", "profit", "expenditure", "rs", "crore"]):
        return "FINANCIAL"

    return "OTHER"


def are_units_compatible(unit_a: Optional[str], unit_b: Optional[str]) -> bool:
    """Verifies whether standard units are semantically compatible."""
    if not unit_a or not unit_b:
        return False
    u_a = unit_a.strip().upper()
    u_b = unit_b.strip().upper()
    if u_a == u_b:
        return True

    volume_units = {"M.CU.M", "MCUM", "MILLION CU.M"}
    weight_units = {"MT", "MILLION TONNES", "LAKH TONNES", "TONNES"}

    if u_a in volume_units and u_b in volume_units:
        return True
    if u_a in weight_units and u_b in weight_units:
        return True

    return False


def detect_and_register_cross_document_conflicts(db: Session) -> Dict[str, Any]:
    """
    Executes Evidence-Driven High-Precision Cross-Document Conflict Detection:
    1. Filters out generic fallback entities ("CIL Mine", "ECL Mine", etc.).
    2. Enforces metric domain matching (PRODUCTION vs PRODUCTION, DRILLING vs DRILLING).
    3. Enforces standard unit compatibility (MT vs MT, M.Cu.M vs M.Cu.M).
    4. Evaluates specific named mine/entity discrepancies (>1.0%).
    Returns stats dict: {new_conflicts_count, generic_exclusions, domain_exclusions, unit_exclusions, scope_exclusions}.
    """
    metrics = db.query(ExtractedMetric, Document.filename, Document.subsidiary).\
        join(Document, ExtractedMetric.document_id == Document.id).all()

    # Filter & Group metrics by (mine_name, metric_name, fiscal_year)
    metric_groups: Dict[tuple, List[tuple]] = {}

    stats = {
        "new_conflicts_count": 0,
        "generic_entity_exclusions": 0,
        "domain_incompatibility_exclusions": 0,
        "unit_incompatibility_exclusions": 0,
        "scope_exclusions": 0,
        "threshold_exclusions": 0
    }

    for m, fname, doc_sub in metrics:
        # Rule 1: Exclude generic fallback entity names
        if is_generic_mine_name(m.mine_name):
            stats["generic_entity_exclusions"] += 1
            continue

        domain = get_metric_domain(m.metric_name, m.raw_snippet or "")
        key = (m.mine_name.strip().lower(), m.metric_name.strip().lower(), m.fiscal_year)
        
        if key not in metric_groups:
            metric_groups[key] = []
        metric_groups[key].append((m, fname, doc_sub, domain))

    for key, group in metric_groups.items():
        if len(group) < 2:
            continue

        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                m_a, fname_a, sub_a, dom_a = group[i]
                m_b, fname_b, sub_b, dom_b = group[j]

                # Rule 2: Distinct documents only
                if m_a.document_id == m_b.document_id:
                    continue

                # Rule 3: Metric Domain Compatibility (e.g. DRILLING vs PRODUCTION is invalid)
                if dom_a != dom_b or dom_a == "OTHER":
                    stats["domain_incompatibility_exclusions"] += 1
                    continue

                # Rule 4: Unit Compatibility (e.g. MT vs M.Cu.M or MT vs Metres is invalid)
                if not are_units_compatible(m_a.standard_unit, m_b.standard_unit):
                    stats["unit_incompatibility_exclusions"] += 1
                    continue

                val_a = float(m_a.standard_value) if m_a.standard_value is not None else 0.0
                val_b = float(m_b.standard_value) if m_b.standard_value is not None else 0.0

                ref_val = max(abs(val_a), abs(val_b))
                if ref_val == 0:
                    continue

                diff = abs(val_a - val_b)
                pct_diff = round((diff / ref_val) * 100.0, 2)

                # Rule 5: Discrepancy Threshold (>1.0%)
                if pct_diff <= CONFLICT_THRESHOLD_PERCENT:
                    stats["threshold_exclusions"] += 1
                    continue

                # Rule 6: De-duplicate existing conflict record
                existing = db.query(DataConflict).filter(
                    DataConflict.mine_name == m_a.mine_name,
                    DataConflict.metric_name == m_a.metric_name,
                    DataConflict.fiscal_year == m_a.fiscal_year,
                    or_(
                        (DataConflict.doc_a_id == m_a.document_id) & (DataConflict.doc_b_id == m_b.document_id),
                        (DataConflict.doc_a_id == m_b.document_id) & (DataConflict.doc_b_id == m_a.document_id)
                    )
                ).first()

                if not existing:
                    conflict_rec = DataConflict(
                        doc_a_id=m_a.document_id,
                        doc_b_id=m_b.document_id,
                        mine_name=m_a.mine_name,
                        metric_name=m_a.metric_name,
                        fiscal_year=m_a.fiscal_year,
                        doc_a_value=val_a,
                        doc_b_value=val_b,
                        discrepancy_pct=pct_diff,
                        status="OPEN"
                    )
                    db.add(conflict_rec)
                    stats["new_conflicts_count"] += 1
                    logger.info(
                        f"Registered high-precision conflict for '{m_a.mine_name}' ({m_a.metric_name}, FY{m_a.fiscal_year}): "
                        f"{val_a} vs {val_b} ({pct_diff}% diff > 1%)."
                    )

    if stats["new_conflicts_count"] > 0:
        db.commit()

    return stats


def resolve_data_conflict(
    db: Session,
    conflict_id: int,
    user_id: int,
    resolution_action: str,
    override_value: Optional[float] = None,
    notes: Optional[str] = None
) -> DataConflict:
    """
    Resolves an open data conflict and appends an immutable audit log entry.
    """
    conflict = db.query(DataConflict).filter(DataConflict.id == conflict_id).first()
    if not conflict:
        raise ValueError(f"Conflict ID #{conflict_id} not found.")

    conflict.status = "RESOLVED"
    conflict.resolved_by = user_id
    conflict.resolution_notes = notes or f"Resolved via action '{resolution_action}' by User #{user_id}"

    audit_entry = AuditLog(
        user_id=user_id,
        action="CONFLICT_RESOLVE",
        resource_type="DataConflict",
        resource_id=conflict.id,
        details=f"Resolved conflict #{conflict.id} for {conflict.mine_name} ({conflict.metric_name}). Action: {resolution_action}.",
        details_json={
            "conflict_id": conflict.id,
            "mine_name": conflict.mine_name,
            "metric_name": conflict.metric_name,
            "resolution_action": resolution_action,
            "override_value": override_value
        }
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(conflict)

    return conflict
