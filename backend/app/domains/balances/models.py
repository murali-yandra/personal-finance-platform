from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column, Date, DateTime, Index, Numeric, UniqueConstraint, func
from sqlmodel import Field, SQLModel


class BalanceSnapshot(SQLModel, table=True):
    """An account balance as at the end of a given day.

    One row per account per day, so a trend can be drawn without replaying every
    transaction. The uniqueness constraint makes a re-run of the snapshot job
    an update rather than a duplicate.
    """

    __tablename__ = "balance_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "snapshot_date",
            name="uq_balance_snapshot_account_date",
        ),
        Index("idx_balance_snapshots_user_id", "user_id"),
        Index("idx_balance_snapshots_account_id", "account_id"),
        Index("idx_balance_snapshots_date", "snapshot_date"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    account_id: UUID = Field(foreign_key="accounts.id", nullable=False)

    snapshot_date: date = Field(sa_column=Column(Date, nullable=False))

    balance: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    currency: str = Field(default="INR", max_length=3, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=False),
            nullable=False,
            server_default=func.now(),
        )
    )
