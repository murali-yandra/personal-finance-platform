from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.shared.exceptions.base import ApplicationError
from app.shared.schemas.responses import ErrorResponse, ErrorResponseDetail

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


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
        )


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid4()))
    correlation_id = request.headers.get(CORRELATION_ID_HEADER, request_id)
    payload = ErrorResponse(
        error=ErrorResponseDetail(
            code=code,
            message=message,
            request_id=request_id,
            correlation_id=correlation_id,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
    )
