from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.ingestion.models import RawEvent


class RawEventRepository:
    """Persistence operations for raw events.

    There is no delete method: raw events are retained permanently
    (``04-database_schema.md`` section 9).
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, raw_event_id: UUID, user_id: UUID) -> RawEvent | None:
        """Return a user-owned raw event."""
        statement = select(RawEvent).where(
            RawEvent.id == raw_event_id,
            RawEvent.user_id == user_id,
        )
        return self._session.exec(statement).first()

    def find_by_hash(self, user_id: UUID, message_hash: str) -> RawEvent | None:
        """Return an existing raw event with the same message hash."""
        statement = select(RawEvent).where(
            RawEvent.user_id == user_id,
            RawEvent.message_hash == message_hash,
        )
        return self._session.exec(statement).first()

    def list_for_user(
        self,
        user_id: UUID,
        processing_status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[RawEvent]:
        """Return a page of raw events, newest first."""
        statement = self._filtered(user_id, processing_status, start_date, end_date)
        statement = statement.order_by(
            RawEvent.received_at.desc(),  # type: ignore[attr-defined]
            RawEvent.id,
        )
        return list(self._session.exec(statement.offset(offset).limit(limit)).all())

    def count_for_user(
        self,
        user_id: UUID,
        processing_status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Return how many raw events match the filters."""
        statement = select(func.count()).select_from(RawEvent)
        statement = self._apply_filters(
            statement, user_id, processing_status, start_date, end_date
        )
        return int(self._session.exec(statement).one())

    def add(self, raw_event: RawEvent) -> RawEvent:
        """Persist a raw event."""
        self._session.add(raw_event)
        self._session.flush()
        return raw_event

    def commit(self) -> None:
        """Commit the active transaction."""
        self._session.commit()

    def rollback(self) -> None:
        """Rollback the active transaction."""
        self._session.rollback()

    def refresh(self, raw_event: RawEvent) -> None:
        """Reload a raw event from the database."""
        self._session.refresh(raw_event)

    def _filtered(
        self,
        user_id: UUID,
        processing_status: str | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ):
        return self._apply_filters(
            select(RawEvent), user_id, processing_status, start_date, end_date
        )

    @staticmethod
    def _apply_filters(
        statement,
        user_id: UUID,
        processing_status: str | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ):
        statement = statement.where(RawEvent.user_id == user_id)
        if processing_status is not None:
            statement = statement.where(RawEvent.processing_status == processing_status)
        if start_date is not None:
            statement = statement.where(RawEvent.received_at >= start_date)
        if end_date is not None:
            statement = statement.where(RawEvent.received_at <= end_date)
        return statement
