"""
app/claims/router.py
FastAPI router for Claims, Readiness Check, Rejection Decoder, and Appeal Builder.
"""
from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.service import get_current_user
from app.claims.models import Claim, ClaimEvent
from app.claims.schemas import (
    ClaimCreate,
    ClaimResponse,
    ReadinessResult,
    RejectionAnalysisResponse,
    AppealDraftResponse,
    AppealDraftUpdate,
    ClaimEventResponse,
    BillAuditResponse,
    BillAuditRequest,
)
from app.claims.readiness.service import run_readiness_check
from app.claims.audit.service import audit_claim_bill
from app.claims.rejection.service import analyze_rejection
from app.claims.appeals.service import (
    get_or_create_draft,
    update_draft,
    approve_draft,
    export_draft_text,
)
from app.core.db import get_db
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/claims", tags=["claims"])


@router.get("", response_model=list[ClaimResponse])
async def list_claims(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = select(Claim).where(Claim.user_id == user.id, Claim.deleted_at.is_(None)).order_by(Claim.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(
    data: ClaimCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    ref = f"CLM-{uuid.uuid4().hex[:5].upper()}"
    claim = Claim(
        user_id=user.id,
        policy_id=data.policy_id,
        claim_reference=ref,
        claim_type=data.claim_type,
        claim_amount=data.claim_amount,
        hospital_name=data.hospital_name,
        admission_date=data.admission_date,
        discharge_date=data.discharge_date,
        patient_name=data.patient_name or user.full_name,
        diagnosis=data.diagnosis,
        status="draft",
        is_demo=user.is_demo,
    )
    db.add(claim)
    await db.flush()

    event = ClaimEvent(
        claim_id=claim.id,
        event_type="claim_created",
        actor_type="customer",
        actor_id=str(user.id),
        metadata_json={"reference": ref},
    )
    db.add(event)
    await db.commit()
    await db.refresh(claim)
    return claim


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = select(Claim).where(Claim.id == claim_id, Claim.user_id == user.id)
    res = await db.execute(stmt)
    claim = res.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.get("/{claim_id}/timeline", response_model=list[ClaimEventResponse])
async def get_claim_timeline(
    claim_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = select(ClaimEvent).where(ClaimEvent.claim_id == claim_id).order_by(ClaimEvent.occurred_at.asc())
    res = await db.execute(stmt)
    return res.scalars().all()


# --- Readiness Engine ---
@router.post("/{claim_id}/readiness-check", response_model=ReadinessResult)
@router.get("/{claim_id}/readiness-check", response_model=ReadinessResult)
async def check_claim_readiness(
    claim_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        return await run_readiness_check(db, claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Bill Audit Engine ---
@router.post("/{claim_id}/bill-audit", response_model=BillAuditResponse)
@router.get("/{claim_id}/bill-audit", response_model=BillAuditResponse)
async def audit_claim_bill_endpoint(
    claim_id: uuid.UUID,
    request: BillAuditRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        return await audit_claim_bill(db, claim_id, request=request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))



# --- Rejection Decoder ---
@router.post("/{claim_id}/rejection-analysis", response_model=RejectionAnalysisResponse)
@router.get("/{claim_id}/rejection-analysis", response_model=RejectionAnalysisResponse)
async def get_rejection_analysis(
    claim_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        rejection = await analyze_rejection(db, claim_id)
        return rejection
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Appeal Builder ---
@router.get("/{claim_id}/appeal-draft/{draft_id}", response_model=AppealDraftResponse)
async def get_appeal(
    claim_id: uuid.UUID,
    draft_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        draft = await get_or_create_draft(db, claim_id)
        return draft
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{claim_id}/appeal-draft/{draft_id}", response_model=AppealDraftResponse)
async def patch_appeal(
    claim_id: uuid.UUID,
    draft_id: uuid.UUID,
    data: AppealDraftUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        return await update_draft(db, claim_id, draft_id, data.content_json)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{claim_id}/appeal-draft/{draft_id}/approve", response_model=AppealDraftResponse)
async def approve_appeal(
    claim_id: uuid.UUID,
    draft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        return await approve_draft(db, claim_id, draft_id, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{claim_id}/appeal-draft/{draft_id}/export")
async def export_appeal(
    claim_id: uuid.UUID,
    draft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        text = await export_draft_text(db, claim_id, draft_id)
        return Response(
            content=text,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="appeal_{claim_id}.txt"'},
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
