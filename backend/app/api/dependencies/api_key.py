"""API key authentication for the ingestion endpoints.

MacroDroid cannot hold a JWT, so ingestion authenticates with a key sent as
``X-API-KEY`` (``10-security_standards.md`` section 7).

Two schemes are accepted, in order:

1. A **per-user hashed key** issued through ``/api/v1/api-keys``. This is the
   Sprint 15 scheme: the key identifies its owner directly, and only a hash is
   stored.
2. The single ``INGEST_API_KEY`` from Sprint 4, whose owner comes from
   ``INGEST_USER_EMAIL``.

The environment key is still honoured so an existing deployment keeps working
across the upgrade; it should be removed once every device holds its own key.
"""

import secrets
from typing import Annotated

from fastapi import Depends, Header
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.db.session import get_session
from app.domains.access.api_keys import ApiKeyService
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
    x_api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None,
) -> User:
    """Return the user that owns ingested messages.

    A per-user key identifies its owner directly. The shared environment key
    falls back to the configured INGEST_USER_EMAIL.
    """
    if not x_api_key:
        raise InvalidApiKeyError()

    owned = ApiKeyService(session).authenticate(x_api_key)
    if owned is not None:
        user = session.get(User, owned.user_id)
        if user is None or not user.is_active or user.deleted_at is not None:
            raise InvalidApiKeyError()
        return user

    settings = get_settings()
    configured = settings.ingest_api_key.get_secret_value()
    if not configured or not secrets.compare_digest(x_api_key, configured):
        raise InvalidApiKeyError()

    email = (settings.ingest_user_email or "").strip().lower()
    if not email:
        raise IngestionUserNotConfiguredError()

    user = session.exec(select(User).where(User.email == email)).first()
    if user is None or not user.is_active or user.deleted_at is not None:
        raise IngestionUserNotConfiguredError()
    return user
