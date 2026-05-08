from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.responses import error_response
from apps.files.services import save_processed_dataframe
from apps.regex_engine import match_preview

from . import phone_normalizer, phone_rule_service, pii_redactor
from .serializers import PhoneNormalizeSerializer, PiiRedactSerializer
from .transformation_stats import cell_to_string, is_nullish, preview_records


class PiiRedactView(APIView):
    def post(self, request):
        serializer = PiiRedactSerializer(data=request.data)
        if not serializer.is_valid():
            return self._serializer_error_response(serializer)

        file_id = serializer.validated_data["file_id"]
        target_columns = serializer.validated_data.get("target_columns", [])
        pii_types = serializer.validated_data.get("pii_types")
        replacement_strategy = serializer.validated_data["replacement_strategy"]

        try:
            dataframe = match_preview.load_uploaded_dataframe(file_id)
            redaction_result = pii_redactor.apply_pii_redaction(
                dataframe=dataframe,
                target_columns=target_columns,
                pii_types=pii_types,
                replacement_strategy=replacement_strategy,
            )
            processed_file_id = save_processed_dataframe(
                redaction_result["processed_dataframe"]
            )
            processed_preview = preview_records(redaction_result["preview_dataframe"])
        except match_preview.MatchPreviewError as exc:
            return _file_error_response(exc)
        except pii_redactor.PiiRedactionError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except Exception:
            return error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred while redacting PII.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "transformation": "pii_redaction",
                "file_id": file_id,
                "processed_file_id": processed_file_id,
                "target_columns": redaction_result["target_columns"],
                "pii_types": pii_types or list(pii_redactor.SUPPORTED_PII_TYPES),
                "replacement_strategy": replacement_strategy,
                "columns": list(redaction_result["processed_dataframe"].columns),
                "row_count": int(len(redaction_result["processed_dataframe"])),
                "preview_limit": redaction_result["preview_limit"],
                "processed_preview": processed_preview,
                "stats": redaction_result["stats"],
                "warnings": redaction_result["warnings"],
            }
        )

    @staticmethod
    def _serializer_error_response(serializer):
        return _serializer_error_response(
            serializer,
            field_error_codes={
                "file_id": "FILE_NOT_FOUND",
                "target_columns": "COLUMN_NOT_FOUND",
                "pii_types": "UNSUPPORTED_PII_TYPE",
                "replacement_strategy": "UNSUPPORTED_REPLACEMENT_STRATEGY",
            },
            field_error_messages={
                "file_id": "The uploaded file could not be found. Please upload the file again.",
                "target_columns": "Choose at least one column before redacting PII.",
                "pii_types": "Choose supported PII types to redact.",
                "replacement_strategy": "Choose a supported replacement strategy.",
            },
            ordered_fields=(
                "file_id",
                "target_columns",
                "pii_types",
                "replacement_strategy",
            ),
        )


