"""
COALINTEL V2 — PHASE 11 REGRESSION TEST SUITE
Mines Intelligence Production Recovery Verification Tests
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from database import SessionLocal
from app.models.mine import MineMaster, MineYearlyMetric, CoalBlock, MineAlias
from app.models.data_provenance import DataSource, IngestionRun
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from data.government_mine_data_seed import run_government_data_ingestion

client = TestClient(app)


def test_migration_002_file_integrity():
    """Verify migration 002 exists, uses safe IF NOT EXISTS, and specifies correct columns."""
    migration_path = os.path.join(backend_dir, "migrations", "002_add_missing_mine_master_and_provenance_columns.sql")
    assert os.path.exists(migration_path), "Migration 002 file must exist"

    with open(migration_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Safety checks (ignore SQL comments)
    non_comment_lines = [line.strip().upper() for line in sql.splitlines() if not line.strip().startswith("--") and line.strip()]
    assert any("ADD COLUMN IF NOT EXISTS" in line for line in non_comment_lines), "Must use IF NOT EXISTS for column additions"
    assert any("CREATE INDEX IF NOT EXISTS" in line for line in non_comment_lines), "Must use IF NOT EXISTS for index creation"
    assert not any(line.startswith("DROP") for line in non_comment_lines), "Must NOT contain any DROP statement"
    assert not any("TRUNCATE" in line for line in non_comment_lines), "Must NOT contain any TRUNCATE statement"

    # Provenance safety assertions: prevent retroactive false attribution to existing rows
    assert "DEFAULT 'OFFICIAL'" not in sql, "DDL must NOT default data_origin to 'OFFICIAL'"
    assert "DEFAULT '2024-25'" not in sql, "DDL must NOT default financial_year to '2024-25'"
    assert "DEFAULT 'VERIFIED'" not in sql.upper(), "DDL must NOT default verification_status to 'verified'"
    assert "DEFAULT NOW()" not in sql, "DDL must NOT default retrieved_at to NOW()"
    assert "DEFAULT 'UNKNOWN'" in sql, "DDL must default unproven provenance columns to 'UNKNOWN'"

    # Required columns checked
    required_cols = [
        "parent_company", "block", "coalfield", "sector",
        "captive_or_commercial", "financial_year", "source_chapter",
        "retrieved_at", "verification_status", "data_origin", "chapter"
    ]
    for col in required_cols:
        assert col in sql, f"Missing required column in migration: {col}"


def test_mines_list_success_and_headers():
    """Verify /api/v1/mines returns HTTP 200, valid canonical schema, and X-Total-Count header."""
    r = client.get("/api/v1/mines")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 60
    assert "x-total-count" in r.headers
    total = int(r.headers["x-total-count"])
    assert total >= 60

    # Verify canonical fields on first mine
    first = data[0]
    assert "mine_id" in first
    assert "mine_name" in first
    assert "company_name" in first
    assert "state" in first
    assert "data_origin" in first
    assert first["data_origin"] in ["OFFICIAL", "government", "UNKNOWN"]

    # Verify natural key patterns and integrity across all returned mines
    for m in data:
        assert m["mine_id"].startswith("MINE-"), f"Invalid natural key prefix: {m['mine_id']}"
        assert len(m["mine_name"].strip()) > 0, f"Empty mine name for {m['mine_id']}"
        assert len(m["company_name"].strip()) > 0, f"Empty company name for {m['mine_id']}"
        assert len(m["state"].strip()) > 0, f"Empty state for {m['mine_id']}"
        assert m["coal_or_lignite"] in ["Coal", "Lignite"], f"Invalid fuel type: {m['coal_or_lignite']}"


def test_mines_list_filtering():
    """Verify multi-field filtering on /api/v1/mines."""
    # Filter by state
    r_state = client.get("/api/v1/mines?state=Chhattisgarh")
    assert r_state.status_code == 200
    data_state = r_state.json()
    assert len(data_state) > 0
    assert all(m["state"] == "Chhattisgarh" for m in data_state)

    # Filter by fuel type (Lignite)
    r_lig = client.get("/api/v1/mines?coal_or_lignite=Lignite")
    assert r_lig.status_code == 200
    data_lig = r_lig.json()
    assert len(data_lig) >= 10
    assert all(m["coal_or_lignite"] == "Lignite" for m in data_lig)

    # Filter by mine type (Mixed)
    r_mixed = client.get("/api/v1/mines?mine_type=Mixed")
    assert r_mixed.status_code == 200
    data_mixed = r_mixed.json()
    assert len(data_mixed) >= 4

    # Search filter
    r_search = client.get("/api/v1/mines?search=Gevra")
    assert r_search.status_code == 200
    data_search = r_search.json()
    assert len(data_search) >= 1
    assert any("Gevra" in m["mine_name"] for m in data_search)


def test_mines_pagination():
    """Verify deterministic pagination parameters."""
    r_p1 = client.get("/api/v1/mines?page=1&page_size=5")
    assert r_p1.status_code == 200
    p1_items = r_p1.json()
    assert len(p1_items) == 5

    r_p2 = client.get("/api/v1/mines?page=2&page_size=5")
    assert r_p2.status_code == 200
    p2_items = r_p2.json()
    assert len(p2_items) == 5

    # Page 1 and Page 2 should not overlap
    p1_ids = {m["mine_id"] for m in p1_items}
    p2_ids = {m["mine_id"] for m in p2_items}
    assert len(p1_ids.intersection(p2_ids)) == 0


def test_mines_stats_and_alias():
    """Verify /api/v1/mines/stats and /api/v1/mines-summary-stats."""
    r_stats = client.get("/api/v1/mines/stats")
    assert r_stats.status_code == 200
    stats = r_stats.json()

    assert stats["total_canonical_mines"] >= 60
    assert "coverage" in stats
    assert stats["coverage"]["states_covered"] >= 12
    assert "breakdowns" in stats
    assert "by_fuel" in stats["breakdowns"]
    assert stats["breakdowns"]["by_fuel"]["Coal"] >= 50
    assert stats["breakdowns"]["by_fuel"]["Lignite"] >= 10

    # Backward compatible alias
    r_alias = client.get("/api/v1/mines-summary-stats")
    assert r_alias.status_code == 200
    assert r_alias.json()["total_canonical_mines"] == stats["total_canonical_mines"]


def test_coal_blocks_endpoints():
    """Verify both /api/v1/coal-blocks and /api/v1/mines/coal-blocks return valid data."""
    r1 = client.get("/api/v1/coal-blocks")
    assert r1.status_code == 200
    blocks1 = r1.json()
    assert len(blocks1) >= 7

    r2 = client.get("/api/v1/mines/coal-blocks")
    assert r2.status_code == 200
    blocks2 = r2.json()
    assert len(blocks2) == len(blocks1)

    # Check block fields
    sample = blocks1[0]
    assert "coal_block_id" in sample
    assert "coal_block_name" in sample
    assert "allottee" in sample


def test_data_sources_endpoints():
    """Verify both /api/v1/data-sources and /api/v1/mines/data-sources return valid data."""
    r1 = client.get("/api/v1/data-sources")
    assert r1.status_code == 200
    sources1 = r1.json()
    assert len(sources1) >= 10

    r2 = client.get("/api/v1/mines/data-sources")
    assert r2.status_code == 200
    sources2 = r2.json()
    assert len(sources2) == len(sources1)

    sample = sources1[0]
    assert "source_id" in sample
    assert "organization" in sample
    assert "document_title" in sample


def test_dimension_count_endpoints():
    """Verify /states, /subsidiaries, /sectors, /types, /companies."""
    for ep in ["/states", "/subsidiaries", "/sectors", "/types", "/companies"]:
        r = client.get(f"/api/v1/mines{ep}")
        assert r.status_code == 200
        items = r.json()
        assert len(items) > 0
        assert all("name" in item and "count" in item for item in items)


def test_single_mine_detail():
    """Verify /api/v1/mines/{mine_id} returns comprehensive details and provenance."""
    r = client.get("/api/v1/mines/MINE-SECL-GEVRA")
    assert r.status_code == 200
    det = r.json()
    assert det["mine_id"] == "MINE-SECL-GEVRA"
    assert det["mine_name"] == "Gevra OpenCast"
    assert len(det["yearly_metrics"]) == 3
    assert len(det["monthly_metrics"]) >= 1
    assert len(det["aliases"]) >= 1
    assert len(det["provenance_sources"]) >= 1


def test_nonexistent_mine_detail():
    """Verify /api/v1/mines/{mine_id} for unknown ID returns 404."""
    r = client.get("/api/v1/mines/NONEXISTENT-MINE-XYZ-999")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


def test_seeder_idempotency_and_zero_metric_mutation():
    """Verify running seeder twice does NOT duplicate rows and does NOT mutate ExtractedMetric."""
    db = SessionLocal()
    try:
        # Snapshot current extracted_metrics
        extracted_snapshot = [
            (em.id, em.fiscal_year, em.data_origin)
            for em in db.query(ExtractedMetric).all()
        ]

        mines_before = db.query(MineMaster).count()
        metrics_before = db.query(MineYearlyMetric).count()
        blocks_before = db.query(CoalBlock).count()
        sources_before = db.query(DataSource).count()
        runs_before = db.query(IngestionRun).count()
        docs_before = db.query(Document).count()

        # Run seeder again
        run_government_data_ingestion(db=db)

        mines_after = db.query(MineMaster).count()
        metrics_after = db.query(MineYearlyMetric).count()
        blocks_after = db.query(CoalBlock).count()
        sources_after = db.query(DataSource).count()
        runs_after = db.query(IngestionRun).count()
        docs_after = db.query(Document).count()

        assert mines_before == mines_after, f"Duplicate mines created: {mines_before} != {mines_after}"
        assert metrics_before == metrics_after, f"Duplicate metrics created: {metrics_before} != {metrics_after}"
        assert blocks_before == blocks_after, f"Duplicate blocks created: {blocks_before} != {blocks_after}"
        assert sources_before == sources_after, f"Duplicate sources created: {sources_before} != {sources_after}"
        assert runs_before == runs_after, f"Duplicate IngestionRun created: {runs_before} != {runs_after}"
        assert docs_before == docs_after, f"Unexpected Document created by seeder: {docs_before} != {docs_after}"

        # Verify extracted_metrics were NOT mutated
        extracted_after = [
            (em.id, em.fiscal_year, em.data_origin)
            for em in db.query(ExtractedMetric).all()
        ]
        assert extracted_snapshot == extracted_after, "ExtractedMetric records were mutated by seeder!"

    finally:
        db.close()


def test_mines_route_precedence_order():
    """Verify route registration order ensures static routes precede parameterized /{mine_id}."""
    from app.api.mines import router as mines_router

    route_map = [(r.path, r.endpoint.__name__) for r in mines_router.routes if hasattr(r, "path")]
    paths = [p for p, _ in route_map]

    assert "/mines/coal-blocks" in paths
    assert "/mines/data-sources" in paths
    assert "/mines/{mine_id}" in paths

    cb_idx = paths.index("/mines/coal-blocks")
    ds_idx = paths.index("/mines/data-sources")
    param_idx = paths.index("/mines/{mine_id}")

    assert cb_idx < param_idx, f"Route /mines/coal-blocks ({cb_idx}) must precede /mines/{{mine_id}} ({param_idx})"
    assert ds_idx < param_idx, f"Route /mines/data-sources ({ds_idx}) must precede /mines/{{mine_id}} ({param_idx})"

    # Verify that HTTP requests to static subpaths resolve to their specific handlers, NOT get_mine_details
    r_cb = client.get("/api/v1/mines/coal-blocks")
    assert r_cb.status_code == 200
    assert isinstance(r_cb.json(), list)
    assert all("coal_block_id" in b for b in r_cb.json())

    r_ds = client.get("/api/v1/mines/data-sources")
    assert r_ds.status_code == 200
    assert isinstance(r_ds.json(), list)
    assert all("source_id" in s for s in r_ds.json())


def test_mines_endpoint_error_handling_graceful_503(monkeypatch):
    """Verify that operational database failures return controlled HTTP 503 rather than unhandled 500."""
    from app.services import mine_service
    from sqlalchemy.exc import OperationalError

    def mock_failure(*args, **kwargs):
        raise OperationalError("SELECT * FROM mine_master", {}, Exception("column mine_master.parent_company does not exist"))

    monkeypatch.setattr(mine_service, "get_mines_list", mock_failure)

    r = client.get("/api/v1/mines")
    assert r.status_code == 503
    assert "temporarily unavailable" in r.json()["detail"].lower()
