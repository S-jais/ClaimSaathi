"""
scripts/seed_demo_data.py
Seeds the demo dataset (Siddhartha Jaiswal, CLM-20491) exactly as specified
in the master prompt Section 4.2.

Usage:
    python scripts/seed_demo_data.py

Requires: DATABASE_URL_SYNC env var (or .env file) pointing to a running DB
with all migrations applied (001–010).
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime, timezone

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL_SYNC = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://claimsaathi:claimsaathi_dev@localhost:5432/claimsaathi",
)
from app.core.security import hash_password


def seed():
    conn = psycopg2.connect(DATABASE_URL_SYNC)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("Seeding demo data...")

    # --- Demo user ---
    demo_user_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO users (id, email, full_name, password_hash, status, is_demo, created_at, updated_at)
        VALUES (%s, %s, %s, %s, 'active', true, NOW(), NOW())
        ON CONFLICT (email) DO NOTHING
        RETURNING id
    """, (demo_user_id, "siddhartha.jaiswal@demo.claimsaathi.in", "Siddhartha Jaiswal", hash_password("DemoPass@2026!")))
    row = cur.fetchone()
    if row:
        demo_user_id = row["id"]
    else:
        cur.execute("SELECT id FROM users WHERE email = %s", ("siddhartha.jaiswal@demo.claimsaathi.in",))
        demo_user_id = cur.fetchone()["id"]

    # Assign customer role
    cur.execute("SELECT id FROM roles WHERE name = 'customer'")
    role = cur.fetchone()
    if role:
        cur.execute("""
            INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (demo_user_id, role["id"]))

    # --- Demo policy ---
    policy_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO policies (id, user_id, insurer_name, policy_number, product_type,
            sum_insured, policy_start_date, policy_end_date, status, is_demo, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active', true, NOW(), NOW())
        ON CONFLICT DO NOTHING
    """, (
        policy_id, demo_user_id,
        "Star Health & Allied Insurance",
        "P/14/120/V01/2024/009823",
        "Individual Health Insurance",
        500000.00,
        date(2024, 4, 1),
        date(2025, 3, 31),
    ))

    # --- Demo claim: CLM-20491 ---
    claim_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO claims (
            id, user_id, policy_id, claim_reference, claim_type, status,
            claim_amount, hospital_name, admission_date, discharge_date, patient_name,
            diagnosis, readiness_score, is_demo, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, NOW(), NOW())
        ON CONFLICT DO NOTHING
    """, (
        claim_id, demo_user_id, policy_id,
        "CLM-20491", "reimbursement", "rejected",
        184500.00,
        "Apollo Hospitals, Chennai",
        date(2026, 1, 10),
        date(2026, 1, 14),
        "Siddhartha Jaiswal",
        "Acute Appendicitis (K35.80) — Laparoscopic Appendectomy",
        75,  # 75% — missing consultation_notes
    ))

    # --- Documents (all present except consultation_notes — the demo gap) ---
    doc_types = [
        ("policy", "completed", "policy_siddhartha_star_health.pdf"),
        ("claim_form", "completed", "claim_form_signed.pdf"),
        ("hospital_bill", "completed", "apollo_hospitals_bill_184500.pdf"),
        ("discharge_summary", "completed", "discharge_summary_jan14.pdf"),
        ("prescription", "completed", "prescription_dr_sharma.pdf"),
        ("rejection_letter", "completed", "rejection_letter_clm20491.pdf"),
        # consultation_notes deliberately ABSENT — the demo gap
    ]

    for doc_type, status, filename in doc_types:
        doc_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO documents (
                id, user_id, claim_id, doc_type, status, original_filename,
                size_bytes, mime_type, is_demo, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, NOW(), NOW())
        """, (
            doc_id, demo_user_id, claim_id,
            doc_type, status, filename,
            512000, "application/pdf",
        ))

    # --- Claim events ---
    events = [
        ("claim_created", "customer", str(demo_user_id), {"claim_type": "reimbursement"}),
        ("document_uploaded", "customer", str(demo_user_id), {"doc_type": "policy"}),
        ("document_uploaded", "customer", str(demo_user_id), {"doc_type": "hospital_bill"}),
        ("document_uploaded", "customer", str(demo_user_id), {"doc_type": "discharge_summary"}),
        ("claim_submitted", "customer", str(demo_user_id), {}),
        ("claim_rejected", "system", "insurer", {"reason": "Insufficient documentation — consultation notes missing", "tpa": "Medi Assist"}),
    ]
    import json
    for event_type, actor_type, actor_id, metadata in events:
        cur.execute("""
            INSERT INTO claim_events (id, claim_id, event_type, actor_type, actor_id, metadata_json, occurred_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (str(uuid.uuid4()), claim_id, event_type, actor_type, actor_id, json.dumps(metadata)))

    # --- Demo consent (granted for all purposes) ---
    for purpose in ["document_processing", "ai_analysis", "notifications"]:
        cur.execute("""
            INSERT INTO consents (id, user_id, purpose, consent_text_version, granted_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW(), NOW())
        """, (str(uuid.uuid4()), demo_user_id, purpose, "1.0"))

    conn.commit()
    cur.close()
    conn.close()

    print(f"""
✅ Demo data seeded successfully!

   User:     Siddhartha Jaiswal <siddhartha.jaiswal@demo.claimsaathi.in>
   Password: DemoPass@2026!
   Claim:    CLM-20491 — ₹1,84,500 (Apollo Hospitals, Chennai)
   Status:   Rejected
   Gap:      consultation_notes (deliberately absent — demo scenario)
   Policy:   ₹5,00,000 sum insured (Star Health, P/14/120/V01/2024/009823)
""")


if __name__ == "__main__":
    seed()
