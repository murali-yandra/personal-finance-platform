"""create categories table

Revision ID: 0008_create_categories_table
Revises: 0007_create_merchants_tables
Create Date: 2026-08-27

Attaches the last two deferred foreign keys: transactions.category_id from
migration 0004, and merchants.default_category_id from 0007.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_create_categories_table"
down_revision: str | None = "0007_create_merchants_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the categories table and attach the remaining foreign keys."""
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "is_system",
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
        sa.ForeignKeyConstraint(["parent_category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_categories_user_id", "categories", ["user_id"], unique=False)
    op.create_index(
        "idx_categories_parent", "categories", ["parent_category_id"], unique=False
    )
    op.create_index("idx_categories_name", "categories", ["name"], unique=False)

    # Two partial indexes rather than one composite unique: a plain unique on
    # (user_id, name) would not constrain system rows at all, because NULL is
    # never equal to NULL in SQL.
    op.create_index(
        "uq_system_category_name",
        "categories",
        ["name"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )
    op.create_index(
        "uq_user_category_name",
        "categories",
        ["user_id", "name"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    op.create_foreign_key(
        "fk_transactions_category_id",
        "transactions",
        "categories",
        ["category_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_merchants_default_category_id",
        "merchants",
        "categories",
        ["default_category_id"],
        ["id"],
    )


def downgrade() -> None:
    """Drop the categories table and the foreign keys that point at it."""
    op.drop_constraint(
        "fk_merchants_default_category_id", "merchants", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_transactions_category_id", "transactions", type_="foreignkey"
    )
    op.drop_index("uq_user_category_name", table_name="categories")
    op.drop_index("uq_system_category_name", table_name="categories")
    op.drop_index("idx_categories_name", table_name="categories")
    op.drop_index("idx_categories_parent", table_name="categories")
    op.drop_index("idx_categories_user_id", table_name="categories")
    op.drop_table("categories")
