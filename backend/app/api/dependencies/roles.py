"""Role-based authorization.

The role is read from the authenticated user record, not from the JWT claim. A
token outlives a role change, so trusting the claim would let a demoted admin
keep admin access until their token expired.
"""

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated

from fastapi import Depends

from app.api.dependencies.auth import get_current_user
from app.domains.users.models import User
from app.shared.enums import UserRole
from app.shared.exceptions.base import ApplicationError


class AccessDeniedError(ApplicationError):
    """Raised when a caller lacks the required role."""

    def __init__(self) -> None:
        super().__init__(
            code="ACCESS_DENIED",
            message="You do not have permission to perform this action.",
            status_code=HTTPStatus.FORBIDDEN,
        )


def require_role(*roles: UserRole) -> Callable[..., User]:
    """Build a dependency that admits only the given roles."""
    allowed = {UserRole(role).value for role in roles}

    def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed:
            raise AccessDeniedError()
        return current_user

    return dependency


require_admin = require_role(UserRole.ADMIN)
