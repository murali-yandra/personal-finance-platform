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
