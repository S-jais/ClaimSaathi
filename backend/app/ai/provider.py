"""
app/ai/provider.py
LLMProvider abstraction — a Python Protocol (structural typing).
All concrete adapters (OpenAI, Gemini, Mock) implement this interface.
Business logic NEVER imports a concrete adapter directly.
The active provider is selected by config (LLM_PROVIDER env var).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------
@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    parsed: dict[str, Any] | None  # non-None if schema was provided and parsing succeeded
    prompt_tokens: int
    completion_tokens: int
    model: str
    provider: str
    raw: dict[str, Any] = field(default_factory=dict)  # raw provider response, for debugging


# ---------------------------------------------------------------------------
# Protocol — the interface every adapter must satisfy
# ---------------------------------------------------------------------------
@runtime_checkable
class LLMProvider(Protocol):
    """
    Single interface for all LLM providers.
    Business logic only calls this interface — never a concrete adapter.

    generate() is the only required method.
    embed() is used by the embedding pipeline.
    """

    provider_name: str

    async def generate(
        self,
        messages: list[LLMMessage],
        schema: type[BaseModel] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a completion.
        If schema is provided, the response is requested in JSON mode
        and parsed against the schema.
        Raises AIProviderError on failure (never returns a partial/broken response).
        """
        ...

    async def embed(
        self,
        texts: list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.
        Returns a list of float vectors (one per input text).
        Raises AIProviderError on failure.
        """
        ...


# ---------------------------------------------------------------------------
# Factory — returns the configured provider
# ---------------------------------------------------------------------------
def get_llm_provider() -> LLMProvider:
    """
    Returns the configured LLM provider.
    Called once at startup and cached.
    To add a new provider: create an adapter in app/ai/adapters/, add a case here.
    """
    from app.core.config import get_settings
    settings = get_settings()

    if settings.LLM_PROVIDER == "openai":
        from app.ai.adapters.openai_adapter import OpenAIAdapter
        return OpenAIAdapter()
    elif settings.LLM_PROVIDER == "gemini":
        from app.ai.adapters.gemini_adapter import GeminiAdapter
        return GeminiAdapter()
    elif settings.LLM_PROVIDER == "mock":
        from app.ai.adapters.mock_adapter import MockLLMProvider
        return MockLLMProvider()
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}")


# Singleton
_provider: LLMProvider | None = None


def llm() -> LLMProvider:
    """FastAPI / worker dependency: returns singleton LLM provider."""
    global _provider
    if _provider is None:
        _provider = get_llm_provider()
    return _provider
