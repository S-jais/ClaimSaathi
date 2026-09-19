"""
backend/tests/unit/test_chat_tools.py
Unit tests for Chatbot Grounding Tools and Numeric Consistency Validator.
"""
from app.chat.tools import (
    get_reimbursement_breakdown,
    explain_line_item,
    validate_numeric_consistency,
)


def test_reimbursement_breakdown_tool():
    sample_items = [
        {"description": "Surgeon Fee", "amount_paise": 4000000},
        {"description": "Surgical Gloves", "amount_paise": 50000},
    ]
    breakdown = get_reimbursement_breakdown("clm-test", items=sample_items)
    assert breakdown["gross_billed_paise"] == 4050000
    assert breakdown["commonly_non_payable_paise"] == 50000
    assert "₹40,500.00" in breakdown["gross_billed"]
    assert "Indicative payable estimate" in breakdown["estimate_label"]


def test_explain_line_item_tool():
    expl = explain_line_item("Nitrile Gloves")
    assert expl["classification"] == "COMMONLY_NON_PAYABLE"
    assert expl["rule_id"] == "IRDAI-NP-001"
    assert "Gloves" in expl["guideline_reference"]
    assert expl["patient_remedy"] is not None


def test_numeric_consistency_validator():
    allowed_amounts = {
        7300000,  # ₹73,000.00
        500000,   # ₹5,000.00
        6120000,  # ₹61,200.00
        18450000, # ₹1,84,500.00
    }

    # Consistent text
    valid_text = "Your gross hospital bill was ₹73,000.00, with deductions of ₹5,000.00 resulting in ₹61,200.00."
    is_valid, unauth = validate_numeric_consistency(valid_text, allowed_amounts)
    assert is_valid is True
    assert len(unauth) == 0

    # Hallucinated number (e.g. ₹42,500.00)
    invalid_text = "Your expected settlement will be ₹42,500.00 based on policy."
    is_valid, unauth = validate_numeric_consistency(invalid_text, allowed_amounts)
    assert is_valid is False
    assert "₹42,500.00" in unauth
