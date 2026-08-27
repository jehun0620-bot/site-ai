# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-10
Development Density Management Area
Current Canonical Bounded Target Query Execution

목표
======================================================================
T-9에서 query effectiveness가 실제로 확인된 성남시 current canonical
고시공고 검색 계약만 사용하여 개발밀도관리구역(UQQ700) exact query를
최소 범위로 실행한다.

핵심 원칙
======================================================================
1. 입력은 T-9 effective_search_contract_pool만 사용한다.
2. query는 "개발밀도관리구역" exact 1종만 사용한다.
3. T-9에서 검증된 실제 action/method/field만 사용한다.
4. 실행 직전 live form contract를 다시 확인하고 fresh hidden params를 사용한다.
5. query 문자열 자체는 candidate evidence가 아니다.
6. page title / 검색 input echo / 검색조건 안내문은 candidate evidence가 아니다.
7. candidate는 result row/link-local evidence에서 target identity가 독립적으로
   확인되어야 한다.
8. target identity 외에 document identity가 추가로 필요하다.
   - detail/document URL
   - 고시/공고 번호
   - 결과 row의 등록일/게재기간 등 문서 메타데이터
9. source endpoint 자체 / navigation link / global page link는 candidate가 아니다.
10. source가 municipality-bound official archive이므로 region은 검증된 source
    provenance를 상속할 수 있다.
11. candidate는 U-stage direct document verification 전까지 verified positive가 아니다.
12. 문서 미발견은 SITE FALSE가 아니라 UNKNOWN이다.
13. runtime registration / SITE TRUE / SITE FALSE 자동판정 금지.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests


# ============================================================
# PATH / TARGET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_current_canonical_query_effectiveness_validation.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_current_canonical_bounded_target_query_execution.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False
TARGET_QUERY = "개발밀도관리구역"

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 4
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


# ============================================================
# CLASSES
# ============================================================

CLASS_NOTICE_DOCUMENT = "CURRENT_CANONICAL_TARGET_NOTICE_DOCUMENT_CANDIDATE"
CLASS_NOTICE_IDENTITY = "CURRENT_CANONICAL_TARGET_NOTICE_IDENTITY_CANDIDATE"
CLASS_REJECTED_QUERY_ECHO = "REJECTED_CURRENT_CANONICAL_QUERY_ECHO"
CLASS_REJECTED_WEAK = "REJECTED_CURRENT_CANONICAL_DOCUMENT_IDENTITY_WEAK"
CLASS_REJECTED_NAVIGATION = "REJECTED_CURRENT_CANONICAL_NAVIGATION"
CLASS_REJECTED_SOURCE_ENDPOINT = "REJECTED_CURRENT_CANONICAL_SOURCE_ENDPOINT"
CLASS_REJECTED_NON_OFFICIAL = "REJECTED_CURRENT_CANONICAL_NON_OFFICIAL_LINK"
CLASS_REJECTED_CROSS_HOST = "REJECTED_CURRENT_CANONICAL_CROSS_HOST_LINK"
CLASS_REJECTED_INVALID = "REJECTED_CURRENT_CANONICAL_INVALID_LINK"

VALID_CLASSES = {
    CLASS_NOTICE_DOCUMENT,
    CLASS_NOTICE_IDENTITY,
    CLASS_REJECTED_QUERY_ECHO,
    CLASS_REJECTED_WEAK,
    CLASS_REJECTED_NAVIGATION,
    CLASS_REJECTED_SOURCE_ENDPOINT,
    CLASS_REJECTED_NON_OFFICIAL,
    CLASS_REJECTED_CROSS_HOST,
    CLASS_REJECTED_INVALID,
}
CANDIDATE_CLASSES = {
    CLASS_NOTICE_DOCUMENT,
    CLASS_NOTICE_IDENTITY,
}


# ============================================================
# SEMANTIC PATTERNS
# ============================================================

