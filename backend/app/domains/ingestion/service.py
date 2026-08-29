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
from app.domains.ingestion.schemas import (
    IngestSmsBatchCommand,
    IngestSmsBatchResult,
    IngestSmsCommand,
    IngestSmsResult,
    ReprocessResult,
)
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

    @property
    def processor(self) -> RawEventProcessor | None:
        """Return the configured downstream processor, if any."""
        return self._processor

    def process_stored_event(self, raw_event: RawEvent) -> IngestSmsResult:
        """Re-run the pipeline over an already-stored raw event."""
        if self._processor is None:
            return IngestSmsResult(
                raw_event_id=raw_event.id,
                status=ProcessingStatus(raw_event.processing_status),
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


MAX_BATCH_SIZE = 1000

# Statuses worth re-running. A message that was IGNORED is not a parser gap,
# and one already PROCESSED would only produce a duplicate.
REPROCESSABLE_STATUSES = (
    ProcessingStatus.FAILED.value,
    ProcessingStatus.UNKNOWN_FORMAT.value,
    ProcessingStatus.RECEIVED.value,
)


class HistoricalImportService:
    """Bulk import and reprocessing of source messages (Sprint 11)."""

    def __init__(
        self,
        repository: RawEventRepository,
        ingestion_service: "IngestionService",
    ) -> None:
        self._repository = repository
        self._ingestion = ingestion_service

    def import_batch(self, command: "IngestSmsBatchCommand") -> "IngestSmsBatchResult":
        """Import many messages, counting each outcome.

        Each message is stored and processed independently. One unreadable
        message in a year of history must not abort the import, so failures are
        counted rather than raised.
        """
        if len(command.messages) > MAX_BATCH_SIZE:
            raise InvalidSmsPayloadError(
                f"A batch may contain at most {MAX_BATCH_SIZE} messages."
            )

        accepted = duplicates = failed = ignored = 0
        raw_event_ids: list[UUID] = []

        for message in command.messages:
            try:
                result = self._ingestion.ingest_sms(message)
            except Exception:
                logger.exception("Batch message failed during import.")
                failed += 1
                continue

            raw_event_ids.append(result.raw_event_id)
            if result.is_duplicate or result.status is ProcessingStatus.DUPLICATE:
                duplicates += 1
            elif result.status is ProcessingStatus.IGNORED:
                ignored += 1
            elif result.status in {
                ProcessingStatus.FAILED,
                ProcessingStatus.UNKNOWN_FORMAT,
            }:
                failed += 1
            else:
                accepted += 1

        return IngestSmsBatchResult(
            accepted=accepted,
            duplicates=duplicates,
            failed=failed,
            ignored=ignored,
            raw_event_ids=tuple(raw_event_ids),
        )

    def reprocess(
        self,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = MAX_BATCH_SIZE,
    ) -> "ReprocessResult":
        """Re-run stored messages that never produced a transaction.

        This is how a parser improvement is applied to history: the raw events
        were kept precisely so they could be re-read later.
        """
        if self._ingestion.processor is None:
            raise InvalidSmsPayloadError("Reprocessing requires a configured parser.")

        candidates = [
            raw_event
            for status in REPROCESSABLE_STATUSES
            for raw_event in self._repository.list_for_user(
                user_id=user_id,
                processing_status=status,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        ][:limit]

        succeeded = 0
        for raw_event in candidates:
            try:
                result = self._ingestion.process_stored_event(raw_event)
            except Exception:
                logger.exception("Reprocessing failed for %s", raw_event.id)
                continue
            if result.transaction_id is not None:
                succeeded += 1

        return ReprocessResult(
            reprocessed=len(candidates),
            succeeded=succeeded,
            still_failing=len(candidates) - succeeded,
        )
