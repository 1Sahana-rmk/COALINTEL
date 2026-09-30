-- Step 2C: evidence-linked structured fact candidates.
-- Additive migration. Legacy extracted_metrics and its consumers remain intact.

CREATE TABLE IF NOT EXISTS structured_facts (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    document_page_id INTEGER REFERENCES document_pages(id) ON DELETE SET NULL,
    page_number INTEGER,
    document_table_id INTEGER REFERENCES document_tables(id) ON DELETE SET NULL,
    source_metric_id INTEGER REFERENCES extracted_metrics(id) ON DELETE SET NULL,

    entity_type VARCHAR(40) NOT NULL DEFAULT 'UNKNOWN',
    entity_id VARCHAR(120),
    entity_name_raw TEXT,
    entity_name_canonical VARCHAR(200),
    entity_resolution_method VARCHAR(60) NOT NULL DEFAULT 'UNRESOLVED',
    entity_resolution_confidence NUMERIC(5,4),

    metric_type VARCHAR(60) NOT NULL DEFAULT 'UNCLASSIFIED',
    metric_name_raw TEXT,
    metric_name_canonical VARCHAR(100),
    metric_resolution_method VARCHAR(60) NOT NULL DEFAULT 'UNRESOLVED',
    metric_resolution_confidence NUMERIC(5,4),

    raw_value_text TEXT,
    raw_value_numeric NUMERIC(24,10),
    normalized_value NUMERIC(24,10),
    raw_unit VARCHAR(80),
    normalized_unit VARCHAR(40),
    period_raw VARCHAR(120),
    period_normalized VARCHAR(120),
    period_type VARCHAR(30),
    qualifiers_json JSON,

    extraction_method VARCHAR(40) NOT NULL DEFAULT 'RULE_BASED',
    extraction_confidence NUMERIC(5,4),
    evidence_type VARCHAR(30) NOT NULL DEFAULT 'PAGE',
    evidence_locator_json JSON,
    validation_status VARCHAR(40) NOT NULL DEFAULT 'REVIEW_REQUIRED',
    validation_warnings_json JSON,
    fact_status VARCHAR(30) NOT NULL DEFAULT 'CANDIDATE',

    fact_key VARCHAR(64) NOT NULL UNIQUE,
    duplicate_group_key VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- The column guard keeps this migration safe to rerun if an earlier partial
-- application created the table before the page-level FK was added.
ALTER TABLE structured_facts
    ADD COLUMN IF NOT EXISTS document_page_id INTEGER REFERENCES document_pages(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_structured_facts_document_id
    ON structured_facts(document_id);
CREATE INDEX IF NOT EXISTS ix_structured_facts_page_number
    ON structured_facts(page_number);
CREATE INDEX IF NOT EXISTS ix_structured_facts_document_page_id
    ON structured_facts(document_page_id);
CREATE INDEX IF NOT EXISTS ix_structured_facts_document_table_id
    ON structured_facts(document_table_id);
CREATE INDEX IF NOT EXISTS ix_structured_facts_source_metric_id
    ON structured_facts(source_metric_id);
CREATE INDEX IF NOT EXISTS ix_structured_facts_entity_name_canonical
    ON structured_facts(entity_name_canonical);
CREATE INDEX IF NOT EXISTS ix_structured_facts_metric_type
    ON structured_facts(metric_type);
CREATE INDEX IF NOT EXISTS ix_structured_facts_metric_name_canonical
    ON structured_facts(metric_name_canonical);
CREATE INDEX IF NOT EXISTS ix_structured_facts_period_normalized
    ON structured_facts(period_normalized);
CREATE INDEX IF NOT EXISTS ix_structured_facts_validation_status
    ON structured_facts(validation_status);
CREATE INDEX IF NOT EXISTS ix_structured_facts_fact_status
    ON structured_facts(fact_status);
CREATE INDEX IF NOT EXISTS ix_structured_facts_duplicate_group_key
    ON structured_facts(duplicate_group_key);
CREATE INDEX IF NOT EXISTS ix_structured_facts_document_period_metric
    ON structured_facts(document_id, period_normalized, metric_name_canonical);
CREATE INDEX IF NOT EXISTS ix_structured_facts_entity_metric_period
    ON structured_facts(entity_name_canonical, metric_name_canonical, period_normalized);
