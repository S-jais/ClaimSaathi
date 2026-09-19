"""
app/ai/adapters/openai_adapter.py
OpenAI concrete adapter implementing the LLMProvider Protocol.
Uses structured outputs (JSON mode) for schema-validated responses.
Hardened with retry logic and connection-reset resilience.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from openai import AsyncOpenAI, APIConnectionError, APIStatusError, APITimeoutError, OpenAIError
from pydantic import BaseModel

from app.ai.provider import LLMMessage, LLMResponse
from app.core.config import get_settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Retryable network-layer errors (wsarecv / connection-reset)
_RETRYABLE = (APIConnectionError, APITimeoutError, ConnectionResetError, OSError)
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.5  # seconds


async def _with_retry(coro_fn, *args, **kwargs):
    """Execute coro_fn with exponential backoff on transient network errors."""
    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return await coro_fn(*args, **kwargs)
        except _RETRYABLE as exc:
            last_err = exc
            wait = _BACKOFF_BASE ** attempt
            logger.warning(
                "openai_retry",
                attempt=attempt + 1,
                max=_MAX_RETRIES,
                error=str(exc),
                wait_s=wait,
            )
            await asyncio.sleep(wait)
        except APIStatusError as exc:
            # 429 / 503 — retryable; other status codes are fatal
            if exc.status_code in (429, 500, 502, 503, 504):
                last_err = exc
                wait = _BACKOFF_BASE ** attempt
                logger.warning(
                    "openai_status_retry",
                    status=exc.status_code,
                    attempt=attempt + 1,
                    wait_s=wait,
                )
                await asyncio.sleep(wait)
            else:
                raise
    raise AIProviderError(f"OpenAI request failed after {_MAX_RETRIES} retries: {last_err}") from last_err


class OpenAIAdapter:
    provider_name = "openai"

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise AIProviderError("OPENAI_API_KEY is not set.")
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=30.0,          # hard socket timeout
            max_retries=0,         # we handle retries ourselves
        )
        self._model = settings.OPENAI_MODEL
        self._embedding_model = settings.OPENAI_EMBEDDING_MODEL

    async def generate(
        self,
        messages: list[LLMMessage],
        schema: type[BaseModel] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        oai_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            if schema is not None:
                async def _call():
                    return await self._client.beta.chat.completions.parse(
                        model=self._model,
                        messages=oai_messages,  # type: ignore[arg-type]
                        response_format=schema,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                response = await _with_retry(_call)
                message = response.choices[0].message
                parsed_obj = message.parsed
                content = message.content or ""
                parsed_dict = parsed_obj.model_dump() if parsed_obj else None
            else:
                async def _call():  # type: ignore[no-redef]
                    return await self._client.chat.completions.create(
                        model=self._model,
                        messages=oai_messages,  # type: ignore[arg-type]
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                response = await _with_retry(_call)
                content = response.choices[0].message.content or ""
                parsed_dict = None

            usage = response.usage
            return LLMResponse(
                content=content,
                parsed=parsed_dict,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                model=self._model,
                provider=self.provider_name,
            )

        except AIProviderError:
            raise
        except OpenAIError as e:
            logger.error("openai_generate_failed", error=str(e))
            raise AIProviderError(f"OpenAI generation failed: {e}") from e

    async def embed(
        self,
        texts: list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        if not texts:
            return []

        async def _call():
            return await self._client.embeddings.create(
                model=self._embedding_model,
                input=texts,
            )

        try:
            response = await _with_retry(_call)
            return [item.embedding for item in response.data]
        except AIProviderError:
            raise
        except OpenAIError as e:
            logger.error("openai_embed_failed", error=str(e))
            raise AIProviderError(f"OpenAI embedding failed: {e}") from e
