from uuid import UUID

from rest_framework import serializers

from .phone_normalizer import ALLOWED_PHONE_FORMATS
from .pii_policy_service import DEFAULT_PII_NATURAL_LANGUAGE
from .pii_patterns import (
    DEFAULT_REDACTION_STRATEGY,
    SUPPORTED_PII_TYPES,
    SUPPORTED_REDACTION_STRATEGIES,
)


class TargetColumnsMixin:
    def to_internal_value(self, data):
        data = data.copy()

        if "target_columns" not in data and "target_column" in data:
            data["target_columns"] = [data["target_column"]]

        if "natural_language" not in data:
            for alias in ("prompt", "instruction", "instructions", "user_prompt"):
                if alias in data:
                    data["natural_language"] = data[alias]
                    break

        return super().to_internal_value(data)

    def validate_file_id(self, value):
        try:
            UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError(
                "The uploaded file could not be found. Please upload the file again.",
                code="FILE_NOT_FOUND",
            ) from exc

        return str(value)

    def validate_target_columns(self, value):
        normalized_columns = []
        for column in value:
            normalized_column = str(column).strip()
            if not normalized_column:
                raise serializers.ValidationError(
                    "Choose at least one column before applying a transformation.",
                    code="COLUMN_NOT_FOUND",
                )
            if normalized_column not in normalized_columns:
                normalized_columns.append(normalized_column)

        if not normalized_columns:
            raise serializers.ValidationError(
                "Choose at least one column before applying a transformation.",
                code="COLUMN_NOT_FOUND",
            )

        return normalized_columns


class PiiRedactSerializer(TargetColumnsMixin, serializers.Serializer):
    file_id = serializers.CharField(required=True, allow_blank=False)
    target_columns = serializers.ListField(
        child=serializers.CharField(allow_blank=False, max_length=255),
        required=False,
        allow_empty=True,
    )
    natural_language = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        default=DEFAULT_PII_NATURAL_LANGUAGE,
    )
    pii_types = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        required=False,
        allow_empty=False,
    )
    replacement_strategy = serializers.CharField(
        required=False,
        default=DEFAULT_REDACTION_STRATEGY,
    )

    def validate_target_columns(self, value):
        normalized_columns = []
        for column in value:
            normalized_column = str(column).strip()
            if not normalized_column:
                raise serializers.ValidationError(
                    "Column names must not be blank.",
                    code="COLUMN_NOT_FOUND",
                )
            if normalized_column not in normalized_columns:
                normalized_columns.append(normalized_column)

        return normalized_columns

    def validate_natural_language(self, value):
        normalized_value = value.strip()
        if not normalized_value:
            raise serializers.ValidationError(
                "Describe the PII redaction policy to generate.",
                code="EMPTY_NATURAL_LANGUAGE",
            )

        return normalized_value

    def validate_pii_types(self, value):
        normalized_types = [str(pii_type).strip().lower() for pii_type in value]
        for pii_type in normalized_types:
            if pii_type not in SUPPORTED_PII_TYPES:
                raise serializers.ValidationError(
                    f"PII type '{pii_type}' is not supported.",
                    code="UNSUPPORTED_PII_TYPE",
                )

        return normalized_types

    def validate_replacement_strategy(self, value):
        normalized_strategy = value.strip().lower()
        if normalized_strategy not in SUPPORTED_REDACTION_STRATEGIES:
            raise serializers.ValidationError(
                f"Replacement strategy '{value}' is not supported.",
                code="UNSUPPORTED_REPLACEMENT_STRATEGY",
            )

        return normalized_strategy


class PhoneNormalizeSerializer(TargetColumnsMixin, serializers.Serializer):
    file_id = serializers.CharField(required=True, allow_blank=False)
    target_columns = serializers.ListField(
        child=serializers.CharField(allow_blank=False, max_length=255),
        required=True,
        allow_empty=False,
    )
    natural_language = serializers.CharField(
        required=True,
        allow_blank=True,
        max_length=500,
    )
    rule = serializers.DictField(required=False)
    target_format = serializers.CharField(
        required=False,
    )
    default_region = serializers.CharField(
        required=False,
        allow_blank=False,
        min_length=2,
        max_length=2,
    )
    preserve_invalid = serializers.BooleanField(required=False)

    def validate_natural_language(self, value):
        normalized_value = value.strip()
        if not normalized_value:
            raise serializers.ValidationError(
                "Describe how phone numbers should be normalized.",
                code="EMPTY_NATURAL_LANGUAGE",
            )

        return normalized_value

    def validate_default_region(self, value):
        return value.strip().upper()

    def validate_target_format(self, value):
        normalized_format = value.strip().upper()
        if normalized_format not in ALLOWED_PHONE_FORMATS:
            raise serializers.ValidationError(
                f"Phone format '{value}' is not supported.",
                code="UNSUPPORTED_TARGET_FORMAT",
            )

        return normalized_format
