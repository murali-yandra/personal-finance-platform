from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.api.dependencies.api_key import get_ingestion_user
from app.api.dependencies.audit import get_audit_service
from app.config import get_settings
from app.db.session import get_session
from app.domains.accounts.repository import AccountRepository
from app.domains.audit.service import AuditService
from app.domains.balances.service import BalanceService
from app.domains.categories.repository import CategoryRepository
from app.domains.ingestion.pipeline import SmsPipeline
from app.domains.ingestion.repository import RawEventRepository
from app.domains.ingestion.schemas import IngestSmsCommand
from app.domains.ingestion.service import IngestionService
from app.domains.merchants.repository import MerchantRepository
from app.domains.merchants.service import MerchantService
from app.domains.transactions.repository import TransactionRepository
from app.domains.transactions.service import TransactionService
from app.domains.users.models import User
from app.events.publisher import (
    BufferedEventPublisher,
    CompositeEventPublisher,
)
from app.shared.enums import SourceType
from app.shared.schemas.responses import SuccessResponse
from app.telegram.factory import build_telegram_client
from app.telegram.notifier import TelegramNotifier

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


def get_sms_pipeline(
    session: Annotated[Session, Depends(get_session)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> SmsPipeline:
    """Build the parse-and-post pipeline that runs after a message is stored.

    The audit service and the balance engine both write inside the transaction,
    so a balance can never drift from the transactions that produced it. The
    Telegram notifier is buffered and released only after the commit succeeds.
    """
    settings = get_settings()
    notifier = BufferedEventPublisher(
        TelegramNotifier(
            client=build_telegram_client(settings),
            session=session,
            enabled=settings.enable_telegram,
        )
    )
    return SmsPipeline(
        raw_event_repository=RawEventRepository(session),
        account_repository=AccountRepository(session),
        transaction_service=TransactionService(
            repository=TransactionRepository(session),
            account_repository=AccountRepository(session),
            event_publisher=CompositeEventPublisher(
                audit_service,
                BalanceService(
                    session=session,
                    account_repository=AccountRepository(session),
                ),
                notifier,
            ),
        ),
        merchant_service=MerchantService(repository=MerchantRepository(session)),
        category_repository=CategoryRepository(session),
        deferred_publisher=notifier,
    )


def get_ingestion_service(
    session: Annotated[Session, Depends(get_session)],
    pipeline: Annotated[SmsPipeline, Depends(get_sms_pipeline)],
) -> IngestionService:
    """Build the ingestion service dependency."""
    return IngestionService(
        repository=RawEventRepository(session),
        processor=pipeline,
    )


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
