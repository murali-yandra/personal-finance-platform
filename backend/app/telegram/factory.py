"""Construction of the Telegram transport from configuration."""

import logging

from app.config import Settings
from app.telegram.client import (
    HttpTelegramClient,
    NullTelegramClient,
    TelegramClient,
)

logger = logging.getLogger(__name__)


def build_telegram_client(settings: Settings) -> TelegramClient:
    """Return the transport implied by configuration.

    Returns the null transport when Telegram is disabled or no token is set, so
    a half-configured deployment degrades to silence rather than erroring on
    every transaction.
    """
    if not settings.enable_telegram:
        return NullTelegramClient()

    token = settings.telegram_bot_token.get_secret_value()
    if not token:
        logger.warning("ENABLE_TELEGRAM is set but TELEGRAM_BOT_TOKEN is empty.")
        return NullTelegramClient()

    return HttpTelegramClient(bot_token=token)
