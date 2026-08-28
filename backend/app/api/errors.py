import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.context import correlation_id_var, request_id_var
from app.shared.exceptions.base import ApplicationError
from app.shared.schemas.responses import (
    ErrorResponse,
    ErrorResponseDetail,
    ValidationErrorDetail,
)

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"
UNEXPECTED_ERROR_MESSAGE = "An unexpected error occurred."

logger = logging.getLogger(__name__)


def register_exception_handlers(application: FastAPI) -> None:
    """Register API exception handlers."""

    @application.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        return _error_response(
            request=request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
        )

    @application.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(
            request=request,
            status_code=400,
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            details=_validation_error_details(exc),
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.error(
            "Unhandled API exception",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return _error_response(
            request=request,
            status_code=500,
            code="UNEXPECTED_ERROR",
            message=UNEXPECTED_ERROR_MESSAGE,
        )


def _validation_error_details(
    exc: RequestValidationError,
) -> list[ValidationErrorDetail]:
    details: list[ValidationErrorDetail] = []
    for error in exc.errors():
        location = error.get("loc", ())
        field_parts = [
            str(part)
            for part in location
            if part not in {"body", "query", "path", "header"}
        ]
        details.append(
            ValidationErrorDetail(
                field=".".join(field_parts) or "request",
                message=str(error.get("msg", "Invalid value.")),
            )
        )
    return details


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[ValidationErrorDetail] | None = None,
) -> JSONResponse:
    # Prefer the ids the request-context middleware bound: they are validated
    # UUIDs and are the ones the log lines carry.
    request_id = (
        request_id_var.get()
        or getattr(request.state, "request_id", None)
        or request.headers.get(REQUEST_ID_HEADER)
        or str(uuid4())
    )
    correlation_id = (
        correlation_id_var.get()
        or getattr(request.state, "correlation_id", None)
        or request.headers.get(CORRELATION_ID_HEADER)
        or request_id
    )
    payload = ErrorResponse(
        error=ErrorResponseDetail(
            code=code,
            message=message,
            request_id=request_id,
            correlation_id=correlation_id,
            details=details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(exclude_none=True),
    )
