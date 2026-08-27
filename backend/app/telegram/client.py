"""Telegram transport.

Every implementation satisfies ``TelegramClient``, so the notifier and the
command handlers never learn whether messages actually leave the process. That
is what lets the whole feature be tested without a bot token, and what lets it
ship disabled by default.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT_SECONDS = 10.0


class TelegramClient(Protocol):
    """Sends a message to a Telegram chat."""

    def send_message(self, chat_id: str, text: str) -> bool:
        """Send text to a chat, returning whether it was delivered."""
        ...


class NullTelegramClient:
    """Client used when Telegram is disabled.

    Returning ``False`` rather than raising keeps every caller on one code path:
    a disabled integration behaves exactly like an unreachable one.
    """

    def send_message(self, chat_id: str, text: str) -> bool:
        """Discard the message."""
        logger.debug("Telegram disabled; dropping message to %s", chat_id)
        return False


@dataclass
class FakeTelegramClient:
    """In-memory client that records what would have been sent."""

    sent: list[tuple[str, str]] = field(default_factory=list)
    should_fail: bool = False

    def send_message(self, chat_id: str, text: str) -> bool:
        """Record the message, or simulate a delivery failure."""
        if self.should_fail:
            raise RuntimeError("Telegram unavailable")
        self.sent.append((chat_id, text))
        return True

    @property
    def messages(self) -> list[str]:
        """Return just the message bodies, in order."""
        return [text for _, text in self.sent]


class HttpTelegramClient:
    """Client that calls the Telegram Bot API over HTTPS."""

    def __init__(
        self,
        bot_token: str,
        base_url: str = TELEGRAM_API_BASE,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._bot_token = bot_token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def send_message(self, chat_id: str, text: str) -> bool:
        """Send text to a chat.

        A transport failure is logged and reported, never raised: Telegram being
        down must not fail the request that triggered the notification
        (``09-error_handling_standards.md`` section 13).
        """
        url = f"{self._base_url}/bot{self._bot_token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            response = httpx.post(url, json=payload, timeout=self._timeout)
        except httpx.HTTPError as exc:
            logger.warning("Telegram request failed: %s", exc)
            return False

        if response.status_code >= 400:
            # The bot token is in the URL, so the URL is never logged.
            logger.warning(
                "Telegram rejected the message with status %s",
                response.status_code,
            )
            return False
        return True
