"""
app/claims/models.py
SQLAlchemy models for claims, requirements, timeline events, rejection reasons,
and appeal drafts.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("policies.id", ondelete="SET NULL"), nullable=True)
    claim_reference: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    claim_type: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="reimbursement")
    status: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="draft")
    claim_amount: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 2), nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    admission_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    discharge_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    patient_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    readiness_score: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    readiness_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ai_explanation_status: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    is_demo: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    requirements: Mapped[list[ClaimRequirement]] = relationship("ClaimRequirement", back_populates="claim", cascade="all, delete-orphan")
    events: Mapped[list[ClaimEvent]] = relationship("ClaimEvent", back_populates="claim", cascade="all, delete-orphan")
    rejection_reasons: Mapped[list[RejectionReason]] = relationship("RejectionReason", back_populates="claim", cascade="all, delete-orphan")
    appeal_drafts: Mapped[list[AppealDraft]] = relationship("AppealDraft", back_populates="claim", cascade="all, delete-orphan")


class ClaimRequirement(Base):
    __tablename__ = "claim_requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    requirement_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    label: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    is_satisfied: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    satisfied_by_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    explanation: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    claim: Mapped[Claim] = relationship("Claim", back_populates="requirements")


class ClaimEvent(Base):
    __tablename__ = "claim_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    actor_type: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="system")
    actor_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    claim: Mapped[Claim] = relationship("Claim", back_populates="events")


class RejectionReason(Base):
    __tablename__ = "rejection_reasons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    raw_reason_text: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    matched_clause_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    match_confidence: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    category: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    fact_text: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    ai_interpretation_text: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    recommendation_text: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    ai_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    extractor_version: Mapped[str | None] = mapped_column(sa.String(20), nullable=True, default="1.0")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    claim: Mapped[Claim] = relationship("Claim", back_populates="rejection_reasons")


class AppealDraft(Base):
    __tablename__ = "appeal_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    rejection_reason_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("rejection_reasons.id", ondelete="SET NULL"), nullable=True)
    ai_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    content_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ai_generation_status: Mapped[str | None] = mapped_column(sa.String(20), nullable=True, default="complete")
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="draft")
    approved_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    exported_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    export_object_key: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    claim: Mapped[Claim] = relationship("Claim", back_populates="appeal_drafts")
