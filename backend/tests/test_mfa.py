"""Multi-factor authentication (Sprint 15)."""

import pyotp
import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.domains.access.mfa import (
    InvalidMfaCodeError,
    MfaAlreadyEnabledError,
    MfaNotEnrolledError,
    MfaService,
)
from app.domains.access.models import MfaRecoveryCode, UserMfa
from app.domains.users.models import User, UserSettings
from tests.conftest import (
    DEFAULT_TEST_EMAIL,
    DEFAULT_TEST_PASSWORD,
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
def service(db_session: Session) -> MfaService:
    return MfaService(db_session)


def _code(secret: str) -> str:
    return pyotp.TOTP(secret).now()


# --------------------------------------------------------------------- enrolment


def test_enrolment_does_not_enable_mfa(
    service: MfaService,
    user: User,
) -> None:
    """A secret that never reached the authenticator must not lock anyone out."""
    service.begin_enrolment(user.id, user.email)

    assert service.is_enabled(user.id) is False


def test_enrolment_returns_a_provisioning_uri(
    service: MfaService,
    user: User,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)

    assert enrolment.provisioning_uri.startswith("otpauth://totp/")
    assert "Personal%20Finance%20Tracker" in enrolment.provisioning_uri


def test_enrolment_issues_ten_recovery_codes(
    service: MfaService,
    user: User,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)

    assert len(enrolment.recovery_codes) == 10
    assert len(set(enrolment.recovery_codes)) == 10


def test_recovery_codes_are_stored_hashed(
    service: MfaService,
    user: User,
    db_session: Session,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)

    stored = list(db_session.exec(select(MfaRecoveryCode)).all())
    hashes = {code.code_hash for code in stored}
    for plaintext in enrolment.recovery_codes:
        assert plaintext not in hashes


def test_a_correct_code_confirms_enrolment(
    service: MfaService,
    user: User,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)

    service.confirm_enrolment(user.id, _code(enrolment.secret))

    assert service.is_enabled(user.id) is True


def test_a_wrong_code_does_not_confirm(
    service: MfaService,
    user: User,
) -> None:
    service.begin_enrolment(user.id, user.email)

    with pytest.raises(InvalidMfaCodeError):
        service.confirm_enrolment(user.id, "000000")

    assert service.is_enabled(user.id) is False


def test_confirming_without_enrolling_is_rejected(
    service: MfaService,
    user: User,
) -> None:
    with pytest.raises(MfaNotEnrolledError):
        service.confirm_enrolment(user.id, "123456")


def test_enrolling_twice_when_enabled_is_rejected(
    service: MfaService,
    user: User,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)
    service.confirm_enrolment(user.id, _code(enrolment.secret))

    with pytest.raises(MfaAlreadyEnabledError):
        service.begin_enrolment(user.id, user.email)


def test_an_abandoned_enrolment_can_be_restarted(
    service: MfaService,
    user: User,
    db_session: Session,
) -> None:
    """Someone whose authenticator failed to scan must be able to start again."""
    first = service.begin_enrolment(user.id, user.email)

    second = service.begin_enrolment(user.id, user.email)

    assert second.secret != first.secret
    assert len(list(db_session.exec(select(UserMfa)).all())) == 1
    # The abandoned secret stops working.
    with pytest.raises(InvalidMfaCodeError):
        service.confirm_enrolment(user.id, _code(first.secret))


# ------------------------------------------------------------------ verification


def test_a_current_code_verifies(service: MfaService, user: User) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)
    service.confirm_enrolment(user.id, _code(enrolment.secret))

    assert service.verify(user.id, _code(enrolment.secret)) is True


def test_a_wrong_code_does_not_verify(service: MfaService, user: User) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)
    service.confirm_enrolment(user.id, _code(enrolment.secret))

    assert service.verify(user.id, "000000") is False


def test_a_non_numeric_code_does_not_verify(
    service: MfaService,
    user: User,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)
    service.confirm_enrolment(user.id, _code(enrolment.secret))

    assert service.verify(user.id, "abcdef") is False


def test_verification_fails_when_mfa_is_not_enabled(
    service: MfaService,
    user: User,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)

    assert service.verify(user.id, _code(enrolment.secret)) is False


# --------------------------------------------------------------- recovery codes


def test_a_recovery_code_works_in_place_of_a_totp_code(
    service: MfaService,
    user: User,
) -> None:
    """A lost phone must not mean a lost account."""
    enrolment = service.begin_enrolment(user.id, user.email)
    service.confirm_enrolment(user.id, _code(enrolment.secret))

    assert service.verify(user.id, enrolment.recovery_codes[0]) is True


def test_a_recovery_code_works_only_once(
    service: MfaService,
    user: User,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)
    service.confirm_enrolment(user.id, _code(enrolment.secret))
    code = enrolment.recovery_codes[0]

    assert service.verify(user.id, code) is True
    assert service.verify(user.id, code) is False


def test_spending_one_code_leaves_the_others(
    service: MfaService,
    user: User,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)
    service.confirm_enrolment(user.id, _code(enrolment.secret))
    service.verify(user.id, enrolment.recovery_codes[0])

    assert service.remaining_recovery_codes(user.id) == 9
    assert service.verify(user.id, enrolment.recovery_codes[1]) is True


