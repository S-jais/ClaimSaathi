"""
backend/tests/unit/test_document_parsers.py
Unit tests for deterministic document parsers and Indian currency normalization.
"""
import pytest
from app.documents.parsers import (
    FileValidationError,
    parse_currency_to_paise,
    format_paise_to_rupees,
    validate_file_bytes,
    parse_csv_bill,
    parse_txt_document,
)


def test_indian_currency_parsing():
    # Basic amounts
    assert parse_currency_to_paise("1,84,500.00") == 18450000
    assert parse_currency_to_paise("₹ 1,84,500") == 18450000
    assert parse_currency_to_paise("Rs. 45,000") == 4500000
    assert parse_currency_to_paise("INR 12,500.50") == 1250050

    # Negative accounting parentheses
    assert parse_currency_to_paise("(1,500.00)") == -150000
    assert parse_currency_to_paise("-500.00") == -50000

    # Zero and empty
    assert parse_currency_to_paise("") == 0
    assert parse_currency_to_paise(None) == 0

    # Format verification
    assert format_paise_to_rupees(18450000) == "₹184,500.00"


def test_csv_bill_parsing_reconciled():
    csv_content = (
        "Item,Amount\n"
        "Surgeon Fee,45000.00\n"
        "Room Rent,15000.00\n"
        "Pharmacy,10000.00\n"
        "Total Billed,70000.00\n"
    ).encode("utf-8")

    result = parse_csv_bill(csv_content)
    assert len(result["line_items"]) == 3
    assert result["stated_total_paise"] == 7000000
    assert result["computed_sum_paise"] == 7000000
    assert result["is_reconciled"] is True
    assert result["reconciliation_warning"] is None


def test_csv_bill_parsing_mismatch_warning():
    csv_content = (
        "Item,Amount\n"
        "Surgeon Fee,45000.00\n"
        "Room Rent,15000.00\n"
        "Total Stated,80000.00\n"
    ).encode("utf-8")

    result = parse_csv_bill(csv_content)
    assert len(result["line_items"]) == 2
    assert result["computed_sum_paise"] == 6000000
    assert result["stated_total_paise"] == 8000000
    assert result["is_reconciled"] is False
    assert result["reconciliation_warning"] is not None
    assert "Bill total mismatch" in result["reconciliation_warning"]


def test_csv_formula_injection_neutralization():
    csv_content = (
        "Item,Amount\n"
        "=1+2,100.00\n"
        "+cmd|' /C calc'!A0,200.00\n"
    ).encode("utf-8")

    result = parse_csv_bill(csv_content)
    assert result["line_items"][0]["description"].startswith("'=")
    assert result["line_items"][1]["description"].startswith("'+")


def test_txt_discharge_summary_parsing():
    txt_content = (
        "APOLLO HOSPITALS BENGALURU\n"
        "DISCHARGE SUMMARY\n"
        "Patient Name: Siddhartha Jaiswal\n"
        "Admission Date: 10-Feb-2026\n"
        "Discharge Date: 14-Feb-2026\n"
        "DIAGNOSIS: Severe Bilateral Osteoarthritis Grade IV\n"
        "Procedure: Total Knee Replacement\n"
    ).encode("utf-8")

    result = parse_txt_document(txt_content)
    assert result["doc_type"] == "DISCHARGE_SUMMARY"
    assert result["patient_name"] == "Siddhartha Jaiswal"
    assert "apollo" in result["hospital_name"].lower()
    assert "10-Feb-2026" in result["dates_found"]
    assert "Severe Bilateral Osteoarthritis Grade IV" in result["diagnosis_text"]


def test_txt_rejection_letter_parsing():
    txt_content = (
        "STAR HEALTH INSURANCE\n"
        "LETTER OF REPUDIATION\n"
        "Claim Reference: CLM-20491\n"
        "Under Clause 4.2 of Policy Terms, claim is rejected.\n"
    ).encode("utf-8")

    result = parse_txt_document(txt_content)
    assert result["doc_type"] == "REJECTION_LETTER"
    assert result["clause_ref"] == "Clause 4.2"


def test_file_validation():
    # Valid PDF signature
    assert validate_file_bytes(b"%PDF-1.4 header text", "claim.pdf") == "pdf"
    # Valid PNG signature
    assert validate_file_bytes(b"\x89PNG\r\n\x1a\n binary data", "bill.png") == "png"
    # Valid text
    assert validate_file_bytes(b"Hospital discharge notes", "notes.txt") == "txt"

    # Blocked executables
    with pytest.raises(FileValidationError, match="Executable files"):
        validate_file_bytes(b"MZ\x90\x00\x03\x00\x00\x00", "setup.exe")

    with pytest.raises(FileValidationError, match="Executable files"):
        validate_file_bytes(b"\x7fELF\x02\x01\x01", "binary")

    # Empty file
    with pytest.raises(FileValidationError, match="empty"):
        validate_file_bytes(b"", "empty.txt")
