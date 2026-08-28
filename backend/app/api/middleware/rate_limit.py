"""Per-caller rate limiting.

Keyed by authenticated user when one is known, and by client address otherwise,
so one user's burst cannot exhaust another's allowance.
"""

import logging
from collections.abc import Awaitable, Callable
from http import HTTPStatus

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import request_id_var
from app.core.rate_limit import RateLimiter
from app.shared.schemas.responses import ErrorResponse, ErrorResponseDetail

logger = logging.getLogger(__name__)

# Liveness probes must never be throttled, or a burst of user traffic would make
# the platform look unhealthy and trigger a restart.
EXEMPT_PATHS = frozenset(
    {
        "/health",
        "/health/ready",
        "/api/v1/health",
        "/api/v1/health/ready",
    }
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rejects a caller that exceeds the configured request rate."""

    def __init__(self, app, limiter: RateLimiter | None = None) -> None:
        super().__init__(app)
        self._limiter = limiter or RateLimiter()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Count the request and either serve or reject it."""
        path = request.url.path.rstrip("/") or "/"
        if path in EXEMPT_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        decision = self._limiter.check(_rate_limit_key(request))

        if not decision.allowed:
            logger.warning("Rate limit exceeded for %s", request.url.path)
            return _rate_limited_response(decision.retry_after_seconds)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(decision.limit)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        return response


def _rate_limit_key(request: Request) -> str:
    """Key by user where known, else by client address."""
    user_id = getattr(request.state, "current_user_id", None)
    if user_id is not None:
        return f"user:{user_id}"

    api_key = request.headers.get("X-API-KEY")
    if api_key:
        # Key on a short digest, never the key itself: this value is held in
        # memory and appears in diagnostics.
        from hashlib import sha256

        return f"apikey:{sha256(api_key.encode()).hexdigest()[:16]}"

    client = request.client
    return f"ip:{client.host}" if client else "ip:unknown"


def _rate_limited_response(retry_after: int) -> JSONResponse:
    request_id = request_id_var.get() or "unknown"
    payload = ErrorResponse(
        error=ErrorResponseDetail(
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests. Please retry shortly.",
            request_id=request_id,
            correlation_id=request_id,
        )
    )
    return JSONResponse(
        status_code=HTTPStatus.TOO_MANY_REQUESTS,
        content=payload.model_dump(exclude_none=True),
        headers={"Retry-After": str(retry_after)},
    )
