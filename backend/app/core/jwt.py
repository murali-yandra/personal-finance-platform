from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from pydantic import SecretStr

from app.config import get_settings

JWT_ALGORITHM = "HS256"
JWT_SECRET_MIN_LENGTH_BYTES = 32
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
DEFAULT_USER_ROLE = "USER"
TOKEN_TYPE_BEARER = "bearer"
REQUIRED_CLAIMS = [
    "sub",
    "user_id",
    "email",
    "role",
    "iat",
    "exp",
    "jti",
    "token_type",
]

Clock = Callable[[], datetime]


class TokenType(StrEnum):
    """Supported JWT token types."""

    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True)
class TokenPair:
    """JWT access and refresh token response payload."""

    access_token: str
    refresh_token: str
    token_type: str = TOKEN_TYPE_BEARER


class JwtConfigurationError(ValueError):
    """Raised when JWT service configuration is invalid."""


class JwtTokenError(ValueError):
    """Base exception for JWT token validation failures."""


class JwtTokenExpiredError(JwtTokenError):
    """Raised when a JWT has expired."""


class JwtTokenInvalidError(JwtTokenError):
    """Raised when a JWT cannot be validated."""


class JwtTokenTypeError(JwtTokenError):
    """Raised when a JWT is valid but has the wrong token type."""


class JwtService:
    """Creates and validates JWT access and refresh tokens."""

    def __init__(
        self,
        secret: SecretStr | str,
        algorithm: str = JWT_ALGORITHM,
        access_token_lifetime: timedelta = timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
        refresh_token_lifetime: timedelta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        clock: Clock | None = None,
    ) -> None:
        self._secret = self._normalize_secret(secret)
        self._algorithm = algorithm
        self._access_token_lifetime = access_token_lifetime
        self._refresh_token_lifetime = refresh_token_lifetime
        self._clock = clock or (lambda: datetime.now(UTC))

    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        role: str = DEFAULT_USER_ROLE,
    ) -> str:
        """Create a short-lived JWT access token."""
        return self._create_token(
            user_id=user_id,
            email=email,
            role=role,
            token_type=TokenType.ACCESS,
            lifetime=self._access_token_lifetime,
        )

    def create_refresh_token(
        self,
        user_id: UUID,
        email: str,
        role: str = DEFAULT_USER_ROLE,
    ) -> str:
        """Create a long-lived JWT refresh token."""
        return self._create_token(
            user_id=user_id,
            email=email,
            role=role,
            token_type=TokenType.REFRESH,
            lifetime=self._refresh_token_lifetime,
        )

    def create_token_pair(
        self,
        user_id: UUID,
        email: str,
        role: str = DEFAULT_USER_ROLE,
    ) -> TokenPair:
        """Create an access and refresh token pair."""
        return TokenPair(
            access_token=self.create_access_token(user_id, email, role),
            refresh_token=self.create_refresh_token(user_id, email, role),
        )

    def decode_token(
        self,
        token: str,
        expected_token_type: TokenType | None = None,
    ) -> dict[str, Any]:
        """Validate and decode a JWT."""
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": REQUIRED_CLAIMS},
            )
        except ExpiredSignatureError as exc:
            raise JwtTokenExpiredError("JWT token has expired.") from exc
        except InvalidTokenError as exc:
            raise JwtTokenInvalidError("JWT token is invalid.") from exc

        if (
            expected_token_type is not None
            and claims.get("token_type") != expected_token_type.value
        ):
            raise JwtTokenTypeError("JWT token type does not match expected type.")

        return claims

    def _create_token(
        self,
        user_id: UUID,
        email: str,
        role: str,
        token_type: TokenType,
        lifetime: timedelta,
    ) -> str:
        issued_at = self._now()
        expires_at = issued_at + lifetime
        user_id_value = str(user_id)
        claims = {
            "sub": user_id_value,
            "user_id": user_id_value,
            "email": email,
            "role": role,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": str(uuid4()),
            "token_type": token_type.value,
        }
        return jwt.encode(claims, self._secret, algorithm=self._algorithm)

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            return now.replace(tzinfo=UTC)
        return now.astimezone(UTC)

    @staticmethod
    def _normalize_secret(secret: SecretStr | str) -> str:
        secret_value = (
            secret.get_secret_value() if isinstance(secret, SecretStr) else secret
        )
        if not secret_value:
            raise JwtConfigurationError("JWT secret must be configured.")
        if len(secret_value.encode("utf-8")) < JWT_SECRET_MIN_LENGTH_BYTES:
            raise JwtConfigurationError("JWT secret must be at least 32 bytes long.")
        return secret_value


def get_jwt_service() -> JwtService:
    """Create a JWT service from environment-backed settings."""
    settings = get_settings()
    return JwtService(settings.jwt_secret)
