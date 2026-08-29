"""Request id propagation.

Binds a request id and correlation id for the lifetime of each request and
echoes them on the response, so a client-visible error can be joined to the log
lines and audit rows it produced.

A caller-supplied correlation id is honoured, which is what lets one id span the
SMS ingestion request, the transaction it creates and the notification it sends.
"""

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import (
    clear_request_context,
    new_request_id,
    set_request_context,
)

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Binds request and correlation ids for the duration of a request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Bind the ids, handle the request, then echo them on the response."""
        request_id = _valid_uuid(request.headers.get(REQUEST_ID_HEADER))
        correlation_id = (
            _valid_uuid(request.headers.get(CORRELATION_ID_HEADER)) or request_id
        )

        set_request_context(request_id=request_id, correlation_id=correlation_id)
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)
        finally:
            clear_request_context()

        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response


def _valid_uuid(raw: str | None) -> str:
    """Return the supplied id if it is a UUID, otherwise a fresh one.

    A client-supplied value is echoed into logs and audit rows, so it is checked
    rather than trusted: an arbitrary string would let a caller inject content
    into the log stream.
    """
    if not raw:
        return new_request_id()
    try:
        return str(UUID(raw))
    except ValueError:
        return new_request_id()
