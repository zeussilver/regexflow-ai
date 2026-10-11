import csv
from datetime import datetime, timedelta, timezone as dt_timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import socket
import tempfile
import threading
from unittest.mock import patch
from uuid import uuid4

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from . import cds_types, rules, services, sources
from .models import ProductCheckRun, ProductIssue


SAMPLE = Path(__file__).resolve().parents[3] / "samples" / "sample_cdr_products.json"
REFERENCE = datetime(2026, 10, 11, 13, 0, tzinfo=dt_timezone.utc)
HOLDER_DATE = "Sun, 11 Oct 2026 13:00:00 GMT"
MISSING = object()


def summary(**overrides):
    product = {
        "productId": "P1",
        "lastUpdated": "2026-10-01T00:00:00Z",
        "productCategory": "TRANS_AND_SAVINGS_ACCOUNTS",
        "name": "Everyday",
        "description": "An everyday account.",
        "brand": "EXAMPLE",
        "brandName": "Example Bank",
        "applicationUri": "https://example.com/apply",
        "isTailored": False,
        "additionalInformation": {"overviewUri": "https://example.com/overview"},
    }
    product.update(overrides)
    return {key: value for key, value in product.items() if value is not MISSING}


def lending_rate(**overrides):
    rate = {
        "lendingRateType": "FIXED",
        "rate": "0.0599",
        "comparisonRate": "0.0612",
        "calculationFrequency": "P1D",
        "applicationType": "PERIODIC",
        "applicationFrequency": "P1M",
        "repaymentType": "PRINCIPAL_AND_INTEREST",
        "loanPurpose": "OWNER_OCCUPIED",
    }
    rate.update(overrides)
    return {key: value for key, value in rate.items() if value is not MISSING}


def fee(**overrides):
    item = {
        "name": "Application fee",
        "feeType": "UPFRONT",
        "feeMethodUType": "fixedAmount",
        "fixedAmount": {"amount": "250.00"},
    }
    item.update(overrides)
    return {key: value for key, value in item.items() if value is not MISSING}


def detail(**overrides):
    return summary(
        **{
            "productCategory": "RESIDENTIAL_MORTGAGES",
            "lendingRates": [lending_rate()],
            "fees": [fee()],
            "features": [
                {"featureType": "OFFSET", "additionalInfoUri": "https://example.com/offset"}
            ],
            **overrides,
        }
    )


def check(products, **kwargs):
    return rules.check_products(products, reference_time=REFERENCE, **kwargs)


def rule_ids(products, **kwargs):
    return [issue.rule_id for issue in check(products, **kwargs)]


