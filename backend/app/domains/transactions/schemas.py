from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.shared.enums import BusinessType, TransactionDirection

UNSET = object()


@dataclass(frozen=True)
class CreateTransactionCommand:
    """Service input for creating a transaction."""

    user_id: UUID
    account_id: UUID
    amount: Decimal
    direction: TransactionDirection
    currency: str = "INR"
    business_type: BusinessType = BusinessType.UNKNOWN
    merchant_raw: str | None = None
    description: str | None = None
    reference_number: str | None = None
    upi_id: str | None = None
    transaction_timestamp: datetime | None = None
    sms_received_timestamp: datetime | None = None
    raw_event_id: UUID | None = None
    merchant_id: UUID | None = None
    category_id: UUID | None = None
    confidence_score: Decimal | None = None
    exchange_rate: Decimal | None = None
    base_currency: str | None = None
    # Set only by the ingestion pipeline. A user cannot manually post to an
    # account they archived, but a bank message proves money still moved on it,
    # and dropping that transaction would silently lose real money.
    allow_archived_account: bool = False


@dataclass(frozen=True)
class UpdateTransactionCommand:
    """Service input for updating a transaction.

    Fields default to ``UNSET`` so an omitted field is distinguishable from an
    explicit ``null``.
    """

    user_id: UUID
    transaction_id: UUID
    description: object = UNSET
    category_id: object = UNSET
    merchant_id: object = UNSET
    business_type: object = UNSET
    is_reviewed: object = UNSET


@dataclass(frozen=True)
class ListTransactionsQuery:
    """Service input for listing transactions."""

    user_id: UUID
    account_id: UUID | None = None
    category_id: UUID | None = None
    merchant_id: UUID | None = None
    business_type: BusinessType | None = None
    direction: TransactionDirection | None = None
    start_date: date | None = None
    end_date: date | None = None
    offset: int = 0
    limit: int = 50


@dataclass(frozen=True)
class TransactionPage:
    """A page of transactions plus the total matching count."""

    items: list
    total_records: int
