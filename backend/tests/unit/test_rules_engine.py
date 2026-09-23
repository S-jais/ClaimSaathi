"""
tests/unit/test_rules_engine.py
Unit tests for the Claim Readiness rules engine.
No LLM calls, no network, no DB — deterministic logic only.
Tests cover all 6 requirement types, all consistency flags, and edge cases.
"""
from __future__ import annotations

from decimal import Decimal
from datetime import date

import pytest

from app.claims.readiness.rules_engine import ClaimReadinessRulesEngine, ReadinessResult


def make_doc(doc_type: str, status: str = "completed", doc_id: str | None = None) -> dict:
    return {"id": doc_id or f"uuid-{doc_type}", "doc_type": doc_type, "status": status}


@pytest.fixture
def engine() -> ClaimReadinessRulesEngine:
    return ClaimReadinessRulesEngine()


class TestReimbursementRequirements:
    def test_no_documents_all_mandatory_missing(self, engine):
        result = engine.evaluate(
            claim_id="claim-1",
            claim_type="reimbursement",
            claim_amount=None,
            sum_insured=None,
            patient_name=None,
            policyholder_name=None,
            admission_date=None,
            discharge_date=None,
            uploaded_documents=[],
        )
        assert result.is_ready is False
        assert result.score == 0
        assert "policy" in result.missing_mandatory
        assert "hospital_bill" in result.missing_mandatory
        assert "discharge_summary" in result.missing_mandatory
        assert "claim_form" in result.missing_mandatory

    def test_all_mandatory_documents_complete_is_ready(self, engine):
        docs = [
            make_doc("policy"),
            make_doc("claim_form"),
            make_doc("hospital_bill"),
            make_doc("discharge_summary"),
        ]
        result = engine.evaluate(
            claim_id="claim-2",
            claim_type="reimbursement",
            claim_amount=Decimal("50000"),
            sum_insured=Decimal("500000"),
            patient_name="Siddhartha Jaiswal",
            policyholder_name="Siddhartha Jaiswal",
            admission_date=date(2026, 1, 10),
            discharge_date=date(2026, 1, 13),
            uploaded_documents=docs,
        )
        assert result.is_ready is True
        assert result.score == 100
        assert result.missing_mandatory == []
        assert result.flags == []

    def test_consultation_notes_missing_not_blocking(self, engine):
        """consultation_notes is not mandatory — missing it should not block readiness."""
        docs = [
            make_doc("policy"),
            make_doc("claim_form"),
            make_doc("hospital_bill"),
            make_doc("discharge_summary"),
        ]
        result = engine.evaluate(
            claim_id="claim-3",
            claim_type="reimbursement",
            claim_amount=None, sum_insured=None,
            patient_name=None, policyholder_name=None,
            admission_date=None, discharge_date=None,
            uploaded_documents=docs,
        )
        assert result.is_ready is True
        assert "consultation_notes" not in result.missing_mandatory

    def test_processing_document_not_counted(self, engine):
        """Documents in 'processing' status do not satisfy requirements."""
        docs = [
            make_doc("policy", status="processing"),
            make_doc("claim_form"),
            make_doc("hospital_bill"),
            make_doc("discharge_summary"),
        ]
        result = engine.evaluate(
            claim_id="claim-4", claim_type="reimbursement",
            claim_amount=None, sum_insured=None,
            patient_name=None, policyholder_name=None,
            admission_date=None, discharge_date=None,
            uploaded_documents=docs,
        )
        assert "policy" in result.missing_mandatory

    def test_score_partial(self, engine):
        """2 of 4 mandatory docs uploaded -> 50%"""
        docs = [make_doc("policy"), make_doc("hospital_bill")]
        result = engine.evaluate(
            claim_id="claim-5", claim_type="reimbursement",
            claim_amount=None, sum_insured=None,
            patient_name=None, policyholder_name=None,
            admission_date=None, discharge_date=None,
            uploaded_documents=docs,
        )
        assert result.score == 50


