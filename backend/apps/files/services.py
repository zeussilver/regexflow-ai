from dataclasses import dataclass
import json
from pathlib import Path
from uuid import uuid4

import pandas as pd
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from rest_framework import status


PREVIEW_ROW_LIMIT = 50


@dataclass
class UploadServiceError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST


def save_and_parse_upload(uploaded_file) -> dict:
    file_id = str(uuid4())
    original_filename = Path(uploaded_file.name).name
    extension = Path(original_filename).suffix.lower()

    storage = FileSystemStorage(location=Path(settings.MEDIA_ROOT) / "uploads")
    stored_name = storage.save(f"{file_id}{extension}", uploaded_file)
    stored_path = Path(storage.path(stored_name))

    dataframe = parse_tabular_file(stored_path, extension)
    return dataframe_preview_response(file_id, original_filename, dataframe)


def parse_tabular_file(path: Path, extension: str) -> pd.DataFrame:
    try:
        if extension == ".csv":
            dataframe = pd.read_csv(path)
        elif extension == ".xlsx":
            dataframe = pd.read_excel(path, engine="openpyxl")
        else:
            raise UploadServiceError(
                code="UNSUPPORTED_FILE_TYPE",
                message="Only CSV and XLSX files are supported.",
            )
    except pd.errors.EmptyDataError as exc:
        raise UploadServiceError(
            code="EMPTY_FILE",
            message="The uploaded file is empty.",
        ) from exc
    except UploadServiceError:
        raise
    except Exception as exc:
        raise UploadServiceError(
            code="FILE_PARSE_ERROR",
            message="The file could not be parsed. Please check the file format.",
        ) from exc

    if len(dataframe.columns) == 0:
        raise UploadServiceError(
            code="EMPTY_FILE",
            message="The uploaded file is empty.",
        )

    return dataframe


def dataframe_preview_response(
    file_id: str,
    filename: str,
    dataframe: pd.DataFrame,
) -> dict:
    normalized_dataframe = dataframe.copy()
    normalized_dataframe.columns = [str(column) for column in normalized_dataframe.columns]

    preview_json = normalized_dataframe.head(PREVIEW_ROW_LIMIT).to_json(
        orient="records",
        date_format="iso",
    )

    return {
        "file_id": file_id,
        "filename": filename,
        "columns": list(normalized_dataframe.columns),
        "row_count": int(len(normalized_dataframe)),
        "preview_rows": json.loads(preview_json),
    }
