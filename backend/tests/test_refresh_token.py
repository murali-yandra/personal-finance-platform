from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.config import get_settings
from app.core.jwt import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    JwtService,
    TokenType,
)
from app.core.refresh_token import (
    RefreshTokenExpiredError,
    RefreshTokenInvalidError,
    RefreshTokenResult,
    RefreshTokenService,
    get_refresh_token_service,
)

JWT_SECRET = "unit-test-jwt-secret-32-bytes-long"
USER_EMAIL = "user@example.com"
USER_ROLE = "USER"


def build_jwt_service() -> JwtService:
    return JwtService(JWT_SECRET, clock=lambda: datetime.now(UTC))


def build_refresh_token_service(
    jwt_service: JwtService | None = None,
) -> RefreshTokenService:
    return RefreshTokenService(jwt_service or build_jwt_service())


def encode_refresh_token_with_claims(claim_overrides: dict[str, object]) -> str:
    issued_at = datetime.now(UTC)
    user_id = str(uuid4())
    claims: dict[str, object] = {
        "sub": user_id,
        "user_id": user_id,
        "email": USER_EMAIL,
        "role": USER_ROLE,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
        "jti": str(uuid4()),
        "token_type": TokenType.REFRESH.value,
    }
    claims.update(claim_overrides)
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def test_refresh_access_token_returns_new_access_token() -> None:
    jwt_service = build_jwt_service()
    refresh_token_service = build_refresh_token_service(jwt_service)
    user_id = uuid4()
    refresh_token = jwt_service.create_refresh_token(
        user_id=user_id,
        email=USER_EMAIL,
        role=USER_ROLE,
    )
    refresh_claims = jwt_service.decode_token(refresh_token, TokenType.REFRESH)

    result = refresh_token_service.refresh_access_token(refresh_token)
    access_claims = jwt_service.decode_token(result.access_token, TokenType.ACCESS)

    assert isinstance(result, RefreshTokenResult)
    assert access_claims["sub"] == str(user_id)
    assert access_claims["user_id"] == str(user_id)
    assert access_claims["email"] == USER_EMAIL
    assert access_claims["role"] == USER_ROLE
    assert access_claims["token_type"] == TokenType.ACCESS.value
    assert access_claims["exp"] - access_claims["iat"] == (
        ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    assert access_claims["jti"] != refresh_claims["jti"]
    assert not hasattr(result, "refresh_token")


def test_refresh_access_token_rejects_access_token() -> None:
    jwt_service = build_jwt_service()
    refresh_token_service = build_refresh_token_service(jwt_service)
    access_token = jwt_service.create_access_token(user_id=uuid4(), email=USER_EMAIL)

    with pytest.raises(RefreshTokenInvalidError):
        refresh_token_service.refresh_access_token(access_token)


def test_refresh_access_token_rejects_expired_refresh_token() -> None:
    expired_jwt_service = JwtService(
        JWT_SECRET,
        refresh_token_lifetime=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        clock=lambda: datetime(2000, 1, 1, tzinfo=UTC),
    )
    expired_refresh_token = expired_jwt_service.create_refresh_token(
        user_id=uuid4(),
        email=USER_EMAIL,
    )

    with pytest.raises(RefreshTokenExpiredError):
        build_refresh_token_service().refresh_access_token(expired_refresh_token)


def test_refresh_access_token_rejects_malformed_token() -> None:
    refresh_token_service = build_refresh_token_service()

    with pytest.raises(RefreshTokenInvalidError):
        refresh_token_service.refresh_access_token("not-a-jwt")


def test_refresh_access_token_rejects_invalid_signature() -> None:
    trusted_jwt_service = build_jwt_service()
    untrusted_jwt_service = JwtService(
        "different-unit-test-jwt-secret-32",
        clock=lambda: datetime.now(UTC),
    )
    untrusted_refresh_token = untrusted_jwt_service.create_refresh_token(
        user_id=uuid4(),
        email=USER_EMAIL,
    )

    with pytest.raises(RefreshTokenInvalidError):
        build_refresh_token_service(trusted_jwt_service).refresh_access_token(
            untrusted_refresh_token
        )


def test_refresh_access_token_rejects_invalid_user_id_claim() -> None:
    refresh_token = encode_refresh_token_with_claims(
        {"sub": "not-a-uuid", "user_id": "not-a-uuid"}
    )

    with pytest.raises(RefreshTokenInvalidError):
        build_refresh_token_service().refresh_access_token(refresh_token)


def test_refresh_access_token_rejects_subject_user_id_mismatch() -> None:
    refresh_token = encode_refresh_token_with_claims({"sub": str(uuid4())})

    with pytest.raises(RefreshTokenInvalidError):
        build_refresh_token_service().refresh_access_token(refresh_token)


def test_refresh_access_token_rejects_empty_email_claim() -> None:
    refresh_token = encode_refresh_token_with_claims({"email": ""})

    with pytest.raises(RefreshTokenInvalidError):
        build_refresh_token_service().refresh_access_token(refresh_token)


def test_refresh_access_token_rejects_empty_role_claim() -> None:
    refresh_token = encode_refresh_token_with_claims({"role": ""})

    with pytest.raises(RefreshTokenInvalidError):
        build_refresh_token_service().refresh_access_token(refresh_token)


def test_get_refresh_token_service_uses_environment_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    get_settings.cache_clear()
    try:
        service = get_refresh_token_service()
        user_id = uuid4()
        refresh_token = build_jwt_service().create_refresh_token(
            user_id=user_id,
            email=USER_EMAIL,
        )
        result = service.refresh_access_token(refresh_token)
        claims = build_jwt_service().decode_token(result.access_token, TokenType.ACCESS)

        assert claims["user_id"] == str(user_id)
    finally:
        get_settings.cache_clear()
