"""Validators for Consumer Data Standards (CDS) common field types."""

from datetime import datetime
import re
from typing import Optional
from urllib.parse import urlsplit


DATETIME_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[Tt](\d{2}:\d{2}:\d{2})(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$"
)
RATE_PATTERN = re.compile(r"^-?\d{1,16}(?:\.\d{1,16})?$")
AMOUNT_PATTERN = re.compile(r"^-?\d{1,16}\.\d{2,16}$")
DURATION_PATTERN = re.compile(
    r"^P(?!$)(?:\d+(?:\.\d+)?Y)?(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?W)?"
    r"(?:\d+(?:\.\d+)?D)?(?:T(?=\d)(?:\d+(?:\.\d+)?H)?(?:\d+(?:\.\d+)?M)?"
    r"(?:\d+(?:\.\d+)?S)?)?$"
)
URI_DISALLOWED_CHARACTERS = re.compile(r'[\s<>"{}|\\^`]')


def parse_datetime_string(value) -> Optional[datetime]:
    """Return an aware datetime for an RFC 3339 DateTimeString, otherwise None."""
    if not isinstance(value, str):
        return None

    match = DATETIME_PATTERN.match(value)
    if not match:
        return None

    date_part, time_part, fraction, offset = match.groups()
    # Python keeps microseconds; CDS allows longer fractions.
    fraction = (fraction or "")[:7]
    offset = "+00:00" if offset in {"Z", "z"} else offset
    try:
        return datetime.fromisoformat(f"{date_part}T{time_part}{fraction}{offset}")
    except ValueError:
        return None


def is_rate_string(value) -> bool:
    return isinstance(value, str) and bool(RATE_PATTERN.match(value))


def is_amount_string(value) -> bool:
    return isinstance(value, str) and bool(AMOUNT_PATTERN.match(value))


def is_iso8601_duration(value) -> bool:
    # CDS has no duration type; frequency fields are ISO 8601 durations.
    return isinstance(value, str) and bool(DURATION_PATTERN.match(value))


def uri_problem(value) -> Optional[str]:
    """Explain why a URIString is unusable as a product link, or return None."""
    if not isinstance(value, str):
        return "is not a URI string"

    if not value:
        return "is an empty string; omit the field instead"

    if value != value.strip():
        return "has leading or trailing whitespace"

    if URI_DISALLOWED_CHARACTERS.search(value):
        return "contains characters that are not allowed in a URI"

    try:
        parts = urlsplit(value)
    except ValueError:
        return "is not a valid URI"

    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return "is not an absolute http(s) URI"

    return None
