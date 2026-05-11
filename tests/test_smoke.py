"""
Day-one smoke test: verifies Postgres is reachable, pgvector is loaded,
and we can round-trip a vector through the database.

Run after `make db-up`:
    uv run pytest tests/test_smoke.py -v
"""

import psycopg
import pytest
from pgvector.psycopg import register_vector


def test_postgres_connection(db_connection: psycopg.Connection) -> None:  # type: ignore[type-arg]
    """Basic connectivity check."""
    with db_connection.cursor() as cur:
        cur.execute("SELECT 1")
        row = cur.fetchone()
    assert row == (1,)


def test_pgvector_extension_loaded(db_connection: psycopg.Connection) -> None:  # type: ignore[type-arg]
    """Confirms init.sql ran and the vector extension is active."""
    with db_connection.cursor() as cur:
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        row = cur.fetchone()
    assert row is not None, "pgvector extension is not installed — check docker/init.sql"
    assert row[0] == "vector"


def test_vector_insert_and_similarity_search(db_connection: psycopg.Connection) -> None:  # type: ignore[type-arg]
    """
    Creates a temp table with a vector(3) column, inserts two rows,
    then queries the nearest neighbour using cosine distance (<=>).
    Uses a SAVEPOINT so the session-scoped connection stays clean.
    """
    register_vector(db_connection)

    with db_connection.cursor() as cur:
        cur.execute("SAVEPOINT smoke_test")
        try:
            cur.execute(
                """
                CREATE TEMP TABLE _smoke_vectors (
                    id   serial PRIMARY KEY,
                    label text,
                    emb  vector(3)
                ) ON COMMIT DROP
                """
            )

            # Insert two vectors: one close to the query, one far away
            cur.execute(
                "INSERT INTO _smoke_vectors (label, emb) VALUES (%s, %s), (%s, %s)",
                ("close", [1.0, 2.0, 3.0], "far", [9.0, 8.0, 7.0]),
            )

            # Query: nearest neighbour to [1, 2, 3] by cosine distance
            cur.execute(
                """
                SELECT label
                FROM _smoke_vectors
                ORDER BY emb <=> %s::vector
                LIMIT 1
                """,
                ([1.0, 2.0, 3.0],),
            )
            row = cur.fetchone()
        except Exception:
            cur.execute("ROLLBACK TO SAVEPOINT smoke_test")
            raise
        else:
            cur.execute("RELEASE SAVEPOINT smoke_test")

    assert row is not None
    assert row[0] == "close", f"Expected 'close' as nearest neighbour, got {row[0]!r}"
