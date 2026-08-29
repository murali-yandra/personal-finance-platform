"""Construction of the AI provider from configuration."""

from app.ai.adapters.base import BaseAIProvider
from app.ai.adapters.fake import FakeAIProvider
from app.ai.adapters.ollama import OllamaProvider
from app.config import Settings


def build_ai_provider(settings: Settings) -> BaseAIProvider:
    """Return the provider implied by configuration.

    When AI is disabled the fake provider stands in, reporting itself as
    unavailable, so callers need no special case for the disabled path.
    """
    if not settings.enable_ai:
        return FakeAIProvider(available=False)

    return OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )
