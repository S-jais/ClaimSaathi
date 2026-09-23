"""
app/speech/spoken.py
Deterministic to_spoken() pipeline for ClaimSaathi Voice Mode.
Transforms validated copilot text into natural, speakable Hindi and English phrases.

Handles:
- Indian number-to-words with complete 0-99 Hindi irregular table
- Indian currency (Lakh/Crore/Hazaar, Rupees, Paise)
- Date formatting (Hindi & English)
- Acronyms & reason codes (IRDAI, TPA, DOC-04)
- Symbol & unit replacement (%, ₹, /, ≥)
- Identifier masking (last 4 digits only)
- Sentence chunking for parallel TTS synthesis
- Spoken ↔ Validated message numeric consistency verification
"""
from __future__ import annotations

import re
from typing import Literal

# ---------------------------------------------------------------------------
# Complete 0-99 Hindi Irregular Number Words
# ---------------------------------------------------------------------------
HINDI_NUMBERS_0_TO_99: dict[int, str] = {
    0: "शून्य", 1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पाँच", 6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस",
    11: "ग्यारह", 12: "बारह", 13: "तेरह", 14: "चौदह", 15: "पंद्रह", 16: "सोलह", 17: "सत्रह", 18: "अठारह", 19: "उन्नीस", 20: "बीस",
    21: "इक्कीस", 22: "बाईस", 23: "तेईस", 24: "चौबीस", 25: "पच्चीस", 26: "छब्बीस", 27: "सत्ताईस", 28: "अट्ठाईस", 29: "उनतीस", 30: "तीस",
    31: "इकतीस", 32: "बत्तीस", 33: "तैंतीस", 34: "चौंतीस", 35: "पैंतीस", 36: "छत्तीस", 37: "सैंतीस", 38: "अड़तीस", 39: "उनतालीस", 40: "चालीस",
    41: "इकतालीस", 42: "बयालीस", 43: "तैंतालीस", 44: "चवालीस", 45: "पैंतालीस", 46: "छियालीस", 47: "सैंतालीस", 48: "अड़तालीस", 49: "उनचास", 50: "पचास",
    51: "इक्यावन", 52: "बावन", 53: "तिरपन", 54: "चौवन", 55: "पचपन", 56: "छप्पन", 57: "सत्तावन", 58: "अट्ठावन", 59: "उनसठ", 60: "साठ",
    61: "इकसठ", 62: "बासठ", 63: "तिरसठ", 64: "चौंसठ", 65: "पैंसठ", 66: "छियासठ", 67: "सरसठ", 68: "अड़सठ", 69: "उनहत्तर", 70: "सत्तर",
    71: "इकहत्तर", 72: "बहत्तर", 73: "तिहत्तर", 74: "चौहत्तर", 75: "पचहत्तर", 76: "छिहत्तर", 77: "सतहत्तर", 78: "अठहत्तर", 79: "उन्नासी", 80: "अस्सी",
    81: "इक्यासी", 82: "बयासी", 83: "तिरासी", 84: "चौरासी", 85: "पचासी", 86: "छियासी", 87: "सत्तासी", 88: "अट्ठासी", 89: "नवासी", 90: "नब्बे",
    91: "इक्यानवे", 92: "बानवे", 93: "तिरानवे", 94: "चौरानवे", 95: "पंचानवे", 96: "छियानवे", 97: "सत्तानवे", 98: "अट्ठानवे", 99: "निन्यानवे"
}

ENGLISH_ONES = [
    "", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen"
]
ENGLISH_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

HINDI_MONTHS = {
    1: "जनवरी", 2: "फ़रवरी", 3: "मार्च", 4: "अप्रैल", 5: "मई", 6: "जून",
    7: "जुलाई", 8: "अगस्त", 9: "सितंबर", 10: "अक्टूबर", 11: "नवंबर", 12: "दिसंबर"
}
ENGLISH_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
}

ACRONYM_MAP_HI = {
    "IRDAI": "आई-आर-डी-ए-आई",
    "TPA": "टी-पी-ए",
    "OPD": "ओ-पी-डी",
    "ICU": "आई-सी-यू",
    "PPE": "पी-पी-ई",
    "GST": "जी-एस-टी",
    "MRD": "एम-आर-डी",
    "GRO": "जी-आर-ओ",
    "ICP": "आई-सी-पी",
}

