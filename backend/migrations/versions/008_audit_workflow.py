"""
migrations/versions/008_audit_workflow.py
Creates: audit_logs (insert-only), workflow_runs tables.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- audit_logs (immutable — no UPDATE/DELETE, enforced by DB role grants in migration 010) ---
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        # actor_type: customer | support_admin | system | ai
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        # object_type: claim | document | policy | appeal_draft | consent | session | ...
        sa.Column("object_type", sa.String(50), nullable=True),
        sa.Column("object_id", sa.String(255), nullable=True),        # UUID as string (polymorphic)
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("workflow_run_id", UUID(as_uuid=True), nullable=True),
        # result: success | failure | blocked
        sa.Column("result", sa.String(20), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # No updated_at — this table is NEVER updated or deleted (enforced by DB role, migration 010)
    )
    op.create_index("ix_audit_logs_correlation_id", "audit_logs", ["correlation_id"])
    op.create_index("ix_audit_logs_object", "audit_logs", ["object_type", "object_id", "occurred_at"])
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor_type", "actor_id"])

    # --- workflow_runs (n8n execution tracking mirrored into Postgres) ---
    op.create_table(
        "workflow_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_name", sa.String(100), nullable=False),
        sa.Column("n8n_execution_id", sa.String(255), nullable=True),
        sa.Column("trigger_source", sa.String(50), nullable=True),     # webhook | schedule
        sa.Column("trigger_payload", JSONB, nullable=True),
        # status: running | success | failed | dead_letter
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_workflow_runs_name_status", "workflow_runs", ["workflow_name", "status"])
    op.create_index("ix_workflow_runs_n8n_id", "workflow_runs", ["n8n_execution_id"])


def downgrade() -> None:
    op.drop_table("workflow_runs")
    op.drop_table("audit_logs")
