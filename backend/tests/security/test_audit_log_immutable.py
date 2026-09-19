"""
tests/security/test_audit_log_immutable.py
Verifies that audit_logs cannot be updated or deleted by the app_role.
This is a REQUIRED acceptance criterion from Section J.
Uses a real (test) database connection via the app_role.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import psycopg2
import pytest

DB_URL_SYNC = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://claimsaathi:claimsaathi_dev@localhost:5432/claimsaathi",
)
APP_ROLE = os.environ.get("DB_APP_ROLE", "app_role")
APP_ROLE_PASSWORD = os.environ.get("DB_APP_ROLE_PASSWORD", "changeme")


def is_postgres_available() -> bool:
    try:
        conn = psycopg2.connect(DB_URL_SYNC, connect_timeout=1)
        conn.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not is_postgres_available(),
    reason="PostgreSQL not running at localhost:5432 (requires docker-compose up)",
)


def get_app_role_conn():
    """Connect as the restricted app_role (not the superuser)."""
    # Parse and reconstruct with app_role credentials
    import re
    url = DB_URL_SYNC
    # Replace user:password with app_role credentials
    url = re.sub(r"://[^@]+@", f"://{APP_ROLE}:{APP_ROLE_PASSWORD}@", url)
    return psycopg2.connect(url)


def get_superuser_conn():
    """Connect as superuser to set up test data."""
    return psycopg2.connect(DB_URL_SYNC)


@pytest.fixture(scope="module")
def test_audit_log_id():
    """Insert a test audit_log row as superuser, return its ID."""
    conn = get_superuser_conn()
    try:
        cur = conn.cursor()
        test_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO audit_logs (id, actor_type, actor_id, action, object_type, object_id, result, occurred_at)
            VALUES (%s, 'system', 'test', 'test_immutability_check', 'test', 'test', 'success', %s)
            """,
            (test_id, datetime.now(timezone.utc)),
        )
        conn.commit()
        cur.close()
        return test_id
    finally:
        conn.close()


class TestAuditLogImmutability:
    def test_update_audit_log_as_app_role_fails(self, test_audit_log_id: str):
        """
        ACCEPTANCE CRITERION: audit_logs cannot be UPDATE'd by the app_role.
        Migration 010 REVOKES UPDATE on audit_logs from app_role.
        """
        conn = get_app_role_conn()
        try:
            cur = conn.cursor()
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(
                    "UPDATE audit_logs SET result = 'tampered' WHERE id = %s",
                    (test_audit_log_id,),
                )
                conn.commit()
        finally:
            conn.rollback()
            conn.close()

    def test_delete_audit_log_as_app_role_fails(self, test_audit_log_id: str):
        """
        ACCEPTANCE CRITERION: audit_logs cannot be DELETE'd by the app_role.
        """
        conn = get_app_role_conn()
        try:
            cur = conn.cursor()
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(
                    "DELETE FROM audit_logs WHERE id = %s",
                    (test_audit_log_id,),
                )
                conn.commit()
        finally:
            conn.rollback()
            conn.close()

    def test_insert_audit_log_as_app_role_succeeds(self):
        """
        Sanity check: app_role CAN insert to audit_logs (only INSERT is allowed).
        """
        conn = get_app_role_conn()
        try:
            cur = conn.cursor()
            test_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO audit_logs (id, actor_type, actor_id, action, result, occurred_at)
                VALUES (%s, 'system', 'test', 'test_insert', 'success', %s)
                """,
                (test_id, datetime.now(timezone.utc)),
            )
            conn.commit()
            cur.close()
        finally:
            conn.close()
