from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Numeric, func
from sqlmodel import Field, SQLModel


class Transfer(SQLModel, table=True):
    """A link between two transactions that represent one movement of money.

    A transfer between the user's own accounts is not income or expense: the
    money never left. Linking the two sides is what lets reporting exclude it
    (``04-database_schema.md`` section 8).

    ``destination_transaction_id`` is nullable because the matching side often
    arrives in a later SMS, or never arrives at all.
    """

    __tablename__ = "transfers"
    __table_args__ = (
        Index("idx_transfers_user_id", "user_id"),
        Index("idx_transfers_source", "source_transaction_id"),
        Index("idx_transfers_destination", "destination_transaction_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)

    source_transaction_id: UUID = Field(
        foreign_key="transactions.id",
        nullable=False,
    )
    destination_transaction_id: UUID | None = Field(
        default=None,
        foreign_key="transactions.id",
    )

    transfer_type: str = Field(default="INTERNAL", max_length=50, nullable=False)

    confidence_score: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(5, 2), nullable=True),
    )
    is_confirmed: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=False),
            nullable=False,
            server_default=func.now(),
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=False),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        )
    )
