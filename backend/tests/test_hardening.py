"""Production hardening and SaaS preparation (Sprints 14 and 15)."""

import json
import logging
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.middleware.request_context import RequestContextMiddleware
from app.core.context import (
    clear_request_context,
    current_context,
    set_current_user_id,
    set_request_context,
)
from app.core.logging import JsonFormatter
from app.core.masking import mask_account_number, mask_text
from app.core.rate_limit import RateLimiter
from app.core.security import SecurityService
from app.domains.access.api_keys import ApiKeyService
from app.domains.users.models import User, UserSettings
from app.shared.enums import UserRole
from tests.conftest import authorization_header, register_user

VALID_UUID = "55555555-5555-4555-8555-555555555555"


# ---------------------------------------------------------------------- masking


@pytest.mark.parametrize(
    "text",
    [
        "password=hunter2",
        'password: "hunter2"',
        "secret=abc123",
        "api_key=pfp_abcdef",
        "X-API-KEY: pfp_abcdef",
        "refresh_token=abc.def.ghi",
    ],
)
def test_sensitive_keys_are_redacted(text: str) -> None:
    """10-security_standards.md section 11: these must never reach a log."""
    masked = mask_text(text)

    assert "hunter2" not in masked
    assert "abc123" not in masked
    assert "pfp_abcdef" not in masked
    assert "REDACTED" in masked


def test_bearer_tokens_are_redacted() -> None:
    masked = mask_text("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig")

    assert "eyJhbGciOiJIUzI1NiJ9" not in masked


def test_jwts_are_redacted_anywhere_in_a_message() -> None:
    masked = mask_text("token was eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc123def")

    assert "eyJhbGciOiJIUzI1NiJ9" not in masked


def test_full_account_numbers_are_masked() -> None:
    masked = mask_text("Account: 1234567890123456")

    assert "1234567890123456" not in masked
    assert masked.endswith("3456")


def test_account_masking_keeps_the_last_four() -> None:
    """The security standard's example: 1234567890 becomes ******7890."""
    assert mask_account_number("1234567890") == "******7890"


def test_short_values_are_left_alone() -> None:
    assert mask_account_number("7890") == "7890"


def test_ordinary_text_is_untouched() -> None:
    text = "Created pending account from parsed message"

    assert mask_text(text) == text


# ---------------------------------------------------------------------- logging


def _format(record: logging.LogRecord) -> dict:
    return json.loads(JsonFormatter().format(record))


