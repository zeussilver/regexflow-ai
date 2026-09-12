"""Versioned deterministic phone rules. No model imports or generated explanations."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO

from django.core import signing
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.files.services import (
    resolve_uploaded_file,
    parse_tabular_file,
    save_processed_dataframe,
    UploadServiceError,
)
from apps.transformations.phone_normalizer import (
    apply_phone_normalization,
    PhoneNormalizationError,
)
from apps.transformations.transformation_stats import preview_records, cell_to_string
from .models import RuleGroup, PhoneRuleVersion, RuleExecution
from .serializers import ExecutionSerializer

TOKEN_SALT = "phone-rule-preview-v1"
TOKEN_MAX_AGE = 15 * 60


@dataclass
class RuleError(Exception):
    code: str
    message: str
    status_code: int = 400


@transaction.atomic
def save_version(parameters, source=None):
    group = source.group if source else RuleGroup.objects.create()
    # Serialize allocation with a write even on SQLite (select_for_update is a no-op there).
    RuleGroup.objects.filter(pk=group.pk).update(next_version=F("next_version") + 1)
    group.refresh_from_db()
    return PhoneRuleVersion.objects.create(
        group=group, version=group.next_version - 1, **parameters
    )


def snapshot(file_id):
    path, extension = resolve_uploaded_file(str(file_id))
    raw = path.read_bytes()
    return raw, extension, sha256(raw).hexdigest()


def transform(version, raw, extension):
    # Parse exactly the bytes whose digest was checked, avoiding a second file read.
    dataframe = parse_tabular_file(BytesIO(raw), extension)
    dataframe.columns = [str(column) for column in dataframe.columns]
    result = apply_phone_normalization(
        dataframe=dataframe,
        target_columns=[version.target_column],
        rule=version.parameters(),
    )
    original = dataframe[version.target_column].map(cell_to_string)
    processed = result["processed_dataframe"][version.target_column].map(cell_to_string)
    result["changed_rows"] = int((original != processed).sum())
    return dataframe, result


def payload(version, file_id, result):
    return {
        "transformation": "phone_normalization",
        "file_id": str(file_id),
        "target_columns": [version.target_column],
        "rule": result["rule"],
        "columns": list(result["processed_dataframe"].columns),
        "row_count": len(result["processed_dataframe"]),
        "preview_limit": result["preview_limit"],
        "processed_preview": preview_records(result["preview_dataframe"]),
        "stats": result["stats"],
        "changed_rows": result["changed_rows"],
        "warnings": result["warnings"],
    }


def preview(version, file_id):
    raw, extension, digest = snapshot(file_id)
    before, result = transform(version, raw, extension)
    return {
        **payload(version, file_id, result),
        "before_preview": preview_records(before),
        "confirmation_token": signing.dumps(
            {"file_id": str(file_id), "version_id": str(version.pk), "digest": digest},
            salt=TOKEN_SALT,
        ),
        "expires_in": TOKEN_MAX_AGE,
    }


def execute(version, token):
    try:
        claim = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
        if claim["version_id"] != str(version.pk):
            raise signing.BadSignature("Version mismatch")
    except (signing.BadSignature, KeyError, TypeError):
        raise RuleError(
            "PREVIEW_REQUIRED",
            "Confirmation is invalid or expired. Preview this file and version again.",
        )

    execution = RuleExecution.objects.create(
        rule_version=version, input_file_id=claim["file_id"]
    )
    try:
        raw, extension, digest = snapshot(claim["file_id"])
        if digest != claim["digest"]:
            raise RuleError("FILE_CHANGED", "The input file changed. Preview it again.")
        _, result = transform(version, raw, extension)
        try:
            output_id = save_processed_dataframe(result["processed_dataframe"])
        except Exception as exc:
            raise RuleError(
                "OUTPUT_SAVE_FAILED",
                "The output could not be saved. Preview and try again.",
                500,
            ) from exc
        response = payload(version, claim["file_id"], result)
        execution.output_file_id = output_id
        execution.changed_rows = result["changed_rows"]
        execution.status = "succeeded"
        execution.finished_at = timezone.now()
        execution.save()
        return {
            **response,
            "processed_file_id": output_id,
            "execution": ExecutionSerializer(execution).data,
        }, 200
    except Exception as exc:
        code, message, http_status = controlled_error(exc)
        execution.status = "failed"
        execution.output_file_id = None
        execution.changed_rows = None
        execution.error_code = code
        execution.finished_at = timezone.now()
        execution.save()
        return {
            "error": {"code": code, "message": message},
            "execution": ExecutionSerializer(execution).data,
        }, http_status


def controlled_error(exc):
    if isinstance(exc, RuleError):
        return exc.code, exc.message, exc.status_code
    messages = {
        "FILE_NOT_FOUND": "The input file is missing. Upload it again.",
        "FILE_PARSE_ERROR": "The input file could not be parsed.",
        "EMPTY_FILE": "The input file is empty.",
        "COLUMN_NOT_FOUND": "The rule's target column is missing from the input file.",
    }
    if (
        isinstance(exc, (UploadServiceError, PhoneNormalizationError))
        and exc.code in messages
    ):
        return exc.code, messages[exc.code], exc.status_code
    return (
        "PROCESSING_FAILED",
        "The rule could not be processed. Preview and try again.",
        500,
    )
