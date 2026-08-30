from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.domains.users.models import User
from app.domains.users.profile import (
    UNSET,
    UpdateProfileCommand,
    UserProfileService,
)
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/users", tags=["users"])


class CurrentUserData(BaseModel):
    """Response data for the authenticated user profile."""

    id: UUID
    email: str
    display_name: str
    timezone: str
    default_currency: str
    telegram_chat_id: str | None = None
    role: str = "USER"

    @classmethod
    def from_user(cls, user: User) -> "CurrentUserData":
        """Build the response payload from a user record."""
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            timezone=user.timezone,
            default_currency=user.default_currency,
            telegram_chat_id=user.telegram_chat_id,
            role=user.role,
        )


class UpdateCurrentUserRequest(BaseModel):
    """Request body for updating the authenticated user's profile.

    Email is not editable: it is the login identity and the address an
    ingestion key resolves against, so changing it needs a verification flow
    rather than a PATCH.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    display_name: str | None = Field(default=None, max_length=255)
    timezone: str | None = Field(default=None, max_length=100)
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    telegram_chat_id: str | None = Field(default=None, max_length=100)


CurrentUserResponse = SuccessResponse[CurrentUserData]


@router.get("/me", response_model=CurrentUserResponse)
def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> CurrentUserResponse:
    """Return the authenticated user's profile."""
    return CurrentUserResponse(data=CurrentUserData.from_user(current_user))


@router.patch("/me", response_model=CurrentUserResponse)
def update_current_user_profile(
    request: UpdateCurrentUserRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> CurrentUserResponse:
    """Update the authenticated user's own profile."""
    submitted = request.model_dump(exclude_unset=True)
    updated = UserProfileService(session).update_profile(
        UpdateProfileCommand(
            user_id=current_user.id,
            **{field: _submitted(submitted, field) for field in _PROFILE_FIELDS},
        )
    )
    return CurrentUserResponse(data=CurrentUserData.from_user(updated))


_PROFILE_FIELDS = (
    "display_name",
    "timezone",
    "default_currency",
    "telegram_chat_id",
)


def _submitted(submitted: dict[str, Any], field: str) -> Any:
    """Return the submitted value, or the sentinel when the field was omitted."""
    if field not in submitted:
        return UNSET
    return submitted[field]
