"""
backend/app/documents/schemas.py
Pydantic schemas for Document upload, line items, and job status.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadRequest(BaseModel):
    doc_type: str = "other"
    original_filename: str
    size_bytes: int
    mime_type: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_id: uuid.UUID | None = None
    doc_type: str
    status: str
    original_filename: str | None = None
    size_bytes: int | None = None
    mime_type: str | None = None
    ocr_confidence: float | None = None
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime


class ExtractedLineItem(BaseModel):
    id: str
    description: str
    amount_paise: int
    quantity: int = 1
    rate_paise: int = 0
    raw_category: str | None = None
    classification: str = "NEEDS_REVIEW"  # PAYABLE_MEDICAL, COMMONLY_NON_PAYABLE, NEEDS_REVIEW
    reason: str | None = None
    rule_id: str | None = None
    source_ref: str | None = None


class ExtractedDocumentPayload(BaseModel):
    doc_type: str = "OTHER"
    doc_type_confidence: float = 0.5
    patient_name: str | None = None
    hospital_name: str | None = None
    admission_date: str | None = None
    discharge_date: str | None = None
    diagnosis_text: str | None = None
    clause_ref: str | None = None
    line_items: list[ExtractedLineItem] = Field(default_factory=list)
    stated_total_paise: int = 0
    computed_sum_paise: int = 0
    is_reconciled: bool = True
    reconciliation_warning: str | None = None
    warnings: list[str] = Field(default_factory=list)


class AnalysisJobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str  # QUEUED, READING, CLASSIFYING, VERIFYING, AUDITING, COMPLETED, FAILED
    stage: str | None = None
    progress_pct: int = 0
    error_code: str | None = None
    error_message: str | None = None
    extracted_data: ExtractedDocumentPayload | None = None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    claim_id: uuid.UUID | None = None
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    job_id: uuid.UUID
    status: str
    stage: str
    extracted: ExtractedDocumentPayload | None = None
