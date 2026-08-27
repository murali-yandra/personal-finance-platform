"""Raw-event duplicate detection.

This is the first of the two deduplication layers in
``04-database_schema.md`` section 7: an exact-message check. The second layer,
transaction fingerprinting, lives in the transactions domain.
"""

import hashlib

FIELD_SEPARATOR = "|"


def build_message_hash(
    sender: str | None,
    message_text: str,
    received_at_iso: str,
) -> str:
    """Return the SHA-256 hash identifying an exact duplicate message.

    The receipt timestamp is part of the hash on purpose. A retry from the
    sending device replays the identical payload and is caught here, while two
    genuinely separate but identically worded purchases arrive with different
    timestamps and are both stored. If those turn out to be the same
    transaction, the transaction fingerprint catches it downstream.
    """
    parts = [
        (sender or "").strip().upper(),
        message_text.strip(),
        received_at_iso,
    ]
    return hashlib.sha256(FIELD_SEPARATOR.join(parts).encode("utf-8")).hexdigest()
