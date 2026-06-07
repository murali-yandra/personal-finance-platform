import pytest
from argon2 import PasswordHasher
from argon2.low_level import Type

from app.core.security import PasswordPolicyError, SecurityService

VALID_PASSWORD = "SecurePass1"


@pytest.fixture
def security_service() -> SecurityService:
    return SecurityService(
        PasswordHasher(
            time_cost=1,
            memory_cost=1024,
            parallelism=1,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
    )


def test_hash_password_returns_argon2id_hash(
    security_service: SecurityService,
) -> None:
    password_hash = security_service.hash_password(VALID_PASSWORD)

    assert password_hash.startswith("$argon2id$")
    assert password_hash != VALID_PASSWORD


def test_verify_password_accepts_matching_password(
    security_service: SecurityService,
) -> None:
    password_hash = security_service.hash_password(VALID_PASSWORD)

    assert security_service.verify_password(VALID_PASSWORD, password_hash) is True


def test_verify_password_rejects_incorrect_password(
    security_service: SecurityService,
) -> None:
    password_hash = security_service.hash_password(VALID_PASSWORD)

    assert security_service.verify_password("WrongPass1", password_hash) is False


def test_hash_password_uses_unique_salts(
    security_service: SecurityService,
) -> None:
    first_hash = security_service.hash_password(VALID_PASSWORD)
    second_hash = security_service.hash_password(VALID_PASSWORD)

    assert first_hash != second_hash


def test_verify_password_rejects_invalid_hash(
    security_service: SecurityService,
) -> None:
    assert (
        security_service.verify_password(VALID_PASSWORD, "not-a-password-hash") is False
    )


@pytest.mark.parametrize(
    "password",
    [
        "Short1",
        "nouppercase1",
        "NOLOWERCASE1",
        "NoNumberHere",
    ],
)
def test_hash_password_rejects_policy_violations(
    security_service: SecurityService,
    password: str,
) -> None:
    with pytest.raises(PasswordPolicyError):
        security_service.hash_password(password)


def test_password_needs_rehash_accepts_current_hash(
    security_service: SecurityService,
) -> None:
    password_hash = security_service.hash_password(VALID_PASSWORD)

    assert security_service.password_needs_rehash(password_hash) is False


def test_password_needs_rehash_flags_invalid_hash(
    security_service: SecurityService,
) -> None:
    assert security_service.password_needs_rehash("not-a-password-hash") is True
