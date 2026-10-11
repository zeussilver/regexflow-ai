"""Deterministic data-quality rules for CDR Banking Product Reference Data.

Rules follow Get Products v5 and Get Product Detail v7 of the Consumer Data
Standards (v1.36). They only read published product JSON; they never change it
or call a model, so the same products and reference time give the same issues.
"""

from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
import json
import math
from typing import Iterator, Optional

from . import cds_types


RULESET_VERSION = "2026.10"
ERROR = "error"
WARNING = "warning"
# Ignore small clock differences between the data holder and this service.
CLOCK_SKEW_TOLERANCE = timedelta(minutes=5)
VALUE_DISPLAY_LIMIT = 200

PRODUCT_CATEGORIES = frozenset(
    {
        "BUSINESS_LOANS",
        "BUY_NOW_PAY_LATER",
        "CRED_AND_CHRG_CARDS",
        "LEASES",
        "MARGIN_LOANS",
        "OVERDRAFTS",
        "PERS_LOANS",
        "REGULATED_TRUST_ACCOUNTS",
        "RESIDENTIAL_MORTGAGES",
        "TERM_DEPOSITS",
        "TRADE_FINANCE",
        "TRANS_AND_SAVINGS_ACCOUNTS",
        "TRAVEL_CARDS",
    }
)
DEPOSIT_RATE_TYPES = frozenset(
    {"BONUS", "BUNDLE_BONUS", "FIXED", "FLOATING", "INTRODUCTORY", "MARKET_LINKED", "VARIABLE"}
)
LENDING_RATE_TYPES = frozenset(
    {
        "BALANCE_TRANSFER",
        "BUNDLE_DISCOUNT_FIXED",
        "BUNDLE_DISCOUNT_VARIABLE",
        "CASH_ADVANCE",
        "DISCOUNT",
        "FIXED",
        "FLOATING",
        "INTRODUCTORY",
        "MARKET_LINKED",
        "PENALTY",
        "PURCHASE",
        "VARIABLE",
    }
)
# Adjustment rates are zero or positive; the type implies whether they are
# added or subtracted (CDS v1.32.0, standards-maintenance issue #641).
DEPOSIT_ADJUSTMENT_TYPES = frozenset({"BONUS", "BUNDLE_BONUS", "INTRODUCTORY"})
LENDING_ADJUSTMENT_TYPES = frozenset(
    {"BUNDLE_DISCOUNT_FIXED", "BUNDLE_DISCOUNT_VARIABLE", "DISCOUNT", "INTRODUCTORY", "PENALTY"}
)
APPLICATION_TYPES = frozenset({"MATURITY", "PERIODIC", "UPFRONT"})
REPAYMENT_TYPES = frozenset(
    {"INTEREST_ONLY", "OTHER", "PRINCIPAL_AND_INTEREST", "UNCONSTRAINED"}
)
LOAN_PURPOSES = frozenset({"INVESTMENT", "OTHER", "OWNER_OCCUPIED", "UNCONSTRAINED"})
FEE_TYPES = frozenset(
    {
        "CASH_ADVANCE",
        "DEPOSIT",
        "DISHONOUR",
        "ENQUIRY",
        "EVENT",
        "EXIT",
        "LATE_PAYMENT",
        "OTHER",
        "PAYMENT",
        "PERIODIC",
        "PURCHASE",
        "REPLACEMENT",
        "TRANSACTION",
        "UPFRONT",
        "UPFRONT_PER_PLAN",
        "VARIATION",
        "WITHDRAWAL",
    }
)
FEE_METHODS = frozenset({"fixedAmount", "rateBased", "variable"})
FEE_RATE_TYPES = frozenset({"BALANCE", "INTEREST_ACCRUED", "TRANSACTION"})
CARD_SCHEMES = frozenset({"AMEX", "EFTPOS", "MASTERCARD", "OTHER", "VISA"})
CARD_TYPES = frozenset({"CHARGE", "CREDIT", "DEBIT"})

