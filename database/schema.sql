-- ============================================
-- COALINTEL DATABASE SCHEMA
-- ============================================

-- 1. Documents
CREATE TABLE documents (
    document_id SERIAL PRIMARY KEY,
    document_name VARCHAR(255) NOT NULL,
    source_organization VARCHAR(255),
    reporting_period VARCHAR(100),
    document_type VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'UPLOADED'
);


-- 2. Pages belonging to a document
CREATE TABLE document_pages (
    page_id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    extracted_text TEXT,

    FOREIGN KEY (document_id)
        REFERENCES documents(document_id)
        ON DELETE CASCADE
);


-- 3. Standardized entities
-- Example: Ramagundam OC-II Extension Project
CREATE TABLE entities (
    entity_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(100) NOT NULL,
    canonical_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- 4. Extracted records
CREATE TABLE extracted_records (
    record_id SERIAL PRIMARY KEY,

    page_id INTEGER NOT NULL,
    entity_id INTEGER,

    metric_name VARCHAR(255) NOT NULL,
    original_value VARCHAR(255),
    normalized_value NUMERIC,
    original_unit VARCHAR(100),
    normalized_unit VARCHAR(100),

    reporting_period VARCHAR(100),

    extraction_method VARCHAR(100),
    extraction_confidence NUMERIC(5,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (page_id)
        REFERENCES document_pages(page_id)
        ON DELETE CASCADE,

    FOREIGN KEY (entity_id)
        REFERENCES entities(entity_id)
);


-- 5. Evidence
CREATE TABLE evidence_items (
    evidence_id SERIAL PRIMARY KEY,

    record_id INTEGER NOT NULL,

    evidence_type VARCHAR(100),
    evidence_text TEXT,

    source_page_id INTEGER,
    source_reference VARCHAR(255),

    confidence_score NUMERIC(5,2),

    status VARCHAR(50) DEFAULT 'PENDING',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (record_id)
        REFERENCES extracted_records(record_id),

    FOREIGN KEY (source_page_id)
        REFERENCES document_pages(page_id)
);


-- 6. Claims generated from verified evidence
CREATE TABLE claims (
    claim_id SERIAL PRIMARY KEY,

    claim_text TEXT NOT NULL,

    evidence_id INTEGER NOT NULL,

    status VARCHAR(50) DEFAULT 'UNVERIFIED',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (evidence_id)
        REFERENCES evidence_items(evidence_id)
);


-- 7. Human verification decisions
CREATE TABLE verification_decisions (
    verification_id SERIAL PRIMARY KEY,

    evidence_id INTEGER NOT NULL,

    decision VARCHAR(50) NOT NULL,

    reason TEXT,

    verified_by VARCHAR(255),

    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (evidence_id)
        REFERENCES evidence_items(evidence_id)
);


-- 8. Conflicting evidence
CREATE TABLE evidence_conflicts (
    conflict_id SERIAL PRIMARY KEY,

    evidence_a_id INTEGER NOT NULL,
    evidence_b_id INTEGER NOT NULL,

    conflict_type VARCHAR(100),

    description TEXT,

    recommended_action VARCHAR(100),

    resolution_status VARCHAR(50) DEFAULT 'OPEN',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (evidence_a_id)
        REFERENCES evidence_items(evidence_id),

    FOREIGN KEY (evidence_b_id)
        REFERENCES evidence_items(evidence_id)
);


-- 9. Audit trail
CREATE TABLE audit_events (
    audit_id SERIAL PRIMARY KEY,

    event_type VARCHAR(100) NOT NULL,

    entity_type VARCHAR(100),

    entity_id INTEGER,

    description TEXT,

    performed_by VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);