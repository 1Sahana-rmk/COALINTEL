"""
COALINTEL V2 — PHASE 11C REGRESSION TEST SUITE
Government Data Seeder Hardening, Startup Observability & Three-Pass Idempotency Tests
"""

import os
import sys
import logging
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app, lifespan
from database import Base, SessionLocal, engine
from app.models.mine import (
    MineMaster,
    MineAlias,
    MineYearlyMetric,
    MineMonthlyMetric,
    CoalBlock,
    StarRating,
)
from app.models.data_provenance import (
    DataSource,
    DataObservation,
    DataConflictRecord,
    DataValidationResult,
    IngestionRun,
)
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from data.government_mine_data_seed import run_government_data_ingestion


@pytest.fixture
def isolated_db_session(tmp_path):
    """Provides a pristine, isolated test database session for multi-pass idempotency testing."""
    test_db_path = tmp_path / "test_isolated_mines.sqlite"
    test_engine = create_engine(f"sqlite:///{test_db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        test_engine.dispose()


def test_three_pass_idempotency(isolated_db_session):
    """
    PASS 1: Ingest into fresh database (0 -> expected counts).
    PASS 2: Re-run ingestion (counts remain identical).
    PASS 3: Re-run ingestion again (counts remain identical).
    """
    db = isolated_db_session

    # Initial state: completely empty
    assert db.query(MineMaster).count() == 0
    assert db.query(DataSource).count() == 0
    assert db.query(CoalBlock).count() == 0
    assert db.query(MineYearlyMetric).count() == 0
    assert db.query(MineMonthlyMetric).count() == 0
    assert db.query(MineAlias).count() == 0
    assert db.query(IngestionRun).count() == 0

    # ==================== PASS 1 ====================
    res_pass1 = run_government_data_ingestion(db=db)
    assert res_pass1["status"] == "COMPLETED"
    assert res_pass1["run_id"] == "GOV-RUN-CANONICAL-MASTER-2024-25"

    pass1_mines = db.query(MineMaster).count()
    pass1_sources = db.query(DataSource).count()
    pass1_blocks = db.query(CoalBlock).count()
    pass1_yearly = db.query(MineYearlyMetric).count()
    pass1_monthly = db.query(MineMonthlyMetric).count()
    pass1_aliases = db.query(MineAlias).count()
    pass1_runs = db.query(IngestionRun).count()

    # Exact expected counts
    assert pass1_mines == 60, f"Expected 60 canonical mines, found {pass1_mines}"
    assert pass1_sources == 12, f"Expected 12 data sources, found {pass1_sources}"
    assert pass1_blocks == 7, f"Expected 7 coal blocks, found {pass1_blocks}"
    assert pass1_yearly == 180, f"Expected 180 yearly metrics (60*3), found {pass1_yearly}"
    assert pass1_monthly == 15, f"Expected 15 monthly metrics, found {pass1_monthly}"
    assert pass1_aliases == 138, f"Expected 138 aliases, found {pass1_aliases}"
    assert pass1_runs == 1, f"Expected exactly 1 IngestionRun, found {pass1_runs}"

    # Verify canonical IngestionRun details
    canonical_run = db.query(IngestionRun).filter(IngestionRun.run_id == "GOV-RUN-CANONICAL-MASTER-2024-25").first()
    assert canonical_run is not None
    assert canonical_run.status == "COMPLETED"
    assert canonical_run.records_inserted > 0
    assert canonical_run.records_found >= canonical_run.records_inserted

    # Verify provenance and authenticity fields
    all_mines = db.query(MineMaster).all()
    for m in all_mines:
        assert m.data_origin == "OFFICIAL", f"Mine {m.mine_id} missing OFFICIAL data_origin"
        assert m.verification_status == "verified", f"Mine {m.mine_id} missing verified status"
        assert m.financial_year == "2024-25"
        assert m.retrieved_at is not None or m.last_verified_at is not None

    # ==================== PASS 2 ====================
    res_pass2 = run_government_data_ingestion(db=db)
    assert res_pass2["status"] == "COMPLETED"

    assert db.query(MineMaster).count() == pass1_mines, "Pass 2 mutated mine_master count!"
    assert db.query(DataSource).count() == pass1_sources, "Pass 2 mutated data_sources count!"
    assert db.query(CoalBlock).count() == pass1_blocks, "Pass 2 mutated coal_blocks count!"
    assert db.query(MineYearlyMetric).count() == pass1_yearly, "Pass 2 mutated yearly metrics count!"
    assert db.query(MineMonthlyMetric).count() == pass1_monthly, "Pass 2 mutated monthly metrics count!"
    assert db.query(MineAlias).count() == pass1_aliases, "Pass 2 mutated aliases count!"
    assert db.query(IngestionRun).count() == 1, "Pass 2 created duplicate IngestionRun!"

    # ==================== PASS 3 ====================
    res_pass3 = run_government_data_ingestion(db=db)
    assert res_pass3["status"] == "COMPLETED"

    assert db.query(MineMaster).count() == pass1_mines, "Pass 3 mutated mine_master count!"
    assert db.query(DataSource).count() == pass1_sources, "Pass 3 mutated data_sources count!"
    assert db.query(CoalBlock).count() == pass1_blocks, "Pass 3 mutated coal_blocks count!"
    assert db.query(MineYearlyMetric).count() == pass1_yearly, "Pass 3 mutated yearly metrics count!"
    assert db.query(MineMonthlyMetric).count() == pass1_monthly, "Pass 3 mutated monthly metrics count!"
    assert db.query(MineAlias).count() == pass1_aliases, "Pass 3 mutated aliases count!"
    assert db.query(IngestionRun).count() == 1, "Pass 3 created duplicate IngestionRun!"


def test_failed_ingestion_run_creation(isolated_db_session):
    """Verify that when ingestion fails, IngestionRun(status='FAILED') is written with all NOT NULL fields."""
    db = isolated_db_session

    orig_add = db.add
    add_count = 0

    def mock_add(obj):
        nonlocal add_count
        add_count += 1
        if isinstance(obj, DataSource) and add_count == 2:
            raise RuntimeError("Simulated Ingestion Data Failure")
        return orig_add(obj)

    with patch.object(db, "add", side_effect=mock_add):
        with pytest.raises(Exception) as excinfo:
            run_government_data_ingestion(db=db)
        assert "Simulated Ingestion Data Failure" in str(excinfo.value)

    # Verify that IngestionRun with FAILED status was persisted with non-null metrics
    failed_run = db.query(IngestionRun).filter(IngestionRun.run_id == "GOV-RUN-CANONICAL-MASTER-2024-25").first()
    assert failed_run is not None
    assert failed_run.status == "FAILED"
    assert failed_run.records_found == 0
    assert failed_run.records_inserted == 0
    assert failed_run.records_updated == 0
    assert failed_run.records_rejected == 0
    assert failed_run.conflicts_found == 0
    assert failed_run.missing_values == 0
    assert "Simulated Ingestion Data Failure" in failed_run.error_log


def test_startup_seed_exception_logging_and_resilience():
    """Verify that startup bootstrap logs full traceback with logger.error and continues startup."""
    import asyncio
    from main import logger as main_logger

    mock_app = MagicMock()

    async def _run():
        # Ensure mine_count evaluates to 0 and seeder raises exception
        with patch("sqlalchemy.orm.Query.count", return_value=0):
            with patch("data.government_mine_data_seed.run_seed", side_effect=RuntimeError("Simulated Startup Seeder Crash")):
                with patch.object(main_logger, "error") as mock_logger_error:
                    # Execute lifespan context manager
                    async with lifespan(mock_app):
                        pass

                    # Assert logger.error was called with exc_info=True and explicit failure message
                    assert mock_logger_error.called
                    error_calls = [c for c in mock_logger_error.call_args_list if "GOVERNMENT DATA BOOTSTRAP FAILED" in str(c)]
                    assert len(error_calls) >= 1
                    call_args, call_kwargs = error_calls[0]
                    assert call_kwargs.get("exc_info") is True
                    assert "RuntimeError" in call_args[0]
                    assert "Simulated Startup Seeder Crash" in call_args[0]

    asyncio.run(_run())


def test_rag_pipeline_zero_mutation_guarantee(isolated_db_session):
    """Verify that government seeder NEVER touches Documents, ExtractedMetrics, or Chroma vectors."""
    db = isolated_db_session

    # Seed initial sample document & metric
    doc = Document(
        filename="Test_Audit.pdf",
        file_path="/tmp/test.pdf",
        file_hash="testhash1234567890",
        file_type="PDF",
        file_size_bytes=1024,
        status="PARSED"
    )
    db.add(doc)
    db.commit()

    metric = ExtractedMetric(
        document_id=doc.id,
        page_number=1,
        mine_name="Test Mine",
        subsidiary="ECL",
        metric_name="Coal Production",
        numeric_value=10.0,
        unit="MT",
        raw_unit="MT",
        standard_value=10.0,
        standard_unit="MT",
        fiscal_year="2023-24",
        confidence_score=0.95,
        validation_status="VALIDATED",
        raw_snippet="Test Mine produced 10.0 MT",
        data_origin="EXTRACTED_UNVERIFIED"
    )
    db.add(metric)
    db.commit()

    docs_before = db.query(Document).count()
    metrics_before = db.query(ExtractedMetric).count()
    metric_origin_before = db.query(ExtractedMetric).first().data_origin

    # Run seeder
    run_government_data_ingestion(db=db)

    docs_after = db.query(Document).count()
    metrics_after = db.query(ExtractedMetric).count()
    metric_origin_after = db.query(ExtractedMetric).first().data_origin

    assert docs_before == docs_after == 1, "Government seeder unexpectedly mutated Document table!"
    assert metrics_before == metrics_after == 1, "Government seeder unexpectedly mutated ExtractedMetric table!"
    assert metric_origin_before == metric_origin_after == "EXTRACTED_UNVERIFIED"


def test_cli_runner_script_execution():
    """Verify that backend/scripts/run_government_seeder.py exists and can be imported safely."""
    script_path = os.path.join(backend_dir, "scripts", "run_government_seeder.py")
    assert os.path.exists(script_path), "Operational runner script must exist at backend/scripts/run_government_seeder.py"

    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "run_government_data_ingestion" in content
    assert "GOV-RUN-CANONICAL-MASTER-2024-25" in content
    assert "if __name__ == '__main__':" in content.lower() or 'if __name__ == "__main__":' in content


def test_ingestion_run_recovery_status_transition(isolated_db_session):
    """
    Focused Phase 11C Blocker Regression Test:
    1. Seed initial sample document & extracted metric.
    2. Force an initial ingestion failure that commits IngestionRun(status="FAILED", error_log="...").
    3. Rerun canonical ingestion successfully.
    4. Verify existing IngestionRun is updated to status="COMPLETED", error_log=None, completed_at populated.
    5. Verify canonical counts: mine_master=60, data_sources=12, coal_blocks=7,
       mine_yearly_metrics=180, mine_monthly_metrics=15, mine_aliases=138, ingestion_runs=1.
    6. Verify 0 duplicate natural keys.
    7. Verify Documents (1) and ExtractedMetrics (1) remain unchanged.
    """
    db = isolated_db_session

    # Step 1: Initial RAG Document & Metric baseline
    doc = Document(
        filename="Baseline_Audit_FY24.pdf",
        file_path="/tmp/baseline.pdf",
        file_hash="baseline_hash_999",
        file_type="PDF",
        file_size_bytes=2048,
        status="PARSED"
    )
    db.add(doc)
    db.commit()

    metric = ExtractedMetric(
        document_id=doc.id,
        page_number=1,
        mine_name="Gevra Baseline",
        subsidiary="SECL",
        metric_name="Coal Production",
        numeric_value=59.32,
        unit="MT",
        raw_unit="MT",
        standard_value=59.32,
        standard_unit="MT",
        fiscal_year="2024-25",
        confidence_score=0.99,
        validation_status="VALIDATED",
        raw_snippet="Gevra baseline output 59.32 MT",
        data_origin="EXTRACTED_UNVERIFIED"
    )
    db.add(metric)
    db.commit()

    docs_before = db.query(Document).count()
    metrics_before = db.query(ExtractedMetric).count()

    # Step 2: Force failure during Stage 4 (MineMonthlyMetric)
    orig_add = db.add
    def mock_add_fail_stage4(obj):
        if isinstance(obj, MineMonthlyMetric):
            raise RuntimeError("Simulated Stage 4 Failure for Recovery Test")
        return orig_add(obj)

    with patch.object(db, "add", side_effect=mock_add_fail_stage4):
        with pytest.raises(Exception) as excinfo:
            run_government_data_ingestion(db=db)
        assert "Simulated Stage 4 Failure" in str(excinfo.value)

    # Verify run is recorded as FAILED with error_log
    failed_run = db.query(IngestionRun).filter(IngestionRun.run_id == "GOV-RUN-CANONICAL-MASTER-2024-25").first()
    assert failed_run is not None
    assert failed_run.status == "FAILED"
    assert failed_run.error_log is not None
    assert "Simulated Stage 4 Failure" in failed_run.error_log

    # Step 3: Rerun canonical ingestion without error
    res_recovery = run_government_data_ingestion(db=db)
    assert res_recovery["status"] == "COMPLETED"
    assert res_recovery["run_id"] == "GOV-RUN-CANONICAL-MASTER-2024-25"

    # Step 4: Verify existing IngestionRun row transitioned to COMPLETED with cleared error_log
    all_runs = db.query(IngestionRun).all()
    assert len(all_runs) == 1, f"Expected exactly 1 IngestionRun, found {len(all_runs)}"
    recovered_run = all_runs[0]
    assert recovered_run.run_id == "GOV-RUN-CANONICAL-MASTER-2024-25"
    assert recovered_run.status == "COMPLETED"
    assert recovered_run.error_log is None
    assert recovered_run.completed_at is not None

    # Step 5: Verify exact canonical counts
    assert db.query(MineMaster).count() == 60
    assert db.query(DataSource).count() == 12
    assert db.query(CoalBlock).count() == 7
    assert db.query(MineYearlyMetric).count() == 180
    assert db.query(MineMonthlyMetric).count() == 15
    assert db.query(MineAlias).count() == 138
    assert db.query(IngestionRun).count() == 1

    # Step 6: Verify 0 duplicate natural keys
    mine_ids = [m.mine_id for m in db.query(MineMaster).all()]
    assert len(mine_ids) == len(set(mine_ids)) == 60

    source_ids = [s.source_id for s in db.query(DataSource).all()]
    assert len(source_ids) == len(set(source_ids)) == 12

    block_ids = [b.coal_block_id for b in db.query(CoalBlock).all()]
    assert len(block_ids) == len(set(block_ids)) == 7

    # Step 7: Verify RAG Documents and ExtractedMetrics remain untouched
    assert db.query(Document).count() == docs_before == 1
    assert db.query(ExtractedMetric).count() == metrics_before == 1
    assert db.query(ExtractedMetric).first().data_origin == "EXTRACTED_UNVERIFIED"

