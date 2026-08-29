"""Telegram integration (Sprint 8)."""

from datetime import datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.config import get_settings
from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.categories.repository import CategoryRepository
from app.domains.ingestion.pipeline import SmsPipeline
from app.domains.ingestion.repository import RawEventRepository
from app.domains.ingestion.schemas import IngestSmsCommand
from app.domains.ingestion.service import IngestionService
from app.domains.merchants.repository import MerchantRepository
from app.domains.merchants.service import MerchantService
from app.domains.transactions.models import Transaction
from app.domains.transactions.repository import TransactionRepository
from app.domains.transactions.service import TransactionService
from app.domains.users.models import User, UserSettings
from app.events.base_event import BaseEvent
from app.events.publisher import (
    BufferedEventPublisher,
    CompositeEventPublisher,
    RecordingEventPublisher,
)
from app.shared.enums import (
    AccountStatus,
    AccountType,
    NotificationMode,
    TransactionDirection,
)
from app.telegram.client import FakeTelegramClient, NullTelegramClient
from app.telegram.commands import (
    HELP_MESSAGE,
    START_MESSAGE,
    UNLINKED_MESSAGE,
    CommandContext,
    handle_command,
)
from app.telegram.factory import build_telegram_client
from app.telegram.formatter import (
    format_account_list,
    format_amount,
    format_transaction_notification,
)
from app.telegram.notifier import TelegramNotifier

CHAT_ID = "123456789"
RECEIVED_AT = datetime(2026, 6, 2, 10, 0, 0)
HDFC_DEBIT = (
    "Rs.70.00 debited from A/C XXXX0452 at SmartQ on 02-06-26 10:00. Ref 998877"
)


# ------------------------------------------------------------------- formatter


def test_format_amount_uses_the_currency_symbol() -> None:
    assert format_amount(Decimal("1234.50"), "INR") == "₹1,234.50"
    assert format_amount(Decimal("10.00"), "USD") == "$10.00"


def test_unknown_currency_falls_back_to_the_code() -> None:
    assert format_amount(Decimal("5.00"), "AED") == "AED 5.00"


def test_debit_notification_names_the_merchant_and_account() -> None:
    account = Account(
        user_id=None,
        account_name="Salary",
        account_type=AccountType.BANK.value,
    )
    transaction = Transaction(
        user_id=account.id,
        account_id=account.id,
        amount=Decimal("70.00"),
        direction=TransactionDirection.DEBIT.value,
        merchant_raw="SmartQ",
        transaction_timestamp=RECEIVED_AT,
    )

    text = format_transaction_notification(transaction, account)

    assert "Debited" in text
    assert "₹70.00" in text
    assert "SmartQ" in text
    assert "Salary" in text


def test_credit_notification_reads_as_credited() -> None:
    transaction = Transaction(
        user_id=None,
        account_id=None,
        amount=Decimal("85000.00"),
        direction=TransactionDirection.CREDIT.value,
    )

    assert "Credited" in format_transaction_notification(transaction, None)


def test_notification_escapes_merchant_text() -> None:
    """Merchant strings come from bank SMS and are rendered as HTML."""
    transaction = Transaction(
        user_id=None,
        account_id=None,
        amount=Decimal("10.00"),
        direction=TransactionDirection.DEBIT.value,
        merchant_raw="<script>alert(1)</script>",
    )

    text = format_transaction_notification(transaction, None)

    assert "<script>" not in text
    assert "&lt;script&gt;" in text


def test_review_prompt_is_added_when_requested() -> None:
    transaction = Transaction(
        user_id=None,
        account_id=None,
        amount=Decimal("10.00"),
        direction=TransactionDirection.DEBIT.value,
    )

    text = format_transaction_notification(transaction, None, needs_review=True)

    assert "⚠️" in text


def test_empty_account_list_explains_itself() -> None:
    assert "no accounts yet" in format_account_list([])


# -------------------------------------------------------------------- commands


def test_start_and_help_work_without_a_linked_user() -> None:
    context = CommandContext(user=None)

    assert handle_command("/start", context) == START_MESSAGE
    assert handle_command("/help", context) == HELP_MESSAGE


def test_data_commands_require_a_linked_user() -> None:
    """A chat ID is not a credential, so an unlinked chat sees no data."""
    context = CommandContext(user=None)

    assert handle_command("/accounts", context) == UNLINKED_MESSAGE
    assert handle_command("/settings", context) == UNLINKED_MESSAGE