class CdsTypeTests(SimpleTestCase):
    def test_datetime_strings_need_rfc3339_with_an_offset(self):
        utc = dt_timezone.utc
        valid = {
            "2026-10-12T00:01:05.000Z": datetime(2026, 10, 12, 0, 1, 5, tzinfo=utc),
            "2026-10-12t00:01:05z": datetime(2026, 10, 12, 0, 1, 5, tzinfo=utc),
            "2026-10-12T11:01:05+11:00": datetime(2026, 10, 12, 0, 1, 5, tzinfo=utc),
            "2026-10-12T00:01:05.123456789Z": datetime(
                2026, 10, 12, 0, 1, 5, 123456, tzinfo=utc
            ),
        }
        for value, expected in valid.items():
            with self.subTest(value=value):
                self.assertEqual(cds_types.parse_datetime_string(value), expected)
        for value in [
            "2026-10-12",
            "2026-10-12T00:01:05",
            "2026-13-01T00:00:00Z",
            "2026-02-30T00:00:00Z",
            "12/10/2026 00:00",
            20261012,
            None,
        ]:
            with self.subTest(value=value):
                self.assertIsNone(cds_types.parse_datetime_string(value))

    def test_rate_amount_and_duration_strings(self):
        for value in ["0.0525", "-0.01", "5", "0"]:
            self.assertTrue(cds_types.is_rate_string(value), value)
        for value in ["5.25%", " 0.05", "0.05 ", "", "1e-2", "1,000.5", 0.05, None]:
            self.assertFalse(cds_types.is_rate_string(value), value)
        for value in ["10.00", "-1001.23", "1.999", "0.00"]:
            self.assertTrue(cds_types.is_amount_string(value), value)
        for value in ["10", "10.0", "$10.00", "1,000.00", 10.0]:
            self.assertFalse(cds_types.is_amount_string(value), value)
        for value in ["P1M", "P1D", "PT12H", "P1Y2M3DT4H5M6S", "P0.5Y"]:
            self.assertTrue(cds_types.is_iso8601_duration(value), value)
        for value in ["P", "PT", "1M", "monthly", "P1H", ""]:
            self.assertFalse(cds_types.is_iso8601_duration(value), value)

    def test_uri_problems(self):
        self.assertIsNone(cds_types.uri_problem("https://www.example.com.au/a?b=1#c"))
        self.assertIsNone(cds_types.uri_problem("http://example.com"))
        cases = {
            "https://example.com/a ": "has leading or trailing whitespace",
            "https://example.com/a b": "contains characters that are not allowed in a URI",
            "www.example.com": "is not an absolute http(s) URI",
            "ftp://example.com/file": "is not an absolute http(s) URI",
            "https://": "is not an absolute http(s) URI",
            "http://[::1": "is not a valid URI",
            "": "is an empty string; omit the field instead",
            42: "is not a URI string",
        }
        for value, problem in cases.items():
            with self.subTest(value=value):
                self.assertEqual(cds_types.uri_problem(value), problem)


