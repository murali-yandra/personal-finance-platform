"""API key authentication for the ingestion endpoints.

MacroDroid cannot hold a JWT, so ingestion authenticates with a shared key sent
as ``X-API-KEY`` (``10-security_standards.md`` section 7). The owning user comes
from configuration; per-user hashed keys arrive in Sprint 15.
"""

import secrets
from typing import Annotated

from fastapi import Depends, Header
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.db.session import get_session
from app.domains.ingestion.exceptions import (
    IngestionUserNotConfiguredError,
    InvalidApiKeyError,
)
from app.domains.users.models import User

API_KEY_HEADER = "X-API-KEY"


def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> None:
    """Reject a request whose API key is missing or wrong.

    The comparison is constant-time so a caller cannot recover the key by timing
    responses.
    """
    configured = (settings or get_settings()).ingest_api_key.get_secret_value()
    if not x_api_key or not secrets.compare_digest(x_api_key, configured):
        raise InvalidApiKeyError()


def get_ingestion_user(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[None, Depends(verify_api_key)] = None,
) -> User:
    """Return the user that owns ingested messages."""
    settings = get_settings()
    email = (settings.ingest_user_email or "").strip().lower()
    if not email:
        raise IngestionUserNotConfiguredError()

    user = session.exec(select(User).where(User.email == email)).first()
    if user is None or not user.is_active or user.deleted_at is not None:
        raise IngestionUserNotConfiguredError()
    return user
