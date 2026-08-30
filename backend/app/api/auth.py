from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlmodel import Session

from app.core.jwt import JwtService, get_jwt_service
from app.core.refresh_token import (
    RefreshTokenExpiredError,
    RefreshTokenInvalidError,
    RefreshTokenService,
    get_refresh_token_service,
)
from app.core.security import security_service
from app.db.session import get_session
from app.domains.access.mfa import MfaRequiredError, MfaService
from app.domains.access.sessions import SessionService
from app.domains.users.exceptions import (
    AccountDisabledError,
    InvalidCredentialsError,
    InvalidTokenApplicationError,
    TokenExpiredApplicationError,
)
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import LoginUserCommand, RegisterUserCommand
from app.domains.users.service import (
    UserAuthenticationService,
    UserRegistrationService,
)
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterUserRequest(BaseModel):
    """Request body for user registration."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: EmailStr) -> str:
        """Normalize emails before they enter the service layer."""
        return str(email).strip().lower()


class RegisterUserData(BaseModel):
    """Response data for user registration."""

    user_id: UUID


RegisterUserResponse = SuccessResponse[RegisterUserData]


class LoginUserRequest(BaseModel):
    """Request body for user login."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    mfa_code: str | None = Field(default=None, max_length=32)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: EmailStr) -> str:
        """Normalize emails before they enter the service layer."""
        return str(email).strip().lower()


class LoginUserData(BaseModel):
    """Response data for successful user login."""

    access_token: str
    refresh_token: str
    expires_in: int


LoginUserResponse = SuccessResponse[LoginUserData]


class LogoutRequest(BaseModel):
    """Request body for ending a session."""

    refresh_token: str = Field(min_length=1)
    everywhere: bool = False


class LogoutData(BaseModel):
    """Response data for a logout."""

    sessions_revoked: int


LogoutResponse = SuccessResponse[LogoutData]


class RefreshTokenRequest(BaseModel):
    """Request body for refreshing an access token."""

    refresh_token: str = Field(min_length=1)


class RefreshTokenData(BaseModel):
    """Response data for a refreshed access token."""

    access_token: str


RefreshTokenResponse = SuccessResponse[RefreshTokenData]


def get_registration_service(
    session: Annotated[Session, Depends(get_session)],
) -> UserRegistrationService:
    """Build the registration service dependency."""
    return UserRegistrationService(
        repository=UserRepository(session),
        security_service=security_service,
    )


def get_authentication_service(
    session: Annotated[Session, Depends(get_session)],
    jwt_service: Annotated[JwtService, Depends(get_jwt_service)],
) -> UserAuthenticationService:
    """Build the authentication service dependency."""
    return UserAuthenticationService(
        repository=UserRepository(session),
        security_service=security_service,
        jwt_service=jwt_service,
    )


@router.post(
    "/register",
    response_model=RegisterUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    request: RegisterUserRequest,
    registration_service: Annotated[
        UserRegistrationService,
        Depends(get_registration_service),
    ],
) -> RegisterUserResponse:
    """Register a platform user."""
    result = registration_service.register_user(
        RegisterUserCommand(
            email=request.email,
            password=request.password,
            display_name=request.display_name,
        )
    )
    return RegisterUserResponse(data=RegisterUserData(user_id=result.user_id))


@router.post("/login", response_model=LoginUserResponse)
def login_user(
    request: LoginUserRequest,
    http_request: Request,
    session: Annotated[Session, Depends(get_session)],
    authentication_service: Annotated[
        UserAuthenticationService,
        Depends(get_authentication_service),
    ],
) -> LoginUserResponse:
    """Authenticate a user and return JWT tokens."""
    result = authentication_service.login_user(
        LoginUserCommand(
            email=request.email,
            password=request.password,
        )
    )

    user = UserRepository(session).get_by_email(request.email)

    # The second factor is checked after the password, and before any token is
    # issued. Failing here returns nothing usable, so a correct password alone
    # never yields a session.
    if user is not None:
        mfa_service = MfaService(session)
        if mfa_service.is_enabled(user.id):
            if not request.mfa_code:
                raise MfaRequiredError()
            if not mfa_service.verify(user.id, request.mfa_code):
                raise InvalidCredentialsError()

    # Recorded so the refresh token can be revoked later. A JWT is
    # self-validating, so without this row a stolen token stays usable for its
    # full lifetime and "sign out everywhere" cannot work.
    if user is not None:
        SessionService(session).start(
            user_id=user.id,
            refresh_token=result.refresh_token,
            ip_address=_client_ip(http_request),
            user_agent=http_request.headers.get("User-Agent"),
        )

    return LoginUserResponse(
        data=LoginUserData(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            expires_in=result.expires_in,
        )
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
def refresh_access_token(
    request: RefreshTokenRequest,
    session: Annotated[Session, Depends(get_session)],
    jwt_service: Annotated[JwtService, Depends(get_jwt_service)],
    refresh_token_service: Annotated[
        RefreshTokenService,
        Depends(get_refresh_token_service),
    ],
) -> RefreshTokenResponse:
    """Validate a refresh token and issue a new access token."""
    try:
        result = refresh_token_service.refresh_access_token(request.refresh_token)
    except RefreshTokenExpiredError as exc:
        raise TokenExpiredApplicationError() from exc
    except RefreshTokenInvalidError as exc:
        raise InvalidTokenApplicationError() from exc

    # A revoked or expired session refuses the exchange even though the JWT
    # itself still verifies. That gap is the point of tracking sessions.
    if SessionService(session).validate(request.refresh_token) is None:
        raise InvalidTokenApplicationError()

    user = UserRepository(session).get_by_id(result.user_id)
    if user is None:
        raise InvalidTokenApplicationError()
    if not user.is_active or user.deleted_at is not None:
        raise AccountDisabledError()

    access_token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        role=result.role,
    )
    return RefreshTokenResponse(data=RefreshTokenData(access_token=access_token))


@router.post("/logout", response_model=LogoutResponse)
def logout_user(
    request: LogoutRequest,
    session: Annotated[Session, Depends(get_session)],
    refresh_token_service: Annotated[
        RefreshTokenService,
        Depends(get_refresh_token_service),
    ],
) -> LogoutResponse:
    """End a session, or every session for the user.

    Logout takes the refresh token rather than an access token, because the
    refresh token is what has a long life and therefore what actually needs
    revoking. An already-revoked or unknown token reports zero revocations
    rather than an error: logging out twice is not a failure, and reporting
    otherwise would tell an attacker which tokens are real.
    """
    session_service = SessionService(session)

    try:
        result = refresh_token_service.refresh_access_token(request.refresh_token)
    except (RefreshTokenExpiredError, RefreshTokenInvalidError):
        return LogoutResponse(data=LogoutData(sessions_revoked=0))

    if request.everywhere:
        revoked = session_service.revoke_all(result.user_id)
    else:
        revoked = 1 if session_service.revoke_by_token(request.refresh_token) else 0

    return LogoutResponse(data=LogoutData(sessions_revoked=revoked))


def _client_ip(request: Request) -> str | None:
    """Return the caller's address, honouring a proxy's forwarded header.

    Behind Nginx or a platform load balancer the socket address is the proxy,
    so the first entry of X-Forwarded-For is the real client.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host[:64] if request.client else None
