import re


SUPPORTED_PII_TYPES = ("email", "phone", "credit_card", "url")
SUPPORTED_REDACTION_STRATEGIES = ("typed_placeholders", "generic_redacted")
DEFAULT_REDACTION_STRATEGY = "typed_placeholders"
REDACTION_ORDER = ("url", "email", "credit_card", "phone")

EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",
    re.IGNORECASE,
)
URL_PATTERN = re.compile(
    r"\b(?:https?://|www\.)[^\s<>'\"]+",
    re.IGNORECASE,
)
CREDIT_CARD_CANDIDATE_PATTERN = re.compile(
    r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"
)
PHONE_CANDIDATE_PATTERN = re.compile(
    r"(?<![\w])(?:\+?\d[\d\s().-]{6,}\d)(?![\w])"
)

PLACEHOLDERS = {
    "email": "[EMAIL_REDACTED]",
    "phone": "[PHONE_REDACTED]",
    "credit_card": "[CARD_REDACTED]",
    "url": "[URL_REDACTED]",
}
GENERIC_PLACEHOLDER = "REDACTED"


def placeholder_for(pii_type: str, strategy: str) -> str:
    if strategy == "generic_redacted":
        return GENERIC_PLACEHOLDER

    return PLACEHOLDERS[pii_type]


def digits_only(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def is_luhn_valid(candidate: str) -> bool:
    digits = digits_only(candidate)
    if len(digits) < 13 or len(digits) > 19:
        return False

    total = 0
    should_double = False
    for character in reversed(digits):
        value = int(character)
        if should_double:
            value *= 2
            if value > 9:
                value -= 9
        total += value
        should_double = not should_double

    return total % 10 == 0


def is_phone_candidate(candidate: str) -> bool:
    digits = digits_only(candidate)
    return 8 <= len(digits) <= 15
