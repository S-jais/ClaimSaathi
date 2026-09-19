"""
migrations/versions/002_consents.py
Creates: consents table (DPDP-aligned, append-only per-purpose consent ledger).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        # Purpose enum: document_processing | ai_analysis | notifications
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("consent_text_version", sa.String(20), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope_json", JSONB, nullable=True),  # optional fine-grained scope
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # NOTE: This table is APPEND-ONLY at the application layer.
        # A revoke creates a NEW row with revoked_at set — never updates an existing row.
        # This preserves the full consent history for DPDP compliance.
    )
    op.create_index("ix_consents_user_id_purpose", "consents", ["user_id", "purpose"])


def downgrade() -> None:
    op.drop_table("consents")
