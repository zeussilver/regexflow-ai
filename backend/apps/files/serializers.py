from pathlib import Path

from rest_framework import serializers


MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    def validate_file(self, uploaded_file):
        filename = uploaded_file.name or ""
        extension = Path(filename).suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            raise serializers.ValidationError(
                "Only CSV and XLSX files are supported.",
                code="UNSUPPORTED_FILE_TYPE",
            )

        if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
            raise serializers.ValidationError(
                "File size must be 5 MB or less.",
                code="FILE_TOO_LARGE",
            )

        if uploaded_file.size == 0:
            raise serializers.ValidationError(
                "The uploaded file is empty.",
                code="EMPTY_FILE",
            )

        return uploaded_file
