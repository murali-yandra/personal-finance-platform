"""SMS ingestion (Sprint 4)."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.config import get_settings
from app.domains.ingestion.exceptions import InvalidSmsPayloadError
from app.domains.ingestion.hashing import build_message_hash
from app.domains.ingestion.models import RawEvent
from app.domains.ingestion.repository import RawEventRepository
from app.domains.ingestion.schemas import IngestSmsCommand
from app.domains.ingestion.service import IngestionService
from app.domains.users.models import User, UserSettings
from app.shared.enums import ProcessingStatus
from tests.conftest import register_user

INGEST_URL = "/api/v1/ingest/sms"
SAMPLE_TEXT = "Rs.70 debited from A/C XXXX0452 at SmartQ"
RECEIVED_AT = datetime(2026, 6, 2, 10, 0, 0)


# ---------------------------------------------------------------- message hash


def test_identical_payloads_hash_the_same() -> None:
    first = build_message_hash("VK-HDFCBK", SAMPLE_TEXT, RECEIVED_AT.isoformat())
    second = build_message_hash("VK-HDFCBK", SAMPLE_TEXT, RECEIVED_AT.isoformat())

    assert first == second


def test_sender_case_does_not_change_the_hash() -> None:
    upper = build_message_hash("VK-HDFCBK", SAMPLE_TEXT, RECEIVED_AT.isoformat())
    lower = build_message_hash("vk-hdfcbk", SAMPLE_TEXT, RECEIVED_AT.isoformat())

    assert upper == lower


def test_different_receipt_time_changes_the_hash() -> None:
    """Two identically worded purchases at different times are different events."""
    first = build_message_hash("VK-HDFCBK", SAMPLE_TEXT, RECEIVED_AT.isoformat())
    later = build_message_hash(
        "VK-HDFCBK",
        SAMPLE_TEXT,
        RECEIVED_AT.replace(hour=18).isoformat(),
    )

    assert first != later


def test_different_text_changes_the_hash() -> None:
    first = build_message_hash("VK-HDFCBK", SAMPLE_TEXT, RECEIVED_AT.isoformat())
    other = build_message_hash("VK-HDFCBK", "Rs.80 debited", RECEIVED_AT.isoformat())

    assert first != other


# ------------------------------------------------------------------- service


@pytest.fixture
def user(db_session: Session) -> User:
    created = User(
        email="owner@example.com",
        password_hash="hash",
        display_name="Owner",
    )
    db_session.add(created)
    db_session.add(UserSettings(user_id=created.id))
    db_session.commit()
    return created


@pytest.fixture
def service(db_session: Session) -> IngestionService:
    return IngestionService(repository=RawEventRepository(db_session))


def _command(user: User, **overrides) -> IngestSmsCommand:
    fields = {
        "user_id": user.id,
        "message_text": SAMPLE_TEXT,
        "received_at": RECEIVED_AT,
        "sender": "VK-HDFCBK",
    }
    fields.update(overrides)
    return IngestSmsCommand(**fields)


def test_ingest_stores_the_raw_event(
    service: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    result = service.ingest_sms(_command(user))

    assert result.status is ProcessingStatus.RECEIVED
    assert result.is_duplicate is False

    stored = db_session.get(RawEvent, result.raw_event_id)
    assert stored is not None
    assert stored.message_text == SAMPLE_TEXT
    assert stored.source_type == "SMS"
    assert stored.processing_status == ProcessingStatus.RECEIVED


def test_replayed_message_is_reported_as_duplicate(
    service: IngestionService,
    user: User,
) -> None:
    first = service.ingest_sms(_command(user))

    second = service.ingest_sms(_command(user))

    assert second.is_duplicate is True
    assert second.status is ProcessingStatus.DUPLICATE
    assert second.raw_event_id == first.raw_event_id


def test_duplicate_does_not_store_a_second_row(
    service: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    service.ingest_sms(_command(user))
    service.ingest_sms(_command(user))

    assert len(list(db_session.exec(select(RawEvent)).all())) == 1


def test_same_text_at_a_different_time_is_stored(
    service: IngestionService,
    user: User,
) -> None:
    service.ingest_sms(_command(user))

    later = service.ingest_sms(_command(user, received_at=RECEIVED_AT.replace(hour=18)))

    assert later.is_duplicate is False


def test_empty_message_is_rejected(
    service: IngestionService,
    user: User,
) -> None:
    with pytest.raises(InvalidSmsPayloadError):
        service.ingest_sms(_command(user, message_text="   "))


def test_oversized_message_is_rejected(
    service: IngestionService,
    user: User,
) -> None:
    with pytest.raises(InvalidSmsPayloadError):
        service.ingest_sms(_command(user, message_text="x" * 4001))


def test_aware_timestamps_are_stored_as_naive_utc(
    service: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    result = service.ingest_sms(
        _command(user, received_at=datetime(2026, 6, 2, 10, 0, tzinfo=UTC))
    )

    stored = db_session.get(RawEvent, result.raw_event_id)
    assert stored.received_at.tzinfo is None
    assert stored.received_at == datetime(2026, 6, 2, 10, 0)


def test_raw_event_repository_exposes_no_delete_method() -> None:
    """Raw events are retained permanently (04-database_schema.md section 9)."""
    names = {name for name in dir(RawEventRepository) if not name.startswith("_")}

    assert not {"delete", "remove", "purge"} & names


def test_processing_failure_does_not_lose_the_stored_message(
    db_session: Session,
    user: User,
) -> None:
    """The raw event is committed before parsing, so a parser crash cannot lose it."""

    class ExplodingProcessor:
        def process(self, raw_event: RawEvent):
            raise RuntimeError("parser exploded")

    service = IngestionService(
        repository=RawEventRepository(db_session),
        processor=ExplodingProcessor(),
    )

    result = service.ingest_sms(_command(user))

    assert result.status is ProcessingStatus.FAILED
    assert db_session.get(RawEvent, result.raw_event_id) is not None


# ------------------------------------------------------------------- endpoint


@pytest.fixture
def configured_ingest_user(override_session: None):
    """Point INGEST_USER_EMAIL at a registered user for the request's lifetime."""
    settings = get_settings()
    original = settings.ingest_user_email
    settings.ingest_user_email = "owner@example.com"
    try:
        yield
    finally:
        settings.ingest_user_email = original


