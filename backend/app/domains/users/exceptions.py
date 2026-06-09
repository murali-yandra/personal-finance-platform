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
