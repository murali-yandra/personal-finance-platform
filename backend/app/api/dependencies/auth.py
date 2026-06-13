from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlmodel import Session

from app.core.jwt import (
    JwtService,
    JwtTokenExpiredError,
    JwtTokenInvalidError,
    JwtTokenTypeError,
    TokenType,
    get_jwt_service,
)
from app.db.session import get_session
from app.domains.users.exceptions import (
    AccountDisabledError,
    InvalidTokenApplicationError,
    TokenExpiredApplicationError,
)
from app.domains.users.models import User
from app.domains.users.repository import UserRepository

BEARER_SCHEME = "bearer"


def get_current_user(
    session: Annotated[Session, Depends(get_session)],
    jwt_service: Annotated[JwtService, Depends(get_jwt_service)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Return the authenticated user for a valid JWT access token."""
    token = _extract_bearer_token(authorization)
    claims = _decode_access_token(jwt_service, token)
    user_id = _extract_user_id(claims)

    user = UserRepository(session).get_by_id(user_id)
    if user is None:
        raise InvalidTokenApplicationError()
    if not user.is_active or user.deleted_at is not None:
        raise AccountDisabledError()

    return user


def _extract_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise InvalidTokenApplicationError()

    parts = authorization.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != BEARER_SCHEME:
        raise InvalidTokenApplicationError()

    token = parts[1].strip()
    if not token:
        raise InvalidTokenApplicationError()
    return token


def _decode_access_token(
    jwt_service: JwtService,
    token: str,
) -> dict[str, object]:
    try:
        return jwt_service.decode_token(token, expected_token_type=TokenType.ACCESS)
    except JwtTokenExpiredError as exc:
        raise TokenExpiredApplicationError() from exc
    except (JwtTokenInvalidError, JwtTokenTypeError) as exc:
        raise InvalidTokenApplicationError() from exc


def _extract_user_id(claims: dict[str, object]) -> UUID:
    user_id_claim = claims.get("user_id")
    subject_claim = claims.get("sub")
    if not isinstance(user_id_claim, str) or subject_claim != user_id_claim:
        raise InvalidTokenApplicationError()

    try:
        return UUID(user_id_claim)
    except ValueError as exc:
        raise InvalidTokenApplicationError() from exc
