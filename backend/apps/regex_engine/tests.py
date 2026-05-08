import json
import os
from pathlib import Path
import shutil
from unittest.mock import patch

import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


TEST_MEDIA_ROOT = "/tmp/regexflow-ai-regex-test-media"


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class RegexGenerateApiTests(APITestCase):
    def setUp(self):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    @patch("apps.regex_engine.llm_service.generate_regex")
    def test_valid_regex_generation_with_mocked_llm_output(self, mock_generate_regex):
        file_id = self._upload_contacts_csv()
        mock_generate_regex.return_value = {
            "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b",
            "explanation": "Matches common email addresses.",
            "flags": ["IGNORECASE"],
            "confidence": "high",
        }

        response = self.client.post(
            reverse("regex-generate"),
            {
                "file_id": file_id,
                "target_column": "Email",
                "natural_language": "Find email addresses",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertIn("regex", payload)
        self.assertEqual(payload["flags"], ["IGNORECASE"])
        self.assertEqual(payload["target_column"], "Email")
        self.assertEqual(payload["explanation"], "Matches common email addresses.")
        self.assertEqual(payload["match_preview"]["checked_rows"], 3)
        self.assertGreater(payload["match_preview"]["matched_rows"], 0)
        self.assertEqual(payload["match_preview"]["examples"][0]["row_index"], 0)

    def test_regex_generation_reliability_prompt_set(self):
        file_id = self._upload_pattern_samples_csv()
        cases = [
            ("Find email addresses", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b"),
            ("Find URLs", r"\bhttps?://[^\s]+"),
            ("Find Australian phone numbers", r"\b(?:\+61|0)4\d{2}\s?\d{3}\s?\d{3}\b"),
            ("Find dates in DD/MM/YYYY format", r"\b\d{2}/\d{2}/\d{4}\b"),
            ("Find invoice IDs starting with INV-", r"\bINV-[A-Z0-9]+\b"),
            ("Find numbers with dollar signs", r"\$\d+(?:\.\d{2})?"),
            ("Find text inside brackets", r"\[[^\]]+\]"),
            ("Find postcodes", r"\b\d{4}\b"),
        ]

        with patch.dict(
            os.environ,
            {
                "LLM_API_KEY": "test-key",
                "LLM_BASE_URL": "https://llm.test/v1",
                "LLM_MODEL": "test-model",
            },
        ):
            for prompt, regex in cases:
                with self.subTest(prompt=prompt):
                    with patch(
                        "apps.regex_engine.llm_service._call_openai_compatible",
                        return_value=json.dumps(
                            {
                                "regex": regex,
                                "explanation": f"Pattern for: {prompt}",
                                "flags": [],
                                "confidence": "high",
                            }
                        ),
                    ):
                        response = self.client.post(
                            reverse("regex-generate"),
                            {
                                "file_id": file_id,
                                "target_column": "Value",
                                "natural_language": prompt,
                            },
                            format="json",
                        )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                payload = response.json()
                self.assertEqual(payload["regex"], regex)
                self.assertGreater(payload["match_preview"]["matched_rows"], 0)
                self.assertEqual(payload["warnings"], [])

    def test_invalid_file_id_returns_file_not_found(self):
        response = self.client.post(
            reverse("regex-generate"),
            {
                "file_id": "00000000-0000-0000-0000-000000000000",
                "target_column": "Email",
                "natural_language": "Find email addresses",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "FILE_NOT_FOUND")

    def test_invalid_target_column_returns_column_not_found(self):
        file_id = self._upload_contacts_csv()

        response = self.client.post(
            reverse("regex-generate"),
            {
                "file_id": file_id,
                "target_column": "Phone",
                "natural_language": "Find email addresses",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "COLUMN_NOT_FOUND")

    def test_empty_natural_language_returns_empty_natural_language(self):
        file_id = self._upload_contacts_csv()

        response = self.client.post(
            reverse("regex-generate"),
            {
                "file_id": file_id,
                "target_column": "Email",
                "natural_language": " ",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "EMPTY_NATURAL_LANGUAGE")

    def test_invalid_llm_json_returns_llm_invalid_json(self):
        file_id = self._upload_contacts_csv()

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
                response = self.client.post(
                    reverse("regex-generate"),
                    {
                        "file_id": file_id,
                        "target_column": "Email",
                        "natural_language": "Find email addresses",
                    },
                    format="json",
                )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.json()["error"]["code"], "LLM_INVALID_JSON")

    @patch("apps.regex_engine.llm_service.generate_regex")
    def test_invalid_regex_returns_regex_compile_error(self, mock_generate_regex):
        file_id = self._upload_contacts_csv()
        mock_generate_regex.return_value = {
            "regex": "[",
            "explanation": "Invalid regex.",
            "flags": [],
            "confidence": "low",
        }

        response = self.client.post(
            reverse("regex-generate"),
            {
                "file_id": file_id,
                "target_column": "Email",
                "natural_language": "Find email addresses",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "REGEX_COMPILE_ERROR")

    @patch("apps.regex_engine.llm_service.generate_regex")
    def test_unsafe_regex_returns_regex_unsafe(self, mock_generate_regex):
        file_id = self._upload_contacts_csv()
        mock_generate_regex.return_value = {
            "regex": "(.+)+",
            "explanation": "Unsafe regex.",
            "flags": [],
            "confidence": "low",
        }

        response = self.client.post(
            reverse("regex-generate"),
            {
                "file_id": file_id,
                "target_column": "Email",
                "natural_language": "Find email addresses",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "REGEX_UNSAFE")

    def test_missing_llm_config_returns_clean_error(self):
        file_id = self._upload_contacts_csv()

        with patch.dict(os.environ, {"LLM_API_KEY": ""}):
            response = self.client.post(
                reverse("regex-generate"),
                {
                    "file_id": file_id,
                    "target_column": "Email",
                    "natural_language": "Find email addresses",
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json()["error"]["code"], "LLM_CONFIG_MISSING")

    def _upload_contacts_csv(self):
        uploaded_file = SimpleUploadedFile(
            "contacts.csv",
            (
                b"Name,Email\n"
                b"Ada,ada@example.com\n"
                b"Grace,grace@example.org\n"
                b"No Email,not-an-email\n"
            ),
            content_type="text/csv",
        )
        response = self.client.post(
            reverse("file-upload"),
            {"file": uploaded_file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.json()["file_id"]

    def _upload_pattern_samples_csv(self):
        uploaded_file = SimpleUploadedFile(
            "patterns.csv",
            (
                b"Value\n"
                b"ada@example.com\n"
                b"https://example.com/profile\n"
                b"0412 345 678\n"
                b"21/05/2026\n"
                b"INV-2026-A1\n"
                b"$123.45\n"
                b"[internal note]\n"
                b"3000\n"
            ),
            content_type="text/csv",
        )
        response = self.client.post(
            reverse("file-upload"),
            {"file": uploaded_file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.json()["file_id"]


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class RegexReplaceApiTests(APITestCase):
    def setUp(self):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def test_successful_email_redaction_saves_full_processed_csv(self):
        rows = ["ID,Name,Email"]
        for index in range(55):
            rows.append(f"{index + 1},User {index + 1},user{index + 1}@example.com")
        file_id = self._upload_csv("\n".join(rows).encode("utf-8"))

        response = self.client.post(
            reverse("regex-replace"),
            {
                "file_id": file_id,
                "target_column": "Email",
                "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b",
                "flags": [],
                "replacement": "REDACTED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["file_id"], file_id)
        self.assertRegex(payload["processed_file_id"], r"^[0-9a-f-]{36}$")
        self.assertEqual(payload["row_count"], 55)
        self.assertEqual(payload["preview_limit"], 50)
        self.assertEqual(len(payload["processed_preview"]), 50)
        self.assertEqual(payload["processed_preview"][0]["Email"], "REDACTED")
        self.assertEqual(
            payload["stats"],
            {
                "checked_rows": 55,
                "matched_rows": 55,
                "total_matches": 55,
                "replaced_rows": 55,
            },
        )

        processed_path = (
            Path(TEST_MEDIA_ROOT)
            / "processed"
            / f"{payload['processed_file_id']}.csv"
        )
        self.assertTrue(processed_path.exists())
        saved_dataframe = pd.read_csv(processed_path)
        self.assertEqual(len(saved_dataframe), 55)
        self.assertEqual(saved_dataframe["Email"].tolist(), ["REDACTED"] * 55)

    def test_replacement_honors_regex_flags(self):
        file_id = self._upload_csv(b"Name\nAda\nada\nGrace\n")

        response = self.client.post(
            reverse("regex-replace"),
            {
                "file_id": file_id,
                "target_column": "Name",
                "regex": "ada",
                "flags": ["IGNORECASE"],
                "replacement": "REDACTED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["stats"]["matched_rows"], 2)
        self.assertEqual(payload["processed_preview"][0]["Name"], "REDACTED")
        self.assertEqual(payload["processed_preview"][1]["Name"], "REDACTED")
        self.assertEqual(payload["processed_preview"][2]["Name"], "Grace")

    def test_empty_replacement_string_removes_matches(self):
        file_id = self._upload_csv(b"Value\nabc123\n")

        response = self.client.post(
            reverse("regex-replace"),
            {
                "file_id": file_id,
                "target_column": "Value",
                "regex": r"\d+",
                "replacement": "",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["processed_preview"][0]["Value"], "abc")

    def test_missing_replacement_field_returns_missing_replacement(self):
        file_id = self._upload_csv(b"Value\nabc123\n")

        response = self.client.post(
            reverse("regex-replace"),
            {
                "file_id": file_id,
                "target_column": "Value",
                "regex": r"\d+",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "MISSING_REPLACEMENT")

    def test_missing_column_returns_column_not_found(self):
        file_id = self._upload_csv(b"Name,Email\nAda,ada@example.com\n")

        response = self.client.post(
            reverse("regex-replace"),
            {
                "file_id": file_id,
                "target_column": "Phone",
                "regex": r"\d+",
                "replacement": "REDACTED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "COLUMN_NOT_FOUND")

    def test_invalid_regex_returns_regex_compile_error(self):
        file_id = self._upload_csv(b"Value\nabc123\n")

        response = self.client.post(
            reverse("regex-replace"),
            {
                "file_id": file_id,
                "target_column": "Value",
                "regex": "[",
                "replacement": "REDACTED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "REGEX_COMPILE_ERROR")

    def test_unsafe_regex_returns_regex_unsafe(self):
        file_id = self._upload_csv(b"Value\nabc123\n")

        response = self.client.post(
            reverse("regex-replace"),
            {
                "file_id": file_id,
                "target_column": "Value",
                "regex": "(.+)+",
                "replacement": "REDACTED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "REGEX_UNSAFE")

    def test_no_matches_returns_success_with_warning(self):
        file_id = self._upload_csv(b"Value\nabc123\n")

        response = self.client.post(
            reverse("regex-replace"),
            {
                "file_id": file_id,
                "target_column": "Value",
                "regex": "not-found",
                "replacement": "REDACTED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["stats"]["matched_rows"], 0)
        self.assertEqual(payload["stats"]["total_matches"], 0)
        self.assertEqual(payload["warnings"], ["No matches were found in the selected column."])

    def test_null_target_values_are_json_safe(self):
        file_id = self._upload_csv(b"Name,Email\nAda,\nGrace,grace@example.com\n")

        response = self.client.post(
            reverse("regex-replace"),
            {
                "file_id": file_id,
                "target_column": "Email",
                "regex": r"^$",
                "replacement": "EMPTY",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["processed_preview"][0]["Email"], "EMPTY")
        self.assertEqual(payload["processed_preview"][1]["Email"], "grace@example.com")
        self.assertEqual(payload["stats"]["matched_rows"], 1)

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
