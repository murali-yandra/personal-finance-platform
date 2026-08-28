from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class IngestSmsBatchCommand:
    """Service input for importing many messages at once."""

    user_id: UUID
    messages: tuple[IngestSmsCommand, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class IngestSmsBatchResult:
    """Service output for a batch import."""

    accepted: int = 0
    duplicates: int = 0
    failed: int = 0
    ignored: int = 0
    raw_event_ids: tuple[UUID, ...] = field(default_factory=tuple)

    @property
    def total(self) -> int:
        """Return how many messages were submitted."""
        return self.accepted + self.duplicates + self.failed + self.ignored


@dataclass(frozen=True)
class ReprocessResult:
    """Service output for reprocessing stored raw events."""

    reprocessed: int = 0
    succeeded: int = 0
    still_failing: int = 0
