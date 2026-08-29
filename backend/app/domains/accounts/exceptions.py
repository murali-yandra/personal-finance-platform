from http import HTTPStatus

from app.shared.exceptions.base import ApplicationError


class AccountNotFoundError(ApplicationError):
    """Raised when an account does not exist or is not owned by the caller.

    Cross-user access deliberately produces the same response as a missing record
    so the API cannot be used to probe for other users' account IDs
    (``10-security_standards.md`` section 6).
    """

    def __init__(self) -> None:
        super().__init__(
            code="ACCOUNT_NOT_FOUND",
            message="Account not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )


class AccountAlreadyExistsError(ApplicationError):
    """Raised when an account duplicates an existing one for the same user."""

    def __init__(self) -> None:
        super().__init__(
            code="ACCOUNT_ALREADY_EXISTS",
            message=(
                "An account with this bank, last four digits and type "
                "already exists."
            ),
            status_code=HTTPStatus.CONFLICT,
        )


class InvalidAccountTypeError(ApplicationError):
    """Raised when an unsupported account type is supplied."""

    def __init__(self, account_type: str) -> None:
        super().__init__(
            code="INVALID_ACCOUNT_TYPE",
            message=f"Unsupported account type: {account_type}.",
            status_code=HTTPStatus.BAD_REQUEST,
        )


class AccountValidationError(ApplicationError):
    """Raised when account input violates a business rule."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
        )


class InvalidAccountStatusTransitionError(ApplicationError):
    """Raised when a status change is not permitted from the current status."""

    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=(
                f"An account cannot move from {current_status} to {target_status}."
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        )


class ArchivedAccountImmutableError(ApplicationError):
    """Raised when a caller tries to modify an archived account."""

    def __init__(self) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message="An archived account cannot be modified.",
            status_code=HTTPStatus.BAD_REQUEST,
        )
