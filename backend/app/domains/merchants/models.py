from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Numeric, func
from sqlmodel import Field, SQLModel


class Merchant(SQLModel, table=True):
    """A normalized merchant, such as Swiggy or Amazon.

    ``default_category_id`` points at the category assigned when nothing more
    specific applies; migration 0008 attached the constraint.
    """

    __tablename__ = "merchants"
    __table_args__ = (
        Index("idx_merchants_name", "merchant_name"),
        Index("idx_merchants_group", "merchant_group"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    merchant_name: str = Field(max_length=255, nullable=False)
    merchant_group: str | None = Field(default=None, max_length=255)
    default_category_id: UUID | None = Field(
        default=None,
        foreign_key="categories.id",
    )
    is_global: bool = Field(default=True, nullable=False)

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


class MerchantPattern(SQLModel, table=True):
    """A rule that maps a raw merchant string onto a merchant.

    A pattern with ``user_id IS NULL`` is global. A pattern owned by a user
    always wins over a global one, so a personal correction is never overridden
    by a shared rule.
    """

    __tablename__ = "merchant_patterns"
    __table_args__ = (
        Index("idx_merchant_patterns_user_id", "user_id"),
        Index("idx_merchant_patterns_pattern", "pattern"),
        Index("idx_merchant_patterns_merchant_id", "merchant_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID | None = Field(default=None, foreign_key="users.id")
    merchant_id: UUID = Field(foreign_key="merchants.id", nullable=False)

    pattern: str = Field(max_length=255, nullable=False)
    pattern_type: str = Field(default="LIKE", max_length=50, nullable=False)

    confidence: Decimal = Field(
        default=Decimal("1.00"),
        sa_column=Column(Numeric(5, 2), nullable=False, server_default="1.00"),
    )

    created_by: str = Field(default="SYSTEM", max_length=50, nullable=False)

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
