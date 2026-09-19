"""
backend/app/documents/parsers.py
Deterministic parsers for ClaimSaathi documents:
1. Magic bytes & mime validation
2. Indian currency & integer paise normalizer
3. Robust CSV hospital bill parser (with encoding/delimiter sniffing and reconciliation checks)
4. TXT parser (discharge summaries, rejection letters)
5. Native PDF text layer extractor (pypdf)
"""
from __future__ import annotations

import csv
import io
import re
from decimal import Decimal, InvalidOperation
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


# ---------------------------------------------------------------------------
# 1. Magic Bytes & File Validation
# ---------------------------------------------------------------------------
MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "pdf": [b"%PDF"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpeg": [b"\xff\xd8\xff"],
}

BLOCKED_EXECUTABLE_SIGNATURES: list[bytes] = [
    b"MZ",            # Windows PE / DLL
    b"\x7fELF",       # Linux ELF
    b"\xca\xfe\xba\xbe", # Mach-O / Java class
]


class FileValidationError(ValueError):
    """Raised when an uploaded file is invalid, corrupt, or unsafe."""
    pass


def validate_file_bytes(data: bytes, filename: str | None = None) -> str:
    """
    Validates file payload by magic bytes and returns detected type:
    'pdf', 'png', 'jpeg', 'csv', 'txt'.
    Rejects executables, zero-byte files, and corrupt payloads.
    """
    if not data or len(data) == 0:
        raise FileValidationError("File is empty (0 bytes). Please upload a valid document.")

    # Check for blocked executable signatures
    for sig in BLOCKED_EXECUTABLE_SIGNATURES:
        if data.startswith(sig):
            raise FileValidationError("Executable files (.exe, .dll, .elf) are strictly prohibited.")

    # Check known binary magic signatures
    for doc_type, sigs in MAGIC_SIGNATURES.items():
        for sig in sigs:
            if data.startswith(sig):
                return doc_type

    # Check if text/csv: must not contain null bytes and must decode as text
    if b"\x00" in data[:4096]:
        raise FileValidationError("Corrupt or unsupported binary document format.")

    # Attempt text decodings
    ext = (filename or "").lower().split(".")[-1]
    if ext in ("csv", "tsv"):
        return "csv"
    return "txt"


# ---------------------------------------------------------------------------
# 2. Indian Currency & Integer Paise Normalization
# ---------------------------------------------------------------------------
INDIAN_CURRENCY_REGEX = re.compile(
    r"[₹\s,]|(?:INR|Rs\.?|Rupees?)\s*",
    re.IGNORECASE,
)

def parse_currency_to_paise(val: Any) -> int:
    """
    Converts currency representations (Indian notation, ₹, Rs., commas, parentheses)
    into integer paise.
    e.g.:
      '1,84,500.00' -> 18450000
      '₹ 4,200'     -> 420000
      '(1,500.00)'  -> -150000 (negative discount)
      '-500'        -> -50000
    Never uses floating-point arithmetic.
    """
    if val is None or val == "":
        return 0

    if isinstance(val, int):
        return val * 100

    if isinstance(val, Decimal):
        return int(val * 100)

    s = str(val).strip()
    if not s:
        return 0

    is_negative = False
    # Check accounting parentheses: (1,500.00)
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        is_negative = True
        s = s[1:].strip()
    elif s.endswith("-"):
        is_negative = True
        s = s[:-1].strip()

    # Strip currency symbols, commas, and whitespace
    clean_s = INDIAN_CURRENCY_REGEX.sub("", s).strip()
    if not clean_s:
        return 0

    try:
        dec = Decimal(clean_s)
        paise = int(round(dec * 100))
        return -paise if is_negative else paise
    except (InvalidOperation, ValueError):
        return 0


def format_paise_to_rupees(paise: int) -> str:
    """Formats integer paise into standard Indian rupee representation with 2 decimal places."""
    rupees = Decimal(paise) / Decimal(100)
    return f"₹{rupees:,.2f}"


# ---------------------------------------------------------------------------
# 3. Deterministic CSV Hospital Bill Parser
# ---------------------------------------------------------------------------
SUMMARY_ROW_PATTERNS = [
    re.compile(r"\b(total|sub\s*total|grand\s*total|net\s*payable|gross\s*total|final\s*bill|balance\s*due)\b", re.IGNORECASE)
]

HEADER_ALIASES: dict[str, list[str]] = {
    "description": ["item description", "description", "particulars", "item name", "service", "procedure", "charge head", "details"],
    "category": ["category", "dept", "department", "service type", "billing group"],
    "quantity": ["quantity", "qty", "units", "count", "nos", "days"],
    "rate": ["rate", "unit price", "price", "unit rate", "cost/unit"],
    "amount": ["amount", "total", "net amount", "total amount", "line total", "charges", "gross"],
}


