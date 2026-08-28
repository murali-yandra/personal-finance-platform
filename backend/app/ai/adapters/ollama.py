"""Ollama provider.

Ollama is the MVP choice in ``13-ai_integration_standards.md`` section 5: local,
free, and no data leaves the machine, which matters for financial messages.
"""

import logging

import httpx

from app.ai.adapters.base import AIResponse, BaseAIProvider, PromptRequest

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3"
DEFAULT_TIMEOUT_SECONDS = 15.0


class OllamaProvider(BaseAIProvider):
    """Calls a local Ollama server."""

    name = "ollama"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def complete(self, request: PromptRequest) -> AIResponse:
        """Run one completion, returning a failure value rather than raising."""
        payload = {
            "model": self._model,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        if request.system:
            payload["system"] = request.system

        try:
            response = httpx.post(
                f"{self._base_url}/api/generate",
                json=payload,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            logger.warning("Ollama request failed: %s", exc)
            return AIResponse.failure(str(exc), model=self._model)

        if response.status_code >= 400:
            logger.warning("Ollama returned status %s", response.status_code)
            return AIResponse.failure(
                f"status {response.status_code}",
                model=self._model,
            )

        try:
            body = response.json()
        except ValueError as exc:
            return AIResponse.failure(f"invalid JSON: {exc}", model=self._model)

        return AIResponse(text=str(body.get("response", "")), model=self._model)

    def is_available(self) -> bool:
        """Return whether the Ollama server answers."""
        try:
            response = httpx.get(f"{self._base_url}/api/tags", timeout=self._timeout)
        except httpx.HTTPError:
            return False
        return response.status_code < 400
