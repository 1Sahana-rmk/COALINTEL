-- Migration: 002_add_missing_mine_master_and_provenance_columns.sql
-- Description: Safely and idempotently adds missing columns and indexes to mine_master and data_sources tables.
-- Phase: COALINTEL V2 Phase 11 Mines Intelligence Production Recovery
--
-- Safety Guarantees:
-- 1. Uses IF NOT EXISTS on all ADD COLUMN statements to guarantee idempotency across multiple executions.
-- 2. Uses CREATE INDEX IF NOT EXISTS to guarantee idempotent index creation.
-- 3. Sets safe provenance default values ('UNKNOWN' for data_origin and verification_status, NULL for financial_year and retrieved_at)
--    to prevent unproven retroactive upgrades to historical rows.
-- 4. Specific official provenance ('OFFICIAL', '2024-25', 'verified', retrieval timestamp) is explicitly attributed
--    by the authoritative government seeder upon genuine ingestion, not by retroactive schema defaults.
-- 5. Does NOT drop tables, truncate data, or alter existing column definitions.
-- 6. Application startup does NOT execute this DDL; executed via authorized DBA workflow or standalone migration script.

-- 1. mine_master table missing columns (added in PR #34 model definition)
ALTER TABLE mine_master
ADD COLUMN IF NOT EXISTS parent_company VARCHAR(150);

ALTER TABLE mine_master
ADD COLUMN IF NOT EXISTS block VARCHAR(150);

ALTER TABLE mine_master
ADD COLUMN IF NOT EXISTS coalfield VARCHAR(150);

ALTER TABLE mine_master
ADD COLUMN IF NOT EXISTS sector VARCHAR(50);

ALTER TABLE mine_master
ADD COLUMN IF NOT EXISTS captive_or_commercial VARCHAR(50);

ALTER TABLE mine_master
ADD COLUMN IF NOT EXISTS financial_year VARCHAR(20);

ALTER TABLE mine_master
ADD COLUMN IF NOT EXISTS source_chapter VARCHAR(100);

ALTER TABLE mine_master
ADD COLUMN IF NOT EXISTS retrieved_at TIMESTAMPTZ;

ALTER TABLE mine_master
ADD COLUMN IF NOT EXISTS verification_status VARCHAR(50) DEFAULT 'UNKNOWN';

ALTER TABLE mine_master
ADD COLUMN IF NOT EXISTS data_origin VARCHAR(30) DEFAULT 'UNKNOWN';

-- Performance & Dimensional Indexes on mine_master
CREATE INDEX IF NOT EXISTS ix_mine_master_sector
ON mine_master (sector);

CREATE INDEX IF NOT EXISTS ix_mine_master_data_origin
ON mine_master (data_origin);

-- 2. data_sources table missing column (added in PR #34 model definition)
ALTER TABLE data_sources
ADD COLUMN IF NOT EXISTS chapter VARCHAR(100);
