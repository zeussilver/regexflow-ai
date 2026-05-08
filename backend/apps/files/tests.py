from io import BytesIO

import pandas as pd
from django.test import override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase


@override_settings(MEDIA_ROOT="/tmp/regexflow-ai-test-media")
class FileUploadApiTests(APITestCase):
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
