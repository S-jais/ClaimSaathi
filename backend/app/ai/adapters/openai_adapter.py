"""
app/ai/adapters/openai_adapter.py
OpenAI concrete adapter implementing the LLMProvider Protocol.
Uses structured outputs (JSON mode) for schema-validated responses.
"""
from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel

from app.ai.provider import LLMMessage, LLMResponse
from app.core.config import get_settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class OpenAIAdapter:
    provider_name = "openai"

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise AIProviderError("OPENAI_API_KEY is not set.")
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
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
                # Use structured outputs (JSON mode with schema)
                response = await self._client.beta.chat.completions.parse(
                    model=self._model,
                    messages=oai_messages,  # type: ignore[arg-type]
                    response_format=schema,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                message = response.choices[0].message
                parsed_obj = message.parsed
                content = message.content or ""
                parsed_dict = parsed_obj.model_dump() if parsed_obj else None
            else:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=oai_messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
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
        try:
            response = await self._client.embeddings.create(
                model=self._embedding_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except OpenAIError as e:
            logger.error("openai_embed_failed", error=str(e))
            raise AIProviderError(f"OpenAI embedding failed: {e}") from e
