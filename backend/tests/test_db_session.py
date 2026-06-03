import os

import pytest
from sqlalchemy import text


@pytest.mark.skipif(
    os.getenv("RUN_DB_SMOKE_TEST") != "1",
    reason="Set RUN_DB_SMOKE_TEST=1 when PostgreSQL is available.",
)
def test_database_session_executes_smoke_query() -> None:
    from app.db.session import engine

    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
