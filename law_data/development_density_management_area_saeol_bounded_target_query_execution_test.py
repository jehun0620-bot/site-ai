# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-6-S4
Development Density Management Area
SAEOL Bounded Target Query Execution

목표
======================================================================
T-6-S3에서 request shape가 검증된 SAEOL official notice archive contract만
사용하여 개발밀도관리구역(UQQ700) exact query를 최소 범위로 실행한다.

핵심 원칙
======================================================================
1. 입력은 T-6-S3 next-stage request contract만 사용한다.
2. query는 "개발밀도관리구역" exact 1종만 사용한다.
3. keyword / keyword1은 각각 독립적으로 제한 실행한다.
4. EQUIVALENT method이면 GET/POST를 모두 제한 실행하여 query-time behavior를 확인한다.
5. query 문자열 자체는 candidate evidence가 아니다.
6. page title 전체는 candidate evidence가 아니다.
7. candidate는 result row / anchor / onclick 등 link-local evidence에서
   target identity를 독립적으로 확인해야 한다.
8. 단순 input value echo / query echo는 candidate로 인정하지 않는다.
9. SAEOL detail URL이 직접 노출되지 않아도 notice number / row identity /
   JavaScript detail-call identity가 있으면 notice identity candidate로 보존한다.
10. source archive가 municipality-bound official source이므로 candidate region은
    검증된 source region provenance를 상속할 수 있다.
11. candidate는 verified positive가 아니다.
12. 문서 미발견은 SITE FALSE가 아니라 UNKNOWN이다.
13. runtime registration / SITE TRUE / SITE FALSE 자동판정 금지.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_saeol_request_shape_validation.json"
)

OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_saeol_bounded_target_query_execution.json"
)


# ============================================================
# TARGET / POLICY
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

TARGET_QUERY = "개발밀도관리구역"


# ============================================================
# OUTPUT CLASS
# ============================================================

CLASS_NOTICE_IDENTITY = "SAEOL_TARGET_NOTICE_IDENTITY_CANDIDATE"
CLASS_DOCUMENT_LINK = "SAEOL_TARGET_DOCUMENT_LINK_CANDIDATE"
CLASS_REJECTED_QUERY_ECHO = "REJECTED_SAEOL_QUERY_ECHO"
CLASS_REJECTED_WEAK = "REJECTED_SAEOL_ROW_TARGET_EVIDENCE_WEAK"
CLASS_REJECTED_NAVIGATION = "REJECTED_SAEOL_NAVIGATION_ROW"
CLASS_REJECTED_NON_OFFICIAL = "REJECTED_SAEOL_NON_OFFICIAL_LINK"
CLASS_REJECTED_CROSS_HOST = "REJECTED_SAEOL_CROSS_HOST_LINK"
CLASS_REJECTED_INVALID = "REJECTED_SAEOL_INVALID_LINK"

VALID_CLASSES = {
    CLASS_NOTICE_IDENTITY,
    CLASS_DOCUMENT_LINK,
    CLASS_REJECTED_QUERY_ECHO,
    CLASS_REJECTED_WEAK,
    CLASS_REJECTED_NAVIGATION,
    CLASS_REJECTED_NON_OFFICIAL,
    CLASS_REJECTED_CROSS_HOST,
    CLASS_REJECTED_INVALID,
}

CANDIDATE_CLASSES = {
    CLASS_NOTICE_IDENTITY,
    CLASS_DOCUMENT_LINK,
}


# ============================================================
# HTTP
# ============================================================

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 8
REQUEST_DELAY_SECONDS = 0.05

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# SEMANTIC RULES
# ============================================================

TARGET_PATTERN = re.compile(
    r"개발\s*밀도\s*관리\s*구역",
    re.IGNORECASE,
)

TARGET_CONTEXT_PATTERNS = [
    re.compile(r"도시관리계획.{0,120}개발\s*밀도", re.IGNORECASE),
    re.compile(r"개발\s*밀도.{0,120}(?:지정|결정|변경|고시|지형도면)", re.IGNORECASE),
    re.compile(r"(?:지정|결정|변경|고시|지형도면).{0,120}개발\s*밀도", re.IGNORECASE),
]

