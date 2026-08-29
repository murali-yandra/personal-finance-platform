"""Account identification from bank SMS text."""

import re
from dataclasses import dataclass

from app.shared.enums import AccountType

# Banks mask account numbers as XXXX0452, XX0452, ****0452 or ...0452.
ACCOUNT_MASK_PATTERN = re.compile(
    r"(?:a/?c|acct|account|card)\s*(?:no\.?|number)?\s*"
    r"[:\s]*[Xx*.•]{2,}\s*(\d{3,6})",
    re.IGNORECASE,
)

BARE_MASK_PATTERN = re.compile(r"[Xx*.•]{3,}\s*(\d{3,6})")

CREDIT_CARD_PATTERN = re.compile(
    r"\b(?:credit\s*card|cc)\b",
    re.IGNORECASE,
)
DEBIT_CARD_PATTERN = re.compile(r"\b(?:debit\s*card|atm\s*card)\b", re.IGNORECASE)


@dataclass(frozen=True)
class AccountHint:
    """What a message reveals about which account it belongs to."""

    last_four_digits: str | None = None
    account_type_hint: str | None = None


def extract_account_hint(message_text: str) -> AccountHint:
    """Return the masked account digits and an account-type hint.

    The digits are the tail of a masked number, which is all a bank discloses.
    Combined with the bank name, they are enough to resolve or create an
    account downstream.
    """
    digits = _extract_digits(message_text)
    return AccountHint(
        last_four_digits=digits,
        account_type_hint=_account_type_hint(message_text),
    )


def _extract_digits(message_text: str) -> str | None:
    match = ACCOUNT_MASK_PATTERN.search(message_text) or BARE_MASK_PATTERN.search(
        message_text
    )
    if match is None:
        return None
    return match.group(1)[-4:]


def _account_type_hint(message_text: str) -> str | None:
    if CREDIT_CARD_PATTERN.search(message_text):
        return AccountType.CREDIT_CARD.value
    if DEBIT_CARD_PATTERN.search(message_text):
        return AccountType.BANK.value
    return None
