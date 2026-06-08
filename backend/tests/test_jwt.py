from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr

from app.core.jwt import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_USER_ROLE,
    REFRESH_TOKEN_EXPIRE_DAYS,
    TOKEN_TYPE_BEARER,
    JwtConfigurationError,
    JwtService,
    JwtTokenExpiredError,
    JwtTokenInvalidError,
    JwtTokenTypeError,
    TokenPair,
    TokenType,
)

JWT_SECRET = "unit-test-jwt-secret-32-bytes-long"
USER_EMAIL = "user@example.com"


def build_jwt_service(secret: str = JWT_SECRET) -> JwtService:
    return JwtService(secret, clock=lambda: datetime.now(UTC))


def test_create_access_token_contains_required_claims() -> None:
    service = build_jwt_service()
    user_id = uuid4()

    token = service.create_access_token(user_id=user_id, email=USER_EMAIL)
    claims = service.decode_token(token, expected_token_type=TokenType.ACCESS)

    assert claims["sub"] == str(user_id)
    assert claims["user_id"] == str(user_id)
    assert claims["email"] == USER_EMAIL
    assert claims["role"] == DEFAULT_USER_ROLE
    assert claims["token_type"] == TokenType.ACCESS.value
    assert claims["exp"] - claims["iat"] == ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert UUID(claims["jti"])


def test_create_refresh_token_contains_required_claims() -> None:
    service = build_jwt_service()
    user_id = uuid4()

    token = service.create_refresh_token(user_id=user_id, email=USER_EMAIL)
    claims = service.decode_token(token, expected_token_type=TokenType.REFRESH)

    assert claims["sub"] == str(user_id)
    assert claims["user_id"] == str(user_id)
    assert claims["email"] == USER_EMAIL
    assert claims["role"] == DEFAULT_USER_ROLE
    assert claims["token_type"] == TokenType.REFRESH.value
    assert claims["exp"] - claims["iat"] == REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    assert UUID(claims["jti"])


def test_create_token_pair_returns_bearer_tokens() -> None:
    service = build_jwt_service()
    user_id = uuid4()

    token_pair = service.create_token_pair(user_id=user_id, email=USER_EMAIL)

    assert isinstance(token_pair, TokenPair)
    assert token_pair.token_type == TOKEN_TYPE_BEARER
    assert service.decode_token(token_pair.access_token, TokenType.ACCESS)[
        "user_id"
    ] == str(user_id)
    assert service.decode_token(token_pair.refresh_token, TokenType.REFRESH)[
        "user_id"
    ] == str(user_id)


def test_decode_token_rejects_wrong_token_type() -> None:
    service = build_jwt_service()
    refresh_token = service.create_refresh_token(user_id=uuid4(), email=USER_EMAIL)

    with pytest.raises(JwtTokenTypeError):
        service.decode_token(refresh_token, expected_token_type=TokenType.ACCESS)


def test_decode_token_rejects_expired_token() -> None:
    expired_service = JwtService(
        JWT_SECRET,
        access_token_lifetime=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        clock=lambda: datetime(2000, 1, 1, tzinfo=UTC),
    )
    expired_token = expired_service.create_access_token(
        user_id=uuid4(),
        email=USER_EMAIL,
    )

    with pytest.raises(JwtTokenExpiredError):
        build_jwt_service().decode_token(expired_token, TokenType.ACCESS)


def test_decode_token_rejects_invalid_signature() -> None:
    trusted_service = build_jwt_service()
    untrusted_service = build_jwt_service(secret="different-unit-test-jwt-secret-32")
    token = untrusted_service.create_access_token(user_id=uuid4(), email=USER_EMAIL)

    with pytest.raises(JwtTokenInvalidError):
        trusted_service.decode_token(token, TokenType.ACCESS)


def test_decode_token_rejects_malformed_token() -> None:
    service = build_jwt_service()

    with pytest.raises(JwtTokenInvalidError):
        service.decode_token("not-a-jwt", TokenType.ACCESS)


def test_create_tokens_use_unique_jti_values() -> None:
    service = build_jwt_service()
    user_id = uuid4()

    first_token = service.create_access_token(user_id=user_id, email=USER_EMAIL)
    second_token = service.create_access_token(user_id=user_id, email=USER_EMAIL)

    first_claims = service.decode_token(first_token, TokenType.ACCESS)
    second_claims = service.decode_token(second_token, TokenType.ACCESS)

    assert first_claims["jti"] != second_claims["jti"]


def test_jwt_service_accepts_secret_str() -> None:
    service = JwtService(SecretStr(JWT_SECRET))
    token = service.create_access_token(user_id=uuid4(), email=USER_EMAIL)

    assert service.decode_token(token, TokenType.ACCESS)["email"] == USER_EMAIL


def test_jwt_service_rejects_missing_secret() -> None:
    with pytest.raises(JwtConfigurationError):
        JwtService("")


def test_jwt_service_rejects_short_secret() -> None:
    with pytest.raises(JwtConfigurationError):
        JwtService("short-secret")
