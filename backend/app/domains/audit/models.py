from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Text, func
from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    """Append-only record of every audited change.

    ``04-database_schema.md`` section 4.12 requires these rows to be immutable:
    never updated, never deleted. There is deliberately no update or delete path
    in the repository.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_log_user_id", "user_id"),
        Index("idx_audit_log_entity", "entity_type", "entity_id"),
        Index("idx_audit_log_action", "action"),
        Index("idx_audit_log_created_at", "created_at"),
        Index("idx_audit_log_correlation_id", "correlation_id"),
        Index("idx_audit_log_request_id", "request_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)

    entity_type: str = Field(max_length=100, nullable=False)
    entity_id: UUID = Field(nullable=False)

    action: str = Field(max_length=100, nullable=False)
    field_name: str | None = Field(default=None, max_length=100)

    old_value: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    new_value: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    source: str = Field(max_length=50, nullable=False)

    correlation_id: UUID | None = Field(default=None)
    request_id: UUID | None = Field(default=None)
    session_id: UUID | None = Field(default=None)

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=False),
            nullable=False,
            server_default=func.now(),
        )
    )
