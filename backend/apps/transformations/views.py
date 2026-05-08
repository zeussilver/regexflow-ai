from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.responses import error_response
from apps.regex_engine import match_preview

from . import (
    phone_normalizer,
    phone_rule_service,
    pii_policy_service,
    pii_redactor,
    services as transformation_services,
)
from .serializers import PhoneNormalizeSerializer, PiiRedactSerializer


class PiiRedactView(APIView):
    def post(self, request):
        serializer = PiiRedactSerializer(data=request.data)
        if not serializer.is_valid():
            return self._serializer_error_response(serializer)

        file_id = serializer.validated_data["file_id"]
        target_columns = serializer.validated_data.get("target_columns", [])
        natural_language = serializer.validated_data["natural_language"]
        pii_types = serializer.validated_data.get("pii_types")
        replacement_strategy = serializer.validated_data["replacement_strategy"]

        try:
            payload = transformation_services.run_pii_redaction(
                file_id=file_id,
                target_columns=target_columns,
                natural_language=natural_language,
                pii_types=pii_types,
                replacement_strategy=replacement_strategy,
            )
        except match_preview.MatchPreviewError as exc:
            return _file_error_response(exc)
        except pii_policy_service.PiiPolicyServiceError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except pii_redactor.PiiRedactionError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except Exception:
            return error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred while redacting PII.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(payload)

    @staticmethod
    def _serializer_error_response(serializer):
        return _serializer_error_response(
            serializer,
            field_error_codes={
                "file_id": "FILE_NOT_FOUND",
                "target_columns": "COLUMN_NOT_FOUND",
                "natural_language": "EMPTY_NATURAL_LANGUAGE",
                "pii_types": "UNSUPPORTED_PII_TYPE",
                "replacement_strategy": "UNSUPPORTED_REPLACEMENT_STRATEGY",
            },
            field_error_messages={
                "file_id": "The uploaded file could not be found. Please upload the file again.",
                "target_columns": "Choose at least one column before redacting PII.",
                "natural_language": "Describe the PII redaction policy to generate.",
                "pii_types": "Choose supported PII types to redact.",
                "replacement_strategy": "Choose a supported replacement strategy.",
            },
            ordered_fields=(
                "file_id",
                "target_columns",
                "natural_language",
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
            payload = transformation_services.run_phone_normalization(
                file_id=file_id,
                target_columns=target_columns,
                validated_data=serializer.validated_data,
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

        return Response(payload)

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
