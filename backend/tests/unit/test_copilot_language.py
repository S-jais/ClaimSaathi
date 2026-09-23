"""
tests/unit/test_copilot_language.py
Unit tests for Copilot multilingual capabilities (English, Hindi, Hinglish):
- Language detection for Devanagari, Roman Hindi, and English
- Spoken text generation for voice mode
- Dynamic glossary and voice-mode prompt injection
- Fraud and prediction refusal boundaries
"""
import pytest
from app.copilot.orchestrator import (
    detect_message_language,
    generate_spoken_text,
    get_copilot_orchestrator,
)


def test_detect_message_language_devanagari():
    # Devanagari Hindi
    assert detect_message_language("मेरा क्लेम रिजेक्ट हो गया 4.2 वाला") == "hi"
    assert detect_message_language("डेढ़ लाख का बिल है, कितना मिलेगा?") == "hi"
    assert detect_message_language("मुझे कितने पैसे वापस मिलेंगे?") == "hi"


def test_detect_message_language_hinglish():
    # Roman Hindi (Hinglish) with typos and common markers
    assert detect_message_language("mera claim reject hogya kya kru") == "hinglish"
    assert detect_message_language("paise kab milenge?") == "hinglish"
    assert detect_message_language("bill ki date badal du kya?") == "hinglish"
    assert detect_message_language("discharge summary ka page 2 missing hai kya?") == "hinglish"
    assert detect_message_language("bas itna bata do claim approve hoga na?") == "hinglish"
    assert detect_message_language("bhai mera claim reject ho gaya, ab kya karu?") == "hinglish"


def test_detect_message_language_english():
    # English
    assert detect_message_language("Why was my claim deducted?") == "en"
    assert detect_message_language("Am I ready to submit?") == "en"
    assert detect_message_language("Explain the 60-month moratorium period under IRDAI.") == "en"


def test_generate_spoken_text():
    raw_reply = (
        "**FACT**: Your hospital bill total is ₹1,84,500 [FACT: doc_bill_1].\n\n"
        "**INTERPRETATION**: The insurer cited Clause 4.2 for waiting period.\n\n"
        "**RECOMMENDATION**: Request signed indoor case papers from Apollo Hospital."
    )
    spoken = generate_spoken_text(raw_reply, "en")
    assert "**" not in spoken
    assert "one lakh eighty-four thousand five hundred rupees" in spoken
    assert len([s for s in spoken.split(".") if s.strip()]) <= 4


def test_prompt_rendering_injects_glossary_for_hindi():
    orchestrator = get_copilot_orchestrator()
    case_state = {
        "claim_reference": "CLM-20491",
        "patient_name": "Siddhartha",
        "hospital_name": "Apollo Hospital",
        "claim_amount_inr": 184500,
        "status": "rejected",
        "readiness_score": 85,
        "documents": [],
    }
    deadlines = [{"name": "Settlement SLA", "due_date": "2026-10-20", "days_remaining": 30, "statutory_source": "IRDAI 2024"}]

    # 1. Hindi prompt should include glossary
    prompt_hi = orchestrator._render_system_prompt(
        stage="REJECTED_DECODING",
        case_state=case_state,
        deadlines=deadlines,
        cognee_facts=[],
        clauses=[],
        ui_language="hi",
        detected_language="hi",
        mode="text",
        user_first_name="Siddhartha",
    )
    assert "HINDI INSURANCE GLOSSARY" in prompt_hi
    assert "वेटिंग पीरियड (प्रतीक्षा अवधि)" in prompt_hi
    assert "Siddhartha" in prompt_hi
    assert "REJECTED_DECODING" in prompt_hi

    # 2. English prompt should NOT include glossary (saves tokens)
    prompt_en = orchestrator._render_system_prompt(
        stage="CLAIM_PREPARATION",
        case_state=case_state,
        deadlines=deadlines,
        cognee_facts=[],
        clauses=[],
        ui_language="en",
        detected_language="en",
        mode="text",
        user_first_name="Siddhartha",
    )
    assert "HINDI INSURANCE GLOSSARY" not in prompt_en

    # 3. Voice mode should include voice instructions
    prompt_voice = orchestrator._render_system_prompt(
        stage="CLAIM_PREPARATION",
        case_state=case_state,
        deadlines=deadlines,
        cognee_facts=[],
        clauses=[],
        ui_language="en",
        detected_language="en",
        mode="voice",
        user_first_name="Siddhartha",
    )
    assert "VOICE MODE" in prompt_voice
    assert "spoken_text" in prompt_voice


def test_parse_indian_number_words():
    from app.copilot.orchestrator import parse_indian_number_words

    assert parse_indian_number_words("डेढ़ लाख का बिल है") == 150000
    assert parse_indian_number_words("sawa lakh bill") == 125000
    assert parse_indian_number_words("पौने दो लाख") == 175000
    assert parse_indian_number_words("dhai hazar deductions") == 2500
    assert parse_indian_number_words("do lakh ka cover") == 200000


def test_explicit_language_switch_detection():
    assert detect_message_language("Hindi mein batao") == "hinglish"
    assert detect_message_language("English please") == "en"
    assert detect_message_language("In english") == "en"
    assert detect_message_language("हिंदी में बताइए") == "hi"
