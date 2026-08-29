"""Message text for outgoing Telegram notifications.

Formatting is kept separate from sending so the wording is unit-testable without
a transport, and so a change of phrasing never risks the delivery path.
"""

from decimal import Decimal
from html import escape

from app.domains.accounts.models import Account
from app.domains.transactions.models import Transaction
from app.shared.enums import TransactionDirection

CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}

REVIEW_PROMPT = "Reply with a description, or use /accounts to name this account."


def format_amount(amount: Decimal, currency: str = "INR") -> str:
    """Render an amount with its currency symbol."""
    symbol = CURRENCY_SYMBOLS.get(currency.upper(), f"{currency.upper()} ")
    return f"{symbol}{amount:,.2f}"


def format_transaction_notification(
    transaction: Transaction,
    account: Account | None = None,
    needs_review: bool = False,
) -> str:
    """Build the message announcing a new transaction."""
    direction = TransactionDirection(transaction.direction)
    verb = "Debited" if direction is TransactionDirection.DEBIT else "Credited"
    arrow = "🔴" if direction is TransactionDirection.DEBIT else "🟢"

    lines = [
        f"{arrow} <b>{verb} "
        f"{escape(format_amount(transaction.amount, transaction.currency))}</b>"
    ]

    if transaction.merchant_raw:
        lines.append(f"Merchant: {escape(transaction.merchant_raw)}")

    lines.append(f"Account: {escape(_describe_account(account))}")

    if transaction.transaction_timestamp:
        lines.append(f"When: {transaction.transaction_timestamp:%d %b %Y %H:%M}")

    if transaction.business_type and transaction.business_type != "UNKNOWN":
        lines.append(f"Type: {escape(transaction.business_type.title())}")

    if needs_review:
        lines.append("")
        lines.append(f"⚠️ {escape(REVIEW_PROMPT)}")

    return "\n".join(lines)


def format_account_list(accounts: list[Account]) -> str:
    """Build the reply to the /accounts command."""
    if not accounts:
        return "You have no accounts yet. They are created automatically from SMS."

    lines = ["<b>Your accounts</b>"]
    for account in accounts:
        name = account.account_name or _describe_account(account)
        balance = format_amount(account.estimated_balance, account.currency)
        lines.append(f"• {escape(name)} — {escape(balance)} ({account.status})")
    return "\n".join(lines)


def _describe_account(account: Account | None) -> str:
    """Describe an account from whatever identifying details it has."""
    if account is None:
        return "Unknown"
    if account.account_name:
        return account.account_name
    parts = [part for part in (account.bank_name, account.last_four_digits) if part]
    return " ".join(parts) if parts else account.account_type
