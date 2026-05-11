from dataclasses import dataclass
import json
import os
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rest_framework import status


LLM_CONFIG_PLACEHOLDERS = {
    "",
    "your_api_key_here",
    "your-model-name",
    "https://api.example.com/v1",
}
ALLOWED_CONFIDENCE_VALUES = {"low", "medium", "high"}


@dataclass
class LLMServiceError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_502_BAD_GATEWAY


def generate_regex(
    *,
    natural_language: str,
    target_column: str,
    sample_values: list[str],
    sample_rows: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    provider = os.getenv("LLM_PROVIDER", "openai_compatible").strip()
    if provider != "openai_compatible":
        raise LLMServiceError(
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
        raise LLMServiceError(
            code="LLM_CONFIG_MISSING",
            message="LLM API key, base URL, or model is not configured.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    raw_content = _call_openai_compatible(
        api_key=api_key,
        base_url=base_url,
        model=model,
        natural_language=natural_language,
        target_column=target_column,
        sample_values=sample_values,
        sample_rows=sample_rows or [],
    )
    return parse_llm_json(raw_content)


def parse_llm_json(raw_content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LLMServiceError(
            code="LLM_INVALID_JSON",
            message="The LLM did not return valid JSON.",
        ) from exc

    if not isinstance(parsed, dict):
        raise LLMServiceError(
            code="LLM_INVALID_JSON",
            message="The LLM response JSON must be an object.",
        )

    flags = parsed.get("flags", [])
    if not isinstance(flags, list):
        raise LLMServiceError(
            code="LLM_INVALID_JSON",
            message="The LLM response flags field must be a list.",
        )

    confidence = parsed.get("confidence", "medium")
    if confidence not in ALLOWED_CONFIDENCE_VALUES:
        confidence = "low"

    explanation = parsed.get("explanation", "")

    return {
        "regex": parsed.get("regex"),
        "explanation": str(explanation) if explanation is not None else "",
        "flags": [str(flag) for flag in flags],
        "confidence": confidence,
    }


def _call_openai_compatible(
    *,
    api_key: str,
    base_url: str,
    model: str,
    natural_language: str,
    target_column: str,
    sample_values: list[str],
    sample_rows: list[dict[str, str]],
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
                    target_column=target_column,
                    sample_values=sample_values,
                    sample_rows=sample_rows,
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
        raise LLMServiceError(
            code="LLM_API_ERROR",
            message="The LLM provider returned an error.",
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LLMServiceError(
            code="LLM_API_ERROR",
            message="The LLM provider could not be reached.",
        ) from exc

    try:
        content = response_payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMServiceError(
            code="LLM_API_ERROR",
            message="The LLM provider response did not include message content.",
        ) from exc

    if not isinstance(content, str):
        raise LLMServiceError(
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
    return """You are a regex generation assistant for a data-processing web application.

Your task is to convert a user's natural language pattern description into a Python-compatible regular expression.

Return only valid JSON. Do not include markdown. Do not include explanations outside JSON.

The JSON schema is:
{
  "regex": "string",
  "explanation": "string",
  "flags": ["IGNORECASE" | "MULTILINE"],
  "confidence": "low" | "medium" | "high"
}

Rules:
- The regex must be compatible with Python's re module.
- Do not include leading and trailing slash delimiters.
- Prefer safe and readable regex.
- If the user asks for a target value that belongs to a named person, account, company, or other row-level entity, use the row samples to identify the matching row and return a regex that matches only that target-column value.
- Avoid catastrophic backtracking patterns.
- If the request is ambiguous, still provide the best reasonable regex and set confidence to "low".
- Do not perform replacement."""


def _user_prompt(
    *,
    natural_language: str,
    target_column: str,
    sample_values: list[str],
    sample_rows: list[dict[str, str]],
) -> str:
    sample_lines = "\n".join(
        f"{index}. {value}" for index, value in enumerate(sample_values, start=1)
    )
    if not sample_lines:
        sample_lines = "No non-empty sample values were available."

    row_lines = "\n".join(
        f"{index}. {json.dumps(row, ensure_ascii=True)}"
        for index, row in enumerate(sample_rows, start=1)
    )
    if not row_lines:
        row_lines = "No row samples were available."

    return f"""Target column: {target_column}

Target-column sample values:
{sample_lines}

Row samples:
{row_lines}

User description:
{natural_language}"""
