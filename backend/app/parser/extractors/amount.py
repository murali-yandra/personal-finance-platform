"""Amount extraction from bank SMS text."""

import re
from decimal import Decimal

from app.shared.financial.financial_calculator import (
    FinancialCalculator,
    MoneyError,
)

CURRENCY_TOKEN = r"(?:INR|Rs\.?|RS\.?|₹)"

# Indian digit grouping is 2,2,3 (12,34,567.89), not the Western 3,3,3.
AMOUNT_PATTERN = re.compile(
    rf"{CURRENCY_TOKEN}\s*([0-9][0-9,]*(?:\.[0-9]{{1,2}})?)",
    re.IGNORECASE,
)

TRAILING_AMOUNT_PATTERN = re.compile(
    rf"([0-9][0-9,]*(?:\.[0-9]{{1,2}})?)\s*{CURRENCY_TOKEN}",
    re.IGNORECASE,
)

BALANCE_PATTERN = re.compile(
    rf"(?:avl|available|avbl|a\/c|clear|closing)?\s*"
    rf"(?:bal|balance)[:\s.]*(?:is)?[:\s]*{CURRENCY_TOKEN}?\s*"
    rf"([0-9][0-9,]*(?:\.[0-9]{{1,2}})?)",
    re.IGNORECASE,
)


def extract_amount(message_text: str) -> Decimal | None:
    """Return the transaction amount, or ``None`` when no amount is present.

    A balance mention is removed first. Many messages state both the amount and
    the resulting balance, and the balance is frequently the larger and later
    number, so a naive scan picks the wrong one.
    """
    without_balance = BALANCE_PATTERN.sub(" ", message_text)

    match = AMOUNT_PATTERN.search(without_balance) or TRAILING_AMOUNT_PATTERN.search(
        without_balance
    )
    if match is None:
        return None
    return _to_decimal(match.group(1))


def extract_available_balance(message_text: str) -> Decimal | None:
    """Return the available balance quoted in the message, if any."""
    match = BALANCE_PATTERN.search(message_text)
    if match is None:
        return None
    return _to_decimal(match.group(1))


def _to_decimal(raw: str) -> Decimal | None:
    try:
        return FinancialCalculator.to_money(raw.replace(",", ""))
    except MoneyError:
        return None
