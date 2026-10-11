from pathlib import Path

from rest_framework import serializers

from .models import ProductCheckRun, ProductIssue


MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024


class LiveCheckSerializer(serializers.Serializer):
    holder = serializers.CharField(max_length=40)
    include_details = serializers.BooleanField(default=True)


class UploadCheckSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, uploaded_file):
        if Path(uploaded_file.name or "").suffix.lower() != ".json":
            raise serializers.ValidationError(
                "Only JSON files are supported.", code="UNSUPPORTED_FILE_TYPE"
            )
        if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
            raise serializers.ValidationError(
                "File size must be 5 MB or less.", code="FILE_TOO_LARGE"
            )
        return uploaded_file


class ProductCheckRunSerializer(serializers.ModelSerializer):
    compared_with_time = serializers.DateTimeField(
        source="compared_with.created_at", allow_null=True, read_only=True
    )

    class Meta:
        model = ProductCheckRun
        fields = (
            "id",
            "source_type",
            "source_label",
            "holder_key",
            "list_version",
            "detail_version",
            "ruleset_version",
            "reference_time",
            "product_count",
            "detail_count",
            "products_with_errors",
            "error_count",
            "warning_count",
            "report_file_id",
            "compared_with",
            "compared_with_time",
            "created_at",
        )


class ProductIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductIssue
        fields = (
            "rule_id",
            "severity",
            "product_index",
            "product_id",
            "product_name",
            "field",
            "message",
            "value",
        )