def _record(message: str, **extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_log_lines_carry_the_required_fields() -> None:
    """Section 11 requires timestamp, request id, correlation id, user id, module."""
    set_request_context(VALID_UUID, VALID_UUID, user_id="user-1")
    try:
        payload = _format(_record("something happened"))
    finally:
        clear_request_context()

    assert payload["timestamp"]
    assert payload["request_id"] == VALID_UUID
    assert payload["correlation_id"] == VALID_UUID
    assert payload["user_id"] == "user-1"
    assert payload["module"]
    assert payload["level"] == "INFO"


def test_log_messages_are_masked() -> None:
    payload = _format(_record("login with password=hunter2"))

    assert "hunter2" not in payload["message"]


def test_extra_fields_are_included_and_masked() -> None:
    payload = _format(_record("event", event_type="LOGIN", token="abc.def.ghi"))

    assert payload["event_type"] == "LOGIN"
    assert "abc.def.ghi" not in json.dumps(payload)


def test_context_is_omitted_when_unbound() -> None:
    clear_request_context()

    payload = _format(_record("no context"))

    assert "request_id" not in payload


def test_setting_the_user_id_updates_the_context() -> None:
    set_request_context(VALID_UUID, VALID_UUID)
    try:
        set_current_user_id(uuid4())
        assert "user_id" in current_context()
    finally:
        clear_request_context()


# -------------------------------------------------------------- request context


@pytest.mark.asyncio
async def test_request_ids_are_echoed_on_the_response(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/health")

    assert UUID(response.headers["X-Request-ID"])
    assert UUID(response.headers["X-Correlation-ID"])


@pytest.mark.asyncio
async def test_a_supplied_uuid_is_honoured(auth_client: AsyncClient) -> None:
    """One correlation id must be able to span a whole workflow."""
    response = await auth_client.get(
        "/health",
        headers={"X-Correlation-ID": VALID_UUID},
    )

    assert response.headers["X-Correlation-ID"] == VALID_UUID


@pytest.mark.asyncio
async def test_a_non_uuid_id_is_replaced(auth_client: AsyncClient) -> None:
    """Client ids reach logs and audit rows, so they are validated not trusted."""
    response = await auth_client.get(
        "/health",
        headers={"X-Request-ID": "'; DROP TABLE users; --"},
    )

    assert response.headers["X-Request-ID"] != "'; DROP TABLE users; --"
    assert UUID(response.headers["X-Request-ID"])


# ------------------------------------------------------------------ rate limits


def test_requests_are_allowed_up_to_the_limit() -> None:
    limiter = RateLimiter(limit=3, window_seconds=60)

    assert [limiter.check("user:1").allowed for _ in range(3)] == [True] * 3


def test_the_next_request_is_rejected() -> None:
    limiter = RateLimiter(limit=2, window_seconds=60)
    limiter.check("user:1")
    limiter.check("user:1")

    decision = limiter.check("user:1")

    assert decision.allowed is False
    assert decision.retry_after_seconds >= 1


def test_callers_have_separate_budgets() -> None:
    """One user's burst must not exhaust another's allowance."""
    limiter = RateLimiter(limit=1, window_seconds=60)
    limiter.check("user:1")

    assert limiter.check("user:2").allowed is True


def test_the_window_resets() -> None:
    clock = iter([0.0, 0.0, 61.0])
    limiter = RateLimiter(limit=1, window_seconds=60, clock=lambda: next(clock))

    assert limiter.check("user:1").allowed is True
    assert limiter.check("user:1").allowed is False
    assert limiter.check("user:1").allowed is True


def test_remaining_is_reported() -> None:
    limiter = RateLimiter(limit=5, window_seconds=60)

    assert limiter.check("user:1").remaining == 4


@pytest.mark.asyncio
async def test_middleware_rejects_over_the_limit_with_retry_after() -> None:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limiter=RateLimiter(limit=2))
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.get("/ping")).status_code == 200
        assert (await client.get("/ping")).status_code == 200

        limited = await client.get("/ping")

    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert int(limited.headers["Retry-After"]) >= 1


