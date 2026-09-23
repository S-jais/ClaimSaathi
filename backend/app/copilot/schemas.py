"""
app/copilot/schemas.py
Pydantic schemas for the Journey Chatbot ("ClaimSaathi Copilot").
Implements the Section 6 structured response payload contract.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class CitationItem(BaseModel):
    id: str = Field(..., description="Unique citation identifier matching fact references")
    type: Literal["document", "policy_clause", "regulatory", "case_data"] = "document"
    title: str = Field(..., description="Human readable title e.g. Settlement Letter")
    reference: str = Field(..., description="Page or Clause identifier e.g. Page 1, Clause 4.2")
    snippet: str = Field("", description="Short excerpt from the source text")


class FactItem(BaseModel):
    id: str
    text: str
    citations: list[str] = Field(default_factory=list)


class InterpretationItem(BaseModel):
    id: str
    text: str


class RecommendationItem(BaseModel):
    id: str
    text: str


class StructuredSections(BaseModel):
    facts: list[FactItem] = Field(default_factory=list)
    interpretations: list[InterpretationItem] = Field(default_factory=list)
    recommendations: list[RecommendationItem] = Field(default_factory=list)


class DraftCard(BaseModel):
    draft_id: str
    draft_type: str = "appeal"
    title: str
    status: Literal["DRAFT", "APPROVED", "REJECTED", "SENT"] = "DRAFT"
    summary: str
    content: dict[str, Any] = Field(default_factory=dict)


class NextBestAction(BaseModel):
    action: str
    label: str
    route: str | None = None


class CopilotResponsePayload(BaseModel):
    """Section 6 structured contract for every Copilot response turn."""
    stage: str
    ui_stage: str
    reply: str
    language: Literal["en", "hi", "hinglish"] = "en"
    spoken_text: str = ""
    read_back_required: bool = False
    speak_priority: Literal["normal", "urgent"] = "normal"
    sections: StructuredSections = Field(default_factory=StructuredSections)
    citations: list[CitationItem] = Field(default_factory=list)
    draft_card: DraftCard | None = None
    quick_replies: list[str] = Field(default_factory=list)
    next_best_action: NextBestAction | None = None
    warnings: list[str] = Field(default_factory=list)


# Request schemas
class CreateSessionRequest(BaseModel):
    case_id: str = Field(..., description="UUID or claim_reference string of the claim")


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    language: str = Field("en", description="Language code: en, hi, or hinglish")
    mode: Literal["text", "voice"] = "text"
    input_source: Literal["text", "voice"] = "text"
    transcript_confidence: float | None = None
    language_hint: str | None = None


class ApproveDraftRequest(BaseModel):
    notes: str | None = None


class RejectDraftRequest(BaseModel):
    reason: str | None = None


# Session and message response schemas
class CopilotMessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    structured_payload: CopilotResponsePayload | None = None
    tool_trace: list[dict[str, Any]] | None = None
    citations: list[dict[str, Any]] | None = None
    created_at: datetime


class CopilotSessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    case_id: uuid.UUID
    stage: str
    ui_stage: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
