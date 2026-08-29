"""create balance snapshots table

Revision ID: 0010_create_balance_snapshots
Revises: 0009_seed_system_categories
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_create_balance_snapshots"
down_revision: str | None = "0009_seed_system_categories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the balance_snapshots table."""
    op.create_table(
        "balance_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="INR",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "snapshot_date",
            name="uq_balance_snapshot_account_date",
        ),
    )
    op.create_index(
        "idx_balance_snapshots_user_id",
        "balance_snapshots",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_balance_snapshots_account_id",
        "balance_snapshots",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "idx_balance_snapshots_date",
        "balance_snapshots",
        ["snapshot_date"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the balance_snapshots table."""
    op.drop_index("idx_balance_snapshots_date", table_name="balance_snapshots")
    op.drop_index("idx_balance_snapshots_account_id", table_name="balance_snapshots")
    op.drop_index("idx_balance_snapshots_user_id", table_name="balance_snapshots")
    op.drop_table("balance_snapshots")
