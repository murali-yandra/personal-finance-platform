from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.domains.reporting.repository import ReportingRepository
from app.domains.reporting.service import ReportingService
from app.domains.users.models import User
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/reports", tags=["reports"])


class MonthlySummaryData(BaseModel):
    """Response data for the monthly summary report."""

    year: int
    month: int
    income: Decimal
    expenses: Decimal
    savings: Decimal
    transaction_count: int


class CategoryBreakdownData(BaseModel):
    """Response data for one category breakdown row."""

    category_id: UUID | None
    category: str
    amount: Decimal
    transaction_count: int


class IncomeVsExpenseData(BaseModel):
    """Response data for one income-versus-expense row."""

    year: int
    month: int
    income: Decimal
    expenses: Decimal


class AccountSummaryData(BaseModel):
    """Response data for one account summary row."""

    account_id: UUID
    account_name: str
    account_type: str
    currency: str
    estimated_balance: Decimal
    transaction_count: int


class NetWorthData(BaseModel):
    """Response data for the net worth report."""

    assets: Decimal
    liabilities: Decimal
    net_worth: Decimal
    currency: str
    accounts: list[AccountSummaryData]


MonthlySummaryResponse = SuccessResponse[MonthlySummaryData]
CategoryBreakdownResponse = SuccessResponse[list[CategoryBreakdownData]]
IncomeVsExpenseResponse = SuccessResponse[list[IncomeVsExpenseData]]
AccountSummaryResponse = SuccessResponse[list[AccountSummaryData]]
NetWorthResponse = SuccessResponse[NetWorthData]


def get_reporting_service(
    session: Annotated[Session, Depends(get_session)],
) -> ReportingService:
    """Build the reporting service dependency."""
    return ReportingService(repository=ReportingRepository(session))


@router.get("/monthly-summary", response_model=MonthlySummaryResponse)
def monthly_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting: Annotated[ReportingService, Depends(get_reporting_service)],
    year: Annotated[int, Query()],
    month: Annotated[int, Query(ge=1, le=12)],
) -> MonthlySummaryResponse:
    """Return income, expenses and savings for one calendar month."""
    summary = reporting.monthly_summary(
        user_id=current_user.id,
        year=year,
        month=month,
    )
    return MonthlySummaryResponse(data=MonthlySummaryData(**summary.__dict__))


@router.get("/category-breakdown", response_model=CategoryBreakdownResponse)
def category_breakdown(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting: Annotated[ReportingService, Depends(get_reporting_service)],
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
) -> CategoryBreakdownResponse:
    """Return spend per category over a window, largest first."""
    rows = reporting.category_breakdown(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    return CategoryBreakdownResponse(
        data=[CategoryBreakdownData(**row.__dict__) for row in rows]
    )


@router.get("/income-vs-expense", response_model=IncomeVsExpenseResponse)
def income_vs_expense(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting: Annotated[ReportingService, Depends(get_reporting_service)],
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
) -> IncomeVsExpenseResponse:
    """Return income and expenses per month over a window."""
    rows = reporting.income_vs_expense(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
    return IncomeVsExpenseResponse(
        data=[IncomeVsExpenseData(**row.__dict__) for row in rows]
    )


@router.get("/account-summary", response_model=AccountSummaryResponse)
def account_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting: Annotated[ReportingService, Depends(get_reporting_service)],
) -> AccountSummaryResponse:
    """Return every non-archived account with its balance and activity."""
    rows = reporting.account_summary(current_user.id)
    return AccountSummaryResponse(
        data=[AccountSummaryData(**row.__dict__) for row in rows]
    )


@router.get("/net-worth", response_model=NetWorthResponse)
def net_worth(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting: Annotated[ReportingService, Depends(get_reporting_service)],
) -> NetWorthResponse:
    """Return assets, liabilities and net worth."""
    result = reporting.net_worth(current_user.id)
    return NetWorthResponse(
        data=NetWorthData(
            assets=result.assets,
            liabilities=result.liabilities,
            net_worth=result.net_worth,
            currency=result.currency,
            accounts=[AccountSummaryData(**row.__dict__) for row in result.accounts],
        )
    )
