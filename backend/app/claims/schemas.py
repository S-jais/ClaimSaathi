"""
app/claims/schemas.py
Pydantic schemas for Claim, Readiness, Rejection Decoder, and Appeal Builder.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ClaimBase(BaseModel):
    policy_id: uuid.UUID | None = None
    claim_type: str = "reimbursement"
    claim_amount: Decimal | None = None
    hospital_name: str | None = None
    admission_date: date | None = None
    discharge_date: date | None = None
    patient_name: str | None = None
    diagnosis: str | None = None


class ClaimCreate(ClaimBase):
    pass


class ClaimUpdate(BaseModel):
    status: str | None = None
    claim_amount: Decimal | None = None
    hospital_name: str | None = None
    admission_date: date | None = None
    discharge_date: date | None = None
    patient_name: str | None = None
    diagnosis: str | None = None


class ClaimRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requirement_type: str
    label: str
    is_satisfied: bool
    satisfied_by_document_id: uuid.UUID | None = None
    is_mandatory: bool = True
    gap_reason: str | None = None
    explanation: str | None = None


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_reference: str | None = None
    claim_type: str
    status: str
    claim_amount: Decimal | None = None
    hospital_name: str | None = None
    admission_date: date | None = None
    discharge_date: date | None = None
    patient_name: str | None = None
    diagnosis: str | None = None
    readiness_score: int | None = None
    ai_explanation_status: str | None = None
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime


class ReadinessResult(BaseModel):
    claim_id: uuid.UUID
    is_ready: bool
    score: int
    requirements: list[dict[str, Any]]
    flags: list[str] = Field(default_factory=list)
    missing_mandatory: list[str] = Field(default_factory=list)
    needs_fix_mandatory: list[str] = Field(default_factory=list)
    cross_doc_checks: list[dict[str, Any]] = Field(default_factory=list)
    ai_explanation_status: str = "available"


class RejectionAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_id: uuid.UUID
    fact_text: str
    ai_interpretation_text: str
    recommendation_text: str
    clause_ref: str | None = None
    confidence: float
    disclaimer: str
    category: str | None = None
    created_at: datetime


class AppealDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_id: uuid.UUID
    status: str
    ai_generation_status: str = "complete"
    content_json: dict[str, Any] | None = None
    approved_at: datetime | None = None
    exported_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AppealDraftUpdate(BaseModel):
    content_json: dict[str, Any]


class ClaimEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_id: uuid.UUID
    event_type: str
    actor_type: str
    metadata_json: dict[str, Any] | None = None
    occurred_at: datetime


class AuditedLineItemSchema(BaseModel):
    item_id: str
    description: str
    amount_paise: int
    classification: str
    category: str | None = None
    rule_id: str | None = None
    guideline_reference: str | None = None
    explanation: str | None = None
    patient_remedy: str | None = None


class WaterfallStepSchema(BaseModel):
    step_key: str
    label: str
    amount_paise: int
    status: str
    notes: str | None = None


class BillAuditResponse(BaseModel):
    rules_version: str
    gross_billed_paise: int
    commonly_non_payable_paise: int
    needs_review_paise: int
    payable_medical_paise: int
    room_rent_deduction_paise: int
    room_rent_status: str
    copay_deduction_paise: int
    copay_status: str
    indicative_payable_paise: int
    estimate_label: str
    waterfall: list[WaterfallStepSchema]
    items: list[AuditedLineItemSchema]
    non_payable_count: int
    needs_review_count: int
    payable_medical_count: int


class BillAuditRequest(BaseModel):
    items: list[dict[str, Any]] | None = None
    policy_room_rent_limit_daily_paise: int | None = None
    actual_room_rent_daily_paise: int | None = None
    stay_days: int = 1
    copay_percentage: int | None = None

