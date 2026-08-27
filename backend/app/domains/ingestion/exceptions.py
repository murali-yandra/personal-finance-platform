from http import HTTPStatus

from app.shared.exceptions.base import ApplicationError


class InvalidApiKeyError(ApplicationError):
    """Raised when the ingestion API key is missing or wrong."""

    def __init__(self) -> None:
        super().__init__(
            code="INVALID_TOKEN",
            message="Invalid API key.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )


class IngestionUserNotConfiguredError(ApplicationError):
    """Raised when no user is configured to own ingested messages.

    The ingestion endpoint authenticates with a shared key rather than a JWT, so
    the owning user comes from configuration until per-user API keys arrive in
    Sprint 15.
    """

    def __init__(self) -> None:
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message="Ingestion is not configured.",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        )


class InvalidSmsPayloadError(ApplicationError):
    """Raised when an SMS payload cannot be accepted."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
        )
