"""seed system categories

Revision ID: 0009_seed_system_categories
Revises: 0008_create_categories_table
Create Date: 2026-08-27

Seeds the default categories from 04-database_schema.md section 6. System
categories have user_id IS NULL and is_system = TRUE, so every user shares them.

The insert skips names that already exist, so re-running on a database that was
seeded by an earlier deploy is safe.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_seed_system_categories"
down_revision: str | None = "0008_create_categories_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYSTEM_CATEGORIES = (
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Health",
    "Travel",
    "Entertainment",
    "Salary",
    "Investment",
    "Transfer",
    "Loan",
    "EMI",
    "Refund",
    "Miscellaneous",
)


def upgrade() -> None:
    """Insert the default system categories."""
    connection = op.get_bind()
    existing = {
        row[0]
        for row in connection.execute(
            sa.text("SELECT name FROM categories WHERE user_id IS NULL")
        )
    }

    rows = [
        {"id": str(uuid.uuid4()), "name": name}
        for name in SYSTEM_CATEGORIES
        if name not in existing
    ]
    if not rows:
        return

    connection.execute(
        sa.text(
            "INSERT INTO categories (id, user_id, name, is_system) "
            "VALUES (:id, NULL, :name, TRUE)"
        ),
        rows,
    )


def downgrade() -> None:
    """Remove the seeded system categories.

    Only rows still marked as system categories are removed, and only by the
    seeded names, so a user category that happens to share a name is untouched.
    """
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM categories "
            "WHERE user_id IS NULL AND is_system = TRUE AND name IN :names"
        ).bindparams(sa.bindparam("names", expanding=True)),
        {"names": list(SYSTEM_CATEGORIES)},
    )