MANDATORY_FIELDS = (
    "productId",
    "lastUpdated",
    "productCategory",
    "name",
    "description",
    "brand",
    "isTailored",
)
STRING_FIELDS = ("productId", "name", "description", "brand", "brandName", "brandGroup")
DATETIME_FIELDS = ("lastUpdated", "effectiveFrom", "effectiveTo")
# A primary URI is mandatory once its list of additional URIs is used.
ADDITIONAL_URI_FIELDS = (
    ("overviewUri", "additionalOverviewUris"),
    ("termsUri", "additionalTermsUris"),
    ("eligibilityUri", "additionalEligibilityUris"),
    ("feesAndPricingUri", "additionalFeesAndPricingUris"),
    ("bundleUri", "additionalBundleUris"),
)
DETAIL_FIELDS = (
    "bundles",
    "constraints",
    "depositRates",
    "eligibility",
    "features",
    "fees",
    "instalments",
    "lendingRates",
)
# Fields that Get Products and Get Product Detail both publish for a product.
COMPARED_FIELDS = (
    "name",
    "description",
    "brand",
    "brandName",
    "productCategory",
    "isTailored",
    "lastUpdated",
    "effectiveFrom",
    "effectiveTo",
    "applicationUri",
    "additionalInformation",
    "cardArt",
)
RATE_COLLECTIONS = (
    ("depositRates", "depositRateType", DEPOSIT_RATE_TYPES, DEPOSIT_ADJUSTMENT_TYPES),
    ("lendingRates", "lendingRateType", LENDING_RATE_TYPES, LENDING_ADJUSTMENT_TYPES),
)
RATE_FREQUENCY_FIELDS = ("calculationFrequency", "applicationFrequency")
TIER_BOUNDS = ("minimumValue", "maximumValue")
CONSUMER_LOAN_CATEGORIES = frozenset({"RESIDENTIAL_MORTGAGES", "PERS_LOANS"})
COMPARISON_RATE_TYPES = frozenset({"FIXED", "VARIABLE"})
# Rates a comparison site needs before it can list a non-tailored product.
EXPECTED_RATES = {
    "CRED_AND_CHRG_CARDS": "lendingRates",
    "PERS_LOANS": "lendingRates",
    "RESIDENTIAL_MORTGAGES": "lendingRates",
    "TERM_DEPOSITS": "depositRates",
}


@dataclass(frozen=True)
class Rule:
    rule_id: str
    severity: str
    title: str


RULES = {
    rule.rule_id: rule
    for rule in (
        Rule("PRD-001", ERROR, "Mandatory field missing or empty"),
        Rule("PRD-002", ERROR, "Duplicate productId"),
        Rule("PRD-003", ERROR, "Wrong JSON type"),
        Rule("PRD-004", ERROR, "Invalid DateTimeString"),
        Rule("PRD-005", ERROR, "lastUpdated is in the future"),
        Rule("PRD-006", WARNING, "Effective period ends before it starts"),
        Rule("PRD-007", WARNING, "Expired product still published"),
        Rule("PRD-008", ERROR, "Unknown enum value"),
        Rule("PRD-009", ERROR, "Invalid URI"),
        Rule("PRD-010", WARNING, "URI does not use HTTPS"),
        Rule("PRD-011", ERROR, "Invalid RateString"),
        Rule("PRD-012", ERROR, "Rate looks like a percentage"),
        Rule("PRD-013", ERROR, "Invalid ISO 8601 duration"),
        Rule("PRD-014", ERROR, "Invalid AmountString"),
        Rule("PRD-015", ERROR, "Fee method details missing"),
        Rule("PRD-016", WARNING, "Comparison rate not published"),
        Rule("PRD-017", WARNING, "Rates missing for a non-tailored product"),
        Rule("PRD-018", ERROR, "Product detail unavailable"),
        Rule("PRD-019", WARNING, "Get Products and detail disagree"),
        Rule("PRD-020", WARNING, "Leading or trailing whitespace"),
        Rule("PRD-021", ERROR, "Adjustment rate is negative"),
        Rule("PRD-022", ERROR, "PERCENT tier is not a decimal fraction"),
        Rule("PRD-023", ERROR, "Content changed without a new lastUpdated"),
    )
}


@dataclass(frozen=True)
class Issue:
    rule_id: str
    severity: str
    product_index: int
    product_id: str
    product_name: str
    field: str
    message: str
    value: str = ""