def _api_key_header() -> dict[str, str]:
    """Read the configured key, so the test does not depend on ambient env."""
    return {"X-API-KEY": get_settings().ingest_api_key.get_secret_value()}


def _payload(**overrides) -> dict:
    payload = {
        "sender": "VK-HDFCBK",
        "message_text": SAMPLE_TEXT,
        "received_at": "2026-06-02T10:00:00",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_ingest_endpoint_accepts_a_valid_api_key(
    auth_client: AsyncClient,
    configured_ingest_user: None,
) -> None:
    await register_user(auth_client, email="owner@example.com")

    response = await auth_client.post(
        INGEST_URL,
        json=_payload(),
        headers=_api_key_header(),
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["status"] == "RECEIVED"
    UUID(data["raw_event_id"])


@pytest.mark.asyncio
async def test_ingest_endpoint_rejects_a_missing_api_key(
    auth_client: AsyncClient,
    configured_ingest_user: None,
) -> None:
    await register_user(auth_client, email="owner@example.com")

    response = await auth_client.post(INGEST_URL, json=_payload())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_ingest_endpoint_rejects_a_wrong_api_key(
    auth_client: AsyncClient,
    configured_ingest_user: None,
) -> None:
    await register_user(auth_client, email="owner@example.com")

    response = await auth_client.post(
        INGEST_URL,
        json=_payload(),
        headers={"X-API-KEY": "not-the-key"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ingest_endpoint_does_not_require_a_jwt(
    auth_client: AsyncClient,
    configured_ingest_user: None,
) -> None:
    """The bearer-token middleware must not reject before the key is checked."""
    await register_user(auth_client, email="owner@example.com")

    response = await auth_client.post(
        INGEST_URL,
        json=_payload(),
        headers=_api_key_header(),
    )

    assert response.status_code != 401


@pytest.mark.asyncio
async def test_replay_returns_duplicate_rather_than_an_error(
    auth_client: AsyncClient,
    configured_ingest_user: None,
) -> None:
    """A retrying sender must not treat a replay as a failure and keep retrying."""
    await register_user(auth_client, email="owner@example.com")
    headers = _api_key_header()
    first = await auth_client.post(INGEST_URL, json=_payload(), headers=headers)

    second = await auth_client.post(INGEST_URL, json=_payload(), headers=headers)

    assert second.status_code == 201
    assert second.json()["data"]["status"] == "DUPLICATE"
    assert second.json()["data"]["raw_event_id"] == first.json()["data"]["raw_event_id"]


@pytest.mark.asyncio
async def test_ingest_is_unavailable_when_no_owner_is_configured(
    auth_client: AsyncClient,
) -> None:
    settings = get_settings()
    original = settings.ingest_user_email
    settings.ingest_user_email = ""
    try:
        response = await auth_client.post(
            INGEST_URL,
            json=_payload(),
            headers=_api_key_header(),
        )
    finally:
        settings.ingest_user_email = original

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_ingest_rejects_an_empty_message(
    auth_client: AsyncClient,
    configured_ingest_user: None,
) -> None:
    await register_user(auth_client, email="owner@example.com")

    response = await auth_client.post(
        INGEST_URL,
        json=_payload(message_text=""),
        headers=_api_key_header(),
    )

    assert response.status_code == 400
