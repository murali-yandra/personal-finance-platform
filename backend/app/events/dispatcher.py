from collections import defaultdict
from collections.abc import Awaitable, Callable
from inspect import isawaitable

from app.events.base_event import BaseEvent

type EventHandler = Callable[[BaseEvent], None | Awaitable[None]]


class EventDispatcher:
    """In-memory dispatcher for internal event handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def register(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for an event type."""
        self._handlers[event_type].append(handler)

    async def dispatch(self, event: BaseEvent) -> None:
        """Dispatch an event to registered handlers."""
        for handler in self._handlers.get(event.event_type, []):
            result = handler(event)
            if isawaitable(result):
                await result

    def clear(self) -> None:
        """Remove all registered handlers."""
        self._handlers.clear()
