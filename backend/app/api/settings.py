"""User settings API."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.domains.users.models import User, UserSettings
from app.domains.users.profile import (
    UNSET,
    UpdateSettingsCommand,
    UserProfileService,
)
from app.shared.enums import NotificationMode
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsData(BaseModel):
    """Response data for a user's settings."""

    notification_mode: str
    ai_suggestions_enabled: bool
    preferred_language: str
    historical_import_mode: str | None = None

    @classmethod
    def from_settings(cls, settings: UserSettings) -> "SettingsData":
        """Build the response payload from a settings record."""
        return cls(
            notification_mode=settings.notification_mode,
            ai_suggestions_enabled=settings.ai_suggestions_enabled,
            preferred_language=settings.preferred_language,
            historical_import_mode=settings.historical_import_mode,
        )


class UpdateSettingsRequest(BaseModel):
    """Request body for updating user settings."""

    model_config = ConfigDict(str_strip_whitespace=True)

    notification_mode: NotificationMode | None = None
    ai_suggestions_enabled: bool | None = None
    preferred_language: str | None = Field(default=None, max_length=20)
    historical_import_mode: str | None = Field(default=None, max_length=50)


SettingsResponse = SuccessResponse[SettingsData]


def get_profile_service(
    session: Annotated[Session, Depends(get_session)],
) -> UserProfileService:
    """Build the profile service dependency."""
    return UserProfileService(session)


@router.get("", response_model=SettingsResponse)
def get_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[UserProfileService, Depends(get_profile_service)],
) -> SettingsResponse:
    """Return the authenticated user's settings."""
    settings = profile_service.get_settings(current_user.id)
    return SettingsResponse(data=SettingsData.from_settings(settings))


@router.patch("", response_model=SettingsResponse)
def update_settings(
    request: UpdateSettingsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[UserProfileService, Depends(get_profile_service)],
) -> SettingsResponse:
    """Update the authenticated user's settings."""
    submitted = request.model_dump(exclude_unset=True)
    settings = profile_service.update_settings(
        UpdateSettingsCommand(
            user_id=current_user.id,
            **{field: _submitted(submitted, field) for field in _SETTINGS_FIELDS},
        )
    )
    return SettingsResponse(data=SettingsData.from_settings(settings))


_SETTINGS_FIELDS = (
    "notification_mode",
    "ai_suggestions_enabled",
    "preferred_language",
    "historical_import_mode",
)


def _submitted(submitted: dict[str, Any], field: str) -> Any:
    if field not in submitted:
        return UNSET
    return submitted[field]
