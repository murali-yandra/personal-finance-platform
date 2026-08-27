from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.pagination import Pagination, get_pagination
from app.db.session import get_session
from app.domains.audit.models import AuditLog
from app.domains.audit.repository import AuditRepository
from app.domains.users.models import User
from app.shared.schemas.responses import PageMeta, PaginatedResponse

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditRecordData(BaseModel):
    """Response data for one audit record."""

    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    field_name: str | None
    old_value: str | None
    new_value: str | None
    source: str
    correlation_id: UUID | None
    request_id: UUID | None
    created_at: datetime

    @classmethod
    def from_entry(cls, entry: AuditLog) -> "AuditRecordData":
        """Build the response payload from a persisted audit record."""
        return cls(
            id=entry.id,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            action=entry.action,
            field_name=entry.field_name,
            old_value=entry.old_value,
            new_value=entry.new_value,
            source=entry.source,
            correlation_id=entry.correlation_id,
            request_id=entry.request_id,
            created_at=entry.created_at,
        )


AuditListResponse = PaginatedResponse[AuditRecordData]


def get_audit_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AuditRepository:
    """Build the audit repository dependency."""
    return AuditRepository(session)


@router.get("", response_model=AuditListResponse)
def list_audit_records(
    current_user: Annotated[User, Depends(get_current_user)],
    repository: Annotated[AuditRepository, Depends(get_audit_repository)],
    pagination: Annotated[Pagination, Depends(get_pagination)],
    entity_type: Annotated[str | None, Query()] = None,
    entity_id: Annotated[UUID | None, Query()] = None,
    start_date: Annotated[datetime | None, Query()] = None,
    end_date: Annotated[datetime | None, Query()] = None,
) -> AuditListResponse:
    """List the authenticated user's audit records, newest first.

    The audit trail is read-only over the API: there is no create, update or
    delete route, because audit rows are append-only.
    """
    entries = repository.list_for_user(
        user_id=current_user.id,
        entity_type=entity_type,
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    total = repository.count_for_user(
        user_id=current_user.id,
        entity_type=entity_type,
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date,
    )
    return AuditListResponse(
        data=[AuditRecordData.from_entry(entry) for entry in entries],
        meta=PageMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_records=total,
        ),
    )
