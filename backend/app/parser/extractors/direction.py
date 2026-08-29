"""Direction and business-type detection."""

import re

from app.shared.enums import BusinessType, TransactionDirection

DEBIT_TOKENS = (
    "debited",
    "debit",
    "withdrawn",
    "spent",
    "paid",
    "payment of",
    "purchase",
    "sent",
    "transferred to",
    "deducted",
)

CREDIT_TOKENS = (
    "credited",
    "credit",
    "received",
    "deposited",
    "refund",
    "reversed",
    "cashback",
)

# Messages that mention money but are not themselves a transaction.
NON_TRANSACTIONAL_PATTERNS = (
    re.compile(r"\bOTP\b", re.IGNORECASE),
    re.compile(r"one[\s-]?time\s+password", re.IGNORECASE),
    re.compile(r"\bdo not share\b", re.IGNORECASE),
    re.compile(r"\bwill be debited\b", re.IGNORECASE),
    re.compile(r"\bwill be credited\b", re.IGNORECASE),
    re.compile(r"\bis due\b", re.IGNORECASE),
    re.compile(r"\bdue on\b", re.IGNORECASE),
    re.compile(r"\bstatement\s+(?:is|for)\b", re.IGNORECASE),
    re.compile(r"\bapply now\b", re.IGNORECASE),
    re.compile(r"\boffer\b", re.IGNORECASE),
    re.compile(r"\bpre[\s-]?approved\b", re.IGNORECASE),
    re.compile(r"\brequest(?:ing|ed)?\s+money\b", re.IGNORECASE),
)

BUSINESS_TYPE_PATTERNS: tuple[tuple[re.Pattern[str], BusinessType], ...] = (
    (re.compile(r"\bsalary\b", re.IGNORECASE), BusinessType.INCOME),
    (re.compile(r"\brefund", re.IGNORECASE), BusinessType.REFUND),
    (re.compile(r"\bcashback\b", re.IGNORECASE), BusinessType.CASHBACK),
    (re.compile(r"\bemi\b", re.IGNORECASE), BusinessType.EMI),
    (re.compile(r"\binterest\b", re.IGNORECASE), BusinessType.INTEREST),
    (re.compile(r"\b(?:charge|fee|penalty|gst)\b", re.IGNORECASE), BusinessType.FEE),
    (
        re.compile(r"\b(?:atm|cash\s*w(?:it)?hdrawa?l)\b", re.IGNORECASE),
        BusinessType.TRANSFER,
    ),
    (
        re.compile(r"\b(?:sip|mutual\s*fund|nps|ppf)\b", re.IGNORECASE),
        BusinessType.INVESTMENT,
    ),
    (re.compile(r"\bloan\b", re.IGNORECASE), BusinessType.LOAN),
)


def is_non_transactional(message_text: str) -> str | None:
    """Return why a message is not a transaction, or ``None`` if it is one.

    OTPs, due-date reminders and marketing all quote amounts. Treating them as
    parse failures would bury genuine failures in noise, so they are classified
    separately and ignored by the pipeline.
    """
    for pattern in NON_TRANSACTIONAL_PATTERNS:
        if pattern.search(message_text):
            return f"Message matched non-transactional pattern: {pattern.pattern}"
    return None


def detect_direction(message_text: str) -> TransactionDirection | None:
    """Return the direction of money movement.

    Whichever keyword appears first wins. Bank messages lead with the action
    ("debited from...", "credited to..."), and a later mention is usually part
    of a balance or advisory clause.
    """
    lowered = message_text.lower()

    debit_at = _first_index(lowered, DEBIT_TOKENS)
    credit_at = _first_index(lowered, CREDIT_TOKENS)

    if debit_at is None and credit_at is None:
        return None
    if credit_at is None:
        return TransactionDirection.DEBIT
    if debit_at is None:
        return TransactionDirection.CREDIT
    return (
        TransactionDirection.DEBIT
        if debit_at < credit_at
        else TransactionDirection.CREDIT
    )


def detect_business_type(
    message_text: str,
    direction: TransactionDirection,
) -> BusinessType:
    """Classify the transaction, falling back to the direction's default."""
    for pattern, business_type in BUSINESS_TYPE_PATTERNS:
        if pattern.search(message_text):
            return business_type
    if direction is TransactionDirection.CREDIT:
        return BusinessType.INCOME
    return BusinessType.EXPENSE


def _first_index(lowered: str, tokens: tuple[str, ...]) -> int | None:
    positions = [lowered.find(token) for token in tokens]
    found = [position for position in positions if position >= 0]
    return min(found) if found else None