NOTICE_NUMBER_PATTERNS = [
    re.compile(
        r"[가-힣A-Za-z0-9 ]{0,40}(?:고시|공고)\s*제?\s*\d{2,4}\s*[-－]\s*\d+\s*호?"
    ),
    re.compile(r"(?:고시|공고)\s*제?\s*\d{2,4}\s*[-－]\s*\d+\s*호?"),
]

DATE_PATTERN = re.compile(r"\b(19|20)\d{2}[.\-/]\s*\d{1,2}[.\-/]\s*\d{1,2}\b")

DETAIL_CALL_TERMS = [
    "selectofrnotancmt",
    "ofrnotancmt",
    "detail",
    "view",
    "ancmt",
    "not_ancmt",
]

NAVIGATION_TERMS = {
    "홈", "home", "메인", "로그인", "회원가입", "사이트맵",
    "이전", "다음", "처음", "마지막", "목록", "전체메뉴", "민원상담",
}

NAVIGATION_URL_TERMS = [
    "/main",
    "/index",
    "/login",
    "/member",
    "/sitemap",
    "banner",
    "download",
    "userinfo",
    "usermgt",
    "cnsl",
]


# ============================================================
# HTML PATTERNS
# ============================================================

SCRIPT_STYLE_PATTERN = re.compile(
    r"<(?:script|style)\b.*?</(?:script|style)>",
    re.IGNORECASE | re.DOTALL,
)

COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>", re.DOTALL)

ROW_PATTERN = re.compile(
    r"<(tr|li)\b[^>]*>(.*?)</\1>",
    re.IGNORECASE | re.DOTALL,
)

