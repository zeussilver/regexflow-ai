from dataclasses import dataclass
import re

import pandas as pd
from rest_framework import status


REPLACEMENT_PREVIEW_ROW_LIMIT = 50


@dataclass
class ReplacementProcessingError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST


def apply_regex_replacement(
    *,
    dataframe: pd.DataFrame,
    target_column: str,
    compiled_pattern: re.Pattern,
    replacement: str,
    preview_limit: int = REPLACEMENT_PREVIEW_ROW_LIMIT,
) -> dict:
    _ensure_column_exists(dataframe, target_column)

    processed_dataframe = dataframe.copy()
    checked_rows = int(len(processed_dataframe))
    matched_rows = 0
    total_matches = 0
    replaced_rows = 0

    for row_index, value in processed_dataframe[target_column].items():
        original_value = _cell_to_string(value)
        try:
            new_value, match_count = compiled_pattern.subn(replacement, original_value)
        except re.error as exc:
            raise ReplacementProcessingError(
                code="REGEX_REPLACEMENT_ERROR",
                message=f"The replacement value is not valid for this regex: {exc}.",
            ) from exc

        if match_count > 0:
            matched_rows += 1
            total_matches += match_count

        if new_value != original_value:
            replaced_rows += 1

        processed_dataframe.at[row_index, target_column] = new_value

    return {
        "processed_dataframe": processed_dataframe,
        "preview_dataframe": processed_dataframe.head(preview_limit),
        "preview_limit": int(preview_limit),
        "stats": {
            "checked_rows": checked_rows,
            "matched_rows": int(matched_rows),
            "total_matches": int(total_matches),
            "replaced_rows": int(replaced_rows),
        },
    }


def _ensure_column_exists(dataframe: pd.DataFrame, target_column: str) -> None:
    if target_column not in dataframe.columns:
        raise ReplacementProcessingError(
            code="COLUMN_NOT_FOUND",
            message=f"Column '{target_column}' was not found in the uploaded file.",
        )


def _cell_to_string(value) -> str:
    if value is None or pd.isna(value):
        return ""

    return str(value)
