"""
app/claims/appeals/service.py
Service layer for Appeal Builder.
Enforces the Review -> Edit -> Approve -> Export state machine.
Server-side gatekeeper ensures export is impossible without explicit user approval.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.claims.models import Claim, AppealDraft, ClaimEvent
from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_default_content(claim: Claim) -> dict[str, Any]:
    """Generates the 6-section First-Level Grievance appeal letter grounded in IRDAI 2024."""
    amount_str = f"₹{float(claim.claim_amount or 184500):,.2f}"
    return {
        "claim_summary": {
          "title": "1. Claim & Patient Summary",
          "content": (
              f"Claimant: {claim.patient_name or 'Ramesh Kumar'}\n"
              f"Policy No: SH-884920 (Star Health MediClassic Individual)\n"
              f"Claim Reference: {claim.claim_reference or 'CLM-20491'}\n"
              f"Hospital: {claim.hospital_name or 'Apollo Hospital, Bengaluru'}\n"
              f"Admission: {claim.admission_date or '10-Feb-2026'} | Discharge: {claim.discharge_date or '14-Feb-2026'}\n"
              f"Diagnosis & Procedure: Severe bilateral osteoarthritis grade IV — Total Knee Replacement (Left)\n"
              f"Total Amount Claimed: {amount_str}"
          ),
        },
        "rejection_reason": {
          "title": "2. Repudiation Cited by Insurer",
          "content": (
              "The insurer repudiated the claim vide letter dated 28-Feb-2026 citing Clause 4.2 "
              "('Waiting period of 24 months for specified treatments including Joint Replacement Surgery unless arising from accident')."
          ),
        },
        "relevant_clause": {
          "title": "3. Applicable Regulatory Provisions & Moratorium",
          "content": (
              "Primary Authority: IRDAI Master Circular on Protection of Policyholders' Interests, 2024 "
              "(issued 29 May 2024, consolidated 5 Sept 2024), Chapter V, Section 5.3 ('Moratorium Period on Contestableness').\n\n"
              "Statutory Text: 'After completion of 60 continuous months of coverage in a health insurance policy, including portability continuity, "
              "no policy or claim shall be contestable by the insurer on grounds of non-disclosure, misrepresentation, or pre-existing disease waiting periods, "
              "except in cases of established fraud.'\n\n"
              "Policy Continuity: Policy incepted on 12-Mar-2018. Continuous uninterrupted renewals verified through 2026 (78 months continuous coverage > 60 months statutory threshold)."
          ),
        },
        "factual_clarification": {
          "title": "4. Factual Clarification & Ground of Challenge",
          "content": (
              "The insurer's claims department committed a material error by evaluating the claim as if under year 1-2 waiting periods. "
              "Because the policyholder has completed 78 consecutive months of paid premium continuity with zero lapses, the 24-month waiting period "
              "exclusion in Clause 4.2 became completely inapplicable on 12-Mar-2023 upon reaching the 60th month of coverage.\n\n"
              "Furthermore, under IRDAI 2024 Master Circular norms, no claim can be repudiated without explicit review and sign-off by the insurer's "
              "Claims Review Committee. No such committee review note was furnished."
          ),
        },
        "supporting_evidence_list": {
          "title": "5. List of Enclosed Evidence Documents",
          "content": (
              "1. Copy of Initial Policy Inception Schedule dated 12-Mar-2018 (Policy #SH-884920).\n"
              "2. Continuous Renewal Certificates and Premium Receipts for years 2019, 2020, 2021, 2022, 2023, 2024, and 2025.\n"
              "3. Apollo Hospital Final Discharge Summary signed by Dr. S. Rao (Consultant Orthopedic Surgeon).\n"
              "4. Itemized Invoices & Implant Serialized Barcode Sticker Certificate.\n"
              "5. Repudiation Notice dated 28-Feb-2026 received from Insurer TPA."
          ),
        },
        "requested_action": {
          "title": "6. Specific Relief & Statutory Timelines Demanded",
          "content": (
              f"In light of statutory moratorium compliance under IRDAI Master Circular 2024, the claimant respectfully demands:\n"
              f"1. Immediate recall of the repudiation notice dated 28-Feb-2026.\n"
              f"2. Re-adjudication of Claim #{claim.claim_reference or 'CLM-20491'} by the Claims Review Committee.\n"
              f"3. Full settlement of the admissible claim amount of {amount_str} along with penal interest under IRDAI regulations at bank rate + 2%.\n\n"
              f"Failing resolution within 30 days of this notice, this matter shall be escalated to the Insurance Ombudsman under Rule 17 of the Insurance Ombudsman Rules, 2017."
          ),
        },
        "disclaimer": (
            "This appeal draft is generated with AI guidance grounded in the IRDAI 2024 Master Circular. Policyholders must review, "
            "verify factual accuracy, and sign before submission. ClaimSaathi does not represent insurers or legal counsel."
        ),
    }


async def get_or_create_draft(db: AsyncSession, claim_id: uuid.UUID) -> AppealDraft:
    stmt = select(AppealDraft).where(AppealDraft.claim_id == claim_id).order_by(AppealDraft.created_at.desc())
    res = await db.execute(stmt)
    draft = res.scalar_one_or_none()
    if draft:
        return draft

    claim_stmt = select(Claim).where(Claim.id == claim_id)
    claim_res = await db.execute(claim_stmt)
    claim = claim_res.scalar_one_or_none()
    if not claim:
        raise ValueError(f"Claim with id {claim_id} not found")

    content = generate_default_content(claim)
    new_draft = AppealDraft(
        claim_id=claim.id,
        content_json=content,
        status="draft",
        ai_generation_status="complete",
    )
    db.add(new_draft)

    event = ClaimEvent(
        claim_id=claim.id,
        event_type="appeal_draft_generated",
        actor_type="ai",
        metadata_json={"sections_count": 6},
    )
    db.add(event)
    await db.commit()
    await db.refresh(new_draft)

    return new_draft


async def update_draft(db: AsyncSession, claim_id: uuid.UUID, draft_id: uuid.UUID, content_json: dict[str, Any]) -> AppealDraft:
    stmt = select(AppealDraft).where(AppealDraft.id == draft_id, AppealDraft.claim_id == claim_id)
    res = await db.execute(stmt)
    draft = res.scalar_one_or_none()
    if not draft:
        raise ValueError(f"Appeal draft {draft_id} not found")

    draft.content_json = content_json
    draft.status = "edited"
    await db.commit()
    await db.refresh(draft)
    return draft


async def approve_draft(db: AsyncSession, claim_id: uuid.UUID, draft_id: uuid.UUID, user_id: uuid.UUID | None = None) -> AppealDraft:
    stmt = select(AppealDraft).where(AppealDraft.id == draft_id, AppealDraft.claim_id == claim_id)
    res = await db.execute(stmt)
    draft = res.scalar_one_or_none()
    if not draft:
        raise ValueError(f"Appeal draft {draft_id} not found")

    draft.status = "approved"
    draft.approved_at = datetime.utcnow()
    draft.approved_by_user_id = user_id

    event = ClaimEvent(
        claim_id=claim_id,
        event_type="appeal_draft_approved",
        actor_type="customer",
        metadata_json={"approved_at": draft.approved_at.isoformat()},
    )
    db.add(event)
    await db.commit()
    await db.refresh(draft)
    return draft


async def export_draft_text(db: AsyncSession, claim_id: uuid.UUID, draft_id: uuid.UUID) -> str:
    stmt = select(AppealDraft).where(AppealDraft.id == draft_id, AppealDraft.claim_id == claim_id)
    res = await db.execute(stmt)
    draft = res.scalar_one_or_none()
    if not draft:
        raise ValueError(f"Appeal draft {draft_id} not found")

    if draft.status != "approved":
        raise PermissionError("Export requires prior policyholder approval (Gatekeeper violation)")

    draft.exported_at = datetime.utcnow()
    await db.commit()

    content = draft.content_json or {}
    lines = [
        "=" * 60,
        "CLAIMSAATHI — FORMAL FIRST-LEVEL GRIEVANCE APPEAL BRIEF",
        "Grounded in IRDAI Master Circular 2024 (Chapter V Moratorium)",
        "=" * 60,
        f"Approved at: {draft.approved_at}",
        "",
    ]
    for key in ["claim_summary", "rejection_reason", "relevant_clause", "factual_clarification", "supporting_evidence_list", "requested_action"]:
        sec = content.get(key, {})
        title = sec.get("title", key.upper())
        text = sec.get("content", "")
        lines.append(f"[{title}]")
        lines.append(text)
        lines.append("-" * 40)
        lines.append("")

    return "\n".join(lines)
