from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class MonthlySummary:
    """Income, expenses and the difference for one month."""

    year: int
    month: int
    income: Decimal
    expenses: Decimal
    savings: Decimal
    transaction_count: int


@dataclass(frozen=True)
class CategoryBreakdownRow:
    """Spend in one category over a period."""

    category_id: UUID | None
    category: str
    amount: Decimal
    transaction_count: int


@dataclass(frozen=True)
class AccountSummaryRow:
    """One account's balance and activity."""

    account_id: UUID
    account_name: str
    account_type: str
    currency: str
    estimated_balance: Decimal
    transaction_count: int


@dataclass(frozen=True)
class NetWorth:
    """Assets, liabilities and their difference."""

    assets: Decimal
    liabilities: Decimal
    net_worth: Decimal
    currency: str = "INR"
    accounts: list[AccountSummaryRow] = field(default_factory=list)


@dataclass(frozen=True)
class IncomeVsExpenseRow:
    """Income and expense totals for one month."""

    year: int
    month: int
    income: Decimal
    expenses: Decimal


@dataclass(frozen=True)
class ReportPeriod:
    """The date window a report covers."""

    start_date: date
    end_date: date
