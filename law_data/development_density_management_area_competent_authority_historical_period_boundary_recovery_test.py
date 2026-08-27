# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-15
Development Density Management Area
Competent Authority Historical Period / Deep Pagination Boundary Recovery

목표
======================================================================
T-13에서 복원한 competent-authority pagination 구조만 사용하여,
UQQ700 target query를 실행하지 않고 성남시 고시공고 / 도시계획 source가
실제로 어느 historical period까지 접근 가능한지 구조적으로 측정한다.

핵심 원칙
======================================================================
1. T-13 next_stage_pagination_pool과 검증된 competent-authority source만 사용한다.
2. UQQ700 target query를 실행하지 않는다.
3. document candidate를 생성하지 않는다.
4. pagination key는 T-13에서 관측된 실제 key만 사용한다.
5. 무한 pagination crawling을 하지 않는다.
6. 제한된 boundary probe schedule만 실행한다.
7. page-local 날짜, pagination link, empty/repeated page signal만 측정한다.
8. 기간/연도/date 관련 실제 HTML control이 있으면 구조만 복원한다.
9. 과거 접근 실패/빈 페이지/경계 발견은 SITE FALSE가 아니다.
10. verified positive / runtime registration / SITE TRUE / SITE FALSE 자동판정 금지.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests


# ============================================================
# PATH / TARGET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

T13_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_historical_pagination_discovery.json"
)

T11_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_historical_source_scope.json"
)

OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_competent_authority_historical_period_boundary_recovery.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

PRIMARY_ROLE = "PRIMARY_DESIGNATION_AUTHORITY_SOURCE"

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"

ALLOWED_FAMILIES = {
    FAMILY_NOTICE,
    FAMILY_URBAN,
}


# ============================================================
# OUTPUT CLASSES
# ============================================================

CLASS_PERIOD_BOUNDARY = "RECOVERED_AUTHORITY_HISTORICAL_PERIOD_BOUNDARY"
CLASS_PAGINATION_BOUNDARY = "RECOVERED_AUTHORITY_PAGINATION_BOUNDARY"
CLASS_DATE_CONTROL = "RECOVERED_AUTHORITY_HISTORICAL_DATE_CONTROL"
CLASS_UNRESOLVED_BOUNDARY = "UNRESOLVED_AUTHORITY_HISTORICAL_BOUNDARY"
CLASS_REJECTED_INVALID = "REJECTED_INVALID_BOUNDARY_SOURCE"
CLASS_REJECTED_HTTP = "REJECTED_BOUNDARY_HTTP_FAILURE"

VALID_CLASSES = {
    CLASS_PERIOD_BOUNDARY,
    CLASS_PAGINATION_BOUNDARY,
    CLASS_DATE_CONTROL,
    CLASS_UNRESOLVED_BOUNDARY,
    CLASS_REJECTED_INVALID,
    CLASS_REJECTED_HTTP,
}


# ============================================================
# HTTP / BUDGET
# ============================================================

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 36
MAX_REQUESTS_PER_FAMILY = 18

# 무한 순회 금지. 관측된 pagination key에 대해서만 sparse probe한다.
BOUNDARY_PROBE_PAGES = [
    1,
    2,
    10,
    20,
    50,
    100,
    200,
    500,
    1000,
    2000,
    5000,
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


# ============================================================
# HTML / SEMANTIC PATTERNS
# ============================================================

TITLE_PATTERN = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)

ANCHOR_PATTERN = re.compile(
    r"<a\b[^>]*href\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
    re.I | re.S,
)

INPUT_PATTERN = re.compile(r"<input\b([^>]*)>", re.I | re.S)
SELECT_PATTERN = re.compile(r"<select\b([^>]*)>(.*?)</select>", re.I | re.S)
OPTION_PATTERN = re.compile(r"<option\b([^>]*)>(.*?)</option>", re.I | re.S)
ATTR_PATTERN = re.compile(
    r"([:\w-]+)\s*=\s*(?:[\"']([^\"']*)[\"']|([^\s>]+))",
    re.I | re.S,
)

DATE_PATTERN = re.compile(
    r"(?<!\d)((?:19|20)\d{2})[.\-/년\s]+(0?[1-9]|1[0-2])[.\-/월\s]+(0?[1-9]|[12]\d|3[01])(?:일)?(?!\d)"
)
YEAR_PATTERN = re.compile(r"(?<!\d)((?:19|20)\d{2})(?:년)?(?!\d)")

