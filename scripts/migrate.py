"""
Create the drug_chunks table and indexes in Neon.
Safe to run multiple times — uses IF NOT EXISTS throughout.

Usage:
    uv run scripts/migrate.py
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DDL = """
CREATE TABLE IF NOT EXISTS drug_chunks (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    drug_name    TEXT        NOT NULL,
    set_id       TEXT        NOT NULL,
    section_code TEXT        NOT NULL,
    section_name TEXT        NOT NULL,
    chunk_index  INTEGER     NOT NULL,
    chunk_text   TEXT        NOT NULL,
    embedding    vector(1024),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HNSW index for fast cosine-distance search (pgvector)
CREATE INDEX IF NOT EXISTS drug_chunks_embedding_idx
    ON drug_chunks USING hnsw (embedding vector_cosine_ops);

-- B-tree index for drug name filter queries
CREATE INDEX IF NOT EXISTS drug_chunks_drug_name_idx
    ON drug_chunks (drug_name);
"""


def main() -> None:
    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url) as conn:
        conn.execute(DDL)
        conn.commit()
    print("Migration complete — drug_chunks table is ready.")


if __name__ == "__main__":
    main()
