"""
backend/tests/unit/test_bill_audit.py
Unit tests for the IRDAI Bill Audit Engine.
Validates classifications, integer paise calculations, waterfall invariants, and regulatory labeling.
"""
import pytest
from app.claims.audit.engine import (
    BillAuditEngine,
    MANDATORY_ESTIMATE_LABEL,
)


@pytest.fixture
def audit_engine():
    return BillAuditEngine()


def test_classify_irdai_non_payable_items(audit_engine):
    # Gloves
    item_gloves = audit_engine.classify_item("Nitrile Examination Gloves (5 pairs)", 45000)
    assert item_gloves.classification == "COMMONLY_NON_PAYABLE"
    assert item_gloves.rule_id == "IRDAI-NP-001"
    assert "Gloves" in item_gloves.guideline_reference
    assert item_gloves.patient_remedy is not None

    # PPE Kit
    item_ppe = audit_engine.classify_item("COVID PPE Kit + Face Mask", 120000)
    assert item_ppe.classification == "COMMONLY_NON_PAYABLE"
    assert item_ppe.rule_id == "IRDAI-NP-002"

    # Registration Fee
    item_reg = audit_engine.classify_item("Patient Registration & MRD File Fee", 50000)
    assert item_reg.classification == "COMMONLY_NON_PAYABLE"
    assert item_reg.rule_id == "IRDAI-NP-004"

    # Biomedical waste
    item_bmw = audit_engine.classify_item("Hospital Bio-Medical Waste Surcharge", 75000)
    assert item_bmw.classification == "COMMONLY_NON_PAYABLE"
    assert item_bmw.rule_id == "IRDAI-NP-005"


def test_classify_ambiguous_review_items(audit_engine):
    # Miscellaneous charges
    item_misc = audit_engine.classify_item("Miscellaneous Ward Charges", 350000)
    assert item_misc.classification == "NEEDS_REVIEW"
    assert "breakdown" in item_misc.explanation.lower()

    # Sundry
    item_sundry = audit_engine.classify_item("Sundry overhead expenses", 100000)
    assert item_sundry.classification == "NEEDS_REVIEW"

    # Zero or negative amount
    item_zero = audit_engine.classify_item("Doctor Round", 0)
    assert item_zero.classification == "NEEDS_REVIEW"


def test_classify_standard_payable_medical(audit_engine):
    item_surg = audit_engine.classify_item("Laparoscopic Cholecystectomy Surgeon Fee", 4500000)
    assert item_surg.classification == "PAYABLE_MEDICAL"

    item_icu = audit_engine.classify_item("ICU Monitoring & Nursing Tariff", 2500000)
    assert item_icu.classification == "PAYABLE_MEDICAL"

    item_med = audit_engine.classify_item("Inj. Ceftriaxone 1g IV", 85000)
    assert item_med.classification == "PAYABLE_MEDICAL"


def test_waterfall_calculation_and_invariants(audit_engine):
    sample_bill_items = [
        {"description": "OT Surgeon Fee", "amount": 50000.0},          # 50,00,000 paise
        {"description": "Anesthetist Charges", "amount": 15000.0},     # 15,00,000 paise
        {"description": "Surgical Gloves", "amount": 1200.0},          # 1,20,000 paise (non-payable)
        {"description": "PPE Kits", "amount": 2500.0},                 # 2,50,000 paise (non-payable)
        {"description": "Registration Fee", "amount": 500.0},          # 50,000 paise (non-payable)
        {"description": "Hospital Bio-Medical Waste", "amount": 800.0},# 80,000 paise (non-payable)
        {"description": "Miscellaneous Admin Charges", "amount": 3000.0},# 3,00,000 paise (needs review)
    ]

    report = audit_engine.audit_bill(
        raw_items=sample_bill_items,
        sum_insured_paise=10000000,   # 1 Lakh SI (1,00,00,000 paise)
        copay_percentage=10,          # 10% co-pay
    )

    # 1. Verification of label
    assert report.estimate_label == MANDATORY_ESTIMATE_LABEL
    assert "Expected Settlement" not in report.estimate_label

    # 2. Integer paise integrity
    assert isinstance(report.gross_billed_paise, int)
    assert isinstance(report.indicative_payable_paise, int)
    assert isinstance(report.commonly_non_payable_paise, int)
    assert report.gross_billed_paise == 7300000  # ₹73,000.00 = 73,00,000 paise

    # 3. Non-payable sum = 1200 + 2500 + 500 + 800 = ₹5,000.00 = 5,00,000 paise
    assert report.commonly_non_payable_paise == 500000

    # 4. Needs review = 3000 = ₹3,000.00 = 3,00,000 paise
    assert report.needs_review_paise == 300000

    # 5. After non-payables: 73,00,000 - 5,00,000 = 68,00,000 paise
    # 10% copay on 68,00,000 = 6,80,000 paise
    assert report.copay_deduction_paise == 680000
    assert report.copay_status == "APPLIED"

    # 6. Indicative payable = 68,00,000 - 6,80,000 = 61,20,000 paise (₹61,200.00)
    assert report.indicative_payable_paise == 6120000

    # 7. Waterfall checks
    waterfall_keys = [step.step_key for step in report.waterfall]
    assert "gross_billed" in waterfall_keys
    assert "non_payable_deductions" in waterfall_keys
    assert "copay_deduction" in waterfall_keys
    assert "indicative_payable_estimate" in waterfall_keys