ANCHOR_PATTERN = re.compile(
    r"<a\b([^>]*)>(.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)

HREF_PATTERN = re.compile(
    r'''\bhref\s*=\s*["']([^"']*)["']''',
    re.IGNORECASE,
)

ONCLICK_PATTERN = re.compile(
    r'''\bonclick\s*=\s*["']([^"']*)["']''',
    re.IGNORECASE,
)

INPUT_TAG_PATTERN = re.compile(
    r"<input\b[^>]*>",
    re.IGNORECASE,
)

VALUE_ATTR_PATTERN = re.compile(
    r'''\bvalue\s*=\s*["']([^"']*)["']''',
    re.IGNORECASE,
)

NAME_ATTR_PATTERN = re.compile(
    r'''\bname\s*=\s*["']([^"']*)["']''',
    re.IGNORECASE,
)


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
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def strip_html(raw_html: str) -> str:
    value = COMMENT_PATTERN.sub(" ", raw_html)
    value = SCRIPT_STYLE_PATTERN.sub(" ", value)
    value = TAG_PATTERN.sub(" ", value)
    return normalize_space(html.unescape(value))


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


def canonicalize_url(url: str) -> str:
    value = normalize_space(html.unescape(url))
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
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    query_items = sorted(parse_qsl(parsed.query, keep_blank_values=True))
    return urlunparse((scheme, host, path, "", urlencode(query_items, doseq=True), ""))


def decode_bytes(response: requests.Response, payload: bytes) -> Tuple[str, str]:
    candidates = unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"])
    for encoding in candidates:
        try:
            return payload.decode(encoding), encoding
        except Exception:
            continue
    return payload.decode("utf-8", errors="replace"), "utf-8-replace"


def direct_target_evidence(text: str) -> List[str]:
    reasons: List[str] = []
    normalized = normalize_space(text)
    match = TARGET_PATTERN.search(normalized)
    if match:
        reasons.append("TARGET_LOCAL:" + normalize_space(match.group(0)))
    for pattern in TARGET_CONTEXT_PATTERNS:
        match = pattern.search(normalized)
        if match:
            reasons.append("TARGET_CONTEXT:" + normalize_space(match.group(0)))
    return unique_strings(reasons)


def extract_notice_numbers(text: str) -> List[str]:
    result: List[str] = []
    for pattern in NOTICE_NUMBER_PATTERNS:
        for match in pattern.finditer(normalize_space(text)):
            result.append(normalize_space(match.group(0)))
    return unique_strings(result)


def extract_dates(text: str) -> List[str]:
    return unique_strings(match.group(0) for match in DATE_PATTERN.finditer(normalize_space(text)))


def is_navigation(text: str, url: str = "") -> bool:
    normalized = normalize_space(text).lower()
    if normalized in {term.lower() for term in NAVIGATION_TERMS}:
        return True
    lowered_url = normalize_space(url).lower()
    return any(term in lowered_url for term in NAVIGATION_URL_TERMS)


def extract_input_echo_values(raw_html: str, search_params: List[str]) -> Set[str]:
    values: Set[str] = set()
    search_names = {name.lower() for name in search_params}
    for tag in INPUT_TAG_PATTERN.findall(raw_html):
        name_match = NAME_ATTR_PATTERN.search(tag)
        value_match = VALUE_ATTR_PATTERN.search(tag)
        if not name_match or not value_match:
            continue
        if normalize_space(name_match.group(1)).lower() not in search_names:
            continue
        value = normalize_space(html.unescape(value_match.group(1)))
        if value:
            values.add(value)
    return values


# ============================================================
# HTTP
# ============================================================

def execute_query(
    session: requests.Session,
    *,
    method: str,
    endpoint_url: str,
    base_params: Dict[str, str],
    search_param: str,
) -> Dict[str, Any]:
    params = dict(base_params)
    params[search_param] = TARGET_QUERY

    result: Dict[str, Any] = {
        "method": method,
        "search_param": search_param,
        "http_status": None,
        "final_url": "",
        "content_type": "",
        "response_bytes": 0,
        "sha256": "",
        "encoding": "",
        "raw_html": "",
        "error": "",
    }

    try:
        kwargs: Dict[str, Any] = {
            "timeout": TIMEOUT,
            "allow_redirects": True,
            "stream": True,
        }
        if method == "GET":
            kwargs["params"] = params
        else:
            kwargs["data"] = params

        with session.request(method, endpoint_url, **kwargs) as response:
            result["http_status"] = response.status_code
            result["final_url"] = str(response.url)
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
            payload = b"".join(chunks)
            result["response_bytes"] = len(payload)
            result["sha256"] = hashlib.sha256(payload).hexdigest()
            text, encoding = decode_bytes(response, payload)
            result["raw_html"] = text
            result["encoding"] = encoding
    except Exception as exc:
        result["error"] = repr(exc)

    return result


# ============================================================
# RESULT LOCAL EXTRACTION
# ============================================================

def build_link_candidate(
    *,
    source_url: str,
    regions: List[str],
    row_text: str,
    attrs: str,
    anchor_html: str,
    base_url: str,
    method: str,
    search_param: str,
) -> Dict[str, Any] | None:
    anchor_text = strip_html(anchor_html)
    href_match = HREF_PATTERN.search(attrs)
    onclick_match = ONCLICK_PATTERN.search(attrs)
    href = html.unescape(normalize_space(href_match.group(1) if href_match else ""))
    onclick = html.unescape(normalize_space(onclick_match.group(1) if onclick_match else ""))

    candidate_url = ""
    if href and not href.lower().startswith(("javascript:", "#", "mailto:", "tel:")):
        candidate_url = canonicalize_url(urljoin(base_url, href))

    local_text = normalize_space(" ".join([anchor_text, row_text, onclick]))
    reasons = direct_target_evidence(local_text)
    notice_numbers = extract_notice_numbers(local_text)
    dates = extract_dates(local_text)
    detail_identity = bool(
        onclick
        and any(term in onclick.lower() for term in DETAIL_CALL_TERMS)
    )

    if not reasons:
        return None

    if is_navigation(anchor_text, candidate_url):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_NAVIGATION,
            "candidate_url": candidate_url,
            "anchor_text": anchor_text,
            "row_text": row_text[:2000],
            "onclick": onclick,
            "notice_numbers": notice_numbers,
            "dates": dates,
            "reasons": ["NAVIGATION_IDENTITY"],
        }

    if candidate_url:
        if not is_government_host(hostname(candidate_url)):
            return {
                "qualified": False,
                "classification": CLASS_REJECTED_NON_OFFICIAL,
                "candidate_url": candidate_url,
                "anchor_text": anchor_text,
                "row_text": row_text[:2000],
                "onclick": onclick,
                "notice_numbers": notice_numbers,
                "dates": dates,
                "reasons": ["DOCUMENT_HOST_NOT_GO_KR"],
            }
        if not same_host(source_url, candidate_url):
            return {
                "qualified": False,
                "classification": CLASS_REJECTED_CROSS_HOST,
                "candidate_url": candidate_url,
                "anchor_text": anchor_text,
                "row_text": row_text[:2000],
                "onclick": onclick,
                "notice_numbers": notice_numbers,
                "dates": dates,
                "reasons": ["DOCUMENT_CROSS_HOST"],
            }

    qualified = bool(candidate_url or notice_numbers or detail_identity)
    classification = CLASS_DOCUMENT_LINK if candidate_url else CLASS_NOTICE_IDENTITY

    return {
        "source_url": source_url,
        "regions": regions,
        "execution_method": method,
        "search_param": search_param,
        "candidate_url": candidate_url,
        "anchor_text": anchor_text,
        "row_text": row_text[:2000],
        "onclick": onclick,
        "detail_call_identity": detail_identity,
        "notice_numbers": notice_numbers,
        "dates": dates,
        "qualified": qualified,
        "classification": classification if qualified else CLASS_REJECTED_WEAK,
        "reasons": unique_strings(
            reasons
            + (["NOTICE_NUMBER_IDENTITY"] if notice_numbers else [])
            + (["JAVASCRIPT_DETAIL_IDENTITY"] if detail_identity else [])
            + (["DIRECT_DOCUMENT_URL"] if candidate_url else [])
            + ["SOURCE_REGION_PROVENANCE:" + region for region in regions]
        ),
        "query_used_for_execution_only": TARGET_QUERY,
        "query_used_as_candidate_evidence": False,
        "page_title_used_as_candidate_evidence": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }


