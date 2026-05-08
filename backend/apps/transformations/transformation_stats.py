import json

import pandas as pd


PREVIEW_ROW_LIMIT = 50


def normalize_dataframe_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    normalized_dataframe = dataframe.copy()
    normalized_dataframe.columns = [str(column) for column in normalized_dataframe.columns]
    return normalized_dataframe


def preview_records(
    dataframe: pd.DataFrame,
    limit: int = PREVIEW_ROW_LIMIT,
) -> list[dict]:
    preview_json = dataframe.head(limit).to_json(
        orient="records",
        date_format="iso",
    )
    return json.loads(preview_json)


def cell_to_string(value) -> str:
    if is_nullish(value):
        return ""

    return str(value)


def is_nullish(value) -> bool:
    if value is None:
        return True

    try:
        is_missing = pd.isna(value)
    except (TypeError, ValueError):
        return False

    return bool(is_missing) if isinstance(is_missing, bool) else False
