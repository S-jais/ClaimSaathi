"""
migrations/versions/010_db_role_grants.py
Enforces audit_logs immutability at the database-role level.
The application's DB role (app_role) has NO UPDATE or DELETE privileges
on audit_logs. Only INSERT is permitted.
This is tested explicitly in tests/security/test_audit_log_immutable.py.
Runs LAST (after all tables exist).
"""
from __future__ import annotations

from alembic import op
from app.core.config import get_settings

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    settings = get_settings()
    app_role = settings.DB_APP_ROLE

    # Create the restricted application role if it doesn't exist
    op.execute(f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{app_role}') THEN CREATE ROLE {app_role} LOGIN PASSWORD '{settings.DB_APP_ROLE_PASSWORD}'; END IF; END $$")

    # Grant standard privileges on all tables
    op.execute(f"GRANT CONNECT ON DATABASE claimsaathi TO {app_role}")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {app_role}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {app_role}")
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {app_role}")

    # REVOKE UPDATE and DELETE on audit_logs — INSERT only
    op.execute(f"REVOKE UPDATE, DELETE ON audit_logs FROM {app_role}")

    # Ensure future tables created inherit the same default privileges
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {app_role}")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {app_role}")


def downgrade() -> None:
    # Restore UPDATE/DELETE on audit_logs (use only in dev; never in production)
    settings = get_settings()
    app_role = settings.DB_APP_ROLE
    op.execute(f"GRANT UPDATE, DELETE ON audit_logs TO {app_role}")