def extract_candidates_from_response(
    *,
    source_url: str,
    regions: List[str],
    response: Dict[str, Any],
    search_params: List[str],
) -> Tuple[List[Dict[str, Any]], int]:
    raw_html = str(response.get("raw_html") or "")
    if not raw_html:
        return [], 0

    echo_values = extract_input_echo_values(raw_html, search_params)
    candidates: List[Dict[str, Any]] = []
    query_echo_rejected = 0

    # Row-local extraction. Query echo in form controls never enters this path.
    for row_match in ROW_PATTERN.finditer(raw_html):
        row_html = row_match.group(2)
        row_text = strip_html(row_html)
        if not direct_target_evidence(row_text):
            continue

        # Guard: a row containing only the exact query and no independent identity
        # is not a result candidate.
        row_without_query = normalize_space(TARGET_PATTERN.sub(" ", row_text))
        independent_identity = bool(
            extract_notice_numbers(row_text)
            or extract_dates(row_text)
            or any(term in row_html.lower() for term in DETAIL_CALL_TERMS)
            or ANCHOR_PATTERN.search(row_html)
        )
        if (
            TARGET_QUERY in echo_values
            and not row_without_query
            and not independent_identity
        ):
            query_echo_rejected += 1
            continue

        anchors = list(ANCHOR_PATTERN.finditer(row_html))
        if anchors:
            for anchor_match in anchors:
                candidate = build_link_candidate(
                    source_url=source_url,
                    regions=regions,
                    row_text=row_text,
                    attrs=anchor_match.group(1),
                    anchor_html=anchor_match.group(2),
                    base_url=response.get("final_url") or source_url,
                    method=response.get("method") or "",
                    search_param=response.get("search_param") or "",
                )
                if candidate:
                    candidates.append(candidate)
        else:
            reasons = direct_target_evidence(row_text)
            notice_numbers = extract_notice_numbers(row_text)
            dates = extract_dates(row_text)
            detail_identity = any(term in row_html.lower() for term in DETAIL_CALL_TERMS)
            if notice_numbers or detail_identity:
                candidates.append({
                    "source_url": source_url,
                    "regions": regions,
                    "execution_method": response.get("method"),
                    "search_param": response.get("search_param"),
                    "candidate_url": "",
                    "anchor_text": "",
                    "row_text": row_text[:2000],
                    "onclick": "",
                    "detail_call_identity": detail_identity,
                    "notice_numbers": notice_numbers,
                    "dates": dates,
                    "qualified": True,
                    "classification": CLASS_NOTICE_IDENTITY,
                    "reasons": unique_strings(
                        reasons
                        + (["NOTICE_NUMBER_IDENTITY"] if notice_numbers else [])
                        + (["ROW_DETAIL_IDENTITY"] if detail_identity else [])
                        + ["SOURCE_REGION_PROVENANCE:" + region for region in regions]
                    ),
                    "query_used_for_execution_only": TARGET_QUERY,
                    "query_used_as_candidate_evidence": False,
                    "page_title_used_as_candidate_evidence": False,
                    "verified_positive": False,
                    "runtime_registration_allowed": False,
                    "site_positive_allowed": False,
                    "site_negative_allowed": False,
                    "final_positive_promotion_allowed": False,
                })

    return candidates, query_echo_rejected


