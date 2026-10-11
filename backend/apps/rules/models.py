import uuid

from django.db import models
from django.utils import timezone


class RuleGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    next_version = models.PositiveIntegerField(default=1)


class PhoneRuleVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(RuleGroup, on_delete=models.PROTECT)
    name = models.CharField(max_length=160)
    version = models.PositiveIntegerField()
    target_column = models.CharField(max_length=255)
    default_region = models.CharField(max_length=2, default="AU")
    target_format = models.CharField(max_length=16, default="E164")
    preserve_invalid = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "version"], name="unique_phone_rule_version"
            )
        ]
        ordering = ["-created_at", "-version"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Saved rule versions are immutable; create a new version.")
        return super().save(*args, **kwargs)

    def parameters(self):
        return {
            "transformation_type": "phone_normalization",
            "default_region": self.default_region,
            "target_format": self.target_format,
            "preserve_invalid": self.preserve_invalid,
        }


class RuleExecution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule_version = models.ForeignKey(PhoneRuleVersion, on_delete=models.PROTECT)
    input_file_id = models.UUIDField()
    output_file_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[(s, s) for s in ("running", "succeeded", "failed")],
        default="running",
    )
    changed_rows = models.PositiveIntegerField(null=True)
    started_at = models.DateTimeField(default=timezone.now, editable=False)
    finished_at = models.DateTimeField(null=True)
    error_code = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]
