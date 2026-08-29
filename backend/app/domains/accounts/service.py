import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domains.accounts.events import (
    account_archived_event,
    account_created_event,
    account_updated_event,
)
from app.domains.accounts.exceptions import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    AccountValidationError,
    ArchivedAccountImmutableError,
    InvalidAccountStatusTransitionError,
    InvalidAccountTypeError,
)
from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.accounts.schemas import (
    UNSET,
    CreateAccountCommand,
    ListAccountsQuery,
    UpdateAccountCommand,
)
from app.events.publisher import EventPublisher, NullEventPublisher
from app.shared.enums import AccountStatus, AccountType

CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
LAST_FOUR_DIGITS_PATTERN = re.compile(r"^\d{1,10}$")

DEFAULT_LIST_STATUSES: tuple[AccountStatus, ...] = (
    AccountStatus.PENDING,
    AccountStatus.ACTIVE,
    AccountStatus.DISABLED,
)

ALLOWED_STATUS_TRANSITIONS: dict[AccountStatus, frozenset[AccountStatus]] = {
    AccountStatus.PENDING: frozenset(
        {AccountStatus.ACTIVE, AccountStatus.DISABLED, AccountStatus.ARCHIVED}
    ),
    AccountStatus.ACTIVE: frozenset({AccountStatus.DISABLED, AccountStatus.ARCHIVED}),
    AccountStatus.DISABLED: frozenset({AccountStatus.ACTIVE, AccountStatus.ARCHIVED}),
    AccountStatus.ARCHIVED: frozenset(),
}

UPDATABLE_FIELDS = (
    "account_name",
    "bank_name",
    "last_four_digits",
    "account_type",
    "currency",
    "status",
)

IDENTITY_FIELDS = ("bank_name", "last_four_digits", "account_type")


