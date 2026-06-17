from collections.abc import Mapping
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domains.accounts.enums import AccountStatus
from app.domains.accounts.exceptions import DuplicateAccountIdentityError
from app.domains.accounts.models import Account

ACCOUNT_IDENTITY_UNIQUE_NAMES = {"uq_user_bank_lastfour_type"}
UPDATABLE_ACCOUNT_FIELDS = {
    "account_name",
    "account_type",
    "bank_name",
    "last_four_digits",
    "currency",
    "opening_balance",
    "estimated_balance",
    "status",
}


class AccountRepository:
    """Persistence operations for user-owned accounts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_account(self, account: Account) -> Account:
        """Persist a new account."""
        self._session.add(account)
        self._flush_with_duplicate_mapping()
        return account

    def get_account_by_id(self, account_id: UUID, user_id: UUID) -> Account | None:
        """Return one account scoped to its owning user."""
        statement = select(Account).where(
            Account.id == account_id,
            Account.user_id == user_id,
        )
        return self._session.exec(statement).first()

    def list_accounts(
        self,
        user_id: UUID,
        *,
        include_archived: bool = False,
    ) -> list[Account]:
        """Return accounts scoped to one user."""
        statement = select(Account).where(Account.user_id == user_id)
        if not include_archived:
            statement = statement.where(Account.status != AccountStatus.ARCHIVED.value)
        statement = statement.order_by(Account.created_at, Account.id)
        return list(self._session.exec(statement).all())

    def update_account(
        self,
        account_id: UUID,
        user_id: UUID,
        values: Mapping[str, Any],
    ) -> Account | None:
        """Update one user-scoped account with already-validated values."""
        account = self.get_account_by_id(account_id, user_id)
        if account is None:
            return None

        for field_name, value in values.items():
            if field_name not in UPDATABLE_ACCOUNT_FIELDS:
                raise ValueError(f"Unsupported account update field: {field_name}")
            setattr(account, field_name, _database_value(value))

        self._session.add(account)
        self._flush_with_duplicate_mapping()
        return account

    def archive_account(self, account_id: UUID, user_id: UUID) -> Account | None:
        """Archive one account without physically deleting it."""
        return self.update_account(
            account_id,
            user_id,
            {"status": AccountStatus.ARCHIVED},
        )

    def account_identity_exists(
        self,
        *,
        user_id: UUID,
        bank_name: str | None,
        last_four_digits: str | None,
        account_type: str | StrEnum,
        exclude_account_id: UUID | None = None,
    ) -> bool:
        """Return whether an account identity already exists for the user."""
        statement = select(Account.id).where(
            Account.user_id == user_id,
            Account.bank_name == bank_name,
            Account.last_four_digits == last_four_digits,
            Account.account_type == _database_value(account_type),
        )
        if exclude_account_id is not None:
            statement = statement.where(Account.id != exclude_account_id)
        return self._session.exec(statement).first() is not None

    def commit(self) -> None:
        """Commit the active transaction."""
        self._session.commit()

    def rollback(self) -> None:
        """Rollback the active transaction."""
        self._session.rollback()

    def _flush_with_duplicate_mapping(self) -> None:
        try:
            self._session.flush()
        except IntegrityError as exc:
            if _is_account_identity_unique_violation(exc):
                raise DuplicateAccountIdentityError() from exc
            raise


def _database_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    return value


def _is_account_identity_unique_violation(exc: IntegrityError) -> bool:
    constraint_name = _constraint_name(exc)
    if constraint_name in ACCOUNT_IDENTITY_UNIQUE_NAMES:
        return True

    error_message = str(exc.orig).lower()
    return "uq_user_bank_lastfour_type" in error_message or (
        "accounts.user_id" in error_message
        and "accounts.bank_name" in error_message
        and "accounts.last_four_digits" in error_message
        and "accounts.account_type" in error_message
    )


def _constraint_name(exc: IntegrityError) -> str | None:
    diagnostic = getattr(exc.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name:
        return str(constraint_name)
    return None
