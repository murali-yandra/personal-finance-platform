from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Text, func
from sqlmodel import Field, SQLModel


class RawEvent(SQLModel, table=True):
    """Immutable record of an incoming source message.

    Raw events are the original source of truth for every parsed transaction and
    must never be deleted (``04-database_schema.md`` section 2.4). Only
    ``processing_status`` and ``processing_error`` change after insert, as the
    message moves through the pipeline.
    """

    __tablename__ = "raw_events"
    __table_args__ = (
        Index("idx_raw_events_user_id", "user_id"),
        Index("idx_raw_events_hash", "message_hash"),
        Index("idx_raw_events_received_at", "received_at"),
        Index("idx_raw_events_status", "processing_status"),
        Index("idx_raw_events_correlation_id", "correlation_id"),
        Index(
            "uq_raw_events_user_message_hash",
            "user_id",
            "message_hash",
            unique=True,
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)

    source_type: str = Field(max_length=50, nullable=False)
    sender: str | None = Field(default=None, max_length=255)
    message_text: str = Field(sa_column=Column(Text, nullable=False))

    received_at: datetime = Field(
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )
    message_hash: str = Field(max_length=255, nullable=False)

    processing_status: str = Field(
        default="RECEIVED",
        max_length=50,
        nullable=False,
    )
    processing_error: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    correlation_id: UUID | None = Field(default=None)
    request_id: UUID | None = Field(default=None)

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=False),
            nullable=False,
            server_default=func.now(),
        )
    )