class RuleTests(SimpleTestCase):
    def test_rule_catalogue_is_complete_and_ordered(self):
        self.assertEqual(
            list(rules.RULES), [f"PRD-{number:03d}" for number in range(1, 24)]
        )
        self.assertTrue(
            all(rule.severity in {rules.ERROR, rules.WARNING} for rule in rules.RULES.values())
        )

    def test_valid_summary_and_detail_have_no_issues(self):
        self.assertEqual(rule_ids([summary(), detail(productId="P2")]), [])

    def test_summary_rules(self):
        card = {
            "cardScheme": "VISA",
            "cardType": "CREDIT",
            "imageUri": "https://example.com/card.png",
        }
        cases = [
            ({"productId": MISSING}, ["PRD-001"]),
            ({"description": "  "}, ["PRD-001"]),
            ({"isTailored": "false"}, ["PRD-003"]),
            ({"name": 42}, ["PRD-003"]),
            ({"productCategory": ["TERM_DEPOSITS"]}, ["PRD-003"]),
            ({"lastUpdated": "2026-10-01"}, ["PRD-004"]),
            ({"effectiveFrom": "2026-10-01T00:00:00"}, ["PRD-004"]),
            (
                {
                    "effectiveFrom": "2026-09-01T00:00:00Z",
                    "effectiveTo": "2026-08-01T00:00:00Z",
                },
                ["PRD-006"],
            ),
            ({"effectiveTo": "2026-10-01T00:00:00Z"}, ["PRD-007"]),
            ({"effectiveTo": "2026-12-01T00:00:00Z"}, []),
            ({"productCategory": "SAVINGS"}, ["PRD-008"]),
            ({"productCategory": "BUY_NOW_PAY_LATER"}, []),
            ({"applicationUri": "https://example.com/apply "}, ["PRD-009"]),
            ({"applicationUri": "http://example.com/apply"}, ["PRD-010"]),
            ({"applicationUri": ""}, ["PRD-009"]),
            (
                {
                    "additionalInformation": {
                        "overviewUri": "https://example.com/overview",
                        "additionalOverviewUris": [{"additionalInfoUri": "example.com"}],
                    }
                },
                ["PRD-009"],
            ),
            (
                {
                    "additionalInformation": {
                        "additionalTermsUris": [{"additionalInfoUri": "https://example.com/t"}]
                    }
                },
                ["PRD-001"],
            ),
            ({"cardArt": [dict(card, title="Card")]}, []),
            ({"cardArt": [dict(card, imageUri="data:image/png;base64,iVBORw0KGgo=")]}, []),
            ({"cardArt": [dict(card, cardScheme=None)]}, ["PRD-001"]),
            ({"cardArt": [dict(card, cardType="PREPAID")]}, ["PRD-008"]),
            ({"cardArt": {"imageUri": "https://example.com/card.png"}}, ["PRD-003"]),
            ({"name": "Everyday "}, ["PRD-020"]),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                self.assertEqual(rule_ids([summary(**overrides)]), expected)

    def test_uri_paths_point_to_nested_fields(self):
        product = summary(
            additionalInformation={
                "overviewUri": "https://example.com/overview",
                "additionalOverviewUris": [
                    {"additionalInfoUri": "https://example.com/a"},
                    {"additionalInfoUri": "https://example.com/b "},
                ]
            }
        )
        [issue] = check([product])
        self.assertEqual(
            issue.field, "additionalInformation.additionalOverviewUris[1].additionalInfoUri"
        )
        self.assertEqual(issue.value, "https://example.com/b ")

    def test_future_last_updated_uses_reference_clock_with_tolerance(self):
        ahead = summary(lastUpdated="2026-10-12T00:00:00.000Z")
        [issue] = check([ahead])
        self.assertEqual(issue.rule_id, "PRD-005")
        self.assertIn("11 h 0 min ahead", issue.message)
        within_skew = REFERENCE + timedelta(minutes=4)
        self.assertEqual(
            rule_ids([summary(lastUpdated=within_skew.isoformat().replace("+00:00", "Z"))]),
            [],
        )

    def test_duplicate_product_ids_flag_each_copy(self):
        issues = check([summary(), summary(name="Copy")])
        self.assertEqual(
            [(issue.rule_id, issue.product_index) for issue in issues],
            [("PRD-002", 0), ("PRD-002", 1)],
        )

    def test_detail_rules(self):
        percent_tier = {"unitOfMeasure": "PERCENT", "minimumValue": 0, "maximumValue": 80}
        cases = [
            ({"lendingRates": [lending_rate(rate="5.99")]}, ["PRD-012"]),
            ({"lendingRates": [lending_rate(rate="5.99%")]}, ["PRD-011"]),
            ({"lendingRates": [lending_rate(comparisonRate=0.0612)]}, ["PRD-011"]),
            ({"lendingRates": [lending_rate(lendingRateType="SUPER_LOW")]}, ["PRD-008"]),
            ({"lendingRates": [lending_rate(lendingRateType=None)]}, ["PRD-001"]),
            ({"lendingRates": [lending_rate(rate=None)]}, ["PRD-001"]),
            ({"lendingRates": [lending_rate(loanPurpose=MISSING)]}, ["PRD-001"]),
            ({"lendingRates": [lending_rate(repaymentType="BALLOON")]}, ["PRD-008"]),
            ({"lendingRates": [lending_rate(applicationFrequency=MISSING)]}, ["PRD-001"]),
            (
                {
                    "lendingRates": [
                        lending_rate(applicationType="MATURITY", applicationFrequency=MISSING)
                    ]
                },
                [],
            ),
            ({"lendingRates": [lending_rate(applicationFrequency="monthly")]}, ["PRD-013"]),
            ({"lendingRates": [lending_rate(comparisonRate=None)]}, ["PRD-016"]),
            (
                {
                    "lendingRates": [lending_rate(comparisonRate=None)],
                    "isTailored": True,
                },
                [],
            ),
            (
                {
                    "lendingRates": [
                        lending_rate(
                            lendingRateType="DISCOUNT", rate="-0.005", comparisonRate=None
                        )
                    ]
                },
                ["PRD-021"],
            ),
            ({"lendingRates": [lending_rate(tiers=[percent_tier])]}, ["PRD-022"]),
            (
                {
                    "lendingRates": [
                        lending_rate(
                            tiers=[
                                {
                                    "unitOfMeasure": "PERCENT",
                                    "minimumValue": "0.6",
                                    "maximumValue": "0.8",
                                },
                                {
                                    "unitOfMeasure": "DOLLAR",
                                    "minimumValue": "0.00",
                                    "maximumValue": "500000.00",
                                },
                            ]
                        )
                    ]
                },
                [],
            ),
            ({"lendingRates": {"rate": "0.05"}}, ["PRD-003"]),
            ({"lendingRates": []}, ["PRD-017"]),
            ({"lendingRates": [], "isTailored": True}, []),
            (
                {
                    "productCategory": "TERM_DEPOSITS",
                    "lendingRates": MISSING,
                    "depositRates": [
                        {"depositRateType": "BONUS", "rate": "-0.0025", "applicationType": "MATURITY"}
                    ],
                },
                ["PRD-021"],
            ),
            (
                {
                    "productCategory": "TERM_DEPOSITS",
                    "lendingRates": MISSING,
                    "depositRates": [
                        {"depositRateType": "FIXED", "rate": "0.0450", "applicationType": "MATURITY"}
                    ],
                },
                [],
            ),
            ({"fees": [fee(feeMethodUType="variable", fixedAmount=MISSING)]}, ["PRD-015"]),
            ({"fees": [fee(feeMethodUType="variable", fixedAmount=MISSING, variable={})]}, []),
            ({"fees": [fee(feeMethodUType="percentage")]}, ["PRD-008"]),
            ({"fees": [fee(feeType="MONTHLY")]}, ["PRD-008"]),
            ({"fees": [fee(name="")]}, ["PRD-001"]),
            ({"fees": [fee(fixedAmount={"amount": "250"})]}, ["PRD-014"]),
            ({"fees": [fee(fixedAmount={})]}, ["PRD-001"]),
            # Detail v5 and earlier: no feeMethodUType, amounts on the fee itself.
            ({"fees": [fee(feeMethodUType=MISSING, fixedAmount=MISSING, amount="2.5")]}, ["PRD-001", "PRD-014"]),
            (
                {
                    "fees": [
                        fee(
                            feeMethodUType="rateBased",
                            fixedAmount=MISSING,
                            rateBased={"rate": "3", "rateType": "TRANSACTION"},
                        )
                    ]
                },
                ["PRD-012"],
            ),
            (
                {
                    "fees": [
                        fee(
                            feeMethodUType="rateBased",
                            fixedAmount=MISSING,
                            rateBased={"rate": "0.01", "rateType": "DAILY"},
                        )
                    ]
                },
                ["PRD-008"],
            ),
            ({"features": [{"additionalInfoUri": "https://example.com/offset "}]}, ["PRD-009"]),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                self.assertEqual(rule_ids([detail(**overrides)]), expected)

    def test_summaries_do_not_trigger_detail_rules(self):
        self.assertEqual(rule_ids([summary(productCategory="TERM_DEPOSITS")]), [])

    def test_unhashable_values_are_reported_instead_of_crashing(self):
        product = detail(
            productCategory={"x": 1},
            lendingRates=[lending_rate(lendingRateType=["FIXED"])],
            fees=[fee(feeMethodUType=["fixedAmount"])],
        )
        self.assertEqual(rule_ids([product]), ["PRD-003", "PRD-008", "PRD-008"])

    def test_list_and_detail_representations_are_compared(self):
        listed = summary(applicationUri="https://example.com/apply ", cardArt=[])
        detailed = detail(
            productCategory="TRANS_AND_SAVINGS_ACCOUNTS",
            description="A different description.",
            lendingRates=MISSING,
        )
        issues = check([detailed], summaries=[listed])
        self.assertEqual(
            [(issue.rule_id, issue.field) for issue in issues],
            [
                ("PRD-009", "applicationUri"),
                ("PRD-019", "description"),
                ("PRD-019", "applicationUri"),
            ],
        )
        self.assertTrue(issues[0].message.endswith("(Get Products response)"))
        self.assertIn("Detail value: A different description.", issues[1].message)
        self.assertEqual(issues[1].value, "An everyday account.")

    def test_issues_shared_by_list_and_detail_are_reported_once(self):
        listed = summary(name="Everyday ")
        detailed = detail(
            name="Everyday ", productCategory="TRANS_AND_SAVINGS_ACCOUNTS", lendingRates=MISSING
        )
        self.assertEqual(rule_ids([detailed], summaries=[listed]), ["PRD-020"])

    def test_detail_unavailable_issue(self):
        issue = rules.detail_unavailable(summary(), 3, "The data holder returned HTTP 404.")
        self.assertEqual((issue.rule_id, issue.product_index, issue.value), ("PRD-018", 3, "P1"))
        self.assertIn("HTTP 404", issue.message)

    def test_fingerprint_ignores_last_updated_and_array_order(self):
        product = detail(fees=[fee(name="A"), fee(name="B")])
        same = detail(fees=[fee(name="B"), fee(name="A")], lastUpdated="2026-10-02T00:00:00Z")
        self.assertEqual(rules.fingerprint(product), rules.fingerprint(same))
        changed = detail(fees=[fee(name="A"), fee(name="B", fixedAmount={"amount": "300.00"})])
        self.assertNotEqual(rules.fingerprint(product), rules.fingerprint(changed))

    def test_display_values_are_serialised_and_truncated(self):
        self.assertEqual(rules.display_value(None), "")
        self.assertEqual(rules.display_value(False), "false")
        self.assertEqual(rules.display_value(["A"]), '["A"]')
        long_value = rules.display_value("x" * 300)
        self.assertEqual(len(long_value), rules.VALUE_DISPLAY_LIMIT)
        self.assertTrue(long_value.endswith("…"))


class ApiTestCase(TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.media_root = temp.name
        override = override_settings(MEDIA_ROOT=temp.name)
        override.enable()
        self.addCleanup(override.disable)
        cache.clear()
        self.client = APIClient()

    def upload(self, content, name="products.json"):
        if not isinstance(content, bytes):
            content = json.dumps(content).encode()
        return self.client.post(
            "/api/product-checks/",
            {"file": SimpleUploadedFile(name, content)},
            format="multipart",
        )

    def report_rows(self, report_file_id):
        response = self.client.get(f"/api/files/processed/{report_file_id}/download/")
        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content).decode()
        response.close()
        return list(csv.DictReader(io.StringIO(content)))


class UploadCheckApiTests(ApiTestCase):
    def test_sample_upload_reports_persists_and_exports_every_issue(self):
        response = self.upload(SAMPLE.read_bytes(), "sample_cdr_products.json")
        self.assertEqual(response.status_code, 201)
        result = response.json()
        run = result["run"]
        self.assertEqual(run["source_type"], "upload")
        self.assertEqual(run["source_label"], "sample_cdr_products.json")
        self.assertEqual(run["ruleset_version"], rules.RULESET_VERSION)
        self.assertEqual(
            [
                run[key]
                for key in (
                    "product_count",
                    "detail_count",
                    "products_with_errors",
                    "error_count",
                    "warning_count",
                )
            ],
            [6, 5, 5, 13, 5],
        )
        self.assertEqual(
            {entry["rule_id"]: entry["count"] for entry in result["by_rule"]},
            {
                "PRD-001": 1,
                "PRD-002": 2,
                "PRD-003": 1,
                "PRD-004": 1,
                "PRD-007": 1,
                "PRD-008": 1,
                "PRD-009": 1,
                "PRD-010": 1,
                "PRD-012": 1,
                "PRD-013": 1,
                "PRD-014": 1,
                "PRD-015": 1,
                "PRD-016": 1,
                "PRD-017": 1,
                "PRD-020": 1,
                "PRD-021": 1,
                "PRD-022": 1,
            },
        )
        severities = [issue["severity"] for issue in result["issues"]]
        self.assertEqual(severities, ["error"] * 13 + ["warning"] * 5)
        self.assertFalse(result["issues_truncated"])
        self.assertEqual(ProductIssue.objects.filter(run_id=run["id"]).count(), 18)

        rows = self.report_rows(run["report_file_id"])
        self.assertEqual(len(rows), 18)
        self.assertEqual(list(rows[0]), services.REPORT_COLUMNS)
        self.assertEqual(
            [row["rule_id"] for row in rows],
            [issue["rule_id"] for issue in result["issues"]],
        )

        self.assertEqual(
            self.client.get("/api/product-checks/").json()["runs"][0]["id"], run["id"]
        )
        self.assertEqual(self.client.get(f"/api/product-checks/{run['id']}/").json(), result)

    def test_supported_payload_shapes(self):
        product = summary()
        for payload in ([product], {"data": product}, {"data": {"products": [product]}}):
            with self.subTest(payload=type(payload).__name__):
                response = self.upload(payload)
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json()["run"]["product_count"], 1)
                self.assertEqual(response.json()["issues"], [])

    def test_invalid_uploads_are_rejected_without_a_run(self):
        cases = [
            (b"{not json", "products.json", "INVALID_JSON"),
            (b"NaN", "products.json", "INVALID_JSON"),
            (b"\xff\xfe", "products.json", "INVALID_JSON"),
            (b'{"data": {"products": []}}', "products.json", "NO_PRODUCTS"),
            (b'{"products": "x"}', "products.json", "UNRECOGNISED_PRODUCT_PAYLOAD"),
            (b"[1, 2]", "products.json", "UNRECOGNISED_PRODUCT_PAYLOAD"),
            (b"[]", "products.txt", "UNSUPPORTED_FILE_TYPE"),
            (b"", "products.json", "EMPTY_FILE"),
            (b" " * (5 * 1024 * 1024 + 1), "products.json", "FILE_TOO_LARGE"),
        ]
        for content, name, code in cases:
            with self.subTest(code=code, content=content[:12]):
                response = self.upload(content, name)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], code)
        with patch.object(sources, "MAX_PRODUCTS", 2):
            response = self.upload([summary()] * 3)
        self.assertEqual(response.json()["error"]["code"], "TOO_MANY_PRODUCTS")
        self.assertEqual(ProductCheckRun.objects.count(), 0)

    def test_issue_list_is_capped_but_report_is_complete(self):
        products = [{"productId": f"P{index}"} for index in range(60)]
        result = self.upload(products).json()
        self.assertEqual(result["run"]["error_count"], 360)
        self.assertEqual(result["run"]["products_with_errors"], 60)
        self.assertEqual(len(result["issues"]), services.ISSUE_RESPONSE_LIMIT)
        self.assertTrue(result["issues_truncated"])
        self.assertEqual(len(self.report_rows(result["run"]["report_file_id"])), 360)

    def test_reference_endpoints_and_missing_run(self):
        response = self.client.get(f"/api/product-checks/{uuid4()}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "CHECK_NOT_FOUND")
        with override_settings(CDR_DATA_HOLDERS={"x": ("X Bank", "https://x.example/")}):
            holders = self.client.get("/api/product-checks/holders/").json()["holders"]
        self.assertEqual(
            holders, [{"key": "x", "name": "X Bank", "product_base_uri": "https://x.example"}]
        )
        catalogue = self.client.get("/api/product-checks/rules/").json()
        self.assertEqual(catalogue["ruleset_version"], rules.RULESET_VERSION)
        self.assertEqual(
            catalogue["rules"][0],
            {
                "rule_id": "PRD-001",
                "severity": "error",
                "title": "Mandatory field missing or empty",
            },
        )

    def test_invalid_live_requests(self):
        response = self.client.post("/api/product-checks/", {}, format="json")
        self.assertEqual(response.json()["error"]["code"], "INVALID_CHECK_REQUEST")
        response = self.client.post("/api/product-checks/", {"holder": "nope"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "UNKNOWN_DATA_HOLDER")

    def test_unexpected_failure_is_sanitised(self):
        with patch(
            "apps.product_checks.services.rules.check_products",
            side_effect=RuntimeError("secret detail"),
        ):
            response = self.upload([summary()])
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("secret", response.content.decode())
        self.assertEqual(ProductCheckRun.objects.count(), 0)


class FakeHolderHandler(BaseHTTPRequestHandler):
    routes = {}
    requests = []

    def do_GET(self):
        type(self).requests.append(
            (self.path, self.headers.get("x-v"), self.headers.get("x-min-v"))
        )
        if not self.headers.get("x-v") or not self.headers.get("x-min-v"):
            status, headers, body = 406, {}, {"errors": []}
        else:
            status, headers, body = type(self).routes.get(self.path, (404, {}, {"errors": []}))
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else json.dumps(body).encode())

    def date_time_string(self, timestamp=None):
        return HOLDER_DATE

    def log_message(self, *args):
        pass


class LiveCheckTests(ApiTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHolderHandler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/bank"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        override = override_settings(CDR_DATA_HOLDERS={"fixture": ("Fixture Bank", self.base)})
        override.enable()
        self.addCleanup(override.disable)
        FakeHolderHandler.requests = []
        products = "/bank/cds-au/v1/banking/products"
        FakeHolderHandler.routes = {
            f"{products}?page-size=100": (
                200,
                {"x-v": "5"},
                {
                    "data": {"products": [summary(), summary(productId="P2", name="Saver")]},
                    "links": {"next": f"{self.base}/cds-au/v1/banking/products?page-size=100&page=2"},
                },
            ),
            f"{products}?page-size=100&page=2": (
                200,
                {"x-v": "5"},
                {"data": {"products": [summary(productId="P3", name="Gone")]}, "links": {}},
            ),
            f"{products}/P1": (
                200,
                {"x-v": "7"},
                {"data": detail(productCategory="TRANS_AND_SAVINGS_ACCOUNTS", description="Changed.")},
            ),
            f"{products}/P2": (
                200,
                {"x-v": "7"},
                {
                    "data": detail(
                        productId="P2",
                        name="Saver",
                        productCategory="TRANS_AND_SAVINGS_ACCOUNTS",
                        lastUpdated="2026-10-11T14:00:00Z",
                    )
                },
            ),
        }
        self.products_path = products

    def live(self, **payload):
        return self.client.post(
            "/api/product-checks/", {"holder": "fixture", **payload}, format="json"
        )

    def test_live_check_follows_pages_fetches_details_and_uses_the_holder_clock(self):
        response = self.live()
        self.assertEqual(response.status_code, 201)
        result = response.json()
        run = result["run"]
        self.assertEqual(
            [run[key] for key in ("source_type", "source_label", "holder_key")],
            ["live", "Fixture Bank", "fixture"],
        )
        self.assertEqual([run["list_version"], run["detail_version"]], ["5", "7"])
        self.assertEqual([run["product_count"], run["detail_count"]], [3, 2])
        self.assertEqual(run["reference_time"], "2026-10-11T13:00:00Z")
        self.assertEqual(
            {entry["rule_id"]: entry["count"] for entry in result["by_rule"]},
            {"PRD-005": 1, "PRD-018": 1, "PRD-019": 2},
        )
        future = next(issue for issue in result["issues"] if issue["rule_id"] == "PRD-005")
        self.assertIn("1 h 0 min ahead", future["message"])
        missing = next(issue for issue in result["issues"] if issue["rule_id"] == "PRD-018")
        self.assertEqual(missing["product_id"], "P3")
        self.assertIn("HTTP 404", missing["message"])
        self.assertEqual(
            sorted(FakeHolderHandler.requests),
            sorted(
                [
                    (f"{self.products_path}?page-size=100", "5", "4"),
                    (f"{self.products_path}?page-size=100&page=2", "5", "4"),
                    (f"{self.products_path}/P1", "7", "6"),
                    (f"{self.products_path}/P2", "7", "6"),
                    (f"{self.products_path}/P3", "7", "6"),
                ]
            ),
        )

    def test_summary_only_live_check_skips_detail_requests(self):
        result = self.live(include_details=False).json()
        self.assertEqual([result["run"]["product_count"], result["run"]["detail_count"]], [3, 0])
        self.assertEqual(result["run"]["detail_version"], "")
        self.assertEqual(result["by_rule"], [])
        self.assertEqual(len(FakeHolderHandler.requests), 2)

    def test_detail_requests_stop_at_the_time_budget(self):
        with patch.object(sources, "DETAIL_TIME_BUDGET_SECONDS", -1):
            result = self.live().json()
        self.assertEqual([result["run"]["product_count"], result["run"]["detail_count"]], [3, 0])
        self.assertNotIn("PRD-018", [entry["rule_id"] for entry in result["by_rule"]])
        self.assertEqual(len(FakeHolderHandler.requests), 2)

    def test_holder_failures_are_controlled(self):
        first_page = f"{self.products_path}?page-size=100"
        cases = [
            ((406, {}, {"errors": []}), "HOLDER_VERSION_UNSUPPORTED"),
            ((500, {}, {"errors": []}), "HOLDER_API_ERROR"),
            ((200, {}, b"{not json"), "HOLDER_INVALID_RESPONSE"),
            ((200, {}, {"data": {}}), "HOLDER_INVALID_RESPONSE"),
            (
                (200, {}, {"data": {"products": []}, "links": {"next": "https://elsewhere.example/p2"}}),
                "HOLDER_INVALID_RESPONSE",
            ),
            (
                (200, {}, {"data": {"products": []}, "links": {"next": f"{self.base}/cds-au/v1/banking/products?page-size=100"}}),
                "HOLDER_INVALID_RESPONSE",
            ),
        ]
        for route, code in cases:
            with self.subTest(code=code, route=route[0]):
                FakeHolderHandler.routes[first_page] = route
                response = self.live()
                self.assertEqual(response.status_code, 502)
                self.assertEqual(response.json()["error"]["code"], code)
        with patch.object(sources, "MAX_RESPONSE_BYTES", 10):
            self.assertEqual(self.live().json()["error"]["code"], "HOLDER_RESPONSE_TOO_LARGE")
        self.assertEqual(ProductCheckRun.objects.count(), 0)

    def test_unreachable_holder(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            closed_port = probe.getsockname()[1]
        with override_settings(
            CDR_DATA_HOLDERS={"fixture": ("Fixture Bank", f"http://127.0.0.1:{closed_port}")}
        ):
            response = self.live()
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"]["code"], "HOLDER_UNAVAILABLE")

    def test_live_checks_are_throttled_but_uploads_are_not(self):
        with patch.object(
            ScopedRateThrottle, "THROTTLE_RATES", {"product_checks_live": "2/hour"}
        ):
            self.assertEqual(self.live(include_details=False).status_code, 201)
            self.assertEqual(self.live(include_details=False).status_code, 201)
            response = self.live(include_details=False)
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.json()["error"]["code"], "THROTTLED")
            self.assertEqual(self.upload([summary()]).status_code, 201)

    def test_content_change_without_new_last_updated_is_flagged_on_the_next_run(self):
        first = self.live().json()["run"]
        self.assertIsNone(first["compared_with"])
        p1 = f"{self.products_path}/P1"
        status, headers, body = FakeHolderHandler.routes[p1]
        changed = dict(body["data"], fees=[fee(fixedAmount={"amount": "300.00"})])
        FakeHolderHandler.routes[p1] = (status, headers, {"data": changed})

        second = self.live().json()
        self.assertEqual(second["run"]["compared_with"], first["id"])
        self.assertEqual(second["run"]["compared_with_time"], first["created_at"])
        [silent] = [issue for issue in second["issues"] if issue["rule_id"] == "PRD-023"]
        self.assertEqual((silent["product_id"], silent["field"]), ("P1", "lastUpdated"))

        # Summary-only runs are compared only with earlier summary-only runs.
        third = self.live(include_details=False).json()
        self.assertIsNone(third["run"]["compared_with"])
        fourth = self.live(include_details=False).json()
        self.assertEqual(fourth["run"]["compared_with"], third["run"]["id"])
        self.assertEqual(fourth["by_rule"], [])

    def test_management_command_checks_configured_holders(self):
        output = io.StringIO()
        call_command("check_cdr_products", "fixture", stdout=output)
        self.assertIn("Fixture Bank: 3 products (2 with detail", output.getvalue())
        self.assertIn("PRD-018", output.getvalue())
        with self.assertRaises(CommandError):
            call_command("check_cdr_products", "nope", stdout=io.StringIO(), stderr=io.StringIO())
