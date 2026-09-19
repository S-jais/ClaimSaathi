"""
backend/app/documents/extraction/redaction.py
Redaction of sensitive Indian personally identifiable information (Aadhaar, PAN, Payment cards).
Ensures sensitive identifiers are never sent to external LLMs or saved in unredacted logs.
"""
from __future__ import annotations

import re

# 12-digit Aadhaar number with optional spaces or hyphens: e.g. 1234 5678 9012
AADHAAR_REGEX = re.compile(r"\b[2-9]\d{3}[-\s]?\d{4}[-\s]?\d{4}\b")

# Indian PAN format: 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F)
PAN_REGEX = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")

# 16-digit credit/debit card numbers
CARD_REGEX = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")

# Bank Account numbers: 9 to 18 consecutive digits
BANK_ACCOUNT_REGEX = re.compile(r"\b\d{9,18}\b")


def redact_sensitive_data(text: str) -> str:
    """
    Replaces sensitive identifiers with masked tokens:
      Aadhaar -> [REDACTED_AADHAAR_XXXX]
      PAN     -> [REDACTED_PAN_XXXX]
      Card    -> [REDACTED_CARD_XXXX]
    """
    if not text:
        return text

    def mask_aadhaar(match: re.Match) -> str:
        val = match.group(0).replace(" ", "").replace("-", "")
        return f"[REDACTED_AADHAAR_{val[-4:]}]"

    def mask_pan(match: re.Match) -> str:
        val = match.group(0)
        return f"[REDACTED_PAN_{val[-3:]}]"

    def mask_card(match: re.Match) -> str:
        val = match.group(0).replace(" ", "").replace("-", "")
        return f"[REDACTED_CARD_{val[-4:]}]"

    redacted = CARD_REGEX.sub(mask_card, text)
    redacted = AADHAAR_REGEX.sub(mask_aadhaar, redacted)
    redacted = PAN_REGEX.sub(mask_pan, redacted)
    return redacted
