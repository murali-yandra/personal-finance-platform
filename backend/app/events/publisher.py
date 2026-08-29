"""Publishing seam for domain events raised inside a service transaction.

Sprint 2 raises ``AccountCreated``, ``AccountUpdated`` and ``AccountArchived`` but
must not persist them: ``audit_log`` arrives with the Sprint 3 audit work
(``14-sprint_roadmap.md`` section 7). Services therefore depend on this protocol
rather than on any concrete sink, so Sprint 3 can supply an audit-writing
implementation without touching service logic.

Implementations that persist must use the service's own ``Session`` so an audit
row can never survive a rolled-back change.
"""

import logging
from typing import Protocol, runtime_checkable

from app.events.base_event import BaseEvent

logger = logging.getLogger(__name__)


@runtime_checkable
class EventPublisher(Protocol):
    """Receives domain events raised by a service."""

    def publish(self, event: BaseEvent) -> None:
        """Handle a single domain event."""
        ...


class NullEventPublisher:
    """Default publisher that records nothing.

    Used until a sprint supplies a persisting implementation.
    """

    def publish(self, event: BaseEvent) -> None:
        """Discard the event, leaving a debug trace for local troubleshooting."""
        logger.debug("Domain event raised: %s", event.event_type)


class RecordingEventPublisher:
    """Publisher that keeps events in memory.

    Intended for tests and for callers that need to inspect what a service raised.
    """

    def __init__(self) -> None:
        self.events: list[BaseEvent] = []

    def publish(self, event: BaseEvent) -> None:
        """Append the event to the recorded list."""
        self.events.append(event)

    def event_types(self) -> list[str]:
        """Return the recorded event types in order."""
        return [event.event_type for event in self.events]


class CompositeEventPublisher:
    """Fans one domain event out to several publishers.

    Lets the audit trail and the notification layer both observe a service
    without either knowing about the other. A failing publisher is logged and
    skipped rather than allowed to abort the others: a notification problem must
    never cost an audit row.
    """

    def __init__(self, *publishers: EventPublisher) -> None:
        self._publishers = [publisher for publisher in publishers if publisher]

    def publish(self, event: BaseEvent) -> None:
        """Forward the event to every registered publisher."""
        for publisher in self._publishers:
            try:
                publisher.publish(event)
            except Exception:
                logger.exception(
                    "Event publisher %s failed for %s",
                    type(publisher).__name__,
                    event.event_type,
                )


class BufferedEventPublisher:
    """Holds events until the caller's transaction has committed.

    External side effects -- sending a Telegram message, calling a model -- must
    not run inside the database transaction. Doing so would notify the user
    about a transaction that then rolled back, and would put network latency on
    the critical path. Events are buffered here and released by ``flush`` once
    the commit has succeeded.
    """

    def __init__(self, sink: EventPublisher) -> None:
        self._sink = sink
        self._buffer: list[BaseEvent] = []

    def publish(self, event: BaseEvent) -> None:
        """Buffer an event for release after commit."""
        self._buffer.append(event)

    def flush(self) -> None:
        """Release buffered events, discarding them even if delivery fails."""
        pending, self._buffer = self._buffer, []
        for event in pending:
            try:
                self._sink.publish(event)
            except Exception:
                logger.exception(
                    "Deferred publisher failed for %s",
                    event.event_type,
                )

    def discard(self) -> None:
        """Drop buffered events without delivering them."""
        self._buffer.clear()

    @property
    def pending_count(self) -> int:
        """Return how many events are waiting for a flush."""
        return len(self._buffer)
