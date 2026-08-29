from http import HTTPStatus

from app.shared.exceptions.base import ApplicationError


class DuplicateAccountIdentityError(ApplicationError):
    """Raised when a user already has the same account identity."""

    def __init__(self) -> None:
        super().__init__(
            code="ACCOUNT_ALREADY_EXISTS",
            message="An account with these details already exists.",
            status_code=HTTPStatus.CONFLICT,
        )


class AccountNotFoundError(ApplicationError):
    """Raised when an account does not exist for the requesting user."""

    def __init__(self) -> None:
        super().__init__(
            code="ACCOUNT_NOT_FOUND",
            message="Account not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )


class AccountValidationError(ApplicationError):
    """Raised when account input violates account business rules."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
        )
