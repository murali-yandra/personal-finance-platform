"""Raw event ingestion.

The raw event is committed before any parsing runs. That ordering matters: a
parser failure must never lose the original message, because raw events are the
source of truth for every transaction derived from them.

Sprint 4 stops at storage. Sprint 5 attaches the parser to the ``processor``
hook, and the status moves on from ``RECEIVED``.
"""

import logging
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.domains.ingestion.exceptions import InvalidSmsPayloadError
from app.domains.ingestion.hashing import build_message_hash
from app.domains.ingestion.models import RawEvent
from app.domains.ingestion.repository import RawEventRepository
from app.domains.ingestion.schemas import IngestSmsCommand, IngestSmsResult
from app.shared.enums import ProcessingStatus

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4000


class RawEventProcessor(Protocol):
    """Downstream pipeline invoked after a raw event is stored."""

    def process(self, raw_event: RawEvent) -> IngestSmsResult:
        """Parse a stored raw event and return the outcome."""
        ...


class IngestionService:
    """Application service for storing incoming source messages."""

    def __init__(
        self,
        repository: RawEventRepository,
        processor: RawEventProcessor | None = None,
    ) -> None:
        self._repository = repository
        self._processor = processor

    def ingest_sms(self, command: IngestSmsCommand) -> IngestSmsResult:
        """Store one message, rejecting exact duplicates."""
        message_text = command.message_text.strip()
        if not message_text:
            raise InvalidSmsPayloadError("Message text is required.")
        if len(message_text) > MAX_MESSAGE_LENGTH:
            raise InvalidSmsPayloadError(
                f"Message text exceeds {MAX_MESSAGE_LENGTH} characters."
            )

        received_at = _normalize_timestamp(command.received_at)
        message_hash = build_message_hash(
            sender=command.sender,
            message_text=message_text,
            received_at_iso=received_at.isoformat(),
        )

        existing = self._repository.find_by_hash(
            user_id=command.user_id,
            message_hash=message_hash,
        )
        if existing is not None:
            return IngestSmsResult(
                raw_event_id=existing.id,
                status=ProcessingStatus.DUPLICATE,
                is_duplicate=True,
            )

        raw_event = RawEvent(
            user_id=command.user_id,
            source_type=command.source_type.value,
            sender=_clean(command.sender),
            message_text=message_text,
            received_at=received_at,
            message_hash=message_hash,
            processing_status=ProcessingStatus.RECEIVED.value,
            correlation_id=command.correlation_id,
            request_id=command.request_id,
        )

        try:
            self._repository.add(raw_event)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        self._repository.refresh(raw_event)

        if self._processor is None:
            return IngestSmsResult(
                raw_event_id=raw_event.id,
                status=ProcessingStatus.RECEIVED,
            )
        return self._process(raw_event)

    def _process(self, raw_event: RawEvent) -> IngestSmsResult:
        """Run the downstream pipeline, never losing the stored message."""
        try:
            return self._processor.process(raw_event)
        except Exception:
            logger.exception(
                "Processing failed for raw event %s",
                raw_event.id,
            )
            return IngestSmsResult(
                raw_event_id=raw_event.id,
                status=ProcessingStatus.FAILED,
            )


def get_raw_event(
    repository: RawEventRepository,
    user_id: UUID,
    raw_event_id: UUID,
) -> RawEvent | None:
    """Return a user-owned raw event."""
    return repository.get_by_id(raw_event_id=raw_event_id, user_id=user_id)


def _normalize_timestamp(value: datetime) -> datetime:
    """Store timestamps as naive UTC, matching the schema's TIMESTAMP columns."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
