import os
import shutil
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from apps.common.exception_handlers import structured_exception_handler


TEST_MEDIA_ROOT = "/tmp/regexflow-ai-error-shape-test-media"


class HealthCheckTests(TestCase):
    def test_health_check_returns_ok(self):
        response = APIClient().get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class StructuredErrorShapeTests(APITestCase):
    def setUp(self):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def test_file_upload_error_shapes(self):
        cases = [
            (
                "NO_FILE_UPLOADED",
                self.client.post(reverse("file-upload"), {}, format="multipart"),
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "UNSUPPORTED_FILE_TYPE",
                self.client.post(
                    reverse("file-upload"),
                    {
                        "file": SimpleUploadedFile(
                            "notes.txt",
                            b"hello",
                            content_type="text/plain",
                        )
                    },
                    format="multipart",
                ),
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "EMPTY_FILE",
                self.client.post(
                    reverse("file-upload"),
                    {
                        "file": SimpleUploadedFile(
                            "empty.csv",
                            b"",
                            content_type="text/csv",
                        )
                    },
                    format="multipart",
                ),
                status.HTTP_400_BAD_REQUEST,
            ),
        ]

        for expected_code, response, expected_status in cases:
            with self.subTest(expected_code=expected_code):
                self.assert_error_shape(response, expected_status, expected_code)

    def test_regex_error_shapes(self):
        file_id = self._upload_csv(b"Name,Email\nAda,ada@example.com\n")

        self.assert_error_shape(
            self.client.post(
                reverse("regex-generate"),
                {
                    "file_id": "00000000-0000-0000-0000-000000000000",
                    "target_column": "Email",
                    "natural_language": "Find email addresses",
                },
                format="json",
            ),
            status.HTTP_404_NOT_FOUND,
            "FILE_NOT_FOUND",
        )
        self.assert_error_shape(
            self.client.post(
                reverse("regex-generate"),
                {
                    "file_id": file_id,
                    "target_column": "Email",
                    "natural_language": " ",
                },
                format="json",
            ),
            status.HTTP_400_BAD_REQUEST,
            "EMPTY_NATURAL_LANGUAGE",
        )

        with patch.dict(
            os.environ,
            {
                "LLM_API_KEY": "test-key",
                "LLM_BASE_URL": "https://llm.test/v1",
                "LLM_MODEL": "test-model",
            },
        ):
            with patch(
                "apps.regex_engine.llm_service._call_openai_compatible",
                return_value="not-json",
            ):
                self.assert_error_shape(
                    self.client.post(
                        reverse("regex-generate"),
                        {
                            "file_id": file_id,
                            "target_column": "Email",
                            "natural_language": "Find email addresses",
                        },
                        format="json",
                    ),
                    status.HTTP_502_BAD_GATEWAY,
                    "LLM_INVALID_JSON",
                )

        regex_replace_cases = [
            (
                "COLUMN_NOT_FOUND",
                {
                    "file_id": file_id,
                    "target_column": "Missing",
                    "regex": r"\d+",
                    "replacement": "REDACTED",
                },
            ),
            (
                "REGEX_COMPILE_ERROR",
                {
                    "file_id": file_id,
                    "target_column": "Email",
                    "regex": "[",
                    "replacement": "REDACTED",
                },
            ),
            (
                "REGEX_UNSAFE",
                {
                    "file_id": file_id,
                    "target_column": "Email",
                    "regex": "(.+)+",
                    "replacement": "REDACTED",
                },
            ),
            (
                "MISSING_REPLACEMENT",
                {
                    "file_id": file_id,
                    "target_column": "Email",
                    "regex": r"\w+",
                },
            ),
        ]
        for expected_code, request_payload in regex_replace_cases:
            with self.subTest(expected_code=expected_code):
                self.assert_error_shape(
                    self.client.post(
                        reverse("regex-replace"),
                        request_payload,
                        format="json",
                    ),
                    status.HTTP_400_BAD_REQUEST,
                    expected_code,
                )

    def test_transformation_error_shapes(self):
        file_id = self._upload_csv(b"Name,Email,Phone\nAda,ada@example.com,0412 345 678\n")

        self.assert_error_shape(
            self.client.post(
                reverse("transformation-pii-redact"),
                {
                    "file_id": file_id,
                    "target_columns": ["Email"],
                    "pii_types": ["address"],
                },
                format="json",
            ),
            status.HTTP_400_BAD_REQUEST,
            "UNSUPPORTED_PII_TYPE",
        )
        self.assert_error_shape(
            self.client.post(
                reverse("transformation-phone-normalize"),
                {
                    "file_id": file_id,
                    "target_columns": ["Phone"],
                    "natural_language": "Normalize phone numbers",
                    "target_format": "LOCAL",
                    "default_region": "AU",
                },
                format="json",
            ),
            status.HTTP_400_BAD_REQUEST,
            "UNSUPPORTED_TARGET_FORMAT",
        )

        with patch(
            "apps.transformations.phone_rule_service.generate_phone_normalization_rule",
            return_value={
                "transformation_type": "pii_redaction",
                "target_format": "E164",
                "default_region": "AU",
                "preserve_invalid": True,
            },
        ):
            self.assert_error_shape(
                self.client.post(
                    reverse("transformation-phone-normalize"),
                    {
                        "file_id": file_id,
                        "target_columns": ["Phone"],
                        "natural_language": "Normalize phone numbers",
                        "target_format": "E164",
                        "default_region": "AU",
                    },
                    format="json",
                ),
                status.HTTP_400_BAD_REQUEST,
                "INVALID_TRANSFORMATION_RULE",
            )

    def test_drf_malformed_json_error_shape(self):
        response = self.client.generic(
            "POST",
            reverse("regex-generate"),
            data=b'{"file_id":',
            content_type="application/json",
        )

        self.assert_error_shape(response, status.HTTP_400_BAD_REQUEST, "PARSE_ERROR")

    def test_drf_method_not_allowed_error_shape(self):
        response = self.client.get(reverse("regex-generate"))

        self.assert_error_shape(
            response,
            status.HTTP_405_METHOD_NOT_ALLOWED,
            "METHOD_NOT_ALLOWED",
        )

    def test_drf_unsupported_media_type_error_shape(self):
        response = self.client.generic(
            "POST",
            reverse("regex-generate"),
            data="<root />",
            content_type="application/xml",
        )

        self.assert_error_shape(
            response,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "UNSUPPORTED_MEDIA_TYPE",
        )

    def test_drf_validation_error_shape(self):
        response = structured_exception_handler(
            ValidationError({"field": ["Invalid value."]}),
            {},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request could not be validated.",
                }
            },
        )

    def assert_error_shape(self, response, expected_status, expected_code):
        self.assertEqual(response.status_code, expected_status)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertEqual(payload["error"]["code"], expected_code)
        self.assertIsInstance(payload["error"]["message"], str)
        self.assertTrue(payload["error"]["message"])

    def _upload_csv(self, content: bytes):
        uploaded_file = SimpleUploadedFile(
            "data.csv",
            content,
            content_type="text/csv",
        )
        response = self.client.post(
            reverse("file-upload"),
            {"file": uploaded_file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.json()["file_id"]