class _Findings:
    def __init__(self, product: dict, product_index: int):
        self.product_index = product_index
        self.product_id = display_value(product.get("productId"))
        self.product_name = display_value(product.get("name"))
        self.issues: list[Issue] = []

    def add(self, rule_id: str, field: str, message: str, value=None) -> None:
        rule = RULES[rule_id]
        self.issues.append(
            Issue(
                rule_id=rule.rule_id,
                severity=rule.severity,
                product_index=self.product_index,
                product_id=self.product_id,
                product_name=self.product_name,
                field=field,
                message=message,
                value=display_value(value),
            )
        )


def check_products(
    products: list[dict],
    *,
    reference_time: datetime,
    summaries: Optional[list[dict]] = None,
) -> list[Issue]:
    """Check products; summaries[i] is the Get Products entry when products[i] is a detail."""
    product_ids = Counter(
        product["productId"]
        for product in products
        if isinstance(product.get("productId"), str) and product["productId"]
    )
    issues = []
    for index, product in enumerate(products):
        findings = _Findings(product, index)
        product_id = product.get("productId")
        if isinstance(product_id, str) and product_ids[product_id] > 1:
            findings.add(
                "PRD-002",
                "productId",
                "productId is used by more than one product in this response.",
                product_id,
            )
        _check_product(product, findings, reference_time)
        summary = summaries[index] if summaries else None
        if summary is not None and summary is not product:
            _check_listed_summary(summary, product, findings, reference_time)
        issues.extend(findings.issues)

    return issues


def has_detail(product: dict) -> bool:
    # Get Products returns summaries; only Get Product Detail carries these fields.
    return any(field in product for field in DETAIL_FIELDS)


def detail_unavailable(product: dict, product_index: int, reason: str) -> Issue:
    findings = _Findings(product, product_index)
    findings.add(
        "PRD-018",
        "productId",
        f"The product is listed, but its detail request failed. {reason}",
        product.get("productId"),
    )
    return findings.issues[0]


def fingerprint(product: dict) -> str:
    """Hash a product's content, ignoring lastUpdated and the order of arrays."""
    content = {key: value for key, value in product.items() if key != "lastUpdated"}
    return sha256(_canonical(content).encode()).hexdigest()


def changed_without_update(
    product: dict, product_index: int, previous_time: datetime
) -> Issue:
    # Any change to a product, including corrections, must update lastUpdated.
    findings = _Findings(product, product_index)
    findings.add(
        "PRD-023",
        "lastUpdated",
        "The product's content differs from the check at "
        f"{previous_time.isoformat(timespec='seconds')}, but lastUpdated did not change.",
        product.get("lastUpdated"),
    )
    return findings.issues[0]


def display_value(value) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if len(text) > VALUE_DISPLAY_LIMIT:
        return f"{text[:VALUE_DISPLAY_LIMIT - 1]}…"
    return text


def _check_product(product: dict, findings: _Findings, reference_time: datetime) -> None:
    _check_summary(product, findings, reference_time)
    if has_detail(product):
        _check_rates(product, findings)
        _check_fees(product, findings)
    _check_uris(product, findings)


def _check_listed_summary(
    summary: dict, detail: dict, findings: _Findings, reference_time: datetime
) -> None:
    # Comparison sites often read Get Products first, so its problems count too.
    listed = _Findings(summary, findings.product_index)
    _check_product(summary, listed, reference_time)
    known = {(issue.rule_id, issue.field, issue.value) for issue in findings.issues}
    for issue in listed.issues:
        if (issue.rule_id, issue.field, issue.value) not in known:
            findings.issues.append(
                replace(
                    issue,
                    product_id=findings.product_id,
                    product_name=findings.product_name,
                    message=f"{issue.message} (Get Products response)",
                )
            )

    for field in COMPARED_FIELDS:
        if _comparable(summary.get(field)) != _comparable(detail.get(field)):
            findings.add(
                "PRD-019",
                field,
                "Get Products and Get Product Detail publish different values. "
                f"Detail value: {display_value(detail.get(field)) or '(none)'}",
                summary.get(field),
            )


