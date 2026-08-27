# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-12
Development Density Management Area
Competent Authority Historical Navigation Recovery

목표
======================================================================
T-11에서 확정한 PRIMARY designation-authority source만 직접 재조회하여,
UQQ700 target query를 실행하지 않고 source-local historical navigation
identity를 복원한다.

탐색 대상
======================================================================
- pagination/list navigation
- archive/history/year/month navigation
- 고시공고 상세/list URL identity
- 도시계획/도시관리계획/지형도면 관련 source-local navigation
- 첨부/다운로드 URL은 이 단계에서 document candidate로 승격하지 않는다.

핵심 원칙
======================================================================
1. T-11 next_stage_primary_source_pool만 사용한다.
2. PRIMARY designation-authority source만 허용한다.
3. direct HTTP requery 필수.
4. final host go.kr + same-host 필수.
5. UQQ700 target query 실행 금지.
6. query 문자열을 evidence로 사용하지 않는다.
7. source endpoint 자체를 historical document로 승격하지 않는다.
8. navigation contract는 verified positive가 아니다.
9. SITE TRUE/FALSE 및 runtime registration 금지.
10. no navigation != SITE FALSE; UNKNOWN 유지.
"""

from __future__ import annotations

import html
import json
import re
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
    "development_density_management_area_competent_authority_historical_source_scope.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_competent_authority_historical_navigation_recovery.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False
PRIMARY_ROLE = "PRIMARY_DESIGNATION_AUTHORITY_SOURCE"


# ============================================================
# CLASS
# ============================================================

CLASS_HISTORICAL_LIST = "RECOVERED_AUTHORITY_HISTORICAL_LIST_NAVIGATION"
CLASS_PAGINATION = "RECOVERED_AUTHORITY_PAGINATION_NAVIGATION"
CLASS_NOTICE_DETAIL = "RECOVERED_AUTHORITY_NOTICE_DETAIL_PATTERN"
CLASS_URBAN_NAV = "RECOVERED_AUTHORITY_URBAN_PLANNING_NAVIGATION"
CLASS_ARCHIVE_NAV = "RECOVERED_AUTHORITY_ARCHIVE_NAVIGATION"

CLASS_REJECTED_SOURCE_ENDPOINT = "REJECTED_SOURCE_ENDPOINT_SELF_LINK"
CLASS_REJECTED_GENERIC = "REJECTED_GENERIC_NAVIGATION"
CLASS_REJECTED_NON_OFFICIAL = "REJECTED_NON_OFFICIAL_NAVIGATION"
CLASS_REJECTED_CROSS_HOST = "REJECTED_CROSS_HOST_NAVIGATION"
CLASS_REJECTED_DOCUMENT_DOWNLOAD = "REJECTED_DOCUMENT_DOWNLOAD_AT_NAVIGATION_STAGE"
CLASS_REJECTED_WEAK = "REJECTED_HISTORICAL_NAVIGATION_EVIDENCE_WEAK"
CLASS_REJECTED_INVALID = "REJECTED_INVALID_NAVIGATION_URL"

VALID_CLASSES = {
    CLASS_HISTORICAL_LIST,
    CLASS_PAGINATION,
    CLASS_NOTICE_DETAIL,
    CLASS_URBAN_NAV,
    CLASS_ARCHIVE_NAV,
    CLASS_REJECTED_SOURCE_ENDPOINT,
    CLASS_REJECTED_GENERIC,
    CLASS_REJECTED_NON_OFFICIAL,
    CLASS_REJECTED_CROSS_HOST,
    CLASS_REJECTED_DOCUMENT_DOWNLOAD,
    CLASS_REJECTED_WEAK,
    CLASS_REJECTED_INVALID,
}
QUALIFIED_CLASSES = {
    CLASS_HISTORICAL_LIST,
    CLASS_PAGINATION,
    CLASS_NOTICE_DETAIL,
    CLASS_URBAN_NAV,
    CLASS_ARCHIVE_NAV,
}


# ============================================================
# HTTP / HTML
# ============================================================

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_LINKS_PER_SOURCE = 3000
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TITLE_PATTERN = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
ANCHOR_PATTERN = re.compile(
    r"<a\b(?P<attrs>[^>]*)href\s*=\s*[\"'](?P<href>[^\"']+)[\"'](?P<tail>[^>]*)>(?P<body>.*?)</a>",
    re.I | re.S,
)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)


# ============================================================
# SEMANTIC TERMS
# ============================================================

ARCHIVE_TERMS = {
    "archive", "history", "historical", "past", "old", "previous",
    "연혁", "과거", "지난", "이전", "년도", "연도", "년", "월",
}
LIST_TERMS = {
    "list", "bbslist", "boardlist", "notice/list", "gosi", "gonggo",
    "고시", "공고", "고시공고", "목록",
}
NOTICE_DETAIL_TERMS = {
    "view", "detail", "read", "bbsview", "board/view", "article", "post/view",
    "고시공고번호", "공고번호", "고시번호",
}
URBAN_TERMS = {
    "도시계획", "도시관리계획", "지형도면", "도시·주택", "urban", "cityplan", "city-plan",
}
PAGINATION_KEYS = {
    "page", "curpage", "pagenum", "pageindex", "page_no", "pageno", "currentpage",
}
YEAR_KEYS = {"year", "yyyy", "searchyear", "srchyear", "schyear"}
DOWNLOAD_TERMS = {
    "download", "filedown", "filedownload", "attach", "attachment", ".pdf", ".hwp", ".hwpx", ".zip",
}
GENERIC_TERMS = {
    "login", "member", "sitemap", "privacy", "facebook", "youtube", "instagram",
    "로그인", "회원가입", "사이트맵", "개인정보", "조직도", "오시는길", "민원신청",
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
    items: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        key = normalize_space(key)
        lowered = key.lower()
        if not key or lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS or "csrf" in lowered or "session" in lowered:
            continue
        pair = (key, val)
        if pair not in seen:
            seen.add(pair)
            items.append(pair)
    items.sort(key=lambda pair: (pair[0].lower(), pair[1]))
    return urlunparse((scheme, host, path, "", urlencode(items, doseq=True), ""))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    value = normalize_space(host).lower()
    return bool(value) and (value == "go.kr" or value.endswith(".go.kr"))


def same_host(a: str, b: str) -> bool:
    return bool(hostname(a)) and hostname(a) == hostname(b)


def url_query_dict(url: str) -> Dict[str, str]:
    try:
        return {normalize_space(k).lower(): normalize_space(v) for k, v in parse_qsl(urlparse(url).query, keep_blank_values=True)}
    except Exception:
        return {}


def same_endpoint_identity(a: str, b: str) -> bool:
    ca = canonicalize_url(a)
    cb = canonicalize_url(b)
    return bool(ca and cb and ca == cb)


# ============================================================
# INPUT
# ============================================================

def load_primary_sources(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("next_stage_primary_source_pool")
    if not isinstance(raw, list):
        return []
    result: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        if normalize_space(item.get("authority_role")) != PRIMARY_ROLE:
            continue
        url = canonicalize_url(item.get("url") or "")
        if not url or url in seen:
            continue
        seen.add(url)
        result.append({
            "region": normalize_space(item.get("region")),
            "source_family": normalize_space(item.get("source_family")),
            "authority_role": PRIMARY_ROLE,
            "authority_entity": normalize_space(item.get("authority_entity")),
            "url": url,
            "reasons": unique_strings(item.get("reasons") or []),
        })
    return result


# ============================================================
# HTTP
# ============================================================

def decode_html(response: requests.Response, data: bytes) -> str:
    candidates: List[str] = []
    content_type = normalize_space(response.headers.get("Content-Type"))
    match = re.search(r"charset\s*=\s*[\"']?([^;\"'\s]+)", content_type, flags=re.I)
    if match:
        candidates.append(match.group(1))
    if response.encoding:
        candidates.append(response.encoding)
    candidates.extend(["utf-8", "cp949", "euc-kr"])
    for encoding in unique_strings(candidates):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "final_url": "", "http_status": None, "content_type": "", "response_bytes": 0,
        "raw_html": "", "error": "",
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
            if "html" in ctype or "text/" in ctype or prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html"):
                result["raw_html"] = decode_html(response, data)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


# ============================================================
# HTML LINK EXTRACTION
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
        if len(result) >= MAX_LINKS_PER_SOURCE:
            break
    return result


# ============================================================
# CLASSIFICATION
# ============================================================

def contains_any(value: str, terms: Iterable[str]) -> bool:
    lowered = normalize_space(value).lower()
    return any(normalize_space(term).lower() in lowered for term in terms if normalize_space(term))


def classify_navigation(source_url: str, candidate_url: str, text: str, attrs: str) -> Dict[str, Any]:
    candidate_url = canonicalize_url(candidate_url)
    if not candidate_url:
        return {"qualified": False, "classification": CLASS_REJECTED_INVALID, "reasons": ["INVALID_URL"]}
    if not is_government_host(hostname(candidate_url)):
        return {"qualified": False, "classification": CLASS_REJECTED_NON_OFFICIAL, "reasons": ["NON_GO_KR"]}
    if not same_host(source_url, candidate_url):
        return {"qualified": False, "classification": CLASS_REJECTED_CROSS_HOST, "reasons": ["CROSS_HOST"]}
    if same_endpoint_identity(source_url, candidate_url):
        return {"qualified": False, "classification": CLASS_REJECTED_SOURCE_ENDPOINT, "reasons": ["SOURCE_ENDPOINT_SELF_LINK"]}

    evidence = normalize_space(" ".join([candidate_url, text, attrs]))
    lowered = evidence.lower()
    query = url_query_dict(candidate_url)

    if contains_any(lowered, DOWNLOAD_TERMS):
        return {"qualified": False, "classification": CLASS_REJECTED_DOCUMENT_DOWNLOAD, "reasons": ["DOWNLOAD_IDENTITY_DEFERRED_TO_DOCUMENT_STAGE"]}
    if contains_any(lowered, GENERIC_TERMS):
        return {"qualified": False, "classification": CLASS_REJECTED_GENERIC, "reasons": ["GENERIC_NAVIGATION"]}

    reasons: List[str] = []
    classification = ""

    pagination_hits = sorted(key for key in query if key in PAGINATION_KEYS)
    year_hits = sorted(key for key in query if key in YEAR_KEYS)
    if pagination_hits:
        classification = CLASS_PAGINATION
        reasons.extend("PAGINATION_KEY:" + key for key in pagination_hits)

    if contains_any(evidence, ARCHIVE_TERMS) or year_hits:
        classification = CLASS_ARCHIVE_NAV
        reasons.append("ARCHIVE_OR_PERIOD_IDENTITY")
        reasons.extend("YEAR_KEY:" + key for key in year_hits)

    if contains_any(evidence, URBAN_TERMS):
        classification = CLASS_URBAN_NAV
        reasons.append("URBAN_PLANNING_NAVIGATION_IDENTITY")

    if contains_any(evidence, NOTICE_DETAIL_TERMS):
        classification = CLASS_NOTICE_DETAIL
        reasons.append("NOTICE_DETAIL_URL_OR_TEXT_IDENTITY")

    if not classification and contains_any(evidence, LIST_TERMS):
        classification = CLASS_HISTORICAL_LIST
        reasons.append("NOTICE_OR_LIST_NAVIGATION_IDENTITY")

    if not classification:
        return {"qualified": False, "classification": CLASS_REJECTED_WEAK, "reasons": ["HISTORICAL_NAVIGATION_EVIDENCE_WEAK"]}

    return {"qualified": True, "classification": classification, "reasons": unique_strings(reasons)}


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("COMPETENT AUTHORITY HISTORICAL NAVIGATION RECOVERY")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
    print()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"T-11 input not found: {INPUT_PATH}")
    input_data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(input_data, dict):
        raise TypeError("T-11 input must be JSON object")
    sources = load_primary_sources(input_data)
    print("Primary source count:", len(sources))
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
    raw_records: List[Dict[str, Any]] = []
    source_results: List[Dict[str, Any]] = []

    for index, source in enumerate(sources, start=1):
        source_url = source["url"]
        print("-" * 60)
        print(f"SOURCE {index}")
        print("Family:", source["source_family"])
        print("Authority:", source["authority_entity"])
        print("Region:", source["region"])
        print("URL:", source_url)

        request_count += 1
        response = fetch_page(session, source_url)
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1

        final_url = canonicalize_url(response.get("final_url") or source_url)
        raw_html = str(response.get("raw_html") or "")
        title = extract_title(raw_html)
        links = extract_links(raw_html, final_url) if raw_html else []
        qualified_count = 0

        for link in links:
            outcome = classify_navigation(source_url, link["url"], link["text"], link["attrs"])
            record = {
                "source_family": source["source_family"],
                "authority_role": PRIMARY_ROLE,
                "authority_entity": source["authority_entity"],
                "region": source["region"],
                "source_url": source_url,
                "page_title": title,
                "url": canonicalize_url(link["url"]),
                "link_text": link["text"],
                "qualified": outcome["qualified"],
                "classification": outcome["classification"],
                "reasons": outcome["reasons"],
                "target_query_executed": False,
                "document_candidate": False,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            }
            raw_records.append(record)
            if record["qualified"]:
                qualified_count += 1

        source_results.append({
            "source_family": source["source_family"],
            "region": source["region"],
            "authority_entity": source["authority_entity"],
            "source_url": source_url,
            "http_status": status,
            "final_url": final_url,
            "title": title,
            "link_count": len(links),
            "qualified_navigation_count": qualified_count,
            "resolution": "HISTORICAL_NAVIGATION_RECOVERED" if qualified_count else "NO_HISTORICAL_NAVIGATION_RECOVERED",
        })

        print("HTTP:", status)
        print("Title:", title)
        print("Links:", len(links))
        print("Qualified navigation:", qualified_count)
        print("Resolution:", source_results[-1]["resolution"])
        print()

    # ========================================================
    # CANONICAL DEDUPE
    # ========================================================

    canonical_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    duplicate_count = 0
    for item in raw_records:
        url = canonicalize_url(item.get("url") or "")
        if not url:
            continue
        key = (item.get("source_family") or "", url)
        if key in canonical_map:
            duplicate_count += 1
            existing = canonical_map[key]
            existing["reasons"] = unique_strings((existing.get("reasons") or []) + (item.get("reasons") or []))
            existing["link_text_variants"] = unique_strings(
                (existing.get("link_text_variants") or [existing.get("link_text")]) + [item.get("link_text")]
            )
            if item.get("qualified") is True:
                existing["qualified"] = True
                if item.get("classification") in QUALIFIED_CLASSES:
                    existing["classification"] = item.get("classification")
            continue
        canonical = dict(item)
        canonical["link_text_variants"] = unique_strings([item.get("link_text")])
        canonical_map[key] = canonical

    canonical_records = list(canonical_map.values())
    canonical_records.sort(key=lambda item: (-int(item.get("qualified") is True), item.get("source_family") or "", item.get("url") or ""))
    qualified_navigation = [item for item in canonical_records if item.get("qualified") is True]
    rejected_navigation = [item for item in canonical_records if item.get("qualified") is not True]

    next_stage_navigation_pool = [
        {
            "source_family": item.get("source_family"),
            "authority_role": item.get("authority_role"),
            "authority_entity": item.get("authority_entity"),
            "region": item.get("region"),
            "source_url": item.get("source_url"),
            "url": item.get("url"),
            "classification": item.get("classification"),
            "link_text": item.get("link_text"),
            "link_text_variants": item.get("link_text_variants") or [],
            "reasons": item.get("reasons") or [],
            "historical_navigation_only": True,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in qualified_navigation
    ]

    if next_stage_navigation_pool:
        resolution = "COMPETENT_AUTHORITY_HISTORICAL_NAVIGATION_RECOVERY_COMPLETED"
        next_action = (
            "T-13에서 recovered authority-local navigation을 직접 검증하여 historical list/detail pattern을 분리한다. "
            "그 후 notice number/date/title 기반 bounded identity discovery를 수행한다. target query 자체는 evidence로 사용하지 않는다."
        )
    else:
        resolution = "COMPETENT_AUTHORITY_HISTORICAL_NAVIGATION_RECOVERY_NO_NAVIGATION"
        next_action = (
            "PRIMARY authority source에서 별도 historical navigation을 복원하지 못했다. SITE FALSE로 판정하지 않고 UNKNOWN을 유지한다. "
            "다음 단계에서는 current notice board의 pagination/date range contract 또는 별도 municipal gazette archive를 구조적으로 복원한다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-12 Competent Authority Historical Navigation Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "inputs": {
            "t11_path": str(INPUT_PATH),
            "t11_resolution": input_data.get("resolution"),
        },
        "method": {
            "primary_authority_sources_only": True,
            "direct_network_requery_enabled": True,
            "target_query_execution_enabled": False,
            "query_evidence_enabled": False,
            "same_host_required": True,
            "go_kr_required": True,
            "pagination_navigation_recovery_enabled": True,
            "archive_navigation_recovery_enabled": True,
            "urban_navigation_recovery_enabled": True,
            "notice_detail_pattern_recovery_enabled": True,
            "document_download_promotion_enabled": False,
            "source_endpoint_promotion_enabled": False,
        },
        "summary": {
            "primary_source_count": len(sources),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "raw_navigation_record_count": len(raw_records),
            "duplicate_navigation_removed": duplicate_count,
            "canonical_navigation_count": len(canonical_records),
            "qualified_navigation_count": len(qualified_navigation),
            "rejected_navigation_count": len(rejected_navigation),
            "next_stage_navigation_pool_count": len(next_stage_navigation_pool),
        },
        "source_results": source_results,
        "qualified_navigation": qualified_navigation,
        "rejected_navigation": rejected_navigation,
        "next_stage_navigation_pool": next_stage_navigation_pool,
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
    # VALIDATION
    # ========================================================

    next_urls = [canonicalize_url(item.get("url") or "") for item in next_stage_navigation_pool]
    canonical_qualified_urls = [canonicalize_url(item.get("url") or "") for item in qualified_navigation]
    invalid_url_leakage = sum(1 for url in next_urls if not url)
    duplicate_url_leakage = len(next_urls) - len(set(next_urls))
    non_go_kr_leakage = sum(1 for item in qualified_navigation if not is_government_host(hostname(item.get("url") or "")))
    cross_host_leakage = sum(1 for item in qualified_navigation if not same_host(item.get("source_url") or "", item.get("url") or ""))
    source_endpoint_leakage = sum(1 for item in qualified_navigation if same_endpoint_identity(item.get("source_url") or "", item.get("url") or ""))
    document_candidate_leakage = sum(1 for item in canonical_records if item.get("document_candidate") is True)
    target_query_leakage = sum(1 for item in canonical_records if item.get("target_query_executed") is True)
    unsafe_leakage = sum(
        1 for item in next_stage_navigation_pool
        if item.get("verified_positive") is True
        or item.get("runtime_registration_allowed") is True
        or item.get("site_positive_allowed") is True
        or item.get("site_negative_allowed") is True
        or item.get("final_positive_promotion_allowed") is True
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-11 input exists": INPUT_PATH.exists(),
        "T-11 input parsed": isinstance(input_data, dict),
        "primary authority sources loaded": len(sources) > 0,
        "primary authority only": all(item.get("authority_role") == PRIMARY_ROLE for item in sources),
        "direct network requery enabled": True,
        "target query execution disabled": target_query_leakage == 0,
        "document candidate generation disabled": document_candidate_leakage == 0,
        "all classes valid": all(item.get("classification") in VALID_CLASSES for item in canonical_records),
        "qualified classes valid": all(item.get("classification") in QUALIFIED_CLASSES for item in qualified_navigation),
        "qualified URLs valid": invalid_url_leakage == 0,
        "qualified URLs unique": duplicate_url_leakage == 0,
        "qualified and next-stage parity": set(canonical_qualified_urls) == set(next_urls),
        "qualified go.kr leakage zero": non_go_kr_leakage == 0,
        "qualified cross-host leakage zero": cross_host_leakage == 0,
        "source endpoint promotion leakage zero": source_endpoint_leakage == 0,
        "next-stage safety leakage zero": unsafe_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print("=" * 60)
    print("COMPETENT AUTHORITY HISTORICAL NAVIGATION RESULT")
    print("=" * 60)
    print("Primary source count:", len(sources))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Transport error count:", transport_error_count)
    print("Raw navigation record count:", len(raw_records))
    print("Duplicate navigation removed:", duplicate_count)
    print("Canonical navigation count:", len(canonical_records))
    print("Qualified navigation count:", len(qualified_navigation))
    print("Next-stage navigation pool count:", len(next_stage_navigation_pool))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)

    if qualified_navigation:
        print()
        print("QUALIFIED AUTHORITY-LOCAL NAVIGATION")
        print("-" * 60)
        for index, item in enumerate(qualified_navigation, start=1):
            print(f"[{index}] {item.get('classification')}")
            print("Family:", item.get("source_family"))
            print("Region:", item.get("region"))
            print("URL:", item.get("url"))
            print("Text:", item.get("link_text"))
            print("Reasons:", item.get("reasons"))
            print()

    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Invalid URL leakage:", invalid_url_leakage)
    print("Duplicate URL leakage:", duplicate_url_leakage)
    print("Non-go.kr leakage:", non_go_kr_leakage)
    print("Cross-host leakage:", cross_host_leakage)
    print("Source endpoint leakage:", source_endpoint_leakage)
    print("Document candidate leakage:", document_candidate_leakage)
    print("Target query leakage:", target_query_leakage)
    print("Unsafe next-stage leakage:", unsafe_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")
    if not all_pass:
        failed = [name for name, passed in validations.items() if not passed]
        print("FAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError("UQQ700 competent authority historical navigation recovery regression failed")


if __name__ == "__main__":
    main()
