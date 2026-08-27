"""create transfers table

Revision ID: 0011_create_transfers_table
Revises: 0010_create_balance_snapshots
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_create_transfers_table"
down_revision: str | None = "0010_create_balance_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the transfers table."""
    op.create_table(
        "transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_transaction_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "destination_transaction_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "transfer_type",
            sa.String(length=50),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "is_confirmed",
            sa.Boolean(),
            server_default=sa.false(),
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
        sa.ForeignKeyConstraint(["source_transaction_id"], ["transactions.id"]),
        sa.ForeignKeyConstraint(["destination_transaction_id"], ["transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_transfers_user_id", "transfers", ["user_id"], unique=False)
    op.create_index(
        "idx_transfers_source",
        "transfers",
        ["source_transaction_id"],
        unique=False,
    )
    op.create_index(
        "idx_transfers_destination",
        "transfers",
        ["destination_transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the transfers table."""
    op.drop_index("idx_transfers_destination", table_name="transfers")
    op.drop_index("idx_transfers_source", table_name="transfers")
    op.drop_index("idx_transfers_user_id", table_name="transfers")
    op.drop_table("transfers")