ACRONYM_MAP_EN = {
    "IRDAI": "I R D A I",
    "TPA": "T P A",
    "OPD": "O P D",
    "ICU": "I C U",
    "PPE": "P P E",
    "GST": "G S T",
    "MRD": "M R D",
    "GRO": "G R O",
    "ICP": "I C P",
}


def number_to_hindi_words(n: int) -> str:
    """Converts non-negative integer into Indian numbering system words in Hindi."""
    if n < 0:
        return "माइनस " + number_to_hindi_words(abs(n))
    if n in HINDI_NUMBERS_0_TO_99:
        return HINDI_NUMBERS_0_TO_99[n]

    parts: list[str] = []

    # Crores (1,00,00,000)
    if n >= 10000000:
        crores = n // 10000000
        n %= 10000000
        parts.append(f"{number_to_hindi_words(crores)} करोड़")

    # Lakhs (1,00,000)
    if n >= 100000:
        lakhs = n // 100000
        n %= 100000
        parts.append(f"{number_to_hindi_words(lakhs)} लाख")

    # Thousands (1,000)
    if n >= 1000:
        thousands = n // 1000
        n %= 1000
        parts.append(f"{number_to_hindi_words(thousands)} हज़ार")

    # Hundreds (100)
    if n >= 100:
        hundreds = n // 100
        n %= 100
        parts.append(f"{number_to_hindi_words(hundreds)} सौ")

    # Remainder 1-99
    if n > 0:
        parts.append(HINDI_NUMBERS_0_TO_99[n])

    return " ".join(parts).strip()


