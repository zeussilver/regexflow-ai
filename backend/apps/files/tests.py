from io import BytesIO
from pathlib import Path
import shutil

import pandas as pd
from django.test import override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from .services import save_processed_dataframe


TEST_MEDIA_ROOT = "/tmp/regexflow-ai-test-media"
FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "generated"
GENERATED_FIXTURE_ROW_COUNTS = {
    "mixed_pii_dataset": 8,
    "email_cases": 10,
    "phone_cases": 9,
    "card_cases": 8,
    "address_cases": 8,
    "edge_cases": 11,
    "medium_mixed_dataset": 600,
}


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class FileUploadApiTests(APITestCase):
    def setUp(self):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def test_valid_csv_upload_returns_preview(self):
        uploaded_file = SimpleUploadedFile(
            "contacts.csv",
            b"name,email\nAda,ada@example.com\nGrace,grace@example.com\n",
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("file-upload"),
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.json()
        self.assertEqual(payload["filename"], "contacts.csv")
        self.assertEqual(payload["columns"], ["name", "email"])
        self.assertEqual(payload["row_count"], 2)
        self.assertEqual(payload["preview_rows"][0]["name"], "Ada")

    def test_valid_xlsx_upload_returns_preview(self):
        buffer = BytesIO()
        dataframe = pd.DataFrame(
            [
                {"name": "Ada", "email": "ada@example.com"},
                {"name": "Grace", "email": "grace@example.com"},
            ]
        )
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            dataframe.to_excel(writer, index=False)
        buffer.seek(0)
        uploaded_file = SimpleUploadedFile(
            "contacts.xlsx",
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = self.client.post(
            reverse("file-upload"),
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.json()
        self.assertEqual(payload["filename"], "contacts.xlsx")
        self.assertEqual(payload["columns"], ["name", "email"])
        self.assertEqual(payload["row_count"], 2)
        self.assertEqual(payload["preview_rows"][1]["name"], "Grace")

    def test_generated_fixture_upload_matrix_csv_and_xlsx(self):
        for fixture_name, expected_row_count in GENERATED_FIXTURE_ROW_COUNTS.items():
            for extension in ("csv", "xlsx"):
                with self.subTest(fixture=fixture_name, extension=extension):
                    response = self._upload_generated_fixture(
                        f"{fixture_name}.{extension}"
                    )

                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    payload = response.json()
                    self.assertEqual(payload["filename"], f"{fixture_name}.{extension}")
                    self.assertEqual(payload["row_count"], expected_row_count)
                    self.assertGreater(len(payload["columns"]), 0)
                    self.assertEqual(
                        len(payload["preview_rows"]),
                        min(expected_row_count, 50),
                    )

    def test_generated_edge_fixture_null_values_are_json_safe(self):
        for extension in ("csv", "xlsx"):
            with self.subTest(extension=extension):
                response = self._upload_generated_fixture(f"edge_cases.{extension}")

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                payload = response.json()
                null_row = next(
                    row for row in payload["preview_rows"] if row["ID"] == "EDGE-011"
                )
                self.assertIsNone(null_row["Email"])
                self.assertIsNone(null_row["Phone"])
                self.assertIsNone(null_row["Notes"])

    def test_missing_file_returns_structured_error(self):
        response = self.client.post(reverse("file-upload"), {}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "NO_FILE_UPLOADED")

    def test_unsupported_file_type_returns_structured_error(self):
        uploaded_file = SimpleUploadedFile(
            "notes.txt",
            b"hello",
            content_type="text/plain",
        )

        response = self.client.post(
            reverse("file-upload"),
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "UNSUPPORTED_FILE_TYPE")

    def test_empty_file_returns_structured_error(self):
        uploaded_file = SimpleUploadedFile(
            "empty.csv",
            b"",
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("file-upload"),
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "EMPTY_FILE")

    def test_processed_file_download_returns_saved_csv(self):
        processed_file_id = save_processed_dataframe(
            pd.DataFrame(
                [
                    {"Name": "Ada", "Email": "REDACTED"},
                    {"Name": "Grace", "Email": "REDACTED"},
                ]
            )
        )

        response = self.client.get(
            reverse(
                "processed-file-download",
                kwargs={"processed_file_id": processed_file_id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("Ada,REDACTED", content)
        self.assertIn("Grace,REDACTED", content)

    def test_missing_processed_file_download_returns_file_not_found(self):
        response = self.client.get(
            reverse(
                "processed-file-download",
                kwargs={"processed_file_id": "00000000-0000-0000-0000-000000000000"},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "FILE_NOT_FOUND")

    def _upload_generated_fixture(self, filename):
        path = FIXTURE_DIR / filename
        self.assertTrue(path.exists(), f"Generated fixture is missing: {path}")
        content_type = (
            "text/csv"
            if path.suffix == ".csv"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        uploaded_file = SimpleUploadedFile(
            path.name,
            path.read_bytes(),
            content_type=content_type,
        )
        return self.client.post(
            reverse("file-upload"),
            {"file": uploaded_file},
            format="multipart",
        )
