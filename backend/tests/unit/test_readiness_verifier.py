"""
backend/tests/unit/test_readiness_verifier.py
Unit tests for cross-document consistency verification and readiness scoring.
"""
from app.claims.readiness.verifier import ClaimReadinessVerifier, fuzzy_name_match


def test_fuzzy_name_matching():
    assert fuzzy_name_match("Rahul Sharma", "Mr. Rahul Sharma") is True
    assert fuzzy_name_match("Dr. Ananya Verma", "Ananya Verma") is True
    assert fuzzy_name_match("Siddhartha Jaiswal", "Siddhartha") is True
    assert fuzzy_name_match("Vikram Singh", "Pooja Malhotra") is False


def test_readiness_all_missing():
    verifier = ClaimReadinessVerifier()
    report = verifier.verify(
        claim_id="clm-101",
        claim_type="reimbursement",
        patient_name="Siddhartha Jaiswal",
        admission_date="2026-03-01",
        discharge_date="2026-03-05",
        claim_amount_paise=15000000,
        documents=[],
    )

    assert report.is_ready is False
    assert report.score == 0
    assert "policy" in report.missing_mandatory
    assert "hospital_bill" in report.missing_mandatory
    assert "discharge_summary" in report.missing_mandatory
    assert "claim_form" in report.missing_mandatory


def test_readiness_needs_fix_when_stamp_missing():
    verifier = ClaimReadinessVerifier()
    docs = [
        {
            "id": "doc-1",
            "doc_type": "policy",
            "original_filename": "policy.pdf",
            "extraction": {"extracted_json": {"patient_name": "Siddhartha Jaiswal"}},
        },
        {
            "id": "doc-2",
            "doc_type": "hospital_bill",
            "original_filename": "bill.csv",
            "extraction": {"extracted_json": {"totals": {"total_amount_paise": 5000000}, "line_items": [{"description": "Bed", "amount_paise": 5000000}]}},
        },
        {
            "id": "doc-3",
            "doc_type": "discharge_summary",
            "original_filename": "discharge.pdf",
            "extraction": {
                "extracted_json": {
                    "patient_name": "Siddhartha Jaiswal",
                    "document_quality": {"has_stamp": False, "has_signature": True, "is_legible": True},
                }
            },
        },
        {
            "id": "doc-4",
            "doc_type": "claim_form",
            "original_filename": "form.pdf",
            "extraction": {"extracted_json": {"patient_name": "Siddhartha Jaiswal"}},
        },
    ]

    report = verifier.verify(
        claim_id="clm-102",
        claim_type="reimbursement",
        patient_name="Siddhartha Jaiswal",
        admission_date="2026-03-01",
        discharge_date="2026-03-05",
        claim_amount_paise=5000000,
        documents=docs,
    )

    assert report.is_ready is False
    assert "discharge_summary" in report.needs_fix_mandatory
    ds_req = next(r for r in report.requirements if r.requirement_type == "discharge_summary")
    assert ds_req.status == "NEEDS_FIX"
    assert any("stamp" in issue.lower() for issue in ds_req.issues)


def test_readiness_100_percent_when_all_verified():
    verifier = ClaimReadinessVerifier()
    docs = [
        {
            "id": "doc-1",
            "doc_type": "policy",
            "original_filename": "policy.pdf",
            "extraction": {"extracted_json": {"patient_name": "Siddhartha Jaiswal"}},
        },
        {
            "id": "doc-2",
            "doc_type": "hospital_bill",
            "original_filename": "bill.csv",
            "extraction": {"extracted_json": {"totals": {"total_amount_paise": 5000000}, "line_items": [{"description": "Surgery", "amount_paise": 5000000}]}},
        },
        {
            "id": "doc-3",
            "doc_type": "discharge_summary",
            "original_filename": "discharge.pdf",
            "extraction": {
                "extracted_json": {
                    "patient_name": "Siddhartha Jaiswal",
                    "document_quality": {"has_stamp": True, "has_signature": True, "is_legible": True},
                }
            },
        },
        {
            "id": "doc-4",
            "doc_type": "claim_form",
            "original_filename": "form.pdf",
            "extraction": {"extracted_json": {"patient_name": "Siddhartha Jaiswal"}},
        },
    ]

    report = verifier.verify(
        claim_id="clm-103",
        claim_type="reimbursement",
        patient_name="Siddhartha Jaiswal",
        admission_date="2026-03-01",
        discharge_date="2026-03-05",
        claim_amount_paise=5000000,
        documents=docs,
    )

    assert report.is_ready is True
    assert report.score == 100
    assert len(report.missing_mandatory) == 0
    assert len(report.needs_fix_mandatory) == 0