def test_command_suffix_is_stripped() -> None:
    """Group chats address bots as /help@MyBot."""
    assert handle_command("/help@FinanceBot", CommandContext(user=None)) == (
        HELP_MESSAGE
    )


def test_unknown_command_is_reported(db_session: Session) -> None:
    user = _make_user(db_session)
    reply = handle_command("/nonsense", CommandContext(user=user))

    assert "did not recognize" in reply


def test_accounts_command_lists_balances(db_session: Session) -> None:
    user = _make_user(db_session)
    db_session.add(
        Account(
            user_id=user.id,
            account_name="Salary",
            account_type=AccountType.BANK.value,
            estimated_balance=Decimal("12345.67"),
            status=AccountStatus.ACTIVE.value,
        )
    )
    db_session.commit()

    reply = handle_command(
        "/accounts",
        CommandContext(user=user, account_repository=AccountRepository(db_session)),
    )

    assert "Salary" in reply
    assert "₹12,345.67" in reply


def test_accounts_command_hides_archived_accounts(db_session: Session) -> None:
    user = _make_user(db_session)
    db_session.add(
        Account(
            user_id=user.id,
            account_name="Old Card",
            account_type=AccountType.CREDIT_CARD.value,
            status=AccountStatus.ARCHIVED.value,
        )
    )
    db_session.commit()

    reply = handle_command(
        "/accounts",
        CommandContext(user=user, account_repository=AccountRepository(db_session)),
    )

    assert "Old Card" not in reply


# ---------------------------------------------------------------------- client


def test_fake_client_records_what_it_would_send() -> None:
    client = FakeTelegramClient()

    assert client.send_message(CHAT_ID, "hello") is True
    assert client.sent == [(CHAT_ID, "hello")]


def test_null_client_reports_non_delivery_without_raising() -> None:
    """A disabled integration must behave like an unreachable one."""
    assert NullTelegramClient().send_message(CHAT_ID, "hello") is False


def test_factory_returns_null_client_when_disabled() -> None:
    settings = get_settings()
    original = settings.enable_telegram
    settings.enable_telegram = False
    try:
        assert isinstance(build_telegram_client(settings), NullTelegramClient)
    finally:
        settings.enable_telegram = original


def test_factory_returns_null_client_when_token_is_missing() -> None:
    """A half-configured deployment degrades to silence, not to errors."""
    settings = get_settings()
    original = settings.enable_telegram
    settings.enable_telegram = True
    try:
        assert isinstance(build_telegram_client(settings), NullTelegramClient)
    finally:
        settings.enable_telegram = original


# -------------------------------------------------------------------- notifier


def _make_user(
    db_session: Session,
    chat_id: str | None = CHAT_ID,
    mode: NotificationMode = NotificationMode.ALWAYS,
) -> User:
    user = User(
        email=f"owner{chat_id or 'none'}@example.com",
        password_hash="hash",
        display_name="Owner",
        telegram_chat_id=chat_id,
    )
    db_session.add(user)
    db_session.add(UserSettings(user_id=user.id, notification_mode=mode.value))
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_transaction(
    db_session: Session,
    user: User,
    confidence: Decimal | None = Decimal("1.00"),
) -> Transaction:
    account = Account(
        user_id=user.id,
        account_name="Salary",
        account_type=AccountType.BANK.value,
        status=AccountStatus.ACTIVE.value,
    )
    db_session.add(account)
    db_session.commit()

    transaction = Transaction(
        user_id=user.id,
        account_id=account.id,
        amount=Decimal("70.00"),
        direction=TransactionDirection.DEBIT.value,
        merchant_raw="SmartQ",
        confidence_score=confidence,
    )
    db_session.add(transaction)
    db_session.commit()
    return transaction


def _event(user: User, transaction: Transaction) -> BaseEvent:
    return BaseEvent(
        event_type="TransactionCreated",
        payload={
            "entity_type": "transaction",
            "entity_id": str(transaction.id),
            "user_id": str(user.id),
        },
    )


def test_notifier_sends_on_transaction_created(db_session: Session) -> None:
    user = _make_user(db_session)
    transaction = _make_transaction(db_session, user)
    client = FakeTelegramClient()

    TelegramNotifier(client, db_session).publish(_event(user, transaction))

    assert len(client.sent) == 1
    assert client.sent[0][0] == CHAT_ID


def test_notifier_ignores_unrelated_events(db_session: Session) -> None:
    user = _make_user(db_session)
    client = FakeTelegramClient()

    TelegramNotifier(client, db_session).publish(
        BaseEvent(event_type="AccountCreated", payload={"user_id": str(user.id)})
    )

    assert client.sent == []


