"""Request-scoped context.

Request and correlation ids are held in context variables so any module can log
them without threading them through every call signature. Context variables are
per-task, so concurrent requests never see each other's ids.
"""

from contextvars import ContextVar
from uuid import UUID, uuid4

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[str | None] = ContextVar(
    "correlation_id",
    default=None,
)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def set_request_context(
    request_id: str,
    correlation_id: str,
    user_id: str | None = None,
) -> None:
    """Bind the ids for the current request."""
    request_id_var.set(request_id)
    correlation_id_var.set(correlation_id)
    user_id_var.set(user_id)


def set_current_user_id(user_id: UUID | str | None) -> None:
    """Bind the authenticated user id once it is known."""
    user_id_var.set(str(user_id) if user_id is not None else None)


def clear_request_context() -> None:
    """Unbind the request context."""
    request_id_var.set(None)
    correlation_id_var.set(None)
    user_id_var.set(None)


def current_context() -> dict[str, str]:
    """Return the bound ids, omitting any that are unset."""
    values = {
        "request_id": request_id_var.get(),
        "correlation_id": correlation_id_var.get(),
        "user_id": user_id_var.get(),
    }
    return {key: value for key, value in values.items() if value}


def new_request_id() -> str:
    """Return a fresh request id."""
    return str(uuid4())
