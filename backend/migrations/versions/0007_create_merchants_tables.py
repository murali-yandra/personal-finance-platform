"""create merchants and merchant patterns tables

Revision ID: 0007_create_merchants_tables
Revises: 0006_create_raw_events_table
Create Date: 2026-08-27

Attaches the transactions.merchant_id foreign key that migration 0004 left off.
merchants.default_category_id stays unconstrained until 0008 creates categories.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_create_merchants_tables"
down_revision: str | None = "0006_create_raw_events_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the merchants and merchant_patterns tables."""
    op.create_table(
        "merchants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("merchant_name", sa.String(length=255), nullable=False),
        sa.Column("merchant_group", sa.String(length=255), nullable=True),
        sa.Column("default_category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "is_global",
            sa.Boolean(),
            server_default=sa.true(),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_merchants_name", "merchants", ["merchant_name"], unique=False)
    op.create_index(
        "idx_merchants_group", "merchants", ["merchant_group"], unique=False
    )

    op.create_table(
        "merchant_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pattern", sa.String(length=255), nullable=False),
        sa.Column(
            "pattern_type",
            sa.String(length=50),
            server_default="LIKE",
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Numeric(5, 2),
            server_default="1.00",
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.String(length=50),
            server_default="SYSTEM",
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
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_merchant_patterns_user_id",
        "merchant_patterns",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_merchant_patterns_pattern",
        "merchant_patterns",
        ["pattern"],
        unique=False,
    )
    op.create_index(
        "idx_merchant_patterns_merchant_id",
        "merchant_patterns",
        ["merchant_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_transactions_merchant_id",
        "transactions",
        "merchants",
        ["merchant_id"],
        ["id"],
    )


def downgrade() -> None:
    """Drop the merchant tables and the transaction link."""
    op.drop_constraint(
        "fk_transactions_merchant_id", "transactions", type_="foreignkey"
    )
    op.drop_index("idx_merchant_patterns_merchant_id", table_name="merchant_patterns")
    op.drop_index("idx_merchant_patterns_pattern", table_name="merchant_patterns")
    op.drop_index("idx_merchant_patterns_user_id", table_name="merchant_patterns")
    op.drop_table("merchant_patterns")
    op.drop_index("idx_merchants_group", table_name="merchants")
    op.drop_index("idx_merchants_name", table_name="merchants")
    op.drop_table("merchants")
