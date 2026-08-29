"""Historical import and reprocessing (Sprint 11)."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.config import get_settings
from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.categories.repository import CategoryRepository
from app.domains.ingestion.models import RawEvent
from app.domains.ingestion.pipeline import SmsPipeline
from app.domains.ingestion.repository import RawEventRepository
from app.domains.ingestion.schemas import IngestSmsBatchCommand, IngestSmsCommand
from app.domains.ingestion.service import (
    HistoricalImportService,
    IngestionService,
)
from app.domains.merchants.repository import MerchantRepository
from app.domains.merchants.service import MerchantService
from app.domains.transactions.models import Transaction
from app.domains.transactions.repository import TransactionRepository
from app.domains.transactions.service import TransactionService
from app.domains.users.models import User, UserSettings
from app.shared.enums import AccountStatus, AccountType
from tests.conftest import register_user

BASE_TIME = datetime(2026, 6, 2, 10, 0, 0)


def _message(index: int, amount: int = 70) -> str:
    return (
        f"Rs.{amount}.00 debited from A/C XXXX0452 at Shop{index} "
        f"on 02-06-26 10:00. Ref REF{index}"
    )


@pytest.fixture
def user(db_session: Session) -> User:
    created = User(
        email="owner@example.com",
        password_hash="hash",
        display_name="Owner",
    )
    db_session.add(created)
    db_session.add(UserSettings(user_id=created.id))
    db_session.add(
        Account(
            user_id=created.id,
            account_type=AccountType.BANK.value,
            bank_name="HDFC",
            last_four_digits="0452",
            status=AccountStatus.ACTIVE.value,
        )
    )
    db_session.commit()
    return created


def _build_ingestion(db_session: Session, with_pipeline: bool = True):
    pipeline = None
    if with_pipeline:
        pipeline = SmsPipeline(
            raw_event_repository=RawEventRepository(db_session),
            account_repository=AccountRepository(db_session),
            transaction_service=TransactionService(
                repository=TransactionRepository(db_session),
                account_repository=AccountRepository(db_session),
            ),
            merchant_service=MerchantService(repository=MerchantRepository(db_session)),
            category_repository=CategoryRepository(db_session),
        )
    return IngestionService(
        repository=RawEventRepository(db_session),
        processor=pipeline,
    )


@pytest.fixture
def import_service(db_session: Session) -> HistoricalImportService:
    return HistoricalImportService(
        repository=RawEventRepository(db_session),
        ingestion_service=_build_ingestion(db_session),
    )


def _batch(user: User, count: int) -> IngestSmsBatchCommand:
    return IngestSmsBatchCommand(
        user_id=user.id,
        messages=tuple(
            IngestSmsCommand(
                user_id=user.id,
                message_text=_message(index),
                received_at=BASE_TIME.replace(minute=index % 60),
                sender="VK-HDFCBK",
            )
            for index in range(count)
        ),
    )


def test_batch_import_creates_a_transaction_per_message(
    import_service: HistoricalImportService,
    user: User,
    db_session: Session,
) -> None:
    result = import_service.import_batch(_batch(user, 5))

    assert result.accepted == 5
    assert result.total == 5
    assert len(list(db_session.exec(select(Transaction)).all())) == 5


def test_batch_import_counts_duplicates_separately(
    import_service: HistoricalImportService,
    user: User,
    db_session: Session,
) -> None:
    """Re-importing an overlapping window must not double-count."""
    import_service.import_batch(_batch(user, 3))

    result = import_service.import_batch(_batch(user, 3))

    assert result.accepted == 0
    assert result.duplicates == 3
    assert len(list(db_session.exec(select(Transaction)).all())) == 3


def test_one_unreadable_message_does_not_abort_the_import(
    import_service: HistoricalImportService,
    user: User,
    db_session: Session,
) -> None:
    """A year of history must not be discarded over a single bad message."""
    messages = (
        IngestSmsCommand(
            user_id=user.id,
            message_text=_message(1),
            received_at=BASE_TIME,
            sender="VK-HDFCBK",
        ),
        IngestSmsCommand(
            user_id=user.id,
            message_text="Transaction of INR 500.00 processed.",
            received_at=BASE_TIME.replace(minute=5),
            sender="VK-HDFCBK",
        ),
        IngestSmsCommand(
            user_id=user.id,
            message_text=_message(3),
            received_at=BASE_TIME.replace(minute=10),
            sender="VK-HDFCBK",
        ),
    )

    result = import_service.import_batch(
        IngestSmsBatchCommand(user_id=user.id, messages=messages)
    )

    assert result.accepted == 2
    assert result.failed == 1
    assert result.total == 3


def test_non_transactional_messages_are_counted_as_ignored(
    import_service: HistoricalImportService,
    user: User,
) -> None:
    result = import_service.import_batch(
        IngestSmsBatchCommand(
            user_id=user.id,
            messages=(
                IngestSmsCommand(
                    user_id=user.id,
                    message_text="123456 is your OTP. Do not share it.",
                    received_at=BASE_TIME,
                    sender="VK-HDFCBK",
                ),
            ),
        )
    )

    assert result.ignored == 1
    assert result.failed == 0


def test_oversized_batch_is_rejected(
    import_service: HistoricalImportService,
    user: User,
) -> None:
    from app.domains.ingestion.exceptions import InvalidSmsPayloadError

    with pytest.raises(InvalidSmsPayloadError):
        import_service.import_batch(_batch(user, 1001))


def test_every_message_is_stored_even_when_unreadable(
    import_service: HistoricalImportService,
    user: User,
    db_session: Session,
) -> None:
    """Raw events are the source of truth and are retained regardless."""
    import_service.import_batch(
        IngestSmsBatchCommand(
            user_id=user.id,
            messages=(
                IngestSmsCommand(
                    user_id=user.id,
                    message_text="Unreadable rubbish",
                    received_at=BASE_TIME,
                    sender="VK-HDFCBK",
                ),
            ),
        )
    )

    assert len(list(db_session.exec(select(RawEvent)).all())) == 1


# ---------------------------------------------------------------- reprocessing


def test_reprocessing_turns_a_stored_message_into_a_transaction(
    user: User,
    db_session: Session,
) -> None:
    """This is how a parser improvement is applied to history."""
    storage_only = HistoricalImportService(
        repository=RawEventRepository(db_session),
        ingestion_service=_build_ingestion(db_session, with_pipeline=False),
    )
    storage_only.import_batch(_batch(user, 2))
    assert list(db_session.exec(select(Transaction)).all()) == []

    with_parser = HistoricalImportService(
        repository=RawEventRepository(db_session),
        ingestion_service=_build_ingestion(db_session),
    )
    result = with_parser.reprocess(user_id=user.id)

    assert result.reprocessed == 2
    assert result.succeeded == 2
    assert len(list(db_session.exec(select(Transaction)).all())) == 2


def test_reprocessing_skips_messages_that_already_produced_a_transaction(
    import_service: HistoricalImportService,
    user: User,
    db_session: Session,
) -> None:
    import_service.import_batch(_batch(user, 2))

    result = import_service.reprocess(user_id=user.id)

    assert result.reprocessed == 0
    assert len(list(db_session.exec(select(Transaction)).all())) == 2


def test_reprocessing_leaves_ignored_messages_alone(
    import_service: HistoricalImportService,
    user: User,
    db_session: Session,
) -> None:
    """An OTP is not a parser gap, so re-running it achieves nothing."""
    import_service.import_batch(
        IngestSmsBatchCommand(
            user_id=user.id,
            messages=(
                IngestSmsCommand(
                    user_id=user.id,
                    message_text="123456 is your OTP. Do not share it.",
                    received_at=BASE_TIME,
                    sender="VK-HDFCBK",
                ),
            ),
        )
    )

    assert import_service.reprocess(user_id=user.id).reprocessed == 0


def test_reprocessing_respects_a_date_window(
    user: User,
    db_session: Session,
) -> None:
    storage_only = HistoricalImportService(
        repository=RawEventRepository(db_session),
        ingestion_service=_build_ingestion(db_session, with_pipeline=False),
    )
    storage_only.import_batch(
        IngestSmsBatchCommand(
            user_id=user.id,
            messages=(
                IngestSmsCommand(
                    user_id=user.id,
                    message_text=_message(1),
                    received_at=datetime(2026, 6, 2, 10, 0),
                    sender="VK-HDFCBK",
                ),
                IngestSmsCommand(
                    user_id=user.id,
                    message_text=_message(2),
                    received_at=datetime(2026, 7, 2, 10, 0),
                    sender="VK-HDFCBK",
                ),
            ),
        )
    )

    with_parser = HistoricalImportService(
        repository=RawEventRepository(db_session),
        ingestion_service=_build_ingestion(db_session),
    )
    result = with_parser.reprocess(
        user_id=user.id,
        start_date=datetime(2026, 7, 1),
        end_date=datetime(2026, 7, 31),
    )

    assert result.reprocessed == 1


# -------------------------------------------------------------------- endpoints


@pytest.fixture
def ingest_owner(override_session: None):
    settings = get_settings()
    original = settings.ingest_user_email
    settings.ingest_user_email = "owner@example.com"
    try:
        yield {"X-API-KEY": settings.ingest_api_key.get_secret_value()}
    finally:
        settings.ingest_user_email = original


@pytest.mark.asyncio
async def test_batch_endpoint_returns_counts(
    auth_client: AsyncClient,
    ingest_owner: dict[str, str],
) -> None:
    await register_user(auth_client, email="owner@example.com")

    response = await auth_client.post(
        "/api/v1/ingest/sms/batch",
        json={
            "messages": [
                {
                    "sender": "VK-HDFCBK",
                    "message_text": _message(index),
                    "received_at": f"2026-06-02T10:{index:02d}:00",
                }
                for index in range(3)
            ]
        },
        headers=ingest_owner,
    )

    assert response.status_code == 202, response.text
    data = response.json()["data"]
    assert data["total"] == 3
    assert data["accepted"] == 3


@pytest.mark.asyncio
async def test_batch_endpoint_requires_the_api_key(
    auth_client: AsyncClient,
    ingest_owner: dict[str, str],
) -> None:
    await register_user(auth_client, email="owner@example.com")

    response = await auth_client.post(
        "/api/v1/ingest/sms/batch",
        json={
            "messages": [{"message_text": "x", "received_at": "2026-06-02T10:00:00"}]
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_batch_endpoint_rejects_an_empty_batch(
    auth_client: AsyncClient,
    ingest_owner: dict[str, str],
) -> None:
    await register_user(auth_client, email="owner@example.com")

    response = await auth_client.post(
        "/api/v1/ingest/sms/batch",
        json={"messages": []},
        headers=ingest_owner,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reprocess_endpoint_reports_counts(
    auth_client: AsyncClient,
    ingest_owner: dict[str, str],
) -> None:
    await register_user(auth_client, email="owner@example.com")

    response = await auth_client.post(
        "/api/v1/ingest/reprocess",
        json={},
        headers=ingest_owner,
    )

    assert response.status_code == 200
    assert response.json()["data"]["reprocessed"] == 0


@pytest.mark.asyncio
async def test_reimporting_the_same_window_does_not_double_count(
    auth_client: AsyncClient,
    ingest_owner: dict[str, str],
) -> None:
    """Users commonly re-import an overlapping range."""
    await register_user(auth_client, email="owner@example.com")
    payload = {
        "messages": [
            {
                "sender": "VK-HDFCBK",
                "message_text": _message(index),
                "received_at": f"2026-06-02T10:{index:02d}:00",
            }
            for index in range(3)
        ]
    }

    await auth_client.post(
        "/api/v1/ingest/sms/batch",
        json=payload,
        headers=ingest_owner,
    )
    second = await auth_client.post(
        "/api/v1/ingest/sms/batch",
        json=payload,
        headers=ingest_owner,
    )

    assert second.json()["data"]["duplicates"] == 3
    assert second.json()["data"]["accepted"] == 0
