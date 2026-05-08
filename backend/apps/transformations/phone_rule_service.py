from dataclasses import dataclass
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rest_framework import status

from apps.regex_engine.llm_service import LLM_CONFIG_PLACEHOLDERS

from .phone_normalizer import (
    ALLOWED_PHONE_FORMATS,
    DEFAULT_PHONE_FORMAT,
    DEFAULT_REGION,
    TRANSFORMATION_TYPE,
    PhoneNormalizationError,
    normalize_rule,
)


SAMPLE_VALUE_LIMIT = 10
ALLOWED_CONFIDENCE_VALUES = {"low", "medium", "high"}


@dataclass
class PhoneRuleServiceError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_502_BAD_GATEWAY


def generate_phone_normalization_rule(
    *,
    natural_language: str,
    target_columns: list[str],
    sample_values: list[str],
) -> dict[str, Any]:
    provider = os.getenv("LLM_PROVIDER", "openai_compatible").strip()
    if provider != "openai_compatible":
        raise PhoneRuleServiceError(
            code="LLM_CONFIG_MISSING",
            message="Only the openai_compatible LLM provider is configured for this app.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    api_key = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    model = os.getenv("LLM_MODEL", "").strip()

    if (
        api_key in LLM_CONFIG_PLACEHOLDERS
        or base_url in LLM_CONFIG_PLACEHOLDERS
        or model in LLM_CONFIG_PLACEHOLDERS
    ):
        raise PhoneRuleServiceError(
            code="LLM_CONFIG_MISSING",
            message="LLM API key, base URL, or model is not configured.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    raw_content = _call_openai_compatible(
        api_key=api_key,
        base_url=base_url,
        model=model,
        natural_language=natural_language,
        target_columns=target_columns,
        sample_values=sample_values[:SAMPLE_VALUE_LIMIT],
    )
    return parse_phone_rule_json(raw_content)


generate_phone_rule = generate_phone_normalization_rule


def parse_phone_rule_json(raw_content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise PhoneRuleServiceError(
            code="LLM_INVALID_JSON",
            message="The LLM did not return valid JSON.",
        ) from exc

    if not isinstance(parsed, dict):
        raise PhoneRuleServiceError(
            code="LLM_INVALID_JSON",
            message="The LLM response JSON must be an object.",
        )

    try:
        normalized_rule = normalize_rule(parsed)
    except PhoneNormalizationError as exc:
        raise PhoneRuleServiceError(
            code=exc.code,
            message=exc.message,
        ) from exc

    return normalized_rule


def _call_openai_compatible(
    *,
    api_key: str,
    base_url: str,
    model: str,
    natural_language: str,
    target_columns: list[str],
    sample_values: list[str],
) -> str:
    timeout = _timeout_seconds()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {
                "role": "user",
                "content": _user_prompt(
                    natural_language=natural_language,
                    target_columns=target_columns,
                    sample_values=sample_values,
                ),
            },
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    request = Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise PhoneRuleServiceError(
            code="LLM_API_ERROR",
            message="The LLM provider returned an error.",
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PhoneRuleServiceError(
            code="LLM_API_ERROR",
            message="The LLM provider could not be reached.",
        ) from exc

    try:
        content = response_payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise PhoneRuleServiceError(
            code="LLM_API_ERROR",
            message="The LLM provider response did not include message content.",
        ) from exc

    if not isinstance(content, str):
        raise PhoneRuleServiceError(
            code="LLM_INVALID_JSON",
            message="The LLM message content must be a JSON string.",
        )

    return content


def _timeout_seconds() -> int:
    raw_timeout = os.getenv("LLM_TIMEOUT_SECONDS", "20")
    try:
        timeout = int(raw_timeout)
    except (TypeError, ValueError):
        return 20

    return max(1, timeout)


def _system_prompt() -> str:
    return f"""You are a phone-number normalization rule assistant for a data-processing web application.

Return only valid JSON. Do not include markdown. Do not include explanations outside JSON.

Do not rewrite table data. Do not output transformed rows. Only generate phone-normalization rules.

If the user asks for international format, prefer E164 unless they explicitly ask for a human-readable format.
Preserve invalid values by default.

The JSON schema is:
{{
  "transformation_type": "phone_normalization",
  "target_format": "E164" | "INTERNATIONAL" | "NATIONAL" | "RFC3966",
  "default_region": "two-letter ISO country/region code",
  "preserve_invalid": true,
  "explanation": "string"
}}

Rules:
- transformation_type must be "{TRANSFORMATION_TYPE}".
- Allowed target_format values are: {", ".join(ALLOWED_PHONE_FORMATS)}.
- Use "{DEFAULT_PHONE_FORMAT}" when the requested output is ambiguous.
- Use "{DEFAULT_REGION}" as default_region unless the user or samples clearly imply another region.
- Return preserve_invalid as true unless the user explicitly asks to clear invalid values."""


def _user_prompt(
    *,
    natural_language: str,
    target_columns: list[str],
    sample_values: list[str],
) -> str:
    sample_lines = "\n".join(
        f"{index}. {value}" for index, value in enumerate(sample_values, start=1)
    )
    if not sample_lines:
        sample_lines = "No non-empty sample values were available."

    column_lines = "\n".join(f"- {column}" for column in target_columns)

    return f"""Target column names:
{column_lines}

Sample values, capped at 10 values total:
{sample_lines}

User instruction:
{natural_language}"""