TARGET_PATTERN = re.compile(r"개발\s*밀도\s*관리\s*구역", re.IGNORECASE)
TARGET_CONTEXT_PATTERNS = [
    re.compile(r"도시관리계획.{0,120}개발\s*밀도", re.IGNORECASE),
    re.compile(r"개발\s*밀도.{0,120}(?:지정|결정|변경|고시|지형도면)", re.IGNORECASE),
    re.compile(r"(?:지정|결정|변경|고시|지형도면).{0,120}개발\s*밀도", re.IGNORECASE),
]
NOTICE_NUMBER_PATTERNS = [
    re.compile(r"[가-힣A-Za-z0-9 ]{0,50}(?:고시|공고)\s*제?\s*\d{2,4}\s*[-－]\s*\d+\s*호?"),
    re.compile(r"(?:고시|공고)\s*제?\s*\d{2,4}\s*[-－]\s*\d+\s*호?"),
]
DATE_PATTERN = re.compile(r"\b(?:19|20)\d{2}[.\-/]\s*\d{1,2}[.\-/]\s*\d{1,2}\b")
DOCUMENT_META_TERMS = [
    "고시공고번호", "고시번호", "공고번호", "등록일", "게재기간", "게시일",
    "담당부서", "작성일", "첨부파일",
]
DETAIL_URL_TERMS = [
    "/view", "/detail", "/read", "bbsview", "board/view", "ntt/view",
    "seq=", "idx=", "no=", "nttid=", "boardseq=", "postno=",
]
NAVIGATION_TERMS = {
    "홈", "home", "메인", "로그인", "회원가입", "사이트맵", "이전", "다음",
    "처음", "마지막", "목록", "전체메뉴", "검색", "검색하기", "민원상담",
}
NAVIGATION_URL_TERMS = [
    "/login", "/member", "/sitemap", "/main", "javascript:void", "#",
]
NO_RESULT_TERMS = [
    "검색 결과가 없습니다", "검색결과가 없습니다", "등록된 게시물이 없습니다",
    "조회된 결과가 없습니다", "게시물이 없습니다",
]


# ============================================================
# HTML PATTERNS
# ============================================================

COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.IGNORECASE | re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>", re.DOTALL)
ROW_PATTERN = re.compile(r"<(tr|li)\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
ANCHOR_PATTERN = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.IGNORECASE | re.DOTALL)
HREF_PATTERN = re.compile(r'''\bhref\s*=\s*["']([^"']*)["']''', re.IGNORECASE)
ONCLICK_PATTERN = re.compile(r'''\bonclick\s*=\s*["']([^"']*)["']''', re.IGNORECASE)
INPUT_TAG_PATTERN = re.compile(r"<input\b[^>]*>", re.IGNORECASE)
NAME_ATTR_PATTERN = re.compile(r'''\bname\s*=\s*["']([^"']*)["']''', re.IGNORECASE)
VALUE_ATTR_PATTERN = re.compile(r'''\bvalue\s*=\s*["']([^"']*)["']''', re.IGNORECASE)


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


def strip_html(raw_html: str) -> str:
    value = COMMENT_PATTERN.sub(" ", raw_html)
    value = SCRIPT_STYLE_PATTERN.sub(" ", value)
    value = TAG_PATTERN.sub(" ", value)
    return normalize_space(html.unescape(value))


def canonicalize_url(url: str) -> str:
    value = html.unescape(normalize_space(url))
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


def direct_target_evidence(text: str) -> List[str]:
    normalized = normalize_space(text)
    reasons: List[str] = []
    match = TARGET_PATTERN.search(normalized)
    if match:
        reasons.append("TARGET_LOCAL:" + normalize_space(match.group(0)))
    for pattern in TARGET_CONTEXT_PATTERNS:
        match = pattern.search(normalized)
        if match:
            reasons.append("TARGET_CONTEXT:" + normalize_space(match.group(0)))
    return unique_strings(reasons)


def extract_notice_numbers(text: str) -> List[str]:
    values: List[str] = []
    for pattern in NOTICE_NUMBER_PATTERNS:
        for match in pattern.finditer(normalize_space(text)):
            values.append(normalize_space(match.group(0)))
    return unique_strings(values)


def extract_dates(text: str) -> List[str]:
    return unique_strings(match.group(0) for match in DATE_PATTERN.finditer(normalize_space(text)))


def is_navigation(text: str, url: str) -> bool:
    normalized = normalize_space(text).lower()
    if normalized in {term.lower() for term in NAVIGATION_TERMS}:
        return True
    lowered_url = normalize_space(url).lower()
    return any(term in lowered_url for term in NAVIGATION_URL_TERMS)


def has_detail_url_identity(url: str) -> bool:
    lowered = normalize_space(url).lower()
    return bool(lowered) and any(term in lowered for term in DETAIL_URL_TERMS)


