from collections.abc import Generator
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv

# Load .env before any test runs so DATABASE_URL is available
load_dotenv(Path(__file__).parent.parent / ".env")


@pytest.fixture(scope="session")
def db_url() -> str:
    import os

    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("DATABASE_URL is not set. Copy .env.example to .env and run `make db-up`.")
    return url


@pytest.fixture(scope="session")
def db_connection(db_url: str) -> Generator[psycopg.Connection, None, None]:  # type: ignore[type-arg]
    with psycopg.connect(db_url) as conn:
        yield conn
