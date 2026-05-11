"""Vector similarity search against the drug_chunks table in Neon."""

from __future__ import annotations

from dataclasses import dataclass

import psycopg
from pgvector.psycopg import register_vector

from fda_rag.ingestion.loader import VOYAGE_MODEL, _voyage_client


@dataclass
class RetrievedChunk:
    drug_name: str
    set_id: str
    section_code: str
    section_name: str
    chunk_index: int
    chunk_text: str
    score: float  # cosine similarity (higher = more similar)


def retrieve(
    query: str,
    conn: psycopg.Connection,  # type: ignore[type-arg]
    top_k: int = 20,
) -> list[RetrievedChunk]:
    """
    Embed the query and return the top_k most similar chunks from Neon.
    top_k is intentionally large so the reranker has enough candidates.
    """
    client = _voyage_client()
    result = client.embed([query], model=VOYAGE_MODEL, input_type="query")
    query_embedding = result.embeddings[0]

    register_vector(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT drug_name, set_id, section_code, section_name,
                   chunk_index, chunk_text,
                   1 - (embedding <=> %s::vector) AS score
            FROM drug_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (query_embedding, query_embedding, top_k),
        )
        rows = cur.fetchall()

    return [
        RetrievedChunk(
            drug_name=row[0],
            set_id=row[1],
            section_code=row[2],
            section_name=row[3],
            chunk_index=row[4],
            chunk_text=row[5],
            score=float(row[6]),
        )
        for row in rows
    ]
