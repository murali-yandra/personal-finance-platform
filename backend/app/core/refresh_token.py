from dataclasses import dataclass
from uuid import UUID

from app.core.jwt import (
    JwtService,
    JwtTokenExpiredError,
    JwtTokenInvalidError,
    JwtTokenTypeError,
    TokenType,
    get_jwt_service,
)


@dataclass(frozen=True)
class RefreshTokenResult:
    """Validated refresh token claims used to issue a new access token."""

    user_id: UUID
    email: str
    role: str


class RefreshTokenError(ValueError):
    """Base exception for refresh token failures."""


class RefreshTokenExpiredError(RefreshTokenError):
    """Raised when a refresh token has expired."""


class RefreshTokenInvalidError(RefreshTokenError):
    """Raised when a refresh token is invalid or malformed."""


class RefreshTokenService:
    """Validates refresh tokens before access-token issuance."""

    def __init__(self, jwt_service: JwtService) -> None:
        self._jwt_service = jwt_service

    def refresh_access_token(self, refresh_token: str) -> RefreshTokenResult:
        """Validate a refresh token and return trusted token claims."""
        claims = self._decode_refresh_token(refresh_token)
        user_id, email, role = self._extract_refresh_claims(claims)
        return RefreshTokenResult(user_id=user_id, email=email, role=role)

    def _decode_refresh_token(self, refresh_token: str) -> dict[str, object]:
        try:
            return self._jwt_service.decode_token(
                refresh_token,
                expected_token_type=TokenType.REFRESH,
            )
        except JwtTokenExpiredError as exc:
            raise RefreshTokenExpiredError("Refresh token has expired.") from exc
        except (JwtTokenInvalidError, JwtTokenTypeError) as exc:
            raise RefreshTokenInvalidError("Refresh token is invalid.") from exc

    @staticmethod
    def _extract_refresh_claims(claims: dict[str, object]) -> tuple[UUID, str, str]:
        user_id_claim = claims.get("user_id")
        subject_claim = claims.get("sub")
        email_claim = claims.get("email")
        role_claim = claims.get("role")

        if not isinstance(user_id_claim, str) or not user_id_claim:
            raise RefreshTokenInvalidError("Refresh token user id is invalid.")
        if subject_claim != user_id_claim:
            raise RefreshTokenInvalidError(
                "Refresh token subject does not match user id."
            )
        if not isinstance(email_claim, str) or not email_claim:
            raise RefreshTokenInvalidError("Refresh token email is invalid.")
        if not isinstance(role_claim, str) or not role_claim:
            raise RefreshTokenInvalidError("Refresh token role is invalid.")

        try:
            user_id = UUID(user_id_claim)
        except ValueError as exc:
            raise RefreshTokenInvalidError("Refresh token user id is invalid.") from exc

        return user_id, email_claim, role_claim


def get_refresh_token_service() -> RefreshTokenService:
    """Create a refresh token service from environment-backed settings."""
    return RefreshTokenService(get_jwt_service())
