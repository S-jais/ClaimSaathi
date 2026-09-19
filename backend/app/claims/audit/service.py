"""
backend/app/claims/audit/service.py
Service layer for hospital bill auditing.
Connects uploaded documents, line-item extractions, and the deterministic IRDAI engine.
"""
from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.claims.models import Claim, ClaimEvent
from app.documents.models import Document, DocumentExtraction
from app.claims.audit.engine import BillAuditEngine, BillAuditReport
from app.claims.schemas import BillAuditRequest
from app.core.logging import get_logger

logger = get_logger(__name__)

engine = BillAuditEngine()


SAMPLE_HOSPITAL_BILL_ITEMS: list[dict[str, Any]] = [
    {"description": "OT Surgeon Professional Fee", "amount_paise": 4500000, "category": "Doctor & Surgeon"},
    {"description": "Anesthetist Charges", "amount_paise": 1500000, "category": "Doctor & Surgeon"},
    {"description": "Operation Theatre Base Charges", "amount_paise": 2000000, "category": "Hospital Tariff"},
    {"description": "Sterile Nitrile Examination Gloves (10 prs)", "amount_paise": 65000, "category": "Consumables"},
    {"description": "Staff COVID PPE Kit + Face Shields", "amount_paise": 180000, "category": "Consumables"},
    {"description": "Hospital Bio-Medical Waste Management", "amount_paise": 85000, "category": "Hospital Overhead"},
    {"description": "Patient Registration & MRD Record Fee", "amount_paise": 50000, "category": "Administrative"},
    {"description": "Inj. Pantoprazole 40mg IV", "amount_paise": 32000, "category": "Pharmacy"},
    {"description": "Attendant Food & Beverage Charges", "amount_paise": 95000, "category": "Attendant Charges"},
    {"description": "Miscellaneous Consumables Kit", "amount_paise": 250000, "category": "Consumables"},
]


async def audit_claim_bill(
    db: AsyncSession,
    claim_id: uuid.UUID,
    request: BillAuditRequest | None = None,
) -> BillAuditReport:
    """
    Audits hospital bill for a claim using deterministic IRDAI rules.
    """
    # 1. Fetch claim
    stmt = select(Claim).where(Claim.id == claim_id)
    res = await db.execute(stmt)
    claim = res.scalar_one_or_none()
    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    items_to_audit: list[dict[str, Any]] = []

    # 2. Check if custom items were submitted in the request
    if request and request.items:
        items_to_audit = request.items
    else:
        # Check if an uploaded hospital bill document exists with extraction
        doc_stmt = (
            select(Document)
            .where(
                Document.claim_id == claim_id,
                Document.doc_type == "hospital_bill",
                Document.deleted_at.is_(None),
            )
            .order_by(Document.created_at.desc())
        )
        doc_res = await db.execute(doc_stmt)
        bill_doc = doc_res.scalars().first()

        if bill_doc:
            ext_stmt = (
                select(DocumentExtraction)
                .where(DocumentExtraction.document_id == bill_doc.id)
                .order_by(DocumentExtraction.created_at.desc())
            )
            ext_res = await db.execute(ext_stmt)
            extraction = ext_res.scalars().first()
            if extraction and extraction.extracted_json:
                ext_items = extraction.extracted_json.get("line_items", [])
                if ext_items:
                    items_to_audit = ext_items

    # 3. Fallback to sample items if no bill is uploaded yet so user can test immediately
    if not items_to_audit:
        items_to_audit = SAMPLE_HOSPITAL_BILL_ITEMS

    # 4. Parameters
    sum_insured_paise = 50000000  # ₹5,00,000 standard
    copay_pct = request.copay_percentage if request else None
    room_rent_limit = request.policy_room_rent_limit_daily_paise if request else None
    actual_room_rent = request.actual_room_rent_daily_paise if request else None
    stay_days = request.stay_days if request else 1

    # 5. Run audit
    report = engine.audit_bill(
        raw_items=items_to_audit,
        sum_insured_paise=sum_insured_paise,
        policy_room_rent_limit_daily_paise=room_rent_limit,
        actual_room_rent_daily_paise=actual_room_rent,
        stay_days=stay_days,
        copay_percentage=copay_pct,
    )

    # 6. Record timeline event
    event = ClaimEvent(
        claim_id=claim.id,
        event_type="bill_audited",
        actor_type="system",
        metadata_json={
            "gross_billed_paise": report.gross_billed_paise,
            "indicative_payable_paise": report.indicative_payable_paise,
            "non_payable_count": report.non_payable_count,
            "rules_version": report.rules_version,
        },
    )
    db.add(event)
    await db.commit()

    return report
