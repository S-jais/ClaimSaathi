"""
migrations/versions/004_claims.py
Creates: claims, claim_requirements, claim_events tables.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- claims ---
    op.create_table(
        "claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("policy_id", UUID(as_uuid=True), sa.ForeignKey("policies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("claim_reference", sa.String(50), nullable=True),   # e.g. CLM-20491
        sa.Column("claim_type", sa.String(30), nullable=False, server_default="reimbursement"),
        # Status machine: draft -> ready -> submitted -> rejected -> appealing -> resolved
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("claim_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("hospital_name", sa.String(500), nullable=True),
        sa.Column("admission_date", sa.Date, nullable=True),
        sa.Column("discharge_date", sa.Date, nullable=True),
        sa.Column("patient_name", sa.String(255), nullable=True),
        sa.Column("diagnosis", sa.Text, nullable=True),
        sa.Column("readiness_score", sa.Integer, nullable=True),       # 0–100 from rules engine
        sa.Column("readiness_summary", JSONB, nullable=True),          # latest rules engine output
        sa.Column("ai_explanation_status", sa.String(20), nullable=True),  # available | unavailable | partial
        sa.Column("is_demo", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_claims_user_id_status", "claims", ["user_id", "status"])
    op.create_index("ix_claims_claim_reference", "claims", ["claim_reference"])

    # --- claim_requirements (rules engine output: checklist) ---
    op.create_table(
        "claim_requirements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_type", sa.String(100), nullable=False),  # e.g. consultation_notes
        sa.Column("label", sa.String(255), nullable=False),             # Human-readable label
        sa.Column("is_satisfied", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("satisfied_by_document_id", UUID(as_uuid=True), nullable=True),  # FK added after docs table
        sa.Column("is_mandatory", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("explanation", sa.Text, nullable=True),               # LLM-generated plain-language explanation
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_claim_requirements_claim_id", "claim_requirements", ["claim_id"])

    # --- claim_events (append-only timeline) ---
    op.create_table(
        "claim_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        # actor_type: customer | system | ai
        sa.Column("actor_type", sa.String(20), nullable=False, server_default="system"),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Note: NO updated_at — this is append-only
    )
    op.create_index("ix_claim_events_claim_id_occurred_at", "claim_events", ["claim_id", "occurred_at"])


def downgrade() -> None:
    op.drop_table("claim_events")
    op.drop_table("claim_requirements")
    op.drop_table("claims")
