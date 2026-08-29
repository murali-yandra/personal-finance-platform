from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domains.transactions.exceptions import DuplicateTransactionError
from app.domains.transactions.models import Transaction
from app.domains.transactions.schemas import ListTransactionsQuery

FINGERPRINT_UNIQUE_NAMES = {"uq_transaction_fingerprint_user"}


class TransactionRepository:
    """Persistence operations for transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, transaction_id: UUID, user_id: UUID) -> Transaction | None:
        """Return a user-owned transaction."""
        statement = select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
        return self._session.exec(statement).first()

    def find_by_fingerprint(
        self,
        user_id: UUID,
        fingerprint: str,
    ) -> Transaction | None:
        """Return an existing transaction with the same fingerprint."""
        statement = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.transaction_fingerprint == fingerprint,
        )
        return self._session.exec(statement).first()

    def list_for_user(self, query: ListTransactionsQuery) -> list[Transaction]:
        """Return a page of transactions, newest first."""
        statement = self._filtered(query)
        statement = statement.order_by(
            Transaction.transaction_timestamp.desc(),  # type: ignore[attr-defined]
            Transaction.created_at.desc(),  # type: ignore[attr-defined]
            Transaction.id,
        )
        statement = statement.offset(query.offset).limit(query.limit)
        return list(self._session.exec(statement).all())

    def count_for_user(self, query: ListTransactionsQuery) -> int:
        """Return how many transactions match the filters."""
        statement = select(func.count()).select_from(Transaction)
        statement = self._apply_filters(statement, query)
        return int(self._session.exec(statement).one())

    def add(self, transaction: Transaction) -> Transaction:
        """Persist a new transaction."""
        try:
            self._session.add(transaction)
            self._session.flush()
        except IntegrityError as exc:
            if _is_fingerprint_violation(exc):
                raise DuplicateTransactionError() from exc
            raise
        return transaction

    def flush(self) -> None:
        """Flush pending changes."""
        self._session.flush()

    def commit(self) -> None:
        """Commit the active transaction."""
        self._session.commit()

    def rollback(self) -> None:
        """Rollback the active transaction."""
        self._session.rollback()

    def refresh(self, transaction: Transaction) -> None:
        """Reload a transaction from the database."""
        self._session.refresh(transaction)

    def _filtered(self, query: ListTransactionsQuery):
        return self._apply_filters(select(Transaction), query)

    @staticmethod
    def _apply_filters(statement, query: ListTransactionsQuery):
        statement = statement.where(Transaction.user_id == query.user_id)
        if query.account_id is not None:
            statement = statement.where(Transaction.account_id == query.account_id)
        if query.category_id is not None:
            statement = statement.where(Transaction.category_id == query.category_id)
        if query.merchant_id is not None:
            statement = statement.where(Transaction.merchant_id == query.merchant_id)
        if query.business_type is not None:
            statement = statement.where(
                Transaction.business_type == query.business_type.value
            )
        if query.direction is not None:
            statement = statement.where(Transaction.direction == query.direction.value)
        if query.start_date is not None:
            statement = statement.where(
                Transaction.transaction_timestamp
                >= datetime.combine(query.start_date, time.min)
            )
        if query.end_date is not None:
            statement = statement.where(
                Transaction.transaction_timestamp
                <= datetime.combine(query.end_date, time.max)
            )
        return statement


def _is_fingerprint_violation(exc: IntegrityError) -> bool:
    diagnostic = getattr(exc.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name and str(constraint_name) in FINGERPRINT_UNIQUE_NAMES:
        return True
    return "uq_transaction_fingerprint_user" in str(exc.orig).lower()


def start_of_day(value: date) -> datetime:
    """Return the earliest instant on a date."""
    return datetime.combine(value, time.min)
