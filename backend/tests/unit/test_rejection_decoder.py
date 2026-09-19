"""
tests/unit/test_rejection_decoder.py
Unit tests for the Rejection Decoder schema, confidence labeling,
and banned-phrase guardrails.
"""
import pytest
from app.ai.prompts.rejection_decoder import REJECTION_DECODER_SCHEMA
from app.ai.guardrails import detect_banned_phrases, validate_no_banned_phrases


def test_rejection_decoder_schema_structure():
    """Verify the enforced tripartite schema requires fact, ai_interpretation, and recommendation."""
    schema = REJECTION_DECODER_SCHEMA
    assert "fact_text" in schema["properties"]
    assert "ai_interpretation_text" in schema["properties"]
    assert "recommendation_text" in schema["properties"]
    assert "confidence" in schema["properties"]
    assert "disclaimer" in schema["properties"]

    required = schema["required"]
    assert "fact_text" in required
    assert "ai_interpretation_text" in required
    assert "recommendation_text" in required
    assert "confidence" in required


def test_rejection_decoder_banned_phrases_detected():
    """Verify that hallucinated guarantees or unauthorized approval promises are detected."""
    guaranteed_claim_text = (
        "We guarantee that your claim will be approved once you submit the appeal. "
        "The insurer is 100% required to pay."
    )
    banned = detect_banned_phrases(guaranteed_claim_text)
    assert len(banned) > 0
    assert any("guarantee" in b.lower() or "approved" in b.lower() for b in banned)

    # When validated by guardrails
    res = validate_no_banned_phrases(guaranteed_claim_text)
    assert res.passed is False
    assert res.result_code == "blocked_banned_phrase"


def test_rejection_decoder_compliant_output():
    """Verify that legally hedged, factually grounded outputs pass guardrails."""
    compliant_text = (
        "The rejection appears to be inconsistent with Chapter V of the IRDAI 2024 Master Circular. "
        "Consider filing a formal First-Level Grievance. Final claim decision remains with the insurer."
    )
    banned = detect_banned_phrases(compliant_text)
    assert banned == []
    res = validate_no_banned_phrases(compliant_text)
    assert res.passed is True
    assert res.result_code == "passed"
