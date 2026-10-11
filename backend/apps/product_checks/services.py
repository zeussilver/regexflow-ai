"""Run CDR product data checks and keep an auditable record of every run."""

from dataclasses import asdict
from pathlib import Path

import pandas as pd
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.files.services import save_processed_dataframe
from . import rules, sources
from .models import ProductCheckRun, ProductIssue, ProductSnapshot
from .serializers import ProductCheckRunSerializer, ProductIssueSerializer


ISSUE_RESPONSE_LIMIT = 200
RECENT_RUN_LIMIT = 20
REPORT_COLUMNS = [
    "product_index",
    "product_id",
    "product_name",
    "rule_id",
    "severity",
    "field",
    "message",
    "value",
]


def check_upload(uploaded_file) -> dict:
    loaded = sources.LoadedProducts(
        products=sources.products_from_upload(uploaded_file),
        reference_time=timezone.now(),
    )
    return _record_run(
        loaded, source_type="upload", source_label=Path(uploaded_file.name).name
    )


def check_live(holder_key: str, *, include_details: bool) -> dict:
    holder = sources.get_holder(holder_key)
    loaded = sources.load_live_products(holder, include_details=include_details)
    return _record_run(
        loaded, source_type="live", source_label=holder.name, holder_key=holder.key
    )


def recent_runs() -> list:
    runs = ProductCheckRun.objects.all()[:RECENT_RUN_LIMIT]
    return ProductCheckRunSerializer(runs, many=True).data


def run_payload(run: ProductCheckRun) -> dict:
    counts = dict(
        run.issues.order_by().values_list("rule_id").annotate(count=Count("id"))
    )
    return {
        "run": ProductCheckRunSerializer(run).data,
        "by_rule": [
            {
                "rule_id": rule.rule_id,
                "severity": rule.severity,
                "title": rule.title,
                "count": counts[rule.rule_id],
            }
            for rule in rules.RULES.values()
            if rule.rule_id in counts
        ],
        "issues": ProductIssueSerializer(
            run.issues.all()[:ISSUE_RESPONSE_LIMIT], many=True
        ).data,
        "issues_truncated": run.error_count + run.warning_count > ISSUE_RESPONSE_LIMIT,
    }


def _record_run(loaded, *, source_type, source_label, holder_key="") -> dict:
    issues = rules.check_products(
        loaded.products,
        reference_time=loaded.reference_time,
        summaries=loaded.summaries,
    )
    issues += [
        rules.detail_unavailable(loaded.products[index], index, reason)
        for index, reason in loaded.detail_failures
    ]
    snapshots = _snapshots(loaded) if source_type == "live" else []
    # Compare with the latest live run of this holder that read the same versions.
    previous = (
        ProductCheckRun.objects.filter(
            source_type="live",
            holder_key=holder_key,
            list_version=loaded.list_version,
            detail_version=loaded.detail_version,
        ).first()
        if snapshots
        else None
    )
    if previous:
        issues += _changed_without_update(previous, snapshots, loaded.products)
    # Errors first, then rule and product order, so the first page shows what matters.
    issues.sort(
        key=lambda issue: (
            issue.severity != rules.ERROR,
            issue.rule_id,
            issue.product_index,
            issue.field,
        )
    )
    report = pd.DataFrame([asdict(issue) for issue in issues], columns=REPORT_COLUMNS)
    report_file_id = save_processed_dataframe(report)

    with transaction.atomic():
        run = ProductCheckRun.objects.create(
            source_type=source_type,
            source_label=source_label[:160],
            holder_key=holder_key,
            list_version=loaded.list_version[:8],
            detail_version=loaded.detail_version[:8],
            ruleset_version=rules.RULESET_VERSION,
            reference_time=loaded.reference_time,
            product_count=len(loaded.products),
            detail_count=sum(rules.has_detail(product) for product in loaded.products),
            products_with_errors=len(
                {issue.product_index for issue in issues if issue.severity == rules.ERROR}
            ),
            error_count=sum(issue.severity == rules.ERROR for issue in issues),
            warning_count=sum(issue.severity == rules.WARNING for issue in issues),
            report_file_id=report_file_id,
            compared_with=previous,
        )
        for _, snapshot in snapshots:
            snapshot.run = run
        ProductSnapshot.objects.bulk_create(
            [snapshot for _, snapshot in snapshots], batch_size=500
        )
        ProductIssue.objects.bulk_create(
            [
                ProductIssue(
                    run=run,
                    rule_id=issue.rule_id,
                    severity=issue.severity,
                    product_index=issue.product_index,
                    product_id=issue.product_id[:255],
                    product_name=issue.product_name[:255],
                    field=issue.field[:255],
                    message=issue.message[:500],
                    value=issue.value[:255],
                )
                for issue in issues
            ],
            batch_size=500,
        )

    return run_payload(run)


def _snapshots(loaded) -> list[tuple[int, ProductSnapshot]]:
    snapshots = []
    for index, product in enumerate(loaded.products):
        product_id, last_updated = product.get("productId"), product.get("lastUpdated")
        if not isinstance(product_id, str) or not isinstance(last_updated, str):
            continue
        # Only compare like with like: a summary never matches a detail.
        representation = (
            f"detail v{loaded.detail_version}"
            if rules.has_detail(product)
            else f"summary v{loaded.list_version}"
        )
        snapshots.append(
            (
                index,
                ProductSnapshot(
                    product_id=product_id[:255],
                    representation=representation[:16],
                    last_updated=last_updated[:64],
                    fingerprint=rules.fingerprint(product),
                ),
            )
        )
    return snapshots


def _changed_without_update(previous, snapshots, products) -> list:
    earlier = {
        (snapshot.product_id, snapshot.representation): snapshot
        for snapshot in previous.snapshots.all()
    }
    issues = []
    for index, snapshot in snapshots:
        before = earlier.get((snapshot.product_id, snapshot.representation))
        if (
            before
            and before.last_updated == snapshot.last_updated
            and before.fingerprint != snapshot.fingerprint
        ):
            issues.append(
                rules.changed_without_update(products[index], index, previous.created_at)
            )
    return issues