def sanitize_cell_formula_injection(cell: str) -> str:
    """Neutralizes formula injection characters (=, +, -, @) for safety."""
    if cell and cell[0] in ("=", "+", "-", "@"):
        return "'" + cell
    return cell


def parse_csv_bill(content: bytes) -> dict[str, Any]:
    """
    Parses CSV hospital bill, extracts itemized line items in paise,
    filters out subtotal/total rows, and calculates reconciliation.
    """
    # Detect encoding
    text = ""
    for enc in ("utf-8-sig", "utf-8", "windows-1252", "iso-8859-1"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if not text:
        text = content.decode("utf-8", errors="replace")

    # Sniff delimiter
    sample = text[:2048]
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)

    if not rows:
        return {
            "line_items": [],
            "stated_total_paise": 0,
            "computed_sum_paise": 0,
            "is_reconciled": True,
            "reconciliation_warning": None,
        }

    # Identify header row
    header_idx = -1
    col_map: dict[str, int] = {}

    for idx, row in enumerate(rows[:10]):
        row_lower = [str(c).strip().lower() for c in row]
        matches = 0
        temp_map: dict[str, int] = {}
        for canon, aliases in HEADER_ALIASES.items():
            for c_idx, cell in enumerate(row_lower):
                if any(alias in cell for alias in aliases):
                    temp_map[canon] = c_idx
                    matches += 1
                    break
        if matches >= 2 and ("description" in temp_map or "amount" in temp_map):
            header_idx = idx
            col_map = temp_map
            break

    if header_idx == -1:
        # Fallback default positions: col 0 description, col -1 amount
        header_idx = 0
        col_map = {"description": 0, "amount": len(rows[0]) - 1}

    line_items: list[dict[str, Any]] = []
    stated_total_paise: int | None = None
    item_counter = 1

    for row in rows[header_idx + 1:]:
        if not row or all(not str(c).strip() for c in row):
            continue

        desc_col = col_map.get("description", 0)
        desc_text = row[desc_col].strip() if desc_col < len(row) else ""
        if not desc_text:
            continue

        amount_col = col_map.get("amount", len(row) - 1)
        amount_text = row[amount_col].strip() if amount_col < len(row) else "0"
        amount_paise = parse_currency_to_paise(amount_text)

        # Check if this row is a summary / total row
        is_summary = any(pat.search(desc_text) for pat in SUMMARY_ROW_PATTERNS)
        if is_summary:
            if amount_paise > 0 and stated_total_paise is None:
                stated_total_paise = amount_paise
            continue

        # Extract quantity and rate if available
        qty = 1
        if "quantity" in col_map and col_map["quantity"] < len(row):
            try:
                qty = max(1, int(Decimal(re.sub(r"[^\d.]", "", row[col_map["quantity"]]) or "1")))
            except Exception:
                qty = 1

        rate_paise = 0
        if "rate" in col_map and col_map["rate"] < len(row):
            rate_paise = parse_currency_to_paise(row[col_map["rate"]])
        elif qty > 0 and amount_paise != 0:
            rate_paise = amount_paise // qty

        raw_cat = ""
        if "category" in col_map and col_map["category"] < len(row):
            raw_cat = row[col_map["category"]].strip()

        line_items.append({
            "id": f"item-{item_counter:03d}",
            "description": sanitize_cell_formula_injection(desc_text),
            "raw_category": raw_cat,
            "quantity": qty,
            "rate_paise": rate_paise,
            "amount_paise": amount_paise,
        })
        item_counter += 1

    computed_sum_paise = sum(item["amount_paise"] for item in line_items)
    effective_total_paise = stated_total_paise if stated_total_paise is not None else computed_sum_paise
    is_reconciled = (stated_total_paise is None) or (stated_total_paise == computed_sum_paise)

    rec_warning = None
    if not is_reconciled and stated_total_paise is not None:
        diff = abs(stated_total_paise - computed_sum_paise)
        rec_warning = (
            f"Bill total mismatch: Stated total is {format_paise_to_rupees(stated_total_paise)} "
            f"but itemized lines sum to {format_paise_to_rupees(computed_sum_paise)} "
            f"(Difference: {format_paise_to_rupees(diff)}). Sent for user review."
        )

    return {
        "line_items": line_items,
        "stated_total_paise": effective_total_paise,
        "computed_sum_paise": computed_sum_paise,
        "is_reconciled": is_reconciled,
        "reconciliation_warning": rec_warning,
    }


