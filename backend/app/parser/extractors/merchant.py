"""Merchant, reference and UPI extraction."""

import re

# Ordered most specific first. The VPA form has to win over the generic
# "to X" form, which would otherwise capture the literal "VPA " prefix.
MERCHANT_PATTERNS = (
    # "to VPA swiggy@icici"
    re.compile(r"\bVPA\s+([A-Za-z0-9._-]+@[A-Za-z0-9.-]+)", re.IGNORECASE),
    # "at SmartQ on", "to SWIGGY.", "towards Amazon"
    re.compile(
        r"\b(?:at|to|towards|in favour of|favouring)\s+"
        r"([A-Za-z0-9][A-Za-z0-9 &._@'/-]{1,60}?)"
        r"(?=\s+(?:on|dated|ref|txn|upi|via|for|avl|a/c|bal)\b|[.;,]|$)",
        re.IGNORECASE,
    ),
)

UPI_ID_PATTERN = re.compile(r"\b([A-Za-z0-9._-]{2,}@[A-Za-z][A-Za-z0-9.-]{1,})\b")

REFERENCE_PATTERNS = (
    re.compile(
        r"\b(?:ref(?:erence)?|txn|transaction|utr|rrn)\s*"
        r"(?:no\.?|id|number)?\s*[:#\s]\s*([A-Za-z0-9-]{4,30})",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:UPI|IMPS|NEFT|RTGS)[:/\s-]+([A-Za-z0-9]{6,30})", re.IGNORECASE),
)

# Words that survive the merchant regex but carry no merchant meaning.
MERCHANT_STOPWORDS = {
    "A",
    "AC",
    "ACCOUNT",
    "AN",
    "BANK",
    "CARD",
    "THE",
    "YOUR",
    "YOU",
    "UPI",
}

TRAILING_NOISE = re.compile(r"\s+(?:on|via|ref|txn|dated)$", re.IGNORECASE)


def extract_merchant(message_text: str) -> str | None:
    """Return the raw merchant string as the bank wrote it.

    No normalization happens here. Mapping ``UPISWIGGY@ICICI`` to ``Swiggy`` is
    the merchant engine's job in Sprint 6; the parser's contract is to report
    what the message actually said.
    """
    for pattern in MERCHANT_PATTERNS:
        match = pattern.search(message_text)
        if match is None:
            continue
        candidate = _clean(match.group(1))
        if candidate:
            return candidate
    return None


def extract_upi_id(message_text: str) -> str | None:
    """Return the UPI virtual payment address, if the message carries one."""
    match = UPI_ID_PATTERN.search(message_text)
    if match is None:
        return None
    return match.group(1)


def extract_reference_number(message_text: str) -> str | None:
    """Return the bank's reference, transaction or UTR number."""
    for pattern in REFERENCE_PATTERNS:
        match = pattern.search(message_text)
        if match is not None:
            return match.group(1).strip()
    return None


def _clean(value: str) -> str | None:
    candidate = TRAILING_NOISE.sub("", value.strip(" .;,-"))
    candidate = re.sub(r"\s{2,}", " ", candidate).strip()
    if not candidate or candidate.upper() in MERCHANT_STOPWORDS:
        return None
    if candidate.isdigit():
        return None
    return candidate