def test_notifier_is_silent_when_disabled(db_session: Session) -> None:
    user = _make_user(db_session)
    transaction = _make_transaction(db_session, user)
    client = FakeTelegramClient()

    TelegramNotifier(client, db_session, enabled=False).publish(
        _event(user, transaction)
    )

    assert client.sent == []


def test_notifier_skips_a_user_without_a_chat_id(db_session: Session) -> None:
    user = _make_user(db_session, chat_id=None)
    transaction = _make_transaction(db_session, user)
    client = FakeTelegramClient()

    TelegramNotifier(client, db_session).publish(_event(user, transaction))

    assert client.sent == []


def test_disabled_notification_mode_is_respected(db_session: Session) -> None:
    user = _make_user(db_session, mode=NotificationMode.DISABLED)
    transaction = _make_transaction(db_session, user)
    client = FakeTelegramClient()

    TelegramNotifier(client, db_session).publish(_event(user, transaction))

    assert client.sent == []


def test_low_confidence_only_skips_a_confident_transaction(
    db_session: Session,
) -> None:
    user = _make_user(db_session, mode=NotificationMode.LOW_CONFIDENCE_ONLY)
    transaction = _make_transaction(db_session, user, confidence=Decimal("1.00"))
    client = FakeTelegramClient()

    TelegramNotifier(client, db_session).publish(_event(user, transaction))

    assert client.sent == []


def test_low_confidence_only_sends_an_uncertain_transaction(
    db_session: Session,
) -> None:
    user = _make_user(db_session, mode=NotificationMode.LOW_CONFIDENCE_ONLY)
    transaction = _make_transaction(db_session, user, confidence=Decimal("0.50"))
    client = FakeTelegramClient()

    TelegramNotifier(client, db_session).publish(_event(user, transaction))

    assert len(client.sent) == 1


def test_a_telegram_outage_never_propagates(db_session: Session) -> None:
    """09-error_handling_standards.md section 13: Telegram down means continue."""
    user = _make_user(db_session)
    transaction = _make_transaction(db_session, user)
    client = FakeTelegramClient(should_fail=True)

    TelegramNotifier(client, db_session).publish(_event(user, transaction))


# ------------------------------------------------------------------- buffering


def test_buffered_publisher_holds_events_until_flush() -> None:
    sink = RecordingEventPublisher()
    buffered = BufferedEventPublisher(sink)

    buffered.publish(BaseEvent(event_type="TransactionCreated"))

    assert sink.events == []
    assert buffered.pending_count == 1

    buffered.flush()
    assert len(sink.events) == 1


def test_discarded_events_are_never_delivered() -> None:
    sink = RecordingEventPublisher()
    buffered = BufferedEventPublisher(sink)
    buffered.publish(BaseEvent(event_type="TransactionCreated"))

    buffered.discard()
    buffered.flush()

    assert sink.events == []


def test_composite_publisher_isolates_a_failing_publisher() -> None:
    """A notification problem must never cost an audit row."""

    class Exploding:
        def publish(self, event: BaseEvent) -> None:
            raise RuntimeError("boom")

    good = RecordingEventPublisher()
    CompositeEventPublisher(Exploding(), good).publish(
        BaseEvent(event_type="TransactionCreated")
    )

    assert len(good.events) == 1


def test_pipeline_notifies_only_after_the_transaction_commits(
    db_session: Session,
) -> None:
    """Sending before commit could announce a transaction that then rolled back."""
    user = _make_user(db_session)
    db_session.add(
        Account(
            user_id=user.id,
            account_type=AccountType.BANK.value,
            bank_name="HDFC",
            last_four_digits="0452",
            status=AccountStatus.ACTIVE.value,
        )
    )
    db_session.commit()

    client = FakeTelegramClient()
    notifier = BufferedEventPublisher(TelegramNotifier(client, db_session))
    pipeline = SmsPipeline(
        raw_event_repository=RawEventRepository(db_session),
        account_repository=AccountRepository(db_session),
        transaction_service=TransactionService(
            repository=TransactionRepository(db_session),
            account_repository=AccountRepository(db_session),
            event_publisher=notifier,
        ),
        merchant_service=MerchantService(repository=MerchantRepository(db_session)),
        category_repository=CategoryRepository(db_session),
        deferred_publisher=notifier,
    )
    ingestion = IngestionService(
        repository=RawEventRepository(db_session),
        processor=pipeline,
    )

    ingestion.ingest_sms(
        IngestSmsCommand(
            user_id=user.id,
            message_text=HDFC_DEBIT,
            received_at=RECEIVED_AT,
            sender="VK-HDFCBK",
        )
    )

    assert len(client.sent) == 1
    assert notifier.pending_count == 0
    assert len(list(db_session.exec(select(Transaction)).all())) == 1


