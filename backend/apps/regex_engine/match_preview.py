from dataclasses import dataclass
import re

import pandas as pd
from rest_framework import status

from apps.files.services import UploadServiceError, parse_tabular_file, resolve_uploaded_file


MATCH_PREVIEW_ROW_LIMIT = 50
MATCH_PREVIEW_EXAMPLE_LIMIT = 5
SAMPLE_VALUE_LIMIT = 10
MATCHES_PER_EXAMPLE_LIMIT = 10


@dataclass
class MatchPreviewError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST


def load_uploaded_dataframe(file_id: str) -> pd.DataFrame:
    try:
        path, extension = resolve_uploaded_file(file_id)
        dataframe = parse_tabular_file(path, extension)
    except UploadServiceError as exc:
        raise MatchPreviewError(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
        ) from exc

    normalized_dataframe = dataframe.copy()
    normalized_dataframe.columns = [str(column) for column in normalized_dataframe.columns]
    return normalized_dataframe


def get_column_sample_values(dataframe: pd.DataFrame, target_column: str) -> list[str]:
    _ensure_column_exists(dataframe, target_column)

    samples = []
    for value in dataframe[target_column].head(MATCH_PREVIEW_ROW_LIMIT):
        string_value = _cell_to_string(value)
        if string_value:
            samples.append(string_value)
        if len(samples) == SAMPLE_VALUE_LIMIT:
            break

    return samples


def build_match_preview(
    *,
    dataframe: pd.DataFrame,
    target_column: str,
    compiled_pattern: re.Pattern,
) -> dict:
    _ensure_column_exists(dataframe, target_column)

    checked_values = dataframe[target_column].head(MATCH_PREVIEW_ROW_LIMIT)
    matched_rows = 0
    examples = []

    for row_index, value in checked_values.items():
        string_value = _cell_to_string(value)
        matches = [
            match.group(0)
            for match in compiled_pattern.finditer(string_value)
        ][:MATCHES_PER_EXAMPLE_LIMIT]

        if not matches:
            continue

        matched_rows += 1
        if len(examples) < MATCH_PREVIEW_EXAMPLE_LIMIT:
            examples.append(
                {
                    "row_index": int(row_index),
                    "value": string_value,
                    "matches": matches,
                }
            )

    return {
        "checked_rows": int(len(checked_values)),
        "matched_rows": int(matched_rows),
        "examples": examples,
    }


def _ensure_column_exists(dataframe: pd.DataFrame, target_column: str) -> None:
    if target_column not in dataframe.columns:
        raise MatchPreviewError(
            code="COLUMN_NOT_FOUND",
            message=f"Column '{target_column}' was not found in the uploaded file.",
        )


def _cell_to_string(value) -> str:
    if value is None or pd.isna(value):
        return ""

    return str(value)
