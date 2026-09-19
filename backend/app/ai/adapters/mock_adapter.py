"""
app/ai/adapters/mock_adapter.py
MockLLMProvider — deterministic, schema-valid responses for CI and demo.
Clearly named so it is never confused with a real provider.
Used when LLM_PROVIDER=mock or in test fixtures.
NEVER silently used in production — get_llm_provider() raises on unknown provider.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.ai.provider import LLMMessage, LLMResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

# Deterministic embedding vector (1536-dim) for testing
_MOCK_EMBEDDING = [0.01] * 1536


class MockLLMProvider:
    """
    Deterministic mock LLM for CI/demo.
    Returns schema-valid, clearly labelled fixture data.
    All responses include the required disclaimer.
    """

    provider_name = "mock"

    async def generate(
        self,
        messages: list[LLMMessage],
        schema: type[BaseModel] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        logger.info("mock_llm_generate", schema=schema.__name__ if schema else None)

        # Build a schema-valid mock response
        if schema is not None:
            # Introspect the schema fields and build a valid mock
            mock_data: dict[str, Any] = {}
            for field_name, field_info in schema.model_fields.items():
                annotation = field_info.annotation
                if annotation is str or annotation == str | None:
                    # Inject meaningful mock content based on field name
                    if field_name == "fact_text":
                        mock_data[field_name] = (
                            "Clause 4.2 of your policy states that hospitalization "
                            "benefits apply for admissions of 24 hours or more."
                        )
                    elif field_name == "ai_interpretation_text":
                        mock_data[field_name] = (
                            "The rejection appears to reference insufficient supporting "
                            "documentation, which may relate to Clause 4.2."
                        )
                    elif field_name == "recommendation_text":
                        mock_data[field_name] = (
                            "Consider uploading your consultation notes. "
                            "This gap may be contestable if documentation is provided."
                        )
                    elif field_name == "disclaimer":
                        mock_data[field_name] = (
                            "AI explanation only. Final claim decision remains with the insurer."
                        )
                    else:
                        mock_data[field_name] = f"[Mock {field_name}]"
                elif annotation is float or annotation == float | None:
                    mock_data[field_name] = 0.82
                elif annotation is int or annotation == int | None:
                    mock_data[field_name] = 1
                elif annotation is bool:
                    mock_data[field_name] = True
                elif annotation is list or str(annotation).startswith("list"):
                    mock_data[field_name] = []
                else:
                    mock_data[field_name] = None

            # Validate against schema
            parsed = schema(**mock_data)
            content = json.dumps(mock_data)
            return LLMResponse(
                content=content,
                parsed=parsed.model_dump(),
                prompt_tokens=100,
                completion_tokens=200,
                model="mock-1.0",
                provider=self.provider_name,
            )

        return LLMResponse(
            content=(
                "This is a mock AI response. "
                "AI explanation only. Final claim decision remains with the insurer."
            ),
            parsed=None,
            prompt_tokens=50,
            completion_tokens=50,
            model="mock-1.0",
            provider=self.provider_name,
        )

    async def embed(
        self,
        texts: list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        """Returns deterministic mock embeddings (all 0.01). For CI use only."""
        return [list(_MOCK_EMBEDDING) for _ in texts]
