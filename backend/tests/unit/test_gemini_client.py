"""
tests/unit/test_gemini_client.py
Unit tests for GeminiClient dual-tier resolution, mock fallbacks, and structured parsing.
"""
import pytest
from pydantic import BaseModel
from app.llm.gemini_client import GeminiClient


class SampleResponseSchema(BaseModel):
    category: str = "health_insurance"
    score: int = 85
    summary: str = "Claim verified"


@pytest.mark.asyncio
async def test_gemini_client_dual_tier_resolution():
    client = GeminiClient(
        api_key=None,
        chat_model="gemini-2.5-flash",
        reasoning_model="gemini-2.5-pro",
    )
    assert client._resolve_model_name("flash") == "gemini-2.5-flash"
    assert client._resolve_model_name("pro") == "gemini-2.5-pro"
    assert client._resolve_model_name("reasoning") == "gemini-2.5-pro"


@pytest.mark.asyncio
async def test_gemini_client_mock_generate_deterministic():
    client = GeminiClient(api_key="")
    
    # Prompt about readiness
    res_readiness = await client.generate("What is my claim readiness score?", model_tier="flash")
    assert "FACT" in res_readiness
    assert "readiness score" in res_readiness.lower()

    # Prompt about rejection
    res_reject = await client.generate("Why did the insurer reject my knee replacement surgery?", model_tier="pro")
    assert "FACT" in res_reject
    assert "Clause 4.3" in res_reject or "dispute" in res_reject.lower()


@pytest.mark.asyncio
async def test_gemini_client_structured_parse():
    client = GeminiClient(api_key="")
    parsed = await client.generate_structured(
        prompt="Assess claim",
        response_schema=SampleResponseSchema,
        model_tier="flash",
    )
    assert isinstance(parsed, SampleResponseSchema)
    assert parsed.score >= 0


@pytest.mark.asyncio
async def test_gemini_client_streaming_chunks():
    client = GeminiClient(api_key="")
    chunks = []
    async for chunk in client.stream("Check my readiness score"):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    full_text = "".join(chunks)
    assert "FACT" in full_text
