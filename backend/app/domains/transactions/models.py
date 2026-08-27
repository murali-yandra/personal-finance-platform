from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Numeric,
    Text,
    func,
)
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domains.accounts.models import Account
    from app.domains.users.models import User


class Transaction(SQLModel, table=True):
    """Database entity for financial transactions.

    ``merchant_id`` and ``category_id`` are still plain UUID columns. Those
    tables arrive in Sprints 6 and 7, whose migrations attach the foreign keys;
    the column types are already correct, so no data rewrite is needed.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_transaction_amount_positive"),
        CheckConstraint(
            "direction IN ('DEBIT', 'CREDIT')",
            name="chk_transaction_direction",
        ),
        Index("idx_transactions_user_id", "user_id"),
        Index("idx_transactions_account_id", "account_id"),
        Index("idx_transactions_raw_event_id", "raw_event_id"),
        Index("idx_transactions_merchant_id", "merchant_id"),
        Index("idx_transactions_category_id", "category_id"),
        Index("idx_transactions_timestamp", "transaction_timestamp"),
        Index("idx_transactions_business_type", "business_type"),
        Index("idx_transactions_direction", "direction"),
        Index("idx_transactions_fingerprint", "transaction_fingerprint"),
        Index(
            "uq_transaction_fingerprint_user",
            "user_id",
            "transaction_fingerprint",
            unique=True,
            postgresql_where=Column("transaction_fingerprint").isnot(None),
            sqlite_where=Column("transaction_fingerprint").isnot(None),
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    account_id: UUID = Field(foreign_key="accounts.id", nullable=False)
    raw_event_id: UUID | None = Field(default=None, foreign_key="raw_events.id")
    merchant_id: UUID | None = Field(default=None)
    category_id: UUID | None = Field(default=None)

    amount: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    currency: str = Field(default="INR", max_length=3, nullable=False)

    exchange_rate: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(18, 6), nullable=True),
    )
    base_currency: str | None = Field(default=None, max_length=3)
    base_currency_amount: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(18, 2), nullable=True),
    )

    direction: str = Field(max_length=20, nullable=False)
    business_type: str = Field(default="UNKNOWN", max_length=50, nullable=False)

    merchant_raw: str | None = Field(default=None, max_length=255)
    description: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    reference_number: str | None = Field(default=None, max_length=255)
    upi_id: str | None = Field(default=None, max_length=255)

    transaction_timestamp: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
    )
    sms_received_timestamp: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
    )

    transaction_fingerprint: str | None = Field(default=None, max_length=255)

    confidence_score: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(5, 2), nullable=True),
    )
    is_reviewed: bool = Field(default=False, nullable=False)

    status: str = Field(default="ACTIVE", max_length=50, nullable=False)

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

    user: "User" = Relationship(back_populates="transactions")
    account: "Account" = Relationship(back_populates="transactions")
