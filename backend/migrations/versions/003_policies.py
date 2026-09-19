"""
migrations/versions/003_policies.py
Creates: policies, policy_versions, policy_clauses tables.
policy_clauses stores pgvector embeddings — this is the RAG corpus per user.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- policies ---
    op.create_table(
        "policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("insurer_name", sa.String(255), nullable=False),
        sa.Column("policy_number", sa.String(100), nullable=False),  # encrypted at column level in prod
        sa.Column("product_type", sa.String(100), nullable=True),
        sa.Column("sum_insured", sa.Numeric(12, 2), nullable=True),
        sa.Column("policy_start_date", sa.Date, nullable=True),
        sa.Column("policy_end_date", sa.Date, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("is_demo", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_policies_user_id", "policies", ["user_id"])

    # --- policy_versions ---
    op.create_table(
        "policy_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("policy_id", UUID(as_uuid=True), sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), nullable=True),  # FK to documents, added after doc table
        sa.Column("version_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("effective_from", sa.Date, nullable=True),
        sa.Column("parsed_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_policy_versions_policy_id", "policy_versions", ["policy_id"])

    # --- policy_clauses (RAG corpus) ---
    op.create_table(
        "policy_clauses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("policy_version_id", UUID(as_uuid=True), sa.ForeignKey("policy_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("clause_ref", sa.String(50), nullable=True),       # e.g. "4.2"
        sa.Column("section_title", sa.String(500), nullable=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("chunk_index", sa.Integer, nullable=False, server_default="0"),
        # pgvector embedding — 1536 dims for text-embedding-3-small
        sa.Column("embedding", sa.Column("embedding", sa.Text).type, nullable=True),  # placeholder; real type set below
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    # Add the actual vector column using raw SQL (pgvector type not native in SQLAlchemy migration DSL)
    op.execute("ALTER TABLE policy_clauses ADD COLUMN IF NOT EXISTS embedding vector(1536)")
    op.execute("ALTER TABLE policy_clauses DROP COLUMN IF EXISTS embedding")  # drop placeholder
    # Re-add as actual vector type
    op.execute("ALTER TABLE policy_clauses ADD COLUMN embedding vector(1536)")

    op.create_index("ix_policy_clauses_policy_version_id", "policy_clauses", ["policy_version_id"])
    # HNSW index for fast approximate nearest-neighbor search
    op.execute(
        "CREATE INDEX ix_policy_clauses_embedding_hnsw "
        "ON policy_clauses USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.drop_table("policy_clauses")
    op.drop_table("policy_versions")
    op.drop_table("policies")
