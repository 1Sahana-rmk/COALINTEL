import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base
import app.models  # noqa: F401 - register all models before create_all
from app.api import sources
from app.models.official_source import OfficialSource
from app.services.official_source_connector import DiscoveryResult
from app.services.official_sync_service import recover_interrupted_source_syncs, sync_official_source, try_claim_source_sync


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_source_claim_is_atomic_and_second_request_is_rejected():
    db = make_db()
    source = OfficialSource(name="Ministry", organization="Ministry", base_url="https://coal.nic.in/major-statistics-page")
    db.add(source)
    db.commit()
    db.refresh(source)

    assert try_claim_source_sync(db, source.id) is True
    assert try_claim_source_sync(db, source.id) is False
    db.refresh(source)
    assert source.status == "SYNCING"


def test_manual_sync_returns_accepted_without_waiting_for_worker():
    source = SimpleNamespace(id=7, name="Ministry of Coal")
    user = SimpleNamespace(id=11)
    db = Mock()
    with patch.object(sources, "ensure_ministry_source", return_value=source), \
         patch.object(sources, "try_claim_source_sync", return_value=True), \
         patch.object(sources._SYNC_EXECUTOR, "submit") as submit:
        result = sources.sync_ministry_of_coal(db=db, current_user=user)

    assert result["accepted"] is True
    assert result["status"] == "SYNCING"
    assert result["source_id"] == 7
    submit.assert_called_once_with(sources._run_ministry_sync_job, 7, 11)


def test_manual_sync_duplicate_request_returns_conflict():
    source = SimpleNamespace(id=7, name="Ministry of Coal")
    user = SimpleNamespace(id=11)
    db = Mock()
    with patch.object(sources, "ensure_ministry_source", return_value=source), \
         patch.object(sources, "try_claim_source_sync", return_value=False):
        try:
            sources.sync_ministry_of_coal(db=db, current_user=user)
            assert False, "expected HTTP 409"
        except sources.HTTPException as exc:
            assert exc.status_code == 409


def test_sync_completion_clears_syncing_state_and_failure_is_explicit():
    db = make_db()
    source = OfficialSource(name="Ministry", organization="Ministry", base_url="https://coal.nic.in/major-statistics-page")
    db.add(source)
    db.commit()
    db.refresh(source)

    class EmptyConnector:
        def discover_documents_with_report(self):
            return DiscoveryResult()

        def close(self):
            pass

    result = sync_official_source(db, source, EmptyConnector())
    assert result["status"] == "CONNECTED"
    db.refresh(source)
    assert source.status == "CONNECTED"
    successful_timestamp = source.last_success_at
    assert successful_timestamp is not None

    class BrokenConnector:
        def discover_documents_with_report(self):
            raise RuntimeError("source unavailable")

    result = sync_official_source(db, source, BrokenConnector())
    assert result["status"] == "ERROR"
    db.refresh(source)
    assert source.status == "ERROR"
    assert "source unavailable" in source.last_error
    assert source.last_success_at == successful_timestamp


def test_last_success_at_is_written_at_terminal_completion_not_attempt_start():
    db = make_db()
    source = OfficialSource(name="Ministry", organization="Ministry", base_url="https://coal.nic.in/major-statistics-page")
    db.add(source)
    db.commit()
    db.refresh(source)

    markers = {}

    class SlowConnector:
        def discover_documents_with_report(self):
            markers["discovery_finished"] = datetime.now(timezone.utc)
            return DiscoveryResult()

    result = sync_official_source(db, source, SlowConnector())
    db.refresh(source)

    assert result["status"] == "CONNECTED"
    assert source.last_sync_at is not None
    assert source.last_success_at is not None
    success_at = source.last_success_at.replace(tzinfo=timezone.utc)
    sync_at = source.last_sync_at.replace(tzinfo=timezone.utc)
    assert success_at >= markers["discovery_finished"]
    assert success_at >= sync_at


def test_restart_reconciles_orphaned_sync_claim():
    db = make_db()
    source = OfficialSource(
        name="Ministry",
        organization="Ministry",
        base_url="https://coal.nic.in/major-statistics-page",
        status="SYNCING",
    )
    db.add(source)
    db.commit()
    assert recover_interrupted_source_syncs(db) == 1
    db.refresh(source)
    assert source.status == "ERROR"
    assert "backend restart" in source.last_error
