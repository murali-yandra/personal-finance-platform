from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.domains.users.models import User
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/users", tags=["users"])


class CurrentUserData(BaseModel):
    """Response data for the authenticated user profile."""

    id: UUID
    email: str
    display_name: str
    timezone: str
    default_currency: str


CurrentUserResponse = SuccessResponse[CurrentUserData]


@router.get("/me", response_model=CurrentUserResponse)
def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> CurrentUserResponse:
    """Return the authenticated user's profile."""
    return CurrentUserResponse(
        data=CurrentUserData(
            id=current_user.id,
            email=current_user.email,
            display_name=current_user.display_name,
            timezone=current_user.timezone,
            default_currency=current_user.default_currency,
        )
    )
