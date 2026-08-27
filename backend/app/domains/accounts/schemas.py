from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.shared.enums import AccountStatus, AccountType

UNSET = object()


@dataclass(frozen=True)
class CreateAccountCommand:
    """Service input for creating an account."""

    user_id: UUID
    account_type: AccountType
    account_name: str | None = None
    bank_name: str | None = None
    last_four_digits: str | None = None
    currency: str = "INR"
    opening_balance: Decimal = Decimal("0.00")
    status: AccountStatus = AccountStatus.ACTIVE


@dataclass(frozen=True)
class UpdateAccountCommand:
    """Service input for updating account metadata.

    Fields default to ``UNSET`` so an explicit ``null`` can be told apart from a
    field the caller omitted. PATCH must only touch what was sent.
    """

    user_id: UUID
    account_id: UUID
    account_name: object = UNSET
    bank_name: object = UNSET
    last_four_digits: object = UNSET
    account_type: object = UNSET
    currency: object = UNSET
    status: object = UNSET


@dataclass(frozen=True)
class ListAccountsQuery:
    """Service input for listing a user's accounts."""

    user_id: UUID
    include_archived: bool = False
    statuses: tuple[AccountStatus, ...] = field(default_factory=tuple)
