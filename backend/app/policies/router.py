"""
app/policies/router.py
FastAPI router for policy management and clause retrieval.
"""
from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.service import get_current_user
from app.core.db import get_db
from app.policies.models import Policy, PolicyVersion, PolicyClause
from app.policies.schemas import PolicyCreate, PolicyResponse, PolicyClauseResponse

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = select(Policy).where(Policy.user_id == user.id, Policy.deleted_at.is_(None)).order_by(Policy.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    data: PolicyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    policy = Policy(
        user_id=user.id,
        insurer_name=data.insurer_name,
        policy_number=data.policy_number,
        product_type=data.product_type,
        sum_insured=data.sum_insured,
        policy_start_date=data.policy_start_date,
        policy_end_date=data.policy_end_date,
        status="active",
        is_demo=user.is_demo,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = select(Policy).where(Policy.id == policy_id, Policy.user_id == user.id)
    res = await db.execute(stmt)
    policy = res.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.get("/{policy_id}/clauses", response_model=list[PolicyClauseResponse])
async def get_policy_clauses(
    policy_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = (
        select(PolicyClause)
        .join(PolicyVersion, PolicyClause.policy_version_id == PolicyVersion.id)
        .where(PolicyVersion.policy_id == policy_id)
        .order_by(PolicyClause.chunk_index.asc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()
