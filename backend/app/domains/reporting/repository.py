"""Read models for reporting.

Every query is scoped by ``user_id`` and excludes transfers from income and
expense figures. A transfer between the user's own accounts is not spending: the
money never left (``04-database_schema.md`` section 8). Counting it would
overstate both sides of every report.
"""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func
from sqlmodel import Session, select

from app.domains.accounts.models import Account
from app.domains.categories.models import Category
from app.domains.transactions.models import Transaction
from app.shared.enums import (
    LIABILITY_ACCOUNT_TYPES,
    AccountStatus,
    BusinessType,
    TransactionDirection,
)

# Business types that move money without being income or expense.
NON_REPORTING_BUSINESS_TYPES = (BusinessType.TRANSFER.value,)

ACTIVE_TRANSACTION_STATUS = "ACTIVE"


class ReportingRepository:
    """Aggregate queries over a user's transactions and accounts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def income_and_expenses(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[Decimal, Decimal, int]:
        """Return total income, total expenses and the transaction count."""
        statement = select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            Transaction.direction == TransactionDirection.CREDIT.value,
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Transaction.direction == TransactionDirection.DEBIT.value,
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.count(),
        )
        statement = self._reporting_scope(statement, user_id, start_date, end_date)
        income, expenses, count = self._session.exec(statement).one()
        return (
            Decimal(str(income or 0)),
            Decimal(str(expenses or 0)),
            int(count or 0),
        )

    def category_breakdown(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        direction: TransactionDirection = TransactionDirection.DEBIT,
    ) -> list[tuple[UUID | None, str | None, Decimal, int]]:
        """Return spend grouped by category, largest first."""
        statement = select(
            Transaction.category_id,
            Category.name,
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(),
        ).join(
            Category,
            Category.id == Transaction.category_id,
            isouter=True,
        )
        statement = self._reporting_scope(statement, user_id, start_date, end_date)
        statement = statement.where(Transaction.direction == direction.value)
        statement = statement.group_by(Transaction.category_id, Category.name)
        statement = statement.order_by(func.sum(Transaction.amount).desc())

        return [
            (row[0], row[1], Decimal(str(row[2] or 0)), int(row[3] or 0))
            for row in self._session.exec(statement).all()
        ]

    def monthly_income_and_expenses(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[tuple[int, int, Decimal, Decimal]]:
        """Return income and expenses grouped by calendar month."""
        rows = self._session.exec(
            self._reporting_scope(
                select(
                    Transaction.transaction_timestamp,
                    Transaction.direction,
                    Transaction.amount,
                ),
                user_id,
                start_date,
                end_date,
            )
        ).all()

        buckets: dict[tuple[int, int], list[Decimal]] = {}
        for timestamp, direction, amount in rows:
            if timestamp is None:
                continue
            key = (timestamp.year, timestamp.month)
            totals = buckets.setdefault(key, [Decimal("0.00"), Decimal("0.00")])
            index = 0 if direction == TransactionDirection.CREDIT.value else 1
            totals[index] += Decimal(str(amount))

        return [
            (year, month, totals[0], totals[1])
            for (year, month), totals in sorted(buckets.items())
        ]

    def account_summaries(
        self,
        user_id: UUID,
    ) -> list[tuple[Account, int]]:
        """Return each non-archived account with its transaction count."""
        accounts = self._session.exec(
            select(Account)
            .where(
                Account.user_id == user_id,
                Account.status != AccountStatus.ARCHIVED.value,
            )
            .order_by(Account.account_type, Account.id)
        ).all()

        counts = dict(
            self._session.exec(
                select(Transaction.account_id, func.count())
                .where(Transaction.user_id == user_id)
                .group_by(Transaction.account_id)
            ).all()
        )
        return [(account, int(counts.get(account.id, 0))) for account in accounts]

    @staticmethod
    def is_liability(account: Account) -> bool:
        """Return whether an account's balance represents money owed."""
        return account.account_type in {
            account_type.value for account_type in LIABILITY_ACCOUNT_TYPES
        }

    @staticmethod
    def _reporting_scope(
        statement,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ):
        """Scope a query to one user's reportable transactions in a window."""
        return statement.where(
            Transaction.user_id == user_id,
            Transaction.status == ACTIVE_TRANSACTION_STATUS,
            Transaction.business_type.notin_(  # type: ignore[attr-defined]
                NON_REPORTING_BUSINESS_TYPES
            ),
            Transaction.transaction_timestamp >= datetime.combine(start_date, time.min),
            Transaction.transaction_timestamp <= datetime.combine(end_date, time.max),
        )
