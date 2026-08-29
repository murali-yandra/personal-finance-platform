"""Turns domain events into Telegram notifications.

This is an ``EventPublisher``, so no service ever calls Telegram directly
(``12-coding_standards.md`` section 23). It is registered behind a
``BufferedEventPublisher``, which releases events only after the database
transaction commits -- otherwise the user could be told about a transaction that
then rolled back.
"""

import logging
from uuid import UUID

from sqlmodel import Session

from app.domains.accounts.models import Account
from app.domains.transactions.models import Transaction
from app.domains.users.models import User
from app.events.base_event import BaseEvent
from app.shared.enums import NotificationMode
from app.telegram.client import TelegramClient
from app.telegram.formatter import format_transaction_notification

logger = logging.getLogger(__name__)

TRANSACTION_CREATED = "TransactionCreated"

# Confidence at or below this is treated as low, and is what
# LOW_CONFIDENCE_ONLY exists to surface.
LOW_CONFIDENCE_THRESHOLD = 0.80


class TelegramNotifier:
    """Sends a Telegram message when a transaction is created."""

    def __init__(
        self,
        client: TelegramClient,
        session: Session,
        enabled: bool = True,
    ) -> None:
        self._client = client
        self._session = session
        self._enabled = enabled

    def publish(self, event: BaseEvent) -> None:
        """Notify the user about a newly created transaction.

        Delivery failures are swallowed. A Telegram outage must never affect
        SMS processing or transaction creation
        (``09-error_handling_standards.md`` section 13).
        """
        if not self._enabled or event.event_type != TRANSACTION_CREATED:
            return

        try:
            self._notify(event)
        except Exception:
            logger.exception("Telegram notification failed; continuing.")

    def _notify(self, event: BaseEvent) -> None:
        transaction_id = _as_uuid(event.payload.get("entity_id"))
        user_id = _as_uuid(event.payload.get("user_id"))
        if transaction_id is None or user_id is None:
            return

        user = self._session.get(User, user_id)
        if user is None or not user.telegram_chat_id:
            return

        transaction = self._session.get(Transaction, transaction_id)
        if transaction is None:
            return

        if not self._should_notify(user, transaction):
            return

        account = self._session.get(Account, transaction.account_id)
        text = format_transaction_notification(
            transaction=transaction,
            account=account,
            needs_review=_needs_review(transaction, account),
        )
        self._client.send_message(user.telegram_chat_id, text)

    def _should_notify(self, user: User, transaction: Transaction) -> bool:
        """Apply the user's notification preference."""
        mode = _notification_mode(user)

        if mode is NotificationMode.DISABLED:
            return False
        if mode is NotificationMode.ALWAYS:
            return True
        if mode is NotificationMode.LOW_CONFIDENCE_ONLY:
            return _is_low_confidence(transaction)
        # Digest modes are delivered by a scheduled job, not per transaction.
        return False


def _notification_mode(user: User) -> NotificationMode:
    settings = getattr(user, "settings", None)
    raw = getattr(settings, "notification_mode", None)
    if raw is None:
        return NotificationMode.LOW_CONFIDENCE_ONLY
    try:
        return NotificationMode(str(raw).upper())
    except ValueError:
        return NotificationMode.LOW_CONFIDENCE_ONLY


def _is_low_confidence(transaction: Transaction) -> bool:
    """Return whether a transaction warrants the user's attention.

    A transaction with no confidence score was entered by hand rather than
    parsed, so there is nothing uncertain to review.
    """
    if transaction.confidence_score is None:
        return False
    return float(transaction.confidence_score) <= LOW_CONFIDENCE_THRESHOLD


def _needs_review(transaction: Transaction, account: Account | None) -> bool:
    if account is not None and account.status == "PENDING":
        return True
    return transaction.merchant_id is None and bool(transaction.merchant_raw)


def _as_uuid(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            return None
    return None
