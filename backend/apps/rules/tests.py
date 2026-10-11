from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import close_old_connections
from django.test import TransactionTestCase
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, OperationalError, transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import PhoneRuleVersion, RuleExecution, RuleGroup
from . import services


class PhoneRuleTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.temp.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.client = APIClient()
        self.raw = b'id,phone,note\n1,0412 345 678,"a, b"\n2,invalid,keep\n3,,empty\n'
        self.file_id = self.upload(self.raw)
        self.rule = self.post(
            "/api/rules/", {"name": "AU phones", "target_column": "phone"}
        ).json()
        self.version_id = self.rule["version_id"]
        self.url = f"/api/rules/{self.version_id}/"

    def post(self, url, data):
        return self.client.post(url, data, format="json")

    def upload(self, raw):
        response = self.client.post(
            "/api/files/upload/",
            {"file": SimpleUploadedFile("synthetic.csv", raw)},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["file_id"]

    def preview(self, file_id=None, url=None):
        return self.post(
            (url or self.url) + "preview/", {"file_id": file_id or self.file_id}
        )

    def execute(self, token=None, url=None):
        if token is None:
            token = self.preview().json()["confirmation_token"]
        return self.post((url or self.url) + "execute/", {"confirmation_token": token})

    def new_version(self, **parameters):
        return self.post(
            self.url + "versions/",
            {"name": "Next", "target_column": "phone", **parameters},
        )

    def input_path(self):
        return Path(self.temp.name) / "uploads" / f"{self.file_id}.csv"

    def test_save_defaults_and_list_only_parameter_metadata(self):
        self.assertEqual(self.rule["version"], 1)
        self.assertEqual(self.rule["default_region"], "AU")
        self.assertEqual(self.rule["target_format"], "E164")
        self.assertTrue(self.rule["preserve_invalid"])
        self.assertEqual(self.client.get("/api/rules/").json()["rules"], [self.rule])
        response = self.post(
            "/api/rules/",
            {
                "name": "Allowed metadata",
                "target_column": "phone",
                "sample": "private value",
                "explanation": "private explanation",
                "prompt": "private prompt",
            },
        )
        stored = PhoneRuleVersion.objects.get(pk=response.json()["version_id"])
        self.assertNotIn("private", str(stored.__dict__))

    def test_versions_increment_from_old_version_and_old_is_immutable(self):
        for number in [2, 3]:
            response = self.new_version(target_format="NATIONAL")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["version"], number)
            self.assertEqual(response.json()["rule_id"], self.rule["rule_id"])
        original = PhoneRuleVersion.objects.get(pk=self.version_id)
        self.assertEqual(original.target_format, "E164")
        with self.assertRaises(ValueError):
            original.save()
        self.assertEqual(
            self.client.patch(self.url + "versions/", {}, format="json").status_code,
            405,
        )
        self.assertEqual(self.client.delete(self.url + "versions/").status_code, 405)

    def test_database_rejects_duplicate_group_version(self):
        original = PhoneRuleVersion.objects.get(pk=self.version_id)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PhoneRuleVersion.objects.create(
                group=original.group, version=1, name="Duplicate", target_column="phone"
            )

    def test_failed_allocation_rolls_back_counter(self):
        original = PhoneRuleVersion.objects.get(pk=self.version_id)
        with patch(
            "apps.rules.services.PhoneRuleVersion.objects.create",
            side_effect=IntegrityError,
        ):
            response = self.new_version()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(RuleGroup.objects.get(pk=original.group_id).next_version, 2)
        self.assertEqual(self.new_version().json()["version"], 2)

    def test_database_busy_returns_controlled_conflict(self):
        with patch(
            "apps.rules.views.services.save_version",
            side_effect=OperationalError("secret detail"),
        ):
            response = self.new_version()
        self.assertEqual(response.status_code, 409)
        self.assertNotIn("secret detail", response.content.decode())

    def test_parameter_validation(self):
        for update in [
            {"name": ""},
            {"target_column": ""},
            {"default_region": "XX"},
            {"target_format": "RAW"},
            {"preserve_invalid": "garbage"},
            {"target_column": ["phone", "id"]},
        ]:
            with self.subTest(update=update):
                response = self.post(
                    "/api/rules/", {"name": "v1", "target_column": "phone", **update}
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json())
        self.assertEqual(PhoneRuleVersion.objects.count(), 1)

    def test_missing_rule_and_malformed_requests(self):
        self.assertEqual(self.preview(url=f"/api/rules/{uuid4()}/").status_code, 404)
        self.assertEqual(self.preview(file_id="../../outside").status_code, 400)
        self.assertEqual(
            self.client.get("/api/rule-executions/?rule_id=not-uuid").status_code, 400
        )

    def test_missing_target_column(self):
        response = self.preview(self.upload(b"id,other\n1,hello\n"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "COLUMN_NOT_FOUND")
        self.assertEqual(RuleExecution.objects.count(), 0)

    def test_preview_no_persistence_50_row_cap_and_full_statistics(self):
        file_id = self.upload(b"id,phone\n" + b"1,0412 345 678\n" * 63)
        result = self.preview(file_id).json()
        self.assertEqual(len(result["before_preview"]), 50)
        self.assertEqual(len(result["processed_preview"]), 50)
        self.assertEqual(result["changed_rows"], 63)
        self.assertEqual(result["stats"]["checked_cells"], 63)
        self.assertEqual(result["row_count"], 63)
        self.assertFalse((Path(self.temp.name) / "processed").exists())
        self.assertEqual(RuleExecution.objects.count(), 0)
        self.assertNotIn("processed_file_id", result)

    def test_reuse_no_model_and_different_other_columns(self):
        other = self.upload(
            b'phone,new_column\n0412 345 678,"new, text"\ninvalid,keep\n'
        )
        with patch(
            "apps.transformations.phone_rule_service.generate_phone_normalization_rule",
            side_effect=AssertionError("Model must not run"),
        ) as model:
            response = self.execute(self.preview(other).json()["confirmation_token"])
        model.assert_not_called()
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["execution"]["changed_rows"], 1)
        self.assertEqual(result["execution"]["status"], "succeeded")
        self.assertEqual(
            result["processed_preview"][0],
            {"phone": "+61412345678", "new_column": "new, text"},
        )
        output = (
            Path(self.temp.name) / "processed" / (result["processed_file_id"] + ".csv")
        )
        self.assertEqual(
            output.read_text(),
            'phone,new_column\n+61412345678,"new, text"\ninvalid,keep\n',
        )

    def test_clear_invalid_counts_actual_changed_rows(self):
        new = self.new_version(preserve_invalid=False).json()
        url = f"/api/rules/{new['version_id']}/"
        response = self.execute(
            self.preview(url=url).json()["confirmation_token"], url=url
        )
        self.assertEqual(response.json()["execution"]["changed_rows"], 2)
        self.assertEqual(response.json()["processed_preview"][1]["phone"], "")

    def test_original_bytes_unchanged_on_repeated_execution(self):
        token = self.preview().json()["confirmation_token"]
        first = self.execute(token).json()
        second = self.execute(token).json()
        self.assertEqual(first["processed_preview"], second["processed_preview"])
        self.assertNotEqual(first["processed_file_id"], second["processed_file_id"])
        self.assertEqual(self.input_path().read_bytes(), self.raw)

    def test_expired_credential_requires_preview(self):
        with patch("django.core.signing.time.time", return_value=1000):
            token = self.preview().json()["confirmation_token"]
        with patch("django.core.signing.time.time", return_value=1901):
            response = self.execute(token)
        self.assertEqual(response.json()["error"]["code"], "PREVIEW_REQUIRED")
        self.assertEqual(RuleExecution.objects.count(), 0)

    def test_credential_tamper_and_version_binding(self):
        token = self.preview().json()["confirmation_token"]
        self.assertEqual(
            self.execute(token + "tamper").json()["error"]["code"], "PREVIEW_REQUIRED"
        )
        new = self.new_version().json()
        response = self.execute(token, url=f"/api/rules/{new['version_id']}/")
        self.assertEqual(response.json()["error"]["code"], "PREVIEW_REQUIRED")

    def test_file_change_failed_record_no_output(self):
        token = self.preview().json()["confirmation_token"]
        self.input_path().write_bytes(b"phone\nchanged\n")
        response = self.execute(token)
        self.assertEqual(response.json()["error"]["code"], "FILE_CHANGED")
        self.assert_failed_record(response)

    def test_missing_file_failed_record(self):
        token = self.preview().json()["confirmation_token"]
        self.input_path().unlink()
        response = self.execute(token)
        self.assertEqual(response.json()["error"]["code"], "FILE_NOT_FOUND")
        self.assert_failed_record(response)

    def test_processing_failure_sanitized(self):
        token = self.preview().json()["confirmation_token"]
        with patch(
            "apps.rules.services.apply_phone_normalization",
            side_effect=RuntimeError("0412 345 678 private exception"),
        ):
            response = self.execute(token)
        self.assertEqual(response.json()["error"]["code"], "PROCESSING_FAILED")
        self.assert_failed_record(response)
        self.assertNotIn("private", response.content.decode())
        self.assertNotIn("0412", str(RuleExecution.objects.values().first()))

    def test_write_failure_never_succeeds(self):
        token = self.preview().json()["confirmation_token"]
        with patch(
            "apps.rules.services.save_processed_dataframe",
            side_effect=OSError("secret filesystem detail"),
        ):
            response = self.execute(token)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "OUTPUT_SAVE_FAILED")
        self.assert_failed_record(response)
        self.assertNotIn("secret filesystem", response.content.decode())

    def test_running_before_output_and_interrupt_not_completed(self):
        token = self.preview().json()["confirmation_token"]

        def interrupt(_dataframe):
            entry = RuleExecution.objects.get()
            self.assertEqual(entry.status, "running")
            self.assertIsNone(entry.output_file_id)
            raise KeyboardInterrupt()

        with patch(
            "apps.rules.services.save_processed_dataframe", side_effect=interrupt
        ), self.assertRaises(KeyboardInterrupt):
            services.execute(PhoneRuleVersion.objects.get(pk=self.version_id), token)
        entry = RuleExecution.objects.get()
        self.assertEqual(entry.status, "running")
        self.assertIsNone(entry.finished_at)

    def test_history_latest_20_scoped_and_no_raw_data(self):
        self.execute()
        version = PhoneRuleVersion.objects.get(pk=self.version_id)
        for _ in range(21):
            RuleExecution.objects.create(
                rule_version=version, input_file_id=self.file_id
            )
        response = self.client.get(
            "/api/rule-executions/", {"rule_id": self.rule["rule_id"]}
        ).json()
        entries = response["executions"]
        self.assertEqual(len(entries), 20)
        self.assertEqual(entries[0]["id"], str(RuleExecution.objects.first().pk))
        self.assertEqual(
            set(entries[0]),
            {
                "id",
                "rule_version_id",
                "input_file_id",
                "output_file_id",
                "status",
                "changed_rows",
                "started_at",
                "finished_at",
                "error_code",
            },
        )
        self.assertNotIn("0412", json.dumps(response))
        self.assertNotIn("note", json.dumps(response))
        self.assertEqual(
            self.client.get("/api/rule-executions/", {"rule_id": str(uuid4())}).json()[
                "executions"
            ],
            [],
        )

    def assert_failed_record(self, response):
        data = response.json()
        self.assertNotIn("processed_file_id", data)
        self.assertEqual(data["execution"]["status"], "failed")
        self.assertIsNone(data["execution"]["output_file_id"])
        self.assertIsNone(data["execution"]["changed_rows"])
        self.assertIsNotNone(data["execution"]["finished_at"])




class ConcurrentVersionTests(TransactionTestCase):
    def test_concurrent_allocation_never_duplicates_and_conflicts_can_retry(self):
        source = services.save_version({"name": "Concurrent", "target_column": "phone"})
        url = f"/api/rules/{source.pk}/versions/"
        barrier = Barrier(2)

        def save():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return (
                    APIClient()
                    .post(
                        url, {"name": "Next", "target_column": "phone"}, format="json"
                    )
                    .status_code
                )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: save(), range(2)))
        for result in results:
            self.assertIn(result, [201, 409])
            if result == 409:
                self.assertEqual(
                    APIClient()
                    .post(
                        url, {"name": "Retry", "target_column": "phone"}, format="json"
                    )
                    .status_code,
                    201,
                )
        self.assertEqual(
            list(
                PhoneRuleVersion.objects.filter(group=source.group)
                .order_by("version")
                .values_list("version", flat=True)
            ),
            [1, 2, 3],
        )
