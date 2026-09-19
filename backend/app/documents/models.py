"""
app/documents/models.py
SQLAlchemy models for uploaded claim & policy documents, versions, and extractions.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="SET NULL"), nullable=True)
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    doc_type: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="other")
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="queued")
    object_storage_key: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True)
    bucket_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    classified_doc_type: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    classification_confirmed: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_demo: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    extractions: Mapped[list[DocumentExtraction]] = relationship("DocumentExtraction", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    object_storage_key: Mapped[str] = mapped_column(sa.String(1000), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    schema_name: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    extracted_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    confidence_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    extractor_version: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="1.0")
    extraction_status: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    document: Mapped[Document] = relationship("Document", back_populates="extractions")