class TestConsistencyFlags:
    def test_amount_exceeds_sum_insured_flagged(self, engine):
        docs = [make_doc("policy"), make_doc("claim_form"), make_doc("hospital_bill"), make_doc("discharge_summary")]
        result = engine.evaluate(
            claim_id="claim-6", claim_type="reimbursement",
            claim_amount=Decimal("600000"),
            sum_insured=Decimal("500000"),
            patient_name=None, policyholder_name=None,
            admission_date=None, discharge_date=None,
            uploaded_documents=docs,
        )
        assert any("sum insured" in f.lower() for f in result.flags)
        # Even though all docs present, flags make is_ready False
        assert result.is_ready is False

    def test_name_mismatch_flagged(self, engine):
        docs = [make_doc("policy"), make_doc("claim_form"), make_doc("hospital_bill"), make_doc("discharge_summary")]
        result = engine.evaluate(
            claim_id="claim-7", claim_type="reimbursement",
            claim_amount=None, sum_insured=None,
            patient_name="Suresh Patel",
            policyholder_name="Siddhartha Jaiswal",
            admission_date=None, discharge_date=None,
            uploaded_documents=docs,
        )
        assert any("name" in f.lower() for f in result.flags)

    def test_name_match_no_flag(self, engine):
        docs = [make_doc("policy"), make_doc("claim_form"), make_doc("hospital_bill"), make_doc("discharge_summary")]
        result = engine.evaluate(
            claim_id="claim-8", claim_type="reimbursement",
            claim_amount=None, sum_insured=None,
            patient_name="Siddhartha Jaiswal",
            policyholder_name="Siddhartha Jaiswal",
            admission_date=None, discharge_date=None,
            uploaded_documents=docs,
        )
        assert not any("name" in f.lower() for f in result.flags)

    def test_same_day_admission_discharge_flagged(self, engine):
        docs = [make_doc("policy"), make_doc("claim_form"), make_doc("hospital_bill"), make_doc("discharge_summary")]
        result = engine.evaluate(
            claim_id="claim-9", claim_type="reimbursement",
            claim_amount=None, sum_insured=None,
            patient_name=None, policyholder_name=None,
            admission_date=date(2026, 1, 10),
            discharge_date=date(2026, 1, 10),
            uploaded_documents=docs,
        )
        assert any("24 hours" in f or "same day" in f.lower() for f in result.flags)

    def test_discharge_before_admission_flagged(self, engine):
        docs = [make_doc("policy"), make_doc("claim_form"), make_doc("hospital_bill"), make_doc("discharge_summary")]
        result = engine.evaluate(
            claim_id="claim-10", claim_type="reimbursement",
            claim_amount=None, sum_insured=None,
            patient_name=None, policyholder_name=None,
            admission_date=date(2026, 1, 15),
            discharge_date=date(2026, 1, 10),
            uploaded_documents=docs,
        )
        assert any("discharge" in f.lower() and "before" in f.lower() for f in result.flags)


class TestDemoScenario:
    """Tests the exact seeded demo scenario from scripts/seed_demo_data.py."""

    def test_demo_claim_missing_consultation_notes(self, engine):
        """
        Demo: Siddhartha Jaiswal, CLM-20491
        Missing: consultation_notes (deliberately absent)
        Present: policy, hospital_bill, discharge_summary, prescription
        """
        docs = [
            make_doc("policy"),
            make_doc("hospital_bill"),
            make_doc("discharge_summary"),
            make_doc("prescription"),
            # consultation_notes deliberately missing
            make_doc("claim_form"),
        ]
        result = engine.evaluate(
            claim_id="CLM-20491",
            claim_type="reimbursement",
            claim_amount=Decimal("184500"),
            sum_insured=Decimal("500000"),
            patient_name="Siddhartha Jaiswal",
            policyholder_name="Siddhartha Jaiswal",
            admission_date=date(2026, 1, 10),
            discharge_date=date(2026, 1, 14),
            uploaded_documents=docs,
        )
        # All mandatory docs present
        assert "policy" not in result.missing_mandatory
        assert "hospital_bill" not in result.missing_mandatory
        assert "discharge_summary" not in result.missing_mandatory
        assert "claim_form" not in result.missing_mandatory
        # consultation_notes not mandatory — should be ready
        assert result.is_ready is True

        # But consultation_notes should show as non-mandatory gap
        consultation_req = next(
            (r for r in result.requirements if r.requirement_type == "consultation_notes"), None
        )
        assert consultation_req is not None
        assert consultation_req.is_satisfied is False
        assert consultation_req.is_mandatory is False
