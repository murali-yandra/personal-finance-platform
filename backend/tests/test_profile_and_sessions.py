"""Profile, settings and login session management."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.core.jwt import JwtService
from app.domains.access.models import UserSession
from app.domains.access.sessions import SessionService, token_hash
from app.domains.users.models import User, UserSettings
from app.domains.users.profile import (
    ProfileValidationError,
    UpdateProfileCommand,
    UpdateSettingsCommand,
    UserProfileService,
)
from tests.conftest import (
    DEFAULT_TEST_EMAIL,
    DEFAULT_TEST_PASSWORD,
    TEST_JWT_SECRET,
    authorization_header,
    register_user,
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
    db_session.commit()
    return created


@pytest.fixture
def profile_service(db_session: Session) -> UserProfileService:
    return UserProfileService(db_session)


# ---------------------------------------------------------------------- profile


def test_display_name_is_updated(
    profile_service: UserProfileService,
    user: User,
) -> None:
    updated = profile_service.update_profile(
        UpdateProfileCommand(user_id=user.id, display_name="New Name")
    )

    assert updated.display_name == "New Name"


def test_omitted_fields_are_untouched(
    profile_service: UserProfileService,
    user: User,
) -> None:
    updated = profile_service.update_profile(
        UpdateProfileCommand(user_id=user.id, display_name="New Name")
    )

    assert updated.timezone == "Asia/Kolkata"
    assert updated.default_currency == "INR"


def test_unknown_timezone_is_rejected(
    profile_service: UserProfileService,
    user: User,
) -> None:
    """An unknown zone would make every date-bounded report silently wrong."""
    with pytest.raises(ProfileValidationError):
        profile_service.update_profile(
            UpdateProfileCommand(user_id=user.id, timezone="Mars/Olympus_Mons")
        )


def test_a_real_timezone_is_accepted(
    profile_service: UserProfileService,
    user: User,
) -> None:
    updated = profile_service.update_profile(
        UpdateProfileCommand(user_id=user.id, timezone="Europe/London")
    )

    assert updated.timezone == "Europe/London"


def test_invalid_currency_is_rejected(
    profile_service: UserProfileService,
    user: User,
) -> None:
    with pytest.raises(ProfileValidationError):
        profile_service.update_profile(
            UpdateProfileCommand(user_id=user.id, default_currency="RUPEE")
        )


def test_empty_display_name_is_rejected(
    profile_service: UserProfileService,
    user: User,
) -> None:
    with pytest.raises(ProfileValidationError):
        profile_service.update_profile(
            UpdateProfileCommand(user_id=user.id, display_name="   ")
        )


def test_telegram_chat_id_can_be_set_and_cleared(
    profile_service: UserProfileService,
    user: User,
) -> None:
    linked = profile_service.update_profile(
        UpdateProfileCommand(user_id=user.id, telegram_chat_id="123456789")
    )
    assert linked.telegram_chat_id == "123456789"

    cleared = profile_service.update_profile(
        UpdateProfileCommand(user_id=user.id, telegram_chat_id=None)
    )
    assert cleared.telegram_chat_id is None


def test_group_chat_ids_are_allowed(
    profile_service: UserProfileService,
    user: User,
) -> None:
    """Telegram group chat ids are negative."""
    updated = profile_service.update_profile(
        UpdateProfileCommand(user_id=user.id, telegram_chat_id="-1001234567890")
    )

    assert updated.telegram_chat_id == "-1001234567890"


def test_non_numeric_chat_id_is_rejected(
    profile_service: UserProfileService,
    user: User,
) -> None:
    with pytest.raises(ProfileValidationError):
        profile_service.update_profile(
            UpdateProfileCommand(user_id=user.id, telegram_chat_id="@my_channel")
        )


# --------------------------------------------------------------------- settings


def test_notification_mode_is_updated(
    profile_service: UserProfileService,
    user: User,
) -> None:
    updated = profile_service.update_settings(
        UpdateSettingsCommand(user_id=user.id, notification_mode="ALWAYS")
    )

    assert updated.notification_mode == "ALWAYS"


def test_unsupported_notification_mode_is_rejected(
    profile_service: UserProfileService,
    user: User,
) -> None:
    with pytest.raises(ProfileValidationError):
        profile_service.update_settings(
            UpdateSettingsCommand(user_id=user.id, notification_mode="SHOUT")
        )


def test_ai_suggestions_can_be_toggled(
    profile_service: UserProfileService,
    user: User,
) -> None:
    updated = profile_service.update_settings(
        UpdateSettingsCommand(user_id=user.id, ai_suggestions_enabled=True)
    )

    assert updated.ai_suggestions_enabled is True


def test_invalid_language_is_rejected(
    profile_service: UserProfileService,
    user: User,
) -> None:
    with pytest.raises(ProfileValidationError):
        profile_service.update_settings(
            UpdateSettingsCommand(user_id=user.id, preferred_language="English")
        )


# --------------------------------------------------------------------- sessions


def test_session_stores_only_a_token_digest(
    db_session: Session,
    user: User,
) -> None:
    """A leaked sessions table must not hand over working credentials."""
    record = SessionService(db_session).start(user.id, "secret-refresh-token")

    assert record.token_hash != "secret-refresh-token"
    assert record.token_hash == token_hash("secret-refresh-token")


def test_a_live_session_validates(db_session: Session, user: User) -> None:
    service = SessionService(db_session)
    service.start(user.id, "token-a")

    assert service.validate("token-a") is not None


def test_an_unknown_token_does_not_validate(
    db_session: Session,
    user: User,
) -> None:
    assert SessionService(db_session).validate("never-issued") is None


def test_a_revoked_session_stops_validating(
    db_session: Session,
    user: User,
) -> None:
    service = SessionService(db_session)
    record = service.start(user.id, "token-a")
    service.revoke(user_id=user.id, session_id=record.id)

    assert service.validate("token-a") is None


def test_an_expired_session_stops_validating(
    db_session: Session,
    user: User,
) -> None:
    service = SessionService(db_session)
    record = service.start(user.id, "token-a")
    record.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
    db_session.add(record)
    db_session.commit()

    assert service.validate("token-a") is None


def test_validating_updates_last_seen(db_session: Session, user: User) -> None:
    service = SessionService(db_session)
    record = service.start(user.id, "token-a")
    record.last_seen_at = None
    db_session.add(record)
    db_session.commit()

    service.validate("token-a")

    assert service.list_sessions(user.id)[0].last_seen_at is not None


def test_revoke_all_ends_every_session(db_session: Session, user: User) -> None:
    service = SessionService(db_session)
    for token in ("a", "b", "c"):
        service.start(user.id, token)

    assert service.revoke_all(user.id) == 3
    assert service.list_sessions(user.id) == []


def test_revoke_all_can_keep_the_current_session(
    db_session: Session,
    user: User,
) -> None:
    """Reacting to a suspicious login must not log you out of the device you use."""
    service = SessionService(db_session)
    keep = service.start(user.id, "current")
    service.start(user.id, "other")

    service.revoke_all(user.id, except_session_id=keep.id)

    remaining = service.list_sessions(user.id)
    assert [record.id for record in remaining] == [keep.id]


def test_another_users_session_cannot_be_revoked(
    db_session: Session,
    user: User,
) -> None:
    service = SessionService(db_session)
    record = service.start(user.id, "token-a")

    assert service.revoke(user_id=uuid4(), session_id=record.id) is None


# -------------------------------------------------------------------- endpoints


@pytest.mark.asyncio
async def test_patch_users_me_updates_the_profile(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    response = await auth_client.patch(
        "/api/v1/users/me",
        json={"display_name": "Murali", "timezone": "Asia/Kolkata"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["display_name"] == "Murali"


@pytest.mark.asyncio
async def test_patch_users_me_rejects_a_bad_timezone(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    response = await auth_client.patch(
        "/api/v1/users/me",
        json={"timezone": "Nowhere/Land"},
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_settings_round_trip(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    initial = await auth_client.get("/api/v1/settings", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["data"]["notification_mode"] == "LOW_CONFIDENCE_ONLY"

    updated = await auth_client.patch(
        "/api/v1/settings",
        json={"notification_mode": "ALWAYS", "ai_suggestions_enabled": True},
        headers=headers,
    )

    assert updated.status_code == 200
    data = updated.json()["data"]
    assert data["notification_mode"] == "ALWAYS"
    assert data["ai_suggestions_enabled"] is True


@pytest.mark.asyncio
async def test_settings_require_authentication(auth_client: AsyncClient) -> None:
    assert (await auth_client.get("/api/v1/settings")).status_code == 401


@pytest.mark.asyncio
async def test_login_records_a_session(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    await register_user(auth_client)
    await auth_client.post(
        "/api/v1/auth/login",
        json={"email": DEFAULT_TEST_EMAIL, "password": DEFAULT_TEST_PASSWORD},
    )

    with Session(test_engine) as session:
        assert len(list(session.exec(select(UserSession)).all())) == 1


@pytest.mark.asyncio
async def test_logout_revokes_the_session_and_blocks_refresh(
    auth_client: AsyncClient,
) -> None:
    """The point of tracking sessions: a valid JWT stops working once revoked."""
    await register_user(auth_client)
    login = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": DEFAULT_TEST_EMAIL, "password": DEFAULT_TEST_PASSWORD},
    )
    refresh_token = login.json()["data"]["refresh_token"]

    before = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert before.status_code == 200

    logout = await auth_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout.json()["data"]["sessions_revoked"] == 1

    after = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_logging_out_twice_is_not_an_error(auth_client: AsyncClient) -> None:
    """Reporting an error would tell an attacker which tokens are real."""
    await register_user(auth_client)
    login = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": DEFAULT_TEST_EMAIL, "password": DEFAULT_TEST_PASSWORD},
    )
    refresh_token = login.json()["data"]["refresh_token"]

    await auth_client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    second = await auth_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )

    assert second.status_code == 200
    assert second.json()["data"]["sessions_revoked"] == 0


@pytest.mark.asyncio
async def test_logout_everywhere_ends_every_session(
    auth_client: AsyncClient,
) -> None:
    await register_user(auth_client)
    tokens = []
    for _ in range(3):
        login = await auth_client.post(
            "/api/v1/auth/login",
            json={"email": DEFAULT_TEST_EMAIL, "password": DEFAULT_TEST_PASSWORD},
        )
        tokens.append(login.json()["data"]["refresh_token"])

    logout = await auth_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens[0], "everywhere": True},
    )

    assert logout.json()["data"]["sessions_revoked"] == 3

    for token in tokens:
        refreshed = await auth_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": token},
        )
        assert refreshed.status_code == 401


@pytest.mark.asyncio
async def test_sessions_are_listed_without_the_token(
    auth_client: AsyncClient,
) -> None:
    user_id = await register_user(auth_client)
    login = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": DEFAULT_TEST_EMAIL, "password": DEFAULT_TEST_PASSWORD},
    )
    refresh_token = login.json()["data"]["refresh_token"]
    headers = authorization_header(user_id)

    response = await auth_client.get("/api/v1/sessions", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert refresh_token not in response.text


@pytest.mark.asyncio
async def test_another_users_session_is_not_listed(
    auth_client: AsyncClient,
) -> None:
    await register_user(auth_client)
    await auth_client.post(
        "/api/v1/auth/login",
        json={"email": DEFAULT_TEST_EMAIL, "password": DEFAULT_TEST_PASSWORD},
    )

    intruder_id = await register_user(auth_client, email="intruder@example.com")
    intruder_headers = authorization_header(intruder_id, email="intruder@example.com")

    response = await auth_client.get("/api/v1/sessions", headers=intruder_headers)

    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_an_access_token_still_works_until_it_expires(
    auth_client: AsyncClient,
) -> None:
    """Revocation applies to refresh tokens; short-lived access tokens time out.

    Access tokens live 15 minutes and are validated without a database lookup,
    which is what keeps every request cheap. Revocation therefore bounds a
    stolen session to that window rather than 30 days.
    """
    user_id = await register_user(auth_client)
    login = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": DEFAULT_TEST_EMAIL, "password": DEFAULT_TEST_PASSWORD},
    )
    refresh_token = login.json()["data"]["refresh_token"]
    access = JwtService(TEST_JWT_SECRET).create_access_token(
        user_id=user_id,
        email=DEFAULT_TEST_EMAIL,
    )

    await auth_client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})

    still_valid = await auth_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert still_valid.status_code == 200