def source_endpoint_equivalent(candidate_url: str, source_url: str, action_url: str) -> bool:
    candidate = canonicalize_url(candidate_url)
    if not candidate:
        return False
    source = canonicalize_url(source_url)
    action = canonicalize_url(action_url)
    if candidate in {source, action}:
        return True
    try:
        cp = urlparse(candidate)
        sp = urlparse(source)
        ap = urlparse(action)
        return (cp.hostname, cp.path.rstrip("/")) in {
            (sp.hostname, sp.path.rstrip("/")),
            (ap.hostname, ap.path.rstrip("/")),
        } and not has_detail_url_identity(candidate)
    except Exception:
        return False


def extract_search_echo_values(raw_html: str, field_name: str) -> Set[str]:
    values: Set[str] = set()
    for tag in INPUT_TAG_PATTERN.findall(raw_html):
        name_match = NAME_ATTR_PATTERN.search(tag)
        value_match = VALUE_ATTR_PATTERN.search(tag)
        if not name_match or not value_match:
            continue
        if normalize_space(name_match.group(1)).lower() != normalize_space(field_name).lower():
            continue
        value = normalize_space(html.unescape(value_match.group(1)))
        if value:
            values.add(value)
    return values


# ============================================================
# LIVE FORM RECONFIRMATION
# ============================================================

def attrs_to_dict(attrs: List[Tuple[str, Optional[str]]]) -> Dict[str, str]:
    return {
        normalize_space(k).lower(): normalize_space(v)
        for k, v in attrs
        if normalize_space(k)
    }


class LiveFormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: List[Dict[str, Any]] = []
        self.current: Optional[Dict[str, Any]] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attr = attrs_to_dict(attrs)
        if tag == "form":
            if self.current is not None:
                self.forms.append(self.current)
            self.current = {
                "action_raw": attr.get("action", ""),
                "method": (attr.get("method", "GET") or "GET").upper(),
                "controls": [],
            }
            return
        if self.current is None:
            return
        if tag == "input":
            self.current["controls"].append({
                "type": (attr.get("type", "text") or "text").lower(),
                "name": attr.get("name", ""),
                "id": attr.get("id", ""),
                "value": attr.get("value", ""),
            })

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "form" and self.current is not None:
            self.forms.append(self.current)
            self.current = None

    def close(self) -> None:
        super().close()
        if self.current is not None:
            self.forms.append(self.current)
            self.current = None


def decode_bytes(response: requests.Response, payload: bytes) -> str:
    for encoding in unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"]):
        try:
            return payload.decode(encoding)
        except Exception:
            continue
    return payload.decode("utf-8", errors="replace")


def fetch_html(session: requests.Session, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"http_status": None, "final_url": "", "raw_html": "", "error": ""}
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result["http_status"] = response.status_code
            result["final_url"] = canonicalize_url(str(response.url))
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
            result["raw_html"] = decode_bytes(response, payload)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def reconfirm_contract(session: requests.Session, contract: Dict[str, Any]) -> Dict[str, Any]:
    source_url = canonicalize_url(contract.get("source_url") or "")
    expected_action = canonicalize_url(contract.get("action_url") or "")
    expected_method = normalize_space(contract.get("method")).upper()
    field_name = normalize_space(contract.get("field_name") or (contract.get("search_field") or {}).get("name"))
    fetched = fetch_html(session, source_url)
    result: Dict[str, Any] = {
        "http_status": fetched.get("http_status"),
        "reconfirmed": False,
        "source_url": source_url,
        "action_url": expected_action,
        "method": expected_method,
        "field_name": field_name,
        "hidden_params": {},
        "error": fetched.get("error") or "",
    }
    status = fetched.get("http_status")
    if fetched.get("error") or not isinstance(status, int) or not (200 <= status < 300):
        return result

    parser = LiveFormParser()
    parser.feed(str(fetched.get("raw_html") or ""))
    parser.close()
    final_url = fetched.get("final_url") or source_url

    for form in parser.forms:
        action = canonicalize_url(urljoin(final_url, normalize_space(form.get("action_raw")) or final_url))
        method = normalize_space(form.get("method") or "GET").upper()
        controls = form.get("controls") or []
        names = {
            normalize_space(control.get("name") or control.get("id"))
            for control in controls
            if normalize_space(control.get("name") or control.get("id"))
        }
        if action != expected_action or method != expected_method or field_name not in names:
            continue
        hidden: Dict[str, str] = {}
        for control in controls:
            if normalize_space(control.get("type")).lower() != "hidden":
                continue
            name = normalize_space(control.get("name"))
            if name:
                hidden[name] = normalize_space(control.get("value"))
        result["reconfirmed"] = True
        result["action_url"] = action
        result["method"] = method
        result["hidden_params"] = hidden
        return result
    return result


