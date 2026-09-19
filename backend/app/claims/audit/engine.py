"""
backend/app/claims/audit/engine.py
Deterministic IRDAI-compliant Hospital Bill Audit Engine.

Evaluates hospital bill line-items, classifies them according to IRDAI Master Circular
exclusions (Annexure I, List I - Items for which no admission is made), detects ambiguous
items needing review, and calculates an indicative payable estimate through an auditable
waterfall structure.

CRITICAL INVARIANTS:
1. All monetary values are handled strictly in integer paise (1 INR = 100 paise).
2. The payable figure MUST ALWAYS be labeled:
   "Indicative payable estimate — subject to your insurer's assessment".
   Never use "Expected Settlement".
3. No LLM hallucination: classifications and waterfall calculations are 100% deterministic.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from app.documents.parsers import parse_currency_to_paise
from app.core.logging import get_logger

logger = get_logger(__name__)

RULES_FILE_PATH = Path(__file__).parent / "rules.json"

ClassificationType = Literal["PAYABLE_MEDICAL", "COMMONLY_NON_PAYABLE", "NEEDS_REVIEW"]
WaterfallStatus = Literal["APPLIED", "NOT_APPLICABLE", "UNKNOWN"]

MANDATORY_ESTIMATE_LABEL = "Indicative payable estimate — subject to your insurer's assessment"


@dataclass
class AuditedLineItem:
    item_id: str
    description: str
    amount_paise: int
    classification: ClassificationType
    category: str | None = None
    rule_id: str | None = None
    guideline_reference: str | None = None
    explanation: str | None = None
    patient_remedy: str | None = None


@dataclass
class WaterfallStep:
    step_key: str
    label: str
    amount_paise: int
    status: WaterfallStatus
    notes: str | None = None


@dataclass
class BillAuditReport:
    rules_version: str
    gross_billed_paise: int
    commonly_non_payable_paise: int
    needs_review_paise: int
    payable_medical_paise: int
    room_rent_deduction_paise: int
    room_rent_status: WaterfallStatus
    copay_deduction_paise: int
    copay_status: WaterfallStatus
    indicative_payable_paise: int
    estimate_label: str
    waterfall: list[WaterfallStep]
    items: list[AuditedLineItem]
    non_payable_count: int
    needs_review_count: int
    payable_medical_count: int


class BillAuditEngine:
    """
    Deterministic rule-based auditor for Indian hospital bills.
    """

    def __init__(self, rules_path: Path = RULES_FILE_PATH):
        self.rules_path = rules_path
        self._load_rules()

    def _load_rules(self) -> None:
        if not self.rules_path.exists():
            raise FileNotFoundError(f"Audit rules file not found: {self.rules_path}")
        with open(self.rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.version = data.get("version", "2024.1")
        self.rules = data.get("rules", [])
        self.review_triggers = [kw.lower() for kw in data.get("review_triggers", [])]

    def classify_item(self, description: str, amount_paise: int, declared_category: str | None = None) -> AuditedLineItem:
        """
        Classifies a single line item into:
        - COMMONLY_NON_PAYABLE (matches IRDAI non-payable rules)
        - NEEDS_REVIEW (ambiguous description or zero/negative amount)
        - PAYABLE_MEDICAL (standard medical care, pharmacy, doctor, surgery)
        """
        desc_clean = (description or "").strip()
        desc_lower = desc_clean.lower()

        # 1. Check for COMMONLY_NON_PAYABLE matches
        for rule in self.rules:
            keywords = [k.lower() for k in rule.get("keywords", [])]
            for kw in keywords:
                if kw in desc_lower:
                    return AuditedLineItem(
                        item_id=f"ITEM-{abs(hash((desc_clean, amount_paise))) % 1000000:06d}",
                        description=desc_clean,
                        amount_paise=amount_paise,
                        classification="COMMONLY_NON_PAYABLE",
                        category=rule.get("category"),
                        rule_id=rule.get("rule_id"),
                        guideline_reference=rule.get("guideline_reference"),
                        explanation=rule.get("explanation"),
                        patient_remedy=rule.get("patient_remedy"),
                    )

        # 2. Check for NEEDS_REVIEW triggers
        is_review_trigger = any(trigger in desc_lower for trigger in self.review_triggers)
        if is_review_trigger or len(desc_clean) < 3 or amount_paise <= 0:
            return AuditedLineItem(
                item_id=f"ITEM-{abs(hash((desc_clean, amount_paise))) % 1000000:06d}",
                description=desc_clean,
                amount_paise=amount_paise,
                classification="NEEDS_REVIEW",
                category="Ambiguous / Unspecified",
                rule_id="REVIEW-AMBIGUOUS",
                guideline_reference="IRDAI Claim Scrutiny Best Practice",
                explanation="The description is generic or ambiguous. Insurers require an itemized breakdown before adjudicating payment.",
                patient_remedy="Request an itemized breakdown or doctor bill specification from the hospital billing desk.",
            )

        # 3. Default: PAYABLE_MEDICAL
        return AuditedLineItem(
            item_id=f"ITEM-{abs(hash((desc_clean, amount_paise))) % 1000000:06d}",
            description=desc_clean,
            amount_paise=amount_paise,
            classification="PAYABLE_MEDICAL",
            category=declared_category or "Medical Expense",
            explanation="Standard admissible medical treatment expense under health insurance coverage.",
        )

    def audit_bill(
        self,
        raw_items: list[dict[str, Any]],
        sum_insured_paise: int | None = None,
        policy_room_rent_limit_daily_paise: int | None = None,
        actual_room_rent_daily_paise: int | None = None,
        stay_days: int = 1,
        copay_percentage: int | None = None,
    ) -> BillAuditReport:
        """
        Audits a list of items and generates the full waterfall and audit report.

        raw_items: list of dicts with at least:
          - "description": str
          - "amount": int (paise) or str/float representing currency
        """
        audited_items: list[AuditedLineItem] = []
        gross_billed_paise = 0
        commonly_non_payable_paise = 0
        needs_review_paise = 0
        payable_medical_paise = 0

        for raw in raw_items:
            desc = str(raw.get("description", raw.get("item_name", "Unspecified")))
            amt_raw = raw.get("amount", raw.get("amount_paise", 0))

            if isinstance(amt_raw, int) and "amount_paise" in raw:
                amt_paise = amt_raw
            elif isinstance(amt_raw, int):
                # If already an integer paise
                amt_paise = amt_raw
            else:
                amt_paise = parse_currency_to_paise(amt_raw)

            category = raw.get("category")
            item = self.classify_item(desc, amt_paise, declared_category=category)
            audited_items.append(item)

            gross_billed_paise += item.amount_paise
            if item.classification == "COMMONLY_NON_PAYABLE":
                commonly_non_payable_paise += item.amount_paise
            elif item.classification == "NEEDS_REVIEW":
                needs_review_paise += item.amount_paise
            else:
                payable_medical_paise += item.amount_paise

        # Subtotal after non-payables
        subtotal_after_np_paise = max(0, gross_billed_paise - commonly_non_payable_paise)

        # Waterfall steps
        waterfall: list[WaterfallStep] = [
            WaterfallStep(
                step_key="gross_billed",
                label="Gross Hospital Bill Amount",
                amount_paise=gross_billed_paise,
                status="APPLIED",
                notes=f"Total of {len(audited_items)} line items submitted.",
            ),
            WaterfallStep(
                step_key="non_payable_deductions",
                label="Less: Commonly Non-Payable Items (IRDAI Exclusions)",
                amount_paise=commonly_non_payable_paise,
                status="APPLIED" if commonly_non_payable_paise > 0 else "NOT_APPLICABLE",
                notes="Consumables, PPE kits, registration fees, and administrative charges excluded per IRDAI List I.",
            ),
        ]

        # Room Rent Proportionate Adjustment
        room_rent_deduction_paise = 0
        room_rent_status: WaterfallStatus = "NOT_APPLICABLE"
        room_rent_notes = "No room rent capping applied or room rent within policy limit."

        if policy_room_rent_limit_daily_paise is not None and actual_room_rent_daily_paise is not None:
            if actual_room_rent_daily_paise > policy_room_rent_limit_daily_paise and actual_room_rent_daily_paise > 0:
                room_rent_status = "APPLIED"
                # Room rent proportionate deduction calculation:
                # Excess per day = actual - limit
                excess_room_rent = (actual_room_rent_daily_paise - policy_room_rent_limit_daily_paise) * max(1, stay_days)
                # In India, proportionate clause deduction:
                # Associated medical charges are adjusted by (limit / actual)
                proportion_payable = policy_room_rent_limit_daily_paise / actual_room_rent_daily_paise
                # Approximate proportionate deduction: room rent excess + proportion reduction on other expenses
                # To be conservative and clear: deduct excess room rent
                room_rent_deduction_paise = min(excess_room_rent, subtotal_after_np_paise)
                room_rent_notes = (
                    f"Room rent of ₹{actual_room_rent_daily_paise / 100:,.2f}/day exceeds policy limit "
                    f"of ₹{policy_room_rent_limit_daily_paise / 100:,.2f}/day for {stay_days} day(s). "
                    "Proportionate deduction applied on room tariff excess."
                )
            else:
                room_rent_status = "NOT_APPLICABLE"
                room_rent_notes = "Room tariff is within policy sub-limits; no proportionate penalty applied."
        elif policy_room_rent_limit_daily_paise is None and actual_room_rent_daily_paise is None:
            room_rent_status = "UNKNOWN"
            room_rent_notes = "Room rent limit not specified in policy; check if 1% sum-insured room capping applies."

        waterfall.append(
            WaterfallStep(
                step_key="room_rent_adjustment",
                label="Less: Room Rent Proportionate Adjustment",
                amount_paise=room_rent_deduction_paise,
                status=room_rent_status,
                notes=room_rent_notes,
            )
        )

        subtotal_after_rr_paise = max(0, subtotal_after_np_paise - room_rent_deduction_paise)

        # Co-pay deduction
        copay_deduction_paise = 0
        copay_status: WaterfallStatus = "NOT_APPLICABLE"
        copay_notes = "No policy co-payment applies."

        if copay_percentage is not None:
            if copay_percentage > 0:
                copay_status = "APPLIED"
                copay_deduction_paise = (subtotal_after_rr_paise * copay_percentage) // 100
                copay_notes = f"{copay_percentage}% co-pay clause applied per policy terms."
            else:
                copay_status = "NOT_APPLICABLE"
                copay_notes = "Zero co-pay policy."
        else:
            copay_status = "UNKNOWN"
            copay_notes = "Co-pay clause unknown. If policy has a senior citizen or zone co-pay, an additional 10-20% may be deducted."

        waterfall.append(
            WaterfallStep(
                step_key="copay_deduction",
                label=f"Less: Policy Co-Payment ({copay_percentage or 0}%)",
                amount_paise=copay_deduction_paise,
                status=copay_status,
                notes=copay_notes,
            )
        )

        # Indicative payable
        indicative_payable_paise = max(0, subtotal_after_rr_paise - copay_deduction_paise)

        # Clamp by sum insured if provided
        if sum_insured_paise is not None and indicative_payable_paise > sum_insured_paise:
            capped_diff = indicative_payable_paise - sum_insured_paise
            waterfall.append(
                WaterfallStep(
                    step_key="sum_insured_capping",
                    label="Less: Capping to Policy Sum Insured",
                    amount_paise=capped_diff,
                    status="APPLIED",
                    notes=f"Payable estimate capped at maximum policy sum insured (₹{sum_insured_paise / 100:,.2f}).",
                )
            )
            indicative_payable_paise = sum_insured_paise

        waterfall.append(
            WaterfallStep(
                step_key="indicative_payable_estimate",
                label=MANDATORY_ESTIMATE_LABEL,
                amount_paise=indicative_payable_paise,
                status="APPLIED",
                notes="Subject to final verification of original physical documents and medical officer review.",
            )
        )

        return BillAuditReport(
            rules_version=self.version,
            gross_billed_paise=gross_billed_paise,
            commonly_non_payable_paise=commonly_non_payable_paise,
            needs_review_paise=needs_review_paise,
            payable_medical_paise=payable_medical_paise,
            room_rent_deduction_paise=room_rent_deduction_paise,
            room_rent_status=room_rent_status,
            copay_deduction_paise=copay_deduction_paise,
            copay_status=copay_status,
            indicative_payable_paise=indicative_payable_paise,
            estimate_label=MANDATORY_ESTIMATE_LABEL,
            waterfall=waterfall,
            items=audited_items,
            non_payable_count=sum(1 for i in audited_items if i.classification == "COMMONLY_NON_PAYABLE"),
            needs_review_count=sum(1 for i in audited_items if i.classification == "NEEDS_REVIEW"),
            payable_medical_count=sum(1 for i in audited_items if i.classification == "PAYABLE_MEDICAL"),
        )
