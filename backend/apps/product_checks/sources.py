"""Load CDR product reference data from uploads or allowlisted data holders.

Live checks only call public base URIs configured in CDR_DATA_HOLDERS, never a
URL supplied by the client, and pagination links must stay on the same host.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
import json
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone
from rest_framework import status


# (x-min-v, x-v): current and deprecated-but-live versions as of CDS v1.36.
PRODUCT_LIST_VERSIONS = ("4", "5")
PRODUCT_DETAIL_VERSIONS = ("6", "7")
PAGE_SIZE = 100
MAX_PAGES = 20
MAX_PRODUCTS = 1000
MAX_DETAIL_REQUESTS = 300
DETAIL_WORKERS = 6
# Stay well inside the 90-second worker timeout; later products keep summaries.
DETAIL_TIME_BUDGET_SECONDS = 45
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 20
USER_AGENT = "RegexFlow-AI-product-checks/1.0"


@dataclass
class ProductSourceError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST


@dataclass(frozen=True)
class DataHolder:
    key: str
    name: str
    product_base_uri: str


@dataclass
class LoadedProducts:
    products: list[dict]
    reference_time: datetime
    list_version: str = ""
    detail_version: str = ""
    # Get Products entries, kept when details replace them in products.
    summaries: Optional[list[dict]] = None
    detail_failures: list[tuple[int, str]] = field(default_factory=list)


def configured_holders() -> list[DataHolder]:
    return [
        DataHolder(key=key, name=name, product_base_uri=base_uri.rstrip("/"))
        for key, (name, base_uri) in settings.CDR_DATA_HOLDERS.items()
    ]


def get_holder(key: str) -> DataHolder:
    for holder in configured_holders():
        if holder.key == key:
            return holder

    raise ProductSourceError(
        code="UNKNOWN_DATA_HOLDER",
        message="Choose one of the listed data holders.",
    )


def products_from_upload(uploaded_file) -> list[dict]:
    try:
        payload = _strict_json(uploaded_file.read().decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProductSourceError(
            code="INVALID_JSON",
            message="The file is not valid UTF-8 JSON.",
        ) from exc

    return products_from_payload(payload)


def products_from_payload(payload) -> list[dict]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(payload, list):
        products = payload
    elif isinstance(data, dict) and isinstance(data.get("products"), list):
        products = data["products"]
    elif isinstance(data, dict) and "productId" in data:
        products = [data]
    else:
        raise ProductSourceError(
            code="UNRECOGNISED_PRODUCT_PAYLOAD",
            message=(
                "Upload a CDR Get Products or Get Product Detail response, "
                "or a JSON array of products."
            ),
        )

    if not products:
        raise ProductSourceError(
            code="NO_PRODUCTS",
            message="The JSON does not contain any products.",
        )
    if len(products) > MAX_PRODUCTS:
        raise ProductSourceError(
            code="TOO_MANY_PRODUCTS",
            message=f"Check at most {MAX_PRODUCTS} products at a time.",
        )
    if not all(isinstance(product, dict) for product in products):
        raise ProductSourceError(
            code="UNRECOGNISED_PRODUCT_PAYLOAD",
            message="Every product must be a JSON object.",
        )

    return products


def load_live_products(holder: DataHolder, *, include_details: bool) -> LoadedProducts:
    products, list_version, reference_time = _fetch_product_list(holder)
    loaded = LoadedProducts(
        products=products,
        reference_time=reference_time,
        list_version=list_version,
    )
    if include_details:
        _attach_details(holder, loaded)
    return loaded


def _fetch_product_list(holder: DataHolder) -> tuple[list[dict], str, datetime]:
    url = f"{holder.product_base_uri}/cds-au/v1/banking/products?page-size={PAGE_SIZE}"
    products = []
    visited = set()
    list_version = ""
    reference_time = None

    while url:
        if url in visited or len(visited) == MAX_PAGES:
            raise ProductSourceError(
                code="HOLDER_INVALID_RESPONSE",
                message="The data holder's product pages did not finish.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        visited.add(url)

        payload, headers = _get_json(url, PRODUCT_LIST_VERSIONS)
        list_version = list_version or headers.get("x-v", "")
        # The holder's own clock is the fairest reference for lastUpdated.
        reference_time = reference_time or _response_time(headers)
        data = payload.get("data") if isinstance(payload, dict) else None
        page = data.get("products") if isinstance(data, dict) else None
        if not isinstance(page, list) or not all(isinstance(item, dict) for item in page):
            raise ProductSourceError(
                code="HOLDER_INVALID_RESPONSE",
                message="The data holder's response has no data.products array.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        products.extend(page)
        if len(products) > MAX_PRODUCTS:
            raise ProductSourceError(
                code="TOO_MANY_PRODUCTS",
                message=f"The data holder lists more than {MAX_PRODUCTS} products.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        url = _next_page_url(payload, holder)

    if not products:
        # Seen in production: a holder served an empty list to a server outside
        # Australia but its full catalogue to an Australian network.
        raise ProductSourceError(
            code="HOLDER_RETURNED_NO_PRODUCTS",
            message=(
                "The data holder returned an empty product list. Some data holders "
                "filter requests by network location, so results can differ outside "
                "Australia."
            ),
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    return products, list_version, reference_time or timezone.now()


def _attach_details(holder: DataHolder, loaded: LoadedProducts) -> None:
    deadline = time.monotonic() + DETAIL_TIME_BUDGET_SECONDS

    def fetch(product: dict):
        product_id = product.get("productId")
        expired = time.monotonic() > deadline
        if expired or not isinstance(product_id, str) or not product_id:
            return None, "", None

        url = (
            f"{holder.product_base_uri}/cds-au/v1/banking/products/"
            f"{quote(product_id, safe='')}"
        )
        try:
            payload, headers = _get_json(url, PRODUCT_DETAIL_VERSIONS)
        except ProductSourceError as exc:
            return None, "", exc.message

        detail = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(detail, dict):
            return None, "", "The detail response has no data object."
        return detail, headers.get("x-v", ""), None

    candidates = loaded.products[:MAX_DETAIL_REQUESTS]
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
        results = list(pool.map(fetch, candidates))

    loaded.summaries = list(loaded.products)
    for index, (detail, version, failure) in enumerate(results):
        if detail is not None:
            loaded.products[index] = detail
            loaded.detail_version = loaded.detail_version or version
        elif failure:
            loaded.detail_failures.append((index, failure))


def _get_json(url: str, versions: tuple[str, str]):
    minimum_version, version = versions
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "x-min-v": minimum_version,
            "x-v": version,
        },
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            headers = response.headers
    except HTTPError as exc:
        if exc.code == status.HTTP_406_NOT_ACCEPTABLE:
            raise ProductSourceError(
                code="HOLDER_VERSION_UNSUPPORTED",
                message=(
                    "The data holder does not support API versions "
                    f"{minimum_version}-{version} for this endpoint."
                ),
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc
        raise ProductSourceError(
            code="HOLDER_API_ERROR",
            message=f"The data holder returned HTTP {exc.code}.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc
    except (URLError, OSError) as exc:
        raise ProductSourceError(
            code="HOLDER_UNAVAILABLE",
            message="The data holder could not be reached. Try again later.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc

    if len(body) > MAX_RESPONSE_BYTES:
        raise ProductSourceError(
            code="HOLDER_RESPONSE_TOO_LARGE",
            message="The data holder's response is larger than 5 MB.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    try:
        return _strict_json(body), headers
    except ValueError as exc:
        raise ProductSourceError(
            code="HOLDER_INVALID_RESPONSE",
            message="The data holder returned invalid JSON.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc


def _strict_json(raw):
    def reject(constant):
        raise ValueError(f"{constant} is not valid JSON.")

    return json.loads(raw, parse_constant=reject)


def _next_page_url(payload: dict, holder: DataHolder) -> Optional[str]:
    links = payload.get("links")
    next_url = links.get("next") if isinstance(links, dict) else None
    if not next_url:
        return None

    base = urlsplit(holder.product_base_uri)
    candidate = urlsplit(str(next_url))
    if (candidate.scheme, candidate.netloc) != (base.scheme, base.netloc):
        raise ProductSourceError(
            code="HOLDER_INVALID_RESPONSE",
            message="The data holder's next page link points to a different host.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    return str(next_url)


def _response_time(headers) -> Optional[datetime]:
    try:
        moment = parsedate_to_datetime(headers.get("Date", ""))
    except (TypeError, ValueError, IndexError):
        return None
    return moment if moment.tzinfo else None
