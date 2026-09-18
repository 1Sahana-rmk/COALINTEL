-- Migration: 001_add_data_origin_to_extracted_metrics.sql
-- Description: Safely and idempotently adds data_origin column and index to extracted_metrics table.
-- Phase: COALINTEL V2 Phase 9C Production Hardening
--
-- Safety Guarantees:
-- 1. Uses IF NOT EXISTS on both column and index to guarantee idempotency across multiple runs.
-- 2. Sets DEFAULT 'UNKNOWN' to prevent false authoritative classification of historical or synthetic records.
-- 3. Does NOT lock tables aggressively; allows nullable historical records.
-- 4. Application startup does NOT execute this DDL; executed exclusively via operational migration procedures.

ALTER TABLE extracted_metrics 
ADD COLUMN IF NOT EXISTS data_origin VARCHAR(30) DEFAULT 'UNKNOWN';

CREATE INDEX IF NOT EXISTS ix_extracted_metrics_data_origin 
ON extracted_metrics (data_origin);