def number_to_english_words(n: int) -> str:
    """Converts integer into Indian numbering system words in English."""
    if n < 0:
        return "minus " + number_to_english_words(abs(n))
    if n == 0:
        return "zero"

    parts: list[str] = []

    if n >= 10000000:
        crores = n // 10000000
        n %= 10000000
        parts.append(f"{number_to_english_words(crores)} crore")

    if n >= 100000:
        lakhs = n // 100000
        n %= 100000
        parts.append(f"{number_to_english_words(lakhs)} lakh")

    if n >= 1000:
        thousands = n // 1000
        n %= 1000
        parts.append(f"{number_to_english_words(thousands)} thousand")

    if n >= 100:
        hundreds = n // 100
        n %= 100
        parts.append(f"{number_to_english_words(hundreds)} hundred")

    if n > 0:
        if n < 20:
            parts.append(ENGLISH_ONES[n])
        else:
            tens = ENGLISH_TENS[n // 10]
            ones = ENGLISH_ONES[n % 10]
            parts.append(f"{tens}-{ones}".strip("-"))

    return " ".join(parts).strip()


def format_currency_amount(amount: float, lang: str = "hi") -> str:
    """Formats numeric currency into spoken words (with paise if applicable)."""
    is_neg = amount < 0
    abs_amt = abs(amount)
    rupees = int(abs_amt)
    paise = int(round((abs_amt - rupees) * 100))

    if lang in {"hi", "hinglish"}:
        words = number_to_hindi_words(rupees) + " रुपये"
        if paise > 0:
            words += f" और {number_to_hindi_words(paise)} पैसे"
        if is_neg:
            words = "माइनस " + words
        return words
    else:
        words = number_to_english_words(rupees) + " rupees"
        if paise > 0:
            words += f" and {number_to_english_words(paise)} paise"
        if is_neg:
            words = "minus " + words
        return words


HINDI_ALPHABET: dict[str, str] = {
    "A": "ए", "B": "बी", "C": "सी", "D": "डी", "E": "ई", "F": "एफ़", "G": "जी",
    "H": "एच", "I": "आई", "J": "जे", "K": "के", "L": "एल", "M": "एम", "N": "एन",
    "O": "ओ", "P": "पी", "Q": "क्यू", "R": "आर", "S": "एस", "T": "टी", "U": "यू",
    "V": "वी", "W": "डब्लू", "X": "एक्स", "Y": "वाय", "Z": "ज़ेड"
}


def format_reason_code(code: str, lang: str = "hi") -> str:
    """DOC-04 -> डी-ओ-सी, शून्य चार / D O C, zero four"""
    m = re.match(r"^([A-Za-z]+)[-_]?(\d+)$", code.strip())
    if not m:
        return code
    letters, digits = m.group(1).upper(), m.group(2)
    if lang in {"hi", "hinglish"}:
        letter_str = "-".join(HINDI_ALPHABET.get(ch, ch) for ch in letters)
        digit_str = " ".join(HINDI_NUMBERS_0_TO_99.get(int(d), d) for d in digits)
        return f"{letter_str}, {digit_str}"
    else:
        letter_str = " ".join(letters)
        digit_str = " ".join(ENGLISH_ONES[int(d)] if int(d) < 10 else d for d in digits)
        return f"{letter_str}, {digit_str}"


def expand_date_to_spoken(match_str: str, lang: str = "hi") -> str:
    """21 March 2026 / 21-03-2026 -> spoken date"""
    # Try dd Month yyyy
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", match_str)
    if m:
        day = int(m.group(1))
        month_name = m.group(2).lower()
        year = int(m.group(3))
        month_num = None
        for num, name in ENGLISH_MONTHS.items():
            if name.lower().startswith(month_name[:3]):
                month_num = num
                break
        if month_num:
            if lang in {"hi", "hinglish"}:
                return f"{number_to_hindi_words(day)} {HINDI_MONTHS[month_num]} {number_to_hindi_words(year)}"
            else:
                return f"{number_to_english_words(day)} of {ENGLISH_MONTHS[month_num]} {number_to_english_words(year)}"

    # Try dd/mm/yyyy or yyyy-mm-dd
    m2 = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", match_str)
    if m2:
        day = int(m2.group(1))
        month = int(m2.group(2))
        year = int(m2.group(3))
        if 1 <= month <= 12:
            if lang in {"hi", "hinglish"}:
                return f"{number_to_hindi_words(day)} {HINDI_MONTHS[month]} {number_to_hindi_words(year)}"
            else:
                return f"{number_to_english_words(day)} of {ENGLISH_MONTHS[month]} {number_to_english_words(year)}"

    return match_str


def to_spoken(
    text: str,
    language: str = "en",
    max_words: int = 85,
) -> str:
    """
    Deterministic speech synthesis pre-processor.
    Transforms text into clear, speakable sentences:
    - Strips markdown, URLs, citation tags
    - Converts amounts (₹1,84,500) into spoken words
    - Expands dates, acronyms, reason codes, symbols
    - Masks policy/account numbers to last 4 digits
    - Restricts to max spoken word budget with summary fallback
    """
    if not text:
        return ""

    is_hindi = language in {"hi", "hinglish"} or bool(re.search(r"[\u0900-\u097F]", text))
    target_lang = "hi" if is_hindi else "en"

    clean = text

    # 1. Strip markdown elements & citations
    clean = re.sub(r"\*\*|\*|#|`|~", "", clean)
    clean = re.sub(r"\[(FACT|INTERPRETATION|RECOMMENDATION).*?\]", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\[cit_[a-zA-Z0-9_-]+\]", "", clean)
    clean = re.sub(r"\[.*?\]\(.*?\)", "", clean)  # markdown links
    clean = re.sub(r"https?://\S+", "", clean)     # URLs

    # 2. Mask sensitive long numbers (Aadhaar, PAN, phone, 8+ digit policy numbers) to last 4
    def _mask_long_digits(match: re.Match) -> str:
        d = match.group(0)
        last4 = d[-4:]
        if is_hindi:
            digits_hi = " ".join(HINDI_NUMBERS_0_TO_99.get(int(x), x) for x in last4)
            return f"आख़िरी चार अंक {digits_hi}"
        return f"last four digits {' '.join(last4)}"

    clean = re.sub(r"\b\d{8,16}\b", _mask_long_digits, clean)

    # 3. Currency expansion: ₹1,84,500 or Rs. 1,84,500 or INR 1,84,500
    def _replace_currency(match: re.Match) -> str:
        raw_num = match.group(2).replace(",", "")
        try:
            amt = float(raw_num)
            return format_currency_amount(amt, lang=target_lang)
        except ValueError:
            return match.group(0)

    clean = re.sub(r"(₹|Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]{1,2})?)", _replace_currency, clean, flags=re.IGNORECASE)

    # 4. Reason codes: e.g. DOC-04, CL-4.2
    def _replace_reason_code(match: re.Match) -> str:
        return format_reason_code(match.group(0), lang=target_lang)

    clean = re.sub(r"\b[A-Z]{2,4}-\d{2,4}\b", _replace_reason_code, clean)

    # 5. Acronyms: IRDAI, TPA, OPD, etc.
    acronym_dict = ACRONYM_MAP_HI if is_hindi else ACRONYM_MAP_EN
    for acr, expansion in acronym_dict.items():
        clean = re.sub(rf"\b{acr}\b", expansion, clean)

    # 6. Dates
    clean = re.sub(
        r"\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
        lambda m: expand_date_to_spoken(m.group(0), target_lang),
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",
        lambda m: expand_date_to_spoken(m.group(0), target_lang),
        clean,
    )

    # 7. Units & symbols
    if is_hindi:
        clean = clean.replace("%", " प्रतिशत")
        clean = clean.replace("≥", " कम से कम ")
        clean = clean.replace("≤", " अधिकतम ")
        clean = clean.replace("/", " प्रति ")
    else:
        clean = clean.replace("%", " percent")
        clean = clean.replace("≥", " at least ")
        clean = clean.replace("≤", " at most ")
        clean = clean.replace("/", " per ")

    # 8. Collapse whitespace
    clean = re.sub(r"\s+", " ", clean).strip()

    # 9. Cap to at most 3 sentences for natural spoken turn (~30s budget)
    sentences = [s.strip() for s in re.split(r"(?<=[।?!.])\s+", clean) if s.strip()]
    if len(sentences) > 3:
        clean = " ".join(sentences[:3])

    # 10. Word budget & truncation
    words = clean.split()
    if len(words) > max_words:
        truncated = " ".join(words[:max_words])
        if is_hindi:
            clean = truncated + "। बाकी विवरण मैंने स्क्रीन पर दिखा दिया है।"
        else:
            clean = truncated + ". I've put the remaining details on your screen."

    return clean


def chunk_sentences(text: str) -> list[str]:
    """Splits spoken text into clean sentence chunks for parallel synthesis."""
    if not text:
        return []
    # Split by standard Indian punctuation (।, ., !, ?)
    chunks = re.split(r"(?<=[।?!.])\s+", text)
    return [c.strip() for c in chunks if c.strip()]


def extract_numbers_and_amounts(text: str) -> set[int]:
    """Extract all plain digits and Indian currency numbers from text for consistency verification."""
    found: set[int] = set()

    # Digits
    digits = re.findall(r"\b\d+\b", text.replace(",", ""))
    for d in digits:
        try:
            found.add(int(d))
        except ValueError:
            pass

    # Hindi number words reverse check
    for num, word in HINDI_NUMBERS_0_TO_99.items():
        if word in text and num > 0:
            found.add(num)

    return found


def verify_numeric_consistency(spoken_text: str, validated_message: str) -> bool:
    """
    Checks that every significant amount (e.g. ₹1,84,500, 12000, 20491)
    mentioned in spoken_text corresponds to numbers in the validated_message.
    """
    if not spoken_text or not validated_message:
        return True

    spoken_nums = extract_numbers_and_amounts(spoken_text)
    msg_nums = extract_numbers_and_amounts(validated_message)

    # Filter out common small conversational counters (0, 1, 2)
    significant_spoken = {n for n in spoken_nums if n > 10}
    significant_msg = {n for n in msg_nums if n > 10}

    # Every significant number in spoken text must be justified by the message
    for num in significant_spoken:
        if num not in significant_msg:
            # Check if it was part of a larger decomposed number (e.g. 184500 -> 184, 500)
            if not any(str(num) in str(m) for m in significant_msg):
                return False

    return True
