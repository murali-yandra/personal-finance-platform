from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Text, func
from sqlmodel import Field, SQLModel


class UserApiKey(SQLModel, table=True):
    """A per-user ingestion key, stored only as a hash.

    ``10-security_standards.md`` section 7 requires hashed API keys and forbids
    storing the plaintext. The key is shown to the user once at creation and is
    unrecoverable afterwards; a lost key is rotated, not looked up.

    ``key_prefix`` is a short non-secret fragment so a user can tell their keys
    apart in a list without the platform holding the secret.
    """

    __tablename__ = "user_api_keys"
    __table_args__ = (
        Index("idx_user_api_keys_user_id", "user_id"),
        Index("idx_user_api_keys_lookup", "lookup_hash", unique=True),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)

    name: str = Field(default="default", max_length=100, nullable=False)
    key_prefix: str = Field(max_length=16, nullable=False)

    # A deterministic digest, used to find the candidate row. The verifying
    # hash below is what actually authenticates.
    lookup_hash: str = Field(max_length=64, nullable=False)
    key_hash: str = Field(sa_column=Column(Text, nullable=False))

    is_active: bool = Field(default=True, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=False),
            nullable=False,
            server_default=func.now(),
        )
    )
    last_used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
    )
    revoked_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
    )


class UserSession(SQLModel, table=True):
    """A record of an issued login session.

    Session tracking is what makes "sign out everywhere" and suspicious-login
    review possible. Only a hash of the refresh token is stored, for the same
    reason passwords are hashed.
    """

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_token", "token_hash"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)

    token_hash: str = Field(max_length=64, nullable=False)

    ip_address: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=255)

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=False),
            nullable=False,
            server_default=func.now(),
        )
    )
    last_seen_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
    )
    expires_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
    )
    revoked_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
    )

    @property
    def is_active(self) -> bool:
        """Return whether this session may still be used."""
        return self.revoked_at is None
