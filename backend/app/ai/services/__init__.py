"""AI services. Only this package may call a model provider."""

from app.ai.services.suggestion_service import AISuggestionService

__all__ = ["AISuggestionService"]
