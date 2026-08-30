"""Login session management."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlmodel import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.domains.access.models import UserSession
from app.domains.access.sessions import SessionService
from app.domains.users.models import User
from app.shared.exceptions.base import ApplicationError
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionNotFoundError(ApplicationError):
    """Raised when a session is missing or owned by another user."""

    def __init__(self) -> None:
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message="Session not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class SessionData(BaseModel):
    """Response data for one login session. Never carries the token."""

    id: UUID
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    last_seen_at: datetime | None
    expires_at: datetime | None

    @classmethod
    def from_session(cls, record: UserSession) -> "SessionData":
        """Build the response payload from a session record."""
        return cls(
            id=record.id,
            ip_address=record.ip_address,
            user_agent=record.user_agent,
            created_at=record.created_at,
            last_seen_at=record.last_seen_at,
            expires_at=record.expires_at,
        )


class RevokeAllData(BaseModel):
    """Response data for revoking every session."""

    sessions_revoked: int


SessionListResponse = SuccessResponse[list[SessionData]]
SessionResponse = SuccessResponse[SessionData]
RevokeAllResponse = SuccessResponse[RevokeAllData]


def get_session_service(
    session: Annotated[Session, Depends(get_session)],
) -> SessionService:
    """Build the session service dependency."""
    return SessionService(session)


@router.get("", response_model=SessionListResponse)
def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionListResponse:
    """List the caller's active sessions.

    Showing address and user agent is what lets someone recognise a login they
    did not make, which is the point of surfacing sessions at all.
    """
    return SessionListResponse(
        data=[
            SessionData.from_session(record)
            for record in service.list_sessions(current_user.id)
        ]
    )


@router.delete("", response_model=RevokeAllResponse)
def revoke_all_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SessionService, Depends(get_session_service)],
) -> RevokeAllResponse:
    """Sign out of every session."""
    return RevokeAllResponse(
        data=RevokeAllData(sessions_revoked=service.revoke_all(current_user.id))
    )


@router.delete("/{session_id}", response_model=SessionResponse)
def revoke_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    """Revoke one of the caller's sessions."""
    revoked = service.revoke(user_id=current_user.id, session_id=session_id)
    if revoked is None:
        raise SessionNotFoundError()
    return SessionResponse(data=SessionData.from_session(revoked))
