"""create user api keys and sessions tables

Revision ID: 0013_create_access_tables
Revises: 0012_create_ai_tables
Create Date: 2026-08-28

Adds per-user hashed API keys, replacing the single INGEST_API_KEY, and session
tracking. Also adds users.role for the role system.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_create_access_tables"
down_revision: str | None = "0012_create_ai_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the access tables and add the user role column."""
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=50),
            server_default="USER",
            nullable=False,
        ),
    )
    op.create_index("idx_users_role", "users", ["role"], unique=False)

    op.create_table(
        "user_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "name",
            sa.String(length=100),
            server_default="default",
            nullable=False,
        ),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("lookup_hash", sa.String(length=64), nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column(
            "is_active",
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
        sa.Column("last_used_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_user_api_keys_user_id", "user_api_keys", ["user_id"], unique=False
    )
    op.create_index(
        "idx_user_api_keys_lookup", "user_api_keys", ["lookup_hash"], unique=True
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_user_sessions_user_id", "user_sessions", ["user_id"], unique=False
    )
    op.create_index(
        "idx_user_sessions_token", "user_sessions", ["token_hash"], unique=False
    )


def downgrade() -> None:
    """Drop the access tables and the user role column."""
    op.drop_index("idx_user_sessions_token", table_name="user_sessions")
    op.drop_index("idx_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("idx_user_api_keys_lookup", table_name="user_api_keys")
    op.drop_index("idx_user_api_keys_user_id", table_name="user_api_keys")
    op.drop_table("user_api_keys")
    op.drop_index("idx_users_role", table_name="users")
    op.drop_column("users", "role")
