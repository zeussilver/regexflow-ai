from pathlib import Path
import shutil
from unittest.mock import patch

import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.transformations.pii_policy_service import PiiPolicyServiceError
from apps.transformations.phone_rule_service import PhoneRuleServiceError


TEST_MEDIA_ROOT = "/tmp/regexflow-ai-transformations-test-media"
PREVIEW_LIMIT = 50
PII_POLICY_SERVICE_TARGET = (
    "apps.transformations.pii_policy_service.generate_pii_redaction_policy"
)
PHONE_RULE_SERVICE_TARGET = (
    "apps.transformations.phone_rule_service.generate_phone_normalization_rule"
)


class TransformationApiTestMixin:
    maxDiff = None

    def setUp(self):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

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

    def _processed_dataframe(self, processed_file_id):
        processed_path = (
            Path(TEST_MEDIA_ROOT) / "processed" / f"{processed_file_id}.csv"
        )
        self.assertTrue(processed_path.exists())
        return pd.read_csv(processed_path, dtype=str).fillna("")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PiiRedactionApiTests(TransformationApiTestMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.policy_patcher = patch(PII_POLICY_SERVICE_TARGET)
        self.mock_generate_policy = self.policy_patcher.start()
        self.mock_generate_policy.return_value = self._valid_pii_policy()

    def tearDown(self):
        self.policy_patcher.stop()
        super().tearDown()

    def test_redacts_email_addresses(self):
        file_id = self._upload_csv(
            b"Name,Contact\nAda,ada@example.com\nGrace,grace@example.org\nPlain,not pii\n"
        )

        response = self.client.post(
            reverse("transformation-pii-redact"),
            {
                "file_id": file_id,
                "target_columns": ["Contact"],
                "pii_types": ["email"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self._assert_pii_success(payload, file_id=file_id, row_count=3)
        self.assertEqual(payload["processed_preview"][0]["Contact"], "[EMAIL_REDACTED]")
        self.assertEqual(payload["processed_preview"][1]["Contact"], "[EMAIL_REDACTED]")
        self.assertEqual(payload["processed_preview"][2]["Contact"], "not pii")
        self.assertEqual(payload["policy"]["pii_types"], ["email"])
        self.assertEqual(payload["policy"]["target_columns_policy"], "selected_columns")
        self.assertEqual(payload["stats"]["by_type"]["email"]["matches"], 2)
        self.mock_generate_policy.assert_called_once()

    def test_redacts_urls(self):
        file_id = self._upload_csv(
            (
                b"Name,Website\n"
                b"Ada,https://example.com/profile\n"
                b"Grace,http://grace.example.org?q=1\n"
                b"Plain,not a url\n"
            )
        )

        response = self.client.post(
            reverse("transformation-pii-redact"),
            {
                "file_id": file_id,
                "target_columns": ["Website"],
                "pii_types": ["url"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["processed_preview"][0]["Website"], "[URL_REDACTED]")
        self.assertEqual(payload["processed_preview"][1]["Website"], "[URL_REDACTED]")
        self.assertEqual(payload["processed_preview"][2]["Website"], "not a url")
        self.assertEqual(payload["stats"]["by_type"]["url"]["matches"], 2)

    def test_redacts_phone_numbers(self):
        file_id = self._upload_csv(
            b"Name,Phone\nAda,0412 345 678\nGrace,+61 412 345 678\nPlain,not a phone\n"
        )

        response = self.client.post(
            reverse("transformation-pii-redact"),
            {
                "file_id": file_id,
                "target_columns": ["Phone"],
                "pii_types": ["phone"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["processed_preview"][0]["Phone"], "[PHONE_REDACTED]")
        self.assertEqual(payload["processed_preview"][1]["Phone"], "[PHONE_REDACTED]")
        self.assertEqual(payload["processed_preview"][2]["Phone"], "not a phone")
        self.assertEqual(payload["stats"]["by_type"]["phone"]["matches"], 2)

    def test_redacts_credit_card_like_numbers_with_luhn_validation(self):
        file_id = self._upload_csv(
            b"Name,Payment\nValid,4111 1111 1111 1111\nInvalid,4111 1111 1111 1112\n"
        )

        response = self.client.post(
            reverse("transformation-pii-redact"),
            {
                "file_id": file_id,
                "target_columns": ["Payment"],
                "pii_types": ["credit_card"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["processed_preview"][0]["Payment"], "[CARD_REDACTED]")
        self.assertEqual(
            payload["processed_preview"][1]["Payment"], "4111 1111 1111 1112"
        )
        self.assertEqual(payload["stats"]["by_type"]["credit_card"]["matches"], 1)
        self.assertEqual(payload["stats"]["changed_cells"], 1)

    def test_handles_null_values_safely(self):
        file_id = self._upload_csv(b"Name,Contact\nMissing,\nAda,ada@example.com\n")

        response = self.client.post(
            reverse("transformation-pii-redact"),
            {
                "file_id": file_id,
                "target_columns": ["Contact"],
                "pii_types": ["email"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertIsNone(payload["processed_preview"][0]["Contact"])
        self.assertEqual(payload["processed_preview"][1]["Contact"], "[EMAIL_REDACTED]")
        self.assertEqual(payload["stats"]["checked_cells"], 2)
        self.assertEqual(payload["stats"]["changed_cells"], 1)

    def test_preserves_non_target_columns(self):
        file_id = self._upload_csv(
            (
                b"ID,Name,Contact,Notes\n"
                b"1,Ada,ada@example.com,keep this note\n"
                b"2,Grace,grace@example.org,also keep this\n"
            )
        )

        response = self.client.post(
            reverse("transformation-pii-redact"),
            {
                "file_id": file_id,
                "target_columns": ["Contact"],
                "pii_types": ["email"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["columns"], ["ID", "Name", "Contact", "Notes"])
        self.assertEqual(payload["processed_preview"][0]["Name"], "Ada")
        self.assertEqual(payload["processed_preview"][0]["Notes"], "keep this note")
        processed_dataframe = self._processed_dataframe(payload["processed_file_id"])
        self.assertEqual(processed_dataframe["Name"].tolist(), ["Ada", "Grace"])
        self.assertEqual(
            processed_dataframe["Notes"].tolist(),
            ["keep this note", "also keep this"],
        )

    def test_returns_correct_stats_by_pii_type(self):
        file_id = self._upload_csv(
            (
                b"ID,Value\n"
                b"1,ada@example.com\n"
                b"2,https://example.com/profile\n"
                b"3,0412 345 678\n"
                b"4,4111 1111 1111 1111\n"
                b"5,not pii\n"
            )
        )

        response = self.client.post(
            reverse("transformation-pii-redact"),
            {
                "file_id": file_id,
                "target_columns": ["Value"],
                "pii_types": ["email", "url", "phone", "credit_card"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["stats"],
            {
                "checked_cells": 5,
                "changed_cells": 4,
                "total_replacements": 4,
                "by_type": {
                    "email": {"matches": 1, "changed_cells": 1},
                    "phone": {"matches": 1, "changed_cells": 1},
                    "credit_card": {"matches": 1, "changed_cells": 1},
                    "url": {"matches": 1, "changed_cells": 1},
                },
            },
        )

    def test_unsupported_pii_type_returns_unsupported_pii_type(self):
        file_id = self._upload_csv(b"Name,Contact\nAda,ada@example.com\n")

        response = self.client.post(
            reverse("transformation-pii-redact"),
            {
                "file_id": file_id,
                "target_columns": ["Contact"],
                "pii_types": ["unsupported_type"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "UNSUPPORTED_PII_TYPE")

    def test_missing_file_returns_file_not_found(self):
        response = self.client.post(
            reverse("transformation-pii-redact"),
            {
                "file_id": "00000000-0000-0000-0000-000000000000",
                "target_columns": ["Contact"],
                "pii_types": ["email"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "FILE_NOT_FOUND")

    def test_missing_target_column_returns_column_not_found(self):
        file_id = self._upload_csv(b"Name,Email\nAda,ada@example.com\n")

        response = self.client.post(
            reverse("transformation-pii-redact"),
            {
                "file_id": file_id,
                "target_columns": ["Phone"],
                "pii_types": ["email"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "COLUMN_NOT_FOUND")

    def test_invalid_llm_policy_returns_unsupported_transformation_rule(self):
        file_id = self._upload_csv(b"Name,Contact\nAda,ada@example.com\n")
        self.mock_generate_policy.return_value = {
            "transformation_type": "phone_normalization",
            "pii_types": ["email"],
            "target_columns_policy": "selected_columns",
            "replacement_strategy": "typed_placeholders",
            "explanation": "Wrong transformation type.",
        }

        response = self.client.post(
            reverse("transformation-pii-redact"),
            {
                "file_id": file_id,
                "target_columns": ["Contact"],
                "pii_types": ["email"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(
            response.json()["error"]["code"], "UNSUPPORTED_TRANSFORMATION_RULE"
        )

    def test_llm_policy_error_returns_structured_error(self):
        file_id = self._upload_csv(b"Name,Contact\nAda,ada@example.com\n")
        self.mock_generate_policy.side_effect = PiiPolicyServiceError(
            code="LLM_INVALID_JSON",
            message="The LLM did not return valid JSON.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )

        response = self.client.post(
            reverse("transformation-pii-redact"),
            {
                "file_id": file_id,
                "target_columns": ["Contact"],
                "pii_types": ["email"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.json()["error"]["code"], "LLM_INVALID_JSON")

    @staticmethod
    def _valid_pii_policy():
        return {
            "transformation_type": "pii_redaction",
            "pii_types": ["email", "phone", "credit_card", "url"],
            "target_columns_policy": "all_text_columns",
            "replacement_strategy": "typed_placeholders",
            "explanation": "Redact supported PII using deterministic backend rules.",
        }

    def _assert_pii_success(self, payload, *, file_id, row_count):
        self.assertEqual(payload["transformation"], "pii_redaction")
        self.assertEqual(payload["file_id"], file_id)
        self.assertRegex(payload["processed_file_id"], r"^[0-9a-f-]{36}$")
        self.assertEqual(payload["row_count"], row_count)
        self.assertEqual(payload["preview_limit"], PREVIEW_LIMIT)
        self.assertEqual(len(payload["processed_preview"]), row_count)
        self.assertEqual(payload["policy"]["transformation_type"], "pii_redaction")
        self.assertIn(payload["policy"]["replacement_strategy"], {"typed_placeholders"})


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PhoneNormalizationApiTests(TransformationApiTestMixin, APITestCase):
    def test_valid_llm_rule_normalizes_au_mobile_number(self):
        file_id = self._upload_csv(b"Name,Phone\nAda,0412 345 678\n")

        response, mock_generate_rule = self._post_phone_normalize(file_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_generate_rule.assert_called_once()
        call_kwargs = mock_generate_rule.call_args.kwargs
        self.assertEqual(call_kwargs["target_columns"], ["Phone"])
        self.assertLessEqual(len(call_kwargs["sample_values"]), 10)
        payload = response.json()
        self._assert_phone_success(payload, file_id=file_id, row_count=1)
        self.assertEqual(payload["processed_preview"][0]["Phone"], "+61412345678")
        self.assertEqual(
            payload["stats"],
            {
                "checked_cells": 1,
                "normalized_cells": 1,
                "invalid_cells": 0,
                "unchanged_cells": 0,
            },
        )

    def test_valid_llm_rule_normalizes_au_landline_number(self):
        file_id = self._upload_csv(b"Name,Phone\nAda,03 9123 4567\n")

        response, mock_generate_rule = self._post_phone_normalize(file_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_generate_rule.assert_called_once()
        self.assertEqual(response.json()["processed_preview"][0]["Phone"], "+61391234567")

    def test_already_international_number_is_normalized_consistently(self):
        file_id = self._upload_csv(b"Name,Phone\nAda,+61 412 345 678\n")

        response, mock_generate_rule = self._post_phone_normalize(file_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_generate_rule.assert_called_once()
        self.assertEqual(response.json()["processed_preview"][0]["Phone"], "+61412345678")

    def test_invalid_number_is_preserved(self):
        file_id = self._upload_csv(b"Name,Phone\nAda,abc123\n")

        response, mock_generate_rule = self._post_phone_normalize(file_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_generate_rule.assert_called_once()
        self.assertEqual(response.json()["processed_preview"][0]["Phone"], "abc123")

    def test_invalid_number_increments_invalid_cells(self):
        file_id = self._upload_csv(
            b"Name,Phone\nAda,abc123\nGrace,0412 345 678\n"
        )

        response, mock_generate_rule = self._post_phone_normalize(file_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_generate_rule.assert_called_once()
        self.assertEqual(
            response.json()["stats"],
            {
                "checked_cells": 2,
                "normalized_cells": 1,
                "invalid_cells": 1,
                "unchanged_cells": 1,
            },
        )

    def test_unsupported_target_format_returns_unsupported_target_format(self):
        file_id = self._upload_csv(b"Name,Phone\nAda,0412 345 678\n")

        response, mock_generate_rule = self._post_phone_normalize(
            file_id, target_format="LOCAL"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_generate_rule.assert_not_called()
        self.assertEqual(response.json()["error"]["code"], "UNSUPPORTED_TARGET_FORMAT")

    def test_invalid_llm_json_returns_llm_invalid_json(self):
        file_id = self._upload_csv(b"Name,Phone\nAda,0412 345 678\n")

        response, mock_generate_rule = self._post_phone_normalize(
            file_id,
            rule_exception=PhoneRuleServiceError(
                code="LLM_INVALID_JSON",
                message="The LLM did not return valid JSON.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        mock_generate_rule.assert_called_once()
        self.assertEqual(response.json()["error"]["code"], "LLM_INVALID_JSON")

    def test_wrong_transformation_type_returns_invalid_transformation_rule(self):
        file_id = self._upload_csv(b"Name,Phone\nAda,0412 345 678\n")
        invalid_rule = self._valid_au_e164_rule()
        invalid_rule["transformation_type"] = "pii_redaction"

        response, mock_generate_rule = self._post_phone_normalize(
            file_id, rule=invalid_rule
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_generate_rule.assert_called_once()
        self.assertEqual(response.json()["error"]["code"], "INVALID_TRANSFORMATION_RULE")

    def test_missing_target_column_returns_column_not_found(self):
        file_id = self._upload_csv(b"Name,Email\nAda,ada@example.com\n")

        response, mock_generate_rule = self._post_phone_normalize(
            file_id, target_column="Phone"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_generate_rule.assert_not_called()
        self.assertEqual(response.json()["error"]["code"], "COLUMN_NOT_FOUND")

    def test_empty_natural_language_returns_empty_natural_language(self):
        file_id = self._upload_csv(b"Name,Phone\nAda,0412 345 678\n")

        response, mock_generate_rule = self._post_phone_normalize(
            file_id, natural_language=" "
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_generate_rule.assert_not_called()
        self.assertEqual(response.json()["error"]["code"], "EMPTY_NATURAL_LANGUAGE")

    def _post_phone_normalize(
        self,
        file_id,
        *,
        target_column="Phone",
        natural_language="Normalize phone numbers to international format",
        target_format="E164",
        default_region="AU",
        rule=None,
        rule_exception=None,
    ):
        if rule is None:
            rule = self._valid_au_e164_rule(
                target_format=target_format,
                default_region=default_region,
            )

        with patch(PHONE_RULE_SERVICE_TARGET) as mock_generate_rule:
            if rule_exception is not None:
                mock_generate_rule.side_effect = rule_exception
            else:
                mock_generate_rule.return_value = rule

            response = self.client.post(
                reverse("transformation-phone-normalize"),
                {
                    "file_id": file_id,
                    "target_columns": [target_column],
                    "natural_language": natural_language,
                    "default_region": default_region,
                    "target_format": target_format,
                },
                format="json",
            )

        return response, mock_generate_rule

    @staticmethod
    def _valid_au_e164_rule(*, target_format="E164", default_region="AU"):
        return {
            "transformation_type": "phone_normalization",
            "target_format": target_format,
            "default_region": default_region,
            "preserve_invalid": True,
            "explanation": (
                "Normalize phone numbers to E.164 format using AU as the default region."
            ),
        }

    def _assert_phone_success(self, payload, *, file_id, row_count):
        self.assertEqual(payload["transformation"], "phone_normalization")
        self.assertEqual(payload["file_id"], file_id)
        self.assertRegex(payload["processed_file_id"], r"^[0-9a-f-]{36}$")
        self.assertEqual(payload["rule"], self._valid_au_e164_rule())
        self.assertEqual(payload["row_count"], row_count)
        self.assertEqual(payload["preview_limit"], PREVIEW_LIMIT)
        self.assertEqual(len(payload["processed_preview"]), row_count)
