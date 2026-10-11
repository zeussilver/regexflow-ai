from dataclasses import asdict

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.common.responses import error_response
from . import rules, services, sources
from .models import ProductCheckRun
from .serializers import LiveCheckSerializer, UploadCheckSerializer


class ProductChecksView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    throttle_scope = "product_checks_live"

    def get_throttles(self):
        # Live checks fan out to a bank's public API; uploads and reads do not.
        if self.request.method == "POST" and "file" not in self.request.FILES:
            return [ScopedRateThrottle()]
        return []

    def get(self, request):
        return Response({"runs": services.recent_runs()})

    def post(self, request):
        try:
            if "file" in request.FILES:
                serializer = UploadCheckSerializer(data=request.data)
                if not serializer.is_valid():
                    return _upload_error_response(serializer)
                result = services.check_upload(serializer.validated_data["file"])
            else:
                serializer = LiveCheckSerializer(data=request.data)
                if not serializer.is_valid():
                    return error_response(
                        "INVALID_CHECK_REQUEST",
                        "Choose a data holder or upload a CDR products JSON file.",
                    )
                result = services.check_live(
                    serializer.validated_data["holder"],
                    include_details=serializer.validated_data["include_details"],
                )
        except sources.ProductSourceError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except Exception:
            return error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred while checking product data.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=status.HTTP_201_CREATED)


class ProductCheckDetailView(APIView):
    def get(self, request, run_id):
        try:
            run = ProductCheckRun.objects.get(pk=run_id)
        except ProductCheckRun.DoesNotExist:
            return error_response(
                "CHECK_NOT_FOUND",
                "The product check was not found.",
                status.HTTP_404_NOT_FOUND,
            )
        return Response(services.run_payload(run))


class DataHoldersView(APIView):
    def get(self, request):
        holders = [asdict(holder) for holder in sources.configured_holders()]
        return Response({"holders": holders})


class CheckRulesView(APIView):
    def get(self, request):
        return Response(
            {
                "ruleset_version": rules.RULESET_VERSION,
                "rules": [asdict(rule) for rule in rules.RULES.values()],
            }
        )


def _upload_error_response(serializer):
    first_error = serializer.errors.get("file", [None])[0]
    code = str(getattr(first_error, "code", ""))
    if code in {"UNSUPPORTED_FILE_TYPE", "FILE_TOO_LARGE"}:
        return error_response(code, str(first_error))
    if code == "empty":
        return error_response("EMPTY_FILE", "The uploaded file is empty.")
    return error_response("INVALID_CHECK_REQUEST", "Upload a CDR products JSON file.")
