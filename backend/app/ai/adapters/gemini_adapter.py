"""
app/ai/adapters/gemini_adapter.py
Google Gemini concrete adapter implementing the LLMProvider Protocol.
Uses google-generativeai SDK with full retry/timeout/connection-reset resilience.
The wsarecv / connection-forcibly-closed error (172.217.x.x:443) is handled here
with exponential backoff so one bad TCP socket never crashes a request.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from pydantic import BaseModel

from app.ai.provider import LLMMessage, LLMResponse
from app.core.config import get_settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0  # seconds — Gemini API can be slower to recover


def _is_retryable(exc: Exception) -> bool:
    """Return True for transient network / server errors worth retrying."""
    msg = str(exc).lower()
    retryable_signals = (
        "connection reset",
        "wsarecv",
        "eof occurred",
        "stream reading error",
        "connection forcibly closed",
        "timed out",
        "resource temporarily unavailable",
        "service unavailable",
        "internal server error",
        "quota exceeded",  # retry after backoff
        "429",
        "500",
        "502",
        "503",
        "504",
    )
    return any(s in msg for s in retryable_signals)


async def _with_retry(coro_fn, *args, **kwargs):
    """Execute coro_fn with exponential backoff on transient errors."""
    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return await coro_fn(*args, **kwargs)
        except (OSError, ConnectionResetError, asyncio.TimeoutError) as exc:
            last_err = exc
            wait = _BACKOFF_BASE ** attempt
            logger.warning(
                "gemini_network_retry",
                attempt=attempt + 1,
                max=_MAX_RETRIES,
                error=str(exc),
                wait_s=wait,
            )
            await asyncio.sleep(wait)
        except Exception as exc:
            if _is_retryable(exc):
                last_err = exc
                wait = _BACKOFF_BASE ** attempt
                logger.warning(
                    "gemini_api_retry",
                    attempt=attempt + 1,
                    max=_MAX_RETRIES,
                    error=str(exc),
                    wait_s=wait,
                )
                await asyncio.sleep(wait)
            else:
                raise
    raise AIProviderError(
        f"Gemini request failed after {_MAX_RETRIES} retries. "
        f"Last error: {last_err}. "
        "If this is a network issue (wsarecv / connection reset), check your internet connection "
        "or switch LLM_PROVIDER=mock in .env for offline operation."
    ) from last_err


class GeminiAdapter:
    """
    Google Gemini adapter.
    Requires: pip install google-generativeai
    Set GEMINI_API_KEY in .env.
    """

    provider_name = "gemini"

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise AIProviderError(
                "GEMINI_API_KEY is not set. "
                "Set it in .env or switch LLM_PROVIDER=mock for offline operation."
            )
        try:
            import google.generativeai as genai  # type: ignore[import]
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._genai = genai
            self._model_name = settings.GEMINI_MODEL
        except ImportError as e:
            raise AIProviderError(
                "google-generativeai package is not installed. "
                "Run: pip install google-generativeai"
            ) from e

    async def generate(
        self,
        messages: list[LLMMessage],
        schema: type[BaseModel] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        # Build Gemini conversation: system → user/model turns
        system_parts: list[str] = []
        gemini_history: list[dict[str, Any]] = []
        last_user_text = ""

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            elif msg.role == "user":
                last_user_text = msg.content
                if gemini_history or system_parts:
                    gemini_history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                gemini_history.append({"role": "model", "parts": [msg.content]})

        system_instruction = "\n\n".join(system_parts) if system_parts else None

        # If schema requested, inject JSON instruction
        if schema and last_user_text:
            schema_json = json.dumps(schema.model_json_schema(), indent=2)
            json_prompt = (
                f"{last_user_text}\n\n"
                f"Respond with ONLY valid JSON matching this schema:\n{schema_json}"
            )
            if gemini_history and gemini_history[-1]["role"] == "user":
                gemini_history[-1]["parts"] = [json_prompt]
            else:
                gemini_history.append({"role": "user", "parts": [json_prompt]})
        elif not gemini_history:
            gemini_history.append({"role": "user", "parts": [last_user_text]})

        async def _call() -> Any:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._sync_generate,
                system_instruction,
                gemini_history,
                temperature,
                max_tokens,
            )

        try:
            result = await asyncio.wait_for(_with_retry(_call), timeout=60.0)
            content: str = result.get("content", "")
            parsed: dict[str, Any] | None = result.get("parsed")

            return LLMResponse(
                content=content,
                parsed=parsed,
                prompt_tokens=result.get("prompt_tokens", 0),
                completion_tokens=result.get("completion_tokens", 0),
                model=self._model_name,
                provider=self.provider_name,
            )
        except asyncio.TimeoutError as e:
            logger.error("gemini_timeout", timeout_s=60)
            raise AIProviderError(
                "Gemini request timed out after 60s. "
                "This may be a network issue (wsarecv / connection reset to Google APIs). "
                "Switch to LLM_PROVIDER=mock in .env for offline operation."
            ) from e

    def _sync_generate(
        self,
        system_instruction: str | None,
        history: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Synchronous Gemini call — run inside executor to avoid blocking event loop."""
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        model = self._genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system_instruction,
            generation_config=generation_config,
        )

        # All turns except last are history; last is the current message
        *prior, last_turn = history
        chat = model.start_chat(history=prior)
        response = chat.send_message(last_turn["parts"])

        content = response.text or ""
        parsed: dict[str, Any] | None = None

        # Try JSON parse if response looks like JSON
        stripped = content.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                # Try extracting JSON block from markdown
                import re
                m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
                if m:
                    try:
                        parsed = json.loads(m.group(1))
                    except json.JSONDecodeError:
                        pass

        usage = getattr(response, "usage_metadata", None)
        return {
            "content": content,
            "parsed": parsed,
            "prompt_tokens": getattr(usage, "prompt_token_count", 0) if usage else 0,
            "completion_tokens": getattr(usage, "candidates_token_count", 0) if usage else 0,
        }

    async def embed(
        self,
        texts: list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        """Gemini embedding via text-embedding-004."""
        if not texts:
            return []

        async def _call() -> list[list[float]]:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_embed, texts)

        try:
            return await asyncio.wait_for(_with_retry(_call), timeout=30.0)
        except asyncio.TimeoutError as e:
            raise AIProviderError("Gemini embedding timed out after 30s.") from e

    def _sync_embed(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            response = self._genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document",
            )
            results.append(response["embedding"])
        return results
