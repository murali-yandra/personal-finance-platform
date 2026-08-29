from http import HTTPStatus

from app.shared.exceptions.base import ApplicationError


class TransactionNotFoundError(ApplicationError):
    """Raised when a transaction is missing or owned by another user."""

    def __init__(self) -> None:
        super().__init__(
            code="TRANSACTION_NOT_FOUND",
            message="Transaction not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )


class DuplicateTransactionError(ApplicationError):
    """Raised when a transaction fingerprint already exists for the user."""

    def __init__(self, existing_transaction_id: str | None = None) -> None:
        super().__init__(
            code="DUPLICATE_TRANSACTION",
            message="A matching transaction already exists.",
            status_code=HTTPStatus.CONFLICT,
        )
        self.existing_transaction_id = existing_transaction_id


class TransactionValidationError(ApplicationError):
    """Raised when transaction input violates a business rule."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
        )


class InvalidAmountError(ApplicationError):
    """Raised when an amount is not a usable monetary value."""

    def __init__(self, message: str = "Amount must be a non-negative number.") -> None:
        super().__init__(
            code="INVALID_AMOUNT",
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
        )


class MissingAccountError(ApplicationError):
    """Raised when the referenced account does not belong to the user."""

    def __init__(self) -> None:
        super().__init__(
            code="ACCOUNT_NOT_FOUND",
            message="Account not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )
