"""Learning from user corrections (Sprint 13).

The example in ``14-sprint_roadmap.md`` section 18:

```text
KA51AJ*
↓
Transport
```

A correction is turned into a user-owned merchant pattern, so the next message
from the same merchant resolves without asking again. Patterns created here are
owned by the correcting user and never global: one person's preference must not
reclassify everyone else's history.
"""

import logging
import re
from decimal import Decimal
from uuid import UUID

from app.domains.ai.models import UserFeedback
from app.domains.ai.repository import SuggestionRepository
from app.domains.merchants.service import MerchantService
from app.shared.enums import FeedbackType, PatternType

logger = logging.getLogger(__name__)

# Confidence for a rule derived from an explicit user correction. It is below
# 1.00 so a later, more specific correction can still outrank it.
LEARNED_PATTERN_CONFIDENCE = Decimal("0.95")

MIN_TOKEN_LENGTH = 4

# A trailing digit run preceded by a letter is the part that varies between
# messages from the same merchant: the vehicle number in KA51AJ1234, the
# terminal id in a card string.
VARYING_TAIL = re.compile(r"^(.*[A-Za-z])\d+$")

# LIKE wildcards appearing literally in a bank string are never intended as
# wildcards, and would silently widen the learned rule to match anything.
LIKE_WILDCARDS = re.compile(r"[%_]")


class LearningService:
    """Turns user corrections into future behaviour."""

    def __init__(
        self,
        repository: SuggestionRepository,
        merchant_service: MerchantService,
    ) -> None:
        self._repository = repository
        self._merchants = merchant_service

    def record_feedback(
        self,
        user_id: UUID,
        feedback_type: FeedbackType,
        old_value: str | None,
        new_value: str | None,
        transaction_id: UUID | None = None,
        source: str = "USER",
    ) -> UserFeedback:
        """Store one correction."""
        feedback = UserFeedback(
            user_id=user_id,
            transaction_id=transaction_id,
            feedback_type=FeedbackType(feedback_type).value,
            old_value=old_value,
            new_value=new_value,
            source=source,
        )
        self._repository.add_feedback(feedback)
        self._repository.commit()
        self._repository.refresh(feedback)
        return feedback

    def learn_merchant_correction(
        self,
        user_id: UUID,
        merchant_raw: str,
        corrected_merchant_name: str,
        transaction_id: UUID | None = None,
    ) -> UserFeedback:
        """Record a merchant correction and create the rule that applies it."""
        feedback = self.record_feedback(
            user_id=user_id,
            feedback_type=FeedbackType.MERCHANT_CHANGE,
            old_value=merchant_raw,
            new_value=corrected_merchant_name,
            transaction_id=transaction_id,
        )

        pattern = build_learned_pattern(merchant_raw)
        if pattern is None:
            logger.info(
                "No usable pattern from %r; feedback recorded without a rule.",
                merchant_raw,
            )
            return feedback

        merchant = self._merchants.get_or_create_merchant(corrected_merchant_name)
        self._merchants.create_pattern(
            user_id=user_id,
            merchant_id=merchant.id,
            pattern=pattern,
            pattern_type=PatternType.LIKE,
            confidence=LEARNED_PATTERN_CONFIDENCE,
            created_by="USER",
        )
        return feedback


def build_learned_pattern(merchant_raw: str) -> str | None:
    """Derive a LIKE pattern that will match similar future strings.

    Bank merchant strings carry a stable part and a varying tail:
    ``KA51AJ1234`` and ``KA51AJ5678`` are the same bus operator with different
    vehicles. Dropping the trailing digits generalizes to the next one, while a
    pattern built from the whole string would only match that one transaction.

    The pattern is derived from the original text rather than a stripped
    version, and wrapped so it matches anywhere in the candidate. That keeps the
    essential guarantee: a learned rule always matches the string it was learned
    from. Stripping punctuation first would produce ``UPISWIGGYICICI%``, which
    never matches ``UPISWIGGY@ICICI``.
    """
    if not merchant_raw or not merchant_raw.strip():
        return None

    core = LIKE_WILDCARDS.sub("", merchant_raw.strip())
    if len(core) < MIN_TOKEN_LENGTH:
        return None

    match = VARYING_TAIL.match(core)
    if match and len(match.group(1)) >= MIN_TOKEN_LENGTH:
        core = match.group(1)

    return f"%{core}%"
