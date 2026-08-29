"""Handlers for the Telegram bot commands.

Commands are read-only in this sprint. A bot chat is authenticated only by its
chat ID, which is not a credential, so it must not be able to change financial
records (``10-security_standards.md`` section 6).
"""

from dataclasses import dataclass

from app.domains.accounts.repository import AccountRepository
from app.domains.users.models import User
from app.telegram.formatter import format_account_list

START_MESSAGE = (
    "👋 <b>Personal Finance Tracker</b>\n\n"
    "I will notify you when a transaction is detected from your bank SMS.\n\n"
    "Use /help to see what I can do."
)

HELP_MESSAGE = (
    "<b>Commands</b>\n"
    "/start — link this chat\n"
    "/help — show this message\n"
    "/accounts — list your accounts and balances\n"
    "/settings — show your notification settings"
)

UNKNOWN_MESSAGE = "I did not recognize that command. Use /help to see the list."

UNLINKED_MESSAGE = (
    "This chat is not linked to an account yet. "
    "Add your Telegram chat ID in your profile settings first."
)


@dataclass(frozen=True)
class CommandContext:
    """What a command handler needs to build its reply."""

    user: User | None
    account_repository: AccountRepository | None = None


def handle_command(command: str, context: CommandContext) -> str:
    """Return the reply text for a bot command."""
    normalized = command.strip().split()[0].lower() if command.strip() else ""
    normalized = normalized.split("@")[0]

    if normalized == "/start":
        return START_MESSAGE
    if normalized == "/help":
        return HELP_MESSAGE

    if context.user is None:
        return UNLINKED_MESSAGE

    if normalized == "/accounts":
        return _accounts_reply(context)
    if normalized == "/settings":
        return _settings_reply(context)
    return UNKNOWN_MESSAGE


def _accounts_reply(context: CommandContext) -> str:
    if context.account_repository is None or context.user is None:
        return UNLINKED_MESSAGE
    accounts = context.account_repository.list_for_user(
        user_id=context.user.id,
        statuses=None,
    )
    visible = [account for account in accounts if account.status != "ARCHIVED"]
    return format_account_list(visible)


def _settings_reply(context: CommandContext) -> str:
    user = context.user
    if user is None:
        return UNLINKED_MESSAGE
    settings = getattr(user, "settings", None)
    mode = getattr(settings, "notification_mode", "LOW_CONFIDENCE_ONLY")
    ai_enabled = bool(getattr(settings, "ai_suggestions_enabled", False))
    return (
        "<b>Your settings</b>\n"
        f"Notifications: {mode}\n"
        f"AI suggestions: {'on' if ai_enabled else 'off'}\n"
        f"Timezone: {user.timezone}\n"
        f"Currency: {user.default_currency}"
    )
