from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import FileResponse

from apps.common.responses import error_response

from .serializers import FileUploadSerializer
from .services import UploadServiceError, resolve_processed_file, save_and_parse_upload


class FileUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if "file" not in request.FILES:
            return error_response(
                code="NO_FILE_UPLOADED",
                message="Please choose a CSV or XLSX file to upload.",
            )

        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return self._serializer_error_response(serializer)

        try:
            payload = save_and_parse_upload(serializer.validated_data["file"])
        except UploadServiceError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except Exception:
            return error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred while processing the file.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(payload, status=status.HTTP_201_CREATED)

    @staticmethod
    def _serializer_error_response(serializer):
        file_errors = serializer.errors.get("file", [])
        first_error = file_errors[0] if file_errors else None
        code = getattr(first_error, "code", "INTERNAL_ERROR")
        message = str(first_error) if first_error else "The upload could not be validated."

        if code == "required":
            code = "NO_FILE_UPLOADED"
            message = "Please choose a CSV or XLSX file to upload."
        elif code == "empty":
            code = "EMPTY_FILE"
            message = "The uploaded file is empty."

        return error_response(code=str(code), message=message)


class ProcessedFileDownloadView(APIView):
    def get(self, request, processed_file_id):
        try:
            processed_path = resolve_processed_file(processed_file_id)
        except UploadServiceError as exc:
            return error_response(exc.code, exc.message, exc.status_code)

        return FileResponse(
            processed_path.open("rb"),
            as_attachment=True,
            filename=f"{processed_file_id}.csv",
            content_type="text/csv",
        )
