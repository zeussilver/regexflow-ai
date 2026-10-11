from django.core.management.base import BaseCommand, CommandError

from apps.product_checks import services, sources


class Command(BaseCommand):
    help = "Check public CDR product reference data from configured data holders."

    def add_arguments(self, parser):
        parser.add_argument(
            "holders",
            nargs="*",
            help="Data holder keys from CDR_DATA_HOLDERS. Defaults to all of them.",
        )
        parser.add_argument(
            "--summary-only",
            action="store_true",
            help="Check Get Products summaries without product detail requests.",
        )

    def handle(self, *args, holders, summary_only, **options):
        keys = holders or [holder.key for holder in sources.configured_holders()]
        failed = []
        for key in keys:
            try:
                result = services.check_live(key, include_details=not summary_only)
            except sources.ProductSourceError as exc:
                failed.append(key)
                self.stderr.write(f"{key}: {exc.code} - {exc.message}")
                continue

            run = result["run"]
            self.stdout.write(
                f"{run['source_label']}: {run['product_count']} products "
                f"({run['detail_count']} with detail, list x-v {run['list_version']}, "
                f"detail x-v {run['detail_version'] or '-'}), "
                f"{run['error_count']} errors, {run['warning_count']} warnings"
            )
            for rule in result["by_rule"]:
                self.stdout.write(
                    f"  {rule['rule_id']}  {rule['severity']:<7} {rule['count']:>4}  "
                    f"{rule['title']}"
                )
            self.stdout.write(f"  report: {run['report_file_id']}.csv | run: {run['id']}")

        if failed:
            raise CommandError(f"Could not check: {', '.join(failed)}")
