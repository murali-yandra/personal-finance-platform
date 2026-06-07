"""create user settings table

Revision ID: 0002_create_user_settings_table
Revises: 0001_create_users_table
Create Date: 2026-06-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_create_user_settings_table"
down_revision: str | None = "0001_create_users_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the user_settings table."""
    op.create_table(
        "user_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "notification_mode",
            sa.String(length=50),
            server_default="LOW_CONFIDENCE_ONLY",
            nullable=False,
        ),
        sa.Column(
            "ai_suggestions_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("historical_import_mode", sa.String(length=50), nullable=True),
        sa.Column(
            "preferred_language",
            sa.String(length=20),
            server_default="en",
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_settings_user"),
    )


def downgrade() -> None:
    """Drop the user_settings table."""
    op.drop_table("user_settings")
