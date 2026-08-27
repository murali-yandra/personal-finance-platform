"""Fixtures for tests that require a real PostgreSQL database.

The suite is skipped unless ``RUN_INTEGRATION_TESTS=1`` and ``DATABASE_URL`` point
at a live PostgreSQL instance. CI sets both; locally, start the compose Postgres
service first. SQLite cannot verify partial indexes, ``NUMERIC(18,2)`` precision,
or that migrations match the SQLModel metadata, which is what these tests exist for.
"""

import os
from collections.abc import Generator

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, create_engine

RUN_INTEGRATION_TESTS = os.getenv("RUN_INTEGRATION_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION_TESTS,
    reason="RUN_INTEGRATION_TESTS is not set to 1.",
)


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:  # pragma: no cover - guarded by the skip above
        pytest.skip("DATABASE_URL is not configured.")
    return url


@pytest.fixture(scope="session")
def postgres_engine() -> Generator[Engine, None, None]:
    """Yield an engine bound to the integration PostgreSQL database."""
    if not RUN_INTEGRATION_TESTS:
        pytest.skip("RUN_INTEGRATION_TESTS is not set to 1.")
    engine = create_engine(_database_url())
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def postgres_session(postgres_engine: Engine) -> Generator[Session, None, None]:
    """Yield a PostgreSQL session that rolls back after each test."""
    with Session(postgres_engine) as session:
        try:
            yield session
        finally:
            session.rollback()
