from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Numeric, Text, func
from sqlmodel import Field, SQLModel


class AISuggestion(SQLModel, table=True):
    """A model-generated suggestion awaiting user review.

    Suggestions are stored rather than applied. A wrong category quietly
    corrupts every report that groups by category, so only a high-confidence
    suggestion is applied automatically
    (``13-ai_integration_standards.md`` section 9).
    """

    __tablename__ = "ai_suggestions"
    __table_args__ = (
        Index("idx_ai_suggestions_user_id", "user_id"),
        Index("idx_ai_suggestions_transaction_id", "transaction_id"),
        Index("idx_ai_suggestions_status", "status"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    transaction_id: UUID | None = Field(
        default=None,
        foreign_key="transactions.id",
    )

    suggestion_type: str = Field(max_length=50, nullable=False)
    suggested_value: str = Field(sa_column=Column(Text, nullable=False))
    confidence_score: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(5, 2), nullable=True),
    )

    prompt_version: str | None = Field(default=None, max_length=50)
    model_name: str | None = Field(default=None, max_length=100)

    status: str = Field(default="PENDING", max_length=50, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=False),
            nullable=False,
            server_default=func.now(),
        )
    )
    reviewed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
    )


class UserFeedback(SQLModel, table=True):
    """A correction the user made, used to learn future behaviour.

    Feedback is the record of what the user actually wanted, which is what makes
    the learning engine in Sprint 13 possible.
    """

    __tablename__ = "user_feedback"
    __table_args__ = (
        Index("idx_user_feedback_user_id", "user_id"),
        Index("idx_user_feedback_transaction_id", "transaction_id"),
        Index("idx_user_feedback_type", "feedback_type"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    transaction_id: UUID | None = Field(
        default=None,
        foreign_key="transactions.id",
    )

    feedback_type: str = Field(max_length=50, nullable=False)

    old_value: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    new_value: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    source: str = Field(default="USER", max_length=50, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=False),
            nullable=False,
            server_default=func.now(),
        )
    )
