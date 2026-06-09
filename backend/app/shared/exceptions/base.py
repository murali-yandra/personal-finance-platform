from http import HTTPStatus


class ApplicationError(Exception):
    """Base exception for errors that are safe to return through the API."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = HTTPStatus.BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
