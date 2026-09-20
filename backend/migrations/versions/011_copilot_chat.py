"""
migrations/versions/011_copilot_chat.py
Creates copilot_sessions, copilot_messages, and copilot_drafts tables
for the Journey Chatbot ("ClaimSaathi Copilot").
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. copilot_sessions
    op.create_table(
        "copilot_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False, server_default="ONBOARDING"),
        sa.Column("session_metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_copilot_sessions_user_id", "copilot_sessions", ["user_id"])
    op.create_index("ix_copilot_sessions_case_id", "copilot_sessions", ["case_id"])

    # 2. copilot_messages
    op.create_table(
        "copilot_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("copilot_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("structured_payload", JSONB, nullable=True),
        sa.Column("tool_trace", JSONB, nullable=True),
        sa.Column("citations", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_copilot_messages_session_id", "copilot_messages", ["session_id"])

    # 3. copilot_drafts
    op.create_table(
        "copilot_drafts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("copilot_sessions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("draft_type", sa.String(50), nullable=False, server_default="appeal"),
        sa.Column("title", sa.String(255), nullable=False, server_default="Grievance / Appeal Draft"),
        sa.Column("content_json", JSONB, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_copilot_drafts_case_id", "copilot_drafts", ["case_id"])
    op.create_index("ix_copilot_drafts_session_id", "copilot_drafts", ["session_id"])


def downgrade() -> None:
    op.drop_table("copilot_drafts")
    op.drop_table("copilot_messages")
    op.drop_table("copilot_sessions")
