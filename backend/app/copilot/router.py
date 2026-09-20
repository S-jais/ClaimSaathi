"""
app/copilot/router.py
FastAPI Router for ClaimSaathi Copilot (Journey Chatbot).
Endpoints:
- POST /copilot/sessions: Create/retrieve active session for a claim
- GET  /copilot/sessions/{id}: Retrieve session state and current UI stage
- POST /copilot/sessions/{id}/messages: Send message (standard JSON or SSE stream)
- GET  /copilot/sessions/{id}/messages: Message history
- POST /copilot/drafts/{id}/approve: Human approval gatekeeper
- POST /copilot/drafts/{id}/reject: Reject/revise draft
- DELETE /copilot/memory: Privacy forget endpoint (Cognee purge + chat purge)
"""
from __future__ import annotations

from datetime import datetime
import json
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.auth.models import User
from app.auth.service import get_current_user
from app.claims.models import Claim, ClaimEvent
from app.claims.router import _resolve_claim
from app.copilot.models import CopilotSession, CopilotMessage, CopilotDraft
from app.copilot.orchestrator import get_copilot_orchestrator
from app.copilot.schemas import (
    ApproveDraftRequest,
    CopilotMessageResponse,
    CopilotResponsePayload,
    CopilotSessionResponse,
    CreateSessionRequest,
    RejectDraftRequest,
    SendMessageRequest,
)
from app.copilot.state_machine import get_ui_stage
from app.core.db import get_db
from app.memory.cognee_client import get_cognee_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/sessions", response_model=CopilotSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_or_get_session(
    body: CreateSessionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create or resume a Copilot session tied to a user's claim."""
    claim = await _resolve_claim(db, user, body.case_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    # Check for existing active session
    stmt = (
        select(CopilotSession)
        .where(CopilotSession.case_id == claim.id, CopilotSession.user_id == user.id)
        .order_by(CopilotSession.created_at.desc())
    )
    res = await db.execute(stmt)
    session = res.scalars().first()

    if not session:
        # Determine initial stage
        initial_stage = "ONBOARDING"
        if claim.status in {"rejected", "partially_approved", "query_raised"}:
            initial_stage = "REJECTED_DECODING"
        elif claim.status in {"submitted", "in_review"}:
            initial_stage = "SUBMITTED_TRACKING"
        elif claim.readiness_score is not None:
            initial_stage = "CLAIM_PREPARATION"

        session = CopilotSession(
            user_id=user.id,
            case_id=claim.id,
            stage=initial_stage,
            session_metadata={},
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # Count messages
    msg_stmt = select(CopilotMessage).where(CopilotMessage.session_id == session.id)
    msg_res = await db.execute(msg_stmt)
    count = len(msg_res.scalars().all())

    return CopilotSessionResponse(
        id=session.id,
        user_id=session.user_id,
        case_id=session.case_id,
        stage=session.stage,
        ui_stage=get_ui_stage(session.stage),
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=count,
    )


@router.get("/sessions/{session_id}", response_model=CopilotSessionResponse)
async def get_session(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieve session metadata and current stage."""
    stmt = select(CopilotSession).where(CopilotSession.id == session_id, CopilotSession.user_id == user.id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    msg_stmt = select(CopilotMessage).where(CopilotMessage.session_id == session.id)
    msg_res = await db.execute(msg_stmt)
    count = len(msg_res.scalars().all())

    return CopilotSessionResponse(
        id=session.id,
        user_id=session.user_id,
        case_id=session.case_id,
        stage=session.stage,
        ui_stage=get_ui_stage(session.stage),
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=count,
    )


@router.get("/sessions/{session_id}/messages", response_model=list[CopilotMessageResponse])
async def get_session_messages(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieve history of turns for the given Copilot session."""
    sess_stmt = select(CopilotSession).where(CopilotSession.id == session_id, CopilotSession.user_id == user.id)
    sess_res = await db.execute(sess_stmt)
    session = sess_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    msg_stmt = (
        select(CopilotMessage)
        .where(CopilotMessage.session_id == session_id)
        .order_by(CopilotMessage.created_at.asc())
    )
    msg_res = await db.execute(msg_stmt)
    messages = msg_res.scalars().all()

    return [
        CopilotMessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            structured_payload=CopilotResponsePayload.model_validate(m.structured_payload) if m.structured_payload else None,
            tool_trace=m.tool_trace,
            citations=m.citations,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID,
    body: SendMessageRequest,
    stream: bool = Query(default=False, description="Enable Server-Sent Events stream"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Send user message to Copilot session. Returns structured JSON or SSE stream."""
    stmt = select(CopilotSession).where(CopilotSession.id == session_id, CopilotSession.user_id == user.id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    claim_stmt = select(Claim).where(Claim.id == session.case_id)
    claim_res = await db.execute(claim_stmt)
    claim = claim_res.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bound claim not found")

    orchestrator = get_copilot_orchestrator()

    if stream:
        async def event_generator():
            async for event_dict in orchestrator.stream_turn(
                db=db,
                session=session,
                claim=claim,
                user=user,
                user_message=body.content,
                language=body.language,
            ):
                event_type = event_dict.get("event", "message")
                data_json = json.dumps(event_dict.get("data", {}))
                yield f"event: {event_type}\ndata: {data_json}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Standard synchronous turn
    payload = await orchestrator.execute_turn(
        db=db,
        session=session,
        claim=claim,
        user=user,
        user_message=body.content,
        language=body.language,
        mode=body.mode,
    )
    return payload


@router.post("/drafts/{draft_id}/approve", status_code=status.HTTP_200_OK)
async def approve_draft(
    draft_id: uuid.UUID,
    body: ApproveDraftRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Human-in-the-loop gatekeeper: User explicitly approves the generated draft.
    Marks status as 'APPROVED' with timestamp and user ID.
    """
    stmt = select(CopilotDraft).where(CopilotDraft.id == draft_id)
    res = await db.execute(stmt)
    draft = res.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    draft.status = "APPROVED"
    draft.approved_at = datetime.utcnow()
    draft.approved_by_user_id = user.id

    # Log ClaimEvent
    event = ClaimEvent(
        claim_id=draft.case_id,
        event_type="appeal_draft_approved",
        actor_type="customer",
        actor_id=str(user.id),
        metadata_json={"draft_id": str(draft.id), "notes": body.notes},
    )
    db.add(event)
    await db.commit()

    return {
        "status": "APPROVED",
        "draft_id": str(draft.id),
        "approved_at": draft.approved_at.isoformat(),
        "message": "Draft approved. You may now export or send this grievance to your insurer.",
    }


@router.post("/drafts/{draft_id}/reject", status_code=status.HTTP_200_OK)
async def reject_draft(
    draft_id: uuid.UUID,
    body: RejectDraftRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Reject or request revision of a draft."""
    stmt = select(CopilotDraft).where(CopilotDraft.id == draft_id)
    res = await db.execute(stmt)
    draft = res.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    draft.status = "REJECTED"
    await db.commit()

    return {
        "status": "REJECTED",
        "draft_id": str(draft.id),
        "reason": body.reason or "Draft rejected by user for revision.",
    }


@router.delete("/memory", status_code=status.HTTP_200_OK)
async def purge_user_memory(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    GDPR & DPDP 'Right to be Forgotten' endpoint.
    Purges Cognee knowledge-graph memory and Copilot message history for this user.
    """
    cognee = get_cognee_client()
    cognee_cleared = await cognee.forget(str(user.id))

    # Remove all Copilot sessions and messages for this user
    del_stmt = delete(CopilotSession).where(CopilotSession.user_id == user.id)
    await db.execute(del_stmt)
    await db.commit()

    logger.info("user_memory_purged", user_id=str(user.id), cognee_cleared=cognee_cleared)
    return {
        "status": "success",
        "message": "All Copilot chat history and institutional memory have been permanently purged.",
        "cognee_cleared": cognee_cleared,
    }
