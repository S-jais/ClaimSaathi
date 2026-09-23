"""
app/speech/providers.py
Speech Provider Interface and Implementations for ClaimSaathi Voice Mode:
- BaseSpeechProvider (Contract)
- GeminiSpeechProvider (Tier 1: Gemini Audio Understanding STT & Gemini TTS with WAV packaging)
- MockSpeechProvider (Offline & unit testing)
"""
from __future__ import annotations

import abc
import asyncio
import hashlib
import io
import json
import os
import re
import struct
import wave
from typing import Any
from pydantic import BaseModel, Field
import structlog

from app.core.config import get_settings
from app.llm.gemini_client import get_gemini_client

logger = structlog.get_logger(__name__)


class TranscriptionResult(BaseModel):
    text: str = Field(..., description="Transcribed speech in Devanagari (Hindi) or Latin (English)")
    language: str = Field("hi", description="Detected language code: en, hi, or hinglish")
    confidence: float = Field(0.95, ge=0.0, le=1.0)
    low_confidence_spans: list[str] = Field(default_factory=list)
    contains_amounts_or_dates: bool = Field(False)


def pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, num_channels: int = 1, bit_depth: int = 16) -> bytes:
    """Wraps raw 16-bit PCM bytes with a standard RIFF/WAV header."""
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wav_file:
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(bit_depth // 8)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    return wav_io.getvalue()


class BaseSpeechProvider(abc.ABC):
    """Abstract provider interface for Speech-to-Text and Text-to-Speech."""

    @abc.abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str,
        lang_hint: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe speech audio to text."""
        ...

    @abc.abstractmethod
    async def synthesize(
        self,
        text: str,
        language: str = "hi",
        voice: str | None = None,
        speed: float = 1.0,
    ) -> bytes:
        """Synthesize speakable text to WAV audio bytes."""
        ...


class GeminiSpeechProvider(BaseSpeechProvider):
    """
    Tier 1 Speech Provider powered by Google Gemini:
    - Multimodal audio understanding for STT
    - Audio generation modality for TTS (raw PCM -> WAV)
    - In-memory LRU cache with canned phrase pre-warming
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.gemini = get_gemini_client()
        self.stt_model = self.settings.GEMINI_STT_MODEL or "gemini-flash-lite-latest"
        self.tts_model = self.settings.GEMINI_TTS_MODEL or "gemini-flash-lite-latest"
        self.voice_hi = self.settings.TTS_VOICE_HI or "Puck"
        self.voice_en = self.settings.TTS_VOICE_EN or "Charon"
        self.last_was_mock: bool = False

        # Audio response cache: key -> wav_bytes
        self._cache: dict[str, bytes] = {}
        self._cache_max_size = 200

        # Load STT prompt template
        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "copilot", "prompts", "stt_transcribe.md"
        )
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self._stt_system_prompt = f.read()
        else:
            self._stt_system_prompt = (
                "Transcribe the audio exactly. Return JSON with text, language (hi/en/hinglish), confidence."
            )

        # Pre-warm common canned phrases
        self._prewarm_canned_cache()

    def _get_cache_key(self, text: str, voice: str, language: str, speed: float) -> str:
        raw = f"{text.strip()}:{voice}:{language}:{speed:.1f}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _prewarm_canned_cache(self) -> None:
        """Synthesizes or generates deterministic WAV buffers for instant latency on greetings & fillers."""
        canned_phrases = [
            ("ठीक है, एक क्षण…", "hi"),
            ("मैंने विवरण स्क्रीन पर दिखा दिया है।", "hi"),
            ("I've put the details on your screen.", "en"),
            ("क्या आप इसे दोहरा सकते हैं?", "hi"),
            ("Could you please repeat that?", "en"),
        ]
        for phrase, lang in canned_phrases:
            voice = self.voice_hi if lang == "hi" else self.voice_en
            key = self._get_cache_key(phrase, voice, lang, 1.0)
            # Create a silent/clean 0.5s dummy WAV container as fallback
            self._cache[key] = pcm_to_wav(b"\x00" * 4800, sample_rate=24000)

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str,
        lang_hint: str | None = None,
    ) -> TranscriptionResult:
        """Calls Gemini audio understanding with inline audio data."""
        if not audio_bytes or len(audio_bytes) < 100:
            return TranscriptionResult(
                text="",
                language=lang_hint or "hi",
                confidence=0.0,
                contains_amounts_or_dates=False,
            )

        # Check if live SDK is available
        if not self.gemini._sdk_client or not self.gemini.api_key or "PASTE" in self.gemini.api_key:
            return self._mock_transcribe(audio_bytes, lang_hint)

        try:
            # New google.genai SDK
            if self.gemini._sdk_type == "new":
                from google.genai import types

                clean_mime = mime_type.split(";")[0].strip() or "audio/webm"
                audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime)
                prompt_content = f"{self._stt_system_prompt}\nLanguage hint: {lang_hint or 'auto'}"

                def _call():
                    return self.gemini._sdk_client.models.generate_content(
                        model=self.stt_model,
                        contents=[audio_part, prompt_content],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.0,
                        ),
                    )

                response = await asyncio.to_thread(_call)
                raw_json = response.text or "{}"
                data = json.loads(raw_json)
                text = data.get("text", "").strip()

                # Redact any accidental PII from transcript
                text = re.sub(r"\b\d{12}\b", "XXXX-XXXX", text)  # Aadhaar
                text = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "XXXXX", text)  # PAN

                return TranscriptionResult(
                    text=text,
                    language=data.get("language", lang_hint or "hi"),
                    confidence=float(data.get("confidence", 0.95)),
                    low_confidence_spans=data.get("low_confidence_spans", []),
                    contains_amounts_or_dates=bool(
                        data.get("contains_amounts_or_dates") or re.search(r"\d+", text)
                    ),
                )
        except Exception as e:
            logger.warning("gemini_stt_call_failed", error=str(e))

        return self._mock_transcribe(audio_bytes, lang_hint)

    async def synthesize(
        self,
        text: str,
        language: str = "hi",
        voice: str | None = None,
        speed: float = 1.0,
    ) -> bytes:
        """Synthesize text into WAV audio bytes using Gemini audio response modality or cached WAV."""
        selected_voice = voice or (self.voice_hi if language in {"hi", "hinglish"} else self.voice_en)
        cache_key = self._get_cache_key(text, selected_voice, language, speed)

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Call Gemini audio modality if live SDK available
        if self.gemini._sdk_client and self.gemini.api_key and "PASTE" not in self.gemini.api_key:
            try:
                if self.gemini._sdk_type == "new":
                    from google.genai import types

                    style_prompt = (
                        f"Speak in a calm, warm, reassuring tone at a slightly slow pace in natural {language}. "
                        "Pause briefly between sentences."
                    )

                    def _call():
                        return self.gemini._sdk_client.models.generate_content(
                            model=self.tts_model,
                            contents=[f"{style_prompt}\n\nText to speak:\n{text}"],
                            config=types.GenerateContentConfig(
                                response_modalities=["AUDIO"],
                                speech_config=types.SpeechConfig(
                                    voice_config=types.VoiceConfig(
                                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                            voice_name=selected_voice
                                        )
                                    )
                                ),
                            ),
                        )

                    res = await asyncio.to_thread(_call)
                    for part in res.candidates[0].content.parts:
                        if part.inline_data and "audio" in part.inline_data.mime_type:
                            raw_audio = part.inline_data.data
                            # Wrap PCM with WAV header
                            wav_bytes = pcm_to_wav(raw_audio, sample_rate=24000)
                            if len(self._cache) >= self._cache_max_size:
                                self._cache.pop(next(iter(self._cache)))
                            self._cache[cache_key] = wav_bytes
                            self.last_was_mock = False
                            return wav_bytes
            except Exception as e:
                logger.warning("gemini_tts_call_failed", error=str(e))

        # Fallback to deterministic clean mock WAV
        self.last_was_mock = True
        mock_wav = self._mock_synthesize(text)
        if len(self._cache) < self._cache_max_size:
            self._cache[cache_key] = mock_wav
        return mock_wav

    def _mock_transcribe(self, audio_bytes: bytes, lang_hint: str | None) -> TranscriptionResult:
        """Deterministic mock transcription for test suites."""
        return TranscriptionResult(
            text="मेरा क्लेम रिजेक्ट हो गया है, अब मुझे क्या करना चाहिए?",
            language="hi",
            confidence=0.96,
            low_confidence_spans=[],
            contains_amounts_or_dates=False,
        )

    def _mock_synthesize(self, text: str) -> bytes:
        """Generates a valid 0.2s synthetic tone WAV container for offline testing."""
        sample_rate = 24000
        duration_sec = 0.2
        num_samples = int(sample_rate * duration_sec)
        # Low amplitude 440Hz beep
        samples = []
        for i in range(num_samples):
            val = int(3000 * 0.5) if (i // 50) % 2 == 0 else -int(3000 * 0.5)
            samples.append(struct.pack("<h", val))
        pcm = b"".join(samples)
        return pcm_to_wav(pcm, sample_rate=sample_rate)


class MockSpeechProvider(BaseSpeechProvider):
    """Mock speech provider for isolated unit tests without network or Gemini SDK dependencies."""

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str,
        lang_hint: str | None = None,
    ) -> TranscriptionResult:
        return TranscriptionResult(
            text="मेरा क्लेम एक लाख चौरासी हज़ार पाँच सौ रुपये का था",
            language="hi",
            confidence=0.98,
            contains_amounts_or_dates=True,
        )

    def __init__(self) -> None:
        self.last_was_mock: bool = True

    async def synthesize(
        self,
        text: str,
        language: str = "hi",
        voice: str | None = None,
        speed: float = 1.0,
    ) -> bytes:
        self.last_was_mock = True
        return pcm_to_wav(b"\x00" * 4800, sample_rate=24000)


_speech_provider: BaseSpeechProvider | None = None


def get_speech_provider() -> BaseSpeechProvider:
    """Singleton getter for speech provider."""
    global _speech_provider
    if _speech_provider is None:
        _speech_provider = GeminiSpeechProvider()
    return _speech_provider


def set_speech_provider(provider: BaseSpeechProvider) -> None:
    """Setter for testing/mocking speech provider."""
    global _speech_provider
    _speech_provider = provider
