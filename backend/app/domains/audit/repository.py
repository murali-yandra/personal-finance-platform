from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.domains.audit.models import AuditLog


class AuditRepository:
    """Append-only persistence for audit records.

    There is deliberately no update or delete method: audit rows are immutable
    (``04-database_schema.md`` section 4.12).
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entry: AuditLog) -> AuditLog:
        """Stage one audit record on the caller's transaction.

        The record shares the caller's session, so it commits or rolls back with
        the change it describes.
        """
        self._session.add(entry)
        return entry

    def add_all(self, entries: list[AuditLog]) -> list[AuditLog]:
        """Stage several audit records."""
        for entry in entries:
            self._session.add(entry)
        return entries

    def list_for_user(
        self,
        user_id: UUID,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Return audit records for a user, newest first."""
        statement = self._filtered(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
        )
        statement = statement.order_by(AuditLog.created_at.desc(), AuditLog.id)  # type: ignore[attr-defined]
        statement = statement.offset(offset).limit(limit)
        return list(self._session.exec(statement).all())

    def count_for_user(
        self,
        user_id: UUID,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Return how many audit records match the filters."""
        statement = self._filtered(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
        )
        return len(list(self._session.exec(statement).all()))

    def _filtered(
        self,
        user_id: UUID,
        entity_type: str | None,
        entity_id: UUID | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ):
        statement = select(AuditLog).where(AuditLog.user_id == user_id)
        if entity_type is not None:
            statement = statement.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            statement = statement.where(AuditLog.entity_id == entity_id)
        if start_date is not None:
            statement = statement.where(AuditLog.created_at >= start_date)
        if end_date is not None:
            statement = statement.where(AuditLog.created_at <= end_date)
        return statement
