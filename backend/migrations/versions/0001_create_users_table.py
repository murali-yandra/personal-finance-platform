"""create users table

Revision ID: 0001_create_users_table
Revises:
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_create_users_table"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the users table."""
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("telegram_chat_id", sa.String(length=100), nullable=True),
        sa.Column(
            "timezone",
            sa.String(length=100),
            server_default="Asia/Kolkata",
            nullable=False,
        ),
        sa.Column(
            "default_currency",
            sa.String(length=3),
            server_default="INR",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=False), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index(
        "idx_users_telegram_chat_id",
        "users",
        ["telegram_chat_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the users table."""
    op.drop_index("idx_users_telegram_chat_id", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
