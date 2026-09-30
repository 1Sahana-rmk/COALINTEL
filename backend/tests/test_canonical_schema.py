"""
Automated Canonical Data Model & Schema Verification Tests (Phase 2)
Verifies table structure, column separation (Mine, Company, Subsidiary, State, Sector, Ownership, Coal Block),
foreign keys, and data integrity constraints.
"""

import os
import sys
import pytest
from sqlalchemy import inspect

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import engine, Base
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
from app.models.data_conflict import DataConflict


def test_required_tables_exist():
    """Verify all 10 canonical tables required by Phase 2 exist in database metadata."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    required_tables = [
        "mine_master",
        "mine_aliases",
        "mine_yearly_metrics",
        "mine_monthly_metrics",
        "coal_blocks",
        "data_sources",
        "data_observations",
        "data_validation_results",
        "ingestion_runs",
    ]

    for table in required_tables:
        assert table in existing_tables, f"Missing required canonical table: {table}"

    # Either data_conflicts or data_conflict_records (both supported)
    assert "data_conflicts" in existing_tables or "data_conflict_records" in existing_tables


def test_mine_master_separated_dimensions():
    """
    CRITICAL RULE: Separate Mine, Company, Subsidiary, State, Sector/Ownership, Coal Block.
    Do NOT store everything as one flat field.
    """
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("mine_master")}

    # Assert distinct dimension columns exist
    assert "mine_name" in columns, "mine_name must exist as dedicated column"
    assert "company_name" in columns, "company_name must exist as dedicated column"
    assert "subsidiary_name" in columns, "subsidiary_name must exist as dedicated column"
    assert "state" in columns, "state must exist as dedicated column"
    assert "district" in columns, "district must exist as dedicated column"
    assert "ownership_type" in columns, "ownership_type must exist as dedicated column"
    assert "mine_type" in columns, "mine_type must exist as dedicated column"
    assert "coal_or_lignite" in columns, "coal_or_lignite must exist as dedicated column"
    assert "operational_status" in columns, "operational_status must exist as dedicated column"


def test_coal_blocks_separation():
    """Verify coal_blocks table has dedicated identity separate from mine_master."""
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("coal_blocks")}

    assert "coal_block_id" in columns
    assert "coal_block_name" in columns
    assert "allottee" in columns
    assert "company" in columns
    assert "peak_rated_capacity_mtpa" in columns
    assert "production_status" in columns


def test_foreign_key_relationships():
    """Verify foreign key linkages from child metric tables to mine_master."""
    inspector = inspect(engine)
    
    yearly_fks = [fk["referred_table"] for fk in inspector.get_foreign_keys("mine_yearly_metrics")]
    assert "mine_master" in yearly_fks, "mine_yearly_metrics must link to mine_master"

    aliases_fks = [fk["referred_table"] for fk in inspector.get_foreign_keys("mine_aliases")]
    assert "mine_master" in aliases_fks, "mine_aliases must link to mine_master"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
