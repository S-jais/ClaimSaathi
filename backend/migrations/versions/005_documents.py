"""
migrations/versions/005_documents.py
Creates: documents, document_versions, document_extractions, document_embeddings tables.
document_embeddings is the pgvector table for NON-POLICY evidence docs
(hospital bill, discharge summary, etc.) — queried by the Rejection Decoder's
evidence-retrieval step (Section E.4).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="SET NULL"), nullable=True),
        sa.Column("policy_version_id", UUID(as_uuid=True), nullable=True),  # FK to policy_versions (optional)
        # doc_type enum
        sa.Column("doc_type", sa.String(50), nullable=False, server_default="other"),
        # status machine: queued -> processing -> completed | failed | retrying
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("object_storage_key", sa.String(1000), nullable=True),  # null until upload confirmed
        sa.Column("bucket_name", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.BigInteger, nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("original_filename", sa.String(500), nullable=True),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column("ocr_confidence", sa.Float, nullable=True),
        sa.Column("classified_doc_type", sa.String(50), nullable=True),  # auto-detected type
        sa.Column("classification_confirmed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_demo", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_documents_claim_id", "documents", ["claim_id"])
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # Add FK from policy_versions.document_id -> documents (cross-migration FK)
    op.create_foreign_key(
        "fk_policy_versions_document_id",
        "policy_versions",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Add FK from claim_requirements.satisfied_by_document_id -> documents
    op.create_foreign_key(
        "fk_claim_requirements_document_id",
        "claim_requirements",
        "documents",
        ["satisfied_by_document_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- document_versions (re-uploads of same logical document) ---
    op.create_table(
        "document_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("object_storage_key", sa.String(1000), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])

    # --- document_extractions (schema-specific structured output per doc type) ---
    op.create_table(
        "document_extractions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("schema_name", sa.String(50), nullable=False),         # e.g. hospital_bill, discharge_summary
        sa.Column("extracted_json", JSONB, nullable=True),               # null if extraction failed; never raw text
        sa.Column("confidence_json", JSONB, nullable=True),              # per-field confidence scores
        sa.Column("extractor_version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("extraction_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_document_extractions_document_id", "document_extractions", ["document_id"])

    # --- document_embeddings (chunk-level vectors for NON-POLICY evidence docs) ---
    # This is what the Rejection Decoder's evidence-retrieval step (Section E.4) queries.
    # Policy embeddings live separately in policy_clauses (migration 003).
    op.create_table(
        "document_embeddings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),              # chunk text (not full doc — chunked for RAG)
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    # Add pgvector column (must use raw SQL — SQLAlchemy migration DSL has no vector type)
    op.execute("ALTER TABLE document_embeddings ADD COLUMN embedding vector(1536)")
    op.create_index("ix_document_embeddings_document_id", "document_embeddings", ["document_id"])
    op.execute(
        "CREATE INDEX ix_document_embeddings_embedding_hnsw "
        "ON document_embeddings USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.drop_constraint("fk_claim_requirements_document_id", "claim_requirements", type_="foreignkey")
    op.drop_constraint("fk_policy_versions_document_id", "policy_versions", type_="foreignkey")
    op.drop_table("document_embeddings")
    op.drop_table("document_extractions")
    op.drop_table("document_versions")
    op.drop_table("documents")
