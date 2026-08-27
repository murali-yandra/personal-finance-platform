from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Numeric, UniqueConstraint, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domains.transactions.models import Transaction
    from app.domains.users.models import User


class Account(SQLModel, table=True):
    """Database entity for user-owned financial accounts."""

    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "bank_name",
            "last_four_digits",
            "account_type",
            name="uq_user_bank_lastfour_type",
        ),
        Index("idx_accounts_user_id", "user_id"),
        Index("idx_accounts_status", "status"),
        Index("idx_accounts_bank_last_four", "bank_name", "last_four_digits"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    account_name: str | None = Field(default=None, max_length=255)
    account_type: str = Field(max_length=50, nullable=False)
    bank_name: str | None = Field(default=None, max_length=100)
    last_four_digits: str | None = Field(default=None, max_length=10)
    currency: str = Field(default="INR", max_length=3, nullable=False)
    opening_balance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(
            Numeric(18, 2),
            nullable=False,
            server_default="0",
        ),
    )
    estimated_balance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(
            Numeric(18, 2),
            nullable=False,
            server_default="0",
        ),
    )
    status: str = Field(default="PENDING", max_length=50, nullable=False)
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

    user: "User" = Relationship(back_populates="accounts")
    transactions: list["Transaction"] = Relationship(back_populates="account")
