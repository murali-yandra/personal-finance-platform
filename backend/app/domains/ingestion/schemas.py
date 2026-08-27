from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.shared.enums import ProcessingStatus, SourceType


@dataclass(frozen=True)
class IngestSmsCommand:
    """Service input for ingesting one source message."""

    user_id: UUID
    message_text: str
    received_at: datetime
    sender: str | None = None
    source_type: SourceType = SourceType.SMS
    correlation_id: UUID | None = None
    request_id: UUID | None = None


@dataclass(frozen=True)
class IngestSmsResult:
    """Service output for a single ingested message."""

    raw_event_id: UUID
    status: ProcessingStatus
    is_duplicate: bool = False
    transaction_id: UUID | None = None
