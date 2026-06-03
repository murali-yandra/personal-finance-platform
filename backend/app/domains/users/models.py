from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Text, func
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """Database entity for platform users."""

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_email", "email", unique=True),
        Index("idx_users_telegram_chat_id", "telegram_chat_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(max_length=255, nullable=False)
    password_hash: str = Field(sa_column=Column(Text, nullable=False))
    display_name: str = Field(max_length=255, nullable=False)
    telegram_chat_id: str | None = Field(default=None, max_length=100)
    timezone: str = Field(default="Asia/Kolkata", max_length=100, nullable=False)
    default_currency: str = Field(default="INR", max_length=3, nullable=False)
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