def test_recovery_codes_ignore_spacing_and_case(
    service: MfaService,
    user: User,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)
    service.confirm_enrolment(user.id, _code(enrolment.secret))
    code = enrolment.recovery_codes[0]

    assert service.verify(user.id, f" {code.lower()} ") is True


def test_regenerating_replaces_the_old_codes(
    service: MfaService,
    user: User,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)
    service.confirm_enrolment(user.id, _code(enrolment.secret))

    fresh = service.regenerate_recovery_codes(user.id, _code(enrolment.secret))

    assert len(fresh) == 10
    assert service.verify(user.id, enrolment.recovery_codes[0]) is False
    assert service.verify(user.id, fresh[0]) is True


def test_regenerating_requires_a_valid_code(
    service: MfaService,
    user: User,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)
    service.confirm_enrolment(user.id, _code(enrolment.secret))

    with pytest.raises(InvalidMfaCodeError):
        service.regenerate_recovery_codes(user.id, "000000")


# ------------------------------------------------------------------- disabling


def test_disabling_requires_a_valid_code(
    service: MfaService,
    user: User,
) -> None:
    """Otherwise a stolen access token could strip the protection."""
    enrolment = service.begin_enrolment(user.id, user.email)
    service.confirm_enrolment(user.id, _code(enrolment.secret))

    with pytest.raises(InvalidMfaCodeError):
        service.disable(user.id, "000000")

    assert service.is_enabled(user.id) is True


def test_disabling_removes_the_secret_and_codes(
    service: MfaService,
    user: User,
    db_session: Session,
) -> None:
    enrolment = service.begin_enrolment(user.id, user.email)
    service.confirm_enrolment(user.id, _code(enrolment.secret))

    service.disable(user.id, _code(enrolment.secret))

    assert service.is_enabled(user.id) is False
    assert list(db_session.exec(select(UserMfa)).all()) == []
    assert list(db_session.exec(select(MfaRecoveryCode)).all()) == []


# ------------------------------------------------------------------- login flow


async def _enable_mfa(client: AsyncClient, headers: dict[str, str]) -> str:
    enrolment = await client.post("/api/v1/mfa/enrol", headers=headers)
    secret = enrolment.json()["data"]["secret"]
    confirm = await client.post(
        "/api/v1/mfa/confirm",
        json={"code": _code(secret)},
        headers=headers,
    )
    assert confirm.status_code == 200, confirm.text
    return secret


@pytest.mark.asyncio
async def test_login_without_mfa_is_unaffected(auth_client: AsyncClient) -> None:
    await register_user(auth_client)

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": DEFAULT_TEST_EMAIL, "password": DEFAULT_TEST_PASSWORD},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login_demands_a_code_once_mfa_is_enabled(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user
    await _enable_mfa(auth_client, headers)

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": DEFAULT_TEST_EMAIL, "password": DEFAULT_TEST_PASSWORD},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MFA_REQUIRED"


@pytest.mark.asyncio
async def test_a_correct_password_alone_issues_no_token(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    """The whole point of a second factor: the password is not sufficient."""
    _, headers = authenticated_user
    await _enable_mfa(auth_client, headers)

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": DEFAULT_TEST_EMAIL, "password": DEFAULT_TEST_PASSWORD},
    )

    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


@pytest.mark.asyncio
async def test_login_succeeds_with_a_valid_code(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user
    secret = await _enable_mfa(auth_client, headers)

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": DEFAULT_TEST_EMAIL,
            "password": DEFAULT_TEST_PASSWORD,
            "mfa_code": _code(secret),
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_login_with_a_wrong_code_is_refused(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user
    await _enable_mfa(auth_client, headers)

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": DEFAULT_TEST_EMAIL,
            "password": DEFAULT_TEST_PASSWORD,
            "mfa_code": "000000",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_works_with_a_recovery_code(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    """The path back in when the authenticator is gone."""
    _, headers = authenticated_user
    enrolment = await auth_client.post("/api/v1/mfa/enrol", headers=headers)
    secret = enrolment.json()["data"]["secret"]
    recovery = enrolment.json()["data"]["recovery_codes"][0]
    await auth_client.post(
        "/api/v1/mfa/confirm",
        json={"code": _code(secret)},
        headers=headers,
    )

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": DEFAULT_TEST_EMAIL,
            "password": DEFAULT_TEST_PASSWORD,
            "mfa_code": recovery,
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_mfa_status_reports_enrolment_state(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    before = await auth_client.get("/api/v1/mfa", headers=headers)
    assert before.json()["data"]["enabled"] is False

    await _enable_mfa(auth_client, headers)

    after = await auth_client.get("/api/v1/mfa", headers=headers)
    data = after.json()["data"]
    assert data["enabled"] is True
    assert data["recovery_codes_remaining"] == 10


@pytest.mark.asyncio
async def test_mfa_endpoints_require_authentication(
    auth_client: AsyncClient,
) -> None:
    assert (await auth_client.get("/api/v1/mfa")).status_code == 401
    assert (await auth_client.post("/api/v1/mfa/enrol")).status_code == 401
