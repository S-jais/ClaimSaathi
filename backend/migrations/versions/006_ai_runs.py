"""
migrations/versions/006_ai_runs.py
Creates: ai_runs AND ai_sources tables.
Both are created here — ai_sources has no meaning without ai_runs.
ai_sources is the "show your work" citation table: every ai_run cites
the specific policy_clauses / document_embeddings it actually used.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- ai_runs (every LLM/RAG call, for audit + cost tracking) ---
    op.create_table(
        "ai_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        # run_type: readiness | rejection_decode | appeal_draft | chat | extraction
        sa.Column("run_type", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),   # openai | gemini | mock
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("prompt_tokens", sa.Integer, nullable=True),
        sa.Column("completion_tokens", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        # status: success | failed | guardrail_blocked | partial
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        # guardrail_result: passed | blocked_banned_phrase | blocked_no_sources | regenerated | hard_fallback
        sa.Column("guardrail_result", sa.String(50), nullable=True),
        sa.Column("guardrail_details", JSONB, nullable=True),
        # NOTE: full prompt/response text is NEVER stored — only structured references
        # Sensitive data is masked before logging (Section E.6, guardrail item 4)
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_runs_claim_id_run_type", "ai_runs", ["claim_id", "run_type"])
    op.create_index("ix_ai_runs_created_at", "ai_runs", ["created_at"])

    # --- ai_sources (which sources an ai_run actually cited) ---
    # Central to the "show your work" citation UI.
    # Every displayed AI-generated factual claim must have at least one row here
    # (enforced programmatically in guardrails.py, not just by convention).
    op.create_table(
        "ai_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ai_run_id", UUID(as_uuid=True), sa.ForeignKey("ai_runs.id", ondelete="CASCADE"), nullable=False),
        # source_type: policy_clause | document_embedding
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), nullable=False),  # polymorphic FK
        sa.Column("rank", sa.Integer, nullable=False, server_default="0"),
        sa.Column("relevance_score", sa.Float, nullable=True),        # vector cosine similarity score
        sa.Column("cited_text_preview", sa.String(500), nullable=True),  # short excerpt for UI
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_sources_ai_run_id", "ai_sources", ["ai_run_id"])
    op.create_index("ix_ai_sources_source", "ai_sources", ["source_type", "source_id"])


def downgrade() -> None:
    op.drop_table("ai_sources")
    op.drop_table("ai_runs")
