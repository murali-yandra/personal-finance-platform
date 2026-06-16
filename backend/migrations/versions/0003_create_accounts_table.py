"""create accounts table

Revision ID: 0003_create_accounts_table
Revises: 0002_create_user_settings_table
Create Date: 2026-06-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_create_accounts_table"
down_revision: str | None = "0002_create_user_settings_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the accounts table."""
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("account_type", sa.String(length=50), nullable=False),
        sa.Column("bank_name", sa.String(length=100), nullable=True),
        sa.Column("last_four_digits", sa.String(length=10), nullable=True),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="INR",
            nullable=False,
        ),
        sa.Column(
            "opening_balance",
            sa.Numeric(18, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "estimated_balance",
            sa.Numeric(18, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="PENDING",
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
        sa.UniqueConstraint(
            "user_id",
            "bank_name",
            "last_four_digits",
            "account_type",
            name="uq_user_bank_lastfour_type",
        ),
    )
    op.create_index("idx_accounts_user_id", "accounts", ["user_id"], unique=False)
    op.create_index("idx_accounts_status", "accounts", ["status"], unique=False)
    op.create_index(
        "idx_accounts_bank_last_four",
        "accounts",
        ["bank_name", "last_four_digits"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the accounts table."""
    op.drop_index("idx_accounts_bank_last_four", table_name="accounts")
    op.drop_index("idx_accounts_status", table_name="accounts")
    op.drop_index("idx_accounts_user_id", table_name="accounts")
    op.drop_table("accounts")