def _check_summary(product: dict, findings: _Findings, reference_time: datetime) -> None:
    _require(findings, product, "", MANDATORY_FIELDS)

    for field in STRING_FIELDS:
        value = product.get(field)
        if value is not None and not isinstance(value, str):
            findings.add("PRD-003", field, f"{field} must be a string.", value)
        elif isinstance(value, str) and value.strip() and value != value.strip():
            findings.add(
                "PRD-020", field, f"{field} has leading or trailing whitespace.", value
            )

    is_tailored = product.get("isTailored")
    if is_tailored not in (None, "") and not isinstance(is_tailored, bool):
        findings.add(
            "PRD-003", "isTailored", "isTailored must be a JSON Boolean.", is_tailored
        )

    category = product.get("productCategory")
    if category is not None and not isinstance(category, str):
        findings.add("PRD-003", "productCategory", "productCategory must be a string.", category)
    else:
        _enum(findings, product, "", "productCategory", PRODUCT_CATEGORIES)

    _check_dates(product, findings, reference_time)

    information = product.get("additionalInformation")
    if isinstance(information, dict):
        for primary, extras in ADDITIONAL_URI_FIELDS:
            if information.get(extras) and not information.get(primary):
                findings.add(
                    "PRD-001",
                    f"additionalInformation.{primary}",
                    f"{primary} is mandatory when {extras} is provided.",
                )

    for index, card in _objects(product, "cardArt", findings):
        path = f"cardArt[{index}]"
        _require(findings, card, path, ("cardScheme", "cardType", "imageUri"))
        _enum(findings, card, path, "cardScheme", CARD_SCHEMES)
        _enum(findings, card, path, "cardType", CARD_TYPES)


def _check_dates(product: dict, findings: _Findings, reference_time: datetime) -> None:
    moments = {}
    for field in DATETIME_FIELDS:
        value = product.get(field)
        if value in (None, ""):
            continue
        moments[field] = cds_types.parse_datetime_string(value)
        if moments[field] is None:
            findings.add(
                "PRD-004",
                field,
                f"{field} is not an RFC 3339 DateTimeString with a UTC offset.",
                value,
            )

    last_updated = moments.get("lastUpdated")
    if last_updated and last_updated > reference_time + CLOCK_SKEW_TOLERANCE:
        findings.add(
            "PRD-005",
            "lastUpdated",
            f"lastUpdated is {_format_delta(last_updated - reference_time)} ahead of "
            f"the reference time {reference_time.isoformat(timespec='seconds')}.",
            product["lastUpdated"],
        )

    effective_from = moments.get("effectiveFrom")
    effective_to = moments.get("effectiveTo")
    if effective_from and effective_to and effective_to < effective_from:
        findings.add(
            "PRD-006",
            "effectiveTo",
            "effectiveTo is earlier than effectiveFrom, so the product can never be effective.",
            product["effectiveTo"],
        )
    elif effective_to and effective_to < reference_time:
        findings.add(
            "PRD-007",
            "effectiveTo",
            "effectiveTo has passed; a default (effective=CURRENT) Get Products "
            "response should no longer include this product.",
            product["effectiveTo"],
        )


def _check_rates(product: dict, findings: _Findings) -> None:
    category = _text(product.get("productCategory"))
    for collection, type_field, rate_types, adjustment_types in RATE_COLLECTIONS:
        for index, rate in _objects(product, collection, findings):
            path = f"{collection}[{index}]"
            rate_type = _text(rate.get(type_field))
            mandatory = [type_field, "rate", "applicationType"]
            enums = [(type_field, rate_types), ("applicationType", APPLICATION_TYPES)]
            if collection == "lendingRates":
                mandatory += ["repaymentType", "loanPurpose"]
                enums += [("repaymentType", REPAYMENT_TYPES), ("loanPurpose", LOAN_PURPOSES)]
            if rate.get("applicationType") == "PERIODIC":
                mandatory.append("applicationFrequency")
            _require(findings, rate, path, mandatory)
            for field, allowed in enums:
                _enum(findings, rate, path, field, allowed)

            for field in ("rate", "comparisonRate"):
                if rate.get(field) is not None:
                    _check_rate_value(findings, f"{path}.{field}", rate[field])
            if (
                rate_type in adjustment_types
                and cds_types.is_rate_string(rate.get("rate"))
                and Decimal(rate["rate"]) < 0
            ):
                findings.add(
                    "PRD-021",
                    f"{path}.rate",
                    f"{rate_type} rates must be zero or positive; the rate type "
                    "already says whether it is added or subtracted.",
                    rate["rate"],
                )
            _check_percent_tiers(rate, path, findings)

            for field in RATE_FREQUENCY_FIELDS:
                value = rate.get(field)
                if value is not None and not cds_types.is_iso8601_duration(value):
                    findings.add(
                        "PRD-013",
                        f"{path}.{field}",
                        f"{field} is not an ISO 8601 duration such as P1M.",
                        value,
                    )

            if (
                collection == "lendingRates"
                and category in CONSUMER_LOAN_CATEGORIES
                and product.get("isTailored") is False
                and rate_type in COMPARISON_RATE_TYPES
                and not rate.get("comparisonRate")
            ):
                findings.add(
                    "PRD-016",
                    f"{path}.comparisonRate",
                    f"No comparisonRate is published for this {rate_type} rate, "
                    "so consumers cannot compare its full cost.",
                    rate.get("rate"),
                )

    expected = EXPECTED_RATES.get(category)
    if expected and product.get("isTailored") is False and not product.get(expected):
        findings.add(
            "PRD-017",
            expected,
            f"This non-tailored {category} product publishes no {expected}.",
        )


