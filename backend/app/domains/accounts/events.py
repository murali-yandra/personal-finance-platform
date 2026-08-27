"""Domain events raised by the accounts service.

Names follow the approved ADR-007 events referenced in
``14-sprint_roadmap.md`` section 7.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.events.base_event import BaseEvent

ACCOUNT_CREATED = "AccountCreated"
ACCOUNT_UPDATED = "AccountUpdated"
ACCOUNT_ARCHIVED = "AccountArchived"

ENTITY_TYPE = "account"


def account_created_event(user_id: UUID, account_id: UUID) -> BaseEvent:
    """Build the event raised when an account is created."""
    return BaseEvent(
        event_type=ACCOUNT_CREATED,
        payload={
            "entity_type": ENTITY_TYPE,
            "entity_id": str(account_id),
            "user_id": str(user_id),
        },
    )


def account_updated_event(
    user_id: UUID,
    account_id: UUID,
    changes: dict[str, tuple[Any, Any]],
) -> BaseEvent:
    """Build the event raised when account metadata changes.

    ``changes`` maps a field name to its ``(old, new)`` values so a future audit
    subscriber can write one row per changed field without re-reading the record.
    """
    return BaseEvent(
        event_type=ACCOUNT_UPDATED,
        payload={
            "entity_type": ENTITY_TYPE,
            "entity_id": str(account_id),
            "user_id": str(user_id),
            "changes": {
                field: [_serialize(old), _serialize(new)]
                for field, (old, new) in changes.items()
            },
        },
    )


def account_archived_event(user_id: UUID, account_id: UUID) -> BaseEvent:
    """Build the event raised when an account is archived."""
    return BaseEvent(
        event_type=ACCOUNT_ARCHIVED,
        payload={
            "entity_type": ENTITY_TYPE,
            "entity_id": str(account_id),
            "user_id": str(user_id),
        },
    )


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    return str(value)
