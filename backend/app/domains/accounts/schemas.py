from decimal import Decimal
from typing import Any, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.domains.accounts.enums import AccountStatus, AccountType
from app.domains.accounts.models import Account
from app.shared.schemas.money import (
    MAX_MONEY_DECIMAL_PLACES,
    MAX_MONEY_INTEGER_DIGITS,
    MONEY_QUANTIZER,
    serialize_money,
    validate_money,
)
from app.shared.schemas.responses import SuccessResponse

__all__ = [
    "MAX_MONEY_DECIMAL_PLACES",
    "MAX_MONEY_INTEGER_DIGITS",
    "MONEY_QUANTIZER",
    "AccountBaseRequest",
    "AccountListResponse",
    "AccountResponse",
    "AccountResponseData",
    "CreateAccountRequest",
    "UpdateAccountRequest",
    "validate_money",
]


class AccountBaseRequest(BaseModel):
    """Shared account request validation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    account_name: str | None = Field(default=None, min_length=1, max_length=255)
    account_type: AccountType
    bank_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_four_digits: str | None = Field(default=None, min_length=1, max_length=10)
    currency: str = Field(default="INR", min_length=3, max_length=3)

    @field_validator("currency", mode="before")
    @classmethod
    def validate_currency(cls, value: Any) -> str:
        """Validate and normalize three-letter currency codes."""
        if not isinstance(value, str):
            raise ValueError("Currency must be a three-letter code.")
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("Currency must be a three-letter code.")
        return normalized

    @field_validator("last_four_digits")
    @classmethod
    def validate_last_four_digits(cls, value: str | None) -> str | None:
        """Validate optional account suffixes without inventing bank logic."""
        if value is not None and not value.isdigit():
            raise ValueError("Last four digits must contain digits only.")
        return value


class CreateAccountRequest(AccountBaseRequest):
    """Request body for creating an account."""

    opening_balance: Decimal = Field(default=Decimal("0.00"))

    @field_validator("opening_balance", mode="before")
    @classmethod
    def validate_opening_balance(cls, value: Any) -> Decimal:
        """Validate money input without accepting floats."""
        return validate_money(value)


class UpdateAccountRequest(BaseModel):
    """Request body for updating account metadata and status."""

    model_config = ConfigDict(str_strip_whitespace=True)

    account_name: str | None = Field(default=None, min_length=1, max_length=255)
    account_type: AccountType | None = None
    bank_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_four_digits: str | None = Field(default=None, min_length=1, max_length=10)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    opening_balance: Decimal | None = None
    status: AccountStatus | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def validate_currency(cls, value: Any) -> str | None:
        """Validate and normalize optional three-letter currency codes."""
        if value is None:
            return None
        return AccountBaseRequest.validate_currency(value)

    @field_validator("last_four_digits")
    @classmethod
    def validate_last_four_digits(cls, value: str | None) -> str | None:
        """Validate optional account suffixes without inventing bank logic."""
        return AccountBaseRequest.validate_last_four_digits(value)

    @field_validator("opening_balance", mode="before")
    @classmethod
    def validate_opening_balance(cls, value: Any) -> Decimal | None:
        """Validate optional money input without accepting floats."""
        if value is None:
            return None
        return validate_money(value)

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> Self:
        """Reject no-op update requests."""
        if not self.model_fields_set:
            raise ValueError("At least one account field must be provided.")
        return self


class AccountResponseData(BaseModel):
    """Account data returned inside the standard success envelope."""

    id: UUID
    account_name: str | None
    account_type: AccountType
    bank_name: str | None
    last_four_digits: str | None
    currency: str
    opening_balance: Decimal
    estimated_balance: Decimal
    status: AccountStatus

    @classmethod
    def from_account(cls, account: Account) -> Self:
        """Build response data from the SQLModel account entity."""
        return cls(
            id=account.id,
            account_name=account.account_name,
            account_type=AccountType(account.account_type),
            bank_name=account.bank_name,
            last_four_digits=account.last_four_digits,
            currency=account.currency,
            opening_balance=account.opening_balance,
            estimated_balance=account.estimated_balance,
            status=AccountStatus(account.status),
        )

    @field_serializer("opening_balance", "estimated_balance")
    def serialize_money(self, value: Decimal) -> str:
        """Serialize API money values as strings to avoid precision loss."""
        return serialize_money(value)


AccountResponse = SuccessResponse[AccountResponseData]
AccountListResponse = SuccessResponse[list[AccountResponseData]]
