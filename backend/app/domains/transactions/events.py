"""Domain events raised by the transactions service."""

from typing import Any
from uuid import UUID

from app.events.base_event import BaseEvent

TRANSACTION_CREATED = "TransactionCreated"
TRANSACTION_UPDATED = "TransactionUpdated"

ENTITY_TYPE = "transaction"


def transaction_created_event(
    user_id: UUID,
    transaction_id: UUID,
    account_id: UUID,
) -> BaseEvent:
    """Build the event raised when a transaction is created."""
    return BaseEvent(
        event_type=TRANSACTION_CREATED,
        payload={
            "entity_type": ENTITY_TYPE,
            "entity_id": str(transaction_id),
            "user_id": str(user_id),
            "account_id": str(account_id),
        },
    )


def transaction_updated_event(
    user_id: UUID,
    transaction_id: UUID,
    changes: dict[str, tuple[Any, Any]],
) -> BaseEvent:
    """Build the event raised when a transaction is updated."""
    return BaseEvent(
        event_type=TRANSACTION_UPDATED,
        payload={
            "entity_type": ENTITY_TYPE,
            "entity_id": str(transaction_id),
            "user_id": str(user_id),
            "changes": {
                field: [_serialize(old), _serialize(new)]
                for field, (old, new) in changes.items()
            },
        },
    )


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    return str(value)