# ============================================================
# QUERY EXECUTION
# ============================================================

def execute_target_query(
    session: requests.Session,
    *,
    method: str,
    action_url: str,
    base_params: Dict[str, str],
    field_name: str,
) -> Dict[str, Any]:
    params = dict(base_params)
    params[field_name] = TARGET_QUERY
    result: Dict[str, Any] = {
        "http_status": None,
        "final_url": "",
        "content_type": "",
        "response_bytes": 0,
        "sha256": "",
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
        elif method == "POST":
            kwargs["data"] = params
        else:
            raise ValueError(f"unsupported method: {method}")
        with session.request(method, action_url, **kwargs) as response:
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
            payload = b"".join(chunks)
            result["response_bytes"] = len(payload)
            result["sha256"] = hashlib.sha256(payload).hexdigest()
            result["raw_html"] = decode_bytes(response, payload)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


# ============================================================
# RESULT-LOCAL CANDIDATE EXTRACTION
# ============================================================

def classify_row_link(
    *,
    source_url: str,
    action_url: str,
    regions: List[str],
    row_text: str,
    attrs: str,
    anchor_html: str,
    base_url: str,
    echo_values: Set[str],
) -> Optional[Dict[str, Any]]:
    anchor_text = strip_html(anchor_html)
    href_match = HREF_PATTERN.search(attrs)
    onclick_match = ONCLICK_PATTERN.search(attrs)
    href = html.unescape(normalize_space(href_match.group(1) if href_match else ""))
    onclick = html.unescape(normalize_space(onclick_match.group(1) if onclick_match else ""))

    candidate_url = ""
    if href and not href.lower().startswith(("javascript:", "#", "mailto:", "tel:")):
        candidate_url = canonicalize_url(urljoin(base_url, href))

    local_text = normalize_space(" ".join([anchor_text, row_text, onclick]))
    target_reasons = direct_target_evidence(local_text)
    if not target_reasons:
        return None

    if any(normalize_space(value) == normalize_space(anchor_text) == TARGET_QUERY for value in echo_values):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_QUERY_ECHO,
            "candidate_url": candidate_url,
            "anchor_text": anchor_text,
            "row_text": row_text[:2000],
            "reasons": ["SEARCH_INPUT_QUERY_ECHO"],
        }

    if any(term in row_text for term in NO_RESULT_TERMS):
        return None

    if is_navigation(anchor_text, candidate_url):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_NAVIGATION,
            "candidate_url": candidate_url,
            "anchor_text": anchor_text,
            "row_text": row_text[:2000],
            "reasons": ["NAVIGATION_IDENTITY"],
        }

    if candidate_url and not is_government_host(hostname(candidate_url)):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_NON_OFFICIAL,
            "candidate_url": candidate_url,
            "anchor_text": anchor_text,
            "row_text": row_text[:2000],
            "reasons": ["DOCUMENT_HOST_NOT_GO_KR"],
        }

    if candidate_url and not same_host(source_url, candidate_url):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_CROSS_HOST,
            "candidate_url": candidate_url,
            "anchor_text": anchor_text,
            "row_text": row_text[:2000],
            "reasons": ["DOCUMENT_CROSS_HOST"],
        }

    if candidate_url and source_endpoint_equivalent(candidate_url, source_url, action_url):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_SOURCE_ENDPOINT,
            "candidate_url": candidate_url,
            "anchor_text": anchor_text,
            "row_text": row_text[:2000],
            "reasons": ["SOURCE_ENDPOINT_PROMOTION_BLOCKED"],
        }

    notice_numbers = extract_notice_numbers(local_text)
    dates = extract_dates(local_text)
    meta_terms = unique_strings(term for term in DOCUMENT_META_TERMS if term in local_text)
    detail_url = has_detail_url_identity(candidate_url)
    onclick_detail = bool(onclick and any(term in onclick.lower() for term in ["view", "detail", "select", "bbs", "board", "seq", "idx", "no"] ))
    document_identity = bool(detail_url or notice_numbers or (dates and meta_terms) or onclick_detail)

    if not document_identity:
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_WEAK,
            "candidate_url": candidate_url,
            "anchor_text": anchor_text,
            "row_text": row_text[:2000],
            "onclick": onclick,
            "notice_numbers": notice_numbers,
            "dates": dates,
            "document_meta_terms": meta_terms,
            "reasons": unique_strings(target_reasons + ["DOCUMENT_IDENTITY_REQUIRED"]),
        }

    classification = CLASS_NOTICE_DOCUMENT if candidate_url else CLASS_NOTICE_IDENTITY
    reasons = list(target_reasons)
    if detail_url:
        reasons.append("DETAIL_URL_IDENTITY")
    if notice_numbers:
        reasons.append("NOTICE_NUMBER_IDENTITY")
    if dates:
        reasons.append("DATE_IDENTITY")
    if meta_terms:
        reasons.append("DOCUMENT_META_IDENTITY")
    if onclick_detail:
        reasons.append("ONCLICK_DOCUMENT_IDENTITY")

    return {
        "qualified": True,
        "classification": classification,
        "candidate_url": candidate_url,
        "anchor_text": anchor_text,
        "row_text": row_text[:2000],
        "onclick": onclick,
        "regions": regions,
        "notice_numbers": notice_numbers,
        "dates": dates,
        "document_meta_terms": meta_terms,
        "reasons": unique_strings(reasons),
    }


