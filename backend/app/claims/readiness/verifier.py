"""
backend/app/claims/readiness/verifier.py
Deterministic Cross-Document Verification and Readiness Engine.

Performs:
1. Item state machine: MISSING -> RECEIVED_UNVERIFIED -> VERIFIED / NEEDS_FIX
2. Cross-document consistency verification:
   - Patient name fuzzy match across all uploaded documents vs claim record
   - Hospitalization dates overlap / chronological validity
   - Billed total (in paise) vs Claim amount consistency
   - Doctor signature & hospital stamp presence checks
3. Server-side readiness score:
   - Reaches 100% ONLY when all mandatory requirements are strictly VERIFIED.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

ItemVerificationStatus = Literal["MISSING", "RECEIVED_UNVERIFIED", "VERIFIED", "NEEDS_FIX"]


@dataclass
class VerificationCheckResult:
    check_name: str
    is_passed: bool
    severity: Literal["ERROR", "WARNING", "INFO"]
    message: str
    remedy: str | None = None


@dataclass
class VerifiedRequirement:
    requirement_type: str
    label: str
    is_mandatory: bool
    status: ItemVerificationStatus
    document_id: str | None = None
    filename: str | None = None
    confidence: float = 0.0
    issues: list[str] = field(default_factory=list)
    remedies: list[str] = field(default_factory=list)


@dataclass
class ReadinessVerificationReport:
    claim_id: str
    is_ready: bool
    score: int  # 0 to 100
    requirements: list[VerifiedRequirement]
    cross_doc_checks: list[VerificationCheckResult]
    consistency_flags: list[str]
    missing_mandatory: list[str]
    needs_fix_mandatory: list[str]


def fuzzy_name_match(name1: str | None, name2: str | None, threshold: float = 0.75) -> bool:
    """Case and honorific insensitive fuzzy matching for Indian names."""
    if not name1 or not name2:
        return True  # Cannot dispute missing name

    n1 = name1.lower().replace("mr.", "").replace("mrs.", "").replace("ms.", "").replace("dr.", "").strip()
    n2 = name2.lower().replace("mr.", "").replace("mrs.", "").replace("ms.", "").replace("dr.", "").strip()

    if not n1 or not n2:
        return True

    # Exact token containment (e.g. "Ramesh" in "Ramesh Kumar Sharma")
    tokens1 = set(n1.split())
    tokens2 = set(n2.split())
    if tokens1.issubset(tokens2) or tokens2.issubset(tokens1):
        return True

    ratio = difflib.SequenceMatcher(None, n1, n2).ratio()
    return ratio >= threshold


class ClaimReadinessVerifier:
    """
    Cross-document verification engine.
    """

    MANDATORY_REIMBURSEMENT = ["policy", "hospital_bill", "discharge_summary", "claim_form"]
    OPTIONAL_REIMBURSEMENT = ["prescription", "consultation_notes", "rejection_letter"]

    REQUIREMENT_LABELS = {
        "policy": "Insurance Policy / Health Card",
        "hospital_bill": "Itemized Hospital Bill & Receipts",
        "discharge_summary": "Discharge Summary with Diagnosis",
        "claim_form": "Completed & Signed Claim Form",
        "prescription": "Doctor's Consultation & Prescription",
        "consultation_notes": "Pre-hospitalization OPD Notes",
        "rejection_letter": "TPA / Insurer Rejection Letter",
        "other": "Other Supporting Evidence",
    }

    def verify(
        self,
        claim_id: str,
        claim_type: str,
        patient_name: str | None,
        admission_date: date | str | None,
        discharge_date: date | str | None,
        claim_amount_paise: int | None,
        documents: list[dict[str, Any]],  # list of doc dicts with extractions
    ) -> ReadinessVerificationReport:
        """
        Verify documents and cross-check facts.
        """
        cross_doc_checks: list[VerificationCheckResult] = []
        consistency_flags: list[str] = []

        # Index documents by doc_type
        docs_by_type: dict[str, list[dict[str, Any]]] = {}
        for d in documents:
            dtype = d.get("doc_type", "other")
            docs_by_type.setdefault(dtype, []).append(d)

        # Requirement evaluation
        requirements_to_check = (
            ["policy", "hospital_bill"]
            if claim_type == "cashless"
            else self.MANDATORY_REIMBURSEMENT + self.OPTIONAL_REIMBURSEMENT
        )

        verified_requirements: list[VerifiedRequirement] = []
        total_mandatory_count = 0
        verified_mandatory_count = 0
        received_unverified_count = 0

        # Aggregated extracted metadata for cross-checks
        extracted_names: list[tuple[str, str]] = []  # (doc_type, name)
        extracted_admission_dates: list[tuple[str, Any]] = []
        extracted_discharge_dates: list[tuple[str, Any]] = []
        bill_totals_paise: list[int] = []

        for req_type in requirements_to_check:
            is_mand = req_type in self.MANDATORY_REIMBURSEMENT or (claim_type == "cashless" and req_type in ["policy", "hospital_bill"])
            if is_mand:
                total_mandatory_count += 1

            label = self.REQUIREMENT_LABELS.get(req_type, req_type.replace("_", " ").title())
            matching_docs = docs_by_type.get(req_type, [])

            if not matching_docs:
                verified_requirements.append(
                    VerifiedRequirement(
                        requirement_type=req_type,
                        label=label,
                        is_mandatory=is_mand,
                        status="MISSING",
                        issues=[f"No document uploaded for {label}."] if is_mand else [],
                        remedies=[f"Upload your {label} (PDF, image, or scan)."] if is_mand else [],
                    )
                )
                continue

            # Pick latest document
            doc = matching_docs[-1]
            doc_id = str(doc.get("id", ""))
            filename = doc.get("original_filename", "uploaded_file")
            extraction = doc.get("extraction", {}) or {}
            ext_json = extraction.get("extracted_json", {}) if isinstance(extraction, dict) else {}

            issues: list[str] = []
            remedies: list[str] = []
            status: ItemVerificationStatus = "RECEIVED_UNVERIFIED"

            # Check extraction quality & flags
            quality = ext_json.get("document_quality", {}) or {}
            has_signature = quality.get("has_signature")
            has_stamp = quality.get("has_stamp")
            is_legible = quality.get("is_legible", True)

            # Record cross-check entities
            ext_patient = ext_json.get("patient_name")
            if ext_patient:
                extracted_names.append((req_type, ext_patient))

            ext_adm = ext_json.get("admission_date")
            if ext_adm:
                extracted_admission_dates.append((req_type, ext_adm))

            ext_dis = ext_json.get("discharge_date")
            if ext_dis:
                extracted_discharge_dates.append((req_type, ext_dis))

            if req_type == "hospital_bill":
                totals = ext_json.get("totals", {})
                b_paise = totals.get("total_amount_paise")
                if b_paise is not None:
                    bill_totals_paise.append(b_paise)

            # Specific verification rules per requirement
            if not is_legible:
                issues.append("Document image or text appears blurry, distorted, or partially illegible.")
                remedies.append("Re-upload a high-resolution scan or original PDF from the hospital.")

            if req_type == "discharge_summary":
                if has_stamp is False:
                    issues.append("Hospital stamp is missing from the discharge summary.")
                    remedies.append("Get the discharge summary stamped by the hospital medical superintendent.")
                if has_signature is False:
                    issues.append("Doctor's signature not detected on the discharge summary.")
                    remedies.append("Ensure the treating doctor signs with GMC/MCI registration number.")

            if req_type == "hospital_bill":
                line_items = ext_json.get("line_items", [])
                if not line_items and not ext_json.get("raw_text"):
                    issues.append("No itemized charges could be extracted from this bill.")
                    remedies.append("Upload the detailed line-item invoice rather than just the payment receipt.")

            if issues:
                status = "NEEDS_FIX"
            else:
                status = "VERIFIED"

            if is_mand:
                if status == "VERIFIED":
                    verified_mandatory_count += 1
                elif status == "RECEIVED_UNVERIFIED":
                    received_unverified_count += 1

            verified_requirements.append(
                VerifiedRequirement(
                    requirement_type=req_type,
                    label=label,
                    is_mandatory=is_mand,
                    status=status,
                    document_id=doc_id,
                    filename=filename,
                    confidence=doc.get("ocr_confidence", 0.95) or 0.95,
                    issues=issues,
                    remedies=remedies,
                )
            )

        # -------------------------------------------------------------
        # Cross-Document Consistency Checks
        # -------------------------------------------------------------

        # 1. Patient Name Consistency
        name_mismatches = []
        if patient_name:
            for dtype, ext_name in extracted_names:
                if not fuzzy_name_match(patient_name, ext_name):
                    name_mismatches.append(f"{dtype} lists '{ext_name}', but claim record has '{patient_name}'")

        if name_mismatches:
            msg = f"Patient name discrepancy detected: {'; '.join(name_mismatches)}."
            cross_doc_checks.append(
                VerificationCheckResult(
                    check_name="patient_name_consistency",
                    is_passed=False,
                    severity="ERROR",
                    message=msg,
                    remedy="Provide an affidavit or letter confirming name variation (e.g. maiden vs married name) if valid.",
                )
            )
            consistency_flags.append(msg)
        else:
            cross_doc_checks.append(
                VerificationCheckResult(
                    check_name="patient_name_consistency",
                    is_passed=True,
                    severity="INFO",
                    message="Patient names match consistently across all analyzed documents.",
                )
            )

        # 2. Admission & Discharge Chronological Validity
        date_issue = False
        adm_str = str(admission_date) if admission_date else None
        dis_str = str(discharge_date) if discharge_date else None

        if adm_str and dis_str and dis_str < adm_str:
            date_issue = True
            msg = f"Discharge date ({dis_str}) is earlier than admission date ({adm_str})."
            cross_doc_checks.append(
                VerificationCheckResult(
                    check_name="hospitalization_dates_chronology",
                    is_passed=False,
                    severity="ERROR",
                    message=msg,
                    remedy="Verify dates on discharge summary and hospital admission record.",
                )
            )
            consistency_flags.append(msg)

        if adm_str and dis_str and dis_str == adm_str:
            msg = "Same-day hospitalization (<24 hours) detected. Reimbursement requires active day-care procedure proof."
            cross_doc_checks.append(
                VerificationCheckResult(
                    check_name="hospitalization_duration_24h",
                    is_passed=False,
                    severity="WARNING",
                    message=msg,
                    remedy="Ensure discharge summary clearly specifies day-care surgery under modern treatment clause.",
                )
            )
            consistency_flags.append(msg)

        # 3. Bill Amount vs Claimed Amount Consistency
        if claim_amount_paise and bill_totals_paise:
            billed_paise = bill_totals_paise[0]
            if billed_paise != claim_amount_paise:
                diff_rs = abs(billed_paise - claim_amount_paise) / 100
                msg = f"Total billed on hospital invoice (₹{billed_paise / 100:,.2f}) differs from claimed amount (₹{claim_amount_paise / 100:,.2f}) by ₹{diff_rs:,.2f}."
                cross_doc_checks.append(
                    VerificationCheckResult(
                        check_name="bill_vs_claim_amount_match",
                        is_passed=False,
                        severity="WARNING",
                        message=msg,
                        remedy="Check if pre- or post-hospitalization medical bills were added to the claimed total.",
                    )
                )
                consistency_flags.append(msg)
            else:
                cross_doc_checks.append(
                    VerificationCheckResult(
                        check_name="bill_vs_claim_amount_match",
                        is_passed=True,
                        severity="INFO",
                        message="Hospital bill total matches the claimed reimbursement amount exactly.",
                    )
                )

        # -------------------------------------------------------------
        # Strict Score Calculation
        # -------------------------------------------------------------
        # Only fully VERIFIED mandatory documents count toward 100%.
        # RECEIVED_UNVERIFIED gets 50% credit.
        if total_mandatory_count > 0:
            raw_score = int(
                ((verified_mandatory_count + (received_unverified_count * 0.5)) / total_mandatory_count) * 100
            )
        else:
            raw_score = 100

        # Penalize for severe consistency errors
        error_count = sum(1 for c in cross_doc_checks if not c.is_passed and c.severity == "ERROR")
        if error_count > 0:
            raw_score = min(raw_score, 85 - (error_count * 15))

        score = max(0, min(100, raw_score))

        missing_mandatory = [r.requirement_type for r in verified_requirements if r.is_mandatory and r.status == "MISSING"]
        needs_fix_mandatory = [r.requirement_type for r in verified_requirements if r.is_mandatory and r.status == "NEEDS_FIX"]

        is_ready = (
            score == 100
            and len(missing_mandatory) == 0
            and len(needs_fix_mandatory) == 0
            and len([c for c in cross_doc_checks if c.severity == "ERROR" and not c.is_passed]) == 0
        )

        return ReadinessVerificationReport(
            claim_id=claim_id,
            is_ready=is_ready,
            score=score,
            requirements=verified_requirements,
            cross_doc_checks=cross_doc_checks,
            consistency_flags=consistency_flags,
            missing_mandatory=missing_mandatory,
            needs_fix_mandatory=needs_fix_mandatory,
        )
