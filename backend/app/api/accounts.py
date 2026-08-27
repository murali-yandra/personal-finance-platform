from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.api.dependencies.audit import get_audit_service
from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.accounts.schemas import (
    UNSET,
    CreateAccountCommand,
    ListAccountsQuery,
    UpdateAccountCommand,
)
from app.domains.accounts.service import AccountService
from app.domains.audit.service import AuditService
from app.domains.users.models import User
from app.shared.enums import AccountStatus, AccountType
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountData(BaseModel):
    """Response data for a single account."""

    id: UUID
    account_name: str | None
    account_type: str
    bank_name: str | None
    last_four_digits: str | None
    currency: str
    opening_balance: Decimal
    estimated_balance: Decimal
    status: str

    @classmethod
    def from_account(cls, account: Account) -> "AccountData":
        """Build the response payload from a persisted account."""
        return cls(
            id=account.id,
            account_name=account.account_name,
            account_type=account.account_type,
            bank_name=account.bank_name,
            last_four_digits=account.last_four_digits,
            currency=account.currency,
            opening_balance=account.opening_balance,
            estimated_balance=account.estimated_balance,
            status=account.status,
        )


class ArchivedAccountData(BaseModel):
    """Response data returned when an account is archived."""

    id: UUID
    status: str


class CreateAccountRequest(BaseModel):
    """Request body for creating an account."""

    model_config = ConfigDict(str_strip_whitespace=True)

    account_type: AccountType
    account_name: str | None = Field(default=None, max_length=255)
    bank_name: str | None = Field(default=None, max_length=100)
    last_four_digits: str | None = Field(default=None, max_length=10)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    opening_balance: Decimal = Decimal("0.00")
    status: AccountStatus = AccountStatus.ACTIVE


class UpdateAccountRequest(BaseModel):
    """Request body for updating an account.

    Every field is optional; only the ones present in the request body are applied.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    account_name: str | None = Field(default=None, max_length=255)
    bank_name: str | None = Field(default=None, max_length=100)
    last_four_digits: str | None = Field(default=None, max_length=10)
    account_type: AccountType | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: AccountStatus | None = None


AccountResponse = SuccessResponse[AccountData]
AccountListResponse = SuccessResponse[list[AccountData]]
ArchiveAccountResponse = SuccessResponse[ArchivedAccountData]


def get_account_service(
    session: Annotated[Session, Depends(get_session)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> AccountService:
    """Build the account service dependency.

    The audit service is the Sprint 3 implementation of the EventPublisher
    protocol the account service was written against in Sprint 2.
    """
    return AccountService(
        repository=AccountRepository(session),
        event_publisher=audit_service,
    )


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    request: CreateAccountRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    """Create an account owned by the authenticated user."""
    account = account_service.create_account(
        CreateAccountCommand(
            user_id=current_user.id,
            account_type=request.account_type,
            account_name=request.account_name,
            bank_name=request.bank_name,
            last_four_digits=request.last_four_digits,
            currency=request.currency,
            opening_balance=request.opening_balance,
            status=request.status,
        )
    )
    return AccountResponse(data=AccountData.from_account(account))


@router.get("", response_model=AccountListResponse)
def list_accounts(
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
    include_archived: Annotated[bool, Query()] = False,
) -> AccountListResponse:
    """List the authenticated user's accounts, excluding archived by default."""
    accounts = account_service.list_accounts(
        ListAccountsQuery(
            user_id=current_user.id,
            include_archived=include_archived,
        )
    )
    return AccountListResponse(
        data=[AccountData.from_account(account) for account in accounts]
    )


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    """Return one account owned by the authenticated user."""
    account = account_service.get_account(
        user_id=current_user.id,
        account_id=account_id,
    )
    return AccountResponse(data=AccountData.from_account(account))


@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: UUID,
    request: UpdateAccountRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    """Update metadata on an account owned by the authenticated user."""
    submitted = request.model_dump(exclude_unset=True)
    account = account_service.update_account(
        UpdateAccountCommand(
            user_id=current_user.id,
            account_id=account_id,
            **{field: _submitted_value(submitted, field) for field in _PATCH_FIELDS},
        )
    )
    return AccountResponse(data=AccountData.from_account(account))


@router.delete("/{account_id}", response_model=ArchiveAccountResponse)
def archive_account(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> ArchiveAccountResponse:
    """Archive an account. The record is never physically deleted."""
    account = account_service.archive_account(
        user_id=current_user.id,
        account_id=account_id,
    )
    return ArchiveAccountResponse(
        data=ArchivedAccountData(id=account.id, status=account.status)
    )


_PATCH_FIELDS = (
    "account_name",
    "bank_name",
    "last_four_digits",
    "account_type",
    "currency",
    "status",
)


def _submitted_value(submitted: dict[str, Any], field: str) -> Any:
    """Return the submitted value, or the sentinel when the field was omitted.

    ``exclude_unset`` keeps an explicit ``null`` distinguishable from an omitted
    field, so PATCH can clear a value without clearing everything else.
    """
    if field not in submitted:
        return UNSET
    return submitted[field]
