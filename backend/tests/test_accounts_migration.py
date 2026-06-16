import os
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import (
    Column,
    ForeignKeyConstraint,
    Numeric,
    PrimaryKeyConstraint,
    UniqueConstraint,
)

MIGRATION_MODULE = "migrations.versions.0003_create_accounts_table"


class OperationRecorder:
    def __init__(self) -> None:
        self.created_tables: list[tuple[str, tuple[Any, ...]]] = []
        self.created_indexes: list[tuple[str, str, list[str], bool]] = []
        self.dropped_indexes: list[tuple[str, str]] = []
        self.dropped_tables: list[str] = []

    def create_table(self, table_name: str, *elements: Any) -> None:
        self.created_tables.append((table_name, elements))

    def create_index(
        self,
        index_name: str,
        table_name: str,
        columns: list[str],
        unique: bool = False,
    ) -> None:
        self.created_indexes.append((index_name, table_name, columns, unique))

    def drop_index(self, index_name: str, table_name: str) -> None:
        self.dropped_indexes.append((index_name, table_name))

    def drop_table(self, table_name: str) -> None:
        self.dropped_tables.append(table_name)


def test_accounts_migration_creates_accounts_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = import_module(MIGRATION_MODULE)
    recorder = OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()

    assert len(recorder.created_tables) == 1
    table_name, elements = recorder.created_tables[0]
    assert table_name == "accounts"

    columns = {
        element.name: element for element in elements if isinstance(element, Column)
    }
    assert set(columns) == {
        "id",
        "user_id",
        "account_name",
        "account_type",
        "bank_name",
        "last_four_digits",
        "currency",
        "opening_balance",
        "estimated_balance",
        "status",
        "created_at",
        "updated_at",
    }
    assert columns["user_id"].nullable is False
    assert isinstance(columns["opening_balance"].type, Numeric)
    assert columns["opening_balance"].type.precision == 18
    assert columns["opening_balance"].type.scale == 2
    assert isinstance(columns["estimated_balance"].type, Numeric)
    assert columns["estimated_balance"].type.precision == 18
    assert columns["estimated_balance"].type.scale == 2

    primary_key = next(
        element for element in elements if isinstance(element, PrimaryKeyConstraint)
    )
    foreign_key = next(
        element for element in elements if isinstance(element, ForeignKeyConstraint)
    )
    unique_constraint = next(
        element
        for element in elements
        if isinstance(element, UniqueConstraint)
        and element.name == "uq_user_bank_lastfour_type"
    )
    assert list(primary_key._pending_colargs) == ["id"]
    assert list(foreign_key._pending_colargs) == ["user_id"]
    assert [element.target_fullname for element in foreign_key.elements] == ["users.id"]
    assert list(unique_constraint._pending_colargs) == [
        "user_id",
        "bank_name",
        "last_four_digits",
        "account_type",
    ]

    assert (
        "idx_accounts_user_id",
        "accounts",
        ["user_id"],
        False,
    ) in recorder.created_indexes
    assert (
        "idx_accounts_status",
        "accounts",
        ["status"],
        False,
    ) in recorder.created_indexes
    assert (
        "idx_accounts_bank_last_four",
        "accounts",
        ["bank_name", "last_four_digits"],
        False,
    ) in recorder.created_indexes


def test_accounts_migration_downgrade_drops_accounts_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = import_module(MIGRATION_MODULE)
    recorder = OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.downgrade()

    assert recorder.dropped_indexes == [
        ("idx_accounts_bank_last_four", "accounts"),
        ("idx_accounts_status", "accounts"),
        ("idx_accounts_user_id", "accounts"),
    ]
    assert recorder.dropped_tables == ["accounts"]


@pytest.mark.skipif(
    not (
        os.getenv("RUN_DB_SMOKE_TEST") == "1"
        and os.getenv("RUN_ACCOUNT_MIGRATION_SMOKE_TEST") == "1"
    ),
    reason=(
        "Set RUN_DB_SMOKE_TEST=1 and RUN_ACCOUNT_MIGRATION_SMOKE_TEST=1 "
        "to run the PostgreSQL account migration apply/rollback smoke test."
    ),
)
def test_accounts_migration_applies_and_rolls_back_on_postgresql() -> None:
    alembic_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))

    command.upgrade(alembic_config, "0003_create_accounts_table")
    command.downgrade(alembic_config, "0002_create_user_settings_table")
    command.upgrade(alembic_config, "head")
