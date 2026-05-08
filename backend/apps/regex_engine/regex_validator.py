from dataclasses import dataclass
import re
from typing import Optional

from rest_framework import status


MAX_REGEX_LENGTH = 300
SUPPORTED_FLAGS = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
}
UNSAFE_REGEX_PATTERNS = [
    re.compile(r"\((?:\?:)?[^)]*(?:\.\*|\.\+)[^)]*\)[+*]"),
    re.compile(r"\([^)]*(?:\[[^\]]+\]|\\?.)\+[^)]*\)[+*]"),
    re.compile(r"\.\*.*\.\*.*\.\*"),
    re.compile(r"\.\{0,\d{5,}\}"),
    re.compile(r"\.\{,\d{5,}\}"),
]


@dataclass
class ValidatedRegex:
    pattern: str
    flags: int
    warnings: list[str]
    compiled_pattern: re.Pattern


@dataclass
class RegexValidationError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST


def validate_regex(pattern, flags: Optional[list[str]] = None) -> ValidatedRegex:
    if not isinstance(pattern, str) or not pattern.strip():
        raise RegexValidationError(
            code="REGEX_MISSING",
            message="The LLM response did not include a regex.",
        )

    normalized_pattern = pattern.strip()
    if len(normalized_pattern) > MAX_REGEX_LENGTH:
        raise RegexValidationError(
            code="REGEX_TOO_LONG",
            message=f"The generated regex must be {MAX_REGEX_LENGTH} characters or fewer.",
        )

    re_flags, warnings = _normalize_flags(flags or [])

    try:
        compiled_pattern = re.compile(normalized_pattern, re_flags)
    except re.error as exc:
        raise RegexValidationError(
            code="REGEX_COMPILE_ERROR",
            message=f"The generated regex is not valid Python regex syntax: {exc}.",
        ) from exc

    if _is_unsafe(normalized_pattern):
        raise RegexValidationError(
            code="REGEX_UNSAFE",
            message="The generated regex looks too risky to run on uploaded data.",
        )

    return ValidatedRegex(
        pattern=normalized_pattern,
        flags=re_flags,
        warnings=warnings,
        compiled_pattern=compiled_pattern,
    )


def _normalize_flags(flags: list[str]) -> tuple[int, list[str]]:
    re_flags = 0
    warnings = []

    for flag in flags:
        if flag in SUPPORTED_FLAGS:
            re_flags |= SUPPORTED_FLAGS[flag]
        else:
            warnings.append(f"Ignored unsupported regex flag: {flag}")

    return re_flags, warnings


def _is_unsafe(pattern: str) -> bool:
    return any(unsafe_pattern.search(pattern) for unsafe_pattern in UNSAFE_REGEX_PATTERNS)
