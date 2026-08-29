from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Text, UniqueConstraint, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domains.accounts.models import Account
    from app.domains.transactions.models import Transaction


class User(SQLModel, table=True):
    """Database entity for platform users."""

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_email", "email", unique=True),
        Index("idx_users_telegram_chat_id", "telegram_chat_id"),
        Index("idx_users_role", "role"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(max_length=255, nullable=False)
    password_hash: str = Field(sa_column=Column(Text, nullable=False))
    display_name: str = Field(max_length=255, nullable=False)
    telegram_chat_id: str | None = Field(default=None, max_length=100)
    timezone: str = Field(default="Asia/Kolkata", max_length=100, nullable=False)
    default_currency: str = Field(default="INR", max_length=3, nullable=False)
    role: str = Field(default="USER", max_length=50, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
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
    deleted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
    )

    settings: "UserSettings" = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False},
    )
    accounts: list["Account"] = Relationship(back_populates="user")
    transactions: list["Transaction"] = Relationship(back_populates="user")


class UserSettings(SQLModel, table=True):
    """Database entity for per-user preferences."""

    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_settings_user"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    notification_mode: str = Field(
        default="LOW_CONFIDENCE_ONLY",
        max_length=50,
        nullable=False,
    )
    ai_suggestions_enabled: bool = Field(default=False, nullable=False)
    historical_import_mode: str | None = Field(default=None, max_length=50)
    preferred_language: str = Field(default="en", max_length=20, nullable=False)
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

    user: User = Relationship(back_populates="settings")


from app.domains.accounts.models import Account  # noqa: E402,F401
from app.domains.transactions.models import Transaction  # noqa: E402,F401
