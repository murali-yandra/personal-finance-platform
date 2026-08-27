from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, func
from sqlmodel import Field, SQLModel


class Category(SQLModel, table=True):
    """A spending category, either seeded by the system or created by a user.

    A system category has ``user_id IS NULL`` and ``is_system = True``; it is
    shared by every user and cannot be edited or deleted. A user category is
    owned by exactly one user.
    """

    __tablename__ = "categories"
    __table_args__ = (
        Index("idx_categories_user_id", "user_id"),
        Index("idx_categories_parent", "parent_category_id"),
        Index("idx_categories_name", "name"),
        # Two partial unique indexes rather than one composite: a plain unique
        # on (user_id, name) would not constrain system rows, because NULL is
        # never equal to NULL in SQL.
        Index(
            "uq_system_category_name",
            "name",
            unique=True,
            postgresql_where=Column("user_id").is_(None),
            sqlite_where=Column("user_id").is_(None),
        ),
        Index(
            "uq_user_category_name",
            "user_id",
            "name",
            unique=True,
            postgresql_where=Column("user_id").isnot(None),
            sqlite_where=Column("user_id").isnot(None),
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID | None = Field(default=None, foreign_key="users.id")

    name: str = Field(max_length=255, nullable=False)
    parent_category_id: UUID | None = Field(
        default=None,
        foreign_key="categories.id",
    )

    is_system: bool = Field(default=False, nullable=False)

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
