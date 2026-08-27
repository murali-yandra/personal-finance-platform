import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domains.accounts.repository import AccountRepository
from app.domains.transactions.events import (
    transaction_created_event,
    transaction_updated_event,
)
from app.domains.transactions.exceptions import (
    DuplicateTransactionError,
    InvalidAmountError,
    MissingAccountError,
    TransactionNotFoundError,
    TransactionValidationError,
)
from app.domains.transactions.fingerprint import build_transaction_fingerprint
from app.domains.transactions.models import Transaction
from app.domains.transactions.repository import TransactionRepository
from app.domains.transactions.schemas import (
    UNSET,
    CreateTransactionCommand,
    ListTransactionsQuery,
    TransactionPage,
    UpdateTransactionCommand,
)
from app.events.publisher import EventPublisher, NullEventPublisher
from app.shared.enums import AccountStatus, BusinessType, TransactionDirection
from app.shared.financial.financial_calculator import (
    FinancialCalculator,
    MoneyError,
)

CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")

UPDATABLE_FIELDS = (
    "description",
    "category_id",
    "merchant_id",
    "business_type",
    "is_reviewed",
)


class TransactionService:
    """Application service for the transaction lifecycle."""

    def __init__(
        self,
        repository: TransactionRepository,
        account_repository: AccountRepository,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._repository = repository
        self._account_repository = account_repository
        self._event_publisher = event_publisher or NullEventPublisher()

    def create_transaction(self, command: CreateTransactionCommand) -> Transaction:
        """Create a transaction after duplicate detection.

        Duplicate detection is a pre-check plus the partial unique index. The
        pre-check gives callers a clean conflict; the index is what actually
        holds under concurrent ingestion of the same message.
        """
        account = self._account_repository.get_by_id(
            account_id=command.account_id,
            user_id=command.user_id,
        )
        if account is None:
            raise MissingAccountError()
        if account.status == AccountStatus.ARCHIVED:
            raise TransactionValidationError(
                "Transactions cannot be posted to an archived account."
            )

        amount = _validate_amount(command.amount)
        direction = _parse_direction(command.direction)
        business_type = _parse_business_type(command.business_type)
        currency = _validate_currency(command.currency)

        fingerprint = build_transaction_fingerprint(
            user_id=command.user_id,
            account_id=command.account_id,
            amount=amount,
            direction=direction.value,
            transaction_timestamp=command.transaction_timestamp,
            merchant_raw=command.merchant_raw,
            reference_number=command.reference_number,
        )

        existing = self._repository.find_by_fingerprint(
            user_id=command.user_id,
            fingerprint=fingerprint,
        )
        if existing is not None:
            raise DuplicateTransactionError(existing_transaction_id=str(existing.id))

        transaction = Transaction(
            user_id=command.user_id,
            account_id=command.account_id,
            raw_event_id=command.raw_event_id,
            merchant_id=command.merchant_id,
            category_id=command.category_id,
            amount=amount,
            currency=currency,
            direction=direction.value,
            business_type=business_type.value,
            merchant_raw=_clean_text(command.merchant_raw),
            description=_clean_text(command.description),
            reference_number=_clean_text(command.reference_number),
            upi_id=_clean_text(command.upi_id),
            transaction_timestamp=command.transaction_timestamp,
            sms_received_timestamp=command.sms_received_timestamp,
            transaction_fingerprint=fingerprint,
            confidence_score=command.confidence_score,
            exchange_rate=command.exchange_rate,
            base_currency=(
                _validate_currency(command.base_currency)
                if command.base_currency
                else None
            ),
        )
        if transaction.exchange_rate is not None:
            transaction.base_currency_amount = FinancialCalculator.convert(
                amount,
                transaction.exchange_rate,
            )

        try:
            self._repository.add(transaction)
            self._event_publisher.publish(
                transaction_created_event(
                    user_id=command.user_id,
                    transaction_id=transaction.id,
                    account_id=command.account_id,
                )
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        self._repository.refresh(transaction)
        return transaction

    def get_transaction(self, user_id: UUID, transaction_id: UUID) -> Transaction:
        """Return one user-owned transaction."""
        transaction = self._repository.get_by_id(
            transaction_id=transaction_id,
            user_id=user_id,
        )
        if transaction is None:
            raise TransactionNotFoundError()
        return transaction

    def list_transactions(self, query: ListTransactionsQuery) -> TransactionPage:
        """Return a page of the user's transactions with the total count."""
        items = self._repository.list_for_user(query)
        total = self._repository.count_for_user(query)
        return TransactionPage(items=items, total_records=total)

    def update_transaction(self, command: UpdateTransactionCommand) -> Transaction:
        """Update a transaction's user-editable fields.

        Amount, direction, account and timestamp are deliberately not editable:
        they are the fingerprint inputs, and changing them would silently break
        duplicate detection for already-ingested messages.
        """
        transaction = self.get_transaction(
            user_id=command.user_id,
            transaction_id=command.transaction_id,
        )

        changes: dict[str, tuple[Any, Any]] = {}
        for field_name in UPDATABLE_FIELDS:
            submitted = getattr(command, field_name)
            if submitted is UNSET:
                continue
            new_value = _normalize_update_value(field_name, submitted)
            old_value = getattr(transaction, field_name)
            if old_value != new_value:
                changes[field_name] = (old_value, new_value)

        if not changes:
            return transaction

        for field_name, (_, new_value) in changes.items():
            setattr(transaction, field_name, new_value)

        try:
            self._repository.flush()
            self._event_publisher.publish(
                transaction_updated_event(
                    user_id=command.user_id,
                    transaction_id=transaction.id,
                    changes=changes,
                )
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        self._repository.refresh(transaction)
        return transaction


def _normalize_update_value(field_name: str, submitted: Any) -> Any:
    if field_name == "business_type":
        return _parse_business_type(submitted).value
    if field_name == "is_reviewed":
        return bool(submitted)
    if field_name in {"category_id", "merchant_id"}:
        if submitted is None:
            return None
        if isinstance(submitted, UUID):
            return submitted
        try:
            return UUID(str(submitted))
        except ValueError as exc:
            raise TransactionValidationError(f"{field_name} must be a UUID.") from exc
    return _clean_text(submitted)


def _validate_amount(value: Any) -> Decimal:
    try:
        amount = FinancialCalculator.to_money(value)
    except MoneyError as exc:
        raise InvalidAmountError(str(exc)) from exc
    if amount < Decimal("0.00"):
        raise InvalidAmountError()
    return amount


def _parse_direction(value: Any) -> TransactionDirection:
    if isinstance(value, TransactionDirection):
        return value
    try:
        return TransactionDirection(str(value).strip().upper())
    except ValueError as exc:
        raise TransactionValidationError(
            f"Unsupported transaction direction: {value}."
        ) from exc


def _parse_business_type(value: Any) -> BusinessType:
    if isinstance(value, BusinessType):
        return value
    try:
        return BusinessType(str(value).strip().upper())
    except ValueError as exc:
        raise TransactionValidationError(
            f"Unsupported business type: {value}."
        ) from exc


def _validate_currency(value: Any) -> str:
    if value is None:
        raise TransactionValidationError("Currency is required.")
    currency = str(value).strip().upper()
    if not CURRENCY_PATTERN.match(currency):
        raise TransactionValidationError(
            "Currency must be a three-letter ISO 4217 code."
        )
    return currency


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