def extract_candidates(
    *,
    raw_html: str,
    source_url: str,
    action_url: str,
    regions: List[str],
    base_url: str,
    field_name: str,
) -> Tuple[List[Dict[str, Any]], int]:
    results: List[Dict[str, Any]] = []
    echo_rejected = 0
    echo_values = extract_search_echo_values(raw_html, field_name)

    for _, row_html in ROW_PATTERN.findall(raw_html):
        row_text = strip_html(row_html)
        if not direct_target_evidence(row_text):
            continue
        for attrs, anchor_html in ANCHOR_PATTERN.findall(row_html):
            candidate = classify_row_link(
                source_url=source_url,
                action_url=action_url,
                regions=regions,
                row_text=row_text,
                attrs=attrs,
                anchor_html=anchor_html,
                base_url=base_url,
                echo_values=echo_values,
            )
            if candidate is None:
                continue
            if candidate.get("classification") == CLASS_REJECTED_QUERY_ECHO:
                echo_rejected += 1
            results.append(candidate)

    return results, echo_rejected


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("CURRENT CANONICAL BOUNDED TARGET QUERY EXECUTION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Query count: 1")
    print()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"T-9 input not found: {INPUT_PATH}")
    data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("T-9 input must be JSON object")

    contracts = data.get("effective_search_contract_pool")
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
    refresh_failure_count = 0
    query_execution_count = 0
    query_echo_rejected = 0
    raw_records: List[Dict[str, Any]] = []
    execution_records: List[Dict[str, Any]] = []

    for index, contract in enumerate(contracts, start=1):
        if request_count + 2 > MAX_TOTAL_REQUESTS:
            break

        print("-" * 60)
        print(f"CONTRACT {index}")
        print("Family:", contract.get("source_family"))
        print("Regions:", contract.get("regions"))
        print("Source URL:", contract.get("source_url"))
        print("Action URL:", contract.get("action_url"))
        print("Method:", contract.get("method"))
        print("Field:", contract.get("field_name"))

        refresh = reconfirm_contract(session, contract)
        request_count += 1
        status = refresh.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if not refresh.get("reconfirmed"):
            refresh_failure_count += 1
            print("Refresh: FAILED")
            continue

        response = execute_target_query(
            session,
            method=refresh["method"],
            action_url=refresh["action_url"],
            base_params=refresh.get("hidden_params") or {},
            field_name=refresh["field_name"],
        )
        request_count += 1
        query_execution_count += 1
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1

        candidates: List[Dict[str, Any]] = []
        echo_count = 0
        if (
            not response.get("error")
            and isinstance(status, int)
            and 200 <= status < 300
            and same_host(contract.get("source_url") or "", response.get("final_url") or "")
        ):
            candidates, echo_count = extract_candidates(
                raw_html=str(response.get("raw_html") or ""),
                source_url=canonicalize_url(contract.get("source_url") or ""),
                action_url=refresh["action_url"],
                regions=contract.get("regions") or [],
                base_url=response.get("final_url") or refresh["action_url"],
                field_name=refresh["field_name"],
            )

        query_echo_rejected += echo_count
        for item in candidates:
            item.update({
                "source_family": contract.get("source_family"),
                "source_url": canonicalize_url(contract.get("source_url") or ""),
                "action_url": refresh["action_url"],
                "method": refresh["method"],
                "field_name": refresh["field_name"],
                "query_used": TARGET_QUERY,
                "query_is_candidate_evidence": False,
                "page_title_is_candidate_evidence": False,
                "result_local_evidence_required": True,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            })
            raw_records.append(item)

        execution_records.append({
            "source_family": contract.get("source_family"),
            "regions": contract.get("regions") or [],
            "source_url": contract.get("source_url"),
            "action_url": refresh["action_url"],
            "method": refresh["method"],
            "field_name": refresh["field_name"],
            "http_status": response.get("http_status"),
            "final_url": response.get("final_url"),
            "response_bytes": response.get("response_bytes"),
            "sha256": response.get("sha256"),
            "raw_candidate_count": len(candidates),
            "query_echo_rejected": echo_count,
            "error": response.get("error") or "",
        })

        print("Refresh: LIVE_FORM_CONTRACT_RECONFIRMED")
        print("HTTP:", response.get("http_status"))
        print("Bytes:", response.get("response_bytes"))
        print("Raw candidates:", len(candidates))
        print("Query echo rejected:", echo_count)

    # ========================================================
    # CANONICAL DEDUPE
    # ========================================================

    canonical_map: Dict[str, Dict[str, Any]] = {}
    duplicate_count = 0

    for item in raw_records:
        candidate_url = canonicalize_url(item.get("candidate_url") or "")
        notice_numbers = item.get("notice_numbers") or []
        identity_key = ""
        if candidate_url:
            identity_key = "URL:" + candidate_url
        elif notice_numbers:
            identity_key = "NOTICE:" + "|".join(sorted(unique_strings(notice_numbers)))
        else:
            identity_key = "ROW:" + hashlib.sha256(
                normalize_space(item.get("row_text")).encode("utf-8")
            ).hexdigest()

        if identity_key in canonical_map:
            duplicate_count += 1
            existing = canonical_map[identity_key]
            existing["regions"] = unique_strings((existing.get("regions") or []) + (item.get("regions") or []))
            existing["notice_numbers"] = unique_strings((existing.get("notice_numbers") or []) + (item.get("notice_numbers") or []))
            existing["dates"] = unique_strings((existing.get("dates") or []) + (item.get("dates") or []))
            existing["reasons"] = unique_strings((existing.get("reasons") or []) + (item.get("reasons") or []))
            if item.get("qualified") is True:
                existing["qualified"] = True
                existing["classification"] = item.get("classification")
            continue

        canonical_map[identity_key] = dict(item)

    canonical_records = list(canonical_map.values())
    canonical_records.sort(key=lambda item: (
        -int(item.get("qualified") is True),
        canonicalize_url(item.get("candidate_url") or ""),
        normalize_space(item.get("row_text")),
    ))

    candidate_documents = [item for item in canonical_records if item.get("qualified") is True]
    rejected_records = [item for item in canonical_records if item.get("qualified") is not True]

    next_stage_notice_identity_pool = [
        {
            "source_family": item.get("source_family"),
            "regions": item.get("regions") or [],
            "source_url": item.get("source_url"),
            "url": canonicalize_url(item.get("candidate_url") or ""),
            "anchor_text": item.get("anchor_text"),
            "row_text": item.get("row_text"),
            "notice_numbers": item.get("notice_numbers") or [],
            "dates": item.get("dates") or [],
            "classification": item.get("classification"),
            "reasons": item.get("reasons") or [],
            "requires_direct_document_verification": True,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in candidate_documents
    ]

    if next_stage_notice_identity_pool:
        resolution = "CURRENT_CANONICAL_BOUNDED_TARGET_QUERY_EXECUTION_COMPLETED"
        next_action = (
            "current canonical result-local evidence로 확인된 UQQ700 notice/document candidate만 U-stage direct verification으로 넘긴다. "
            "문서 본문에서 고시번호, 시행일/등록일, 발령기관, 개발밀도관리구역 지정·변경·해제 identity와 공간 적용범위를 직접 검증한다."
        )
    else:
        resolution = "CURRENT_CANONICAL_BOUNDED_TARGET_QUERY_EXECUTION_NO_DOCUMENT"
        next_action = (
            "실효성이 확인된 성남시 current canonical 고시공고 검색에서 독립적인 UQQ700 document identity가 발견되지 않았다. "
            "이는 SITE FALSE가 아니다. UNKNOWN을 유지하고 historical archive 또는 spatial designation source를 추가 탐색한다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-10 Current Canonical Bounded Target Query Execution",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "input": {"path": str(INPUT_PATH), "resolution": data.get("resolution")},
        "method": {
            "exact_query_count": 1,
            "live_contract_reconfirmation": True,
            "fresh_hidden_parameter_recovery": True,
            "query_as_candidate_evidence": False,
            "page_title_as_candidate_evidence": False,
            "result_local_target_evidence_required": True,
            "document_identity_required": True,
            "source_endpoint_promotion_disabled": True,
            "navigation_promotion_disabled": True,
            "query_echo_guard_enabled": True,
        },
        "summary": {
            "contract_count": len(contracts),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "contract_refresh_failure_count": refresh_failure_count,
            "query_execution_count": query_execution_count,
            "query_echo_rejected": query_echo_rejected,
            "raw_candidate_count": len(raw_records),
            "duplicate_candidate_removed": duplicate_count,
            "canonical_record_count": len(canonical_records),
            "qualified_candidate_count": len(candidate_documents),
            "rejected_record_count": len(rejected_records),
            "next_stage_notice_identity_pool_count": len(next_stage_notice_identity_pool),
        },
        "execution_records": execution_records,
        "candidate_documents": candidate_documents,
        "rejected_records": rejected_records,
        "all_canonical_records": canonical_records,
        "next_stage_notice_identity_pool": next_stage_notice_identity_pool,
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

    all_classes_valid = all(item.get("classification") in VALID_CLASSES for item in canonical_records)
    candidate_classes_valid = all(item.get("classification") in CANDIDATE_CLASSES for item in candidate_documents)

    identity_keys: List[str] = []
    for item in candidate_documents:
        url = canonicalize_url(item.get("candidate_url") or "")
        nums = item.get("notice_numbers") or []
        identity_keys.append(url or ("NOTICE:" + "|".join(sorted(unique_strings(nums)))) or normalize_space(item.get("row_text")))

    duplicate_candidate_identity_leakage = len(identity_keys) - len(set(identity_keys))
    candidate_query_evidence_leakage = sum(1 for item in candidate_documents if item.get("query_is_candidate_evidence") is True)
    candidate_page_title_evidence_leakage = sum(1 for item in candidate_documents if item.get("page_title_is_candidate_evidence") is True)
    candidate_source_endpoint_leakage = sum(
        1 for item in candidate_documents
        if item.get("candidate_url") and source_endpoint_equivalent(
            item.get("candidate_url") or "", item.get("source_url") or "", item.get("action_url") or ""
        )
    )
    candidate_non_go_leakage = sum(
        1 for item in candidate_documents
        if item.get("candidate_url") and not is_government_host(hostname(item.get("candidate_url") or ""))
    )
    candidate_cross_host_leakage = sum(
        1 for item in candidate_documents
        if item.get("candidate_url") and not same_host(item.get("source_url") or "", item.get("candidate_url") or "")
    )
    candidate_region_unbound_leakage = sum(1 for item in candidate_documents if not (item.get("regions") or []))
    candidate_target_evidence_leakage = sum(1 for item in candidate_documents if not direct_target_evidence(item.get("row_text") or ""))
    candidate_document_identity_leakage = sum(
        1 for item in candidate_documents
        if not (
            has_detail_url_identity(item.get("candidate_url") or "")
            or (item.get("notice_numbers") or [])
            or ((item.get("dates") or []) and (item.get("document_meta_terms") or []))
            or normalize_space(item.get("onclick"))
        )
    )
    verified_leakage = sum(1 for item in canonical_records if item.get("verified_positive") is True)
    runtime_leakage = sum(1 for item in canonical_records if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in canonical_records if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in canonical_records if item.get("site_negative_allowed") is True)
    next_stage_safety_leakage = sum(
        1 for item in next_stage_notice_identity_pool
        if item.get("verified_positive") is True
        or item.get("runtime_registration_allowed") is True
        or item.get("site_positive_allowed") is True
        or item.get("site_negative_allowed") is True
        or item.get("final_positive_promotion_allowed") is True
    )
    false_from_no_document_leakage = 1 if (
        not candidate_documents and output_data["resolution_policy"]["source_failure_site_status"] == "FALSE"
    ) else 0

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-9 input exists": INPUT_PATH.exists(),
        "T-9 input parsed": isinstance(data, dict),
        "effective search contract loaded": len(contracts) > 0,
        "exact query matrix count one": True,
        "bounded request count respected": request_count <= MAX_TOTAL_REQUESTS,
        "live contract reconfirmation enabled": True,
        "query evidence disabled": candidate_query_evidence_leakage == 0,
        "page-title evidence disabled": candidate_page_title_evidence_leakage == 0,
        "result-local target evidence required": candidate_target_evidence_leakage == 0,
        "document identity required": candidate_document_identity_leakage == 0,
        "source endpoint promotion disabled": candidate_source_endpoint_leakage == 0,
        "all classes valid": all_classes_valid,
        "candidate classes valid": candidate_classes_valid,
        "candidate identities unique": duplicate_candidate_identity_leakage == 0,
        "candidate non-go.kr leakage zero": candidate_non_go_leakage == 0,
        "candidate cross-host leakage zero": candidate_cross_host_leakage == 0,
        "candidate region-unbound leakage zero": candidate_region_unbound_leakage == 0,
        "verified positive leakage zero": verified_leakage == 0,
        "runtime registration leakage zero": runtime_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "next-stage safety leakage zero": next_stage_safety_leakage == 0,
        "false from no document leakage zero": false_from_no_document_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("CURRENT CANONICAL BOUNDED TARGET QUERY RESULT")
    print("=" * 60)
    print("Contract count:", len(contracts))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Contract refresh failure count:", refresh_failure_count)
    print("Query execution count:", query_execution_count)
    print("Query echo rejected:", query_echo_rejected)
    print("Raw candidate count:", len(raw_records))
    print("Duplicate candidate removed:", duplicate_count)
    print("Canonical candidate count:", len(canonical_records))
    print("Qualified candidate count:", len(candidate_documents))
    print("Next-stage notice identity pool count:", len(next_stage_notice_identity_pool))

    if candidate_documents:
        print()
        print("CURRENT CANONICAL TARGET CANDIDATES")
        print("-" * 60)
        for index, item in enumerate(candidate_documents, start=1):
            print(f"[{index}]", item.get("classification"))
            print("Regions:", item.get("regions"))
            print("URL:", item.get("candidate_url"))
            print("Anchor:", item.get("anchor_text"))
            print("Notice numbers:", item.get("notice_numbers"))
            print("Dates:", item.get("dates"))
            print("Reasons:", item.get("reasons"))
            print()

    print("=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    print(resolution)
    print()
    print(next_action)
    print("Output:", OUTPUT_PATH)

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Duplicate candidate identity leakage:", duplicate_candidate_identity_leakage)
    print("Candidate query evidence leakage:", candidate_query_evidence_leakage)
    print("Candidate page-title evidence leakage:", candidate_page_title_evidence_leakage)
    print("Candidate source endpoint leakage:", candidate_source_endpoint_leakage)
    print("Candidate non-go.kr leakage:", candidate_non_go_leakage)
    print("Candidate cross-host leakage:", candidate_cross_host_leakage)
    print("Candidate region-unbound leakage:", candidate_region_unbound_leakage)
    print("Candidate target evidence leakage:", candidate_target_evidence_leakage)
    print("Candidate document identity leakage:", candidate_document_identity_leakage)
    print("Verified positive leakage:", verified_leakage)
    print("Runtime registration leakage:", runtime_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print("Next-stage safety leakage:", next_stage_safety_leakage)
    print("False from no document leakage:", false_from_no_document_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")
    if not all_pass:
        print("\nFAILED:")
        for name, passed in validations.items():
            if not passed:
                print("-", name)
        raise AssertionError("UQQ700 current canonical bounded target query regression failed")


if __name__ == "__main__":
    main()
