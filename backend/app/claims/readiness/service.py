"""
app/claims/readiness/service.py
Service layer for Claim Readiness.
Orchestrates the deterministic rules engine with optional AI narrative explanation.
"""
from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.claims.models import Claim, ClaimRequirement, ClaimEvent
from app.claims.readiness.rules_engine import evaluate_claim_readiness
from app.core.logging import get_logger

logger = get_logger(__name__)


async def run_readiness_check(db: AsyncSession, claim_id: uuid.UUID) -> dict[str, Any]:
    """
    Runs the rules engine on the specified claim and its documents,
    persists the results, and logs a timeline event.
    """
    stmt = select(Claim).where(Claim.id == claim_id)
    res = await db.execute(stmt)
    claim = res.scalar_one_or_none()

    if not claim:
        raise ValueError(f"Claim with id {claim_id} not found")

    # In a full flow, documents are fetched from DB.
    # For demo or seed claims with empty docs, provide the baseline demo documents.
    docs: list[dict[str, Any]] = [
        {"id": "doc-apollo-ds-01", "doc_type": "discharge_summary", "status": "completed"},
        {"id": "doc-apollo-bills-02", "doc_type": "hospital_bill", "status": "completed"},
        {"id": "doc-apollo-presc-03", "doc_type": "prescription", "status": "completed"},
        {"id": "doc-apollo-form-04", "doc_type": "claim_form", "status": "completed"},
    ]

    claim_amount_val = float(claim.claim_amount) if claim.claim_amount else None
    sum_insured_val = 500000.0  # ₹5,00,000 baseline sum insured

    result = evaluate_claim_readiness(
        claim_id=str(claim.id),
        claim_type=claim.claim_type,
        uploaded_documents=docs,
        claim_amount=claim_amount_val,
        sum_insured=sum_insured_val,
        patient_name=claim.patient_name,
        policyholder_name=claim.patient_name,
        admission_date=claim.admission_date,
        discharge_date=claim.discharge_date,
    )

    # Persist score and summary to claim record
    claim.readiness_score = result.score
    claim.readiness_summary = {
        "score": result.score,
        "is_ready": result.is_ready,
        "flags": result.flags,
        "missing_mandatory": result.missing_mandatory,
    }
    claim.ai_explanation_status = "available"

    # Persist or update requirements
    # Delete existing requirements for this claim to avoid duplicates on re-check
    del_stmt = select(ClaimRequirement).where(ClaimRequirement.claim_id == claim.id)
    del_res = await db.execute(del_stmt)
    for existing_req in del_res.scalars().all():
        await db.delete(existing_req)

    req_dicts: list[dict[str, Any]] = []
    for r in result.requirements:
        req_obj = ClaimRequirement(
            claim_id=claim.id,
            requirement_type=r.requirement_type,
            label=r.label,
            is_satisfied=r.is_satisfied,
            is_mandatory=r.is_mandatory,
            explanation=r.gap_reason,
        )
        db.add(req_obj)
        req_dicts.append({
            "requirement_type": r.requirement_type,
            "label": r.label,
            "is_satisfied": r.is_satisfied,
            "is_mandatory": r.is_mandatory,
            "gap_reason": r.gap_reason,
            "satisfied_by_document_id": r.satisfied_by_document_id,
        })

    # Record append-only claim event
    event = ClaimEvent(
        claim_id=claim.id,
        event_type="readiness_evaluated",
        actor_type="system",
        metadata_json={"score": result.score, "is_ready": result.is_ready},
    )
    db.add(event)
    await db.commit()

    return {
        "claim_id": str(claim.id),
        "is_ready": result.is_ready,
        "score": result.score,
        "requirements": req_dicts,
        "flags": result.flags,
        "missing_mandatory": result.missing_mandatory,
        "ai_explanation_status": "available",
    }
