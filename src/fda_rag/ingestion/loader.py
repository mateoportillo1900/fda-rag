"""Embed chunks with Voyage AI and write them to Neon."""

from __future__ import annotations

import os
import time

import psycopg
import voyageai
from pgvector.psycopg import register_vector

from fda_rag.ingestion.chunker import Chunk

VOYAGE_MODEL = "voyage-3"
BATCH_SIZE = 20        # texts per Voyage AI call (kept small for free-tier TPM limit)
EMBEDDING_DIM = 1024   # voyage-3 output dimensions


def _voyage_client() -> voyageai.Client:
    key = os.environ.get("VOYAGE_API_KEY", "")
    if not key or key.startswith("pa-..."):
        raise RuntimeError(
            "VOYAGE_API_KEY is not set. "
            "Get a free key at https://dash.voyageai.com and add it to your .env file."
        )
    return voyageai.Client(api_key=key)


def embed_chunks(chunks: list[Chunk]) -> list[list[float]]:
    """
    Call Voyage AI to embed each chunk as a document.
    Returns one float[1024] embedding per chunk, in the same order.
    """
    client = _voyage_client()
    texts = [c.chunk_text for c in chunks]
    embeddings: list[list[float]] = []

    for batch_start in range(0, len(texts), BATCH_SIZE):
        batch = texts[batch_start : batch_start + BATCH_SIZE]
        result = client.embed(batch, model=VOYAGE_MODEL, input_type="document")
        embeddings.extend(result.embeddings)
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = -(-len(texts) // BATCH_SIZE)  # ceiling division
        print(f"    embedded batch {batch_num}/{total_batches} ({len(batch)} chunks)")
        if batch_start + BATCH_SIZE < len(texts):
            time.sleep(65)

    return embeddings


def store_chunks(
    conn: psycopg.Connection,  # type: ignore[type-arg]
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> int:
    """
    Insert chunks + embeddings into drug_chunks.
    Returns the number of rows written.
    """
    register_vector(conn)

    rows = [
        (
            chunk.drug_name,
            chunk.set_id,
            chunk.section_code,
            chunk.section_name,
            chunk.chunk_index,
            chunk.chunk_text,
            embedding,
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO drug_chunks
                (drug_name, set_id, section_code, section_name,
                 chunk_index, chunk_text, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )
    conn.commit()
    return len(rows)
