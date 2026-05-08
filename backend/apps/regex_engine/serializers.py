from uuid import UUID

from rest_framework import serializers


class RegexGenerateSerializer(serializers.Serializer):
    file_id = serializers.CharField(required=True, allow_blank=False)
    target_column = serializers.CharField(required=True, allow_blank=True, max_length=255)
    natural_language = serializers.CharField(required=True, allow_blank=True)

    def validate_file_id(self, value):
        try:
            UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError(
                "The uploaded file could not be found. Please upload the file again.",
                code="FILE_NOT_FOUND",
            ) from exc

        return str(value)

    def validate_target_column(self, value):
        normalized_value = value.strip()
        if not normalized_value:
            raise serializers.ValidationError(
                "Choose a column before generating a regex.",
                code="COLUMN_NOT_FOUND",
            )

        return normalized_value

    def validate_natural_language(self, value):
        normalized_value = value.strip()
        if not normalized_value:
            raise serializers.ValidationError(
                "Describe the pattern you want to find.",
                code="EMPTY_NATURAL_LANGUAGE",
            )

        if len(normalized_value) > 500:
            raise serializers.ValidationError(
                "Pattern descriptions must be 500 characters or fewer.",
                code="NATURAL_LANGUAGE_TOO_LONG",
            )

        return normalized_value


class RegexReplaceSerializer(serializers.Serializer):
    file_id = serializers.CharField(required=True, allow_blank=False)
    target_column = serializers.CharField(required=True, allow_blank=True, max_length=255)
    regex = serializers.CharField(required=True, allow_blank=True)
    flags = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        required=False,
        default=list,
    )
    replacement = serializers.CharField(
        required=True,
        allow_blank=True,
        trim_whitespace=False,
    )

    def validate_file_id(self, value):
        try:
            UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError(
                "The uploaded file could not be found. Please upload the file again.",
                code="FILE_NOT_FOUND",
            ) from exc

        return str(value)

    def validate_target_column(self, value):
        normalized_value = value.strip()
        if not normalized_value:
            raise serializers.ValidationError(
                "Choose a column before applying a replacement.",
                code="COLUMN_NOT_FOUND",
            )

        return normalized_value

    def validate_regex(self, value):
        normalized_value = value.strip()
        if not normalized_value:
            raise serializers.ValidationError(
                "Enter or generate a regex before applying a replacement.",
                code="EMPTY_REGEX",
            )

        return normalized_value
