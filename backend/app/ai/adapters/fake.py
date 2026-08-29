"""Deterministic provider used in tests and when AI is disabled."""

from dataclasses import dataclass, field

from app.ai.adapters.base import AIResponse, BaseAIProvider, PromptRequest


@dataclass
class FakeAIProvider(BaseAIProvider):
    """Returns canned responses and records what it was asked."""

    name: str = "fake"
    responses: list[str] = field(default_factory=list)
    requests: list[PromptRequest] = field(default_factory=list)
    should_fail: bool = False
    available: bool = True

    def complete(self, request: PromptRequest) -> AIResponse:
        """Return the next canned response."""
        self.requests.append(request)
        if self.should_fail:
            return AIResponse.failure("fake provider failure", model=self.name)
        if not self.responses:
            return AIResponse(text="", model=self.name)
        return AIResponse(text=self.responses.pop(0), model=self.name)

    def is_available(self) -> bool:
        """Return the configured availability."""
        return self.available
