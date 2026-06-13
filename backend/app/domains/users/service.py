from app.core.jwt import ACCESS_TOKEN_EXPIRE_MINUTES, JwtService
from app.core.security import PasswordPolicyError, SecurityService
from app.domains.users.exceptions import (
    AccountDisabledError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserRegistrationValidationError,
)
from app.domains.users.models import User, UserSettings
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import (
    LoginUserCommand,
    LoginUserResult,
    RegisterUserCommand,
    RegisterUserResult,
)

ACCESS_TOKEN_EXPIRES_IN_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60


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


class UserAuthenticationService:
    """Application service for user authentication."""

    def __init__(
        self,
        repository: UserRepository,
        security_service: SecurityService,
        jwt_service: JwtService,
    ) -> None:
        self._repository = repository
        self._security_service = security_service
        self._jwt_service = jwt_service

    def login_user(self, command: LoginUserCommand) -> LoginUserResult:
        """Authenticate a user and issue an access and refresh token pair."""
        email = command.email.strip().lower()
        user = self._repository.get_by_email(email)
        if user is None:
            raise InvalidCredentialsError()
        if not self._security_service.verify_password(
            command.password,
            user.password_hash,
        ):
            raise InvalidCredentialsError()
        if not user.is_active or user.deleted_at is not None:
            raise AccountDisabledError()

        token_pair = self._jwt_service.create_token_pair(
            user_id=user.id,
            email=user.email,
        )
        return LoginUserResult(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRES_IN_SECONDS,
        )