class AccountService:
    """Application service for account management."""

    def __init__(
        self,
        repository: AccountRepository,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher or NullEventPublisher()

    def create_account(self, command: CreateAccountCommand) -> Account:
        """Create an account for the calling user."""
        account_type = _parse_account_type(command.account_type)
        status = _parse_status(command.status)
        if status is AccountStatus.ARCHIVED:
            raise AccountValidationError("An account cannot be created as ARCHIVED.")

        account_name = _normalize_optional_text(command.account_name)
        bank_name = _normalize_optional_text(command.bank_name)
        last_four_digits = _validate_last_four_digits(command.last_four_digits)
        currency = _validate_currency(command.currency)
        opening_balance = _validate_opening_balance(command.opening_balance)

        if (
            self._repository.find_duplicate(
                user_id=command.user_id,
                bank_name=bank_name,
                last_four_digits=last_four_digits,
                account_type=account_type.value,
            )
            is not None
        ):
            raise AccountAlreadyExistsError()

        account = Account(
            user_id=command.user_id,
            account_name=account_name,
            account_type=account_type.value,
            bank_name=bank_name,
            last_four_digits=last_four_digits,
            currency=currency,
            opening_balance=opening_balance,
            estimated_balance=opening_balance,
            status=status.value,
        )

        try:
            self._repository.add(account)
            self._event_publisher.publish(
                account_created_event(user_id=command.user_id, account_id=account.id)
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        self._repository.refresh(account)
        return account

    def get_account(self, user_id: UUID, account_id: UUID) -> Account:
        """Return one user-owned account."""
        account = self._repository.get_by_id(account_id=account_id, user_id=user_id)
        if account is None:
            raise AccountNotFoundError()
        return account

    def list_accounts(self, query: ListAccountsQuery) -> list[Account]:
        """Return the user's accounts.

        Archived accounts are excluded unless explicitly requested, per
        ``08-api_contracts.md`` section 7.2.
        """
        if query.statuses:
            statuses = tuple(_parse_status(status) for status in query.statuses)
        elif query.include_archived:
            statuses = ()
        else:
            statuses = DEFAULT_LIST_STATUSES
        return self._repository.list_for_user(user_id=query.user_id, statuses=statuses)

    def update_account(self, command: UpdateAccountCommand) -> Account:
        """Update account metadata and optionally its status."""
        account = self.get_account(
            user_id=command.user_id,
            account_id=command.account_id,
        )
        if account.status == AccountStatus.ARCHIVED:
            raise ArchivedAccountImmutableError()

        changes = self._collect_changes(account, command)
        if not changes:
            return account

        self._guard_duplicate_identity(account, changes)

        for field_name, (_, new_value) in changes.items():
            setattr(account, field_name, new_value)

        try:
            self._repository.flush()
            self._event_publisher.publish(
                account_updated_event(
                    user_id=command.user_id,
                    account_id=account.id,
                    changes=changes,
                )
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        self._repository.refresh(account)
        return account

    def archive_account(self, user_id: UUID, account_id: UUID) -> Account:
        """Archive an account without deleting the record.

        Archiving is idempotent: re-archiving raises no event and changes nothing.
        """
        account = self.get_account(user_id=user_id, account_id=account_id)
        if account.status == AccountStatus.ARCHIVED:
            return account

        account.status = AccountStatus.ARCHIVED.value

        try:
            self._repository.flush()
            self._event_publisher.publish(
                account_archived_event(user_id=user_id, account_id=account.id)
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        self._repository.refresh(account)
        return account

    def _collect_changes(
        self,
        account: Account,
        command: UpdateAccountCommand,
    ) -> dict[str, tuple[Any, Any]]:
        changes: dict[str, tuple[Any, Any]] = {}
        for field_name in UPDATABLE_FIELDS:
            submitted = getattr(command, field_name)
            if submitted is UNSET:
                continue

            new_value = self._normalize_update_value(account, field_name, submitted)
            old_value = getattr(account, field_name)
            if old_value != new_value:
                changes[field_name] = (old_value, new_value)
        return changes

    @staticmethod
    def _normalize_update_value(
        account: Account,
        field_name: str,
        submitted: Any,
    ) -> Any:
        if field_name == "account_type":
            return _parse_account_type(submitted).value
        if field_name == "status":
            target = _parse_status(submitted)
            current = _parse_status(account.status)
            if (
                target is not current
                and target not in ALLOWED_STATUS_TRANSITIONS[current]
            ):
                raise InvalidAccountStatusTransitionError(current.value, target.value)
            return target.value
        if field_name == "currency":
            return _validate_currency(submitted)
        if field_name == "last_four_digits":
            return _validate_last_four_digits(submitted)
        return _normalize_optional_text(submitted)

    def _guard_duplicate_identity(
        self,
        account: Account,
        changes: dict[str, tuple[Any, Any]],
    ) -> None:
        if not any(field_name in changes for field_name in IDENTITY_FIELDS):
            return

        def resolved(field_name: str) -> Any:
            if field_name in changes:
                return changes[field_name][1]
            return getattr(account, field_name)

        duplicate = self._repository.find_duplicate(
            user_id=account.user_id,
            bank_name=resolved("bank_name"),
            last_four_digits=resolved("last_four_digits"),
            account_type=resolved("account_type"),
            exclude_account_id=account.id,
        )
        if duplicate is not None:
            raise AccountAlreadyExistsError()


def _parse_account_type(value: Any) -> AccountType:
    if isinstance(value, AccountType):
        return value
    try:
        return AccountType(str(value).strip().upper())
    except ValueError as exc:
        raise InvalidAccountTypeError(str(value)) from exc


def _parse_status(value: Any) -> AccountStatus:
    if isinstance(value, AccountStatus):
        return value
    try:
        return AccountStatus(str(value).strip().upper())
    except ValueError as exc:
        raise AccountValidationError(f"Unsupported account status: {value}.") from exc


def _validate_currency(value: Any) -> str:
    if value is None:
        raise AccountValidationError("Currency is required.")
    currency = str(value).strip().upper()
    if not CURRENCY_PATTERN.match(currency):
        raise AccountValidationError("Currency must be a three-letter ISO 4217 code.")
    return currency


def _validate_last_four_digits(value: Any) -> str | None:
    if value is None:
        return None
    digits = str(value).strip()
    if not digits:
        return None
    if not LAST_FOUR_DIGITS_PATTERN.match(digits):
        raise AccountValidationError("Last four digits must be numeric.")
    return digits


def _validate_opening_balance(value: Decimal) -> Decimal:
    balance = Decimal(str(value))
    if balance.is_nan() or balance.is_infinite():
        raise AccountValidationError("Opening balance must be a finite amount.")
    return balance.quantize(Decimal("0.01"))


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text
