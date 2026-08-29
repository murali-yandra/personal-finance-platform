from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.api.dependencies.audit import get_audit_service
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.pagination import Pagination, get_pagination
from app.db.session import get_session
from app.domains.accounts.repository import AccountRepository
from app.domains.audit.service import AuditService
from app.domains.balances.service import BalanceService
from app.domains.transactions.models import Transaction
from app.domains.transactions.repository import TransactionRepository
from app.domains.transactions.schemas import (
    UNSET,
    CreateTransactionCommand,
    ListTransactionsQuery,
    UpdateTransactionCommand,
)
from app.domains.transactions.service import TransactionService
from app.domains.users.models import User
from app.events.publisher import CompositeEventPublisher
from app.shared.enums import BusinessType, TransactionDirection
from app.shared.schemas.responses import (
    PageMeta,
    PaginatedResponse,
    SuccessResponse,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


class TransactionData(BaseModel):
    """Response data for a single transaction."""

    id: UUID
    account_id: UUID
    raw_event_id: UUID | None
    merchant_id: UUID | None
    category_id: UUID | None
    amount: Decimal
    currency: str
    direction: str
    business_type: str
    merchant_raw: str | None
    description: str | None
    reference_number: str | None
    upi_id: str | None
    transaction_timestamp: datetime | None
    confidence_score: Decimal | None
    is_reviewed: bool
    status: str

    @classmethod
    def from_transaction(cls, transaction: Transaction) -> "TransactionData":
        """Build the response payload from a persisted transaction."""
        return cls(
            id=transaction.id,
            account_id=transaction.account_id,
            raw_event_id=transaction.raw_event_id,
            merchant_id=transaction.merchant_id,
            category_id=transaction.category_id,
            amount=transaction.amount,
            currency=transaction.currency,
            direction=transaction.direction,
            business_type=transaction.business_type,
            merchant_raw=transaction.merchant_raw,
            description=transaction.description,
            reference_number=transaction.reference_number,
            upi_id=transaction.upi_id,
            transaction_timestamp=transaction.transaction_timestamp,
            confidence_score=transaction.confidence_score,
            is_reviewed=transaction.is_reviewed,
            status=transaction.status,
        )


class CreateTransactionRequest(BaseModel):
    """Request body for manually creating a transaction."""

    model_config = ConfigDict(str_strip_whitespace=True)

    account_id: UUID
    amount: Decimal = Field(ge=0)
    direction: TransactionDirection
    currency: str = Field(default="INR", min_length=3, max_length=3)
    business_type: BusinessType = BusinessType.UNKNOWN
    merchant_raw: str | None = Field(default=None, max_length=255)
    description: str | None = None
    reference_number: str | None = Field(default=None, max_length=255)
    upi_id: str | None = Field(default=None, max_length=255)
    transaction_timestamp: datetime | None = None
    category_id: UUID | None = None
    merchant_id: UUID | None = None


class UpdateTransactionRequest(BaseModel):
    """Request body for updating a transaction.

    Amount, direction, account and timestamp are not editable: they are the
    fingerprint inputs, so changing them would break duplicate detection.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    description: str | None = None
    category_id: UUID | None = None
    merchant_id: UUID | None = None
    business_type: BusinessType | None = None
    is_reviewed: bool | None = None


TransactionResponse = SuccessResponse[TransactionData]
TransactionListResponse = PaginatedResponse[TransactionData]


def get_transaction_service(
    session: Annotated[Session, Depends(get_session)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> TransactionService:
    """Build the transaction service dependency.

    The publisher must fan out to the balance service as well as the audit
    service: a manually posted transaction moves real money, so it has to move
    the account balance exactly like an ingested one does. Publishing to audit
    alone leaves ``estimated_balance`` stale.
    """
    return TransactionService(
        repository=TransactionRepository(session),
        account_repository=AccountRepository(session),
        event_publisher=CompositeEventPublisher(
            audit_service,
            BalanceService(
                session=session,
                account_repository=AccountRepository(session),
            ),
        ),
    )


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    request: CreateTransactionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[
        TransactionService,
        Depends(get_transaction_service),
    ],
) -> TransactionResponse:
    """Create a transaction owned by the authenticated user."""
    transaction = transaction_service.create_transaction(
        CreateTransactionCommand(
            user_id=current_user.id,
            account_id=request.account_id,
            amount=request.amount,
            direction=request.direction,
            currency=request.currency,
            business_type=request.business_type,
            merchant_raw=request.merchant_raw,
            description=request.description,
            reference_number=request.reference_number,
            upi_id=request.upi_id,
            transaction_timestamp=request.transaction_timestamp,
            category_id=request.category_id,
            merchant_id=request.merchant_id,
        )
    )
    return TransactionResponse(data=TransactionData.from_transaction(transaction))


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[
        TransactionService,
        Depends(get_transaction_service),
    ],
    pagination: Annotated[Pagination, Depends(get_pagination)],
    account_id: Annotated[UUID | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
    merchant_id: Annotated[UUID | None, Query()] = None,
    business_type: Annotated[BusinessType | None, Query()] = None,
    direction: Annotated[TransactionDirection | None, Query()] = None,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> TransactionListResponse:
    """List the authenticated user's transactions."""
    page = transaction_service.list_transactions(
        ListTransactionsQuery(
            user_id=current_user.id,
            account_id=account_id,
            category_id=category_id,
            merchant_id=merchant_id,
            business_type=business_type,
            direction=direction,
            start_date=start_date,
            end_date=end_date,
            offset=pagination.offset,
            limit=pagination.limit,
        )
    )
    return TransactionListResponse(
        data=[TransactionData.from_transaction(item) for item in page.items],
        meta=PageMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_records=page.total_records,
        ),
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[
        TransactionService,
        Depends(get_transaction_service),
    ],
) -> TransactionResponse:
    """Return one transaction owned by the authenticated user."""
    transaction = transaction_service.get_transaction(
        user_id=current_user.id,
        transaction_id=transaction_id,
    )
    return TransactionResponse(data=TransactionData.from_transaction(transaction))


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: UUID,
    request: UpdateTransactionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[
        TransactionService,
        Depends(get_transaction_service),
    ],
) -> TransactionResponse:
    """Update the user-editable fields of a transaction."""
    submitted = request.model_dump(exclude_unset=True)
    transaction = transaction_service.update_transaction(
        UpdateTransactionCommand(
            user_id=current_user.id,
            transaction_id=transaction_id,
            **{field: _submitted(submitted, field) for field in _PATCH_FIELDS},
        )
    )
    return TransactionResponse(data=TransactionData.from_transaction(transaction))


_PATCH_FIELDS = (
    "description",
    "category_id",
    "merchant_id",
    "business_type",
    "is_reviewed",
)


def _submitted(submitted: dict[str, Any], field: str) -> Any:
    if field not in submitted:
        return UNSET
    return submitted[field]