# ---------------------------------------------------------------------------
# 4. Deterministic TXT Parser
# ---------------------------------------------------------------------------
DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b"),
    re.compile(r"\b(\d{1,2}[-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s]\d{2,4})\b", re.IGNORECASE),
]

def parse_txt_document(content: bytes) -> dict[str, Any]:
    """
    Extracts text entities, dates, diagnosis, and clause references from text files.
    """
    text = ""
    for enc in ("utf-8-sig", "utf-8", "windows-1252", "iso-8859-1"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        text = content.decode("utf-8", errors="replace")

    # Document type heuristics
    doc_type = "OTHER"
    confidence = 0.6
    text_lower = text.lower()

    if "discharge summary" in text_lower or "course in hospital" in text_lower:
        doc_type = "DISCHARGE_SUMMARY"
        confidence = 0.95
    elif "repudiat" in text_lower or "grounds for repudiation" in text_lower or "rejection" in text_lower:
        doc_type = "REJECTION_LETTER"
        confidence = 0.95
    elif "indoor case" in text_lower or "ot notes" in text_lower:
        doc_type = "INDOOR_CASE_PAPERS"
        confidence = 0.90
    elif "bill" in text_lower or "incurred" in text_lower:
        doc_type = "HOSPITAL_BILL"
        confidence = 0.85

    # Extract dates
    dates: list[str] = []
    for pat in DATE_PATTERNS:
        for match in pat.finditer(text):
            val = match.group(1).strip()
            if val not in dates:
                dates.append(val)

    # Extract patient name
    patient_name = None
    pat_match = re.search(r"(?:Patient\s*Name|Patient|Claimant|Name)\s*[:\-]\s*([A-Za-z\.\s]{2,40})", text, re.IGNORECASE)
    if pat_match:
        patient_name = pat_match.group(1).split("\n")[0].split("\r")[0].strip()

    # Extract hospital name
    hospital_name = None
    hosp_match = re.search(r"((?:Apollo|Fortis|Manipal|Max|Narayana|AIIMS|Medanta|[A-Za-z\s]+)\s*Hospital[s]?[A-Za-z,\s]*)", text, re.IGNORECASE)
    if hosp_match:
        hospital_name = hosp_match.group(1).split("\n")[0].strip()

    # Extract clause reference
    clause_ref = None
    clause_match = re.search(r"(Clause\s*\d+(?:\.\d+)?|Section\s*\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if clause_match:
        clause_ref = clause_match.group(1).strip()

    # Extract diagnosis
    diagnosis_text = None
    diag_match = re.search(r"DIAGNOSIS\s*[:\-]?\s*([^\n\r]+(?:\n[^\n\r]+)?)", text, re.IGNORECASE)
    if diag_match:
        diagnosis_text = diag_match.group(1).strip()

    return {
        "doc_type": doc_type,
        "doc_type_confidence": confidence,
        "text": text,
        "dates_found": dates,
        "patient_name": patient_name,
        "hospital_name": hospital_name,
        "clause_ref": clause_ref,
        "diagnosis_text": diagnosis_text,
    }


# ---------------------------------------------------------------------------
# 5. Deterministic PDF Text Layer Extractor
# ---------------------------------------------------------------------------
def parse_pdf_text(content: bytes) -> dict[str, Any]:
    """
    Extracts text layer from a PDF file using pypdf.
    Returns page count, page-by-page text, and indicates if multimodal OCR is needed.
    """
    if PdfReader is None:
        return {
            "num_pages": 1,
            "total_text_len": 0,
            "needs_multimodal_ocr": True,
            "pages": [],
            "combined_text": "",
        }

    stream = io.BytesIO(content)
    try:
        reader = PdfReader(stream)
    except Exception as e:
        raise FileValidationError(f"Could not read PDF: {str(e)}")

    if reader.is_encrypted:
        raise FileValidationError("Password-protected PDF files cannot be processed. Please upload an unlocked copy.")

    pages_text: list[dict[str, Any]] = []
    total_text_len = 0

    for idx, page in enumerate(reader.pages, 1):
        try:
            page_text = (page.extract_text() or "").strip()
        except Exception:
            page_text = ""
        total_text_len += len(page_text)
        pages_text.append({
            "page": idx,
            "text": page_text,
            "length": len(page_text),
        })

    # If entire document has fewer than 60 characters, it is likely a scanned image/photo PDF
    needs_multimodal_ocr = total_text_len < 60

    return {
        "num_pages": len(reader.pages),
        "total_text_len": total_text_len,
        "needs_multimodal_ocr": needs_multimodal_ocr,
        "pages": pages_text,
        "combined_text": "\n\n".join(p["text"] for p in pages_text if p["text"]),
    }
