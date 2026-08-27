"""Transaction-level duplicate detection.

``04-database_schema.md`` section 7.2 defines a two-layer strategy. Raw messages
are deduplicated by ``message_hash``; transactions are deduplicated by this
fingerprint. Raw SMS text must never be the basis for transaction-level
deduplication, because two genuinely different transactions can produce
byte-identical text, and one transaction can arrive worded two different ways.
"""

import hashlib
import re
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.shared.financial.financial_calculator import FinancialCalculator

FIELD_SEPARATOR = "|"
NON_ALPHANUMERIC = re.compile(r"[^A-Z0-9]+")


def build_transaction_fingerprint(
    user_id: UUID,
    account_id: UUID,
    amount: Decimal,
    direction: str,
    transaction_timestamp: datetime | None,
    merchant_raw: str | None = None,
    reference_number: str | None = None,
) -> str:
    """Return the SHA-256 fingerprint for a transaction.

    The inputs are exactly the fields listed in the schema specification. Text
    inputs are normalized so that formatting differences between two renderings
    of the same transaction do not defeat the match.
    """
    parts = [
        str(user_id),
        str(account_id),
        str(FinancialCalculator.to_money(amount)),
        str(direction).strip().upper(),
        _normalize_timestamp(transaction_timestamp),
        _normalize_text(merchant_raw),
        _normalize_text(reference_number),
    ]
    digest_source = FIELD_SEPARATOR.join(parts)
    return hashlib.sha256(digest_source.encode("utf-8")).hexdigest()


def _normalize_timestamp(value: datetime | None) -> str:
    """Normalize the timestamp to whole minutes.

    Banks routinely report the same transaction with a few seconds of drift
    between the SMS and a statement import, so seconds are not part of identity.
    """
    if value is None:
        return ""
    return value.strftime("%Y-%m-%dT%H:%M")


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return NON_ALPHANUMERIC.sub("", value.strip().upper())
