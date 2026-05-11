"""Rerank retrieved chunks with Voyage AI to surface the most relevant results."""

from __future__ import annotations

from fda_rag.ingestion.loader import _voyage_client
from fda_rag.retrieval.retriever import RetrievedChunk

RERANK_MODEL = "rerank-2"


def rerank(
    query: str,
    chunks: list[RetrievedChunk],
    top_n: int = 5,
) -> list[RetrievedChunk]:
    """
    Rerank chunks using Voyage AI and return the top_n results.
    The returned list is sorted by relevance score descending.
    """
    if not chunks:
        return []

    client = _voyage_client()
    documents = [c.chunk_text for c in chunks]

    result = client.rerank(query, documents, model=RERANK_MODEL, top_k=top_n)

    reranked: list[RetrievedChunk] = []
    for item in result.results:
        chunk = chunks[item.index]
        chunk.score = item.relevance_score
        reranked.append(chunk)

    return reranked
