from rest_framework import serializers

from apps.transformations.phone_normalizer import (
    normalize_rule,
    PhoneNormalizationError,
)
from .models import PhoneRuleVersion, RuleExecution


class RuleInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    target_column = serializers.CharField(max_length=255)
    default_region = serializers.CharField(default="AU", min_length=2, max_length=2)
    target_format = serializers.CharField(default="E164")
    preserve_invalid = serializers.BooleanField(default=True)

    def validate(self, data):
        try:
            rule = normalize_rule(
                {"transformation_type": "phone_normalization", **data}
            )
        except PhoneNormalizationError as exc:
            raise serializers.ValidationError(exc.message, code=exc.code) from exc
        for key in ("default_region", "target_format", "preserve_invalid"):
            data[key] = rule[key]
        return data


class RuleSerializer(serializers.ModelSerializer):
    rule_id = serializers.UUIDField(source="group_id")
    version_id = serializers.UUIDField(source="id")

    class Meta:
        model = PhoneRuleVersion
        fields = (
            "rule_id",
            "version_id",
            "name",
            "version",
            "target_column",
            "default_region",
            "target_format",
            "preserve_invalid",
            "created_at",
        )


class ExecutionSerializer(serializers.ModelSerializer):
    rule_version_id = serializers.UUIDField()

    class Meta:
        model = RuleExecution
        fields = (
            "id",
            "rule_version_id",
            "input_file_id",
            "output_file_id",
            "status",
            "changed_rows",
            "started_at",
            "finished_at",
            "error_code",
        )


class PreviewInputSerializer(serializers.Serializer):
    file_id = serializers.UUIDField()


class ExecuteInputSerializer(serializers.Serializer):
    confirmation_token = serializers.CharField(max_length=2048)
