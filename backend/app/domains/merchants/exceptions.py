from http import HTTPStatus

from app.shared.exceptions.base import ApplicationError


class MerchantNotFoundError(ApplicationError):
    """Raised when a merchant does not exist."""

    def __init__(self) -> None:
        super().__init__(
            code="MERCHANT_NOT_FOUND",
            message="Merchant not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )


class MerchantPatternValidationError(ApplicationError):
    """Raised when a merchant pattern is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
        )
