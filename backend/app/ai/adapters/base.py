"""Provider abstraction.

``13-ai_integration_standards.md`` section 21 requires the adapter pattern so a
local Ollama deployment can be swapped for a hosted provider later without
touching the services that consume suggestions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromptRequest:
    """One request to a model."""

    prompt: str
    system: str | None = None
    max_tokens: int = 256
    temperature: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AIResponse:
    """One response from a model."""

    text: str
    model: str
    succeeded: bool = True
    error: str | None = None

    @classmethod
    def failure(cls, error: str, model: str = "unknown") -> "AIResponse":
        """Build a failed response.

        Failure is a value rather than an exception so callers cannot forget to
        handle an outage and accidentally take the pipeline down with it.
        """
        return cls(text="", model=model, succeeded=False, error=error)


class BaseAIProvider(ABC):
    """Interface every model provider implements."""

    name: str = "base"

    @abstractmethod
    def complete(self, request: PromptRequest) -> AIResponse:
        """Run one completion."""
        raise NotImplementedError

    def is_available(self) -> bool:
        """Return whether the provider can currently be used."""
        return True
