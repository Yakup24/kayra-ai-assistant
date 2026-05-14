import re


PII_PATTERNS = [
    (re.compile(r"\b[1-9][0-9]{10}\b"), "[TC_KIMLIK]"),
    (re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\b(?:\+90|0)?\s?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b"), "[TELEFON]"),
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "[KART_NO]"),
]


def mask_sensitive_data(text: str) -> str:
    masked = text
    for pattern, replacement in PII_PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked

