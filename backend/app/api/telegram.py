"""Telegram webhook.

The webhook is authenticated by Telegram's secret-token header rather than a
JWT, so its path is listed in ``PUBLIC_PATHS``. It is not public: an
unauthenticated caller is rejected here.
"""

import logging
import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.db.session import get_session
from app.domains.accounts.repository import AccountRepository
from app.domains.ingestion.exceptions import InvalidApiKeyError
from app.domains.users.models import User
from app.shared.schemas.responses import SuccessResponse
from app.telegram.client import NullTelegramClient
from app.telegram.commands import CommandContext, handle_command
from app.telegram.factory import build_telegram_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

SECRET_TOKEN_HEADER = "X-Telegram-Bot-Api-Secret-Token"


class WebhookAcknowledgement(BaseModel):
    """Response data for a processed webhook update."""

    handled: bool


WebhookResponse = SuccessResponse[WebhookAcknowledgement]


def verify_webhook_secret(
    secret_token: Annotated[
        str | None,
        Header(alias=SECRET_TOKEN_HEADER),
    ] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> None:
    """Reject an update that does not carry the configured secret token."""
    resolved = settings or get_settings()
    configured = resolved.telegram_webhook_secret.get_secret_value()
    if not configured:
        # Refuse rather than accept anything when no secret is configured, so a
        # misconfiguration cannot silently expose the webhook.
        raise InvalidApiKeyError()
    if not secret_token or not secrets.compare_digest(secret_token, configured):
        raise InvalidApiKeyError()


@router.post("/webhook", response_model=WebhookResponse)
def telegram_webhook(
    update: dict[str, Any],
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[None, Depends(verify_webhook_secret)],
) -> WebhookResponse:
    """Handle one Telegram update.

    Errors are never surfaced to Telegram: a non-2xx response makes Telegram
    retry the same update indefinitely.
    """
    try:
        handled = _handle_update(update, session)
    except Exception:
        logger.exception("Failed to handle Telegram update.")
        handled = False
    return WebhookResponse(data=WebhookAcknowledgement(handled=handled))


def _handle_update(update: dict[str, Any], session: Session) -> bool:
    message = update.get("message") or update.get("edited_message") or {}
    text = str(message.get("text") or "").strip()
    chat_id = _chat_id(message)

    if not text or not chat_id:
        return False

    user = session.exec(select(User).where(User.telegram_chat_id == chat_id)).first()

    reply = handle_command(
        text,
        CommandContext(
            user=user,
            account_repository=AccountRepository(session),
        ),
    )

    settings = get_settings()
    client = (
        build_telegram_client(settings)
        if settings.enable_telegram
        else NullTelegramClient()
    )
    client.send_message(chat_id, reply)
    return True


def _chat_id(message: dict[str, Any]) -> str | None:
    chat = message.get("chat") or {}
    raw = chat.get("id")
    if raw is None:
        return None
    return str(raw)
