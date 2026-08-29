"""Translation of domain events into append-only audit records.

This is the Sprint 3 implementation of the ``EventPublisher`` protocol that
Sprint 2's account service was written against. Because it writes through the
caller's own ``Session``, an audit row cannot survive a rolled-back change and a
committed change cannot lose its audit row.
"""

import logging
from typing import Any
from uuid import UUID

from app.domains.audit.models import AuditLog
from app.domains.audit.repository import AuditRepository
from app.events.base_event import BaseEvent
from app.shared.enums import AuditAction, AuditSource

logger = logging.getLogger(__name__)

EVENT_ACTIONS: dict[str, AuditAction] = {
    "AccountCreated": AuditAction.CREATE,
    "AccountUpdated": AuditAction.ACCOUNT_UPDATE,
    "AccountArchived": AuditAction.UPDATE,
    "TransactionCreated": AuditAction.CREATE,
    "TransactionUpdated": AuditAction.UPDATE,
    "BalanceReconciled": AuditAction.BALANCE_RECONCILIATION,
    "MerchantPatternCreated": AuditAction.RULE_CREATED,
    "CategoryChanged": AuditAction.CATEGORY_CHANGE,
    "MerchantChanged": AuditAction.MERCHANT_CHANGE,
}

MAX_AUDIT_VALUE_LENGTH = 4000


class AuditService:
    """Writes audit records for domain events."""

    def __init__(
        self,
        repository: AuditRepository,
        source: AuditSource = AuditSource.USER,
        correlation_id: UUID | None = None,
        request_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> None:
        self._repository = repository
        self._source = source
        self._correlation_id = correlation_id
        self._request_id = request_id
        self._session_id = session_id

    def publish(self, event: BaseEvent) -> None:
        """Record a domain event as one or more audit rows.

        An update carrying a ``changes`` map produces one row per changed field,
        so a reviewer can see exactly what moved without diffing snapshots.
        """
        entries = self._build_entries(event)
        if entries:
            self._repository.add_all(entries)

    def _build_entries(self, event: BaseEvent) -> list[AuditLog]:
        payload = event.payload
        user_id = _as_uuid(payload.get("user_id"))
        entity_id = _as_uuid(payload.get("entity_id"))
        entity_type = payload.get("entity_type")

        if user_id is None or entity_id is None or not entity_type:
            logger.warning(
                "Skipping audit for %s: missing user_id, entity_id or entity_type.",
                event.event_type,
            )
            return []

        action = EVENT_ACTIONS.get(event.event_type, AuditAction.UPDATE)
        common = {
            "user_id": user_id,
            "entity_type": str(entity_type),
            "entity_id": entity_id,
            "action": action.value,
            "source": self._source.value,
            "correlation_id": self._correlation_id or event.correlation_id,
            "request_id": self._request_id,
            "session_id": self._session_id,
        }

        changes = payload.get("changes")
        if isinstance(changes, dict) and changes:
            return [
                AuditLog(
                    **common,
                    field_name=str(field_name)[:100],
                    old_value=_truncate(_pair_value(values, 0)),
                    new_value=_truncate(_pair_value(values, 1)),
                )
                for field_name, values in changes.items()
            ]

        return [AuditLog(**common)]


def _pair_value(values: Any, index: int) -> Any:
    if isinstance(values, list | tuple) and len(values) > index:
        return values[index]
    return None


def _truncate(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)[:MAX_AUDIT_VALUE_LENGTH]


def _as_uuid(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            return None
    return None
