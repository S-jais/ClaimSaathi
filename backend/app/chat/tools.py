"""
backend/app/chat/tools.py
Deterministic Grounding Tools and Numeric Consistency Validator for ClaimSaathi Chatbot.

Provides tools that query:
1. Document findings (status, missing, needs_fix, cross-doc checks)
2. Reimbursement breakdown (gross billed, non-payables, room rent, co-pay, indicative payable)
3. Line item explanations (IRDAI rules, explanations, patient remedies)
4. Comparison of indicative payable estimate to rejection letter grounds

Also includes validate_numeric_consistency() to prevent LLM hallucinations on amounts.
"""
from __future__ import annotations

import re
from typing import Any
from app.claims.audit.engine import BillAuditEngine
from app.claims.readiness.verifier import ClaimReadinessVerifier

engine = BillAuditEngine()
verifier = ClaimReadinessVerifier()

# Matches amounts like ₹1,84,500 or Rs. 5,000 or INR 61,200
CURRENCY_REGEX = re.compile(r"(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)


def get_reimbursement_breakdown(claim_id: str, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Returns deterministic audit waterfall and calculations for the claim."""
    report = engine.audit_bill(raw_items=items or [])
    return {
        "claim_id": claim_id,
        "gross_billed": f"₹{report.gross_billed_paise / 100:,.2f}",
        "gross_billed_paise": report.gross_billed_paise,
        "commonly_non_payable": f"₹{report.commonly_non_payable_paise / 100:,.2f}",
        "commonly_non_payable_paise": report.commonly_non_payable_paise,
        "needs_review": f"₹{report.needs_review_paise / 100:,.2f}",
        "needs_review_paise": report.needs_review_paise,
        "room_rent_deduction": f"₹{report.room_rent_deduction_paise / 100:,.2f}",
        "room_rent_status": report.room_rent_status,
        "copay_deduction": f"₹{report.copay_deduction_paise / 100:,.2f}",
        "copay_status": report.copay_status,
        "indicative_payable_estimate": f"₹{report.indicative_payable_paise / 100:,.2f}",
        "indicative_payable_paise": report.indicative_payable_paise,
        "estimate_label": report.estimate_label,
        "item_count": len(report.items),
    }


def explain_line_item(description: str) -> dict[str, Any]:
    """Classifies a line item and returns the IRDAI rule explanation and remedy."""
    item = engine.classify_item(description, 10000)
    return {
        "description": item.description,
        "classification": item.classification,
        "category": item.category,
        "rule_id": item.rule_id,
        "guideline_reference": item.guideline_reference,
        "explanation": item.explanation,
        "patient_remedy": item.patient_remedy,
    }


def get_document_findings(claim_id: str, docs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Returns document readiness gate status, missing mandatory files, and quality flags."""
    rep = verifier.verify(
        claim_id=claim_id,
        claim_type="reimbursement",
        patient_name=None,
        admission_date=None,
        discharge_date=None,
        claim_amount_paise=None,
        documents=docs or [],
    )
    return {
        "claim_id": claim_id,
        "score": rep.score,
        "is_ready": rep.is_ready,
        "missing_mandatory": rep.missing_mandatory,
        "needs_fix_mandatory": rep.needs_fix_mandatory,
        "flags": rep.consistency_flags,
    }


def validate_numeric_consistency(
    answer: str,
    allowed_amounts_paise: set[int] | None = None,
) -> tuple[bool, list[str]]:
    """
    Checks all currency amounts mentioned in the chatbot's answer.
    If an amount is found that deviates completely from the allowed engine amounts,
    returns False along with detected discrepancies.
    """
    if not allowed_amounts_paise:
        return True, []

    matches = CURRENCY_REGEX.findall(answer)
    unauthorized_amounts = []

    for m in matches:
        clean_num = m.replace(",", "")
        try:
            val_float = float(clean_num)
            val_paise = round(val_float * 100)

            # Check if this exact amount or rounded value is allowed
            matched = False
            for allowed in allowed_amounts_paise:
                if abs(val_paise - allowed) <= 100:  # within 1 rupee tolerance for rounding
                    matched = True
                    break

            if not matched:
                unauthorized_amounts.append(f"₹{val_float:,.2f}")
        except ValueError:
            continue

    is_consistent = len(unauthorized_amounts) == 0
    return is_consistent, unauthorized_amounts
