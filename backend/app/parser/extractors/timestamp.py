"""Transaction timestamp extraction."""

import re
from datetime import date, datetime

DATE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(\d{2}-\d{2}-\d{4})\b"), "%d-%m-%Y"),
    (re.compile(r"\b(\d{2}/\d{2}/\d{4})\b"), "%d/%m/%Y"),
    (re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"), "%Y-%m-%d"),
    (re.compile(r"\b(\d{2}-\d{2}-\d{2})\b"), "%d-%m-%y"),
    (re.compile(r"\b(\d{2}/\d{2}/\d{2})\b"), "%d/%m/%y"),
    (re.compile(r"\b(\d{1,2}-[A-Za-z]{3}-\d{2,4})\b"), "%d-%b-%Y"),
    (re.compile(r"\b(\d{1,2}[A-Za-z]{3}\d{2})\b"), "%d%b%y"),
)

TIME_PATTERN = re.compile(r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b")


def extract_timestamp(message_text: str) -> datetime | None:
    """Return the transaction timestamp stated in the message.

    Indian bank SMS use day-first dates. A two-digit year is read as 20xx; these
    messages are never decades old, so the century is unambiguous in practice.
    """
    parsed_date = _extract_date(message_text)
    if parsed_date is None:
        return None

    hour, minute, second = _extract_time(message_text)
    return datetime(
        parsed_date.year,
        parsed_date.month,
        parsed_date.day,
        hour,
        minute,
        second,
    )


def _extract_date(message_text: str) -> date | None:
    for pattern, fmt in DATE_PATTERNS:
        match = pattern.search(message_text)
        if match is None:
            continue
        raw = match.group(1)
        for candidate_format in _format_variants(fmt):
            try:
                return datetime.strptime(raw, candidate_format).date()
            except ValueError:
                continue
    return None


def _format_variants(fmt: str) -> tuple[str, ...]:
    if "%Y" in fmt:
        return (fmt, fmt.replace("%Y", "%y"))
    return (fmt, fmt.replace("%y", "%Y"))


def _extract_time(message_text: str) -> tuple[int, int, int]:
    match = TIME_PATTERN.search(message_text)
    if match is None:
        return (0, 0, 0)
    hour = int(match.group(1))
    minute = int(match.group(2))
    second = int(match.group(3) or 0)
    if hour > 23 or minute > 59 or second > 59:
        return (0, 0, 0)
    return (hour, minute, second)
