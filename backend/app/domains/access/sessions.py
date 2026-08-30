"""Login session tracking.

A session row is created for every issued refresh token and checked whenever
that token is exchanged. This is what makes revocation possible at all: a JWT
is self-validating, so without a server-side record a stolen refresh token
stays usable for its full 30-day life and "sign out everywhere" cannot work.

Only a SHA-256 digest of the token is stored, for the same reason passwords are
hashed: a leaked sessions table must not hand over working credentials.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlmodel import Session, select

from app.core.jwt import REFRESH_TOKEN_EXPIRE_DAYS
from app.domains.access.models import UserSession

MAX_USER_AGENT_LENGTH = 255


class SessionService:
    """Creates, validates and revokes login sessions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def start(
        self,
        user_id: UUID,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession:
        """Record a newly issued refresh token."""
        now = _now()
        record = UserSession(
            user_id=user_id,
            token_hash=token_hash(refresh_token),
            ip_address=(ip_address or None),
            user_agent=(user_agent or "")[:MAX_USER_AGENT_LENGTH] or None,
            last_seen_at=now,
            expires_at=now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def validate(self, refresh_token: str) -> UserSession | None:
        """Return the live session for a refresh token, or ``None``.

        A token whose session is missing, revoked or expired is refused even
        though the JWT itself still verifies. That gap is the whole point of
        tracking sessions.
        """
        statement = select(UserSession).where(
            UserSession.token_hash == token_hash(refresh_token)
        )
        record = self._session.exec(statement).first()
        if record is None or record.revoked_at is not None:
            return None
        if record.expires_at is not None and record.expires_at <= _now():
            return None

        record.last_seen_at = _now()
        self._session.add(record)
        self._session.commit()
        return record

    def list_sessions(
        self,
        user_id: UUID,
        include_revoked: bool = False,
    ) -> list[UserSession]:
        """Return a user's sessions, newest first."""
        statement = select(UserSession).where(UserSession.user_id == user_id)
        if not include_revoked:
            statement = statement.where(
                UserSession.revoked_at.is_(None)  # type: ignore[union-attr]
            )
        statement = statement.order_by(
            UserSession.created_at.desc(),  # type: ignore[attr-defined]
            UserSession.id,
        )
        return list(self._session.exec(statement).all())

    def revoke(self, user_id: UUID, session_id: UUID) -> UserSession | None:
        """Revoke one session the user owns."""
        statement = select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == user_id,
        )
        record = self._session.exec(statement).first()
        if record is None:
            return None
        return self._revoke(record)

    def revoke_by_token(self, refresh_token: str) -> UserSession | None:
        """Revoke the live session for a refresh token. Used by logout.

        Returns ``None`` when there was nothing to revoke, including when the
        session was already revoked, so a caller counting revocations does not
        report the same session twice.
        """
        statement = select(UserSession).where(
            UserSession.token_hash == token_hash(refresh_token)
        )
        record = self._session.exec(statement).first()
        if record is None or record.revoked_at is not None:
            return None
        return self._revoke(record)

    def revoke_all(self, user_id: UUID, except_session_id: UUID | None = None) -> int:
        """Revoke every live session for a user. Returns how many were revoked.

        This is "sign out everywhere". ``except_session_id`` keeps the current
        session alive, so a user reacting to a suspicious login is not logged
        out of the device they are using to react.
        """
        revoked = 0
        for record in self.list_sessions(user_id):
            if except_session_id is not None and record.id == except_session_id:
                continue
            self._revoke(record, commit=False)
            revoked += 1

        if revoked:
            self._session.commit()
        return revoked

    def _revoke(self, record: UserSession, commit: bool = True) -> UserSession:
        if record.revoked_at is None:
            record.revoked_at = _now()
            self._session.add(record)
            if commit:
                self._session.commit()
                self._session.refresh(record)
        return record


def token_hash(refresh_token: str) -> str:
    """Return the digest stored in place of a refresh token."""
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    """Return the current time as naive UTC, matching the schema's columns."""
    return datetime.now(UTC).replace(tzinfo=None)
