"""
app/claims/readiness/rules_engine.py
Deterministic Python rules engine for Claim Readiness.
This module is the SOLE authority on what documents/fields are required.
The LLM is NEVER consulted here — it only narrates the output (in readiness/service.py).
Every rule is independently testable with no LLM dependency.

Rules reflect common requirements for health insurance reimbursement claims in India.
Review against the specific insurer's policy terms before production deployment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------
@dataclass
class RequirementResult:
    """Result for a single claim requirement."""
    requirement_type: str
    label: str
    is_mandatory: bool
    is_satisfied: bool
    satisfied_by_document_id: str | None
    gap_reason: str | None  # Human-readable gap description (for LLM to narrate)


@dataclass
class ReadinessResult:
    """Full output of the rules engine for a claim."""
    claim_id: str
    is_ready: bool                          # True only if ALL mandatory requirements are satisfied
    score: int                              # 0–100: percentage of mandatory requirements satisfied
    requirements: list[RequirementResult]   # One entry per requirement
    flags: list[str]                        # Non-requirement issues (e.g., amount > sum insured)
    missing_mandatory: list[str]            # Convenience: list of unsatisfied mandatory req types


# ---------------------------------------------------------------------------
# Document type registry
# ---------------------------------------------------------------------------
# Maps doc_type values (stored in documents.doc_type) to requirement_types
DOC_TYPE_MAP: dict[str, str] = {
    "policy": "policy",
    "hospital_bill": "hospital_bill",
    "discharge_summary": "discharge_summary",
    "prescription": "prescription",
    "consultation_notes": "consultation_notes",
    "claim_form": "claim_form",
    "rejection_letter": "rejection_letter",
    "other": "other",
}

# ---------------------------------------------------------------------------
# Requirement definitions per claim type
# ---------------------------------------------------------------------------
REIMBURSEMENT_REQUIREMENTS: list[dict[str, Any]] = [
    {
        "requirement_type": "policy",
        "label": "Insurance Policy Document",
        "is_mandatory": True,
        "gap_reason": "Your insurance policy document is required to verify coverage terms and the applicable clauses for this claim.",
    },
    {
        "requirement_type": "claim_form",
        "label": "Completed Claim Form",
        "is_mandatory": True,
        "gap_reason": "A completed claim form signed by the treating doctor is required by most insurers for reimbursement processing.",
    },
    {
        "requirement_type": "hospital_bill",
        "label": "Hospital Bill / Invoice",
        "is_mandatory": True,
        "gap_reason": "The itemised hospital bill with amounts, patient name, and hospital registration number is required to verify the claimed amount.",
    },
    {
        "requirement_type": "discharge_summary",
        "label": "Discharge Summary",
        "is_mandatory": True,
        "gap_reason": "The discharge summary from the treating hospital is required to confirm the admission period, diagnosis, and treating doctor.",
    },
    {
        "requirement_type": "prescription",
        "label": "Doctor's Prescription",
        "is_mandatory": False,  # Mandatory for medicine claims; optional for procedure-only
        "gap_reason": "A prescription from the treating doctor helps support the medical necessity of the treatment.",
    },
    {
        "requirement_type": "consultation_notes",
        "label": "Consultation / OPD Notes",
        "is_mandatory": False,  # Commonly requested by TPAs — not always mandatory at submission
        "gap_reason": "Consultation notes provide evidence of the medical journey prior to hospitalization and are often requested to verify medical necessity.",
    },
]

CASHLESS_REQUIREMENTS: list[dict[str, Any]] = [
    {
        "requirement_type": "policy",
        "label": "Insurance Policy / Health Card",
        "is_mandatory": True,
        "gap_reason": "Your insurance policy or health card number is required to initiate a cashless authorization request.",
    },
    {
        "requirement_type": "hospital_bill",
        "label": "Pre-authorization Form / Estimated Bill",
        "is_mandatory": True,
        "gap_reason": "The hospital's estimated cost and pre-authorization form must be submitted for cashless authorization.",
    },
]


# ---------------------------------------------------------------------------
# Rules engine
# ---------------------------------------------------------------------------
class ClaimReadinessRulesEngine:
    """
    Deterministic rules engine for claim readiness.
    Takes structured claim + document inventory data; returns ReadinessResult.
    No LLM calls, no network calls — pure Python logic, fully unit-testable.
    """

    def evaluate(
        self,
        claim_id: str,
        claim_type: str,
        claim_amount: Decimal | None,
        sum_insured: Decimal | None,
        patient_name: str | None,
        policyholder_name: str | None,
        admission_date: Any | None,
        discharge_date: Any | None,
        uploaded_documents: list[dict[str, Any]],  # list of documents rows (doc_type, status, id)
    ) -> ReadinessResult:
        """
        Evaluate claim readiness.

        uploaded_documents: list of dicts with keys:
            - id: str
            - doc_type: str
            - status: str (completed | processing | queued | failed)
        """
        # Select requirement set by claim type
        if claim_type == "cashless":
            requirements_def = CASHLESS_REQUIREMENTS
        else:
            requirements_def = REIMBURSEMENT_REQUIREMENTS  # default: reimbursement

        # Index completed documents by type
        completed_docs: dict[str, str] = {}  # doc_type -> document_id
        for doc in uploaded_documents:
            if doc.get("status") == "completed":
                completed_docs[doc["doc_type"]] = doc["id"]

        # Evaluate each requirement
        results: list[RequirementResult] = []
        for req in requirements_def:
            req_type = req["requirement_type"]
            satisfying_doc_id = completed_docs.get(req_type)
            results.append(RequirementResult(
                requirement_type=req_type,
                label=req["label"],
                is_mandatory=req["is_mandatory"],
                is_satisfied=satisfying_doc_id is not None,
                satisfied_by_document_id=satisfying_doc_id,
                gap_reason=req["gap_reason"] if satisfying_doc_id is None else None,
            ))

        # Compute score (mandatory requirements only)
        mandatory = [r for r in results if r.is_mandatory]
        satisfied_mandatory = [r for r in mandatory if r.is_satisfied]
        score = int((len(satisfied_mandatory) / len(mandatory)) * 100) if mandatory else 100

        # Flags: non-requirement consistency checks
        flags: list[str] = []

        # Flag: claim amount exceeds sum insured
        if claim_amount and sum_insured and claim_amount > sum_insured:
            flags.append(
                f"Claimed amount (₹{claim_amount:,.2f}) exceeds your policy's sum insured "
                f"(₹{sum_insured:,.2f}). The excess amount is unlikely to be reimbursed."
            )

        # Flag: patient name mismatch (if both available)
        if (
            patient_name
            and policyholder_name
            and patient_name.strip().lower() != policyholder_name.strip().lower()
        ):
            flags.append(
                f"Patient name on documents ('{patient_name}') may not match the "
                f"policyholder name ('{policyholder_name}'). Insurers commonly flag this. "
                "Confirm if the patient is covered as a family member under a floater policy."
            )

        # Flag: discharge before admission
        if admission_date and discharge_date and discharge_date < admission_date:
            flags.append(
                "Discharge date appears to be before admission date. "
                "Please verify the dates on your discharge summary."
            )

        # Flag: same-day admission/discharge (less than 24 hours) — common rejection trigger
        if admission_date and discharge_date and admission_date == discharge_date:
            flags.append(
                "Admission and discharge appear to be on the same day. "
                "Most policies require hospitalization of at least 24 hours for reimbursement. "
                "Verify the hours of admission and discharge."
            )

        missing_mandatory = [r.requirement_type for r in mandatory if not r.is_satisfied]
        is_ready = score == 100 and len(flags) == 0

        return ReadinessResult(
            claim_id=claim_id,
            is_ready=is_ready,
            score=score,
            requirements=results,
            flags=flags,
            missing_mandatory=missing_mandatory,
        )


def evaluate_claim_readiness(
    claim_id: str,
    claim_type: str,
    uploaded_documents: list[dict[str, Any]],
    claim_amount: Any = None,
    sum_insured: Any = None,
    patient_name: str | None = None,
    policyholder_name: str | None = None,
    admission_date: Any = None,
    discharge_date: Any = None,
) -> ReadinessResult:
    """Convenience helper to evaluate claim readiness with default engine."""
    engine = ClaimReadinessRulesEngine()
    return engine.evaluate(
        claim_id=claim_id,
        claim_type=claim_type,
        uploaded_documents=uploaded_documents,
        claim_amount=claim_amount,
        sum_insured=sum_insured,
        patient_name=patient_name,
        policyholder_name=policyholder_name,
        admission_date=admission_date,
        discharge_date=discharge_date,
    )

