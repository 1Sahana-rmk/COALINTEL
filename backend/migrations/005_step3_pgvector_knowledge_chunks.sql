-- Step 3: PostgreSQL/pgvector evidence-linked knowledge chunks.
-- This migration is additive and idempotent.  It intentionally fails with a
-- clear PostgreSQL error when the server has not installed pgvector; falling
-- back to JSON or Chroma here would falsely claim that semantic retrieval is
-- PostgreSQL-backed.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id SERIAL PRIMARY KEY,
    chunk_key VARCHAR(64) NOT NULL UNIQUE,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    document_page_id INTEGER REFERENCES document_pages(id) ON DELETE SET NULL,
    document_table_id INTEGER REFERENCES document_tables(id) ON DELETE SET NULL,
    page_number INTEGER,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    chunk_type VARCHAR(40) NOT NULL,
    chunk_text TEXT NOT NULL,
    token_count INTEGER,
    embedding vector(384),
    embedding_provider VARCHAR(60),
    embedding_model VARCHAR(200),
    embedding_status VARCHAR(30) NOT NULL DEFAULT 'UNAVAILABLE',
    content_hash VARCHAR(64) NOT NULL,
    source_locator_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_document_page
    ON knowledge_chunks(document_id, page_number);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_document_page_id
    ON knowledge_chunks(document_page_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_document_table_id
    ON knowledge_chunks(document_table_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_type
    ON knowledge_chunks(chunk_type);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_status
    ON knowledge_chunks(embedding_status);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_content_hash
    ON knowledge_chunks(content_hash);

-- The IVFFlat/HNSW index is deliberately not created here.  It requires an
-- embedding population and should be added after a deployment-specific
-- benchmark determines the right lists/ef parameters.
