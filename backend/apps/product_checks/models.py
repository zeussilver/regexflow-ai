import uuid

from django.db import models
from django.utils import timezone


class ProductCheckRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_type = models.CharField(
        max_length=6, choices=[(s, s) for s in ("upload", "live")]
    )
    source_label = models.CharField(max_length=160)
    holder_key = models.CharField(max_length=40, blank=True)
    list_version = models.CharField(max_length=8, blank=True)
    detail_version = models.CharField(max_length=8, blank=True)
    ruleset_version = models.CharField(max_length=16)
    reference_time = models.DateTimeField()
    product_count = models.PositiveIntegerField()
    detail_count = models.PositiveIntegerField(default=0)
    products_with_errors = models.PositiveIntegerField()
    error_count = models.PositiveIntegerField()
    warning_count = models.PositiveIntegerField()
    report_file_id = models.UUIDField(null=True, blank=True)
    # The previous live run for the same holder, used to spot silent changes.
    compared_with = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]


class ProductIssue(models.Model):
    run = models.ForeignKey(
        ProductCheckRun, on_delete=models.CASCADE, related_name="issues"
    )
    rule_id = models.CharField(max_length=8)
    severity = models.CharField(max_length=8)
    product_index = models.PositiveIntegerField()
    product_id = models.CharField(max_length=255, blank=True)
    product_name = models.CharField(max_length=255, blank=True)
    field = models.CharField(max_length=255)
    message = models.CharField(max_length=500)
    value = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["id"]


class ProductSnapshot(models.Model):
    """Fingerprint of one product as published in a live run."""

    run = models.ForeignKey(
        ProductCheckRun, on_delete=models.CASCADE, related_name="snapshots"
    )
    product_id = models.CharField(max_length=255)
    representation = models.CharField(max_length=16)
    last_updated = models.CharField(max_length=64)
    fingerprint = models.CharField(max_length=64)
