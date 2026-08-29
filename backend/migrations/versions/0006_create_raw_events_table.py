"""create raw events table

Revision ID: 0006_create_raw_events_table
Revises: 0005_create_audit_log_table
Create Date: 2026-08-27

Also attaches the transactions.raw_event_id foreign key, which migration 0004
deliberately left off because this table did not exist yet.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_create_raw_events_table"
down_revision: str | None = "0005_create_audit_log_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the raw_events table and link transactions to it."""
    op.create_table(
        "raw_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("sender", sa.String(length=255), nullable=True),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("message_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(length=50),
            server_default="RECEIVED",
            nullable=False,
        ),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_raw_events_user_id", "raw_events", ["user_id"], unique=False)
    op.create_index("idx_raw_events_hash", "raw_events", ["message_hash"], unique=False)
    op.create_index(
        "idx_raw_events_received_at", "raw_events", ["received_at"], unique=False
    )
    op.create_index(
        "idx_raw_events_status", "raw_events", ["processing_status"], unique=False
    )
    op.create_index(
        "idx_raw_events_correlation_id",
        "raw_events",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        "uq_raw_events_user_message_hash",
        "raw_events",
        ["user_id", "message_hash"],
        unique=True,
    )
    op.create_foreign_key(
        "fk_transactions_raw_event_id",
        "transactions",
        "raw_events",
        ["raw_event_id"],
        ["id"],
    )


def downgrade() -> None:
    """Drop the raw_events table and its transaction link."""
    op.drop_constraint(
        "fk_transactions_raw_event_id", "transactions", type_="foreignkey"
    )
    op.drop_index("uq_raw_events_user_message_hash", table_name="raw_events")
    op.drop_index("idx_raw_events_correlation_id", table_name="raw_events")
    op.drop_index("idx_raw_events_status", table_name="raw_events")
    op.drop_index("idx_raw_events_received_at", table_name="raw_events")
    op.drop_index("idx_raw_events_hash", table_name="raw_events")
    op.drop_index("idx_raw_events_user_id", table_name="raw_events")
    op.drop_table("raw_events")
