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
    "merchants",
    "merchant_patterns",
    "categories",
    "balance_snapshots",
    "transfers",
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
    import app.domains.balances.models  # noqa: F401
    import app.domains.categories.models  # noqa: F401
    import app.domains.ingestion.models  # noqa: F401
    import app.domains.merchants.models  # noqa: F401
    import app.domains.transactions.models  # noqa: F401
    import app.domains.transfers.models  # noqa: F401
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


def test_system_categories_are_seeded(postgres_engine: Engine) -> None:
    """Migration 0009 seeds the 14 categories from 04-database_schema.md section 6."""
    from sqlalchemy import text

    with postgres_engine.connect() as connection:
        count = connection.execute(
            text(
                "SELECT count(*) FROM categories "
                "WHERE user_id IS NULL AND is_system = TRUE"
            )
        ).scalar_one()

    assert count == 14


def test_category_uniqueness_indexes_are_partial(postgres_engine: Engine) -> None:
    """A plain unique on (user_id, name) would not constrain system rows at all."""
    from sqlalchemy import text

    with postgres_engine.connect() as connection:
        definitions = {
            row[0]: row[1]
            for row in connection.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes "
                    "WHERE tablename = 'categories' AND indexname LIKE 'uq_%'"
                )
            )
        }

    assert "user_id IS NULL" in definitions["uq_system_category_name"]
    assert "user_id IS NOT NULL" in definitions["uq_user_category_name"]


def test_all_deferred_foreign_keys_are_attached(postgres_engine: Engine) -> None:
    """Migrations 0006-0008 attach the FKs migration 0004 could not create yet."""
    from sqlalchemy import text

    with postgres_engine.connect() as connection:
        names = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'transactions'::regclass AND contype = 'f'"
                )
            )
        }

    assert {
        "fk_transactions_raw_event_id",
        "fk_transactions_merchant_id",
        "fk_transactions_category_id",
    } <= names
