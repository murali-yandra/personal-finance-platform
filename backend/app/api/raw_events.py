"""Read-only view over ingested messages.

Ingestion never loses a message, but until now there was no way to see the ones
that did not become transactions. ``POST /api/v1/ingest/reprocess`` takes a date
window and runs blind, so a message stuck on ``UNKNOWN_FORMAT`` was invisible
unless you queried the database directly.

This endpoint exposes that queue. Raw events are immutable
(``04-database_schema.md`` section 2.4), so like the audit trail it is read-only:
there is no create, update or delete route.
"""

from datetime import datetime
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.pagination import Pagination, get_pagination
from app.db.session import get_session
from app.domains.ingestion.models import RawEvent
from app.domains.ingestion.repository import RawEventRepository
from app.domains.users.models import User
from app.shared.enums import ProcessingStatus
from app.shared.exceptions.base import ApplicationError
from app.shared.schemas.responses import (
    PageMeta,
    PaginatedResponse,
    SuccessResponse,
)

router = APIRouter(prefix="/raw-events", tags=["raw-events"])

MESSAGE_PREVIEW_LENGTH = 200


class RawEventData(BaseModel):
    """Response data for one ingested message."""

    id: UUID
    source_type: str
    sender: str | None
    message_preview: str
    received_at: datetime
    processing_status: str
    processing_error: str | None
    correlation_id: UUID | None
    created_at: datetime

    @classmethod
    def from_event(cls, event: RawEvent) -> "RawEventData":
        """Build the response payload from a stored raw event.

        The message body is truncated: this is a triage list, and a bank SMS can
        carry a balance and account details that do not belong in a list view.
        Fetch the single event for the full text.
        """
        return cls(
            id=event.id,
            source_type=event.source_type,
            sender=event.sender,
            message_preview=_preview(event.message_text),
            received_at=event.received_at,
            processing_status=event.processing_status,
            processing_error=event.processing_error,
            correlation_id=event.correlation_id,
            created_at=event.created_at,
        )


class RawEventDetailData(RawEventData):
    """Response data for a single ingested message, with the full text."""

    message_text: str

    @classmethod
    def from_event(cls, event: RawEvent) -> "RawEventDetailData":
        """Build the detail payload, including the untruncated message."""
        base = RawEventData.from_event(event)
        return cls(**base.model_dump(), message_text=event.message_text)


class RawEventNotFoundError(ApplicationError):
    """Raised when a raw event is missing or owned by another user."""

    def __init__(self) -> None:
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message="Message not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )


RawEventListResponse = PaginatedResponse[RawEventData]
RawEventDetailResponse = SuccessResponse[RawEventDetailData]


def get_raw_event_repository(
    session: Annotated[Session, Depends(get_session)],
) -> RawEventRepository:
    """Build the raw event repository dependency."""
    return RawEventRepository(session)


@router.get("", response_model=RawEventListResponse)
def list_raw_events(
    current_user: Annotated[User, Depends(get_current_user)],
    repository: Annotated[RawEventRepository, Depends(get_raw_event_repository)],
    pagination: Annotated[Pagination, Depends(get_pagination)],
    processing_status: Annotated[ProcessingStatus | None, Query()] = None,
    start_date: Annotated[datetime | None, Query()] = None,
    end_date: Annotated[datetime | None, Query()] = None,
) -> RawEventListResponse:
    """List the authenticated user's ingested messages, newest first.

    Filter by ``processing_status`` to triage: ``UNKNOWN_FORMAT`` and ``FAILED``
    are the messages a parser could not turn into a transaction and that
    ``/ingest/reprocess`` will retry. ``IGNORED`` is not a gap — it is an OTP or
    promotional message the pipeline correctly declined.
    """
    status_filter = processing_status.value if processing_status else None
    events = repository.list_for_user(
        user_id=current_user.id,
        processing_status=status_filter,
        start_date=start_date,
        end_date=end_date,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    total = repository.count_for_user(
        user_id=current_user.id,
        processing_status=status_filter,
        start_date=start_date,
        end_date=end_date,
    )
    return RawEventListResponse(
        data=[RawEventData.from_event(event) for event in events],
        meta=PageMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_records=total,
        ),
    )


@router.get("/{raw_event_id}", response_model=RawEventDetailResponse)
def get_raw_event(
    raw_event_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    repository: Annotated[RawEventRepository, Depends(get_raw_event_repository)],
) -> RawEventDetailResponse:
    """Return one ingested message with its full text.

    Another user's message reports as not found rather than forbidden, so the
    API cannot be used to probe for message IDs
    (``10-security_standards.md`` section 6).
    """
    event = repository.get_by_id(raw_event_id=raw_event_id, user_id=current_user.id)
    if event is None:
        raise RawEventNotFoundError()
    return RawEventDetailResponse(data=RawEventDetailData.from_event(event))


def _preview(message_text: str) -> str:
    if len(message_text) <= MESSAGE_PREVIEW_LENGTH:
        return message_text
    return message_text[:MESSAGE_PREVIEW_LENGTH] + "..."
