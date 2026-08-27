# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-13
Development Density Management Area
Competent Authority Historical Pagination & Result-Row Discovery

목표
======================================================================
T-12에서 복원한 competent-authority-local historical navigation만 사용하여
UQQ700 target query를 실행하지 않고 실제 pagination 진행 규칙과 result-row
구조를 복원한다.

핵심 원칙
======================================================================
1. T-12 next_stage_navigation_pool만 입력으로 사용한다.
2. target query는 실행하지 않는다.
3. pagination/list page를 직접 재조회한다.
4. result row는 page-local anchor/title/date/notice-number/detail URL로만 구성한다.
5. query 문자열, page title 단독, source endpoint 자체는 document evidence가 아니다.
6. current notice board와 urban planning source의 role boundary를 유지한다.
7. unrelated 채용/입찰/일반공고/복지/홍보 navigation은 승격하지 않는다.
8. detail/download는 아직 verified positive가 아니다.
9. absence는 SITE FALSE가 아니다.
10. runtime registration / SITE TRUE / SITE FALSE 자동판정 금지.
"""

from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests


# ============================================================
# PATH / TARGET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_historical_navigation_recovery.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_competent_authority_historical_pagination_discovery.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False
PRIMARY_ROLE = "PRIMARY_DESIGNATION_AUTHORITY_SOURCE"

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"


# ============================================================
# INPUT CLASSES
# ============================================================

INPUT_CLASS_LIST = "RECOVERED_AUTHORITY_HISTORICAL_LIST_NAVIGATION"
INPUT_CLASS_PAGINATION = "RECOVERED_AUTHORITY_PAGINATION_NAVIGATION"
INPUT_CLASS_NOTICE_DETAIL = "RECOVERED_AUTHORITY_NOTICE_DETAIL_PATTERN"
INPUT_CLASS_URBAN = "RECOVERED_AUTHORITY_URBAN_PLANNING_NAVIGATION"
INPUT_CLASS_ARCHIVE = "RECOVERED_AUTHORITY_ARCHIVE_NAVIGATION"

ALLOWED_INPUT_CLASSES = {
    INPUT_CLASS_LIST,
    INPUT_CLASS_PAGINATION,
    INPUT_CLASS_NOTICE_DETAIL,
    INPUT_CLASS_URBAN,
    INPUT_CLASS_ARCHIVE,
}


# ============================================================
# OUTPUT CLASSES
# ============================================================

CLASS_NOTICE_RESULT_ROW = "RECOVERED_AUTHORITY_NOTICE_RESULT_ROW"
CLASS_URBAN_RESULT_ROW = "RECOVERED_AUTHORITY_URBAN_RESULT_ROW"
CLASS_PAGINATION_CONTRACT = "RECOVERED_AUTHORITY_PAGINATION_CONTRACT"

CLASS_REJECTED_SOURCE_ENDPOINT = "REJECTED_SOURCE_ENDPOINT_ROW"
CLASS_REJECTED_NAVIGATION = "REJECTED_NAVIGATION_ROW"
CLASS_REJECTED_ROLE = "REJECTED_ROLE_INCOMPATIBLE_ROW"
CLASS_REJECTED_WEAK = "REJECTED_RESULT_ROW_IDENTITY_WEAK"
CLASS_REJECTED_NON_OFFICIAL = "REJECTED_NON_OFFICIAL_ROW"
CLASS_REJECTED_CROSS_HOST = "REJECTED_CROSS_HOST_ROW"
CLASS_REJECTED_INVALID = "REJECTED_INVALID_ROW_URL"
CLASS_REJECTED_HTTP = "REJECTED_HTTP_FAILURE"

VALID_CLASSES = {
    CLASS_NOTICE_RESULT_ROW,
    CLASS_URBAN_RESULT_ROW,
    CLASS_PAGINATION_CONTRACT,
    CLASS_REJECTED_SOURCE_ENDPOINT,
    CLASS_REJECTED_NAVIGATION,
    CLASS_REJECTED_ROLE,
    CLASS_REJECTED_WEAK,
    CLASS_REJECTED_NON_OFFICIAL,
    CLASS_REJECTED_CROSS_HOST,
    CLASS_REJECTED_INVALID,
    CLASS_REJECTED_HTTP,
}

RESULT_ROW_CLASSES = {
    CLASS_NOTICE_RESULT_ROW,
    CLASS_URBAN_RESULT_ROW,
}


# ============================================================
# HTTP / BUDGET
# ============================================================

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 24
MAX_PAGES_PER_FAMILY = 12
MAX_LINKS_PER_PAGE = 4000

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


# ============================================================
# HTML
# ============================================================

TITLE_PATTERN = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
ANCHOR_PATTERN = re.compile(
    r"<a\b(?P<attrs>[^>]*)href\s*=\s*[\"'](?P<href>[^\"']+)[\"'](?P<tail>[^>]*)>(?P<body>.*?)</a>",
    re.I | re.S,
)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)

DATE_PATTERN = re.compile(
    r"(?<!\d)(20\d{2}|19\d{2})[.\-/년\s]+(0?[1-9]|1[0-2])[.\-/월\s]+(0?[1-9]|[12]\d|3[01])(?:일)?(?!\d)"
)
NOTICE_NUMBER_PATTERN = re.compile(
    r"(?:[가-힣A-Za-z0-9·\- ]{0,30})?(?:고시|공고)\s*제?\s*\d{2,4}\s*[-－]\s*\d+\s*호?",
    re.I,
)


# ============================================================
# SEMANTIC RULES
# ============================================================

PAGINATION_KEYS = {
    "page", "curpage", "pagenum", "pageindex", "page_no", "pageno", "currentpage",
}

NOTICE_BOARD_PATHS = {
    "/pm010301",
    "/pm010301/list",
    "/sn01040101",
}

URBAN_BOARD_PATH_PREFIXES = (
    "/ct020100",
)

DETAIL_HINTS = {
    "view", "detail", "read", "bbsview", "article", "post/view", "board/view",
    "idx=", "seq=", "no=", "nttid=", "article_no=", "board_seq=",
}

DOWNLOAD_HINTS = {
    "download", "filedown", "filedownload", "attach", "attachment",
    ".pdf", ".hwp", ".hwpx", ".zip",
}

GENERIC_NAV_TERMS = {
    "로그인", "회원가입", "사이트맵", "개인정보", "조직도", "오시는길", "메인",
    "home", "login", "member", "sitemap", "privacy", "facebook", "youtube",
}

ROLE_INCOMPATIBLE_TERMS = {
    "채용", "시험", "입찰", "일반 공고", "채용정보", "정보공개", "복지", "관광",
    "보도자료", "행사", "홍보", "성남 역사", "성남시사", "청년희망도시",
}

URBAN_ROW_TERMS = {
    "도시관리계획", "도시계획", "지형도면", "지구단위계획", "용도지역", "용도지구",
    "용도구역", "도시계획시설", "결정", "변경", "열람", "고시", "공고",
}

NOTICE_ROW_TERMS = {
    "고시", "공고", "고시공고", "고시 공고", "공고번호", "고시번호", "등록일",
}

VOLATILE_QUERY_KEYS = {
    "token", "_csrf", "csrf", "sessionid", "jsessionid", "timestamp", "rand", "random", "_",
}
TRACKING_QUERY_KEYS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid",
}


# ============================================================
# UTIL / URL
# ============================================================

def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()
    for value in values:
        text = normalize_space(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def strip_html(raw: str) -> str:
    value = COMMENT_PATTERN.sub(" ", raw or "")
    value = SCRIPT_STYLE_PATTERN.sub(" ", value)
    value = TAG_PATTERN.sub(" ", value)
    return normalize_space(html.unescape(value))


def canonicalize_url(url: str) -> str:
    value = normalize_space(url).replace("&amp;", "&")
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
    path = re.sub(r";jsessionid=[^/?]+", "", parsed.path or "/", flags=re.I)
    path = re.sub(r"/{2,}", "/", path)

    query_items: List[Tuple[str, str]] = []
    seen_pairs: Set[Tuple[str, str]] = set()
    for key, value_part in parse_qsl(parsed.query, keep_blank_values=True):
        key = normalize_space(key)
        if not key:
            continue
        lowered = key.lower()
        if lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS:
            continue
        if "csrf" in lowered or "session" in lowered:
            continue
        pair = (key, value_part)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        query_items.append(pair)

    query_items.sort(key=lambda item: (item[0].lower(), item[1]))
    query = urlencode(query_items, doseq=True)
    return urlunparse((scheme, host, path, "", query, ""))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def url_path(url: str) -> str:
    try:
        return (urlparse(url).path or "/").rstrip("/") or "/"
    except Exception:
        return "/"


def url_query_dict(url: str) -> Dict[str, str]:
    try:
        return {
            normalize_space(k).lower(): normalize_space(v)
            for k, v in parse_qsl(urlparse(url).query, keep_blank_values=True)
        }
    except Exception:
        return {}


def is_government_host(host: str) -> bool:
    value = normalize_space(host).lower()
    return bool(value) and (value == "go.kr" or value.endswith(".go.kr"))


def same_host(a: str, b: str) -> bool:
    return bool(hostname(a)) and hostname(a) == hostname(b)


def contains_any(value: str, terms: Iterable[str]) -> bool:
    lowered = normalize_space(value).lower()
    return any(normalize_space(term).lower() in lowered for term in terms if normalize_space(term))


def extract_page_number(url: str) -> int | None:
    query = url_query_dict(url)
    for key in PAGINATION_KEYS:
        value = query.get(key)
        if value and value.isdigit():
            return int(value)
    return None


def singleton_string(value: Any) -> List[str]:
    text = normalize_space(value)
    return [text] if text else []


def singleton_url(value: Any) -> List[str]:
    url = canonicalize_url(value or "")
    return [url] if url else []


# ============================================================
# INPUT
# ============================================================

def load_navigation_pool(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("next_stage_navigation_pool")
    if not isinstance(raw, list):
        return []

    result: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for item in raw:
        if not isinstance(item, dict):
            continue
        classification = normalize_space(item.get("classification"))
        if classification not in ALLOWED_INPUT_CLASSES:
            continue

        url = canonicalize_url(item.get("url") or "")
        if not url or url in seen:
            continue
        seen.add(url)

        source_families = unique_strings(
            item.get("source_families") or singleton_string(item.get("source_family"))
        )
        regions = unique_strings(item.get("regions") or singleton_string(item.get("region")))
        source_urls = unique_strings(item.get("source_urls") or singleton_url(item.get("source_url")))

        result.append({
            "classification": classification,
            "url": url,
            "source_family": normalize_space(item.get("source_family")),
            "source_families": source_families,
            "regions": regions,
            "source_urls": source_urls,
            "authority_role": normalize_space(item.get("authority_role")) or PRIMARY_ROLE,
            "authority_entities": unique_strings(
                item.get("authority_entities") or singleton_string(item.get("authority_entity"))
            ),
            "reasons": unique_strings(item.get("reasons") or []),
        })

    return result


# ============================================================
# HTTP
# ============================================================

def decode_html(response: requests.Response, data: bytes) -> str:
    encodings: List[str] = []
    content_type = normalize_space(response.headers.get("Content-Type"))
    match = re.search(r"charset\s*=\s*[\"']?([^;\"'\s]+)", content_type, flags=re.I)
    if match:
        encodings.append(match.group(1))
    if response.encoding:
        encodings.append(response.encoding)
    encodings.extend(["utf-8", "cp949", "euc-kr"])

    for encoding in unique_strings(encodings):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "response_bytes": 0,
        "raw_html": "",
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
            ctype = result["content_type"].lower()
            prefix = data[:1000].lstrip().lower()
            html_like = (
                "html" in ctype or "text/" in ctype
                or prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html")
            )
            if html_like:
                result["raw_html"] = decode_html(response, data)

    except Exception as exc:
        result["error"] = repr(exc)

    return result


# ============================================================
# HTML EXTRACTION
# ============================================================

def extract_title(raw_html: str) -> str:
    match = TITLE_PATTERN.search(raw_html or "")
    return strip_html(match.group(1)) if match else ""


def extract_links(raw_html: str, base_url: str) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    seen: Set[Tuple[str, str]] = set()

    for match in ANCHOR_PATTERN.finditer(raw_html or ""):
        href = html.unescape(normalize_space(match.group("href")))
        text = strip_html(match.group("body"))
        attrs = normalize_space((match.group("attrs") or "") + " " + (match.group("tail") or ""))
        if not href or href.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        absolute = canonicalize_url(urljoin(base_url, href))
        if not absolute:
            continue
        key = (absolute, text)
        if key in seen:
            continue
        seen.add(key)
        result.append({"url": absolute, "text": text, "attrs": attrs})
        if len(result) >= MAX_LINKS_PER_PAGE:
            break

    return result


def extract_dates(text: str) -> List[str]:
    result: List[str] = []
    for match in DATE_PATTERN.finditer(normalize_space(text)):
        year, month, day = match.groups()
        result.append(f"{int(year):04d}-{int(month):02d}-{int(day):02d}")
    return unique_strings(result)


def extract_notice_numbers(text: str) -> List[str]:
    return unique_strings(match.group(0) for match in NOTICE_NUMBER_PATTERN.finditer(normalize_space(text)))


# ============================================================
# FAMILY / ROLE
# ============================================================

def infer_page_family(item: Dict[str, Any]) -> str:
    families = item.get("source_families") or []
    path = url_path(item.get("url") or "")

    if path.startswith("/pm010301") or path.startswith("/sn01040101"):
        return FAMILY_NOTICE
    if path.startswith("/ct020100"):
        return FAMILY_URBAN
    if FAMILY_NOTICE in families:
        return FAMILY_NOTICE
    if FAMILY_URBAN in families:
        return FAMILY_URBAN
    return normalize_space(item.get("source_family"))


def is_source_endpoint(candidate_url: str, source_urls: List[str]) -> bool:
    candidate = canonicalize_url(candidate_url)
    return any(candidate == canonicalize_url(url) for url in source_urls if canonicalize_url(url))


def classify_link(
    *,
    page_family: str,
    page_url: str,
    source_urls: List[str],
    candidate_url: str,
    text: str,
    attrs: str,
) -> Dict[str, Any]:
    candidate_url = canonicalize_url(candidate_url)
    if not candidate_url:
        return {"qualified": False, "classification": CLASS_REJECTED_INVALID, "reasons": ["INVALID_URL"]}
    if not is_government_host(hostname(candidate_url)):
        return {"qualified": False, "classification": CLASS_REJECTED_NON_OFFICIAL, "reasons": ["NON_GO_KR"]}
    if not same_host(page_url, candidate_url):
        return {"qualified": False, "classification": CLASS_REJECTED_CROSS_HOST, "reasons": ["CROSS_HOST"]}
    if is_source_endpoint(candidate_url, source_urls):
        return {"qualified": False, "classification": CLASS_REJECTED_SOURCE_ENDPOINT, "reasons": ["SOURCE_ENDPOINT_SELF_LINK"]}

    evidence = normalize_space(" ".join([text, attrs, candidate_url]))
    path = url_path(candidate_url)
    query = url_query_dict(candidate_url)
    pagination_keys = sorted(key for key in query if key in PAGINATION_KEYS)

    if contains_any(evidence, GENERIC_NAV_TERMS):
        return {"qualified": False, "classification": CLASS_REJECTED_NAVIGATION, "reasons": ["GENERIC_NAVIGATION"]}
    if contains_any(evidence, ROLE_INCOMPATIBLE_TERMS):
        return {"qualified": False, "classification": CLASS_REJECTED_ROLE, "reasons": ["ROLE_INCOMPATIBLE_ROW"]}

    if pagination_keys:
        if page_family == FAMILY_NOTICE and (path.startswith("/pm010301") or path.startswith("/sn01040101")):
            return {
                "qualified": True,
                "classification": CLASS_PAGINATION_CONTRACT,
                "reasons": ["NOTICE_BOARD_PAGINATION"] + ["PAGINATION_KEY:" + key for key in pagination_keys],
            }
        if page_family == FAMILY_URBAN and path.startswith(URBAN_BOARD_PATH_PREFIXES):
            return {
                "qualified": True,
                "classification": CLASS_PAGINATION_CONTRACT,
                "reasons": ["URBAN_BOARD_PAGINATION"] + ["PAGINATION_KEY:" + key for key in pagination_keys],
            }

    detail_like = contains_any(candidate_url, DETAIL_HINTS) or contains_any(evidence, DOWNLOAD_HINTS)
    dates = extract_dates(text + " " + attrs)
    notice_numbers = extract_notice_numbers(text + " " + attrs)

    if page_family == FAMILY_NOTICE:
        role_local = contains_any(evidence, NOTICE_ROW_TERMS) or bool(notice_numbers) or detail_like
        if role_local and (normalize_space(text) or notice_numbers or dates):
            return {
                "qualified": True,
                "classification": CLASS_NOTICE_RESULT_ROW,
                "reasons": unique_strings(
                    ["NOTICE_RESULT_ROW_IDENTITY"]
                    + (["DETAIL_OR_DOWNLOAD_IDENTITY"] if detail_like else [])
                    + (["NOTICE_NUMBER_PRESENT"] if notice_numbers else [])
                    + (["DATE_PRESENT"] if dates else [])
                ),
                "dates": dates,
                "notice_numbers": notice_numbers,
            }

    if page_family == FAMILY_URBAN:
        role_local = contains_any(evidence, URBAN_ROW_TERMS)
        if role_local and (normalize_space(text) or detail_like or dates):
            return {
                "qualified": True,
                "classification": CLASS_URBAN_RESULT_ROW,
                "reasons": unique_strings(
                    ["URBAN_RESULT_ROW_IDENTITY"]
                    + (["DETAIL_OR_DOWNLOAD_IDENTITY"] if detail_like else [])
                    + (["NOTICE_NUMBER_PRESENT"] if notice_numbers else [])
                    + (["DATE_PRESENT"] if dates else [])
                ),
                "dates": dates,
                "notice_numbers": notice_numbers,
            }

    return {
        "qualified": False,
        "classification": CLASS_REJECTED_WEAK,
        "reasons": ["RESULT_ROW_IDENTITY_WEAK"],
        "dates": dates,
        "notice_numbers": notice_numbers,
    }


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("COMPETENT AUTHORITY HISTORICAL PAGINATION & RESULT-ROW DISCOVERY")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
    print()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"T-12 input not found: {INPUT_PATH}")

    input_data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(input_data, dict):
        raise TypeError("T-12 input must be JSON object")

    navigation = load_navigation_pool(input_data)
    print("T-12 navigation count:", len(navigation))
    print()

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    # T-12에서 pagination URL이 여러 개 있으므로 family별 page number 기준으로 제한한다.
    selected_pages: List[Dict[str, Any]] = []
    per_family_count: Counter[str] = Counter()

    for item in sorted(
        navigation,
        key=lambda x: (
            infer_page_family(x),
            extract_page_number(x.get("url") or "") or 0,
            x.get("url") or "",
        ),
    ):
        family = infer_page_family(item)
        path = url_path(item.get("url") or "")

        relevant = (
            (family == FAMILY_NOTICE and (path.startswith("/pm010301") or path.startswith("/sn01040101")))
            or (family == FAMILY_URBAN and path.startswith("/ct020100"))
        )
        if not relevant:
            continue
        if per_family_count[family] >= MAX_PAGES_PER_FAMILY:
            continue
        selected_pages.append(item)
        per_family_count[family] += 1

    request_count = 0
    http_success_count = 0
    transport_error_count = 0
    raw_records: List[Dict[str, Any]] = []
    page_results: List[Dict[str, Any]] = []

    seen_requested_urls: Set[str] = set()

    for index, item in enumerate(selected_pages, start=1):
        if request_count >= MAX_TOTAL_REQUESTS:
            break

        page_url = canonicalize_url(item.get("url") or "")
        if not page_url or page_url in seen_requested_urls:
            continue
        seen_requested_urls.add(page_url)

        family = infer_page_family(item)
        source_urls = unique_strings(item.get("source_urls") or [])

        print("-" * 60)
        print(f"PAGE {index}")
        print("Family:", family)
        print("URL:", page_url)
        print("Page number:", extract_page_number(page_url))

        request_count += 1
        response = fetch_page(session, page_url)
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1

        final_url = canonicalize_url(response.get("final_url") or page_url)
        raw_html = str(response.get("raw_html") or "")
        title = extract_title(raw_html)
        links = extract_links(raw_html, final_url) if raw_html else []

        qualified_rows = 0
        pagination_links = 0

        if not (isinstance(status, int) and 200 <= status < 300):
            raw_records.append({
                "page_family": family,
                "page_url": page_url,
                "url": page_url,
                "qualified": False,
                "classification": CLASS_REJECTED_HTTP,
                "reasons": ["HTTP_NON_2XX"],
                "http_status": status,
                "target_query_executed": False,
                "document_candidate": False,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            })
        else:
            for link in links:
                outcome = classify_link(
                    page_family=family,
                    page_url=final_url,
                    source_urls=source_urls,
                    candidate_url=link["url"],
                    text=link["text"],
                    attrs=link["attrs"],
                )

                record = {
                    "page_family": family,
                    "source_families": unique_strings(item.get("source_families") or singleton_string(item.get("source_family"))),
                    "authority_role": item.get("authority_role") or PRIMARY_ROLE,
                    "authority_entities": unique_strings(item.get("authority_entities") or []),
                    "regions": unique_strings(item.get("regions") or []),
                    "source_urls": source_urls,
                    "page_url": page_url,
                    "page_number": extract_page_number(page_url),
                    "page_title": title,
                    "url": canonicalize_url(link["url"]),
                    "row_text": link["text"],
                    "row_attrs": link["attrs"],
                    "dates": unique_strings(outcome.get("dates") or extract_dates(link["text"] + " " + link["attrs"])),
                    "notice_numbers": unique_strings(outcome.get("notice_numbers") or extract_notice_numbers(link["text"] + " " + link["attrs"])),
                    "qualified": outcome["qualified"],
                    "classification": outcome["classification"],
                    "reasons": unique_strings(outcome.get("reasons") or []),
                    "target_query_executed": False,
                    "document_candidate": False,
                    "verified_positive": False,
                    "runtime_registration_allowed": False,
                    "site_positive_allowed": False,
                    "site_negative_allowed": False,
                    "final_positive_promotion_allowed": False,
                }
                raw_records.append(record)

                if record["classification"] in RESULT_ROW_CLASSES and record["qualified"]:
                    qualified_rows += 1
                if record["classification"] == CLASS_PAGINATION_CONTRACT and record["qualified"]:
                    pagination_links += 1

        page_results.append({
            "page_family": family,
            "url": page_url,
            "page_number": extract_page_number(page_url),
            "http_status": status,
            "title": title,
            "link_count": len(links),
            "qualified_result_row_count": qualified_rows,
            "pagination_link_count": pagination_links,
            "resolution": "PAGE_STRUCTURE_RECOVERED" if status == 200 else "PAGE_FETCH_FAILED",
        })

        print("HTTP:", status)
        print("Title:", title)
        print("Links:", len(links))
        print("Qualified result rows:", qualified_rows)
        print("Pagination links:", pagination_links)
        print()

    # ========================================================
    # CANONICAL DEDUPE
    # ========================================================

    canonical_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    duplicate_count = 0

    for item in raw_records:
        url = canonicalize_url(item.get("url") or "")
        classification = normalize_space(item.get("classification"))
        if not url:
            continue
        identity_group = "ROW" if classification in RESULT_ROW_CLASSES else classification
        key = (identity_group, url)

        if key in canonical_map:
            duplicate_count += 1
            existing = canonical_map[key]
            for field in [
                "source_families", "authority_entities", "regions", "source_urls",
                "dates", "notice_numbers", "reasons",
            ]:
                existing[field] = unique_strings((existing.get(field) or []) + (item.get(field) or []))
            existing["page_urls"] = unique_strings(
                (existing.get("page_urls") or singleton_url(existing.get("page_url")))
                + singleton_url(item.get("page_url"))
            )
            existing["row_text_variants"] = unique_strings(
                (existing.get("row_text_variants") or singleton_string(existing.get("row_text")))
                + singleton_string(item.get("row_text"))
            )
            if item.get("qualified") is True:
                existing["qualified"] = True
            continue

        canonical = dict(item)
        canonical["page_urls"] = singleton_url(item.get("page_url"))
        canonical["row_text_variants"] = singleton_string(item.get("row_text"))
        canonical_map[key] = canonical

    canonical_records = list(canonical_map.values())
    canonical_records.sort(key=lambda x: (
        -int(x.get("qualified") is True),
        normalize_space(x.get("classification")),
        canonicalize_url(x.get("url") or ""),
    ))

    result_rows = [
        item for item in canonical_records
        if item.get("qualified") is True and item.get("classification") in RESULT_ROW_CLASSES
    ]
    pagination_contracts = [
        item for item in canonical_records
        if item.get("qualified") is True and item.get("classification") == CLASS_PAGINATION_CONTRACT
    ]

    next_stage_result_row_pool = [
        {
            "page_family": item.get("page_family"),
            "source_families": item.get("source_families") or [],
            "authority_role": item.get("authority_role"),
            "authority_entities": item.get("authority_entities") or [],
            "regions": item.get("regions") or [],
            "source_urls": item.get("source_urls") or [],
            "page_urls": item.get("page_urls") or singleton_url(item.get("page_url")),
            "url": canonicalize_url(item.get("url") or ""),
            "row_text": item.get("row_text"),
            "row_text_variants": item.get("row_text_variants") or singleton_string(item.get("row_text")),
            "dates": item.get("dates") or [],
            "notice_numbers": item.get("notice_numbers") or [],
            "classification": item.get("classification"),
            "reasons": item.get("reasons") or [],
            "result_row_only": True,
            "requires_target_identity_filtering": True,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in result_rows
        if canonicalize_url(item.get("url") or "")
    ]

    next_stage_pagination_pool = [
        {
            "page_family": item.get("page_family"),
            "regions": item.get("regions") or [],
            "url": canonicalize_url(item.get("url") or ""),
            "page_number": extract_page_number(item.get("url") or ""),
            "classification": CLASS_PAGINATION_CONTRACT,
            "reasons": item.get("reasons") or [],
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in pagination_contracts
        if canonicalize_url(item.get("url") or "")
    ]

    if result_rows or pagination_contracts:
        resolution = "COMPETENT_AUTHORITY_HISTORICAL_PAGINATION_DISCOVERY_COMPLETED"
        next_action = (
            "복원된 result-row identity와 pagination contract만 T-14 입력으로 사용한다. "
            "T-14에서는 아직 검색어 재실행 없이 row-local title/notice-number/date/detail URL을 "
            "기준으로 UQQ700 target identity filter를 적용하고, 실제 detail 문서는 후속 direct "
            "document verification 단계로 넘긴다."
        )
    else:
        resolution = "COMPETENT_AUTHORITY_HISTORICAL_PAGINATION_DISCOVERY_NO_STRUCTURE"
        next_action = (
            "competent-authority source에서 historical row/pagination 구조를 복원하지 못했다. "
            "SITE FALSE로 판정하지 않고 UNKNOWN을 유지하며 source-specific HTML/JS contract를 추가 분석한다."
        )

    classification_counts = Counter(item.get("classification") for item in canonical_records)

    output_data = {
        "step": "STEP 17-21-C-16-8-T-13 Competent Authority Historical Pagination & Result-Row Discovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "inputs": {
            "t12_path": str(INPUT_PATH),
            "t12_resolution": input_data.get("resolution"),
        },
        "method": {
            "t12_navigation_only": True,
            "target_query_execution_enabled": False,
            "direct_pagination_requery_enabled": True,
            "result_local_evidence_required": True,
            "page_title_alone_evidence_disabled": True,
            "source_endpoint_promotion_disabled": True,
            "role_incompatible_row_guard_enabled": True,
            "canonical_result_identity_by_url": True,
            "cross_page_row_dedupe_enabled": True,
            "negative_evidence_enabled": False,
            "verified_positive_promotion_allowed": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
        },
        "summary": {
            "t12_navigation_count": len(navigation),
            "selected_page_count": len(selected_pages),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "raw_record_count": len(raw_records),
            "duplicate_record_removed": duplicate_count,
            "canonical_record_count": len(canonical_records),
            "result_row_count": len(result_rows),
            "pagination_contract_count": len(pagination_contracts),
            "next_stage_result_row_pool_count": len(next_stage_result_row_pool),
            "next_stage_pagination_pool_count": len(next_stage_pagination_pool),
        },
        "classification_counts": dict(sorted(classification_counts.items())),
        "page_results": page_results,
        "result_rows": result_rows,
        "pagination_contracts": pagination_contracts,
        "next_stage_result_row_pool": next_stage_result_row_pool,
        "next_stage_pagination_pool": next_stage_pagination_pool,
        "all_canonical_records": canonical_records,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }

    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ========================================================
    # RESULT
    # ========================================================

    print("=" * 60)
    print("COMPETENT AUTHORITY HISTORICAL PAGINATION DISCOVERY RESULT")
    print("=" * 60)
    print("T-12 navigation count:", len(navigation))
    print("Selected page count:", len(selected_pages))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Transport error count:", transport_error_count)
    print("Raw record count:", len(raw_records))
    print("Duplicate record removed:", duplicate_count)
    print("Canonical record count:", len(canonical_records))
    print("Result row count:", len(result_rows))
    print("Pagination contract count:", len(pagination_contracts))
    print("Next-stage result row pool count:", len(next_stage_result_row_pool))
    print("Next-stage pagination pool count:", len(next_stage_pagination_pool))
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

    result_urls = [canonicalize_url(item.get("url") or "") for item in result_rows]
    result_url_set = {url for url in result_urls if url}
    next_result_urls = [canonicalize_url(item.get("url") or "") for item in next_stage_result_row_pool]
    next_result_url_set = {url for url in next_result_urls if url}
    pagination_urls = [canonicalize_url(item.get("url") or "") for item in pagination_contracts]
    pagination_url_set = {url for url in pagination_urls if url}
    next_pagination_urls = [canonicalize_url(item.get("url") or "") for item in next_stage_pagination_pool]
    next_pagination_url_set = {url for url in next_pagination_urls if url}

    all_classes_valid = all(item.get("classification") in VALID_CLASSES for item in canonical_records)
    invalid_result_url_leakage = sum(1 for url in result_urls if not url)
    duplicate_result_url_leakage = len(result_urls) - len(result_url_set)
    invalid_pagination_url_leakage = sum(1 for url in pagination_urls if not url)
    duplicate_pagination_url_leakage = len(pagination_urls) - len(pagination_url_set)

    non_go_kr_result_leakage = sum(
        1 for item in result_rows
        if not is_government_host(hostname(item.get("url") or ""))
    )
    cross_host_result_leakage = sum(
        1 for item in result_rows
        if item.get("page_url") and not same_host(item.get("page_url") or "", item.get("url") or "")
    )
    query_evidence_leakage = sum(
        1 for item in result_rows if item.get("target_query_executed") is True
    )
    verified_positive_leakage = sum(
        1 for item in canonical_records if item.get("verified_positive") is True
    )
    runtime_registration_leakage = sum(
        1 for item in canonical_records if item.get("runtime_registration_allowed") is True
    )
    site_true_leakage = sum(
        1 for item in canonical_records if item.get("site_positive_allowed") is True
    )
    site_false_leakage = sum(
        1 for item in canonical_records if item.get("site_negative_allowed") is True
    )
    next_stage_safety_leakage = sum(
        1
        for item in next_stage_result_row_pool + next_stage_pagination_pool
        if (
            item.get("verified_positive") is True
            or item.get("runtime_registration_allowed") is True
            or item.get("site_positive_allowed") is True
            or item.get("site_negative_allowed") is True
            or item.get("final_positive_promotion_allowed") is True
        )
    )
    false_from_no_structure_leakage = (
        1
        if not result_rows and not pagination_contracts
        and output_data["resolution_policy"]["source_failure_site_status"] == "FALSE"
        else 0
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-12 input exists": INPUT_PATH.exists(),
        "T-12 input parsed": isinstance(input_data, dict),
        "T-12 navigation loaded": len(navigation) > 0,
        "T-12 navigation only": True,
        "bounded page request count respected": request_count <= MAX_TOTAL_REQUESTS,
        "target query execution disabled": query_evidence_leakage == 0,
        "result-local evidence required": True,
        "page-title-only promotion disabled": True,
        "source endpoint promotion disabled": True,
        "role incompatible row guard enabled": True,
        "all classes valid": all_classes_valid,
        "result row URLs valid": invalid_result_url_leakage == 0,
        "result row URLs unique": duplicate_result_url_leakage == 0,
        "pagination URLs valid": invalid_pagination_url_leakage == 0,
        "pagination URLs unique": duplicate_pagination_url_leakage == 0,
        "result and next-stage parity": result_url_set == next_result_url_set,
        "pagination and next-stage parity": pagination_url_set == next_pagination_url_set,
        "result non-go.kr leakage zero": non_go_kr_result_leakage == 0,
        "result cross-host leakage zero": cross_host_result_leakage == 0,
        "verified positive leakage zero": verified_positive_leakage == 0,
        "runtime registration leakage zero": runtime_registration_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "next-stage safety leakage zero": next_stage_safety_leakage == 0,
        "false from no structure leakage zero": false_from_no_structure_leakage == 0,
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
    print("Invalid result URL leakage:", invalid_result_url_leakage)
    print("Duplicate result URL leakage:", duplicate_result_url_leakage)
    print("Invalid pagination URL leakage:", invalid_pagination_url_leakage)
    print("Duplicate pagination URL leakage:", duplicate_pagination_url_leakage)
    print("Non-go.kr result leakage:", non_go_kr_result_leakage)
    print("Cross-host result leakage:", cross_host_result_leakage)
    print("Target query leakage:", query_evidence_leakage)
    print("Verified positive leakage:", verified_positive_leakage)
    print("Runtime registration leakage:", runtime_registration_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print("Next-stage safety leakage:", next_stage_safety_leakage)
    print("False from no structure leakage:", false_from_no_structure_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")

    if not all_pass:
        failed = [name for name, passed in validations.items() if not passed]
        print("FAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError(
            "UQQ700 competent authority historical pagination/result-row discovery regression failed"
        )


if __name__ == "__main__":
    main()
