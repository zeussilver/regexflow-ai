from uuid import UUID

from django.db import IntegrityError, OperationalError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.responses import error_response
from .models import PhoneRuleVersion, RuleExecution
from .serializers import (
    RuleInputSerializer,
    RuleSerializer,
    ExecutionSerializer,
    PreviewInputSerializer,
    ExecuteInputSerializer,
)
from . import services


def invalid(serializer):
    return error_response(
        "INVALID_RULE_REQUEST",
        "Check the required fields and supported phone parameters.",
    )


def version_or_error(version_id):
    try:
        return PhoneRuleVersion.objects.get(pk=version_id)
    except PhoneRuleVersion.DoesNotExist:
        raise services.RuleError(
            "RULE_NOT_FOUND", "The rule version was not found.", 404
        )


class RulesView(APIView):
    def get(self, request):
        return Response(
            {"rules": RuleSerializer(PhoneRuleVersion.objects.all(), many=True).data}
        )

    def post(self, request, version_id=None):
        serializer = RuleInputSerializer(data=request.data)
        if not serializer.is_valid():
            return invalid(serializer)
        try:
            source = version_or_error(version_id) if version_id else None
            saved = services.save_version(serializer.validated_data, source)
        except services.RuleError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        except (IntegrityError, OperationalError):
            return error_response(
                "VERSION_CONFLICT",
                "The version could not be allocated. Retry saving.",
                409,
            )
        return Response(RuleSerializer(saved).data, status=201)


class NewVersionView(RulesView):
    http_method_names = ["post", "options"]


class PreviewView(APIView):
    def post(self, request, version_id):
        serializer = PreviewInputSerializer(data=request.data)
        if not serializer.is_valid():
            return invalid(serializer)
        try:
            result = services.preview(
                version_or_error(version_id), serializer.validated_data["file_id"]
            )
        except Exception as exc:
            return error_response(*services.controlled_error(exc))
        return Response(result)


class ExecuteView(APIView):
    def post(self, request, version_id):
        serializer = ExecuteInputSerializer(data=request.data)
        if not serializer.is_valid():
            return invalid(serializer)
        try:
            result, http_status = services.execute(
                version_or_error(version_id),
                serializer.validated_data["confirmation_token"],
            )
        except services.RuleError as exc:
            return error_response(exc.code, exc.message, exc.status_code)
        return Response(result, status=http_status)


class ExecutionsView(APIView):
    def get(self, request):
        try:
            group_id = UUID(request.query_params.get("rule_id", ""))
        except (ValueError, TypeError, AttributeError):
            return error_response("INVALID_RULE_REQUEST", "Provide a rule group ID.")
        recent = RuleExecution.objects.filter(rule_version__group_id=group_id)[:20]
        return Response({"executions": ExecutionSerializer(recent, many=True).data})
