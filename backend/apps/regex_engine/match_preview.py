from dataclasses import dataclass
import re
from typing import Any, Optional

import pandas as pd
from rest_framework import status

from apps.files.services import UploadServiceError, parse_tabular_file, resolve_uploaded_file


MATCH_PREVIEW_ROW_LIMIT = 50
MATCH_PREVIEW_EXAMPLE_LIMIT = 5
SAMPLE_VALUE_LIMIT = 10
SAMPLE_ROW_LIMIT = 10
SAMPLE_ROW_COLUMN_LIMIT = 12
SAMPLE_CELL_CHARACTER_LIMIT = 120
MATCHES_PER_EXAMPLE_LIMIT = 10
LOOKUP_PROMPT_MARKERS = (
    "what is",
    "what's",
    "which",
    "whose",
    "对应",
    "属于",
    "的",
)


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


def get_row_sample_context(dataframe: pd.DataFrame) -> list[dict[str, str]]:
    columns = [str(column) for column in dataframe.columns[:SAMPLE_ROW_COLUMN_LIMIT]]
    samples = []

    for _, row in dataframe.head(SAMPLE_ROW_LIMIT).iterrows():
        sample_row = {}
        for column in columns:
            string_value = _cell_to_string(row[column]).strip()
            if string_value:
                sample_row[column] = _truncate_sample_cell(string_value)
        if sample_row:
            samples.append(sample_row)

    return samples


def resolve_contextual_target_regex(
    *,
    dataframe: pd.DataFrame,
    target_column: str,
    natural_language: str,
) -> Optional[dict[str, Any]]:
    _ensure_column_exists(dataframe, target_column)

    normalized_prompt = _normalize_lookup_text(natural_language)
    if not _looks_like_row_lookup(normalized_prompt):
        return None

    best_match = None
    best_match_length = 0

    for row_index, row in dataframe.head(MATCH_PREVIEW_ROW_LIMIT).iterrows():
        target_value = _cell_to_string(row[target_column]).strip()
        if not target_value:
            continue

        for column in dataframe.columns:
            column_name = str(column)
            if column_name == target_column:
                continue

            candidate_value = _cell_to_string(row[column_name]).strip()
            normalized_candidate = _normalize_lookup_text(candidate_value)
            if len(normalized_candidate) < 3:
                continue

            if (
                normalized_candidate in normalized_prompt
                and len(normalized_candidate) > best_match_length
            ):
                best_match = {
                    "row_index": int(row_index),
                    "lookup_column": column_name,
                    "lookup_value": candidate_value,
                    "target_value": target_value,
                }
                best_match_length = len(normalized_candidate)

    if not best_match:
        return None

    escaped_value = _exact_value_regex(best_match["target_value"])
    return {
        "regex": escaped_value,
        "flags": [],
        "explanation": (
            f"Matches the {target_column} value from the row where "
            f"{best_match['lookup_column']} is {best_match['lookup_value']}."
        ),
        "confidence": "high",
    }


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


def _truncate_sample_cell(value: str) -> str:
    if len(value) <= SAMPLE_CELL_CHARACTER_LIMIT:
        return value

    return f"{value[:SAMPLE_CELL_CHARACTER_LIMIT - 1]}..."


def _exact_value_regex(value: str) -> str:
    return re.escape(value).replace(r"\ ", " ")


def _normalize_lookup_text(value: str) -> str:
    return " ".join(str(value).casefold().replace("’", "'").split())


def _looks_like_row_lookup(normalized_prompt: str) -> bool:
    if not normalized_prompt:
        return False

    if any(marker in normalized_prompt for marker in LOOKUP_PROMPT_MARKERS):
        return True

    return "'s" in normalized_prompt
