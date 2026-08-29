"""create audit log table

Revision ID: 0005_create_audit_log_table
Revises: 0004_create_transactions_table
Create Date: 2026-08-27

Audit rows are append-only: never updated, never deleted
(04-database_schema.md section 4.12).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_create_audit_log_table"
down_revision: str | None = "0004_create_transactions_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the audit_log table."""
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_log_user_id", "audit_log", ["user_id"], unique=False)
    op.create_index(
        "idx_audit_log_entity",
        "audit_log",
        ["entity_type", "entity_id"],
        unique=False,
    )
    op.create_index("idx_audit_log_action", "audit_log", ["action"], unique=False)
    op.create_index(
        "idx_audit_log_created_at", "audit_log", ["created_at"], unique=False
    )
    op.create_index(
        "idx_audit_log_correlation_id",
        "audit_log",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        "idx_audit_log_request_id", "audit_log", ["request_id"], unique=False
    )


def downgrade() -> None:
    """Drop the audit_log table."""
    op.drop_index("idx_audit_log_request_id", table_name="audit_log")
    op.drop_index("idx_audit_log_correlation_id", table_name="audit_log")
    op.drop_index("idx_audit_log_created_at", table_name="audit_log")
    op.drop_index("idx_audit_log_action", table_name="audit_log")
    op.drop_index("idx_audit_log_entity", table_name="audit_log")
    op.drop_index("idx_audit_log_user_id", table_name="audit_log")
    op.drop_table("audit_log")
