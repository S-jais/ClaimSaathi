"""
tests/unit/test_speech_spoken.py
Unit tests for deterministic to_spoken() pipeline:
- Hindi irregular numbers 0-99
- Indian currency expansion (Lakh/Crore/Hazaar, Rupees, Paise)
- Date formatting
- Acronym and reason code expansions
- Sentence chunking
- Numeric consistency validation
"""
import pytest
from app.speech.spoken import (
    number_to_hindi_words,
    number_to_english_words,
    format_currency_amount,
    format_reason_code,
    expand_date_to_spoken,
    to_spoken,
    chunk_sentences,
    verify_numeric_consistency,
)


def test_hindi_numbers_0_to_99_irregulars():
    assert number_to_hindi_words(0) == "शून्य"
    assert number_to_hindi_words(1) == "एक"
    assert number_to_hindi_words(2) == "दो"
    assert number_to_hindi_words(11) == "ग्यारह"
    assert number_to_hindi_words(21) == "इक्कीस"
    assert number_to_hindi_words(26) == "छब्बीस"
    assert number_to_hindi_words(67) == "सरसठ"
    assert number_to_hindi_words(84) == "चौरासी"
    assert number_to_hindi_words(89) == "नवासी"
    assert number_to_hindi_words(99) == "निन्यानवे"


def test_indian_currency_to_hindi_words():
    # 1,84,500 -> एक लाख चौरासी हज़ार पाँच सौ रुपये
    amt_184500 = format_currency_amount(184500, lang="hi")
    assert "एक लाख" in amt_184500
    assert "चौरासी हज़ार" in amt_184500
    assert "पाँच सौ रुपये" in amt_184500

    # 12,000 -> बारह हज़ार रुपये
    amt_12000 = format_currency_amount(12000, lang="hi")
    assert amt_12000 == "बारह हज़ार रुपये"

    # 2,50,000 -> दो लाख पचास हज़ार रुपये
    amt_250000 = format_currency_amount(250000, lang="hi")
    assert "दो लाख पचास हज़ार रुपये" in amt_250000

    # Paise check: 184500.50
    amt_paise = format_currency_amount(184500.50, lang="hi")
    assert "पचास पैसे" in amt_paise


def test_indian_currency_to_english_words():
    amt_en = format_currency_amount(184500, lang="en")
    assert "one lakh" in amt_en
    assert "eighty-four thousand" in amt_en
    assert "five hundred rupees" in amt_en


def test_acronym_and_reason_code_expansion():
    # Reason code DOC-04
    rc_hi = format_reason_code("DOC-04", lang="hi")
    assert "डी-ओ-सी" in rc_hi
    assert "चार" in rc_hi

    # Acronyms in text
    res_hi = to_spoken("IRDAI and TPA guidelines under OPD claim.", language="hi")
    assert "आई-आर-डी-ए-आई" in res_hi
    assert "टी-पी-ए" in res_hi
    assert "ओ-पी-डी" in res_hi


def test_date_expansion():
    d_hi = expand_date_to_spoken("21 March 2026", lang="hi")
    assert "इक्कीस" in d_hi
    assert "मार्च" in d_hi
    assert "दो हज़ार छब्बीस" in d_hi

    d_en = expand_date_to_spoken("21 March 2026", lang="en")
    assert "twenty-one" in d_en
    assert "March" in d_en


def test_identifier_masking():
    # Long 12-digit number should be masked to last 4
    res = to_spoken("Your policy number is 987654321049.", language="en")
    assert "987654321049" not in res
    assert "last four digits 1 0 4 9" in res


def test_sentence_chunking():
    text = "पहला वाक्य यहाँ समाप्त होता है। दूसरा वाक्य यहाँ है। तीसरा वाक्य!"
    chunks = chunk_sentences(text)
    assert len(chunks) == 3
    assert chunks[0] == "पहला वाक्य यहाँ समाप्त होता है।"
    assert chunks[1] == "दूसरा वाक्य यहाँ है।"
    assert chunks[2] == "तीसरा वाक्य!"


def test_numeric_consistency_validator():
    # Matching numbers
    msg = "Your gross bill was ₹1,84,500 with ₹12,000 non-payable deductions."
    spoken_matching = "Aapke hospital bill ki amount ek lakh chaurasi hazaar paanch sau rupees hai aur 12000 rupaye non-payable hain."
    assert verify_numeric_consistency(spoken_matching, msg) is True

    # Hallucinated extra number
    spoken_hallucinated = "Aapka claim 95000 rupees ka tha."
    assert verify_numeric_consistency(spoken_hallucinated, msg) is False
