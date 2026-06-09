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
