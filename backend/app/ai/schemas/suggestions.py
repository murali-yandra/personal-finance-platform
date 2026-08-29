from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class SuggestionKind(StrEnum):
    """What an AI suggestion is about."""

    MERCHANT = "MERCHANT"
    CATEGORY = "CATEGORY"


class SuggestionStatus(StrEnum):
    """Lifecycle of a stored suggestion."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ConfidenceBand(StrEnum):
    """Confidence bands from 13-ai_integration_standards.md section 10."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Only a HIGH suggestion may be applied without asking the user. Anything less
# is stored for confirmation: a wrong category quietly corrupts reporting.
HIGH_CONFIDENCE_THRESHOLD = Decimal("0.90")
MEDIUM_CONFIDENCE_THRESHOLD = Decimal("0.70")


@dataclass(frozen=True)
class Suggestion:
    """A single suggestion produced by a model."""

    kind: SuggestionKind
    value: str
    confidence: Decimal
    transaction_id: UUID | None = None
    reasoning: str | None = None

    @property
    def band(self) -> ConfidenceBand:
        """Return the confidence band this suggestion falls in."""
        if self.confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return ConfidenceBand.HIGH
        if self.confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            return ConfidenceBand.MEDIUM
        return ConfidenceBand.LOW

    @property
    def can_auto_apply(self) -> bool:
        """Return whether this may be applied without user confirmation."""
        return self.band is ConfidenceBand.HIGH
