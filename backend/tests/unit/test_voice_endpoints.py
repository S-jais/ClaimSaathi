"""
tests/unit/test_voice_endpoints.py
Unit tests for Voice Mode endpoints:
- GET /api/v1/voice/config
- POST /api/v1/voice/transcribe
- POST /api/v1/voice/speak
- Voice turn through copilot messages with mode="voice"
"""
import io
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_app
from app.speech.providers import MockSpeechProvider, set_speech_provider, BaseSpeechProvider


@pytest.fixture(autouse=True)
def setup_mock_speech():
    mock = MockSpeechProvider()
    set_speech_provider(mock)
    yield
    from app.speech.providers import GeminiSpeechProvider
    set_speech_provider(GeminiSpeechProvider())


@pytest.mark.asyncio
async def test_voice_config_endpoint():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/voice/config")
        assert res.status_code == 200
        data = res.json()
        assert data["enabled"] is True
        assert data["max_seconds"] == 30
        assert data["max_chars"] == 800
        assert "default_voice_hi" in data


@pytest.mark.asyncio
async def test_voice_transcribe_endpoint():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        dummy_audio = b"\x00" * 500
        files = {"file": ("test.webm", dummy_audio, "audio/webm")}
        res = await client.post(
            "/api/v1/voice/transcribe",
            files=files,
            data={"language_hint": "hi"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "text" in data
        assert data["language"] in {"hi", "en", "hinglish"}
        assert data["confidence"] > 0.5


@pytest.mark.asyncio
async def test_voice_speak_endpoint():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/voice/speak",
            json={
                "text": "नमस्ते, आपका क्लेम ₹1,84,500 का है।",
                "language": "hi",
                "speed": 1.0,
            },
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "audio/wav"
        # Check RIFF header for valid WAV container
        content = res.content
        assert content[:4] == b"RIFF"
        assert content[8:12] == b"WAVE"


@pytest.mark.asyncio
async def test_copilot_voice_mode_turn():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        sess_res = await client.post("/api/v1/copilot/sessions", json={"case_id": "CLM-20491"})
        assert sess_res.status_code in {200, 201}
        session_id = sess_res.json()["id"]

        # Send voice message
        msg_res = await client.post(
            f"/api/v1/copilot/sessions/{session_id}/messages",
            json={
                "content": "mera claim reject ho gaya hai, ab kya karu?",
                "language": "hinglish",
                "mode": "voice",
                "input_source": "voice",
                "transcript_confidence": 0.96,
            },
        )
        assert msg_res.status_code == 200
        data = msg_res.json()
        assert "spoken_text" in data
        assert len(data["spoken_text"]) > 0
        assert "read_back_required" in data
        assert "reply" in data
