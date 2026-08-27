"""create transactions table

Revision ID: 0004_create_transactions_table
Revises: 0003_create_accounts_table
Create Date: 2026-08-27

``raw_event_id``, ``merchant_id`` and ``category_id`` are created without foreign
keys because ``raw_events``, ``merchants`` and ``categories`` arrive in Sprints 4,
6 and 7. Those migrations add the constraints; the column types are already
correct, so no data rewrite is needed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_create_transactions_table"
down_revision: str | None = "0003_create_accounts_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the transactions table."""
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="INR",
            nullable=False,
        ),
        sa.Column("exchange_rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("base_currency", sa.String(length=3), nullable=True),
        sa.Column("base_currency_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column(
            "business_type",
            sa.String(length=50),
            server_default="UNKNOWN",
            nullable=False,
        ),
        sa.Column("merchant_raw", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reference_number", sa.String(length=255), nullable=True),
        sa.Column("upi_id", sa.String(length=255), nullable=True),
        sa.Column(
            "transaction_timestamp",
            sa.DateTime(timezone=False),
            nullable=True,
        ),
        sa.Column(
            "sms_received_timestamp",
            sa.DateTime(timezone=False),
            nullable=True,
        ),
        sa.Column("transaction_fingerprint", sa.String(length=255), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "is_reviewed",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="ACTIVE",
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
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount >= 0", name="chk_transaction_amount_positive"),
        sa.CheckConstraint(
            "direction IN ('DEBIT', 'CREDIT')",
            name="chk_transaction_direction",
        ),
    )
    op.create_index(
        "idx_transactions_user_id", "transactions", ["user_id"], unique=False
    )
    op.create_index(
        "idx_transactions_account_id", "transactions", ["account_id"], unique=False
    )
    op.create_index(
        "idx_transactions_raw_event_id",
        "transactions",
        ["raw_event_id"],
        unique=False,
    )
    op.create_index(
        "idx_transactions_merchant_id",
        "transactions",
        ["merchant_id"],
        unique=False,
    )
    op.create_index(
        "idx_transactions_category_id",
        "transactions",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        "idx_transactions_timestamp",
        "transactions",
        ["transaction_timestamp"],
        unique=False,
    )
    op.create_index(
        "idx_transactions_business_type",
        "transactions",
        ["business_type"],
        unique=False,
    )
    op.create_index(
        "idx_transactions_direction", "transactions", ["direction"], unique=False
    )
    op.create_index(
        "idx_transactions_fingerprint",
        "transactions",
        ["transaction_fingerprint"],
        unique=False,
    )
    op.create_index(
        "uq_transaction_fingerprint_user",
        "transactions",
        ["user_id", "transaction_fingerprint"],
        unique=True,
        postgresql_where=sa.text("transaction_fingerprint IS NOT NULL"),
    )


def downgrade() -> None:
    """Drop the transactions table."""
    op.drop_index("uq_transaction_fingerprint_user", table_name="transactions")
    op.drop_index("idx_transactions_fingerprint", table_name="transactions")
    op.drop_index("idx_transactions_direction", table_name="transactions")
    op.drop_index("idx_transactions_business_type", table_name="transactions")
    op.drop_index("idx_transactions_timestamp", table_name="transactions")
    op.drop_index("idx_transactions_category_id", table_name="transactions")
    op.drop_index("idx_transactions_merchant_id", table_name="transactions")
    op.drop_index("idx_transactions_raw_event_id", table_name="transactions")
    op.drop_index("idx_transactions_account_id", table_name="transactions")
    op.drop_index("idx_transactions_user_id", table_name="transactions")
    op.drop_table("transactions")
