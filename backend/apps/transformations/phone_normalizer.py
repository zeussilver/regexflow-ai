from dataclasses import dataclass

import pandas as pd
import phonenumbers
from rest_framework import status

from .transformation_stats import PREVIEW_ROW_LIMIT, cell_to_string, is_nullish


TRANSFORMATION_TYPE = "phone_normalization"
ALLOWED_PHONE_FORMATS = ("E164", "INTERNATIONAL", "NATIONAL", "RFC3966")
DEFAULT_PHONE_FORMAT = "E164"
DEFAULT_REGION = "AU"

PHONE_FORMAT_MAP = {
    "E164": phonenumbers.PhoneNumberFormat.E164,
    "INTERNATIONAL": phonenumbers.PhoneNumberFormat.INTERNATIONAL,
    "NATIONAL": phonenumbers.PhoneNumberFormat.NATIONAL,
    "RFC3966": phonenumbers.PhoneNumberFormat.RFC3966,
}


@dataclass
class PhoneNormalizationError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST


def apply_phone_normalization(
    *,
    dataframe: pd.DataFrame,
    target_columns: list[str],
    rule: dict,
) -> dict:
    _ensure_columns_exist(dataframe, target_columns)
    normalized_rule = normalize_rule(rule)

    processed_dataframe = dataframe.copy()
    stats = _empty_stats()

    for column in target_columns:
        processed_dataframe[column] = processed_dataframe[column].astype("object")
        for row_index, value in processed_dataframe[column].items():
            if is_nullish(value):
                continue

            original_value = cell_to_string(value).strip()
            if not original_value:
                continue

            stats["checked_cells"] += 1
            normalized_value, is_valid, changed = normalize_phone_value(
                original_value,
                rule=normalized_rule,
            )

            if not is_valid:
                stats["invalid_cells"] += 1
                if not changed:
                    stats["unchanged_cells"] += 1
                else:
                    processed_dataframe.at[row_index, column] = normalized_value
                continue

            if changed:
                processed_dataframe.at[row_index, column] = normalized_value
                stats["normalized_cells"] += 1
            else:
                stats["unchanged_cells"] += 1

    warnings = _build_warnings(stats, normalized_rule)

    return {
        "processed_dataframe": processed_dataframe,
        "preview_dataframe": processed_dataframe.head(PREVIEW_ROW_LIMIT),
        "preview_limit": PREVIEW_ROW_LIMIT,
        "rule": normalized_rule,
        "stats": stats,
        "warnings": warnings,
    }


def normalize_phone_value(value: str, *, rule: dict) -> tuple[str, bool, bool]:
    try:
        parsed_number = phonenumbers.parse(value, rule["default_region"])
    except phonenumbers.NumberParseException:
        return _invalid_value(value, rule)

    if not phonenumbers.is_valid_number(parsed_number):
        return _invalid_value(value, rule)

    normalized_value = phonenumbers.format_number(
        parsed_number,
        PHONE_FORMAT_MAP[rule["target_format"]],
    )
    return normalized_value, True, normalized_value != value


def normalize_rule(rule: dict | None) -> dict:
    if not isinstance(rule, dict):
        raise PhoneNormalizationError(
            code="INVALID_TRANSFORMATION_RULE",
            message="Phone normalization requires a valid transformation rule.",
        )

    transformation_type = str(rule.get("transformation_type", "")).strip()
    if transformation_type != TRANSFORMATION_TYPE:
        raise PhoneNormalizationError(
            code="INVALID_TRANSFORMATION_RULE",
            message="The transformation rule must be for phone normalization.",
        )

    target_format = str(
        rule.get("target_format") or rule.get("format") or DEFAULT_PHONE_FORMAT
    ).strip().upper()
    default_region = str(
        rule.get("default_region") or rule.get("region") or DEFAULT_REGION
    ).strip().upper()
    preserve_invalid = rule.get("preserve_invalid", True)

    if target_format not in ALLOWED_PHONE_FORMATS:
        raise PhoneNormalizationError(
            code="UNSUPPORTED_TARGET_FORMAT",
            message=f"Phone format '{target_format}' is not supported.",
        )

    if default_region not in phonenumbers.SUPPORTED_REGIONS:
        raise PhoneNormalizationError(
            code="INVALID_DEFAULT_REGION",
            message=f"Default region '{default_region}' is not supported.",
        )

    if not isinstance(preserve_invalid, bool):
        preserve_invalid = str(preserve_invalid).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    explanation = rule.get("explanation", "")

    return {
        "transformation_type": TRANSFORMATION_TYPE,
        "target_format": target_format,
        "default_region": default_region,
        "preserve_invalid": preserve_invalid,
        "explanation": str(explanation) if explanation is not None else "",
    }


def _invalid_value(value: str, rule: dict) -> tuple[str, bool, bool]:
    if rule["preserve_invalid"]:
        return value, False, False

    return "", False, value != ""


def _ensure_columns_exist(dataframe: pd.DataFrame, target_columns: list[str]) -> None:
    missing_columns = [column for column in target_columns if column not in dataframe.columns]
    if missing_columns:
        raise PhoneNormalizationError(
            code="COLUMN_NOT_FOUND",
            message=f"Column '{missing_columns[0]}' was not found in the uploaded file.",
        )


def _empty_stats() -> dict:
    return {
        "checked_cells": 0,
        "normalized_cells": 0,
        "invalid_cells": 0,
        "unchanged_cells": 0,
    }


def _build_warnings(stats: dict, rule: dict) -> list[str]:
    warnings = []
    if stats["checked_cells"] == 0:
        warnings.append("No non-empty phone values were found in the selected columns.")

    if stats["invalid_cells"] > 0 and rule["preserve_invalid"]:
        value_label = "value" if stats["invalid_cells"] == 1 else "values"
        warnings.append(
            f"{stats['invalid_cells']} {value_label} could not be parsed as a valid "
            "phone number and was left unchanged."
        )
    elif stats["invalid_cells"] > 0:
        value_label = "value" if stats["invalid_cells"] == 1 else "values"
        warnings.append(
            f"{stats['invalid_cells']} {value_label} could not be parsed as a valid "
            "phone number and was cleared."
        )

    return warnings
