"""create mfa tables

Revision ID: 0014_create_mfa_tables
Revises: 0013_create_access_tables
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_create_mfa_tables"
down_revision: str | None = "0013_create_access_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the user_mfa and mfa_recovery_codes tables."""
    op.create_table(
        "user_mfa",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("secret", sa.Text(), nullable=False),
        sa.Column(
            "is_enabled",
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
        sa.Column("confirmed_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # One second factor per user, enforced by the database rather than by
    # convention, so a concurrent double enrolment cannot leave two secrets.
    op.create_index("idx_user_mfa_user_id", "user_mfa", ["user_id"], unique=True)

    op.create_table(
        "mfa_recovery_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mfa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("used_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["mfa_id"], ["user_mfa.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_mfa_recovery_codes_mfa_id",
        "mfa_recovery_codes",
        ["mfa_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the MFA tables."""
    op.drop_index("idx_mfa_recovery_codes_mfa_id", table_name="mfa_recovery_codes")
    op.drop_table("mfa_recovery_codes")
    op.drop_index("idx_user_mfa_user_id", table_name="user_mfa")
    op.drop_table("user_mfa")
