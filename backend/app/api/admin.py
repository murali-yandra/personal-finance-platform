"""Administrative APIs.

Every route requires the ADMIN role. Responses deliberately carry no financial
detail: an administrator manages accounts and access, and does not need to read
anyone's transactions to do it.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.dependencies.pagination import Pagination, get_pagination
from app.api.dependencies.roles import require_admin
from app.db.session import get_session
from app.domains.accounts.models import Account
from app.domains.transactions.models import Transaction
from app.domains.users.models import User
from app.shared.enums import UserRole
from app.shared.exceptions.base import ApplicationError
from app.shared.schemas.responses import (
    PageMeta,
    PaginatedResponse,
    SuccessResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminUserNotFoundError(ApplicationError):
    """Raised when an administered user does not exist."""

    def __init__(self) -> None:
        super().__init__(
            code="USER_NOT_FOUND",
            message="User not found.",
            status_code=404,
        )


class AdminUserData(BaseModel):
    """Response data for one user, without financial detail."""

    id: UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> "AdminUserData":
        """Build the response payload from a user record."""
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )


class PlatformStatsData(BaseModel):
    """Aggregate counts across the platform."""

    users: int
    active_users: int
    accounts: int
    transactions: int


class UpdateUserRoleRequest(BaseModel):
    """Request body for changing a user's role."""

    role: UserRole


class SetUserActiveRequest(BaseModel):
    """Request body for enabling or disabling a user."""

    is_active: bool


AdminUserListResponse = PaginatedResponse[AdminUserData]
AdminUserResponse = SuccessResponse[AdminUserData]
PlatformStatsResponse = SuccessResponse[PlatformStatsData]


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_session)],
    pagination: Annotated[Pagination, Depends(get_pagination)],
    search: Annotated[str | None, Query()] = None,
) -> AdminUserListResponse:
    """List platform users."""
    statement = select(User)
    count_statement = select(func.count()).select_from(User)

    if search:
        pattern = f"%{search.strip().lower()}%"
        statement = statement.where(func.lower(User.email).like(pattern))
        count_statement = count_statement.where(func.lower(User.email).like(pattern))

    statement = statement.order_by(User.created_at, User.id)
    users = session.exec(statement.offset(pagination.offset).limit(pagination.limit))
    total = int(session.exec(count_statement).one())

    return AdminUserListResponse(
        data=[AdminUserData.from_user(user) for user in users],
        meta=PageMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_records=total,
        ),
    )


@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
def update_user_role(
    user_id: UUID,
    request: UpdateUserRoleRequest,
    admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserResponse:
    """Change a user's role."""
    user = _load_user(session, user_id)
    user.role = request.role.value
    session.add(user)
    session.commit()
    session.refresh(user)
    return AdminUserResponse(data=AdminUserData.from_user(user))


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
def set_user_active(
    user_id: UUID,
    request: SetUserActiveRequest,
    admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminUserResponse:
    """Enable or disable a user.

    An administrator cannot disable their own account: doing so would lock the
    platform out of administration entirely if they were the only admin.
    """
    if user_id == admin.id and not request.is_active:
        from app.api.dependencies.roles import AccessDeniedError

        raise AccessDeniedError()

    user = _load_user(session, user_id)
    user.is_active = request.is_active
    session.add(user)
    session.commit()
    session.refresh(user)
    return AdminUserResponse(data=AdminUserData.from_user(user))


@router.get("/stats", response_model=PlatformStatsResponse)
def platform_stats(
    admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_session)],
) -> PlatformStatsResponse:
    """Return aggregate platform counts."""
    return PlatformStatsResponse(
        data=PlatformStatsData(
            users=int(session.exec(select(func.count()).select_from(User)).one()),
            active_users=int(
                session.exec(
                    select(func.count()).select_from(User).where(User.is_active)
                ).one()
            ),
            accounts=int(session.exec(select(func.count()).select_from(Account)).one()),
            transactions=int(
                session.exec(select(func.count()).select_from(Transaction)).one()
            ),
        )
    )


def _load_user(session: Session, user_id: UUID) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise AdminUserNotFoundError()
    return user
