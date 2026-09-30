-- Step 1: generic document artifacts, processing state, and official-source registry.
-- Execute through the existing migration workflow; application startup remains
-- read-only with respect to production schemas.

ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_status VARCHAR(40) NOT NULL DEFAULT 'DISCOVERED';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_type VARCHAR(30) NOT NULL DEFAULT 'MANUAL';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_organization VARCHAR(200);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS title VARCHAR(500);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS reporting_period VARCHAR(100);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS publication_date TIMESTAMPTZ;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS language VARCHAR(30);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_method VARCHAR(40);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_confidence DOUBLE PRECISION;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS metadata_json JSON;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_warnings JSON;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_version INTEGER NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS official_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    organization VARCHAR(200) NOT NULL,
    base_url TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL DEFAULT 'OFFICIAL_WEBSITE',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sync_frequency VARCHAR(30) NOT NULL DEFAULT '24h',
    last_sync_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL DEFAULT 'CONNECTED',
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS official_documents (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES official_sources(id) ON DELETE CASCADE,
    document_url TEXT NOT NULL,
    title VARCHAR(500),
    category VARCHAR(200),
    published_at TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64),
    download_status VARCHAR(40) NOT NULL DEFAULT 'DISCOVERED',
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    version INTEGER NOT NULL DEFAULT 1,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    last_error TEXT,
    source_metadata TEXT
);
CREATE INDEX IF NOT EXISTS ix_official_documents_url_version ON official_documents(source_id, document_url, version);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_document_id INTEGER REFERENCES official_documents(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS document_pages (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    extraction_method VARCHAR(30) NOT NULL DEFAULT 'NATIVE',
    extraction_confidence DOUBLE PRECISION,
    classification VARCHAR(20),
    width DOUBLE PRECISION,
    height DOUBLE PRECISION,
    blocks_json JSON,
    metadata_json JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_document_pages_document_id ON document_pages(document_id);

CREATE TABLE IF NOT EXISTS document_tables (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    table_number INTEGER NOT NULL,
    title VARCHAR(500),
    headers_json JSON,
    rows_json JSON,
    bounding_box_json JSON,
    extraction_confidence DOUBLE PRECISION,
    extraction_method VARCHAR(30) NOT NULL DEFAULT 'NATIVE',
    sheet_name VARCHAR(255),
    cells_json JSON,
    merged_cells_json JSON,
    formulas_json JSON,
    displayed_values_json JSON,
    warnings_json JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_document_tables_document_id ON document_tables(document_id);

CREATE TABLE IF NOT EXISTS document_images (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER,
    image_number INTEGER NOT NULL,
    source VARCHAR(30) NOT NULL DEFAULT 'embedded',
    mime_type VARCHAR(100),
    width INTEGER,
    height INTEGER,
    text TEXT,
    bounding_box_json JSON,
    ocr_confidence DOUBLE PRECISION,
    metadata_json JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_document_images_document_id ON document_images(document_id);