class PhoneNormalizeView(APIView):
    def post(self, request):
        serializer = PhoneNormalizeSerializer(data=request.data)
        if not serializer.is_valid():
            return self._serializer_error_response(serializer)

        file_id = serializer.validated_data["file_id"]
        target_columns = serializer.validated_data["target_columns"]

        try:
            dataframe = match_preview.load_uploaded_dataframe(file_id)
            rule = self._resolve_rule(
                dataframe=dataframe,
                target_columns=target_columns,
                validated_data=serializer.validated_data,
            )
            normalization_result = phone_normalizer.apply_phone_normalization(
                dataframe=dataframe,
                target_columns=target_columns,
                rule=rule,
            )
            processed_file_id = save_processed_dataframe(
                normalization_result["processed_dataframe"]
            )
            processed_preview = preview_records(
                normalization_result["preview_dataframe"]
            )
        except match_preview.MatchPreviewError as exc:
            return _file_error_response(exc)
        except phone_rule_service.PhoneRuleServiceError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except phone_normalizer.PhoneNormalizationError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except Exception:
            return error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred while normalizing phone numbers.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "transformation": "phone_normalization",
                "file_id": file_id,
                "processed_file_id": processed_file_id,
                "target_columns": target_columns,
                "rule": normalization_result["rule"],
                "columns": list(normalization_result["processed_dataframe"].columns),
                "row_count": int(len(normalization_result["processed_dataframe"])),
                "preview_limit": normalization_result["preview_limit"],
                "processed_preview": processed_preview,
                "stats": normalization_result["stats"],
                "warnings": normalization_result["warnings"],
            }
        )

    @staticmethod
    def _resolve_rule(*, dataframe, target_columns, validated_data):
        explicit_rule = dict(validated_data.get("rule") or {})
        for field_name in ("target_format", "default_region", "preserve_invalid"):
            if field_name in validated_data:
                explicit_rule[field_name] = validated_data[field_name]

        natural_language = validated_data.get("natural_language", "")
        sample_values = _sample_phone_values(dataframe, target_columns)
        llm_rule = phone_rule_service.generate_phone_normalization_rule(
            natural_language=natural_language,
            target_columns=target_columns,
            sample_values=sample_values,
        )
        llm_rule.update(explicit_rule)
        return llm_rule

    @staticmethod
    def _serializer_error_response(serializer):
        return _serializer_error_response(
            serializer,
            field_error_codes={
                "file_id": "FILE_NOT_FOUND",
                "target_columns": "COLUMN_NOT_FOUND",
                "natural_language": "EMPTY_NATURAL_LANGUAGE",
                "rule": "PHONE_RULE_INVALID",
                "target_format": "UNSUPPORTED_TARGET_FORMAT",
                "default_region": "INVALID_DEFAULT_REGION",
                "preserve_invalid": "PHONE_RULE_INVALID",
            },
            field_error_messages={
                "file_id": "The uploaded file could not be found. Please upload the file again.",
                "target_columns": "Choose at least one column before normalizing phone numbers.",
                "natural_language": "Describe how phone numbers should be normalized.",
                "rule": "Provide a valid phone normalization rule.",
                "target_format": "Choose a supported phone output format.",
                "default_region": "Use a two-letter default region code.",
                "preserve_invalid": "preserve_invalid must be true or false.",
            },
            ordered_fields=(
                "file_id",
                "target_columns",
                "natural_language",
                "rule",
                "target_format",
                "default_region",
                "preserve_invalid",
            ),
        )


def _sample_phone_values(dataframe, target_columns: list[str]) -> list[str]:
    sample_values = []
    for column in target_columns:
        if column not in dataframe.columns:
            raise phone_normalizer.PhoneNormalizationError(
                code="COLUMN_NOT_FOUND",
                message=f"Column '{column}' was not found in the uploaded file.",
            )

        for value in dataframe[column].head(50):
            if is_nullish(value):
                continue
            string_value = cell_to_string(value).strip()
            if not string_value:
                continue
            sample_values.append(string_value)
            if len(sample_values) == phone_rule_service.SAMPLE_VALUE_LIMIT:
                return sample_values

    return sample_values


def _serializer_error_response(
    serializer,
    *,
    field_error_codes: dict,
    field_error_messages: dict,
    ordered_fields: tuple[str, ...],
):
    for field_name in ordered_fields:
        field_errors = serializer.errors.get(field_name)
        if not field_errors:
            continue

        first_error = _first_serializer_error(field_errors)
        code = str(getattr(first_error, "code", field_error_codes[field_name]))
        message = str(first_error) or field_error_messages[field_name]

        if code in {"required", "blank", "null", "invalid", "empty"}:
            code = field_error_codes[field_name]
            message = field_error_messages[field_name]

        return error_response(code=code, message=message)

    return error_response(
        code="INTERNAL_ERROR",
        message="The transformation request could not be validated.",
    )


def _file_error_response(exc):
    if exc.code == "FILE_NOT_FOUND":
        return error_response(exc.code, exc.message, exc.status_code)

    return error_response(
        code="FILE_PARSE_ERROR",
        message="The file could not be parsed. Please check the file format.",
        http_status=exc.status_code,
    )


def _first_serializer_error(field_errors):
    if isinstance(field_errors, dict):
        for nested_errors in field_errors.values():
            return _first_serializer_error(nested_errors)

    if isinstance(field_errors, (list, tuple)) and field_errors:
        return _first_serializer_error(field_errors[0])

    return field_errors
