from app.core.security import PasswordPolicyError, SecurityService
from app.domains.users.exceptions import (
    UserAlreadyExistsError,
    UserRegistrationValidationError,
)
from app.domains.users.models import User, UserSettings
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import RegisterUserCommand, RegisterUserResult


class UserRegistrationService:
    """Application service for user registration."""

    def __init__(
        self,
        repository: UserRepository,
        security_service: SecurityService,
    ) -> None:
        self._repository = repository
        self._security_service = security_service

    def register_user(self, command: RegisterUserCommand) -> RegisterUserResult:
        """Register a user and create default user settings."""
        email = self._normalize_email(command.email)
        display_name = command.display_name.strip()
        if not display_name:
            raise UserRegistrationValidationError("Display name is required.")

        if self._repository.get_by_email(email) is not None:
            raise UserAlreadyExistsError()

        try:
            password_hash = self._security_service.hash_password(command.password)
            user = User(
                email=email,
                password_hash=password_hash,
                display_name=display_name,
            )
            settings = UserSettings(user_id=user.id)

            self._repository.add_user_with_settings(user, settings)
            self._repository.commit()
        except PasswordPolicyError as exc:
            self._repository.rollback()
            raise UserRegistrationValidationError(str(exc)) from exc
        except Exception:
            self._repository.rollback()
            raise

        return RegisterUserResult(user_id=user.id)

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()
