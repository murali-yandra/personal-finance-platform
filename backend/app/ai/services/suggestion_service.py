"""Merchant and category suggestions.

``13-ai_integration_standards.md`` section 20 allows only this package to call a
model. Everything else consumes stored suggestions, which is what keeps a model
outage away from the ingestion path.
"""

import logging
from decimal import Decimal
from uuid import UUID

from app.ai.adapters.base import BaseAIProvider, PromptRequest
from app.ai.prompts.templates import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_category_prompt,
    build_merchant_prompt,
)
from app.ai.schemas.suggestions import Suggestion, SuggestionKind, SuggestionStatus
from app.ai.validators.response import parse_suggestion
from app.domains.ai.models import AISuggestion
from app.domains.ai.repository import SuggestionRepository

logger = logging.getLogger(__name__)


class AISuggestionService:
    """Produces and stores merchant and category suggestions."""

    def __init__(
        self,
        provider: BaseAIProvider,
        repository: SuggestionRepository,
        enabled: bool = True,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._enabled = enabled

    def suggest_merchant(
        self,
        user_id: UUID,
        merchant_raw: str,
        transaction_id: UUID | None = None,
    ) -> Suggestion | None:
        """Suggest a normalized merchant name for a raw string."""
        if not self._enabled or not merchant_raw.strip():
            return None

        response = self._complete(build_merchant_prompt(merchant_raw))
        if response is None:
            return None

        suggestion = parse_suggestion(response.text, SuggestionKind.MERCHANT)
        if suggestion is None:
            return None

        self._store(
            user_id=user_id,
            suggestion=suggestion,
            transaction_id=transaction_id,
            model_name=response.model,
        )
        return suggestion

    def suggest_category(
        self,
        user_id: UUID,
        merchant_name: str,
        amount: Decimal,
        allowed_categories: list[str],
        transaction_id: UUID | None = None,
    ) -> Suggestion | None:
        """Suggest a category, restricted to categories that actually exist."""
        if not self._enabled or not allowed_categories:
            return None

        response = self._complete(
            build_category_prompt(merchant_name, amount, allowed_categories)
        )
        if response is None:
            return None

        suggestion = parse_suggestion(
            response.text,
            SuggestionKind.CATEGORY,
            allowed_values=set(allowed_categories),
        )
        if suggestion is None:
            return None

        self._store(
            user_id=user_id,
            suggestion=suggestion,
            transaction_id=transaction_id,
            model_name=response.model,
        )
        return suggestion

    def _complete(self, prompt: str):
        """Call the provider, converting any failure into ``None``.

        A model outage must never propagate: it would take down SMS processing,
        which has nothing to do with AI
        (``13-ai_integration_standards.md`` section 22).
        """
        try:
            response = self._provider.complete(
                PromptRequest(prompt=prompt, system=SYSTEM_PROMPT)
            )
        except Exception:
            logger.exception("AI provider raised; continuing without a suggestion.")
            return None

        if not response.succeeded:
            logger.info("AI provider unavailable: %s", response.error)
            return None
        return response

    def _store(
        self,
        user_id: UUID,
        suggestion: Suggestion,
        transaction_id: UUID | None,
        model_name: str,
    ) -> AISuggestion:
        record = AISuggestion(
            user_id=user_id,
            transaction_id=transaction_id,
            suggestion_type=suggestion.kind.value,
            suggested_value=suggestion.value,
            confidence_score=suggestion.confidence,
            prompt_version=PROMPT_VERSION,
            model_name=model_name,
            status=SuggestionStatus.PENDING.value,
        )
        self._repository.add_suggestion(record)
        self._repository.commit()
        self._repository.refresh(record)
        return record
