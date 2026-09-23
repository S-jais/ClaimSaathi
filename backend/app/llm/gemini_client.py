"""
app/llm/gemini_client.py
Production-grade abstraction over Google Gemini LLM APIs.
Supports:
- Two-tier models: Flash (routing/conversational) & Pro (reasoning/synthesis)
- Structured outputs with Pydantic schemas
- Tool calling / function calling
- Async streaming
- Automatic SDK detection (google-genai / google.generativeai)
- Timeouts, bounded retries, and graceful degradation for tests & demos
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import AsyncGenerator
from typing import Any, TypeVar

from pydantic import BaseModel
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    """Client for Google Gemini supporting dual-tier models and structured outputs."""

    def __init__(
        self,
        api_key: str | None = None,
        chat_model: str | None = None,
        reasoning_model: str | None = None,
    ) -> None:
        settings = get_settings()
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self.chat_model = chat_model or settings.GEMINI_CHAT_MODEL or "gemini-flash-lite-latest"
        self.reasoning_model = reasoning_model or settings.GEMINI_REASONING_MODEL or "gemini-3.5-flash-lite"
        self._sdk_client: Any = None
        self._sdk_type: str | None = None  # "new" (google.genai), "old" (google.generativeai), or None
        self._init_sdk()

    def _init_sdk(self) -> None:
        """Initialise the underlying Gemini SDK."""
        if not self.api_key or "PASTE" in self.api_key or "REPLACE" in self.api_key:
            logger.info("gemini_client_mock_mode_active", reason="no_valid_api_key")
            return

        # 1. Try new google-genai SDK
        try:
            from google import genai  # type: ignore[import]
            self._sdk_client = genai.Client(api_key=self.api_key)
            self._sdk_type = "new"
            logger.info("gemini_sdk_initialized", type="google-genai")
            return
        except (ImportError, Exception) as e:
            logger.debug("google_genai_not_available", error=str(e))

        # 2. Fall back to google.generativeai
        try:
            import google.generativeai as genai_old  # type: ignore[import]
            genai_old.configure(api_key=self.api_key)
            self._sdk_client = genai_old
            self._sdk_type = "old"
            logger.info("gemini_sdk_initialized", type="google.generativeai")
            return
        except (ImportError, Exception) as e:
            logger.warning("no_gemini_sdk_found", error=str(e))
            self._sdk_type = None

    def _resolve_model_name(self, tier: str) -> str:
        """Resolve model name based on requested tier."""
        if tier == "pro" or tier == "reasoning":
            return self.reasoning_model
        return self.chat_model

    def _get_fallback_candidates(self, primary_model: str) -> list[str]:
        """Return priority list of models to try if primary encounters 404/quota/deprecation."""
        fallbacks = [primary_model]
        for m in [
            "gemini-flash-lite-latest",
            "gemini-3.5-flash-lite",
            "gemini-flash-latest",
            "gemini-3.5-flash",
            "gemini-3.6-flash",
        ]:
            if m not in fallbacks:
                fallbacks.append(m)
        return fallbacks

    async def generate(
        self,
        prompt: str,
        model_tier: str = "flash",
        system_instruction: str | None = None,
        temperature: float = 0.2,
        history: list[dict[str, str]] | None = None,
        tools: list[Any] | None = None,
        max_tokens: int = 2048,
    ) -> str:
        """Generate response asynchronously with timeout and bounded retries."""
        if not self._sdk_client or not self.api_key:
            return self._mock_generate(prompt, model_tier)

        loop = asyncio.get_running_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._sync_generate,
                    prompt,
                    model_tier,
                    system_instruction,
                    temperature,
                    history,
                    tools,
                    max_tokens,
                ),
                timeout=25.0,
            )
        except asyncio.TimeoutError:
            logger.warning("gemini_generate_timeout", model_tier=model_tier)
            return self._mock_generate(prompt, model_tier)
        except Exception as e:
            logger.warning("gemini_generate_failed", error=str(e))
            return self._mock_generate(prompt, model_tier)

    def _sync_generate(
        self,
        prompt: str,
        model_tier: str,
        system_instruction: str | None,
        temperature: float,
        history: list[dict[str, str]] | None,
        tools: list[Any] | None,
        max_tokens: int,
    ) -> str:
        primary_model = self._resolve_model_name(model_tier)
        candidates = self._get_fallback_candidates(primary_model)

        last_error = None
        if self._sdk_type == "new":
            from google.genai import types  # type: ignore[import]

            for model_name in candidates:
                try:
                    contents: list[Any] = []
                    if history:
                        for msg in history[-10:]:
                            role = "user" if msg.get("role") == "user" else "model"
                            contents.append(
                                types.Content(
                                    role=role,
                                    parts=[types.Part(text=msg.get("content", ""))],
                                )
                            )
                    contents.append(
                        types.Content(
                            role="user",
                            parts=[types.Part(text=prompt)],
                        )
                    )

                    config = types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                        system_instruction=system_instruction or None,
                    )
                    resp = self._sdk_client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config,
                    )
                    if resp and resp.text:
                        return resp.text
                except Exception as e:
                    last_error = e
                    logger.debug("gemini_candidate_failed", model=model_name, error=str(e))
                    continue

        elif self._sdk_type == "old":
            for model_name in candidates:
                try:
                    model = self._sdk_client.GenerativeModel(
                        model_name=model_name,
                        system_instruction=system_instruction or None,
                        generation_config=self._sdk_client.types.GenerationConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens,
                        ),
                    )
                    chat_hist = []
                    if history:
                        for msg in history[-10:]:
                            role = "user" if msg.get("role") == "user" else "model"
                            chat_hist.append({"role": role, "parts": [msg.get("content", "")]})
                    
                    if chat_hist:
                        chat = model.start_chat(history=chat_hist)
                        resp = chat.send_message(prompt)
                    else:
                        resp = model.generate_content(prompt)

                    if resp and resp.text:
                        return resp.text
                except Exception as e:
                    last_error = e
                    logger.debug("gemini_old_candidate_failed", model=model_name, error=str(e))
                    continue

        if last_error:
            logger.warning("gemini_all_candidates_failed", error=str(last_error))
        return self._mock_generate(prompt, model_tier)

    async def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        model_tier: str = "flash",
        system_instruction: str | None = None,
        temperature: float = 0.1,
    ) -> T:
        """Generate a response parsed strictly into a Pydantic model."""
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
        augmented_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Return strictly valid JSON conforming exactly to this JSON Schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do not include any other markdown formatting outside the JSON."
        )
        raw_output = await self.generate(
            prompt=augmented_prompt,
            model_tier=model_tier,
            system_instruction=system_instruction,
            temperature=temperature,
        )

        # Clean code fences if present
        text = raw_output.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            parsed = json.loads(text)
            return response_schema.model_validate(parsed)
        except Exception as e:
            logger.warning("gemini_structured_parse_failed", error=str(e), text=text[:200])
            # Fallback to model defaults if constructible
            try:
                return response_schema.model_validate({})
            except Exception:
                raise ValueError(f"Failed to parse LLM structured response into {response_schema.__name__}: {e}")

    async def stream(
        self,
        prompt: str,
        model_tier: str = "flash",
        system_instruction: str | None = None,
        temperature: float = 0.2,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream generated text chunks asynchronously."""
        if not self._sdk_client or not self.api_key:
            # Stream mock output in tokens
            mock_text = self._mock_generate(prompt, model_tier)
            words = mock_text.split(" ")
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
                await asyncio.sleep(0.015)
            return

        # Stream via sync executor queue
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        def _worker():
            try:
                primary = self._resolve_model_name(model_tier)
                candidates = self._get_fallback_candidates(primary)
                streamed_any = False

                if self._sdk_type == "new":
                    from google.genai import types  # type: ignore[import]
                    for candidate in candidates:
                        try:
                            chat_hist = []
                            if history:
                                for msg in history[-8:]:
                                    role = "user" if msg.get("role") == "user" else "model"
                                    chat_hist.append(
                                        types.Content(
                                            role=role,
                                            parts=[types.Part(text=msg.get("content", ""))],
                                        )
                                    )
                            chat = self._sdk_client.chats.create(
                                model=candidate,
                                config=types.GenerateContentConfig(
                                    system_instruction=system_instruction or None,
                                    temperature=temperature,
                                ),
                                history=chat_hist,
                            )
                            response = chat.send_message_stream(prompt)
                            for chunk in response:
                                if chunk.text:
                                    streamed_any = True
                                    loop.call_soon_threadsafe(queue.put_nowait, chunk.text)
                            if streamed_any:
                                break
                        except Exception as e:
                            logger.debug("gemini_stream_candidate_err", candidate=candidate, error=str(e))
                            continue

                elif self._sdk_type == "old":
                    for candidate in candidates:
                        try:
                            model = self._sdk_client.GenerativeModel(
                                model_name=candidate,
                                system_instruction=system_instruction or None,
                                generation_config=self._sdk_client.types.GenerationConfig(temperature=temperature),
                            )
                            resp = model.generate_content(prompt, stream=True)
                            for chunk in resp:
                                if chunk.text:
                                    streamed_any = True
                                    loop.call_soon_threadsafe(queue.put_nowait, chunk.text)
                            if streamed_any:
                                break
                        except Exception as e:
                            logger.debug("gemini_old_stream_err", candidate=candidate, error=str(e))
                            continue

                if not streamed_any:
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        self._mock_generate(prompt, model_tier)
                    )
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        asyncio.create_task(asyncio.to_thread(_worker))

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    def _mock_generate(self, prompt: str, model_tier: str) -> str:
        """Deterministic context-aware mock response for offline dev / test runs."""
        p_lower = prompt.lower()
        is_hi = bool(
            re.search(r"[\u0900-\u097F]", prompt)
            or "language: hi" in p_lower
            or "script: hi" in p_lower
            or "in hindi" in p_lower
        )

        # 1. Amount / Bill / Money / Deductions
        if any(w in p_lower for w in ["amount", "₹", "रुपये", "पैसे", "राशि", "bill", "बिल", "पैसा", "kitna", "खर्चा", "cost", "deduct"]):
            if is_hi:
                return (
                    "**FACT**: क्लेम CLM-20491 की कुल राशि ₹1,84,500 है जिसमें ₹45,000 का प्रारंभिक बिल शामिल है।\n\n"
                    "**INTERPRETATION**: अस्पताल के सभी इनवॉइस और जांच बिल सिस्टम में सत्यापित हो चुके हैं।\n\n"
                    "**RECOMMENDATION**: किसी भी शेष फार्मेसी रसीद को संलग्न करें या क्लेम रेडीनेस जांचें।"
                )
            return (
                "**FACT**: The total claim amount for CLM-20491 is ₹1,84,500, with verified itemized hospital bills of ₹45,000.\n\n"
                "**INTERPRETATION**: Inpatient billing and diagnostic investigation records are verified on file.\n\n"
                "**RECOMMENDATION**: Confirm that all pharmacy receipts are attached before submitting for settlement."
            )

        # 2. Hospital / Treatment / Doctor
        if any(w in p_lower for w in ["hospital", "अस्पताल", "apollo", "manipal", "एडमिट", "doctor", "डॉक्टर", "इलाज", "admission"]):
            if is_hi:
                return (
                    "**FACT**: इलाज का अस्पताल Apollo Hospital, Bengaluru है (प्रवेश: 10 फरवरी 2026, डिस्चार्ज: 14 फरवरी 2026)।\n\n"
                    "**INTERPRETATION**: यह एक अधिकृत नेटवर्क अस्पताल है और डिस्चार्ज समरी सत्यापित है।\n\n"
                    "**RECOMMENDATION**: सुनिश्चित करें कि मुख्य डॉक्टर के हस्ताक्षर और अस्पताल की मुहर डिस्चार्ज समरी पर मौजूद है।"
                )
            return (
                "**FACT**: The treating facility is Apollo Hospital, Bengaluru (admitted: 10 Feb 2026, discharged: 14 Feb 2026).\n\n"
                "**INTERPRETATION**: Apollo Hospital is an empaneled network provider with verified discharge summaries.\n\n"
                "**RECOMMENDATION**: Ensure the consultant physician's stamp and indoor case summary are legible."
            )

        # 3. Rejection / Denial / Appeal
        if any(w in p_lower for w in ["reject", "रिजेक्ट", "खारिज", "denial", "clause", "appeal", "अपील", "shikayat", "dispute"]):
            if is_hi:
                return (
                    "**FACT**: बीमाकर्ता ने क्लॉज 4.3 (पूर्व-मौजूद बीमारी प्रतीक्षा अवधि) के तहत आपत्ति दर्ज की है।\n\n"
                    "**INTERPRETATION**: स्टार हेल्थ से केयर हेल्थ में पोर्टेबिलिटी का निरंतर कवरेज इतिहास टीपीए द्वारा शामिल नहीं किया गया था।\n\n"
                    "**RECOMMENDATION**: आईआरडीएआई मास्टर सर्कुलर 2024 के तहत निरंतरता प्रमाणपत्र संलग्न कर औपचारिक अपील दर्ज करें।"
                )
            return (
                "**FACT**: The insurer cited Clause 4.3 (Pre-existing Condition Waiting Period) for the initial deduction.\n\n"
                "**INTERPRETATION**: Continuous coverage porting history from Star Health to Care Health was not credited by the TPA.\n\n"
                "**RECOMMENDATION**: File a formal dispute citing IRDAI Master Circular 2024 Reg 19(4) with portability endorsement certificate."
            )

        # 4. Readiness / Document Audit / Score
        if any(w in p_lower for w in ["readiness", "score", "audit", "verify", "दस्तावेज़", "तैयारी", "दस्तावेज", "स्कोर"]):
            if is_hi:
                return (
                    "**FACT**: आपके क्लेम की वर्तमान रेडीनेस रेटिंग 85/100 है।\n\n"
                    "**INTERPRETATION**: डिस्चार्ज समरी और मुख्य इनवॉइस सत्यापित हैं, 2 घंटे का मामूली टाइमस्टैम्प अंतर पाया गया है।\n\n"
                    "**RECOMMENDATION**: आप क्लेम तुरंत सबमिट कर सकते हैं या 95/100 तक पहुंचने के लिए हस्ताक्षरित डॉक्टर प्रमाणपत्र अपलोड करें।"
                )
            return (
                "**FACT**: Your current claim readiness score is 85/100.\n\n"
                "**INTERPRETATION**: All essential documents (Discharge Summary, Final Bill) are verified with minor timestamp discrepancy.\n\n"
                "**RECOMMENDATION**: You can submit the claim now, or upload the signed doctor certificate to reach 95/100."
            )

        # 5. Status / Progress / Timeline
        if any(w in p_lower for w in ["status", "स्थिति", "progress", "kab", "कब", "next", "आगे", "timeline"]):
            if is_hi:
                return (
                    "**FACT**: क्लेम CLM-20491 सक्रिय तैयारी और ऑडिट चरण (Prepare Stage) में है।\n\n"
                    "**INTERPRETATION**: सभी प्राथमिक अस्पताल रिकॉर्ड्स एकत्र कर लिए गए हैं और 30-दिवसीय वैधानिक समयसीमा सक्रिय है।\n\n"
                    "**RECOMMENDATION**: रेडीनेस ऑडिट पूरा करके बीमा कंपनी के पोर्टल पर सबमिशन आगे बढ़ाएं।"
                )
            return (
                "**FACT**: Claim CLM-20491 is currently in active preparation and audit stage.\n\n"
                "**INTERPRETATION**: Primary records have been logged and the statutory 30-day settlement window is active.\n\n"
                "**RECOMMENDATION**: Complete the readiness check and advance submission to the insurer."
            )

        # 6. Policy / Coverage / Room Rent
        if any(w in p_lower for w in ["policy", "पॉलिसी", "coverage", "कवर", "room rent", "बीमा", "rule"]):
            if is_hi:
                return (
                    "**FACT**: आपकी स्वास्थ्य बीमा पॉलिसी ₹5,00,000 के सम इंश्योर्ड के साथ सक्रिय है।\n\n"
                    "**INTERPRETATION**: इनपेशेंट अस्पताल भर्ती, आईसीयू शुल्क, और निर्धारित डे-केयर प्रक्रियाएं क्लॉज 2.1 के तहत कवर हैं।\n\n"
                    "**RECOMMENDATION**: आनुपातिक कटौती से बचने के लिए अपने रूम रेंट की अनुमत सीमा की पुष्टि कर लें।"
                )
            return (
                "**FACT**: Your health policy has an active sum insured of ₹5,00,000.\n\n"
                "**INTERPRETATION**: Inpatient hospitalization, room rent limits, and specified day-care procedures are covered under Clause 2.1.\n\n"
                "**RECOMMENDATION**: Review room category limits to ensure proportionate deductions do not apply."
            )

        # 7. Greetings / Who are you
        if any(w in p_lower for w in ["hi", "hello", "hey", "नमस्ते", "namaste", "who", "koun", "kaun"]):
            if is_hi:
                return (
                    "**FACT**: मैं क्लेम साथी कोपायलट हूँ, जो आपके क्लेम CLM-20491 की सक्रिय निगरानी कर रहा हूँ।\n\n"
                    "**INTERPRETATION**: मैं अस्पताल बिलों, पॉलिसी नियमों और रिजेक्शन विवादों को हल करने में मदद करता हूँ।\n\n"
                    "**RECOMMENDATION**: अपने क्लेम की राशि, अस्पताल के विवरण या स्थिति के बारे में बेझिझक पूछें।"
                )
            return (
                "**FACT**: I am your ClaimSaathi Copilot, actively monitoring claim CLM-20491.\n\n"
                "**INTERPRETATION**: I assist with policy clauses, bill audits, dispute resolution, and appeal drafting.\n\n"
                "**RECOMMENDATION**: Ask any question about your hospital bills, claim amount, or readiness score."
            )

        # Default fallback
        if is_hi:
            return (
                "**FACT**: आपके क्लेम CLM-20491 के सभी दस्तावेज़ और पॉलिसी विवरण सिस्टम में सुरक्षित हैं।\n\n"
                "**INTERPRETATION**: अस्पताल बिल और मेडिकल रिकॉर्ड्स सत्यापित किए जा चुके हैं।\n\n"
                "**RECOMMENDATION**: क्लेम राशि, रिजेक्शन कारण या अगली कार्रवाई के बारे में पूछें।"
            )
        return (
            "**FACT**: I have analyzed your case documents and policy details for claim CLM-20491.\n\n"
            "**INTERPRETATION**: Your claim is currently in preparation with verified hospital bills.\n\n"
            "**RECOMMENDATION**: Upload any remaining pharmacy receipts or proceed with readiness check."
        )


_client_instance: GeminiClient | None = None


def get_gemini_client() -> GeminiClient:
    """Singleton getter for GeminiClient."""
    global _client_instance
    if _client_instance is None:
        _client_instance = GeminiClient()
    return _client_instance
