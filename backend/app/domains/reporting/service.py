import calendar
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domains.reporting.repository import ReportingRepository
from app.domains.reporting.schemas import (
    AccountSummaryRow,
    CategoryBreakdownRow,
    IncomeVsExpenseRow,
    MonthlySummary,
    NetWorth,
    ReportPeriod,
)
from app.shared.exceptions.base import ApplicationError
from app.shared.financial.financial_calculator import FinancialCalculator

UNCATEGORIZED = "Uncategorized"
MIN_YEAR = 2000
MAX_YEAR = 2100


class ReportValidationError(ApplicationError):
    """Raised when report parameters are out of range."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
        )


class ReportingService:
    """Builds the reports exposed under /api/v1/reports."""

    def __init__(self, repository: ReportingRepository) -> None:
        self._repository = repository

    def monthly_summary(
        self,
        user_id: UUID,
        year: int,
        month: int,
    ) -> MonthlySummary:
        """Return income, expenses and savings for one calendar month."""
        period = month_period(year, month)
        income, expenses, count = self._repository.income_and_expenses(
            user_id=user_id,
            start_date=period.start_date,
            end_date=period.end_date,
        )
        return MonthlySummary(
            year=year,
            month=month,
            income=FinancialCalculator.to_money(income),
            expenses=FinancialCalculator.to_money(expenses),
            savings=FinancialCalculator.subtract(income, expenses),
            transaction_count=count,
        )

    def category_breakdown(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[CategoryBreakdownRow]:
        """Return spend per category over a window, largest first."""
        _validate_range(start_date, end_date)
        rows = self._repository.category_breakdown(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
        return [
            CategoryBreakdownRow(
                category_id=category_id,
                category=name or UNCATEGORIZED,
                amount=FinancialCalculator.to_money(amount),
                transaction_count=count,
            )
            for category_id, name, amount, count in rows
        ]

    def income_vs_expense(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[IncomeVsExpenseRow]:
        """Return income and expenses per month over a window."""
        _validate_range(start_date, end_date)
        rows = self._repository.monthly_income_and_expenses(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
        return [
            IncomeVsExpenseRow(
                year=year,
                month=month,
                income=FinancialCalculator.to_money(income),
                expenses=FinancialCalculator.to_money(expenses),
            )
            for year, month, income, expenses in rows
        ]

    def account_summary(self, user_id: UUID) -> list[AccountSummaryRow]:
        """Return every non-archived account with its balance and activity."""
        return [
            AccountSummaryRow(
                account_id=account.id,
                account_name=_account_label(account),
                account_type=account.account_type,
                currency=account.currency,
                estimated_balance=FinancialCalculator.to_money(
                    account.estimated_balance
                ),
                transaction_count=count,
            )
            for account, count in self._repository.account_summaries(user_id)
        ]

    def net_worth(self, user_id: UUID) -> NetWorth:
        """Return assets, liabilities and net worth.

        Liability balances are stored as a positive amount owed, so they are
        summed separately and subtracted rather than simply added
        (``04-database_schema.md`` section 8).
        """
        assets = Decimal("0.00")
        liabilities = Decimal("0.00")
        rows: list[AccountSummaryRow] = []

        for account, count in self._repository.account_summaries(user_id):
            balance = FinancialCalculator.to_money(account.estimated_balance)
            if self._repository.is_liability(account):
                liabilities = FinancialCalculator.add(liabilities, balance)
            else:
                assets = FinancialCalculator.add(assets, balance)

            rows.append(
                AccountSummaryRow(
                    account_id=account.id,
                    account_name=_account_label(account),
                    account_type=account.account_type,
                    currency=account.currency,
                    estimated_balance=balance,
                    transaction_count=count,
                )
            )

        return NetWorth(
            assets=assets,
            liabilities=liabilities,
            net_worth=FinancialCalculator.subtract(assets, liabilities),
            accounts=rows,
        )


def month_period(year: int, month: int) -> ReportPeriod:
    """Return the first and last dates of a calendar month."""
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ReportValidationError(f"Year must be between {MIN_YEAR} and {MAX_YEAR}.")
    if not 1 <= month <= 12:
        raise ReportValidationError("Month must be between 1 and 12.")

    last_day = calendar.monthrange(year, month)[1]
    return ReportPeriod(
        start_date=date(year, month, 1),
        end_date=date(year, month, last_day),
    )


def _validate_range(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        raise ReportValidationError("start_date must not be after end_date.")


def _account_label(account) -> str:
    if account.account_name:
        return account.account_name
    parts = [part for part in (account.bank_name, account.last_four_digits) if part]
    return " ".join(parts) if parts else account.account_type
