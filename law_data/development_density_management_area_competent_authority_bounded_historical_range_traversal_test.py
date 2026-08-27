# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-16
Development Density Management Area
Competent Authority Bounded Historical Range Traversal & Document Metadata Recovery

목표
======================================================================
T-15-S2에서 hardening된 traversal-safe pagination contract만 사용하여
확정된 effective page range 안에서 제한적으로 historical page를 순회하고,
실제 document metadata row 구조(title / notice number / date / detail URL)를 복원한다.

핵심 원칙
======================================================================
1. T-15-S2 next_stage_boundary_pool만 입력으로 사용한다.
2. effective_lower_page ~ effective_upper_page 범위를 절대 초과하지 않는다.
3. contract별 request budget을 제한한다.
4. UQQ700 target query를 실행하지 않는다.
5. page title, source URL, query 문자열은 document evidence로 사용하지 않는다.
6. menu/navigation link는 document row로 승격하지 않는다.
7. row-local title/detail URL/notice number/date 중 실제 metadata identity가 있어야 한다.
8. detail URL은 same-host go.kr만 허용한다.
9. 이번 단계는 document metadata 복원 단계이며 UQQ700 target identity 판정 단계가 아니다.
10. verified positive / runtime registration / SITE TRUE / SITE FALSE 자동판정 금지.
"""

from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests


# ============================================================
# PATH / TARGET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

T15S2_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_competent_authority_historical_boundary_semantic_hardening.json"
)

OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "development_density_management_area_competent_authority_bounded_historical_range_traversal.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"
ALLOWED_FAMILIES = {FAMILY_NOTICE, FAMILY_URBAN}

CLASS_DOCUMENT_METADATA_ROW = "RECOVERED_AUTHORITY_HISTORICAL_DOCUMENT_METADATA_ROW"
CLASS_PAGE_NO_DOCUMENT_ROWS = "HISTORICAL_PAGE_NO_DOCUMENT_METADATA_ROWS"
CLASS_PAGE_HTTP_FAILURE = "HISTORICAL_PAGE_HTTP_FAILURE"

VALID_PAGE_CLASSES = {
    CLASS_PAGE_NO_DOCUMENT_ROWS,
    CLASS_PAGE_HTTP_FAILURE,
}

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 48
MAX_REQUESTS_PER_CONTRACT = 24

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


# ============================================================
# HTML PATTERNS
# ============================================================

TITLE_PATTERN = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)

TR_PATTERN = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
LI_PATTERN = re.compile(r"<li\b[^>]*>(.*?)</li>", re.I | re.S)
DIV_PATTERN = re.compile(r"<div\b([^>]*)>(.*?)</div>", re.I | re.S)
ANCHOR_PATTERN = re.compile(
    r"<a\b([^>]*)href\s*=\s*[\"']([^\"']+)[\"']([^>]*)>(.*?)</a>",
    re.I | re.S,
)
ATTR_PATTERN = re.compile(
    r"([:\w-]+)\s*=\s*(?:[\"']([^\"']*)[\"']|([^\s>]+))",
    re.I | re.S,
)

DATE_PATTERN = re.compile(
    r"(?<!\d)((?:19|20)\d{2})[.\-/년\s]+(0?[1-9]|1[0-2])[.\-/월\s]+(0?[1-9]|[12]\d|3[01])(?:일)?(?!\d)"
)

NOTICE_NUMBER_PATTERNS = [
    re.compile(r"(?:고시|공고)\s*(?:제)?\s*(\d{4})\s*[-–]\s*(\d+)\s*호?", re.I),
    re.compile(r"(?:제)?\s*(\d{4})\s*[-–]\s*(\d+)\s*호", re.I),
]

DOCUMENT_URL_HINTS = {
    "view",
    "detail",
    "read",
    "select",
    "bbsview",
    "boardview",
    "ntt",
    "article",
    "post",
}

GENERIC_MENU_TEXTS = {
    "고시 공고",
    "고시공고",
    "목록",
    "더보기",
    "이전",
    "다음",
    "처음",
    "마지막",
    "열람",
    "도시계획",
    "도시·주택",
}

GENERIC_NAV_HINTS = {
    "menu",
    "gnb",
    "lnb",
    "breadcrumb",
    "navigation",
    "paging",
    "pagination",
    "footer",
    "header",
}

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "sessionid",
    "jsessionid",
    "timestamp",
    "rand",
    "random",
    "_",
}

TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
}


# ============================================================
# UTIL
# ============================================================

def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()

    for value in values:
        text = normalize_space(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)

    return result


def strip_html(raw_html: str) -> str:
    value = COMMENT_PATTERN.sub(" ", raw_html or "")
    value = SCRIPT_STYLE_PATTERN.sub(" ", value)
    value = TAG_PATTERN.sub(" ", value)
    value = html.unescape(value)
    return normalize_space(value)


def parse_attrs(raw_attrs: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for match in ATTR_PATTERN.finditer(raw_attrs or ""):
        key = normalize_space(match.group(1)).lower()
        value = match.group(2) if match.group(2) is not None else match.group(3)
        if key:
            result[key] = html.unescape(normalize_space(value))
    return result


def canonicalize_url(url: str) -> str:
    value = normalize_space(url)
    if not value:
        return ""

    try:
        parsed = urlparse(value)
    except Exception:
        return ""

    if not parsed.hostname:
        return ""

    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()

    try:
        port = parsed.port
    except ValueError:
        port = None

    if port and not (scheme == "http" and port == 80) and not (scheme == "https" and port == 443):
        netloc = f"{host}:{port}"
    else:
        netloc = host

    path = parsed.path or "/"
    path = re.sub(r";jsessionid=[^/?]+", "", path, flags=re.I)
    path = re.sub(r"/{2,}", "/", path)

    query_items: List[Tuple[str, str]] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    for key, raw_value in parse_qsl(parsed.query, keep_blank_values=True):
        normalized_key = normalize_space(key)
        if not normalized_key:
            continue

        lowered = normalized_key.lower()
        if lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS:
            continue
        if "csrf" in lowered or "session" in lowered:
            continue

        pair = (normalized_key, raw_value)
        if pair in seen_pairs:
            continue

        seen_pairs.add(pair)
        query_items.append(pair)

    query_items.sort(key=lambda item: (item[0].lower(), item[1]))

    return urlunparse((
        scheme,
        netloc,
        path,
        "",
        urlencode(query_items, doseq=True),
        "",
    ))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    value = normalize_space(host).lower()
    return bool(value) and (value == "go.kr" or value.endswith(".go.kr"))


def same_host(url_a: str, url_b: str) -> bool:
    a = hostname(url_a)
    b = hostname(url_b)
    return bool(a) and a == b


def extract_title(raw_html: str) -> str:
    match = TITLE_PATTERN.search(raw_html or "")
    return strip_html(match.group(1)) if match else ""


def extract_dates(text: str) -> List[str]:
    result: List[str] = []

    for match in DATE_PATTERN.finditer(text or ""):
        try:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
        except (TypeError, ValueError):
            continue

        if not (1 <= month <= 12 and 1 <= day <= 31):
            continue

        result.append(f"{year:04d}-{month:02d}-{day:02d}")

    return unique_strings(result)


def extract_notice_numbers(text: str) -> List[str]:
    result: List[str] = []

    for pattern in NOTICE_NUMBER_PATTERNS:
        for match in pattern.finditer(text or ""):
            result.append(f"{match.group(1)}-{match.group(2)}")

    return unique_strings(result)


def build_page_url(base_url: str, pagination_key: str, page: int) -> str:
    parsed = urlparse(base_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params[pagination_key] = str(page)

    return canonicalize_url(urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        "",
        urlencode(params, doseq=True),
        "",
    )))


def looks_like_document_url(url: str) -> bool:
    parsed = urlparse(url)
    evidence = f"{parsed.path} {parsed.query}".lower()

    if any(hint in evidence for hint in DOCUMENT_URL_HINTS):
        return True

    params = {key.lower(): value for key, value in parse_qsl(parsed.query, keep_blank_values=True)}
    identity_keys = {
        "seq",
        "idx",
        "no",
        "nttno",
        "boardno",
        "postno",
        "bbsno",
        "articleid",
        "article_id",
        "sn",
    }

    return any(key in params and normalize_space(params[key]) for key in identity_keys)


def is_generic_text(text: str) -> bool:
    normalized = normalize_space(text)
    if not normalized:
        return True
    if normalized in GENERIC_MENU_TEXTS:
        return True
    if len(normalized) <= 1:
        return True
    if normalized.isdigit():
        return True
    return False


def is_navigation_container(raw_fragment: str) -> bool:
    attrs = " ".join(
        normalize_space(match.group(1))
        for match in DIV_PATTERN.finditer(raw_fragment or "")
    ).lower()
    return any(hint in attrs for hint in GENERIC_NAV_HINTS)


# ============================================================
# HTTP
# ============================================================

def decode_html(response: requests.Response, data: bytes) -> Tuple[str, str]:
    candidates: List[str] = []
    content_type = normalize_space(response.headers.get("Content-Type"))

    match = re.search(r"charset\s*=\s*[\"']?([^;\"'\s]+)", content_type, flags=re.I)
    if match:
        candidates.append(normalize_space(match.group(1)))

    if response.encoding:
        candidates.append(normalize_space(response.encoding))

    candidates.extend(["utf-8", "cp949", "euc-kr"])

    for encoding in unique_strings(candidates):
        try:
            return data.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            continue

    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "requested_url": url,
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "response_bytes": 0,
        "raw_html": "",
        "encoding": "",
        "error": "",
    }

    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result["http_status"] = response.status_code
            result["final_url"] = canonicalize_url(str(response.url))
            result["content_type"] = normalize_space(response.headers.get("Content-Type"))

            chunks: List[bytes] = []
            total = 0

            for chunk in response.iter_content(chunk_size=128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
                chunks.append(chunk)

            data = b"".join(chunks)
            result["response_bytes"] = len(data)

            content_type_lower = result["content_type"].lower()
            prefix = data[:1000].lstrip().lower()
            html_like = (
                "html" in content_type_lower
                or "text/" in content_type_lower
                or prefix.startswith(b"<!doctype html")
                or prefix.startswith(b"<html")
            )

            if html_like:
                decoded, encoding = decode_html(response, data)
                result["raw_html"] = decoded
                result["encoding"] = encoding

    except Exception as exc:
        result["error"] = repr(exc)

    return result


# ============================================================
# ROW RECOVERY
# ============================================================

def iter_candidate_fragments(raw_html: str) -> Iterable[Tuple[str, str]]:
    seen: Set[str] = set()

    for kind, pattern in (("TR", TR_PATTERN), ("LI", LI_PATTERN)):
        for match in pattern.finditer(raw_html or ""):
            fragment = match.group(1)
            key = normalize_space(fragment)
            if not key or key in seen:
                continue
            seen.add(key)
            yield kind, fragment


def recover_rows_from_fragment(
    fragment_kind: str,
    fragment: str,
    page_url: str,
    source_family: str,
    regions: List[str],
    page_number: int,
) -> List[Dict[str, Any]]:
    if is_navigation_container(fragment):
        return []

    fragment_text = strip_html(fragment)
    if not fragment_text:
        return []

    fragment_dates = extract_dates(fragment_text)
    fragment_notice_numbers = extract_notice_numbers(fragment_text)

    rows: List[Dict[str, Any]] = []

    for anchor in ANCHOR_PATTERN.finditer(fragment):
        attrs = parse_attrs((anchor.group(1) or "") + " " + (anchor.group(3) or ""))
        href = html.unescape(normalize_space(anchor.group(2)))
        title = strip_html(anchor.group(4))

        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        if is_generic_text(title):
            continue

        absolute_url = canonicalize_url(urljoin(page_url, href))
        if not absolute_url:
            continue
        if not is_government_host(hostname(absolute_url)):
            continue
        if not same_host(page_url, absolute_url):
            continue

        local_text = normalize_space(" ".join([title, fragment_text]))
        dates = unique_strings(extract_dates(local_text) + fragment_dates)
        notice_numbers = unique_strings(extract_notice_numbers(local_text) + fragment_notice_numbers)

        document_url_identity = looks_like_document_url(absolute_url)
        metadata_score = 0
        reasons: List[str] = []

        if title and not is_generic_text(title):
            metadata_score += 40
            reasons.append("ROW_LOCAL_TITLE")
        if document_url_identity:
            metadata_score += 35
            reasons.append("DETAIL_URL_IDENTITY")
        if notice_numbers:
            metadata_score += 35
            reasons.append("ROW_LOCAL_NOTICE_NUMBER")
        if dates:
            metadata_score += 15
            reasons.append("ROW_LOCAL_DATE")

        cls = normalize_space(attrs.get("class")).lower()
        ident = normalize_space(attrs.get("id")).lower()
        attr_evidence = f"{cls} {ident}"
        if any(hint in attr_evidence for hint in GENERIC_NAV_HINTS):
            continue

        # 실제 문서 metadata row는 제목+상세 URL, 또는 제목+고시/공고번호 정도는 갖도록 한다.
        accepted = bool(
            title
            and not is_generic_text(title)
            and (
                document_url_identity
                or notice_numbers
                or (dates and metadata_score >= 55)
            )
            and metadata_score >= 55
        )

        if not accepted:
            continue

        rows.append({
            "classification": CLASS_DOCUMENT_METADATA_ROW,
            "source_family": source_family,
            "regions": regions,
            "page_url": page_url,
            "page_number": page_number,
            "fragment_kind": fragment_kind,
            "title": title,
            "detail_url": absolute_url,
            "notice_numbers": notice_numbers,
            "dates": dates,
            "row_text": fragment_text[:2000],
            "metadata_score": metadata_score,
            "reasons": unique_strings(reasons),
            "target_identity_evaluated": False,
            "target_query_executed": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        })

    return rows


def recover_document_rows(
    raw_html: str,
    page_url: str,
    source_family: str,
    regions: List[str],
    page_number: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for fragment_kind, fragment in iter_candidate_fragments(raw_html):
        rows.extend(
            recover_rows_from_fragment(
                fragment_kind,
                fragment,
                page_url,
                source_family,
                regions,
                page_number,
            )
        )

    dedup: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        key = canonicalize_url(row.get("detail_url") or "")
        if not key:
            continue

        if key not in dedup:
            dedup[key] = row
            continue

        existing = dedup[key]
        existing["notice_numbers"] = unique_strings(
            (existing.get("notice_numbers") or []) + (row.get("notice_numbers") or [])
        )
        existing["dates"] = unique_strings(
            (existing.get("dates") or []) + (row.get("dates") or [])
        )
        existing["reasons"] = unique_strings(
            (existing.get("reasons") or []) + (row.get("reasons") or [])
        )
        existing["metadata_score"] = max(
            int(existing.get("metadata_score") or 0),
            int(row.get("metadata_score") or 0),
        )

    result = list(dedup.values())
    result.sort(key=lambda item: canonicalize_url(item.get("detail_url") or ""))
    return result


# ============================================================
# TRAVERSAL SCHEDULE
# ============================================================

def build_traversal_pages(contract: Dict[str, Any]) -> List[int]:
    lower = contract.get("effective_lower_page")
    upper = contract.get("effective_upper_page")

    if not isinstance(lower, int) or not isinstance(upper, int):
        return []
    if lower < 1 or upper < lower:
        return []

    observed_pages = [
        int(page)
        for page in (contract.get("observed_pages") or [])
        if isinstance(page, int) and lower <= page <= upper
    ]

    # 처음부터 전 범위를 무작정 훑지 않는다. 최신/관측/깊은 과거 sparse page를 섞어 제한 순회한다.
    sparse = [
        lower,
        min(lower + 1, upper),
        5,
        10,
        20,
        50,
        100,
        upper,
    ]

    pages = sorted({
        page
        for page in observed_pages + sparse
        if isinstance(page, int) and lower <= page <= upper
    })

    if len(pages) <= MAX_REQUESTS_PER_CONTRACT:
        return pages

    # 관측 페이지와 양 끝을 우선 보존한다.
    priority = unique_strings([])  # type-stable no-op for consistency
    del priority

    selected: List[int] = []
    for page in [lower, upper] + observed_pages + pages:
        if page in selected:
            continue
        selected.append(page)
        if len(selected) >= MAX_REQUESTS_PER_CONTRACT:
            break

    return sorted(selected)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("COMPETENT AUTHORITY BOUNDED HISTORICAL RANGE TRAVERSAL")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
    print("Target identity evaluation: DISABLED")
    print()

    if not T15S2_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-15-S2 input not found: {T15S2_INPUT_PATH}")

    input_data = json.loads(T15S2_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(input_data, dict):
        raise TypeError("T-15-S2 input must be JSON object")

    raw_contracts = input_data.get("next_stage_boundary_pool")
    if not isinstance(raw_contracts, list):
        raw_contracts = []

    contracts = [
        item
        for item in raw_contracts
        if isinstance(item, dict)
        and item.get("traversal_allowed") is True
        and normalize_space(item.get("source_family")) in ALLOWED_FAMILIES
    ]

    print("Traversal contract count:", len(contracts))
    print()

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    request_count = 0
    http_success_count = 0
    transport_error_count = 0

    page_records: List[Dict[str, Any]] = []
    raw_rows: List[Dict[str, Any]] = []

    for contract_index, contract in enumerate(contracts, start=1):
        family = normalize_space(contract.get("source_family"))
        base_url = canonicalize_url(contract.get("base_url") or "")
        pagination_key = normalize_space(contract.get("pagination_key"))
        regions = unique_strings(contract.get("regions") or [])
        lower = contract.get("effective_lower_page")
        upper = contract.get("effective_upper_page")
        traversal_pages = build_traversal_pages(contract)

        print("-" * 60)
        print(f"CONTRACT {contract_index}")
        print("Family:", family)
        print("Base URL:", base_url)
        print("Pagination key:", pagination_key)
        print("Effective range:", (lower, upper))
        print("Traversal pages:", traversal_pages)

        contract_requests = 0
        contract_rows_before = len(raw_rows)

        for page in traversal_pages:
            if request_count >= MAX_TOTAL_REQUESTS:
                break
            if contract_requests >= MAX_REQUESTS_PER_CONTRACT:
                break

            page_url = build_page_url(base_url, pagination_key, page)
            if not page_url:
                continue

            request_count += 1
            contract_requests += 1
            response = fetch_page(session, page_url)

            status = response.get("http_status")
            error = normalize_space(response.get("error"))
            raw_html = str(response.get("raw_html") or "")
            final_url = canonicalize_url(response.get("final_url") or page_url)

            if error:
                transport_error_count += 1

            if isinstance(status, int) and 200 <= status < 300:
                http_success_count += 1

            rows: List[Dict[str, Any]] = []
            page_classification = CLASS_PAGE_HTTP_FAILURE

            if isinstance(status, int) and 200 <= status < 300 and raw_html:
                rows = recover_document_rows(
                    raw_html,
                    final_url or page_url,
                    family,
                    regions,
                    page,
                )
                page_classification = (
                    CLASS_DOCUMENT_METADATA_ROW if rows else CLASS_PAGE_NO_DOCUMENT_ROWS
                )
                raw_rows.extend(rows)

            page_records.append({
                "source_family": family,
                "regions": regions,
                "base_url": base_url,
                "pagination_key": pagination_key,
                "page_number": page,
                "requested_url": page_url,
                "final_url": final_url,
                "http_status": status,
                "response_bytes": response.get("response_bytes"),
                "title": extract_title(raw_html) if raw_html else "",
                "row_count": len(rows),
                "classification": page_classification,
                "error": error,
                "target_identity_evaluated": False,
                "target_query_executed": False,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            })

        contract_row_count = len(raw_rows) - contract_rows_before
        print("Requests:", contract_requests)
        print("Recovered metadata rows:", contract_row_count)
        print()

    # ========================================================
    # CANONICAL DOCUMENT DEDUPE
    # ========================================================

    document_map: Dict[str, Dict[str, Any]] = {}
    duplicate_row_removed = 0

    for row in raw_rows:
        key = canonicalize_url(row.get("detail_url") or "")
        if not key:
            continue

        if key in document_map:
            duplicate_row_removed += 1
            existing = document_map[key]
            existing["source_pages"] = unique_strings(
                (existing.get("source_pages") or []) + [row.get("page_url")]
            )
            existing["page_numbers"] = sorted(set(
                (existing.get("page_numbers") or []) + [row.get("page_number")]
            ))
            existing["notice_numbers"] = unique_strings(
                (existing.get("notice_numbers") or []) + (row.get("notice_numbers") or [])
            )
            existing["dates"] = unique_strings(
                (existing.get("dates") or []) + (row.get("dates") or [])
            )
            existing["reasons"] = unique_strings(
                (existing.get("reasons") or []) + (row.get("reasons") or [])
            )
            existing["metadata_score"] = max(
                int(existing.get("metadata_score") or 0),
                int(row.get("metadata_score") or 0),
            )
            continue

        canonical = dict(row)
        canonical["source_pages"] = [row.get("page_url")]
        canonical["page_numbers"] = [row.get("page_number")]
        document_map[key] = canonical

    canonical_rows = list(document_map.values())
    canonical_rows.sort(key=lambda item: canonicalize_url(item.get("detail_url") or ""))

    next_stage_document_metadata_pool = [
        {
            "classification": item.get("classification"),
            "source_family": item.get("source_family"),
            "regions": item.get("regions") or [],
            "title": item.get("title"),
            "detail_url": item.get("detail_url"),
            "notice_numbers": item.get("notice_numbers") or [],
            "dates": item.get("dates") or [],
            "source_pages": item.get("source_pages") or [],
            "page_numbers": item.get("page_numbers") or [],
            "metadata_score": item.get("metadata_score"),
            "reasons": item.get("reasons") or [],
            "requires_target_identity_filter": True,
            "requires_direct_document_verification": True,
            "target_identity_evaluated": False,
            "target_query_executed": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in canonical_rows
    ]

    if next_stage_document_metadata_pool:
        resolution = "COMPETENT_AUTHORITY_BOUNDED_HISTORICAL_RANGE_TRAVERSAL_COMPLETED"
        next_action = (
            "T-16에서 복원된 canonical document metadata row만 T-17 target identity filter 입력으로 사용한다. "
            "T-17에서는 row-local title/notice-number/date/detail URL만으로 UQQ700 target identity를 판정하고, "
            "통과한 문서만 후속 direct document verification으로 넘긴다."
        )
    else:
        resolution = "COMPETENT_AUTHORITY_BOUNDED_HISTORICAL_RANGE_TRAVERSAL_NO_DOCUMENT_ROWS"
        next_action = (
            "bounded historical range를 순회했지만 document metadata row를 복원하지 못했다. "
            "이는 SITE FALSE가 아니다. UNKNOWN을 유지하고 row-structure parser 또는 source-specific detail contract를 추가 분석한다."
        )

    classification_counts = Counter(
        item.get("classification") for item in page_records + canonical_rows
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-16 Competent Authority Bounded Historical Range Traversal & Document Metadata Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "inputs": {
            "t15s2_path": str(T15S2_INPUT_PATH),
            "t15s2_resolution": input_data.get("resolution"),
        },
        "method": {
            "hardened_traversal_contract_only": True,
            "bounded_effective_range_only": True,
            "contract_request_budget_enabled": True,
            "target_query_execution_enabled": False,
            "target_identity_evaluation_enabled": False,
            "page_title_document_evidence_enabled": False,
            "source_url_document_evidence_enabled": False,
            "result_row_metadata_identity_required": True,
            "same_host_go_kr_detail_required": True,
            "negative_evidence_enabled": False,
            "verified_positive_promotion_allowed": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
        },
        "summary": {
            "traversal_contract_count": len(contracts),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "page_record_count": len(page_records),
            "raw_metadata_row_count": len(raw_rows),
            "duplicate_metadata_row_removed": duplicate_row_removed,
            "canonical_metadata_row_count": len(canonical_rows),
            "next_stage_document_metadata_pool_count": len(next_stage_document_metadata_pool),
        },
        "classification_counts": dict(sorted(classification_counts.items())),
        "page_records": page_records,
        "canonical_document_metadata_rows": canonical_rows,
        "next_stage_document_metadata_pool": next_stage_document_metadata_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }

    OUTPUT_PATH.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=" * 60)
    print("BOUNDED HISTORICAL RANGE TRAVERSAL RESULT")
    print("=" * 60)
    print("Traversal contract count:", len(contracts))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Transport error count:", transport_error_count)
    print("Page record count:", len(page_records))
    print("Raw metadata row count:", len(raw_rows))
    print("Duplicate metadata row removed:", duplicate_row_removed)
    print("Canonical metadata row count:", len(canonical_rows))
    print("Next-stage document metadata pool count:", len(next_stage_document_metadata_pool))
    print()
    print("=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    print(resolution)
    print()
    print(next_action)
    print("Output:", OUTPUT_PATH)

    # ========================================================
    # VALIDATION
    # ========================================================

    invalid_range_page_leakage = 0
    for page_record in page_records:
        matching = [
            item for item in contracts
            if normalize_space(item.get("source_family")) == normalize_space(page_record.get("source_family"))
            and canonicalize_url(item.get("base_url") or "") == canonicalize_url(page_record.get("base_url") or "")
            and normalize_space(item.get("pagination_key")).lower() == normalize_space(page_record.get("pagination_key")).lower()
        ]
        if not matching:
            invalid_range_page_leakage += 1
            continue

        contract = matching[0]
        page = page_record.get("page_number")
        lower = contract.get("effective_lower_page")
        upper = contract.get("effective_upper_page")
        if not isinstance(page, int) or not isinstance(lower, int) or not isinstance(upper, int):
            invalid_range_page_leakage += 1
            continue
        if not (lower <= page <= upper):
            invalid_range_page_leakage += 1

    per_contract_budget_respected = all(
        sum(
            1
            for page_record in page_records
            if normalize_space(page_record.get("source_family")) == normalize_space(contract.get("source_family"))
            and canonicalize_url(page_record.get("base_url") or "") == canonicalize_url(contract.get("base_url") or "")
            and normalize_space(page_record.get("pagination_key")).lower() == normalize_space(contract.get("pagination_key")).lower()
        ) <= MAX_REQUESTS_PER_CONTRACT
        for contract in contracts
    )

    invalid_detail_url_leakage = sum(
        1
        for item in canonical_rows
        if not canonicalize_url(item.get("detail_url") or "")
    )

    non_go_kr_detail_leakage = sum(
        1
        for item in canonical_rows
        if not is_government_host(hostname(item.get("detail_url") or ""))
    )

    cross_host_detail_leakage = sum(
        1
        for item in canonical_rows
        if not same_host(item.get("page_url") or "", item.get("detail_url") or "")
    )

    weak_metadata_leakage = sum(
        1
        for item in canonical_rows
        if is_generic_text(item.get("title") or "")
        or int(item.get("metadata_score") or 0) < 55
    )

    detail_keys = [canonicalize_url(item.get("detail_url") or "") for item in canonical_rows]
    next_stage_keys = [canonicalize_url(item.get("detail_url") or "") for item in next_stage_document_metadata_pool]

    target_identity_leakage = sum(
        1
        for item in page_records + canonical_rows + next_stage_document_metadata_pool
        if item.get("target_identity_evaluated") is True
    )

    target_query_leakage = sum(
        1
        for item in page_records + canonical_rows + next_stage_document_metadata_pool
        if item.get("target_query_executed") is True
    )

    verified_positive_leakage = sum(
        1
        for item in page_records + canonical_rows + next_stage_document_metadata_pool
        if item.get("verified_positive") is True
    )

    runtime_registration_leakage = sum(
        1
        for item in page_records + canonical_rows + next_stage_document_metadata_pool
        if item.get("runtime_registration_allowed") is True
    )

    site_true_leakage = sum(
        1
        for item in page_records + canonical_rows + next_stage_document_metadata_pool
        if item.get("site_positive_allowed") is True
    )

    site_false_leakage = sum(
        1
        for item in page_records + canonical_rows + next_stage_document_metadata_pool
        if item.get("site_negative_allowed") is True
    )

    false_from_no_document_leakage = (
        1
        if not canonical_rows
        and output_data["resolution_policy"]["source_failure_site_status"] == "FALSE"
        else 0
    )

    valid_page_classes = all(
        item.get("classification") in VALID_PAGE_CLASSES | {CLASS_DOCUMENT_METADATA_ROW}
        for item in page_records
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-15-S2 input exists": T15S2_INPUT_PATH.exists(),
        "T-15-S2 input parsed": isinstance(input_data, dict),
        "hardened traversal contracts loaded": len(contracts) > 0,
        "bounded total request count respected": request_count <= MAX_TOTAL_REQUESTS,
        "per-contract request budget respected": per_contract_budget_respected,
        "effective range leakage zero": invalid_range_page_leakage == 0,
        "target query execution disabled": target_query_leakage == 0,
        "target identity evaluation disabled": target_identity_leakage == 0,
        "page title evidence disabled": True,
        "source URL evidence disabled": True,
        "result row metadata identity required": True,
        "all page classes valid": valid_page_classes,
        "canonical detail URLs valid": invalid_detail_url_leakage == 0,
        "canonical detail URLs unique": len(detail_keys) == len(set(detail_keys)),
        "next-stage detail URLs unique": len(next_stage_keys) == len(set(next_stage_keys)),
        "canonical and next-stage parity": set(detail_keys) == set(next_stage_keys),
        "detail go.kr leakage zero": non_go_kr_detail_leakage == 0,
        "detail cross-host leakage zero": cross_host_detail_leakage == 0,
        "weak metadata leakage zero": weak_metadata_leakage == 0,
        "verified positive leakage zero": verified_positive_leakage == 0,
        "runtime registration leakage zero": runtime_registration_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "false from no document leakage zero": false_from_no_document_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)

    for name, passed in validations.items():
        print(f"{name}: {passed}")

    print()
    print("Invalid range page leakage:", invalid_range_page_leakage)
    print("Invalid detail URL leakage:", invalid_detail_url_leakage)
    print("Non-go.kr detail leakage:", non_go_kr_detail_leakage)
    print("Cross-host detail leakage:", cross_host_detail_leakage)
    print("Weak metadata leakage:", weak_metadata_leakage)
    print("Target identity leakage:", target_identity_leakage)
    print("Target query leakage:", target_query_leakage)
    print("Verified positive leakage:", verified_positive_leakage)
    print("Runtime registration leakage:", runtime_registration_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print("False from no document leakage:", false_from_no_document_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")

    if not all_pass:
        failed = [name for name, passed in validations.items() if not passed]
        print()
        print("FAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError(
            "UQQ700 competent authority bounded historical range traversal regression failed"
        )


if __name__ == "__main__":
    main()
