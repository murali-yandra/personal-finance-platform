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
