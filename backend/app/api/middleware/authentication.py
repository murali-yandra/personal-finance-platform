from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager
from http import HTTPStatus
from uuid import UUID, uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlmodel import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.jwt import (
    JwtService,
    JwtTokenExpiredError,
    JwtTokenInvalidError,
    JwtTokenTypeError,
    TokenType,
    get_jwt_service,
)
from app.db.session import engine
from app.domains.users.models import User
from app.domains.users.repository import UserRepository
from app.shared.schemas.responses import ErrorResponse, ErrorResponseDetail

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"
AUTHORIZATION_HEADER = "Authorization"
BEARER_SCHEME = "bearer"

PUBLIC_PATHS = {
    "/health",
    "/health/ready",
    "/api/v1/health",
    "/api/v1/health/ready",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    # Authenticated by X-API-KEY instead of a JWT, so the bearer-token
    # middleware must not reject the request before the key is checked.
    "/api/v1/ingest/sms",
}
PROTECTED_PREFIX = "/api/v1"

JwtServiceFactory = Callable[[], JwtService]
SessionFactory = Callable[[], AbstractContextManager[Session]]


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Validate JWT access tokens for protected API paths."""

    def __init__(
        self,
        app,
        jwt_service_factory: JwtServiceFactory = get_jwt_service,
    ) -> None:
        super().__init__(app)
        self._jwt_service_factory = jwt_service_factory

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Authenticate protected API requests before route handling."""
        if _is_public_request(request):
            return await call_next(request)

        token = _extract_bearer_token(request.headers.get(AUTHORIZATION_HEADER))
        if token is None:
            return _authentication_error_response(request, "INVALID_TOKEN")

        jwt_service = _jwt_service_factory(request, self._jwt_service_factory)()
        try:
            claims = jwt_service.decode_token(
                token,
                expected_token_type=TokenType.ACCESS,
            )
        except JwtTokenExpiredError:
            return _authentication_error_response(request, "TOKEN_EXPIRED")
        except (JwtTokenInvalidError, JwtTokenTypeError):
            return _authentication_error_response(request, "INVALID_TOKEN")

        user_id = _extract_user_id(claims)
        if user_id is None:
            return _authentication_error_response(request, "INVALID_TOKEN")

        with _session_factory(request)() as session:
            user = UserRepository(session).get_by_id(user_id)
            if user is None:
                return _authentication_error_response(request, "INVALID_TOKEN")
            if not user.is_active or user.deleted_at is not None:
                return _authentication_error_response(request, "ACCOUNT_DISABLED")

            _attach_current_user(request, user)
            return await call_next(request)


def _is_public_request(request: Request) -> bool:
    if request.method == "OPTIONS":
        return True
    path = request.url.path.rstrip("/") or "/"
    is_protected_api_path = path == PROTECTED_PREFIX or path.startswith(
        f"{PROTECTED_PREFIX}/"
    )
    return not is_protected_api_path or path in PUBLIC_PATHS


def _jwt_service_factory(
    request: Request,
    default_factory: JwtServiceFactory,
) -> JwtServiceFactory:
    return getattr(request.app.state, "auth_jwt_service_factory", default_factory)


def _session_factory(request: Request) -> SessionFactory:
    return getattr(
        request.app.state,
        "auth_session_factory",
        lambda: Session(engine),
    )


def _extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != BEARER_SCHEME:
        return None
    return parts[1]


def _extract_user_id(claims: dict[str, object]) -> UUID | None:
    user_id_claim = claims.get("user_id")
    subject_claim = claims.get("sub")
    if not isinstance(user_id_claim, str) or subject_claim != user_id_claim:
        return None

    try:
        return UUID(user_id_claim)
    except ValueError:
        return None


def _attach_current_user(request: Request, user: User) -> None:
    request.state.current_user = user
    request.state.current_user_id = user.id


def _authentication_error_response(request: Request, code: str) -> JSONResponse:
    message = _error_message(code)
    request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid4()))
    correlation_id = request.headers.get(CORRELATION_ID_HEADER, request_id)
    payload = ErrorResponse(
        error=ErrorResponseDetail(
            code=code,
            message=message,
            request_id=request_id,
            correlation_id=correlation_id,
        )
    )
    return JSONResponse(
        status_code=HTTPStatus.UNAUTHORIZED,
        content=payload.model_dump(exclude_none=True),
    )


def _error_message(code: str) -> str:
    if code == "TOKEN_EXPIRED":
        return "Your session has expired."
    if code == "ACCOUNT_DISABLED":
        return "Account is disabled."
    return "Invalid authentication token."
