from dataclasses import dataclass
import json
import os
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
from rest_framework import status

from apps.regex_engine.llm_service import LLM_CONFIG_PLACEHOLDERS

from . import pii_redactor
from .pii_patterns import (
    DEFAULT_REDACTION_STRATEGY,
    SUPPORTED_PII_TYPES,
    SUPPORTED_REDACTION_STRATEGIES,
)
from .transformation_stats import cell_to_string, is_nullish


TRANSFORMATION_TYPE = "pii_redaction"
TARGET_COLUMNS_POLICY_ALL_TEXT = "all_text_columns"
TARGET_COLUMNS_POLICY_SELECTED = "selected_columns"
SUPPORTED_TARGET_COLUMNS_POLICIES = (
    TARGET_COLUMNS_POLICY_ALL_TEXT,
    TARGET_COLUMNS_POLICY_SELECTED,
)
DEFAULT_PII_NATURAL_LANGUAGE = (
    "Redact common sensitive personal information from selected or text-like columns."
)
SAMPLE_VALUE_LIMIT = 10


@dataclass
class PiiPolicyServiceError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_502_BAD_GATEWAY


def generate_pii_redaction_policy(
    *,
    natural_language: str,
    target_columns: list[str],
    requested_pii_types: Optional[list[str]],
    requested_replacement_strategy: str,
    sample_values: list[str],
) -> dict[str, Any]:
    provider = os.getenv("LLM_PROVIDER", "openai_compatible").strip()
    if provider != "openai_compatible":
        raise PiiPolicyServiceError(
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
        raise PiiPolicyServiceError(
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
        requested_pii_types=requested_pii_types,
        requested_replacement_strategy=requested_replacement_strategy,
        sample_values=sample_values[:SAMPLE_VALUE_LIMIT],
    )
    return parse_pii_policy_json(raw_content)


def parse_pii_policy_json(raw_content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise PiiPolicyServiceError(
            code="LLM_INVALID_JSON",
            message="The LLM did not return valid JSON.",
        ) from exc

    if not isinstance(parsed, dict):
        raise PiiPolicyServiceError(
            code="LLM_INVALID_JSON",
            message="The LLM response JSON must be an object.",
        )

    return normalize_policy(parsed)


def resolve_policy(
    *,
    llm_policy: dict[str, Any],
    target_columns: list[str],
    requested_pii_types: Optional[list[str]],
    requested_replacement_strategy: str,
) -> dict[str, Any]:
    policy = normalize_policy(llm_policy)

    if requested_pii_types is not None:
        policy["pii_types"] = _normalize_pii_types(requested_pii_types)

    policy["replacement_strategy"] = _normalize_replacement_strategy(
        requested_replacement_strategy
    )
    policy["target_columns_policy"] = (
        TARGET_COLUMNS_POLICY_SELECTED
        if target_columns
        else TARGET_COLUMNS_POLICY_ALL_TEXT
    )

    return normalize_policy(policy)


def normalize_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise PiiPolicyServiceError(
            code="LLM_INVALID_JSON",
            message="The LLM response JSON must be an object.",
        )

    transformation_type = str(policy.get("transformation_type", "")).strip()
    if transformation_type != TRANSFORMATION_TYPE:
        raise PiiPolicyServiceError(
            code="UNSUPPORTED_TRANSFORMATION_RULE",
            message="The transformation policy must be for PII redaction.",
        )

    pii_types = _normalize_pii_types(policy.get("pii_types"))
    target_columns_policy = str(
        policy.get("target_columns_policy") or TARGET_COLUMNS_POLICY_ALL_TEXT
    ).strip()
    if target_columns_policy not in SUPPORTED_TARGET_COLUMNS_POLICIES:
        raise PiiPolicyServiceError(
            code="UNSUPPORTED_TRANSFORMATION_RULE",
            message="The PII redaction target column policy is not supported.",
        )

    replacement_strategy = _normalize_replacement_strategy(
        policy.get("replacement_strategy") or DEFAULT_REDACTION_STRATEGY
    )
    explanation = policy.get("explanation", "")

    return {
        "transformation_type": TRANSFORMATION_TYPE,
        "pii_types": pii_types,
        "target_columns_policy": target_columns_policy,
        "replacement_strategy": replacement_strategy,
        "explanation": str(explanation) if explanation is not None else "",
    }


def sample_pii_values(
    *,
    dataframe: pd.DataFrame,
    target_columns: list[str],
) -> list[str]:
    resolved_columns = pii_redactor.resolve_target_columns(dataframe, target_columns)
    sample_values = []

    for column in resolved_columns:
        for value in dataframe[column].head(50):
            if is_nullish(value):
                continue
            string_value = cell_to_string(value).strip()
            if not string_value:
                continue
            sample_values.append(string_value)
            if len(sample_values) == SAMPLE_VALUE_LIMIT:
                return sample_values

    return sample_values


def _normalize_pii_types(pii_types) -> list[str]:
    if pii_types is None:
        return list(SUPPORTED_PII_TYPES)

    if not isinstance(pii_types, list):
        raise PiiPolicyServiceError(
            code="LLM_INVALID_JSON",
            message="The PII policy pii_types field must be a list.",
        )

    normalized_types = []
    for pii_type in pii_types:
        normalized_type = str(pii_type).strip().lower()
        if normalized_type not in SUPPORTED_PII_TYPES:
            raise PiiPolicyServiceError(
                code="UNSUPPORTED_PII_TYPE",
                message=f"PII type '{pii_type}' is not supported.",
            )
        if normalized_type not in normalized_types:
            normalized_types.append(normalized_type)

    if not normalized_types:
        raise PiiPolicyServiceError(
            code="UNSUPPORTED_PII_TYPE",
            message="Choose at least one PII type to redact.",
        )

    return normalized_types


def _normalize_replacement_strategy(replacement_strategy) -> str:
    normalized_strategy = str(replacement_strategy).strip().lower()
    if normalized_strategy not in SUPPORTED_REDACTION_STRATEGIES:
        raise PiiPolicyServiceError(
            code="UNSUPPORTED_REPLACEMENT_STRATEGY",
            message=f"Replacement strategy '{replacement_strategy}' is not supported.",
        )

    return normalized_strategy


def _call_openai_compatible(
    *,
    api_key: str,
    base_url: str,
    model: str,
    natural_language: str,
    target_columns: list[str],
    requested_pii_types: Optional[list[str]],
    requested_replacement_strategy: str,
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
                    requested_pii_types=requested_pii_types,
                    requested_replacement_strategy=requested_replacement_strategy,
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
        raise PiiPolicyServiceError(
            code="LLM_API_ERROR",
            message="The LLM provider returned an error.",
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PiiPolicyServiceError(
            code="LLM_API_ERROR",
            message="The LLM provider could not be reached.",
        ) from exc

    try:
        content = response_payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise PiiPolicyServiceError(
            code="LLM_API_ERROR",
            message="The LLM provider response did not include message content.",
        ) from exc

    if not isinstance(content, str):
        raise PiiPolicyServiceError(
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
    return f"""You are a PII redaction policy assistant for a data-processing web application.

Return only valid JSON. Do not include markdown. Do not include explanations outside JSON.

Do not rewrite table data. Do not output transformed rows. Only generate a redaction policy.

The backend will execute deterministic regex and validation logic. Your policy only chooses supported options.

The JSON schema is:
{{
  "transformation_type": "pii_redaction",
  "pii_types": ["email" | "phone" | "credit_card" | "url"],
  "target_columns_policy": "all_text_columns" | "selected_columns",
  "replacement_strategy": "typed_placeholders" | "generic_redacted",
  "explanation": "string"
}}

Rules:
- transformation_type must be "{TRANSFORMATION_TYPE}".
- Supported pii_types are: {", ".join(SUPPORTED_PII_TYPES)}.
- Supported replacement_strategy values are: {", ".join(SUPPORTED_REDACTION_STRATEGIES)}.
- Use "{TARGET_COLUMNS_POLICY_SELECTED}" when target columns are provided.
- Use "{TARGET_COLUMNS_POLICY_ALL_TEXT}" when target columns are not provided.
- Prefer "{DEFAULT_REDACTION_STRATEGY}" unless the user asks for generic redaction.
- Never invent unsupported PII types or output row-level data."""


def _user_prompt(
    *,
    natural_language: str,
    target_columns: list[str],
    requested_pii_types: Optional[list[str]],
    requested_replacement_strategy: str,
    sample_values: list[str],
) -> str:
    if target_columns:
        column_lines = "\n".join(f"- {column}" for column in target_columns)
    else:
        column_lines = "No explicit columns selected. Use all text-like columns."

    requested_types = (
        ", ".join(requested_pii_types)
        if requested_pii_types
        else "No explicit PII types selected. Choose supported common PII types."
    )
    sample_lines = "\n".join(
        f"{index}. {value}" for index, value in enumerate(sample_values, start=1)
    )
    if not sample_lines:
        sample_lines = "No non-empty sample values were available."

    return f"""Target columns:
{column_lines}

Requested PII types:
{requested_types}

Requested replacement strategy:
{requested_replacement_strategy}

Sample values, capped at 10 values total:
{sample_lines}

User instruction:
{natural_language}"""
