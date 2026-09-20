"""
tests/unit/test_copilot_guardrails.py
Unit tests for Copilot-specific safety guardrails:
- Approval prediction blocking (Section 5)
- Mandatory "Indicative payable estimate" label enforcement
- Uncited FACT downgrading to INTERPRETATION
"""
import pytest
from app.ai.guardrails import (
    detect_approval_predictions,
    sanitize_copilot_text,
    enforce_copilot_guardrails,
)


def test_detect_approval_predictions():
    bad_texts = [
        "You have an 85% chance of approval with this draft.",
        "Your claim will definitely be approved by Star Health.",
        "We promise a guaranteed settlement of ₹1,50,000.",
        "What are the odds of approval?",
    ]
    for text in bad_texts:
        matches = detect_approval_predictions(text)
        assert len(matches) > 0, f"Expected forbidden prediction in: {text}"

    clean_text = "Based on IRDAI regulations, you may appeal this room rent deduction."
    assert len(detect_approval_predictions(clean_text)) == 0


def test_sanitize_copilot_text():
    raw = "The Expected Settlement for your hospitalization is ₹65,000."
    sanitized = sanitize_copilot_text(raw)
    assert "Expected Settlement" not in sanitized
    assert "Indicative payable estimate — subject to your insurer's assessment" in sanitized


def test_enforce_copilot_guardrails_downgrades_uncited_fact():
    payload = {
        "reply": "Your claim has an 80% chance of approval. Expected Settlement: ₹50,000.",
        "sections": {
            "facts": [
                {"id": "f1", "text": "Hospital bill total is ₹85,000", "citations": ["doc_1"]},
                {"id": "f2", "text": "Insurer owes you an additional ₹25,000", "citations": []},  # Uncited
            ],
            "interpretations": [],
            "recommendations": [],
        },
    }

    guarded = enforce_copilot_guardrails(payload)

    # 1. Prediction removed from reply
    assert "80% chance of approval" not in guarded["reply"]
    # 2. Expected settlement replaced
    assert "Expected Settlement" not in guarded["reply"]
    # 3. Uncited fact f2 downgraded to interpretations
    facts = guarded["sections"]["facts"]
    assert len(facts) == 1
    assert facts[0]["id"] == "f1"

    interps = guarded["sections"]["interpretations"]
    assert len(interps) == 1
    assert "Insurer owes you" in interps[0]["text"]
