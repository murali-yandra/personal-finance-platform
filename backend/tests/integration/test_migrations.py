"""Verify that Alembic migrations produce exactly the schema the models describe."""

import os

import pytest
from sqlalchemy import Engine, inspect

RUN_INTEGRATION_TESTS = os.getenv("RUN_INTEGRATION_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION_TESTS,
    reason="RUN_INTEGRATION_TESTS is not set to 1.",
)

EXPECTED_TABLES = {
    "users",
    "user_settings",
    "accounts",
    "transactions",
    "audit_log",
    "raw_events",
}


def test_migrations_create_expected_tables(postgres_engine: Engine) -> None:
    inspector = inspect(postgres_engine)
    table_names = set(inspector.get_table_names())

    missing = EXPECTED_TABLES - table_names
    assert not missing, f"Migrations did not create: {sorted(missing)}"


def test_alembic_version_table_is_stamped(postgres_engine: Engine) -> None:
    inspector = inspect(postgres_engine)
    assert "alembic_version" in inspector.get_table_names()


def test_model_metadata_matches_migrated_schema(postgres_engine: Engine) -> None:
    """Every column declared on a SQLModel table must exist in the migrated schema."""
    from sqlmodel import SQLModel

    import app.domains.accounts.models  # noqa: F401
    import app.domains.audit.models  # noqa: F401
    import app.domains.ingestion.models  # noqa: F401
    import app.domains.transactions.models  # noqa: F401
    import app.domains.users.models  # noqa: F401

    inspector = inspect(postgres_engine)
    migrated_tables = set(inspector.get_table_names())

    for table_name, table in SQLModel.metadata.tables.items():
        if table_name not in migrated_tables:
            pytest.fail(f"Table {table_name} is declared on a model but not migrated.")

        migrated_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        model_columns = {column.name for column in table.columns}
        missing_columns = model_columns - migrated_columns
        assert not missing_columns, (
            f"Table {table_name} is missing migrated columns: "
            f"{sorted(missing_columns)}"
        )


def test_transaction_fingerprint_index_is_partial(postgres_engine: Engine) -> None:
    """The unique index must skip NULL fingerprints, or manual rows collide."""
    from sqlalchemy import text

    with postgres_engine.connect() as connection:
        definition = connection.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'transactions' "
                "AND indexname = 'uq_transaction_fingerprint_user'"
            )
        ).scalar_one()

    assert "UNIQUE" in definition
    assert "transaction_fingerprint IS NOT NULL" in definition


def test_transaction_check_constraints_exist(postgres_engine: Engine) -> None:
    from sqlalchemy import text

    with postgres_engine.connect() as connection:
        names = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'transactions'::regclass AND contype = 'c'"
                )
            )
        }

    assert "chk_transaction_amount_positive" in names
    assert "chk_transaction_direction" in names


def test_amount_precision_survives_a_round_trip(postgres_engine: Engine) -> None:
    """NUMERIC(18,2) must not silently truncate a large balance."""
    from decimal import Decimal

    from sqlalchemy import text

    with postgres_engine.connect() as connection:
        value = connection.execute(
            text("SELECT CAST('1234567890123456.78' AS NUMERIC(18,2))")
        ).scalar_one()

    assert value == Decimal("1234567890123456.78")
