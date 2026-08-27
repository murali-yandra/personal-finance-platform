"""Resolution of a raw merchant string onto a known merchant.

Example from ``14-sprint_roadmap.md`` section 11:

```text
UPISWIGGY@ICICI
↓
Swiggy
```

Patterns are evaluated most specific first: EXACT, then LIKE, then REGEX. Within
each type, user-owned patterns beat global ones, so a personal correction is
never overridden by a shared rule.
"""

import logging
import re
from dataclasses import dataclass
from decimal import Decimal

from app.domains.merchants.models import MerchantPattern
from app.shared.enums import PatternType

logger = logging.getLogger(__name__)

# Precedence: a literal match is stronger evidence than a wildcard, which is
# stronger than a regex written to catch a family of strings.
PATTERN_TYPE_PRECEDENCE: dict[str, int] = {
    PatternType.EXACT.value: 0,
    PatternType.LIKE.value: 1,
    PatternType.REGEX.value: 2,
    PatternType.AI_SUGGESTED.value: 3,
}

MAX_REGEX_LENGTH = 255


@dataclass(frozen=True)
class MerchantMatch:
    """A pattern that matched a raw merchant string."""

    pattern: MerchantPattern
    confidence: Decimal

    @property
    def merchant_id(self):
        """Return the merchant the matched pattern points at."""
        return self.pattern.merchant_id


def resolve_merchant(
    merchant_raw: str | None,
    patterns: list[MerchantPattern],
) -> MerchantMatch | None:
    """Return the best pattern match for a raw merchant string.

    Returns ``None`` rather than guessing when nothing matches. An unresolved
    merchant is recoverable; a wrongly attributed one quietly corrupts every
    report that groups by merchant.
    """
    if not merchant_raw or not merchant_raw.strip():
        return None

    candidate = merchant_raw.strip()
    ranked = sorted(patterns, key=_precedence_key)

    for pattern in ranked:
        if _matches(candidate, pattern):
            return MerchantMatch(
                pattern=pattern,
                confidence=_confidence(pattern),
            )
    return None


def _precedence_key(pattern: MerchantPattern) -> tuple[int, int, int]:
    """Rank patterns: user before global, exact before fuzzy, longer first."""
    return (
        1 if pattern.user_id is None else 0,
        PATTERN_TYPE_PRECEDENCE.get(pattern.pattern_type, 99),
        -len(pattern.pattern or ""),
    )


def _matches(candidate: str, pattern: MerchantPattern) -> bool:
    raw_pattern = (pattern.pattern or "").strip()
    if not raw_pattern:
        return False

    pattern_type = pattern.pattern_type
    if pattern_type == PatternType.EXACT:
        return candidate.casefold() == raw_pattern.casefold()
    if pattern_type in {PatternType.LIKE, PatternType.AI_SUGGESTED}:
        return _like_matches(candidate, raw_pattern)
    if pattern_type == PatternType.REGEX:
        return _regex_matches(candidate, raw_pattern)
    return False


def _like_matches(candidate: str, raw_pattern: str) -> bool:
    """Match SQL LIKE semantics: ``%`` is any run, ``_`` is one character."""
    escaped = re.escape(raw_pattern)
    translated = escaped.replace("%", ".*").replace("_", ".")
    try:
        return re.fullmatch(translated, candidate, re.IGNORECASE) is not None
    except re.error:
        return False


def _regex_matches(candidate: str, raw_pattern: str) -> bool:
    """Match a stored regex, treating a bad or oversized pattern as no match.

    Patterns can be user-supplied, so a broken expression must not take down
    resolution for every other pattern in the list.
    """
    if len(raw_pattern) > MAX_REGEX_LENGTH:
        logger.warning("Skipping oversized merchant regex.")
        return False
    try:
        return re.search(raw_pattern, candidate, re.IGNORECASE) is not None
    except re.error:
        logger.warning("Skipping invalid merchant regex: %s", raw_pattern)
        return False


def _confidence(pattern: MerchantPattern) -> Decimal:
    value = pattern.confidence
    if value is None:
        return Decimal("1.00")
    return Decimal(str(value))
