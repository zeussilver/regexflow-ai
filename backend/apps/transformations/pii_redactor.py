from dataclasses import dataclass
from typing import Callable

import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype
from rest_framework import status

from .pii_patterns import (
    CREDIT_CARD_CANDIDATE_PATTERN,
    DEFAULT_REDACTION_STRATEGY,
    EMAIL_PATTERN,
    PHONE_CANDIDATE_PATTERN,
    REDACTION_ORDER,
    SUPPORTED_PII_TYPES,
    SUPPORTED_REDACTION_STRATEGIES,
    URL_PATTERN,
    is_luhn_valid,
    is_phone_candidate,
    placeholder_for,
)
from .transformation_stats import PREVIEW_ROW_LIMIT, cell_to_string, is_nullish


@dataclass
class PiiRedactionError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST


def apply_pii_redaction(
    *,
    dataframe: pd.DataFrame,
    target_columns: list[str] | None = None,
    pii_types: list[str] | None = None,
    replacement_strategy: str = DEFAULT_REDACTION_STRATEGY,
) -> dict:
    normalized_target_columns = resolve_target_columns(dataframe, target_columns)
    normalized_pii_types = _normalize_pii_types(pii_types)
    _validate_replacement_strategy(replacement_strategy)

    processed_dataframe = dataframe.copy()
    stats = _empty_stats()
    stats["checked_cells"] = int(len(processed_dataframe) * len(normalized_target_columns))

    for column in normalized_target_columns:
        processed_dataframe[column] = processed_dataframe[column].astype("object")
        for row_index, value in processed_dataframe[column].items():
            if is_nullish(value):
                continue

            original_value = cell_to_string(value)
            redacted_value, counts = redact_text(
                original_value,
                pii_types=normalized_pii_types,
                replacement_strategy=replacement_strategy,
            )

            replacement_count = sum(counts.values())
            if replacement_count == 0:
                continue

            processed_dataframe.at[row_index, column] = redacted_value
            stats["changed_cells"] += 1
            stats["total_replacements"] += replacement_count

            for pii_type, count in counts.items():
                if count == 0:
                    continue
                stats["by_type"][pii_type]["matches"] += count
                stats["by_type"][pii_type]["changed_cells"] += 1

    warnings = []
    if stats["total_replacements"] == 0:
        warnings.append("No supported PII values were found in the selected columns.")

    return {
        "processed_dataframe": processed_dataframe,
        "preview_dataframe": processed_dataframe.head(PREVIEW_ROW_LIMIT),
        "preview_limit": PREVIEW_ROW_LIMIT,
        "target_columns": normalized_target_columns,
        "stats": stats,
        "warnings": warnings,
    }


def redact_text(
    value: str,
    *,
    pii_types: list[str],
    replacement_strategy: str,
) -> tuple[str, dict[str, int]]:
    redacted_value = value
    counts = {pii_type: 0 for pii_type in SUPPORTED_PII_TYPES}

    for pii_type in REDACTION_ORDER:
        if pii_type not in pii_types:
            continue

        redacted_value, replacement_count = _redact_type(
            redacted_value,
            pii_type=pii_type,
            replacement_strategy=replacement_strategy,
        )
        counts[pii_type] += replacement_count

    return redacted_value, counts


def resolve_target_columns(
    dataframe: pd.DataFrame,
    target_columns: list[str] | None,
) -> list[str]:
    if target_columns:
        _ensure_columns_exist(dataframe, target_columns)
        return target_columns

    text_columns = [
        str(column)
        for column in dataframe.columns
        if _is_text_like_column(dataframe[column])
    ]
    if not text_columns:
        raise PiiRedactionError(
            code="NO_TARGET_COLUMNS",
            message="No text-like columns are available for PII redaction.",
        )

    return text_columns


def _redact_type(
    value: str,
    *,
    pii_type: str,
    replacement_strategy: str,
) -> tuple[str, int]:
    replacement = placeholder_for(pii_type, replacement_strategy)

    if pii_type == "url":
        return _sub_with_count(URL_PATTERN, value, lambda _: replacement)

    if pii_type == "email":
        return _sub_with_count(EMAIL_PATTERN, value, lambda _: replacement)

    if pii_type == "credit_card":
        return _sub_with_count(
            CREDIT_CARD_CANDIDATE_PATTERN,
            value,
            lambda match: replacement if is_luhn_valid(match.group(0)) else match.group(0),
            count_when=lambda original, replaced: original != replaced,
        )

    if pii_type == "phone":
        return _sub_with_count(
            PHONE_CANDIDATE_PATTERN,
            value,
            lambda match: replacement if is_phone_candidate(match.group(0)) else match.group(0),
            count_when=lambda original, replaced: original != replaced,
        )

    return value, 0


def _sub_with_count(
    pattern,
    value: str,
    replacement_factory: Callable,
    *,
    count_when: Callable[[str, str], bool] | None = None,
) -> tuple[str, int]:
    replacements = 0

    def replace(match):
        nonlocal replacements
        original = match.group(0)
        replacement = replacement_factory(match)
        should_count = True
        if count_when is not None:
            should_count = count_when(original, replacement)

        if should_count:
            replacements += 1
        return replacement

    return pattern.sub(replace, value), replacements


def _normalize_pii_types(pii_types: list[str] | None) -> list[str]:
    if pii_types is None:
        return list(SUPPORTED_PII_TYPES)

    normalized_types = []
    for pii_type in pii_types:
        normalized_type = str(pii_type).strip().lower()
        if normalized_type not in SUPPORTED_PII_TYPES:
            raise PiiRedactionError(
                code="UNSUPPORTED_PII_TYPE",
                message=f"PII type '{pii_type}' is not supported.",
            )
        if normalized_type not in normalized_types:
            normalized_types.append(normalized_type)

    if not normalized_types:
        raise PiiRedactionError(
            code="UNSUPPORTED_PII_TYPE",
            message="Choose at least one PII type to redact.",
        )

    return normalized_types


def _validate_replacement_strategy(replacement_strategy: str) -> None:
    if replacement_strategy not in SUPPORTED_REDACTION_STRATEGIES:
        raise PiiRedactionError(
            code="UNSUPPORTED_REPLACEMENT_STRATEGY",
            message=f"Replacement strategy '{replacement_strategy}' is not supported.",
        )


def _ensure_columns_exist(dataframe: pd.DataFrame, target_columns: list[str]) -> None:
    missing_columns = [column for column in target_columns if column not in dataframe.columns]
    if missing_columns:
        raise PiiRedactionError(
            code="COLUMN_NOT_FOUND",
            message=f"Column '{missing_columns[0]}' was not found in the uploaded file.",
        )


def _empty_stats() -> dict:
    return {
        "checked_cells": 0,
        "changed_cells": 0,
        "total_replacements": 0,
        "by_type": {
            pii_type: {
                "matches": 0,
                "changed_cells": 0,
            }
            for pii_type in SUPPORTED_PII_TYPES
        },
    }


def _is_text_like_column(series: pd.Series) -> bool:
    return (
        is_string_dtype(series.dtype)
        or is_object_dtype(series.dtype)
        or str(series.dtype) == "category"
    )