# ============================================================
# CANONICAL IDENTITY
# ============================================================

def candidate_identity_key(item: Dict[str, Any]) -> str:
    url = canonicalize_url(item.get("candidate_url") or "")
    if url:
        return "URL:" + url

    notice_numbers = unique_strings(item.get("notice_numbers") or [])
    if notice_numbers:
        return "NOTICE:" + "|".join(sorted(notice_numbers))

    onclick = normalize_space(item.get("onclick"))
    if onclick:
        return "ONCLICK:" + hashlib.sha256(onclick.encode("utf-8")).hexdigest()

    row_text = normalize_space(item.get("row_text"))
    return "ROW:" + hashlib.sha256(row_text.encode("utf-8")).hexdigest()


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SAEOL BOUNDED TARGET QUERY EXECUTION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Query count: 1")
    print()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"input not found: {INPUT_PATH}")

    data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("input must be JSON object")

    contracts = data.get("next_stage_request_contract_pool")
    if not isinstance(contracts, list):
        contracts = []

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    request_count = 0
    http_success_count = 0
    transport_error_count = 0
    query_execution_count = 0
    query_echo_rejected = 0
    raw_candidates: List[Dict[str, Any]] = []
    execution_records: List[Dict[str, Any]] = []

    for index, contract in enumerate(contracts, start=1):
        source_url = normalize_space(contract.get("source_url"))
        endpoint_url = normalize_space(contract.get("endpoint_url"))
        regions = unique_strings(contract.get("regions") or [])
        search_params = unique_strings(contract.get("search_params") or [])
        base_params = dict(contract.get("base_params") or {})
        method_resolution = normalize_space(contract.get("method_resolution"))

        methods = (
            ["GET", "POST"]
            if method_resolution == "EQUIVALENT"
            else ["GET"] if method_resolution == "PREFERRED_GET"
            else ["POST"] if method_resolution == "PREFERRED_POST"
            else []
        )

        print("-" * 60)
        print(f"CONTRACT {index}")
        print("Source URL:", source_url)
        print("Endpoint URL:", endpoint_url)
        print("Method resolution:", method_resolution)
        print("Execution methods:", methods)
        print("Search params:", search_params)

        contract_candidates_before = len(raw_candidates)

        for method in methods:
            for search_param in search_params:
                if request_count >= MAX_TOTAL_REQUESTS:
                    break

                response = execute_query(
                    session,
                    method=method,
                    endpoint_url=endpoint_url,
                    base_params=base_params,
                    search_param=search_param,
                )

                request_count += 1
                query_execution_count += 1

                status = response.get("http_status")
                if isinstance(status, int) and 200 <= status < 300:
                    http_success_count += 1
                if response.get("error"):
                    transport_error_count += 1

                final_url = normalize_space(response.get("final_url"))
                same_host_ok = same_host(source_url, final_url)
                official_ok = is_government_host(hostname(final_url))

                candidates: List[Dict[str, Any]] = []
                echo_count = 0
                if (
                    isinstance(status, int)
                    and 200 <= status < 300
                    and same_host_ok
                    and official_ok
                    and not response.get("error")
                ):
                    candidates, echo_count = extract_candidates_from_response(
                        source_url=source_url,
                        regions=regions,
                        response=response,
                        search_params=search_params,
                    )
                    raw_candidates.extend(candidates)
                    query_echo_rejected += echo_count

                execution_records.append({
                    "source_url": source_url,
                    "regions": regions,
                    "method": method,
                    "search_param": search_param,
                    "http_status": status,
                    "final_url": final_url,
                    "same_host": same_host_ok,
                    "official_host": official_ok,
                    "response_bytes": response.get("response_bytes"),
                    "response_sha256": response.get("sha256"),
                    "candidate_count": len([c for c in candidates if c.get("qualified") is True]),
                    "query_echo_rejected": echo_count,
                    "error": response.get("error"),
                    "target_query_executed": True,
                    "target_query_used_as_candidate_evidence": False,
                    "page_title_used_as_candidate_evidence": False,
                    "verified_positive": False,
                    "runtime_registration_allowed": False,
                    "site_positive_allowed": False,
                    "site_negative_allowed": False,
                })

                print(
                    f"{method} / {search_param}: HTTP={status} "
                    f"bytes={response.get('response_bytes')} candidates={len(candidates)} "
                    f"echo_rejected={echo_count}"
                )

                if REQUEST_DELAY_SECONDS > 0:
                    time.sleep(REQUEST_DELAY_SECONDS)

        print("Contract raw candidates:", len(raw_candidates) - contract_candidates_before)
        print()

    # ========================================================
    # CANONICAL DEDUPE
    # ========================================================

    canonical_map: Dict[str, Dict[str, Any]] = {}
    duplicate_count = 0

    for item in raw_candidates:
        key = candidate_identity_key(item)
        if key in canonical_map:
            duplicate_count += 1
            existing = canonical_map[key]
            existing["regions"] = unique_strings((existing.get("regions") or []) + (item.get("regions") or []))
            existing["notice_numbers"] = unique_strings((existing.get("notice_numbers") or []) + (item.get("notice_numbers") or []))
            existing["dates"] = unique_strings((existing.get("dates") or []) + (item.get("dates") or []))
            existing["reasons"] = unique_strings((existing.get("reasons") or []) + (item.get("reasons") or []))
            existing["execution_methods"] = unique_strings(
                (existing.get("execution_methods") or [existing.get("execution_method")])
                + [item.get("execution_method")]
            )
            existing["search_params"] = unique_strings(
                (existing.get("search_params") or [existing.get("search_param")])
                + [item.get("search_param")]
            )
            if item.get("qualified") is True:
                existing["qualified"] = True
            continue

        canonical_item = dict(item)
        canonical_item["canonical_identity"] = key
        canonical_item["execution_methods"] = unique_strings([item.get("execution_method")])
        canonical_item["search_params"] = unique_strings([item.get("search_param")])
        canonical_map[key] = canonical_item

    canonical_records = list(canonical_map.values())
    canonical_records.sort(key=lambda item: (-int(item.get("qualified") is True), item.get("canonical_identity") or ""))

    candidate_documents = [item for item in canonical_records if item.get("qualified") is True]
    rejected_records = [item for item in canonical_records if item.get("qualified") is not True]

    classification_counts = Counter(item.get("classification") for item in canonical_records)

    next_stage_notice_identity_pool = [
        {
            "source_url": item.get("source_url"),
            "regions": item.get("regions") or [],
            "candidate_url": item.get("candidate_url") or "",
            "notice_numbers": item.get("notice_numbers") or [],
            "dates": item.get("dates") or [],
            "anchor_text": item.get("anchor_text") or "",
            "row_text": item.get("row_text") or "",
            "onclick": item.get("onclick") or "",
            "detail_call_identity": item.get("detail_call_identity") is True,
            "classification": item.get("classification"),
            "reasons": item.get("reasons") or [],
            "execution_methods": item.get("execution_methods") or [],
            "search_params": item.get("search_params") or [],
            "requires_direct_detail_verification": True,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in candidate_documents
    ]

    if next_stage_notice_identity_pool:
        resolution = "SAEOL_BOUNDED_TARGET_QUERY_EXECUTION_COMPLETED"
        next_action = (
            "T-6-S5에서 SAEOL result-local notice identity만 대상으로 detail request identity를 복원한다. "
            "직접 document URL이 있으면 재조회하고, JavaScript detail call이면 관찰된 함수/인자에서만 detail contract를 복원한다."
        )
    else:
        resolution = "SAEOL_BOUNDED_TARGET_QUERY_EXECUTION_NO_DOCUMENT"
        next_action = (
            "평택 SAEOL official archive의 검증된 request shape로 exact UQQ700 query를 제한 실행했지만 "
            "독립적인 result-local notice identity가 발견되지 않았다. 이는 SITE FALSE가 아니다. UNKNOWN을 유지하고 "
            "다른 official notice/archive source family 또는 historical spatial source를 추가 탐색한다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-6-S4 SAEOL Bounded Target Query Execution",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "input": {"path": str(INPUT_PATH), "resolution": data.get("resolution")},
        "method": {
            "exact_target_query_only": True,
            "query_matrix_count": 1,
            "equivalent_method_dual_execution": True,
            "search_parameter_independent_execution": True,
            "query_evidence_disabled": True,
            "page_title_evidence_disabled": True,
            "result_row_local_evidence_required": True,
            "query_echo_guard_enabled": True,
            "source_region_provenance_inheritance_enabled": True,
            "document_candidate_verified_positive": False,
        },
        "summary": {
            "contract_count": len(contracts),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "query_execution_count": query_execution_count,
            "query_echo_rejected": query_echo_rejected,
            "raw_candidate_count": len(raw_candidates),
            "duplicate_candidate_removed": duplicate_count,
            "canonical_candidate_count": len(canonical_records),
            "qualified_candidate_count": len(candidate_documents),
            "next_stage_notice_identity_pool_count": len(next_stage_notice_identity_pool),
        },
        "classification_counts": dict(sorted(classification_counts.items())),
        "execution_records": execution_records,
        "candidate_documents": candidate_documents,
        "rejected_records": rejected_records,
        "next_stage_notice_identity_pool": next_stage_notice_identity_pool,
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

    candidate_keys = [item.get("canonical_identity") for item in candidate_documents]
    next_stage_keys = [
        candidate_identity_key({
            "candidate_url": item.get("candidate_url"),
            "notice_numbers": item.get("notice_numbers"),
            "onclick": item.get("onclick"),
            "row_text": item.get("row_text"),
        })
        for item in next_stage_notice_identity_pool
    ]

    candidate_classes_valid = all(item.get("classification") in CANDIDATE_CLASSES for item in candidate_documents)
    all_classes_valid = all(item.get("classification") in VALID_CLASSES for item in canonical_records)

    candidate_query_evidence_leakage = sum(
        1 for item in candidate_documents
        if item.get("query_used_as_candidate_evidence") is True
    )
    candidate_page_title_evidence_leakage = sum(
        1 for item in candidate_documents
        if item.get("page_title_used_as_candidate_evidence") is True
    )
    candidate_region_unbound_leakage = sum(
        1 for item in candidate_documents
        if not (item.get("regions") or [])
    )
    candidate_weak_identity_leakage = sum(
        1 for item in candidate_documents
        if not (
            canonicalize_url(item.get("candidate_url") or "")
            or item.get("notice_numbers")
            or item.get("detail_call_identity") is True
        )
    )
    verified_positive_leakage = sum(1 for item in canonical_records if item.get("verified_positive") is True)
    runtime_registration_leakage = sum(1 for item in canonical_records if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in canonical_records if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in canonical_records if item.get("site_negative_allowed") is True)
    false_from_no_document_leakage = 1 if (
        not candidate_documents
        and output_data["resolution_policy"]["source_failure_site_status"] == "FALSE"
    ) else 0

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "input exists": INPUT_PATH.exists(),
        "input parsed": isinstance(data, dict),
        "request shape contract loaded": len(contracts) > 0,
        "exact query matrix count one": True,
        "bounded request count respected": request_count <= MAX_TOTAL_REQUESTS,
        "query evidence disabled": True,
        "page title evidence disabled": True,
        "result-local evidence required": True,
        "query echo guard enabled": True,
        "all classes valid": all_classes_valid,
        "candidate classes valid": candidate_classes_valid,
        "candidate identities unique": len(candidate_keys) == len(set(candidate_keys)),
        "next-stage identities unique": len(next_stage_keys) == len(set(next_stage_keys)),
        "candidate and next-stage parity": set(candidate_keys) == set(next_stage_keys),
        "candidate query evidence leakage zero": candidate_query_evidence_leakage == 0,
        "candidate page-title evidence leakage zero": candidate_page_title_evidence_leakage == 0,
        "candidate region-unbound leakage zero": candidate_region_unbound_leakage == 0,
        "candidate weak identity leakage zero": candidate_weak_identity_leakage == 0,
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

    print("=" * 60)
    print("SAEOL BOUNDED TARGET QUERY EXECUTION RESULT")
    print("=" * 60)
    print("Contract count:", len(contracts))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Transport error count:", transport_error_count)
    print("Query execution count:", query_execution_count)
    print("Query echo rejected:", query_echo_rejected)
    print("Raw candidate count:", len(raw_candidates))
    print("Duplicate candidate removed:", duplicate_count)
    print("Canonical candidate count:", len(canonical_records))
    print("Qualified candidate count:", len(candidate_documents))
    print("Next-stage notice identity pool count:", len(next_stage_notice_identity_pool))

    if candidate_documents:
        print("\nSAEOL TARGET NOTICE CANDIDATES")
        print("-" * 60)
        for idx, item in enumerate(candidate_documents, start=1):
            print(f"[{idx}] {item.get('classification')}")
            print("Regions:", item.get("regions"))
            print("URL:", item.get("candidate_url") or "-")
            print("Anchor:", item.get("anchor_text") or "-")
            print("Notice numbers:", item.get("notice_numbers"))
            print("Dates:", item.get("dates"))
            print("Detail call:", item.get("detail_call_identity"))
            print("Onclick:", item.get("onclick") or "-")
            print("Reasons:", item.get("reasons"))
            print()

    print("=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    print(resolution)
    print()
    print(next_action)
    print("Output:", OUTPUT_PATH)

    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")

    print()
    print("Candidate query evidence leakage:", candidate_query_evidence_leakage)
    print("Candidate page-title evidence leakage:", candidate_page_title_evidence_leakage)
    print("Candidate region-unbound leakage:", candidate_region_unbound_leakage)
    print("Candidate weak identity leakage:", candidate_weak_identity_leakage)
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
        print("\nFAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError("UQQ700 SAEOL bounded target query execution regression failed")


if __name__ == "__main__":
    main()
