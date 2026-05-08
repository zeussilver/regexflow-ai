import json

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.responses import error_response
from apps.files.services import save_processed_dataframe

from . import llm_service, match_preview, regex_validator, replacement_processor
from .serializers import RegexGenerateSerializer, RegexReplaceSerializer


class RegexGenerateView(APIView):
    def post(self, request):
        serializer = RegexGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return self._serializer_error_response(serializer)

        file_id = serializer.validated_data["file_id"]
        target_column = serializer.validated_data["target_column"]
        natural_language = serializer.validated_data["natural_language"]

        try:
            dataframe = match_preview.load_uploaded_dataframe(file_id)
            sample_values = match_preview.get_column_sample_values(dataframe, target_column)
            llm_result = llm_service.generate_regex(
                natural_language=natural_language,
                target_column=target_column,
                sample_values=sample_values,
            )
            if not isinstance(llm_result, dict):
                raise llm_service.LLMServiceError(
                    code="LLM_INVALID_JSON",
                    message="The LLM response JSON must be an object.",
                )
            validated_regex = regex_validator.validate_regex(
                llm_result.get("regex"),
                flags=llm_result.get("flags", []),
            )
            preview = match_preview.build_match_preview(
                dataframe=dataframe,
                target_column=target_column,
                compiled_pattern=validated_regex.compiled_pattern,
            )
        except match_preview.MatchPreviewError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except llm_service.LLMServiceError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except regex_validator.RegexValidationError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except Exception:
            return error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred while generating the regex.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "regex": validated_regex.pattern,
                "flags": llm_result.get("flags", []),
                "explanation": llm_result.get("explanation", ""),
                "target_column": target_column,
                "match_preview": preview,
                "warnings": validated_regex.warnings,
            }
        )

    @staticmethod
    def _serializer_error_response(serializer):
        field_error_codes = {
            "file_id": "FILE_NOT_FOUND",
            "target_column": "COLUMN_NOT_FOUND",
            "natural_language": "EMPTY_NATURAL_LANGUAGE",
        }
        field_error_messages = {
            "file_id": "The uploaded file could not be found. Please upload the file again.",
            "target_column": "Choose a column before generating a regex.",
            "natural_language": "Describe the pattern you want to find.",
        }

        for field_name in ("file_id", "target_column", "natural_language"):
            field_errors = serializer.errors.get(field_name)
            if not field_errors:
                continue

            first_error = field_errors[0]
            code = str(getattr(first_error, "code", field_error_codes[field_name]))
            message = str(first_error) or field_error_messages[field_name]

            if code == "required" or code == "blank":
                code = field_error_codes[field_name]
                message = field_error_messages[field_name]

            return error_response(code=code, message=message)

        return error_response(
            code="INTERNAL_ERROR",
            message="The regex generation request could not be validated.",
        )


class RegexReplaceView(APIView):
    def post(self, request):
        serializer = RegexReplaceSerializer(data=request.data)
        if not serializer.is_valid():
            return self._serializer_error_response(serializer)

        file_id = serializer.validated_data["file_id"]
        target_column = serializer.validated_data["target_column"]
        regex = serializer.validated_data["regex"]
        flags = serializer.validated_data.get("flags", [])
        replacement = serializer.validated_data["replacement"]

        try:
            dataframe = match_preview.load_uploaded_dataframe(file_id)
            validated_regex = regex_validator.validate_regex(regex, flags=flags)
            replacement_result = replacement_processor.apply_regex_replacement(
                dataframe=dataframe,
                target_column=target_column,
                compiled_pattern=validated_regex.compiled_pattern,
                replacement=replacement,
            )
            processed_file_id = save_processed_dataframe(
                replacement_result["processed_dataframe"]
            )
            processed_preview = json.loads(
                replacement_result["preview_dataframe"].to_json(
                    orient="records",
                    date_format="iso",
                )
            )
        except match_preview.MatchPreviewError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except regex_validator.RegexValidationError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except replacement_processor.ReplacementProcessingError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except Exception:
            return error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred while applying the replacement.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        warnings = list(validated_regex.warnings)
        if replacement_result["stats"]["total_matches"] == 0:
            warnings.append("No matches were found in the selected column.")

        return Response(
            {
                "file_id": file_id,
                "processed_file_id": processed_file_id,
                "target_column": target_column,
                "regex": validated_regex.pattern,
                "flags": flags,
                "replacement": replacement,
                "columns": list(replacement_result["processed_dataframe"].columns),
                "row_count": int(len(replacement_result["processed_dataframe"])),
                "preview_limit": replacement_result["preview_limit"],
                "processed_preview": processed_preview,
                "stats": replacement_result["stats"],
                "warnings": warnings,
            }
        )

    @staticmethod
    def _serializer_error_response(serializer):
        field_error_codes = {
            "file_id": "FILE_NOT_FOUND",
            "target_column": "COLUMN_NOT_FOUND",
            "regex": "EMPTY_REGEX",
            "flags": "REGEX_FLAGS_INVALID",
            "replacement": "MISSING_REPLACEMENT",
        }
        field_error_messages = {
            "file_id": "The uploaded file could not be found. Please upload the file again.",
            "target_column": "Choose a column before applying a replacement.",
            "regex": "Enter or generate a regex before applying a replacement.",
            "flags": "Regex flags must be provided as a list of strings.",
            "replacement": "Include a replacement value. Use an empty string to remove matches.",
        }

        for field_name in ("file_id", "target_column", "regex", "flags", "replacement"):
            field_errors = serializer.errors.get(field_name)
            if not field_errors:
                continue

            first_error = field_errors[0]
            code = str(getattr(first_error, "code", field_error_codes[field_name]))
            message = str(first_error) or field_error_messages[field_name]

            if code in {"required", "blank", "null", "invalid"}:
                code = field_error_codes[field_name]
                message = field_error_messages[field_name]

            return error_response(code=code, message=message)

        return error_response(
            code="INTERNAL_ERROR",
            message="The regex replacement request could not be validated.",
        )
