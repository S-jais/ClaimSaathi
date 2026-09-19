"""
app/documents/router.py
FastAPI router for document management and presigned upload URLs.
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
from app.documents.models import Document
from app.documents.schemas import DocumentUploadRequest, DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    claim_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = select(Document).where(Document.user_id == user.id, Document.deleted_at.is_(None))
    if claim_id:
        stmt = stmt.where(Document.claim_id == claim_id)
    stmt = stmt.order_by(Document.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def register_document(
    data: DocumentUploadRequest,
    claim_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    doc = Document(
        user_id=user.id,
        claim_id=claim_id,
        doc_type=data.doc_type,
        status="queued",
        original_filename=data.original_filename,
        size_bytes=data.size_bytes,
        mime_type=data.mime_type,
        is_demo=user.is_demo,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = select(Document).where(Document.id == document_id, Document.user_id == user.id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
