"""Per-user ingestion API keys.

Replaces the single ``INGEST_API_KEY`` from Sprint 4. Keys are stored hashed,
per ``10-security_standards.md`` section 7.

Authentication is two-step: a deterministic SHA-256 lookup hash finds the
candidate row, then Argon2 verifies the secret. A pure Argon2 scheme would need
one expensive verification per stored key on every request; a pure SHA-256
scheme would leave the keys vulnerable if the table leaked. This gets a single
indexed lookup and a slow, salted verification.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.core.security import SecurityService
from app.domains.access.models import UserApiKey

KEY_PREFIX = "pfp"
KEY_BYTES = 32
PREFIX_LENGTH = 12


@dataclass(frozen=True)
class IssuedApiKey:
    """A newly created key, including the plaintext shown only once."""

    record: UserApiKey
    plaintext: str


class ApiKeyService:
    """Issues, verifies and revokes per-user API keys."""

    def __init__(
        self,
        session: Session,
        security_service: SecurityService | None = None,
    ) -> None:
        self._session = session
        self._security = security_service or SecurityService()

    def issue(self, user_id: UUID, name: str = "default") -> IssuedApiKey:
        """Create a key and return the plaintext once."""
        plaintext = f"{KEY_PREFIX}_{secrets.token_urlsafe(KEY_BYTES)}"

        record = UserApiKey(
            user_id=user_id,
            name=name.strip() or "default",
            key_prefix=plaintext[:PREFIX_LENGTH],
            lookup_hash=lookup_hash(plaintext),
            # An API key is a credential, so it gets the same salted, slow
            # hashing a password does.
            key_hash=self._security.hash_secret(plaintext),
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return IssuedApiKey(record=record, plaintext=plaintext)

    def authenticate(self, plaintext: str) -> UserApiKey | None:
        """Return the active key matching this secret, or ``None``."""
        if not plaintext:
            return None

        statement = select(UserApiKey).where(
            UserApiKey.lookup_hash == lookup_hash(plaintext),
            UserApiKey.revoked_at.is_(None),  # type: ignore[union-attr]
        )
        record = self._session.exec(statement).first()
        if record is None or not record.is_active:
            return None

        if not self._security.verify_secret(plaintext, record.key_hash):
            return None

        record.last_used_at = datetime.now(UTC).replace(tzinfo=None)
        self._session.add(record)
        self._session.commit()
        return record

    def list_keys(self, user_id: UUID) -> list[UserApiKey]:
        """Return a user's keys, newest first. Never returns a secret."""
        statement = (
            select(UserApiKey)
            .where(UserApiKey.user_id == user_id)
            .order_by(UserApiKey.created_at.desc(), UserApiKey.id)  # type: ignore[attr-defined]
        )
        return list(self._session.exec(statement).all())

    def revoke(self, user_id: UUID, key_id: UUID) -> UserApiKey | None:
        """Revoke a key the user owns."""
        statement = select(UserApiKey).where(
            UserApiKey.id == key_id,
            UserApiKey.user_id == user_id,
        )
        record = self._session.exec(statement).first()
        if record is None:
            return None

        record.is_active = False
        record.revoked_at = datetime.now(UTC).replace(tzinfo=None)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record


def lookup_hash(plaintext: str) -> str:
    """Return the deterministic digest used to find a key row."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
