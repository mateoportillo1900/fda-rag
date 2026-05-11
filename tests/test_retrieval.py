"""
Tests for the retrieval layer (vector search + reranker).
Requires DATABASE_URL and VOYAGE_API_KEY in .env, and at least one
drug label already ingested into drug_chunks.
"""

import os

import psycopg
import pytest
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

from fda_rag.retrieval.retriever import RetrievedChunk, retrieve
from fda_rag.retrieval.reranker import rerank

_has_voyage_key = bool(os.environ.get("VOYAGE_API_KEY", "").strip("pa-. "))
_skip_api = pytest.mark.skipif(
    not _has_voyage_key,
    reason="VOYAGE_API_KEY not set — add it to .env to run retrieval tests",
)


@pytest.fixture(scope="module")
def conn():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set")
    with psycopg.connect(url) as c:
        yield c


@pytest.fixture(scope="module")
def has_chunks(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM drug_chunks")
        count = cur.fetchone()[0]
    if count == 0:
        pytest.skip("drug_chunks table is empty — run ingestion first")
    return count


@_skip_api
class TestRetriever:
    def test_returns_results(self, conn, has_chunks) -> None:
        results = retrieve("What are the contraindications?", conn, top_k=5)
        assert len(results) > 0

    def test_returns_retrieved_chunk_objects(self, conn, has_chunks) -> None:
        results = retrieve("dosage and administration", conn, top_k=5)
        for r in results:
            assert isinstance(r, RetrievedChunk)

    def test_all_fields_populated(self, conn, has_chunks) -> None:
        results = retrieve("adverse reactions", conn, top_k=3)
        for r in results:
            assert r.drug_name
            assert r.set_id
            assert r.section_code
            assert r.section_name
            assert r.chunk_text
            assert isinstance(r.score, float)

    def test_scores_in_valid_range(self, conn, has_chunks) -> None:
        results = retrieve("drug interactions", conn, top_k=5)
        for r in results:
            assert -1.0 <= r.score <= 1.0, f"Score out of range: {r.score}"

    def test_results_ordered_by_score_descending(self, conn, has_chunks) -> None:
        results = retrieve("warnings and precautions", conn, top_k=10)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True), "Results not sorted by score"

    def test_top_k_respected(self, conn, has_chunks) -> None:
        results = retrieve("indications", conn, top_k=3)
        assert len(results) <= 3


@_skip_api
class TestReranker:
    def test_reranker_returns_fewer_results(self, conn, has_chunks) -> None:
        candidates = retrieve("contraindications for anticoagulants", conn, top_k=8)
        reranked = rerank("contraindications for anticoagulants", candidates, top_n=3)
        assert len(reranked) <= 3

    def test_reranker_preserves_chunk_fields(self, conn, has_chunks) -> None:
        candidates = retrieve("dosage", conn, top_k=5)
        reranked = rerank("dosage", candidates, top_n=3)
        for r in reranked:
            assert r.drug_name
            assert r.chunk_text

    def test_empty_input_returns_empty(self, conn, has_chunks) -> None:
        result = rerank("anything", [], top_n=5)
        assert result == []