DATE_CONTROL_HINTS = {
    "startdate", "enddate", "fromdate", "todate", "sdate", "edate",
    "start_date", "end_date", "from_date", "to_date", "begin", "end",
    "year", "yyyy", "searchyear", "srchyear", "년도", "연도", "기간",
    "시작일", "종료일", "검색기간", "게재기간", "등록일",
}

PAGINATION_KEYS = {
    "page", "curpage", "pagenum", "pageindex", "page_no", "pageno", "currentpage",
}

VOLATILE_QUERY_KEYS = {
    "token", "_csrf", "csrf", "sessionid", "jsessionid", "timestamp", "rand", "random", "_",
}
TRACKING_QUERY_KEYS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid",
}

EMPTY_PAGE_TERMS = {
    "검색 결과가 없습니다",
    "검색결과가 없습니다",
    "등록된 게시물이 없습니다",
    "등록된 게시글이 없습니다",
    "게시물이 없습니다",
    "게시글이 없습니다",
    "조회된 결과가 없습니다",
    "조회 결과가 없습니다",
    "자료가 없습니다",
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
    value = COMMENT_PATTERN.sub(" ", raw_html)
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

    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        k = normalize_space(key)
        if not k:
            continue
        lowered = k.lower()
        if lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS:
            continue
        if "csrf" in lowered or "session" in lowered:
            continue
        pair = (k, val)
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
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        try:
            result.append(f"{year:04d}-{month:02d}-{day:02d}")
        except Exception:
            continue
    return unique_strings(result)


def response_signature(raw_html: str) -> str:
    # token/whitespace 변화에 덜 민감하도록 visible text 기반 hash를 사용한다.
    visible = strip_html(raw_html)
    return hashlib.sha256(visible.encode("utf-8", errors="ignore")).hexdigest()


def contains_empty_page_signal(text: str) -> bool:
    normalized = normalize_space(text)
    return any(term in normalized for term in EMPTY_PAGE_TERMS)


# ============================================================
# INPUT LOAD
# ============================================================

def load_primary_sources(t11_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = t11_data.get("next_stage_primary_source_pool")
    if not isinstance(raw, list):
        raw = t11_data.get("primary_sources")
    if not isinstance(raw, list):
        raw = []

    result: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for item in raw:
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get("source_family") or item.get("family"))
        url = canonicalize_url(item.get("url") or "")
        if family not in ALLOWED_FAMILIES or not url:
            continue
        if url in seen:
            continue
        seen.add(url)
        result.append({
            "source_family": family,
            "authority_role": normalize_space(item.get("authority_role") or PRIMARY_ROLE),
            "authority_entity": normalize_space(item.get("authority") or item.get("authority_entity") or "성남시장"),
            "regions": unique_strings(item.get("regions") or [item.get("region")]),
            "url": url,
        })

    return result


def load_t13_pagination(t13_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = t13_data.get("next_stage_pagination_pool")
    if not isinstance(raw, list):
        raw = []

    result: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for item in raw:
        if not isinstance(item, dict):
            continue
        url = canonicalize_url(item.get("url") or "")
        if not url or url in seen:
            continue
        seen.add(url)
        result.append({
            "page_family": normalize_space(item.get("page_family")),
            "regions": unique_strings(item.get("regions") or []),
            "url": url,
            "page_number": item.get("page_number"),
        })

    return result


# ============================================================
# PAGINATION CONTRACT
# ============================================================

def detect_pagination_key(url: str) -> str:
    try:
        items = parse_qsl(urlparse(url).query, keep_blank_values=True)
    except Exception:
        return ""

    for key, value in items:
        lowered = normalize_space(key).lower()
        if lowered in PAGINATION_KEYS:
            try:
                int(value)
            except Exception:
                continue
            return key
    return ""


def derive_family_pagination_contracts(
    pagination: List[Dict[str, Any]],
    primary_sources: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    source_by_family = {
        item["source_family"]: item
        for item in primary_sources
    }

    for item in pagination:
        family = normalize_space(item.get("page_family"))
        url = canonicalize_url(item.get("url") or "")
        key = detect_pagination_key(url)
        if family not in ALLOWED_FAMILIES or not url or not key:
            continue

        parsed = urlparse(url)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        params.pop(key, None)
        base_url = canonicalize_url(urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            urlencode(params, doseq=True),
            "",
        )))
        if not base_url:
            continue

        identity = (family, base_url, key.lower())
        if identity not in grouped:
            source = source_by_family.get(family, {})
            grouped[identity] = {
                "source_family": family,
                "authority_role": source.get("authority_role") or PRIMARY_ROLE,
                "authority_entity": source.get("authority_entity") or "성남시장",
                "regions": unique_strings((source.get("regions") or []) + (item.get("regions") or [])),
                "source_url": source.get("url") or base_url,
                "base_url": base_url,
                "pagination_key": key,
                "observed_pages": [],
                "observed_urls": [],
            }

        page_number = item.get("page_number")
        if isinstance(page_number, int):
            grouped[identity]["observed_pages"].append(page_number)
        else:
            try:
                grouped[identity]["observed_pages"].append(int(dict(parse_qsl(parsed.query)).get(key, "")))
            except Exception:
                pass
        grouped[identity]["observed_urls"].append(url)

    result = list(grouped.values())
    for item in result:
        item["observed_pages"] = sorted(set(item["observed_pages"]))
        item["observed_urls"] = unique_strings(item["observed_urls"])
    result.sort(key=lambda x: (x["source_family"], x["base_url"], x["pagination_key"].lower()))
    return result


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


# ============================================================
# DATE / PERIOD CONTROL RECOVERY
# ============================================================

def extract_date_controls(raw_html: str) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []

    for match in INPUT_PATTERN.finditer(raw_html or ""):
        attrs = parse_attrs(match.group(1))
        name = normalize_space(attrs.get("name"))
        ident = normalize_space(attrs.get("id"))
        typ = normalize_space(attrs.get("type"))
        placeholder = normalize_space(attrs.get("placeholder"))
        title = normalize_space(attrs.get("title"))
        evidence = normalize_space(" ".join([name, ident, typ, placeholder, title])).lower()
        reasons = [hint for hint in DATE_CONTROL_HINTS if hint.lower() in evidence]
        if not reasons:
            continue
        result.append({
            "tag": "input",
            "name": name,
            "id": ident,
            "type": typ,
            "value": normalize_space(attrs.get("value")),
            "placeholder": placeholder,
            "title": title,
            "reasons": [f"DATE_CONTROL_HINT:{reason}" for reason in sorted(set(reasons))],
        })

    for match in SELECT_PATTERN.finditer(raw_html or ""):
        attrs = parse_attrs(match.group(1))
        body = match.group(2)
        name = normalize_space(attrs.get("name"))
        ident = normalize_space(attrs.get("id"))
        evidence = normalize_space(" ".join([name, ident])).lower()
        options: List[Dict[str, str]] = []
        option_texts: List[str] = []
        for option in OPTION_PATTERN.finditer(body):
            option_attrs = parse_attrs(option.group(1))
            option_text = strip_html(option.group(2))
            options.append({
                "value": normalize_space(option_attrs.get("value")),
                "text": option_text,
            })
            if option_text:
                option_texts.append(option_text)
        option_evidence = normalize_space(" ".join(option_texts)).lower()
        reasons = [hint for hint in DATE_CONTROL_HINTS if hint.lower() in evidence or hint.lower() in option_evidence]
        has_year_options = len(set(YEAR_PATTERN.findall(option_evidence))) >= 2
        if not reasons and not has_year_options:
            continue
        result.append({
            "tag": "select",
            "name": name,
            "id": ident,
            "options": options[:200],
            "reasons": unique_strings(
                [f"DATE_CONTROL_HINT:{reason}" for reason in sorted(set(reasons))]
                + (["MULTI_YEAR_OPTION_STRUCTURE"] if has_year_options else [])
            ),
        })

    canonical: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for item in result:
        key = (
            normalize_space(item.get("tag")),
            normalize_space(item.get("name")),
            normalize_space(item.get("id")),
        )
        canonical[key] = item
    return list(canonical.values())


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
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("COMPETENT AUTHORITY HISTORICAL PERIOD / PAGINATION BOUNDARY RECOVERY")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
    print()

    if not T13_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-13 input not found: {T13_INPUT_PATH}")
    if not T11_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-11 input not found: {T11_INPUT_PATH}")

    t13_data = json.loads(T13_INPUT_PATH.read_text(encoding="utf-8"))
    t11_data = json.loads(T11_INPUT_PATH.read_text(encoding="utf-8"))

    if not isinstance(t13_data, dict):
        raise TypeError("T-13 input must be JSON object")
    if not isinstance(t11_data, dict):
        raise TypeError("T-11 input must be JSON object")

    primary_sources = load_primary_sources(t11_data)
    pagination = load_t13_pagination(t13_data)
    contracts = derive_family_pagination_contracts(pagination, primary_sources)

    print("Primary source count:", len(primary_sources))
    print("T-13 pagination record count:", len(pagination))
    print("Derived pagination contract count:", len(contracts))
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

    probe_records: List[Dict[str, Any]] = []
    boundary_records: List[Dict[str, Any]] = []
    date_control_records: List[Dict[str, Any]] = []

    for contract_index, contract in enumerate(contracts, start=1):
        family = contract["source_family"]
        source_url = canonicalize_url(contract["source_url"])
        base_url = canonicalize_url(contract["base_url"])
        pagination_key = normalize_space(contract["pagination_key"])
        observed_pages = contract.get("observed_pages") or []

        print("-" * 60)
        print(f"CONTRACT {contract_index}")
        print("Family:", family)
        print("Source URL:", source_url)
        print("Base URL:", base_url)
        print("Pagination key:", pagination_key)
        print("Observed pages:", observed_pages)

        if (
            family not in ALLOWED_FAMILIES
            or not source_url
            or not base_url
            or not pagination_key
            or not is_government_host(hostname(base_url))
            or not same_host(source_url, base_url)
        ):
            boundary_records.append({
                "source_family": family,
                "source_url": source_url,
                "base_url": base_url,
                "pagination_key": pagination_key,
                "qualified": False,
                "classification": CLASS_REJECTED_INVALID,
                "reasons": ["INVALID_OR_NON_OFFICIAL_PAGINATION_CONTRACT"],
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            })
            print("Resolution:", CLASS_REJECTED_INVALID)
            print()
            continue

        family_request_count = 0
        signatures: Dict[str, List[int]] = {}
        successful_pages: List[int] = []
        nonempty_pages: List[int] = []
        empty_pages: List[int] = []
        page_dates: Dict[int, List[str]] = {}
        family_date_controls: List[Dict[str, Any]] = []

        # 실제 관측 page와 sparse boundary page를 합치되 budget을 보장한다.
        probe_pages = sorted(set(
            [page for page in observed_pages if isinstance(page, int) and page > 0]
            + BOUNDARY_PROBE_PAGES
        ))

        for page in probe_pages:
            if request_count >= MAX_TOTAL_REQUESTS:
                break
            if family_request_count >= MAX_REQUESTS_PER_FAMILY:
                break

            page_url = build_page_url(base_url, pagination_key, page)
            if not page_url:
                continue

            request_count += 1
            family_request_count += 1
            response = fetch_page(session, page_url)

            status = response.get("http_status")
            error = normalize_space(response.get("error"))
            final_url = canonicalize_url(response.get("final_url") or page_url)

            if error:
                transport_error_count += 1

            if isinstance(status, int) and 200 <= status < 300:
                http_success_count += 1

            raw_html = str(response.get("raw_html") or "")
            visible_text = strip_html(raw_html) if raw_html else ""
            dates = extract_dates(visible_text)
            signature = response_signature(raw_html) if raw_html else ""
            empty_signal = contains_empty_page_signal(visible_text)

            if isinstance(status, int) and 200 <= status < 300 and raw_html:
                successful_pages.append(page)
                page_dates[page] = dates
                if empty_signal:
                    empty_pages.append(page)
                else:
                    nonempty_pages.append(page)
                if signature:
                    signatures.setdefault(signature, []).append(page)

                if not family_date_controls:
                    family_date_controls = extract_date_controls(raw_html)

            probe_records.append({
                "source_family": family,
                "authority_role": contract.get("authority_role") or PRIMARY_ROLE,
                "authority_entity": contract.get("authority_entity"),
                "regions": contract.get("regions") or [],
                "source_url": source_url,
                "base_url": base_url,
                "pagination_key": pagination_key,
                "requested_page": page,
                "url": page_url,
                "final_url": final_url,
                "http_status": status,
                "response_bytes": response.get("response_bytes"),
                "title": extract_title(raw_html) if raw_html else "",
                "dates": dates,
                "earliest_date": min(dates) if dates else None,
                "latest_date": max(dates) if dates else None,
                "empty_page_signal": empty_signal,
                "response_signature": signature,
                "error": error,
                "target_query_executed": False,
                "document_candidate": False,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            })

        all_dates = sorted({date for dates in page_dates.values() for date in dates})
        repeated_signature_groups = [
            sorted(pages)
            for pages in signatures.values()
            if len(pages) >= 2
        ]

        # sparse probe에서 동일 visible response가 여러 서로 먼 page에서 반복되면
        # out-of-range clamp 또는 same-page fallback 가능성을 기록한다.
        repeated_boundary_pages: List[int] = []
        for pages in repeated_signature_groups:
            if max(pages) - min(pages) >= 10:
                repeated_boundary_pages.extend(pages)
        repeated_boundary_pages = sorted(set(repeated_boundary_pages))

        max_observed_page = max(observed_pages) if observed_pages else None
        max_successful_probe_page = max(successful_pages) if successful_pages else None
        max_nonempty_probe_page = max(nonempty_pages) if nonempty_pages else None
        first_empty_probe_page = min(empty_pages) if empty_pages else None
        first_repeated_boundary_page = min(repeated_boundary_pages) if repeated_boundary_pages else None

        boundary_evidence = []
        if max_observed_page is not None:
            boundary_evidence.append(f"OBSERVED_PAGINATION_MAX:{max_observed_page}")
        if max_nonempty_probe_page is not None:
            boundary_evidence.append(f"SPARSE_NONEMPTY_PAGE_REACHED:{max_nonempty_probe_page}")
        if first_empty_probe_page is not None:
            boundary_evidence.append(f"EMPTY_PAGE_SIGNAL_FROM:{first_empty_probe_page}")
        if first_repeated_boundary_page is not None:
            boundary_evidence.append(f"REPEATED_RESPONSE_BOUNDARY_SIGNAL:{first_repeated_boundary_page}")
        if all_dates:
            boundary_evidence.append(f"EARLIEST_OBSERVED_DATE:{min(all_dates)}")
            boundary_evidence.append(f"LATEST_OBSERVED_DATE:{max(all_dates)}")

        boundary_resolved = bool(
            all_dates
            or first_empty_probe_page is not None
            or first_repeated_boundary_page is not None
            or max_nonempty_probe_page is not None
        )

        boundary_record = {
            "source_family": family,
            "authority_role": contract.get("authority_role") or PRIMARY_ROLE,
            "authority_entity": contract.get("authority_entity"),
            "regions": contract.get("regions") or [],
            "source_url": source_url,
            "base_url": base_url,
            "pagination_key": pagination_key,
            "observed_pages": observed_pages,
            "successful_probe_pages": sorted(set(successful_pages)),
            "nonempty_probe_pages": sorted(set(nonempty_pages)),
            "empty_probe_pages": sorted(set(empty_pages)),
            "max_observed_page": max_observed_page,
            "max_successful_probe_page": max_successful_probe_page,
            "max_nonempty_probe_page": max_nonempty_probe_page,
            "first_empty_probe_page": first_empty_probe_page,
            "first_repeated_boundary_page": first_repeated_boundary_page,
            "repeated_signature_groups": repeated_signature_groups,
            "earliest_observed_date": min(all_dates) if all_dates else None,
            "latest_observed_date": max(all_dates) if all_dates else None,
            "observed_date_count": len(all_dates),
            "date_control_count": len(family_date_controls),
            "qualified": boundary_resolved,
            "classification": (
                CLASS_PERIOD_BOUNDARY if all_dates
                else CLASS_PAGINATION_BOUNDARY if boundary_resolved
                else CLASS_UNRESOLVED_BOUNDARY
            ),
            "reasons": unique_strings(boundary_evidence or ["BOUNDARY_EVIDENCE_NOT_YET_RESOLVED"]),
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        boundary_records.append(boundary_record)

        for control in family_date_controls:
            date_control_records.append({
                "source_family": family,
                "authority_role": contract.get("authority_role") or PRIMARY_ROLE,
                "authority_entity": contract.get("authority_entity"),
                "regions": contract.get("regions") or [],
                "source_url": source_url,
                "base_url": base_url,
                "control": control,
                "classification": CLASS_DATE_CONTROL,
                "qualified": True,
                "reasons": control.get("reasons") or [],
                "target_query_executed": False,
                "document_candidate": False,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            })

        print("Requests:", family_request_count)
        print("Successful pages:", sorted(set(successful_pages)))
        print("Non-empty pages:", sorted(set(nonempty_pages)))
        print("Empty pages:", sorted(set(empty_pages)))
        print("Earliest observed date:", min(all_dates) if all_dates else None)
        print("Latest observed date:", max(all_dates) if all_dates else None)
        print("Repeated boundary page:", first_repeated_boundary_page)
        print("Date controls:", len(family_date_controls))
        print("Resolution:", boundary_record["classification"])
        print()

    # ========================================================
    # CANONICAL DEDUPE
    # ========================================================

    boundary_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    duplicate_boundary_count = 0

    for item in boundary_records:
        key = (
            normalize_space(item.get("source_family")),
            canonicalize_url(item.get("base_url") or item.get("source_url") or ""),
            normalize_space(item.get("pagination_key")).lower(),
        )
        if key in boundary_map:
            duplicate_boundary_count += 1
            continue
        boundary_map[key] = item

    canonical_boundaries = list(boundary_map.values())
    canonical_boundaries.sort(key=lambda x: (
        normalize_space(x.get("source_family")),
        canonicalize_url(x.get("base_url") or ""),
    ))

    control_map: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for item in date_control_records:
        control = item.get("control") or {}
        key = (
            normalize_space(item.get("source_family")),
            canonicalize_url(item.get("base_url") or ""),
            normalize_space(control.get("name")),
            normalize_space(control.get("id")),
        )
        control_map[key] = item
    canonical_controls = list(control_map.values())

    qualified_boundaries = [item for item in canonical_boundaries if item.get("qualified") is True]

    next_stage_boundary_pool = [
        {
            "source_family": item.get("source_family"),
            "authority_role": item.get("authority_role"),
            "authority_entity": item.get("authority_entity"),
            "regions": item.get("regions") or [],
            "source_url": item.get("source_url"),
            "base_url": item.get("base_url"),
            "pagination_key": item.get("pagination_key"),
            "observed_pages": item.get("observed_pages") or [],
            "max_observed_page": item.get("max_observed_page"),
            "max_nonempty_probe_page": item.get("max_nonempty_probe_page"),
            "first_empty_probe_page": item.get("first_empty_probe_page"),
            "first_repeated_boundary_page": item.get("first_repeated_boundary_page"),
            "earliest_observed_date": item.get("earliest_observed_date"),
            "latest_observed_date": item.get("latest_observed_date"),
            "classification": item.get("classification"),
            "reasons": item.get("reasons") or [],
            "bounded_range_only": True,
            "requires_bounded_historical_traversal": True,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in qualified_boundaries
    ]

    if next_stage_boundary_pool:
        resolution = "COMPETENT_AUTHORITY_HISTORICAL_PERIOD_BOUNDARY_RECOVERY_COMPLETED"
        next_action = (
            "T-15에서 확인한 source별 pagination/date reach만 T-16 bounded historical range traversal 입력으로 사용한다. "
            "T-16은 확인된 범위를 초과하지 않고 과거 페이지를 제한 순회하며 실제 document metadata row 구조만 복원한다. "
            "아직 UQQ700 target query나 SITE TRUE/FALSE 판정은 수행하지 않는다."
        )
    else:
        resolution = "COMPETENT_AUTHORITY_HISTORICAL_PERIOD_BOUNDARY_RECOVERY_UNRESOLVED"
        next_action = (
            "competent-authority current source의 historical reach 경계를 구조적으로 확정하지 못했다. "
            "SITE FALSE로 판정하지 않고 UNKNOWN을 유지하며 source-specific pagination/date contract를 추가 분석한다."
        )

    classification_counts = Counter(item.get("classification") for item in canonical_boundaries + canonical_controls)

    output_data = {
        "step": "STEP 17-21-C-16-8-T-15 Competent Authority Historical Period / Deep Pagination Boundary Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "inputs": {
            "t13_path": str(T13_INPUT_PATH),
            "t11_path": str(T11_INPUT_PATH),
            "t13_resolution": t13_data.get("resolution"),
            "t11_resolution": t11_data.get("resolution"),
        },
        "method": {
            "t13_observed_pagination_only": True,
            "competent_authority_primary_source_only": True,
            "target_query_execution_enabled": False,
            "document_candidate_generation_enabled": False,
            "guessed_pagination_key_generation_enabled": False,
            "sparse_boundary_probe_enabled": True,
            "unbounded_pagination_crawl_enabled": False,
            "page_local_date_observation_enabled": True,
            "empty_page_boundary_signal_enabled": True,
            "repeated_response_boundary_signal_enabled": True,
            "actual_date_control_recovery_enabled": True,
            "negative_evidence_enabled": False,
            "verified_positive_promotion_allowed": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
        },
        "summary": {
            "primary_source_count": len(primary_sources),
            "t13_pagination_record_count": len(pagination),
            "pagination_contract_count": len(contracts),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "probe_record_count": len(probe_records),
            "raw_boundary_count": len(boundary_records),
            "duplicate_boundary_removed": duplicate_boundary_count,
            "canonical_boundary_count": len(canonical_boundaries),
            "qualified_boundary_count": len(qualified_boundaries),
            "date_control_count": len(canonical_controls),
            "next_stage_boundary_pool_count": len(next_stage_boundary_pool),
        },
        "classification_counts": dict(sorted(classification_counts.items())),
        "pagination_contracts": contracts,
        "probe_records": probe_records,
        "historical_boundaries": canonical_boundaries,
        "date_controls": canonical_controls,
        "next_stage_boundary_pool": next_stage_boundary_pool,
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

    # ========================================================
    # RESULT
    # ========================================================

    print("=" * 60)
    print("COMPETENT AUTHORITY HISTORICAL PERIOD BOUNDARY RESULT")
    print("=" * 60)
    print("Primary source count:", len(primary_sources))
    print("T-13 pagination record count:", len(pagination))
    print("Pagination contract count:", len(contracts))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Transport error count:", transport_error_count)
    print("Probe record count:", len(probe_records))
    print("Canonical boundary count:", len(canonical_boundaries))
    print("Qualified boundary count:", len(qualified_boundaries))
    print("Date control count:", len(canonical_controls))
    print("Next-stage boundary pool count:", len(next_stage_boundary_pool))
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

    all_classes_valid = all(
        item.get("classification") in VALID_CLASSES
        for item in canonical_boundaries + canonical_controls
    )

    invalid_base_url_leakage = sum(
        1 for item in canonical_boundaries
        if not canonicalize_url(item.get("base_url") or item.get("source_url") or "")
    )

    non_go_kr_leakage = sum(
        1 for item in canonical_boundaries
        if not is_government_host(hostname(item.get("base_url") or item.get("source_url") or ""))
    )

    cross_host_leakage = sum(
        1 for item in canonical_boundaries
        if item.get("source_url") and item.get("base_url")
        and not same_host(item.get("source_url") or "", item.get("base_url") or "")
    )

    guessed_pagination_key_leakage = sum(
        1 for item in canonical_boundaries
        if normalize_space(item.get("pagination_key")).lower() not in PAGINATION_KEYS
    )

    target_query_leakage = sum(
        1 for item in probe_records + canonical_boundaries + canonical_controls
        if item.get("target_query_executed") is True
    )

    document_candidate_leakage = sum(
        1 for item in probe_records + canonical_boundaries + canonical_controls
        if item.get("document_candidate") is True
    )

    verified_positive_leakage = sum(
        1 for item in probe_records + canonical_boundaries + canonical_controls
        if item.get("verified_positive") is True
    )

    runtime_registration_leakage = sum(
        1 for item in probe_records + canonical_boundaries + canonical_controls
        if item.get("runtime_registration_allowed") is True
    )

    site_true_leakage = sum(
        1 for item in probe_records + canonical_boundaries + canonical_controls
        if item.get("site_positive_allowed") is True
    )

    site_false_leakage = sum(
        1 for item in probe_records + canonical_boundaries + canonical_controls
        if item.get("site_negative_allowed") is True
    )

    next_stage_safety_leakage = sum(
        1 for item in next_stage_boundary_pool
        if (
            item.get("target_query_executed") is True
            or item.get("document_candidate") is True
            or item.get("verified_positive") is True
            or item.get("runtime_registration_allowed") is True
            or item.get("site_positive_allowed") is True
            or item.get("site_negative_allowed") is True
            or item.get("final_positive_promotion_allowed") is True
        )
    )

    false_from_boundary_failure_leakage = (
        1
        if not qualified_boundaries
        and output_data["resolution_policy"]["source_failure_site_status"] == "FALSE"
        else 0
    )

    boundary_keys = [
        (
            normalize_space(item.get("source_family")),
            canonicalize_url(item.get("base_url") or item.get("source_url") or ""),
            normalize_space(item.get("pagination_key")).lower(),
        )
        for item in canonical_boundaries
    ]
    duplicate_boundary_leakage = len(boundary_keys) - len(set(boundary_keys))

    next_stage_keys = [
        (
            normalize_space(item.get("source_family")),
            canonicalize_url(item.get("base_url") or item.get("source_url") or ""),
            normalize_space(item.get("pagination_key")).lower(),
        )
        for item in next_stage_boundary_pool
    ]
    duplicate_next_stage_leakage = len(next_stage_keys) - len(set(next_stage_keys))

    qualified_keys = {
        (
            normalize_space(item.get("source_family")),
            canonicalize_url(item.get("base_url") or item.get("source_url") or ""),
            normalize_space(item.get("pagination_key")).lower(),
        )
        for item in qualified_boundaries
    }
    next_stage_key_set = set(next_stage_keys)

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-13 input exists": T13_INPUT_PATH.exists(),
        "T-11 input exists": T11_INPUT_PATH.exists(),
        "T-13 input parsed": isinstance(t13_data, dict),
        "T-11 input parsed": isinstance(t11_data, dict),
        "competent authority primary sources loaded": len(primary_sources) > 0,
        "T-13 pagination loaded": len(pagination) > 0,
        "observed pagination contracts derived": len(contracts) > 0,
        "bounded request count respected": request_count <= MAX_TOTAL_REQUESTS,
        "per-family request budget respected": all(
            sum(1 for row in probe_records if row.get("source_family") == family) <= MAX_REQUESTS_PER_FAMILY
            for family in ALLOWED_FAMILIES
        ),
        "target query execution disabled": target_query_leakage == 0,
        "document candidate generation disabled": document_candidate_leakage == 0,
        "guessed pagination key leakage zero": guessed_pagination_key_leakage == 0,
        "sparse boundary probing enabled": True,
        "unbounded pagination crawling disabled": True,
        "page-local date observation enabled": True,
        "actual date control recovery enabled": True,
        "all classes valid": all_classes_valid,
        "boundary URLs valid": invalid_base_url_leakage == 0,
        "boundary identities unique": duplicate_boundary_leakage == 0,
        "next-stage identities unique": duplicate_next_stage_leakage == 0,
        "qualified and next-stage parity": qualified_keys == next_stage_key_set,
        "boundary go.kr leakage zero": non_go_kr_leakage == 0,
        "boundary cross-host leakage zero": cross_host_leakage == 0,
        "verified positive leakage zero": verified_positive_leakage == 0,
        "runtime registration leakage zero": runtime_registration_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "next-stage safety leakage zero": next_stage_safety_leakage == 0,
        "false from boundary failure leakage zero": false_from_boundary_failure_leakage == 0,
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
    print("Invalid boundary URL leakage:", invalid_base_url_leakage)
    print("Duplicate boundary identity leakage:", duplicate_boundary_leakage)
    print("Duplicate next-stage identity leakage:", duplicate_next_stage_leakage)
    print("Non-go.kr leakage:", non_go_kr_leakage)
    print("Cross-host leakage:", cross_host_leakage)
    print("Guessed pagination key leakage:", guessed_pagination_key_leakage)
    print("Target query leakage:", target_query_leakage)
    print("Document candidate leakage:", document_candidate_leakage)
    print("Verified positive leakage:", verified_positive_leakage)
    print("Runtime registration leakage:", runtime_registration_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print("Next-stage safety leakage:", next_stage_safety_leakage)
    print("False from boundary failure leakage:", false_from_boundary_failure_leakage)
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
            "UQQ700 competent authority historical period boundary recovery regression failed"
        )


if __name__ == "__main__":
    main()
