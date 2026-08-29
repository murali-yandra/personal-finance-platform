from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlmodel import Session, select

from app.domains.balances.models import BalanceSnapshot


class BalanceRepository:
    """Persistence operations for balance snapshots."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_snapshot(
        self,
        account_id: UUID,
        snapshot_date: date,
    ) -> BalanceSnapshot | None:
        """Return the snapshot for an account on a date."""
        statement = select(BalanceSnapshot).where(
            BalanceSnapshot.account_id == account_id,
            BalanceSnapshot.snapshot_date == snapshot_date,
        )
        return self._session.exec(statement).first()

    def upsert_snapshot(
        self,
        user_id: UUID,
        account_id: UUID,
        snapshot_date: date,
        balance: Decimal,
        currency: str,
    ) -> BalanceSnapshot:
        """Insert or update the snapshot for an account on a date.

        Updating rather than inserting keeps a re-run of the snapshot job
        idempotent, which the account/date uniqueness constraint requires.
        """
        existing = self.get_snapshot(account_id, snapshot_date)
        if existing is not None:
            existing.balance = balance
            existing.currency = currency
            self._session.add(existing)
            self._session.flush()
            return existing

        snapshot = BalanceSnapshot(
            user_id=user_id,
            account_id=account_id,
            snapshot_date=snapshot_date,
            balance=balance,
            currency=currency,
        )
        self._session.add(snapshot)
        self._session.flush()
        return snapshot

    def list_for_account(
        self,
        user_id: UUID,
        account_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[BalanceSnapshot]:
        """Return an account's snapshots in date order."""
        statement = select(BalanceSnapshot).where(
            BalanceSnapshot.user_id == user_id,
            BalanceSnapshot.account_id == account_id,
        )
        if start_date is not None:
            statement = statement.where(BalanceSnapshot.snapshot_date >= start_date)
        if end_date is not None:
            statement = statement.where(BalanceSnapshot.snapshot_date <= end_date)
        statement = statement.order_by(BalanceSnapshot.snapshot_date)
        return list(self._session.exec(statement).all())

    def commit(self) -> None:
        """Commit the active transaction."""
        self._session.commit()

    def rollback(self) -> None:
        """Rollback the active transaction."""
        self._session.rollback()
