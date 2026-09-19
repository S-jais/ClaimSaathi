"""
app/policies/models.py
SQLAlchemy models for policies, versions, and clause-level RAG embeddings.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    insurer_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    policy_number: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    product_type: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    sum_insured: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 2), nullable=True)
    policy_start_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    policy_end_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="active")
    is_demo: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    versions: Mapped[list[PolicyVersion]] = relationship("PolicyVersion", back_populates="policy", cascade="all, delete-orphan")


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    version_number: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    effective_from: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    parsed_status: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    policy: Mapped[Policy] = relationship("Policy", back_populates="versions")
    clauses: Mapped[list[PolicyClause]] = relationship("PolicyClause", back_populates="policy_version", cascade="all, delete-orphan")


class PolicyClause(Base):
    __tablename__ = "policy_clauses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("policy_versions.id", ondelete="CASCADE"), nullable=False)
    clause_ref: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    section_title: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    policy_version: Mapped[PolicyVersion] = relationship("PolicyVersion", back_populates="clauses")
