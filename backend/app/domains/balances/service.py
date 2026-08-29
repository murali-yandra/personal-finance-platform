"""Estimated account balances.

Balances are estimated, not authoritative: they are derived from the bank
messages the platform happened to receive. Reconciliation against a real
statement is what corrects drift (``04-database_schema.md`` section 8).
"""

import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlmodel import Session

from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.balances.models import BalanceSnapshot
from app.domains.balances.repository import BalanceRepository
from app.domains.transactions.models import Transaction
from app.events.base_event import BaseEvent
from app.shared.enums import AccountType, AuditAction, TransactionDirection
from app.shared.financial.financial_calculator import FinancialCalculator

logger = logging.getLogger(__name__)

TRANSACTION_CREATED = "TransactionCreated"


class BalanceService:
    """Keeps estimated account balances in step with transactions."""

    def __init__(
        self,
        session: Session,
        account_repository: AccountRepository,
        balance_repository: BalanceRepository | None = None,
    ) -> None:
        self._session = session
        self._accounts = account_repository
        self._balances = balance_repository

    def apply_transaction(self, transaction: Transaction) -> Decimal:
        """Apply a transaction to its account's estimated balance.

        A transfer still moves the account balance. It is excluded from income
        and expense reporting, not from the balance itself: the money really did
        leave one account and arrive in another.
        """
        account = self._session.get(Account, transaction.account_id)
        if account is None:
            logger.warning(
                "Cannot apply transaction %s: account missing",
                transaction.id,
            )
            return Decimal("0.00")

        delta = FinancialCalculator.balance_delta(
            amount=transaction.amount,
            direction=TransactionDirection(transaction.direction),
            account_type=AccountType(account.account_type),
        )
        account.estimated_balance = FinancialCalculator.apply_delta(
            account.estimated_balance,
            delta,
        )
        self._session.add(account)
        return delta

    def publish(self, event: BaseEvent) -> None:
        """Update the balance when a transaction is created.

        This runs inside the caller's transaction, so the balance and the
        transaction commit together. A balance that drifted from its
        transactions would be worse than no balance at all.
        """
        if event.event_type != TRANSACTION_CREATED:
            return

        transaction_id = _as_uuid(event.payload.get("entity_id"))
        if transaction_id is None:
            return

        transaction = self._session.get(Transaction, transaction_id)
        if transaction is None:
            return

        self.apply_transaction(transaction)

    def reconcile(
        self,
        user_id: UUID,
        account_id: UUID,
        actual_balance: Decimal,
    ) -> tuple[Account, Decimal, Decimal]:
        """Set an account's balance to a figure the user read from their bank.

        Returns the account with the estimate it held before the correction and
        the difference, so the caller can report the drift that was absorbed.
        """
        from app.domains.accounts.exceptions import AccountNotFoundError

        account = self._accounts.get_by_id(account_id=account_id, user_id=user_id)
        if account is None:
            raise AccountNotFoundError()

        previous = FinancialCalculator.to_money(account.estimated_balance)
        actual = FinancialCalculator.to_money(actual_balance)
        difference = FinancialCalculator.subtract(actual, previous)

        account.estimated_balance = actual
        self._session.add(account)
        return account, previous, difference

    def capture_snapshot(
        self,
        user_id: UUID,
        account: Account,
        snapshot_date: date,
    ) -> BalanceSnapshot:
        """Record the account's balance for a day, replacing any existing row."""
        if self._balances is None:
            raise ValueError("A balance repository is required to take snapshots.")
        return self._balances.upsert_snapshot(
            user_id=user_id,
            account_id=account.id,
            snapshot_date=snapshot_date,
            balance=FinancialCalculator.to_money(account.estimated_balance),
            currency=account.currency,
        )


def reconciliation_event(
    user_id: UUID,
    account_id: UUID,
    previous: Decimal,
    actual: Decimal,
) -> BaseEvent:
    """Build the audit event for a balance reconciliation."""
    return BaseEvent(
        event_type="BalanceReconciled",
        payload={
            "entity_type": "account",
            "entity_id": str(account_id),
            "user_id": str(user_id),
            "action": AuditAction.BALANCE_RECONCILIATION.value,
            "changes": {"estimated_balance": [str(previous), str(actual)]},
        },
    )


def _as_uuid(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            return None
    return None
