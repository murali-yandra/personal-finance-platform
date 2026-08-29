"""Redaction of sensitive values before they reach a log.

``10-security_standards.md`` section 11 forbids logging passwords, tokens, card
numbers, full account numbers and secrets. Masking happens in the log formatter
rather than at call sites, so a new log line cannot accidentally leak a value by
forgetting to mask it.
"""

import re

MASK = "[REDACTED]"

# Keys whose value must never appear in a log, whatever the surrounding format.
SENSITIVE_KEYS = (
    "password",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
    "apikey",
    "x-api-key",
    "jwt",
    "password_hash",
    "card_number",
    "cvv",
    "pin",
)

_KEY_ALTERNATION = "|".join(re.escape(key) for key in SENSITIVE_KEYS)

# key=value, key: value, "key": "value"
KEY_VALUE_PATTERN = re.compile(
    rf'(?i)(["\']?(?:{_KEY_ALTERNATION})["\']?\s*[:=]\s*)(["\']?)([^\s,;}}"\']+)\2'
)

BEARER_PATTERN = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/-]+=*")

# A JWT is three base64url segments separated by dots.
JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")

# 12 to 19 digits, optionally grouped, is a card or full account number.
LONG_NUMBER_PATTERN = re.compile(r"\b(?:\d[ -]?){11,18}\d\b")

MIN_VISIBLE_DIGITS = 4


def mask_text(text: str) -> str:
    """Redact sensitive values in a log message."""
    if not text:
        return text

    masked = KEY_VALUE_PATTERN.sub(rf"\1\2{MASK}\2", text)
    masked = BEARER_PATTERN.sub(rf"\1{MASK}", masked)
    masked = JWT_PATTERN.sub(MASK, masked)
    return LONG_NUMBER_PATTERN.sub(_mask_number, masked)


def is_sensitive_key(key: str) -> bool:
    """Return whether a field name identifies a value that must not be logged.

    Text masking works on ``key=value`` inside a message. A value passed as a
    structured field has its name as a dict key rather than in the text, so the
    name is checked separately or the value would be logged verbatim.
    """
    lowered = key.strip().lower().replace("-", "_")
    return any(sensitive in lowered for sensitive in SENSITIVE_KEYS)


def mask_account_number(value: str) -> str:
    """Show only the last four digits of an account number.

    ``1234567890`` becomes ``******7890``, the form the security standard
    requires.
    """
    digits = re.sub(r"\D", "", value)
    if len(digits) <= MIN_VISIBLE_DIGITS:
        return value
    return "*" * (len(digits) - MIN_VISIBLE_DIGITS) + digits[-MIN_VISIBLE_DIGITS:]


def _mask_number(match: re.Match[str]) -> str:
    return mask_account_number(match.group(0))
