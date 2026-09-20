"""
app/copilot/models.py
SQLAlchemy models for Journey Chatbot sessions, messages, and human-in-the-loop drafts.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class CopilotSession(Base):
    __tablename__ = "copilot_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="ONBOARDING")
    session_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    messages: Mapped[list[CopilotMessage]] = relationship(
        "CopilotMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="CopilotMessage.created_at",
    )
    drafts: Mapped[list[CopilotDraft]] = relationship(
        "CopilotDraft",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class CopilotMessage(Base):
    __tablename__ = "copilot_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("copilot_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(sa.String(20), nullable=False)  # "user", "assistant", "system", "tool"
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    structured_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tool_trace: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationship
    session: Mapped[CopilotSession] = relationship("CopilotSession", back_populates="messages")


class CopilotDraft(Base):
    __tablename__ = "copilot_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("copilot_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draft_type: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="appeal")
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False, default="Grievance / Appeal Draft")
    content_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="DRAFT")  # DRAFT, APPROVED, REJECTED, SENT
    approved_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationship
    session: Mapped[CopilotSession | None] = relationship("CopilotSession", back_populates="drafts")
