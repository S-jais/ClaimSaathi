"""
app/documents/schemas.py
Pydantic schemas for Document upload and retrieval.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


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
    is_demo: bool
    created_at: datetime
    updated_at: datetime
