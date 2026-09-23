"""
app/speech/router.py
FastAPI Router for ClaimSaathi Voice Mode:
- GET  /voice/config: Capabilities, available voices, and rate limit specs
- POST /voice/transcribe: Ingest audio recording and return validated transcript
- POST /voice/speak: Synthesize speakable text into streaming WAV audio
"""
from __future__ import annotations

import io
from typing import Any, Literal
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
import structlog

from app.auth.models import User
from app.auth.service import get_optional_current_user
from app.core.config import get_settings
from app.speech.providers import get_speech_provider, TranscriptionResult

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


class VoiceConfigResponse(BaseModel):
    enabled: bool
    gemini_stt_available: bool
    gemini_tts_available: bool
    default_voice_hi: str
    default_voice_en: str
    max_seconds: int
    max_chars: int


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=800)
    language: str = Field("hi", description="Language code: en, hi, or hinglish")
    voice: str | None = None
    speed: float = Field(1.0, ge=0.5, le=2.0)


@router.get("/config", response_model=VoiceConfigResponse)
async def get_voice_config() -> VoiceConfigResponse:
    """Returns Voice Mode configuration, supported voices, and limits."""
    settings = get_settings()
    has_gemini = bool(settings.GEMINI_API_KEY and "PASTE" not in settings.GEMINI_API_KEY)
    return VoiceConfigResponse(
        enabled=settings.VOICE_ENABLED,
        gemini_stt_available=has_gemini,
        gemini_tts_available=has_gemini,
        default_voice_hi=settings.TTS_VOICE_HI,
        default_voice_en=settings.TTS_VOICE_EN,
        max_seconds=settings.VOICE_MAX_SECONDS,
        max_chars=settings.TTS_MAX_CHARS,
    )


@router.post("/transcribe", response_model=TranscriptionResult)
async def transcribe_audio(
    file: UploadFile = File(...),
    language_hint: str = Form("auto"),
    auth_user: User | None = Depends(get_optional_current_user),
) -> TranscriptionResult:
    """
    Ingests recorded audio, performs privacy check, and transcribes speech using Gemini STT.
    Process audio in-memory only (STORE_AUDIO=false default).
    """
    settings = get_settings()
    if not settings.VOICE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice Mode is currently disabled by administrator configuration.",
        )

    # Read audio bytes (max 25MB upload protection)
    audio_bytes = await file.read()
    if len(audio_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio recording exceeds maximum permitted size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    if len(audio_bytes) < 100:
        return TranscriptionResult(
            text="",
            language=language_hint if language_hint != "auto" else "hi",
            confidence=0.0,
            contains_amounts_or_dates=False,
        )

    mime_type = file.content_type or "audio/webm"
    provider = get_speech_provider()

    result = await provider.transcribe(
        audio_bytes=audio_bytes,
        mime_type=mime_type,
        lang_hint=language_hint if language_hint != "auto" else None,
    )

    logger.info(
        "voice_transcribed",
        bytes=len(audio_bytes),
        lang=result.language,
        confidence=result.confidence,
        contains_numbers=result.contains_amounts_or_dates,
    )
    return result


@router.post("/speak")
async def speak_text(
    body: SpeakRequest,
    auth_user: User | None = Depends(get_optional_current_user),
) -> Response:
    """
    Synthesize speakable text into WAV audio stream.
    Validates character limits and returns audio/wav container.
    """
    settings = get_settings()
    if not settings.VOICE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice Mode is currently disabled.",
        )

    if len(body.text) > settings.TTS_MAX_CHARS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Speech synthesis text exceeds max character limit ({settings.TTS_MAX_CHARS}).",
        )

    provider = get_speech_provider()
    wav_bytes = await provider.synthesize(
        text=body.text,
        language=body.language,
        voice=body.voice,
        speed=body.speed,
    )

    is_mock = getattr(provider, "last_was_mock", False)
    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "Cache-Control": f"public, max-age={settings.VOICE_CACHE_TTL_SECONDS}",
            "Content-Disposition": "inline; filename=speech.wav",
            "X-Speech-Provider": "mock" if is_mock else "gemini",
        },
    )