def _check_fees(product: dict, findings: _Findings) -> None:
    for index, fee in _objects(product, "fees", findings):
        path = f"fees[{index}]"
        _require(findings, fee, path, ("name", "feeType", "feeMethodUType"))
        _enum(findings, fee, path, "feeType", FEE_TYPES)
        _enum(findings, fee, path, "feeMethodUType", FEE_METHODS)

        method = _text(fee.get("feeMethodUType"))
        if method in FEE_METHODS:
            details = fee.get(method)
            if not isinstance(details, dict):
                findings.add(
                    "PRD-015",
                    f"{path}.{method}",
                    f"feeMethodUType is {method}, but the {method} object is missing.",
                )
            elif method == "fixedAmount":
                _require(findings, details, f"{path}.fixedAmount", ("amount",))
            elif method == "rateBased":
                _require(findings, details, f"{path}.rateBased", ("rate", "rateType"))
                _enum(findings, details, f"{path}.rateBased", "rateType", FEE_RATE_TYPES)

        for field, value in _fee_amounts(fee):
            if value is not None and not cds_types.is_amount_string(value):
                findings.add(
                    "PRD-014",
                    f"{path}.{field}",
                    f"{field} is not an AmountString such as 10.00.",
                    value,
                )
        for field, value in _fee_rates(fee):
            if value is not None:
                _check_rate_value(findings, f"{path}.{field}", value)


def _check_uris(product: dict, findings: _Findings) -> None:
    for path, value in _walk_uris(product):
        # Card art may embed the image as an RFC 2397 data URI.
        if path.endswith("imageUri") and str(value).startswith("data:image/"):
            continue
        problem = cds_types.uri_problem(value)
        if problem:
            findings.add("PRD-009", path, f"The URI {problem}.", value)
        elif value.lower().startswith("http://"):
            findings.add("PRD-010", path, "The URI uses http instead of https.", value)


def _check_rate_value(findings: _Findings, path: str, value) -> None:
    if not cds_types.is_rate_string(value):
        findings.add(
            "PRD-011",
            path,
            "The rate is not a RateString (a decimal fraction such as 0.0525).",
            value,
        )
    elif abs(Decimal(value)) > 1:
        # RateString has no bounds, but deposit and lending rates above 100% are
        # almost always percentages published in the wrong format.
        findings.add(
            "PRD-012",
            path,
            f"The rate means {Decimal(value) * 100:f}%. It looks like a percentage "
            "published where a decimal fraction is required.",
            value,
        )


def _check_percent_tiers(rate: dict, path: str, findings: _Findings) -> None:
    # PERCENT tier bounds use the RateString style: 0.8 means 80% (issue #614).
    for index, tier in _objects(rate, "tiers", findings, path):
        if tier.get("unitOfMeasure") != "PERCENT":
            continue
        for bound in TIER_BOUNDS:
            number = _decimal(tier.get(bound))
            if number is not None and number > 1:
                findings.add(
                    "PRD-022",
                    f"{path}.tiers[{index}].{bound}",
                    "PERCENT tier values are decimal fractions (0.8 means 80%), "
                    f"so this value means {number * 100:f}%.",
                    tier.get(bound),
                )


