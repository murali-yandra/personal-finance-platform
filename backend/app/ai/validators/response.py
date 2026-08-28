"""Validation of model output.

``13-ai_integration_standards.md`` section 19 requires every response to be
validated before use. A model can return prose, malformed JSON, or a category
that does not exist; none of that may reach the database.
"""

import json
import logging
import re
from decimal import Decimal, InvalidOperation

from app.ai.schemas.suggestions import Suggestion, SuggestionKind

logger = logging.getLogger(__name__)

MAX_VALUE_LENGTH = 255

# Models often wrap JSON in prose or a fenced code block.
JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def parse_suggestion(
    raw_text: str,
    kind: SuggestionKind,
    allowed_values: set[str] | None = None,
) -> Suggestion | None:
    """Parse a model response into a validated suggestion.

    Returns ``None`` for anything that cannot be trusted, rather than raising.
    An absent suggestion is harmless; a fabricated one silently corrupts the
    user's financial history.
    """
    payload = _extract_json(raw_text)
    if payload is None:
        return None

    value = payload.get("value")
    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value or len(value) > MAX_VALUE_LENGTH:
        return None

    if allowed_values is not None and not _is_allowed(value, allowed_values):
        # A model asked for a category will happily invent one.
        logger.info("Discarding suggestion outside the allowed set: %s", value)
        return None

    confidence = _parse_confidence(payload.get("confidence"))
    if confidence is None:
        return None

    reasoning = payload.get("reasoning")
    return Suggestion(
        kind=kind,
        value=value,
        confidence=confidence,
        reasoning=str(reasoning)[:500] if reasoning else None,
    )


def _extract_json(raw_text: str) -> dict | None:
    if not raw_text or not raw_text.strip():
        return None

    candidate = raw_text.strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        match = JSON_OBJECT_PATTERN.search(candidate)
        if match is None:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    return parsed if isinstance(parsed, dict) else None


def _is_allowed(value: str, allowed_values: set[str]) -> bool:
    lowered = {allowed.casefold() for allowed in allowed_values}
    return value.casefold() in lowered


def _parse_confidence(raw: object) -> Decimal | None:
    """Coerce a confidence into the 0.00-1.00 range, rejecting anything else."""
    if raw is None:
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None
    if value.is_nan() or value.is_infinite():
        return None
    # Models sometimes answer 85 when asked for 0.85.
    if value > 1:
        value = value / Decimal("100")
    if not (Decimal("0") <= value <= Decimal("1")):
        return None
    return value.quantize(Decimal("0.01"))
