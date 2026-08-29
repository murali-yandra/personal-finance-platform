"""API contract for the read-only ingested-message queue."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.config import get_settings
from tests.conftest import authorization_header, register_user

RAW_EVENTS_URL = "/api/v1/raw-events"
INGEST_URL = "/api/v1/ingest/sms"

PARSEABLE_TEXT = (
    "Rs.70.00 debited from A/C XXXX0452 at SmartQ on 02-06-26 10:00. "
    "Avl Bal Rs.12,345.67. Ref 998877"
)
UNPARSEABLE_TEXT = "Your account was involved in something we cannot describe."
OTP_TEXT = "123456 is your one time password. Do not share it with anyone."


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
    return {"X-API-KEY": get_settings().ingest_api_key.get_secret_value()}


async def _ingest(client: AsyncClient, text: str, received_at: str) -> dict:
    response = await client.post(
        INGEST_URL,
        json={
            "sender": "VK-HDFCBK",
            "message_text": text,
            "received_at": received_at,
        },
        headers=_api_key_header(),
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.mark.asyncio
async def test_listing_returns_ingested_messages(
    auth_client: AsyncClient,
    configured_ingest_user: None,
) -> None:
    user_id = await register_user(auth_client, email="owner@example.com")
    headers = authorization_header(user_id, email="owner@example.com")
    await _ingest(auth_client, PARSEABLE_TEXT, "2026-06-02T10:00:00")

    response = await auth_client.get(RAW_EVENTS_URL, headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["meta"]["total_records"] == 1
    assert body["data"][0]["sender"] == "VK-HDFCBK"
    assert body["data"][0]["processing_status"] == "NEEDS_REVIEW"


@pytest.mark.asyncio
async def test_status_filter_isolates_the_unparsed_queue(
    auth_client: AsyncClient,
    configured_ingest_user: None,
) -> None:
    """The whole point of the endpoint: find what failed to parse."""
    user_id = await register_user(auth_client, email="owner@example.com")
    headers = authorization_header(user_id, email="owner@example.com")
    await _ingest(auth_client, PARSEABLE_TEXT, "2026-06-02T10:00:00")
    await _ingest(auth_client, UNPARSEABLE_TEXT, "2026-06-02T11:00:00")

    response = await auth_client.get(
        RAW_EVENTS_URL,
        params={"processing_status": "UNKNOWN_FORMAT"},
        headers=headers,
    )

    body = response.json()
    assert body["meta"]["total_records"] == 1
    assert body["data"][0]["message_preview"] == UNPARSEABLE_TEXT
    assert body["data"][0]["processing_error"]


@pytest.mark.asyncio
async def test_ignored_messages_are_separate_from_failures(
    auth_client: AsyncClient,
    configured_ingest_user: None,
) -> None:
    """An OTP is IGNORED, not UNKNOWN_FORMAT — it is not a parser gap."""
    user_id = await register_user(auth_client, email="owner@example.com")
    headers = authorization_header(user_id, email="owner@example.com")
    await _ingest(auth_client, OTP_TEXT, "2026-06-02T12:00:00")

    failures = await auth_client.get(
        RAW_EVENTS_URL,
        params={"processing_status": "UNKNOWN_FORMAT"},
        headers=headers,
    )
    ignored = await auth_client.get(
        RAW_EVENTS_URL,
        params={"processing_status": "IGNORED"},
        headers=headers,
    )

    assert failures.json()["meta"]["total_records"] == 0
    assert ignored.json()["meta"]["total_records"] == 1


@pytest.mark.asyncio
async def test_an_invalid_status_is_rejected(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user

    response = await auth_client.get(
        RAW_EVENTS_URL,
        params={"processing_status": "NOT_A_STATUS"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_listing_never_returns_another_users_messages(
    auth_client: AsyncClient,
    configured_ingest_user: None,
) -> None:
    await register_user(auth_client, email="owner@example.com")
    await _ingest(auth_client, PARSEABLE_TEXT, "2026-06-02T10:00:00")

    intruder_id = await register_user(auth_client, email="intruder@example.com")
    intruder_headers = authorization_header(intruder_id, email="intruder@example.com")

    response = await auth_client.get(RAW_EVENTS_URL, headers=intruder_headers)

    assert response.json()["meta"]["total_records"] == 0


@pytest.mark.asyncio
async def test_detail_returns_the_full_message_text(
    auth_client: AsyncClient,
    configured_ingest_user: None,
) -> None:
    user_id = await register_user(auth_client, email="owner@example.com")
    headers = authorization_header(user_id, email="owner@example.com")
    data = await _ingest(auth_client, PARSEABLE_TEXT, "2026-06-02T10:00:00")

    response = await auth_client.get(
        f"{RAW_EVENTS_URL}/{data['raw_event_id']}",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["message_text"] == PARSEABLE_TEXT


@pytest.mark.asyncio
async def test_detail_hides_another_users_message_as_not_found(
    auth_client: AsyncClient,
    configured_ingest_user: None,
) -> None:
    """404 rather than 403, so message IDs cannot be probed."""
    await register_user(auth_client, email="owner@example.com")
    data = await _ingest(auth_client, PARSEABLE_TEXT, "2026-06-02T10:00:00")

    intruder_id = await register_user(auth_client, email="intruder@example.com")
    intruder_headers = authorization_header(intruder_id, email="intruder@example.com")

    response = await auth_client.get(
        f"{RAW_EVENTS_URL}/{data['raw_event_id']}",
        headers=intruder_headers,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_a_missing_message_is_not_found(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user

    response = await auth_client.get(f"{RAW_EVENTS_URL}/{uuid4()}", headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_the_queue_requires_authentication(auth_client: AsyncClient) -> None:
    response = await auth_client.get(RAW_EVENTS_URL)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_the_queue_is_read_only(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    """Raw events are immutable, so there must be no write route."""
    _, headers = authenticated_user

    for method in (auth_client.post, auth_client.patch, auth_client.delete):
        response = await method(RAW_EVENTS_URL, headers=headers)
        assert response.status_code == 405