def _require(findings: _Findings, obj: dict, path: str, fields) -> None:
    # CDS: mandatory fields must be present and non-null; "" is not null but
    # carries no information, so it is reported too.
    for field in fields:
        value = obj.get(field)
        if value is None:
            findings.add("PRD-001", _join(path, field), f"{field} is mandatory but missing.")
        elif isinstance(value, str) and not value.strip():
            findings.add(
                "PRD-001", _join(path, field), f"{field} is mandatory but empty.", value
            )


def _enum(findings: _Findings, obj: dict, path: str, field: str, allowed) -> None:
    value = obj.get(field)
    if value not in (None, "") and _text(value) not in allowed:
        findings.add(
            "PRD-008", _join(path, field), f"{field} is not a supported value.", value
        )


def _objects(
    parent: dict, field: str, findings: _Findings, path: str = ""
) -> Iterator[tuple[int, dict]]:
    value = parent.get(field)
    if value is None:
        return
    field_path = _join(path, field)
    if not isinstance(value, list):
        findings.add("PRD-003", field_path, f"{field} must be an array.", value)
        return
    for index, item in enumerate(value):
        if isinstance(item, dict):
            yield index, item
        else:
            findings.add(
                "PRD-003", f"{field_path}[{index}]", "Each entry must be a JSON object.", item
            )


def _decimal(value) -> Optional[Decimal]:
    # Tier bounds were JSON numbers before CDS v1.34.0 and strings after it.
    if isinstance(value, int) and not isinstance(value, bool):
        return Decimal(value)
    if isinstance(value, float) and math.isfinite(value):
        return Decimal(str(value))
    if cds_types.is_rate_string(value):
        return Decimal(value)
    return None


def _comparable(value):
    # Treat absent, null and empty values alike when comparing representations.
    if isinstance(value, dict):
        value = {key: _comparable(child) for key, child in value.items()}
        value = {key: child for key, child in value.items() if child is not None}
    elif isinstance(value, list):
        value = [_comparable(child) for child in value]
    return None if value in ("", [], {}) else value


def _canonical(value) -> str:
    if isinstance(value, dict):
        items = (f"{json.dumps(key)}:{_canonical(child)}" for key, child in value.items())
        return "{" + ",".join(sorted(items)) + "}"
    if isinstance(value, list):
        return "[" + ",".join(sorted(_canonical(child) for child in value)) + "]"
    return json.dumps(value, ensure_ascii=False)


def _text(value) -> str:
    # Enum lookups must not fail on unhashable JSON values such as lists.
    return value if isinstance(value, str) else ""


def _join(path: str, field: str) -> str:
    return f"{path}.{field}" if path else field


def _fee_amounts(fee: dict) -> Iterator[tuple[str, object]]:
    # Detail v5 and earlier put amounts on the fee; v6+ nest them by method.
    yield "amount", fee.get("amount")
    fixed_amount = fee.get("fixedAmount")
    if isinstance(fixed_amount, dict):
        yield "fixedAmount.amount", fixed_amount.get("amount")
    variable = fee.get("variable")
    if isinstance(variable, dict):
        yield "variable.feeMinimum", variable.get("feeMinimum")
        yield "variable.feeMaximum", variable.get("feeMaximum")
    yield "feeCap", fee.get("feeCap")


def _fee_rates(fee: dict) -> Iterator[tuple[str, object]]:
    for field in ("balanceRate", "transactionRate", "accruedRate"):
        yield field, fee.get(field)
    rate_based = fee.get("rateBased")
    if isinstance(rate_based, dict):
        yield "rateBased.rate", rate_based.get("rate")


def _walk_uris(value, path: str = "") -> Iterator[tuple[str, object]]:
    # Every CDS field whose name ends in "Uri" is a URIString.
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = _join(path, key)
            if key.endswith("Uri") and child is not None:
                yield child_path, child
            else:
                yield from _walk_uris(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_uris(child, f"{path}[{index}]")


def _format_delta(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes >= 48 * 60:
        return f"{minutes // (24 * 60)} days"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes} min" if hours else f"{minutes} min"
