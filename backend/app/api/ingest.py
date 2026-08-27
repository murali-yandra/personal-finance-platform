from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.api.dependencies.api_key import get_ingestion_user
from app.db.session import get_session
from app.domains.ingestion.repository import RawEventRepository
from app.domains.ingestion.schemas import IngestSmsCommand
from app.domains.ingestion.service import IngestionService
from app.domains.users.models import User
from app.shared.enums import SourceType
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/ingest", tags=["ingestion"])

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


class IngestSmsRequest(BaseModel):
    """Request body for a single incoming SMS."""

    model_config = ConfigDict(str_strip_whitespace=True)

    message_text: str = Field(min_length=1, max_length=4000)
    received_at: datetime
    sender: str | None = Field(default=None, max_length=255)


class IngestSmsData(BaseModel):
    """Response data for an ingested message."""

    raw_event_id: UUID
    status: str
    transaction_id: UUID | None = None


IngestSmsResponse = SuccessResponse[IngestSmsData]


def get_ingestion_service(
    session: Annotated[Session, Depends(get_session)],
) -> IngestionService:
    """Build the ingestion service dependency."""
    return IngestionService(repository=RawEventRepository(session))


@router.post(
    "/sms",
    response_model=IngestSmsResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_sms(
    request: Request,
    payload: IngestSmsRequest,
    ingestion_user: Annotated[User, Depends(get_ingestion_user)],
    ingestion_service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> IngestSmsResponse:
    """Store an incoming SMS.

    A replay of an already-stored message returns 201 with status ``DUPLICATE``
    rather than an error, so a retrying sender does not treat it as a failure and
    keep retrying.
    """
    result = ingestion_service.ingest_sms(
        IngestSmsCommand(
            user_id=ingestion_user.id,
            message_text=payload.message_text,
            received_at=payload.received_at,
            sender=payload.sender,
            source_type=SourceType.SMS,
            correlation_id=_header_uuid(request, CORRELATION_ID_HEADER),
            request_id=_header_uuid(request, REQUEST_ID_HEADER),
        )
    )
    return IngestSmsResponse(
        data=IngestSmsData(
            raw_event_id=result.raw_event_id,
            status=result.status.value,
            transaction_id=result.transaction_id,
        )
    )


def _header_uuid(request: Request, header: str) -> UUID | None:
    raw = request.headers.get(header)
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None