@pytest.mark.asyncio
async def test_health_checks_are_never_throttled() -> None:
    """A throttled probe would make a busy platform look unhealthy."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limiter=RateLimiter(limit=1))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for _ in range(5):
            assert (await client.get("/health")).status_code == 200


# --------------------------------------------------------------------- api keys


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


def test_issued_key_is_returned_once_and_stored_hashed(
    db_session: Session,
    user: User,
) -> None:
    """10-security_standards.md section 7: never store a plaintext API key."""
    issued = ApiKeyService(db_session).issue(user.id)

    assert issued.plaintext.startswith("pfp_")
    assert issued.plaintext not in issued.record.key_hash
    assert issued.record.key_hash != issued.plaintext


def test_a_valid_key_authenticates(db_session: Session, user: User) -> None:
    service = ApiKeyService(db_session)
    issued = service.issue(user.id)

    authenticated = service.authenticate(issued.plaintext)

    assert authenticated is not None
    assert authenticated.user_id == user.id


def test_a_wrong_key_does_not_authenticate(db_session: Session, user: User) -> None:
    service = ApiKeyService(db_session)
    service.issue(user.id)

    assert service.authenticate("pfp_wrong") is None


def test_a_revoked_key_stops_working(db_session: Session, user: User) -> None:
    service = ApiKeyService(db_session)
    issued = service.issue(user.id)
    service.revoke(user_id=user.id, key_id=issued.record.id)

    assert service.authenticate(issued.plaintext) is None


def test_using_a_key_records_when(db_session: Session, user: User) -> None:
    service = ApiKeyService(db_session)
    issued = service.issue(user.id)
    assert issued.record.last_used_at is None

    service.authenticate(issued.plaintext)

    assert service.list_keys(user.id)[0].last_used_at is not None


def test_another_users_key_cannot_be_revoked(
    db_session: Session,
    user: User,
) -> None:
    service = ApiKeyService(db_session)
    issued = service.issue(user.id)

    assert service.revoke(user_id=uuid4(), key_id=issued.record.id) is None


def test_secret_hashing_bypasses_the_password_policy() -> None:
    """A generated key has ample entropy but need not contain every character class."""
    service = SecurityService()

    hashed = service.hash_secret("pfp_aaaaaaaaaaaaaaaaaaaaaaaaaaaa")

    assert service.verify_secret("pfp_aaaaaaaaaaaaaaaaaaaaaaaaaaaa", hashed)


# -------------------------------------------------------------------- endpoints


@pytest.mark.asyncio
async def test_api_key_endpoint_returns_the_secret_once(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    created = await auth_client.post(
        "/api/v1/api-keys",
        json={"name": "macrodroid"},
        headers=headers,
    )
    assert created.status_code == 201
    secret = created.json()["data"]["api_key"]

    listed = await auth_client.get("/api/v1/api-keys", headers=headers)
    assert secret not in listed.text
    assert listed.json()["data"][0]["name"] == "macrodroid"


@pytest.mark.asyncio
async def test_a_per_user_key_authenticates_ingestion(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    """The Sprint 15 key identifies its owner directly, with no env setting."""
    _, headers = authenticated_user
    created = await auth_client.post(
        "/api/v1/api-keys",
        json={"name": "phone"},
        headers=headers,
    )
    secret = created.json()["data"]["api_key"]

    response = await auth_client.post(
        "/api/v1/ingest/sms",
        json={
            "sender": "VK-HDFCBK",
            "message_text": "Rs.70.00 debited from A/C XXXX0452 at SmartQ",
            "received_at": "2026-06-02T10:00:00",
        },
        headers={"X-API-KEY": secret},
    )

    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_a_revoked_key_is_refused_by_ingestion(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user
    created = await auth_client.post(
        "/api/v1/api-keys",
        json={"name": "phone"},
        headers=headers,
    )
    secret = created.json()["data"]["api_key"]
    key_id = created.json()["data"]["id"]

    await auth_client.delete(f"/api/v1/api-keys/{key_id}", headers=headers)

    response = await auth_client.post(
        "/api/v1/ingest/sms",
        json={
            "sender": "VK-HDFCBK",
            "message_text": "Rs.70.00 debited from A/C XXXX0452 at SmartQ",
            "received_at": "2026-06-02T10:00:00",
        },
        headers={"X-API-KEY": secret},
    )

    assert response.status_code == 401


# ----------------------------------------------------------------------- admin


async def _promote(auth_client: AsyncClient, db_session_engine, email: str) -> None:
    from sqlmodel import Session as SqlSession
    from sqlmodel import select

    with SqlSession(db_session_engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        user.role = UserRole.ADMIN.value
        session.add(user)
        session.commit()


@pytest.mark.asyncio
async def test_admin_routes_reject_a_normal_user(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    response = await auth_client.get("/api/v1/admin/users", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_admin_can_list_users(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    user_id = await register_user(auth_client, email="admin@example.com")
    await _promote(auth_client, test_engine, "admin@example.com")
    headers = authorization_header(user_id, email="admin@example.com")

    response = await auth_client.get("/api/v1/admin/users", headers=headers)

    assert response.status_code == 200
    assert response.json()["meta"]["total_records"] == 1


@pytest.mark.asyncio
async def test_admin_stats_carry_no_financial_detail(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    user_id = await register_user(auth_client, email="admin@example.com")
    await _promote(auth_client, test_engine, "admin@example.com")
    headers = authorization_header(user_id, email="admin@example.com")

    response = await auth_client.get("/api/v1/admin/stats", headers=headers)

    data = response.json()["data"]
    assert set(data) == {"users", "active_users", "accounts", "transactions"}


@pytest.mark.asyncio
async def test_an_admin_cannot_disable_themselves(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    """Otherwise a sole admin could lock the platform out of administration."""
    user_id = await register_user(auth_client, email="admin@example.com")
    await _promote(auth_client, test_engine, "admin@example.com")
    headers = authorization_header(user_id, email="admin@example.com")

    response = await auth_client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_role_is_read_from_the_record_not_the_token(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    """A token outlives a role change, so a demoted admin must lose access at once."""
    user_id = await register_user(auth_client, email="admin@example.com")
    await _promote(auth_client, test_engine, "admin@example.com")
    headers = authorization_header(user_id, email="admin@example.com")
    granted = await auth_client.get("/api/v1/admin/stats", headers=headers)
    assert granted.status_code == 200

    from sqlmodel import Session as SqlSession

    with SqlSession(test_engine) as session:
        user = session.get(User, user_id)
        user.role = UserRole.USER.value
        session.add(user)
        session.commit()

    # Same token, still valid, but the role has changed.
    revoked = await auth_client.get("/api/v1/admin/stats", headers=headers)
    assert revoked.status_code == 403