def test_duplicate_transaction_sends_no_notification(db_session: Session) -> None:
    """A replay must not re-notify the user about money they already saw."""
    user = _make_user(db_session)
    db_session.add(
        Account(
            user_id=user.id,
            account_type=AccountType.BANK.value,
            bank_name="HDFC",
            last_four_digits="0452",
            status=AccountStatus.ACTIVE.value,
        )
    )
    db_session.commit()

    client = FakeTelegramClient()

    def build_pipeline():
        notifier = BufferedEventPublisher(TelegramNotifier(client, db_session))
        return (
            SmsPipeline(
                raw_event_repository=RawEventRepository(db_session),
                account_repository=AccountRepository(db_session),
                transaction_service=TransactionService(
                    repository=TransactionRepository(db_session),
                    account_repository=AccountRepository(db_session),
                    event_publisher=notifier,
                ),
                merchant_service=MerchantService(
                    repository=MerchantRepository(db_session)
                ),
                category_repository=CategoryRepository(db_session),
                deferred_publisher=notifier,
            ),
            notifier,
        )

    for received_at in (RECEIVED_AT, RECEIVED_AT.replace(second=30)):
        pipeline, _ = build_pipeline()
        IngestionService(
            repository=RawEventRepository(db_session),
            processor=pipeline,
        ).ingest_sms(
            IngestSmsCommand(
                user_id=user.id,
                message_text=HDFC_DEBIT,
                received_at=received_at,
                sender="VK-HDFCBK",
            )
        )

    assert len(client.sent) == 1


# -------------------------------------------------------------------- webhook


def _webhook_payload(text: str = "/help") -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "chat": {"id": int(CHAT_ID)},
            "text": text,
        },
    }


@pytest.fixture
def webhook_secret(override_session: None):
    settings = get_settings()
    from pydantic import SecretStr

    original = settings.telegram_webhook_secret
    settings.telegram_webhook_secret = SecretStr("test-webhook-secret")
    try:
        yield "test-webhook-secret"
    finally:
        settings.telegram_webhook_secret = original


@pytest.mark.asyncio
async def test_webhook_rejects_a_missing_secret(
    auth_client: AsyncClient,
    webhook_secret: str,
) -> None:
    response = await auth_client.post(
        "/api/v1/telegram/webhook",
        json=_webhook_payload(),
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_rejects_a_wrong_secret(
    auth_client: AsyncClient,
    webhook_secret: str,
) -> None:
    response = await auth_client.post(
        "/api/v1/telegram/webhook",
        json=_webhook_payload(),
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_accepts_a_valid_secret(
    auth_client: AsyncClient,
    webhook_secret: str,
) -> None:
    response = await auth_client.post(
        "/api/v1/telegram/webhook",
        json=_webhook_payload(),
        headers={"X-Telegram-Bot-Api-Secret-Token": webhook_secret},
    )

    assert response.status_code == 200
    assert response.json()["data"]["handled"] is True


@pytest.mark.asyncio
async def test_webhook_refuses_when_no_secret_is_configured(
    auth_client: AsyncClient,
) -> None:
    """A misconfiguration must not silently open the webhook."""
    response = await auth_client.post(
        "/api/v1/telegram/webhook",
        json=_webhook_payload(),
        headers={"X-Telegram-Bot-Api-Secret-Token": "anything"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_does_not_require_a_jwt(
    auth_client: AsyncClient,
    webhook_secret: str,
) -> None:
    """The middleware must not reject before the secret token is checked."""
    response = await auth_client.post(
        "/api/v1/telegram/webhook",
        json=_webhook_payload(),
        headers={"X-Telegram-Bot-Api-Secret-Token": webhook_secret},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_malformed_update_still_returns_success(
    auth_client: AsyncClient,
    webhook_secret: str,
) -> None:
    """A non-2xx makes Telegram retry the same update indefinitely."""
    response = await auth_client.post(
        "/api/v1/telegram/webhook",
        json={"update_id": 2},
        headers={"X-Telegram-Bot-Api-Secret-Token": webhook_secret},
    )

    assert response.status_code == 200
    assert response.json()["data"]["handled"] is False
