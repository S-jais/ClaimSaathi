"""
migrations/versions/009_notifications.py
Creates: notifications table.
Separate from Phase 1 auth migrations; applied in Phase 9 but listed
explicitly here to prevent it being forgotten.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="SET NULL"), nullable=True),
        # channel: email | in_app
        sa.Column("channel", sa.String(20), nullable=False, server_default="in_app"),
        sa.Column("template", sa.String(100), nullable=False),
        sa.Column("payload_json", JSONB, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        # status: pending | sent | failed | read
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notifications_user_id_sent_at", "notifications", ["user_id", "sent_at"])
    op.create_index("ix_notifications_status", "notifications", ["status"])


def downgrade() -> None:
    op.drop_table("notifications")
