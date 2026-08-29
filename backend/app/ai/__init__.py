"""AI assistance.

Every entry point is gated by ``ENABLE_AI`` and degrades to no suggestion when
the provider is unavailable. AI failures must never block SMS processing,
transaction creation, balance updates or reporting
(``13-ai_integration_standards.md`` section 22).
"""

from app.ai.adapters.base import AIResponse, BaseAIProvider, PromptRequest
from app.ai.adapters.fake import FakeAIProvider
from app.ai.adapters.ollama import OllamaProvider
from app.ai.schemas.suggestions import Suggestion, SuggestionKind

__all__ = [
    "AIResponse",
    "BaseAIProvider",
    "FakeAIProvider",
    "OllamaProvider",
    "PromptRequest",
    "Suggestion",
    "SuggestionKind",
]
