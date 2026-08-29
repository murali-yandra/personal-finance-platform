from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domains.accounts.exceptions import AccountAlreadyExistsError
from app.domains.accounts.models import Account
from app.shared.enums import AccountStatus

ACCOUNT_UNIQUE_CONSTRAINT_NAMES = {"uq_user_bank_lastfour_type"}


class AccountRepository:
    """Persistence operations for accounts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, account_id: UUID, user_id: UUID) -> Account | None:
        """Return a user-owned account, or ``None`` when it is not theirs."""
        statement = select(Account).where(
            Account.id == account_id,
            Account.user_id == user_id,
        )
        return self._session.exec(statement).first()

    def list_for_user(
        self,
        user_id: UUID,
        statuses: tuple[AccountStatus, ...] | None = None,
    ) -> list[Account]:
        """Return the user's accounts, optionally filtered by status."""
        statement = select(Account).where(Account.user_id == user_id)
        if statuses:
            statement = statement.where(
                Account.status.in_([status.value for status in statuses])  # type: ignore[attr-defined]
            )
        statement = statement.order_by(Account.created_at, Account.id)  # type: ignore[arg-type]
        return list(self._session.exec(statement).all())

    def find_duplicate(
        self,
        user_id: UUID,
        bank_name: str | None,
        last_four_digits: str | None,
        account_type: str,
        exclude_account_id: UUID | None = None,
    ) -> Account | None:
        """Return an account matching the uniqueness tuple, if one exists.

        Mirrors the ``uq_user_bank_lastfour_type`` constraint so the service can
        report a clean conflict instead of relying on the database error.
        """
        statement = select(Account).where(
            Account.user_id == user_id,
            Account.bank_name == bank_name,
            Account.last_four_digits == last_four_digits,
            Account.account_type == account_type,
        )
        if exclude_account_id is not None:
            statement = statement.where(Account.id != exclude_account_id)
        return self._session.exec(statement).first()

    def add(self, account: Account) -> Account:
        """Persist a new account."""
        try:
            self._session.add(account)
            self._session.flush()
        except IntegrityError as exc:
            if _is_account_unique_violation(exc):
                raise AccountAlreadyExistsError() from exc
            raise
        return account

    def flush(self) -> None:
        """Flush pending changes, translating uniqueness violations."""
        try:
            self._session.flush()
        except IntegrityError as exc:
            if _is_account_unique_violation(exc):
                raise AccountAlreadyExistsError() from exc
            raise

    def commit(self) -> None:
        """Commit the active transaction."""
        self._session.commit()

    def rollback(self) -> None:
        """Rollback the active transaction."""
        self._session.rollback()

    def refresh(self, account: Account) -> None:
        """Reload an account from the database."""
        self._session.refresh(account)


def _is_account_unique_violation(exc: IntegrityError) -> bool:
    constraint_name = _constraint_name(exc)
    if constraint_name in ACCOUNT_UNIQUE_CONSTRAINT_NAMES:
        return True
    error_message = str(exc.orig).lower()
    return "uq_user_bank_lastfour_type" in error_message


def _constraint_name(exc: IntegrityError) -> str | None:
    diagnostic = getattr(exc.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name:
        return str(constraint_name)
    return None
