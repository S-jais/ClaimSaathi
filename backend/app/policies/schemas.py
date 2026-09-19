"""
app/policies/schemas.py
Pydantic schemas for Policy management.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class PolicyCreate(BaseModel):
    insurer_name: str
    policy_number: str
    product_type: str | None = None
    sum_insured: Decimal | None = None
    policy_start_date: date | None = None
    policy_end_date: date | None = None


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    insurer_name: str
    policy_number: str
    product_type: str | None = None
    sum_insured: Decimal | None = None
    policy_start_date: date | None = None
    policy_end_date: date | None = None
    status: str
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class PolicyClauseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clause_ref: str | None = None
    section_title: str | None = None
    text: str
    page_number: int | None = None
