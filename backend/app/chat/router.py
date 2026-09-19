"""
app/chat/router.py
FastAPI router for the ClaimSaathi AI Chatbot.
Supports both streaming (SSE) and non-streaming endpoints.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.chat.service import chat_stream, chat_once
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    claim_id: str = "CLM-20491"
    history: list[dict[str, str]] = []


class ChatResponse(BaseModel):
    answer: str
    claim_id: str
    cognee_used: bool = False


@router.post("/message", response_model=ChatResponse)
async def chat_message(body: ChatRequest) -> Any:
    """Non-streaming chat endpoint — returns full answer at once."""
    answer = await chat_once(
        question=body.question,
        claim_id=body.claim_id,
        history=body.history,
    )
    return ChatResponse(
        answer=answer,
        claim_id=body.claim_id,
    )


@router.post("/stream")
async def chat_stream_endpoint(body: ChatRequest, request: Request) -> StreamingResponse:
    """
    Server-Sent Events streaming endpoint.
    Frontend reads chunks as they arrive for typewriter effect.
    """
    async def event_generator():
        try:
            async for chunk in chat_stream(
                question=body.question,
                claim_id=body.claim_id,
                history=body.history,
            ):
                # SSE format: data: <chunk>\n\n
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            logger.error("chat_stream_error", error=str(e))
            yield f"data: {json.dumps({'error': 'Stream error, please retry'})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
async def chat_health() -> dict[str, str]:
    """Quick health check for chat service."""
    import os
    gemini_ok = bool(os.environ.get("GEMINI_API_KEY")) and "PASTE" not in os.environ.get("GEMINI_API_KEY", "")
    cognee_ok = bool(os.environ.get("COGNEE_API_KEY")) and "PASTE" not in os.environ.get("COGNEE_API_KEY", "")
    return {
        "status": "ok",
        "gemini": "configured" if gemini_ok else "mock_mode",
        "cognee": "configured" if cognee_ok else "disabled",
    }
