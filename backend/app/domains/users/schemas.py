from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RegisterUserCommand:
    """Service input for user registration."""

    email: str
    password: str
    display_name: str


@dataclass(frozen=True)
class RegisterUserResult:
    """Service output for user registration."""

    user_id: UUID


@dataclass(frozen=True)
class LoginUserCommand:
    """Service input for user login."""

    email: str
    password: str


@dataclass(frozen=True)
class LoginUserResult:
    """Service output for successful user login."""

    access_token: str
    refresh_token: str
    expires_in: int
