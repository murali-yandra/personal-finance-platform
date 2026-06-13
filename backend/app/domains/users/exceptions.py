from http import HTTPStatus

from app.shared.exceptions.base import ApplicationError


class UserAlreadyExistsError(ApplicationError):
    """Raised when attempting to register an email that already exists."""

    def __init__(self) -> None:
        super().__init__(
            code="USER_ALREADY_EXISTS",
            message="A user with this email already exists.",
            status_code=HTTPStatus.CONFLICT,
        )


class UserRegistrationValidationError(ApplicationError):
    """Raised when registration input violates user rules."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
        )


class InvalidCredentialsError(ApplicationError):
    """Raised when login credentials cannot be authenticated."""

    def __init__(self) -> None:
        super().__init__(
            code="INVALID_CREDENTIALS",
            message="Invalid email or password.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )


class InvalidTokenApplicationError(ApplicationError):
    """Raised when a submitted JWT cannot be validated."""

    def __init__(self) -> None:
        super().__init__(
            code="INVALID_TOKEN",
            message="Invalid authentication token.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )


class TokenExpiredApplicationError(ApplicationError):
    """Raised when a submitted JWT has expired."""

    def __init__(self) -> None:
        super().__init__(
            code="TOKEN_EXPIRED",
            message="Your session has expired.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )


class AccountDisabledError(ApplicationError):
    """Raised when a disabled account attempts to access the API."""

    def __init__(self) -> None:
        super().__init__(
            code="ACCOUNT_DISABLED",
            message="Account is disabled.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )
