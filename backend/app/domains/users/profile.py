"""User profile and settings management.

Both live in one service because they are edited from the same screens and
share the same ownership rule: a user may read and write only their own.
"""

import re
from dataclasses import dataclass
from http import HTTPStatus
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session, select

from app.domains.users.models import User, UserSettings
from app.shared.enums import NotificationMode
from app.shared.exceptions.base import ApplicationError

CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
LANGUAGE_PATTERN = re.compile(r"^[A-Za-z]{2}(?:-[A-Za-z]{2})?$")
TELEGRAM_CHAT_ID_PATTERN = re.compile(r"^-?\d{1,32}$")

UNSET = object()


class ProfileValidationError(ApplicationError):
    """Raised when profile or settings input is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
        )


class SettingsNotFoundError(ApplicationError):
    """Raised when a user has no settings row."""

    def __init__(self) -> None:
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message="User settings not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )


@dataclass(frozen=True)
class UpdateProfileCommand:
    """Service input for updating a user profile.

    Fields default to ``UNSET`` so an omitted field is distinguishable from an
    explicit ``null``, matching the PATCH semantics used elsewhere.
    """

    user_id: UUID
    display_name: object = UNSET
    timezone: object = UNSET
    default_currency: object = UNSET
    telegram_chat_id: object = UNSET


@dataclass(frozen=True)
class UpdateSettingsCommand:
    """Service input for updating user settings."""

    user_id: UUID
    notification_mode: object = UNSET
    ai_suggestions_enabled: object = UNSET
    preferred_language: object = UNSET
    historical_import_mode: object = UNSET


class UserProfileService:
    """Reads and updates a user's own profile and settings."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_settings(self, user_id: UUID) -> UserSettings:
        """Return the user's settings row."""
        statement = select(UserSettings).where(UserSettings.user_id == user_id)
        settings = self._session.exec(statement).first()
        if settings is None:
            raise SettingsNotFoundError()
        return settings

    def update_profile(self, command: UpdateProfileCommand) -> User:
        """Update the caller's own profile.

        Email is deliberately not editable here. Changing it would move the
        login identity and, with it, which messages an ingestion key resolves
        to, so it needs a verification flow rather than a PATCH.
        """
        user = self._session.get(User, command.user_id)
        if user is None:
            raise ProfileValidationError("User not found.")

        if command.display_name is not UNSET:
            user.display_name = _validate_display_name(command.display_name)
        if command.timezone is not UNSET:
            user.timezone = _validate_timezone(command.timezone)
        if command.default_currency is not UNSET:
            user.default_currency = _validate_currency(command.default_currency)
        if command.telegram_chat_id is not UNSET:
            user.telegram_chat_id = _validate_chat_id(command.telegram_chat_id)

        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user

    def update_settings(self, command: UpdateSettingsCommand) -> UserSettings:
        """Update the caller's own settings."""
        settings = self.get_settings(command.user_id)

        if command.notification_mode is not UNSET:
            settings.notification_mode = _validate_notification_mode(
                command.notification_mode
            )
        if command.ai_suggestions_enabled is not UNSET:
            settings.ai_suggestions_enabled = bool(command.ai_suggestions_enabled)
        if command.preferred_language is not UNSET:
            settings.preferred_language = _validate_language(command.preferred_language)
        if command.historical_import_mode is not UNSET:
            value = command.historical_import_mode
            settings.historical_import_mode = (
                str(value).strip()[:50] if value is not None else None
            )

        self._session.add(settings)
        self._session.commit()
        self._session.refresh(settings)
        return settings


def _validate_display_name(value: object) -> str:
    name = str(value or "").strip()
    if not name:
        raise ProfileValidationError("Display name is required.")
    if len(name) > 255:
        raise ProfileValidationError("Display name exceeds 255 characters.")
    return name


def _validate_timezone(value: object) -> str:
    name = str(value or "").strip()
    if not name:
        raise ProfileValidationError("Timezone is required.")
    try:
        # Validated against the real tz database: an unknown zone would make
        # every date-bounded report silently wrong for this user.
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ProfileValidationError(f"Unknown timezone: {name}.") from exc
    return name


def _validate_currency(value: object) -> str:
    currency = str(value or "").strip().upper()
    if not CURRENCY_PATTERN.match(currency):
        raise ProfileValidationError("Currency must be a three-letter ISO 4217 code.")
    return currency


def _validate_language(value: object) -> str:
    language = str(value or "").strip()
    if not LANGUAGE_PATTERN.match(language):
        raise ProfileValidationError("Language must be an ISO 639-1 code.")
    return language


def _validate_chat_id(value: object) -> str | None:
    """Validate a Telegram chat id, allowing it to be cleared with null."""
    if value is None:
        return None
    chat_id = str(value).strip()
    if not chat_id:
        return None
    if not TELEGRAM_CHAT_ID_PATTERN.match(chat_id):
        # Group chat ids are negative, hence the optional leading minus.
        raise ProfileValidationError("Telegram chat id must be numeric.")
    return chat_id


def _validate_notification_mode(value: object) -> str:
    if isinstance(value, NotificationMode):
        return value.value
    try:
        return NotificationMode(str(value).strip().upper()).value
    except ValueError as exc:
        raise ProfileValidationError(
            f"Unsupported notification mode: {value}."
        ) from exc
