"""
migrations/versions/007_appeals_grievances.py
Creates: rejection_reasons, evidence_links, appeal_drafts, grievances tables.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- rejection_reasons (Rejection Decoder core output) ---
    op.create_table(
        "rejection_reasons",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_reason_text", sa.Text, nullable=True),
        sa.Column("matched_clause_id", UUID(as_uuid=True), nullable=True),   # FK to policy_clauses
        sa.Column("match_confidence", sa.Float, nullable=True),               # retrieval confidence, NOT approval probability
        # category: documentation_gap | exclusion | waiting_period | needs_manual_review | other
        sa.Column("category", sa.String(50), nullable=True),
        # Structured output — three labeled fields (enforced in guardrails.py)
        sa.Column("fact_text", sa.Text, nullable=True),                       # FACT section
        sa.Column("ai_interpretation_text", sa.Text, nullable=True),          # AI INTERPRETATION section
        sa.Column("recommendation_text", sa.Text, nullable=True),             # RECOMMENDATION section
        sa.Column("ai_run_id", UUID(as_uuid=True), sa.ForeignKey("ai_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("extractor_version", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_rejection_reasons_claim_id", "rejection_reasons", ["claim_id"])

    # --- evidence_links (many-to-many evidence graph) ---
    op.create_table(
        "evidence_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_type", sa.String(50), nullable=False),    # claim_requirement | rejection_reason
        sa.Column("source_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),    # document | policy_clause | document_embedding
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        # relation: supports | contradicts | missing
        sa.Column("relation", sa.String(20), nullable=False, server_default="supports"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_evidence_links_source", "evidence_links", ["source_type", "source_id"])
    op.create_index("ix_evidence_links_target", "evidence_links", ["target_type", "target_id"])

    # --- appeal_drafts ---
    op.create_table(
        "appeal_drafts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rejection_reason_id", UUID(as_uuid=True), sa.ForeignKey("rejection_reasons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ai_run_id", UUID(as_uuid=True), sa.ForeignKey("ai_runs.id", ondelete="SET NULL"), nullable=True),
        # Structured content — rendered as editable sections in the UI
        sa.Column("content_json", JSONB, nullable=True),
        sa.Column("ai_generation_status", sa.String(20), nullable=True),  # complete | partial | failed
        # Status machine: draft -> edited -> approved
        # Export only permitted when status = 'approved' (enforced server-side)
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("export_object_key", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # NOTE: submitted_to_insurer_at is deliberately absent — ClaimSaathi never auto-submits.
    )
    op.create_index("ix_appeal_drafts_claim_id", "appeal_drafts", ["claim_id"])

    # --- grievances ---
    op.create_table(
        "grievances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("package_json", JSONB, nullable=True),     # timeline + evidence + draft communication
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_grievances_claim_id", "grievances", ["claim_id"])


def downgrade() -> None:
    op.drop_table("grievances")
    op.drop_table("appeal_drafts")
    op.drop_table("evidence_links")
    op.drop_table("rejection_reasons")
