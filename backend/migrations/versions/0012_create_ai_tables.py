"""create ai suggestions and user feedback tables

Revision ID: 0012_create_ai_tables
Revises: 0011_create_transfers_table
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_create_ai_tables"
down_revision: str | None = "0011_create_transfers_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the ai_suggestions and user_feedback tables."""
    op.create_table(
        "ai_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("suggestion_type", sa.String(length=50), nullable=False),
        sa.Column("suggested_value", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
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
        sa.Column("reviewed_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_ai_suggestions_user_id", "ai_suggestions", ["user_id"], unique=False
    )
    op.create_index(
        "idx_ai_suggestions_transaction_id",
        "ai_suggestions",
        ["transaction_id"],
        unique=False,
    )
    op.create_index(
        "idx_ai_suggestions_status", "ai_suggestions", ["status"], unique=False
    )

    op.create_table(
        "user_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("feedback_type", sa.String(length=50), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column(
            "source",
            sa.String(length=50),
            server_default="USER",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_user_feedback_user_id", "user_feedback", ["user_id"], unique=False
    )
    op.create_index(
        "idx_user_feedback_transaction_id",
        "user_feedback",
        ["transaction_id"],
        unique=False,
    )
    op.create_index(
        "idx_user_feedback_type", "user_feedback", ["feedback_type"], unique=False
    )


def downgrade() -> None:
    """Drop the AI tables."""
    op.drop_index("idx_user_feedback_type", table_name="user_feedback")
    op.drop_index("idx_user_feedback_transaction_id", table_name="user_feedback")
    op.drop_index("idx_user_feedback_user_id", table_name="user_feedback")
    op.drop_table("user_feedback")
    op.drop_index("idx_ai_suggestions_status", table_name="ai_suggestions")
    op.drop_index("idx_ai_suggestions_transaction_id", table_name="ai_suggestions")
    op.drop_index("idx_ai_suggestions_user_id", table_name="ai_suggestions")
    op.drop_table("ai_suggestions")
