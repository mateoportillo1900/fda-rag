-- Runs once when the Postgres container is first created.
-- pgvector/pgvector:pg16 ships the extension; we just need to enable it.
CREATE EXTENSION IF NOT EXISTS vector;
