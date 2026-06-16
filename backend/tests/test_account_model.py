import subprocess
import sys
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKeyConstraint, Numeric, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.domains.accounts.models import Account
from app.domains.users.models import User


def test_account_defaults_and_uuid_primary_key() -> None:
    user = User(
        email="murali@example.com",
        password_hash="argon2-placeholder-hash",
        display_name="Murali Yandra",
    )
    account = Account(
        user_id=user.id,
        account_name="Salary Account",
        account_type="BANK",
        bank_name="ICICI",
        last_four_digits="0452",
    )

    assert isinstance(account.id, UUID)
    assert account.user_id == user.id
    assert account.account_name == "Salary Account"
    assert account.account_type == "BANK"
    assert account.bank_name == "ICICI"
    assert account.last_four_digits == "0452"
    assert account.currency == "INR"
    assert account.opening_balance == Decimal("0.00")
    assert account.estimated_balance == Decimal("0.00")
    assert account.status == "PENDING"


def test_accounts_table_has_required_columns() -> None:
    table = Account.__table__

    assert table.name == "accounts"
    assert table.c.id.primary_key is True
    assert table.c.id.nullable is False
    assert table.c.user_id.nullable is False
    assert table.c.account_name.nullable is True
    assert table.c.account_type.nullable is False
    assert table.c.bank_name.nullable is True
    assert table.c.last_four_digits.nullable is True
    assert table.c.currency.nullable is False
    assert table.c.opening_balance.nullable is False
    assert table.c.estimated_balance.nullable is False
    assert table.c.status.nullable is False
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False


def test_accounts_table_uses_decimal_money_columns() -> None:
    table = Account.__table__

    for column_name in ("opening_balance", "estimated_balance"):
        column_type = table.c[column_name].type

        assert isinstance(column_type, Numeric)
        assert column_type.precision == 18
        assert column_type.scale == 2


def test_accounts_table_has_user_foreign_key_and_unique_constraint() -> None:
    table = Account.__table__
    foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    unique_constraints = {
        constraint.name: constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert len(foreign_keys) == 1
    assert [column.name for column in foreign_keys[0].columns] == ["user_id"]
    assert [element.target_fullname for element in foreign_keys[0].elements] == [
        "users.id"
    ]
    assert [
        column.name
        for column in unique_constraints["uq_user_bank_lastfour_type"].columns
    ] == ["user_id", "bank_name", "last_four_digits", "account_type"]


def test_accounts_table_defines_required_indexes() -> None:
    indexes = {index.name: index for index in Account.__table__.indexes}

    assert [column.name for column in indexes["idx_accounts_user_id"].columns] == [
        "user_id"
    ]
    assert [column.name for column in indexes["idx_accounts_status"].columns] == [
        "status"
    ]
    assert [
        column.name for column in indexes["idx_accounts_bank_last_four"].columns
    ] == ["bank_name", "last_four_digits"]


def test_user_to_accounts_relationship_is_one_to_many() -> None:
    user_relationship = User.__mapper__.relationships["accounts"]
    account_relationship = Account.__mapper__.relationships["user"]

    assert user_relationship.uselist is True
    assert user_relationship.back_populates == "user"
    assert account_relationship.uselist is False
    assert account_relationship.back_populates == "accounts"


def test_user_model_import_resolves_accounts_relationship_in_fresh_process() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.domains.users.models import User; "
                "print(sorted(User.__mapper__.relationships.keys()))"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "accounts" in result.stdout


def test_user_to_accounts_relationship_persists() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(
            email="accounts@example.com",
            password_hash="argon2-placeholder-hash",
            display_name="Accounts User",
        )
        account = Account(
            user_id=user.id,
            account_name="Salary Account",
            account_type="BANK",
            bank_name="ICICI",
            last_four_digits="0452",
        )
        session.add(user)
        session.add(account)
        session.commit()

        stored_user = session.get(User, user.id)
        stored_account = session.exec(select(Account)).one()

        assert stored_user is not None
        assert stored_user.accounts[0].id == stored_account.id
        assert stored_account.user.id == user.id


def test_accounts_table_enforces_user_bank_last_four_type_uniqueness() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(
            email="duplicate-account@example.com",
            password_hash="argon2-placeholder-hash",
            display_name="Duplicate Account User",
        )
        first_account = Account(
            user_id=user.id,
            account_type="BANK",
            bank_name="ICICI",
            last_four_digits="0452",
        )
        duplicate_account = Account(
            user_id=user.id,
            account_type="BANK",
            bank_name="ICICI",
            last_four_digits="0452",
        )
        session.add(user)
        session.add(first_account)
        session.commit()

        session.add(duplicate_account)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("Expected duplicate account uniqueness violation.")
