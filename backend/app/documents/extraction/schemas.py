"""
backend/app/documents/extraction/schemas.py
Pydantic schemas for structured document extraction from LLM/multimodal OCR.
"""
from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class DocumentTypeEnum(str, Enum):
    POLICY = "POLICY"
    HOSPITAL_BILL = "HOSPITAL_BILL"
    PHARMACY_BILL = "PHARMACY_BILL"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    INDOOR_CASE_PAPERS = "INDOOR_CASE_PAPERS"
    PRESCRIPTION = "PRESCRIPTION"
    INVESTIGATION_REPORT = "INVESTIGATION_REPORT"
    CLAIM_FORM = "CLAIM_FORM"
    ID_PROOF = "ID_PROOF"
    REJECTION_LETTER = "REJECTION_LETTER"
    OTHER = "OTHER"


class QualityIssueEnum(str, Enum):
    BLURRY = "BLURRY"
    CUT_OFF = "CUT_OFF"
    MISSING_PAGE = "MISSING_PAGE"
    LOW_CONTRAST = "LOW_CONTRAST"
    NO_SIGNATURE = "NO_SIGNATURE"
    NO_STAMP = "NO_STAMP"


class ExtractedLineItem(BaseModel):
    id: str = Field(description="Unique line item key, e.g. item-001")
    description: str = Field(description="Exact line item description from document")
    quantity: int = Field(default=1, description="Billed quantity or units")
    rate_paise: int = Field(default=0, description="Unit rate in integer paise")
    amount_paise: int = Field(description="Line total amount in integer paise (1 Rupee = 100 Paise)")
    raw_category: str | None = Field(default=None, description="Original bill category if stated")
    page: int | None = Field(default=1, description="Page number where item was found")
    source_ref: str | None = Field(default=None, description="Line/section reference in document")


class TotalsBreakdown(BaseModel):
    gross_paise: int | None = Field(default=None, description="Gross total in paise")
    discount_paise: int | None = Field(default=None, description="Discount in paise")
    tax_paise: int | None = Field(default=None, description="Taxes in paise")
    advance_paid_paise: int | None = Field(default=None, description="Advance paid in paise")
    patient_payable_paise: int | None = Field(default=None, description="Patient payable amount in paise")


class DocumentQuality(BaseModel):
    pages: int = Field(default=1, description="Total pages analyzed")
    legible: bool = Field(default=True, description="Whether document is legible")
    issues: list[QualityIssueEnum] = Field(default_factory=list, description="Quality defects identified")


class ExtractedDocument(BaseModel):
    doc_type: DocumentTypeEnum = Field(description="Classified document type")
    doc_type_confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Classification confidence")
    patient_name: str | None = Field(default=None, description="Extracted patient name")
    policyholder_name: str | None = Field(default=None, description="Extracted policyholder name")
    hospital_name: str | None = Field(default=None, description="Hospital or healthcare provider name")
    hospital_city: str | None = Field(default=None, description="City where hospital is located")
    admission_date: str | None = Field(default=None, description="Hospitalization admission date (YYYY-MM-DD or standard format)")
    discharge_date: str | None = Field(default=None, description="Hospitalization discharge date")
    diagnosis_text: str | None = Field(default=None, description="Clinical diagnosis or primary ailment")
    claim_reference: str | None = Field(default=None, description="Claim reference number if mentioned")
    policy_number_last4: str | None = Field(default=None, description="Last 4 digits of policy number for safe logging")
    line_items: list[ExtractedLineItem] = Field(default_factory=list, description="Itemized bill entries")
    totals: TotalsBreakdown = Field(default_factory=TotalsBreakdown, description="Stated totals summary")
    quality: DocumentQuality = Field(default_factory=DocumentQuality, description="Document image and scan quality audit")
    extraction_warnings: list[str] = Field(default_factory=list, description="Extraction warnings or reconciliation discrepancies")
