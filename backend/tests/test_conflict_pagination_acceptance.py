import os
import sys
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base
from app.api.validation import get_conflict_page, get_conflict_by_id, recompute_conflicts, resolve_conflict_endpoint
from app.models.audit_log import AuditLog
from app.models.data_conflict import DataConflict
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.models.user import User
from app.schemas.validation import ConflictResolveRequest


def test_conflict_list_is_bounded_and_does_not_recompute():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        for index in range(120):
            session.add(DataConflict(
                mine_name=f"Mine {index}",
                metric_name="Coal Production",
                fiscal_year="2023-24",
                doc_a_value=10,
                doc_b_value=12,
                discrepancy_pct=16.67,
                status="OPEN",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ))
        session.commit()
        user = User(id=1, username="admin", email="admin@example.test", role="Admin", subsidiary="CIL HQ")

        with patch("app.api.validation.detect_and_register_cross_document_conflicts") as detector:
            page = get_conflict_page(skip=0, limit=50, db=session, current_user=user)

        assert detector.call_count == 0
        assert page.total == 120
        assert len(page.items) == 50
        assert page.has_next is True
        assert page.limit == 50
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_conflict_list_page_two_is_bounded():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        for index in range(75):
            session.add(DataConflict(
                mine_name=f"Mine {index}",
                metric_name="Coal Production",
                fiscal_year="2023-24",
                doc_a_value=10,
                doc_b_value=12,
                discrepancy_pct=16.67,
                status="OPEN",
            ))
        session.commit()
        user = User(id=1, username="admin", email="admin@example.test", role="Admin", subsidiary="CIL HQ")
        page = get_conflict_page(skip=50, limit=50, db=session, current_user=user)

        assert page.total == 75
        assert len(page.items) == 25
        assert page.has_next is False
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_conflict_list_preserves_direct_page_500_offset():
    """A direct page jump must not be clamped to the legacy 10k offset."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        user = User(id=1, username="admin", email="admin@example.test", role="Admin", subsidiary="CIL HQ")
        with patch(
            "app.api.validation._fetch_conflict_page",
            return_value=([], 65560, {
                "data_conflict_rows": 65555,
                "official_non_overlapping_rows": 5,
                "window_rows_loaded": 50,
            }),
        ) as fetch_page:
            page = get_conflict_page(skip=24950, limit=50, db=session, current_user=user)

        fetch_page.assert_called_once()
        assert fetch_page.call_args.kwargs["skip"] == 24950
        assert page.skip == 24950
        assert page.limit == 50
        assert page.has_next is True
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_recompute_is_explicit_and_separate_from_list_read():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        user = User(id=1, username="admin", email="admin@example.test", role="Admin", subsidiary="CIL HQ")
        stats = {"candidate_pair_count": 4, "discrepancy_count": 2, "new_conflicts_count": 0}
        with patch("app.api.validation.detect_and_register_cross_document_conflicts", return_value=stats) as detector:
            result = recompute_conflicts(db=session, current_user=user)
        detector.assert_called_once_with(session)
        assert result.status == "COMPLETED"
        assert result.stats == stats
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_paginated_generated_id_can_resolve_above_legacy_cutoff():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        conflict = DataConflict(
            id=65555,
            mine_name="MCL",
            metric_name="Coal Production",
            fiscal_year="2023-24",
            doc_a_value=8,
            doc_b_value=18.2,
            discrepancy_pct=56.04,
            status="OPEN",
        )
        session.add(conflict)
        session.commit()
        user = User(id=1, username="admin", email="admin@example.test", role="Admin", subsidiary="CIL HQ")

        page = get_conflict_page(skip=0, limit=50, db=session, current_user=user)
        item = page.items[0]
        assert item.id == 65555
        assert item.conflict_key == "data:65555"

        detail = get_conflict_by_id(id=item.conflict_key, db=session, current_user=user)
        assert detail.conflict_key == "data:65555"
        resolved = resolve_conflict_endpoint(
            id=item.conflict_key,
            payload=ConflictResolveRequest(resolution_action="ACCEPT_DOC_A", notes="Reviewed source pair"),
            db=session,
            current_user=user,
        )
        assert resolved.status == "RESOLVED"
        assert session.query(DataConflict).filter(DataConflict.id == 65555).one().status == "RESOLVED"
        assert session.query(AuditLog).filter(
            AuditLog.resource_type == "DataConflict",
            AuditLog.resource_id == 65555,
            AuditLog.action == "CONFLICT_RESOLVE",
        ).count() == 1

        # Numeric legacy URLs remain compatible and now prefer the generated
        # row instead of applying the obsolete <10000 namespace cutoff.
        legacy_detail = get_conflict_by_id(id=65555, db=session, current_user=user)
        assert legacy_detail.conflict_key == "data:65555"
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_conflict_list_exposes_independent_page_provenance_for_both_sides():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        doc_a = Document(
            id=66, filename="msg-may23.pdf", file_path="/tmp/msg-may23.pdf",
            file_hash="a" * 64, file_type="PDF", status="PARSED", total_pages=12,
        )
        doc_b = Document(
            id=64, filename="msg-july23.pdf", file_path="/tmp/msg-july23.pdf",
            file_hash="b" * 64, file_type="PDF", status="PARSED", total_pages=18,
        )
        session.add_all([
            doc_a,
            doc_b,
            ExtractedMetric(
                id=7001, document_id=66, page_number=1, mine_name="MCL",
                metric_name="Coal Production", numeric_value=8, unit="MT",
                standard_value=8, standard_unit="MT", fiscal_year="2023-24",
                raw_snippet="8 MT",
            ),
            ExtractedMetric(
                id=7002, document_id=64, page_number=7, mine_name="MCL",
                metric_name="Coal Production", numeric_value=18.2, unit="MT",
                standard_value=18.2, standard_unit="MT", fiscal_year="2023-24",
                raw_snippet="18.2 MT",
            ),
            DataConflict(
                id=65555, mine_name="MCL", metric_name="Coal Production",
                fiscal_year="2023-24", doc_a_id=66, doc_a_value=8,
                doc_b_id=64, doc_b_value=18.2, discrepancy_pct=56.04,
                status="OPEN",
            ),
        ])
        session.commit()
        user = User(id=1, username="admin", email="admin@example.test", role="Admin", subsidiary="CIL HQ")

        item = get_conflict_page(skip=0, limit=50, db=session, current_user=user).items[0]

        assert item.conflict_key == "data:65555"
        assert item.evidence_a.document_id == 66
        assert item.evidence_a.metric_id == 7001
        assert item.evidence_a.page_number == 1
        assert item.evidence_a.provenance_available is True
        assert item.evidence_b.document_id == 64
        assert item.evidence_b.metric_id == 7002
        assert item.evidence_b.page_number == 7
        assert item.evidence_b.provenance_available is True
        # The metric schema has no reliable metric-level geometry; the API
        # must not fabricate a bounding box.
        assert item.evidence_a.bounding_box is None
        assert item.evidence_b.bounding_box is None
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_conflict_evidence_explicitly_reports_missing_page_provenance():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        doc = Document(
            id=10, filename="no-page.pdf", file_path="/tmp/no-page.pdf",
            file_hash="c" * 64, file_type="PDF", status="PARSED",
        )
        session.add_all([
            doc,
            ExtractedMetric(
                id=7100, document_id=10, page_number=None, mine_name="MCL",
                metric_name="Coal Production", numeric_value=8, unit="MT",
                standard_value=8, standard_unit="MT", fiscal_year="2023-24",
            ),
            DataConflict(
                id=9, mine_name="MCL", metric_name="Coal Production",
                fiscal_year="2023-24", doc_a_id=10, doc_a_value=8,
                doc_b_id=None, doc_b_value=9, discrepancy_pct=11.11,
                status="OPEN",
            ),
        ])
        session.commit()
        user = User(id=1, username="admin", email="admin@example.test", role="Admin", subsidiary="CIL HQ")
        item = get_conflict_page(skip=0, limit=50, db=session, current_user=user).items[0]

        assert item.evidence_a.metric_id == 7100
        assert item.evidence_a.page_number is None
        assert item.evidence_a.provenance_available is False
        assert "page-level provenance" in item.evidence_a.warning.lower()
        assert item.evidence_b.provenance_available is False
        assert item.evidence_b.document_id is None
    finally:
        session.close()
        Base.metadata.drop_all(engine)
