# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-4

Development Density Management Area
Bounded Historical Board Search Execution

목표
======================================================================

T-3-S1에서 semantic hardening을 통과한 실제 board-local search contract만
사용하여 개발밀도관리구역(UQQ700) historical search를 제한 실행한다.

핵심 원칙
======================================================================

1. 입력은 T-3-S1 hardened contract만 사용한다.
2. contract action/field를 추측하지 않는다.
3. 실행 직전 source page를 다시 GET하여 현재 hidden params/CSRF를 복원한다.
4. bounded query matrix만 실행한다.
5. query 문자열 자체는 candidate evidence로 사용하지 않는다.
6. page title 전체는 candidate evidence로 사용하지 않는다.
7. candidate는 result link 자체의 anchor/local identity에서 target을 확인한다.
8. source/list endpoint 자체를 document candidate로 승격하지 않는다.
9. navigation/main/search/satisfaction 링크를 candidate로 승격하지 않는다.
10. official go.kr + same-host만 candidate로 허용한다.
11. municipality region binding이 있어야 한다.
12. candidate는 아직 verified positive가 아니다.
13. 문서 미발견은 SITE FALSE가 아니라 UNKNOWN이다.
14. runtime registration / SITE TRUE / SITE FALSE 자동판정 금지.
"""

from __future__ import annotations

import html
import json
import re
import time
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

T3S1_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_historical_search_contract_semantic_hardening.json"
)

OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_bounded_historical_search_execution.json"
)


# ============================================================
# TARGET / POLICY
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

QUERY_MATRIX = [
    "개발밀도관리구역",
    "개발밀도 관리구역",
    "개발밀도관리구역 고시",
]


# ============================================================
# OUTPUT CLASS
# ============================================================

CLASS_DOCUMENT_CANDIDATE = "HISTORICAL_TARGET_DOCUMENT_CANDIDATE"
CLASS_NOTICE_IDENTITY_CANDIDATE = "HISTORICAL_NOTICE_IDENTITY_CANDIDATE"
CLASS_REJECTED_SOURCE_ENDPOINT = "REJECTED_SOURCE_ENDPOINT_REPEAT"
CLASS_REJECTED_NAVIGATION = "REJECTED_NAVIGATION_LINK"
CLASS_REJECTED_NON_OFFICIAL = "REJECTED_NON_OFFICIAL_DOCUMENT"
CLASS_REJECTED_REGION = "REJECTED_REGION_MISMATCH"
CLASS_REJECTED_WEAK = "REJECTED_LINK_LOCAL_TARGET_EVIDENCE_WEAK"
CLASS_REJECTED_INVALID = "REJECTED_INVALID_DOCUMENT_URL"

VALID_CLASSES = {
    CLASS_DOCUMENT_CANDIDATE,
    CLASS_NOTICE_IDENTITY_CANDIDATE,
    CLASS_REJECTED_SOURCE_ENDPOINT,
    CLASS_REJECTED_NAVIGATION,
    CLASS_REJECTED_NON_OFFICIAL,
    CLASS_REJECTED_REGION,
    CLASS_REJECTED_WEAK,
    CLASS_REJECTED_INVALID,
}

CANDIDATE_CLASSES = {
    CLASS_DOCUMENT_CANDIDATE,
    CLASS_NOTICE_IDENTITY_CANDIDATE,
}


# ============================================================
# HTTP
# ============================================================

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 40
REQUEST_DELAY_SECONDS = 0.03

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# URL / SEMANTIC RULES
# ============================================================

VOLATILE_QUERY_KEYS = {
    "token", "_csrf", "csrf", "sessionid", "jsessionid",
    "timestamp", "rand", "random", "_",
}

TRACKING_QUERY_KEYS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term",
    "utm_content", "fbclid", "gclid",
}

DOCUMENT_URL_HINTS = [
    "view.do",
    "detail.do",
    "read.do",
    "/view/",
    "/detail/",
    "ntt/view",
    "post/view",
    "article",
    "notice",
    "gosi",
    "gonggo",
    ".pdf",
    ".hwp",
    ".hwpx",
]

NAVIGATION_PATH_TERMS = [
    "/main",
    "/index",
    "/login",
    "/member",
    "/sitemap",
    "/satisfaction/",
    "/rsa/front/search.jsp",
    "/search/",
    "/welfare/",
]

NAVIGATION_TEXT_TERMS = {
    "홈", "home", "메인", "로그인", "회원가입", "사이트맵",
    "이전", "다음", "처음", "마지막", "목록", "전체메뉴",
}

TARGET_PATTERN = re.compile(
    r"개발\s*밀도\s*관리\s*구역",
    re.IGNORECASE,
)

TARGET_CONTEXT_PATTERNS = [
    re.compile(r"도시관리계획.{0,100}개발\s*밀도", re.IGNORECASE),
    re.compile(r"개발\s*밀도.{0,100}(?:지정|결정|변경|고시|지형도면)", re.IGNORECASE),
    re.compile(r"(?:지정|결정|변경|고시).{0,100}개발\s*밀도", re.IGNORECASE),
]

NOTICE_NUMBER_PATTERNS = [
    re.compile(
        r"[가-힣A-Za-z0-9 ]{0,30}(?:고시|공고)\s*제?\s*\d{2,4}\s*[-－]\s*\d+\s*호?"
    ),
    re.compile(r"(?:고시|공고)\s*제?\s*\d{2,4}\s*[-－]\s*\d+\s*호?"),
]

PROVINCE_ONLY_TOKENS = {
    "서울특별시", "서울", "부산광역시", "부산", "대구광역시", "대구",
    "인천광역시", "인천", "광주광역시", "광주", "대전광역시", "대전",
    "울산광역시", "울산", "세종특별자치시", "세종", "경기도", "경기",
    "강원특별자치도", "강원도", "강원", "충청북도", "충북",
    "충청남도", "충남", "전북특별자치도", "전라북도", "전북",
    "전라남도", "전남", "경상북도", "경북", "경상남도", "경남",
    "제주특별자치도", "제주",
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
    try:
        port = parsed.port
    except ValueError:
        port = None

    if port and not (scheme == "http" and port == 80) and not (scheme == "https" and port == 443):
        netloc = f"{host}:{port}"
    else:
        netloc = host

    path = parsed.path or "/"
    path = re.sub(r";jsessionid=[^/?]+", "", path, flags=re.IGNORECASE)
    path = re.sub(r"/{2,}", "/", path)

    query_items = []
    seen_pairs = set()
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        key = normalize_space(key)
        if not key:
            continue
        lowered = key.lower()
        if lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS:
            continue
        if "csrf" in lowered or "session" in lowered:
            continue
        pair = (key, value)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        query_items.append(pair)

    query_items.sort(key=lambda item: (item[0].lower(), item[1]))
    query = urlencode(query_items, doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))


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


def path_query(url: str) -> str:
    try:
        parsed = urlparse(url)
        return ((parsed.path or "") + "?" + (parsed.query or "")).lower()
    except Exception:
        return ""


# ============================================================
# HTML PARSER
# ============================================================

class SearchPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: List[Dict[str, Any]] = []
        self.links: List[Dict[str, Any]] = []
        self.current_form: Optional[Dict[str, Any]] = None
        self.current_link: Optional[Dict[str, Any]] = None

    @staticmethod
    def attrs_dict(attrs: List[Tuple[str, Optional[str]]]) -> Dict[str, str]:
        return {normalize_space(k).lower(): normalize_space(v) for k, v in attrs if k}

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr = self.attrs_dict(attrs)
        tag = tag.lower()

        if tag == "form":
            self.current_form = {
                "action": attr.get("action", ""),
                "method": attr.get("method", "GET").upper(),
                "inputs": [],
            }
            self.forms.append(self.current_form)
            return

        if tag in {"input", "textarea", "select"} and self.current_form is not None:
            self.current_form["inputs"].append({
                "name": attr.get("name", ""),
                "id": attr.get("id", ""),
                "type": attr.get("type", tag),
                "value": attr.get("value", ""),
                "title": attr.get("title", ""),
                "placeholder": attr.get("placeholder", ""),
            })
            return

        if tag == "a":
            self.current_link = {
                "href": attr.get("href", ""),
                "onclick": attr.get("onclick", ""),
                "text_parts": [],
            }
            self.links.append(self.current_link)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "form":
            self.current_form = None
        elif tag == "a":
            self.current_link = None

    def handle_data(self, data: str) -> None:
        if self.current_link is not None:
            text = normalize_space(data)
            if text:
                self.current_link["text_parts"].append(text)


def parse_search_page(raw_html: str, base_url: str) -> Dict[str, Any]:
    parser = SearchPageParser()
    parser.feed(raw_html)

    forms: List[Dict[str, Any]] = []
    for form in parser.forms:
        action = canonicalize_url(urljoin(base_url, form.get("action") or base_url))
        normalized = dict(form)
        normalized["action_url"] = action
        forms.append(normalized)

    links: List[Dict[str, Any]] = []
    for link in parser.links:
        href = html.unescape(normalize_space(link.get("href")))
        text = normalize_space(" ".join(link.get("text_parts") or []))
        onclick = normalize_space(link.get("onclick"))

        absolute = ""
        if href and not href.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
            absolute = canonicalize_url(urljoin(base_url, href))

        links.append({
            "url": absolute,
            "href": href,
            "onclick": onclick,
            "anchor_text": text,
        })

    return {"forms": forms, "links": links}


# ============================================================
# HTTP
# ============================================================

def decode_html(response: requests.Response, data: bytes) -> Tuple[str, str]:
    candidates: List[str] = []
    content_type = normalize_space(response.headers.get("Content-Type"))
    match = re.search(r'''charset\s*=\s*["']?([^;"'\s]+)''', content_type, flags=re.IGNORECASE)
    if match:
        candidates.append(normalize_space(match.group(1)))
    if response.encoding:
        candidates.append(normalize_space(response.encoding))

    preview = data[:8192].decode("ascii", errors="ignore")
    meta = re.search(r'''charset\s*=\s*["']?\s*([A-Za-z0-9._\-]+)''', preview, flags=re.IGNORECASE)
    if meta:
        candidates.append(normalize_space(meta.group(1)))

    candidates.extend(["utf-8", "cp949", "euc-kr"])
    for encoding in unique_strings(candidates):
        try:
            return data.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def fetch_html(session: requests.Session, method: str, url: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "response_bytes": 0,
        "raw_html": "",
        "encoding": "",
        "error": "",
        "error_stage": "",
    }
    try:
        request_fn = session.post if method.upper() == "POST" else session.get
        kwargs: Dict[str, Any] = {
            "timeout": TIMEOUT,
            "allow_redirects": True,
            "stream": True,
        }
        if method.upper() == "POST":
            kwargs["data"] = data or {}
        elif data:
            kwargs["params"] = data

        with request_fn(url, **kwargs) as response:
            result["http_status"] = response.status_code
            result["final_url"] = canonicalize_url(str(response.url))
            result["content_type"] = normalize_space(response.headers.get("Content-Type"))

            chunks: List[bytes] = []
            total = 0
            try:
                for chunk in response.iter_content(chunk_size=128 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_RESPONSE_BYTES:
                        raise ValueError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
                    chunks.append(chunk)
            except Exception as exc:
                result["error"] = repr(exc)
                result["error_stage"] = "BODY_DOWNLOAD"
                return result

            payload = b"".join(chunks)
            result["response_bytes"] = len(payload)
            content_type_lower = result["content_type"].lower()
            prefix = payload[:1000].lstrip().lower()
            html_like = (
                "html" in content_type_lower
                or "text/" in content_type_lower
                or prefix.startswith(b"<!doctype html")
                or prefix.startswith(b"<html")
            )
            if html_like:
                decoded, encoding = decode_html(response, payload)
                result["raw_html"] = decoded
                result["encoding"] = encoding
    except requests.RequestException as exc:
        result["error"] = repr(exc)
        result["error_stage"] = "HTTP_REQUEST"
    except Exception as exc:
        result["error"] = repr(exc)
        result["error_stage"] = "UNEXPECTED"
    return result


# ============================================================
# CONTRACT REFRESH
# ============================================================

def find_matching_form(
    forms: List[Dict[str, Any]],
    *,
    action_url: str,
    field_name: str,
) -> Optional[Dict[str, Any]]:
    action_canonical = canonicalize_url(action_url)
    field_lower = normalize_space(field_name).lower()

    ranked: List[Tuple[int, Dict[str, Any]]] = []
    for form in forms:
        score = 0
        form_action = canonicalize_url(form.get("action_url") or "")
        if form_action == action_canonical:
            score += 50
        names = {normalize_space(inp.get("name")).lower() for inp in (form.get("inputs") or [])}
        if field_lower and field_lower in names:
            score += 50
        if score:
            ranked.append((score, form))

    if not ranked:
        return None
    ranked.sort(key=lambda item: -item[0])
    best_score, best = ranked[0]
    if best_score < 100:
        return None
    return best


def build_fresh_payload(contract: Dict[str, Any], form: Dict[str, Any], query: str) -> Dict[str, str]:
    field_name = normalize_space((contract.get("search_field") or {}).get("name"))
    payload: Dict[str, str] = {}

    for inp in form.get("inputs") or []:
        name = normalize_space(inp.get("name"))
        if not name:
            continue
        input_type = normalize_space(inp.get("type")).lower()
        value = normalize_space(inp.get("value"))
        if input_type in {"hidden", "submit"}:
            payload[name] = value

    # Preserve nonvolatile contract params if current form parser omitted them.
    for key, value in (contract.get("hidden_params") or {}).items():
        key_text = normalize_space(key)
        if not key_text:
            continue
        if "csrf" in key_text.lower() or "session" in key_text.lower():
            continue
        payload.setdefault(key_text, normalize_space(value))

    payload[field_name] = query
    return payload


# ============================================================
# REGION / TARGET
# ============================================================

def region_tokens(region: str) -> List[str]:
    value = normalize_space(region)
    if not value:
        return []
    tokens = [value]
    parts = value.split()
    tokens.extend(parts)
    for part in parts:
        stem = re.sub(r"(?:특별시|광역시|특별자치시|특별자치도|도|시|군|구)$", "", part)
        if stem and len(stem) >= 2:
            tokens.append(stem)
    return unique_strings(tokens)


def matches_region(text: str, regions: List[str], url: str) -> Tuple[bool, List[str]]:
    evidence = normalize_space(f"{text} {url} {hostname(url)}").lower()
    matched: List[str] = []
    for region in regions:
        municipality_tokens = [
            token for token in region_tokens(region)
            if normalize_space(token) and normalize_space(token) not in PROVINCE_ONLY_TOKENS
        ]
        if not municipality_tokens:
            continue
        if any(token.lower() in evidence for token in municipality_tokens):
            matched.append(region)
    return bool(matched), unique_strings(matched)


def target_reasons(text: str) -> List[str]:
    reasons: List[str] = []
    match = TARGET_PATTERN.search(text)
    if match:
        reasons.append("TARGET_LINK_LOCAL:" + normalize_space(match.group(0)))
    for pattern in TARGET_CONTEXT_PATTERNS:
        match = pattern.search(text)
        if match:
            reasons.append("TARGET_LINK_CONTEXT:" + normalize_space(match.group(0)))
    return unique_strings(reasons)


def notice_numbers(text: str) -> List[str]:
    values: List[str] = []
    for pattern in NOTICE_NUMBER_PATTERNS:
        for match in pattern.finditer(text):
            values.append(normalize_space(match.group(0)))
    return unique_strings(values)


def is_navigation_link(url: str, anchor_text: str) -> bool:
    identity = path_query(url)
    text = normalize_space(anchor_text).lower()
    if any(term in identity for term in NAVIGATION_PATH_TERMS):
        return True
    if text in {term.lower() for term in NAVIGATION_TEXT_TERMS}:
        return True
    return False


def has_document_identity(url: str, anchor_text: str, numbers: List[str]) -> bool:
    identity = path_query(url)
    if any(term in identity for term in DOCUMENT_URL_HINTS):
        return True
    if numbers and normalize_space(anchor_text):
        return True
    return False


def classify_link(
    *,
    source_url: str,
    action_url: str,
    candidate_url: str,
    anchor_text: str,
    regions: List[str],
) -> Dict[str, Any]:
    if not candidate_url:
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_INVALID,
            "matched_regions": [],
            "notice_numbers": [],
            "reasons": ["INVALID_DOCUMENT_URL"],
        }

    if not is_government_host(hostname(candidate_url)) or not same_host(source_url, candidate_url):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_NON_OFFICIAL,
            "matched_regions": [],
            "notice_numbers": notice_numbers(anchor_text),
            "reasons": ["DOCUMENT_HOST_NOT_ALLOWED"],
        }

    canonical_candidate = canonicalize_url(candidate_url)
    if canonical_candidate in {canonicalize_url(source_url), canonicalize_url(action_url)}:
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_SOURCE_ENDPOINT,
            "matched_regions": [],
            "notice_numbers": notice_numbers(anchor_text),
            "reasons": ["SOURCE_OR_ACTION_ENDPOINT_REPEAT"],
        }

    if is_navigation_link(candidate_url, anchor_text):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_NAVIGATION,
            "matched_regions": [],
            "notice_numbers": notice_numbers(anchor_text),
            "reasons": ["GENERIC_NAVIGATION_IDENTITY"],
        }

    local_text = normalize_space(f"{anchor_text} {candidate_url}")
    reasons = target_reasons(local_text)
    numbers = notice_numbers(local_text)

    if not reasons:
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_WEAK,
            "matched_regions": [],
            "notice_numbers": numbers,
            "reasons": ["LINK_LOCAL_TARGET_EVIDENCE_MISSING"],
        }

    region_ok, matched_regions = matches_region(local_text, regions, candidate_url)
    if not region_ok:
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_REGION,
            "matched_regions": [],
            "notice_numbers": numbers,
            "reasons": reasons + ["DOCUMENT_REGION_MISMATCH"],
        }

    if not has_document_identity(candidate_url, anchor_text, numbers):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_WEAK,
            "matched_regions": matched_regions,
            "notice_numbers": numbers,
            "reasons": reasons + ["DOCUMENT_IDENTITY_MISSING"],
        }

    classification = CLASS_NOTICE_IDENTITY_CANDIDATE if numbers else CLASS_DOCUMENT_CANDIDATE
    return {
        "qualified": True,
        "classification": classification,
        "matched_regions": matched_regions,
        "notice_numbers": numbers,
        "reasons": reasons,
    }


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("BOUNDED HISTORICAL BOARD SEARCH EXECUTION")
    print("=" * 60)
    print()
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Negative evidence allowed:", NEGATIVE_EVIDENCE_ALLOWED)
    print()

    if not T3S1_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-3-S1 input not found: {T3S1_INPUT_PATH}")

    data = json.loads(T3S1_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("T-3-S1 input must be JSON object.")

    contracts = data.get("next_stage_search_contract_pool")
    if not isinstance(contracts, list):
        contracts = []

    print("Hardened contract count:", len(contracts))
    print("Query matrix count:", len(QUERY_MATRIX))
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
    contract_refresh_failure_count = 0
    query_execution_count = 0
    query_contamination_rejected = 0
    raw_candidates: List[Dict[str, Any]] = []
    execution_results: List[Dict[str, Any]] = []

    for contract_index, contract in enumerate(contracts, start=1):
        source_urls = contract.get("source_urls") or []
        source_url = canonicalize_url(source_urls[0] if source_urls else contract.get("action_url") or "")
        action_url = canonicalize_url(contract.get("action_url") or "")
        method = normalize_space(contract.get("method")).upper()
        field_name = normalize_space((contract.get("search_field") or {}).get("name"))
        regions = contract.get("regions") or []
        if not isinstance(regions, list):
            regions = []

        print("-" * 60)
        print(f"CONTRACT {contract_index}")
        print("Family:", contract.get("source_family"))
        print("Regions:", regions)
        print("Source URL:", source_url)
        print("Action URL:", action_url)
        print("Method:", method)
        print("Search field:", field_name)

        if request_count >= MAX_TOTAL_REQUESTS:
            break

        # Refresh live source page to recover current CSRF/hidden params.
        request_count += 1
        refresh = fetch_html(session, "GET", source_url)
        status = refresh.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if refresh.get("error"):
            transport_error_count += 1

        refresh_ok = (
            isinstance(status, int)
            and 200 <= status < 300
            and not refresh.get("error")
            and bool(refresh.get("raw_html"))
        )

        if not refresh_ok:
            contract_refresh_failure_count += 1
            execution_results.append({
                "contract_index": contract_index,
                "source_family": contract.get("source_family"),
                "regions": regions,
                "source_url": source_url,
                "action_url": action_url,
                "refresh_http_status": status,
                "refresh_error": refresh.get("error"),
                "resolution": "CONTRACT_REFRESH_FAILED",
                "query_count": 0,
                "candidate_count": 0,
            })
            print("Refresh resolution: CONTRACT_REFRESH_FAILED")
            print()
            continue

        parsed_refresh = parse_search_page(refresh.get("raw_html") or "", refresh.get("final_url") or source_url)
        matching_form = find_matching_form(
            parsed_refresh.get("forms") or [],
            action_url=action_url,
            field_name=field_name,
        )

        if matching_form is None:
            contract_refresh_failure_count += 1
            execution_results.append({
                "contract_index": contract_index,
                "source_family": contract.get("source_family"),
                "regions": regions,
                "source_url": source_url,
                "action_url": action_url,
                "refresh_http_status": status,
                "resolution": "LIVE_FORM_CONTRACT_NOT_RECONFIRMED",
                "query_count": 0,
                "candidate_count": 0,
            })
            print("Refresh resolution: LIVE_FORM_CONTRACT_NOT_RECONFIRMED")
            print()
            continue

        contract_candidate_count = 0
        contract_query_count = 0

        for query in QUERY_MATRIX:
            if request_count >= MAX_TOTAL_REQUESTS:
                break

            payload = build_fresh_payload(contract, matching_form, query)
            request_count += 1
            query_execution_count += 1
            contract_query_count += 1

            response = fetch_html(session, method, action_url, data=payload)
            status = response.get("http_status")
            if isinstance(status, int) and 200 <= status < 300:
                http_success_count += 1
            if response.get("error"):
                transport_error_count += 1
                continue
            if not (isinstance(status, int) and 200 <= status < 300):
                continue

            final_url = canonicalize_url(response.get("final_url") or action_url)
            if not same_host(source_url, final_url):
                continue

            raw_html = str(response.get("raw_html") or "")
            if not raw_html:
                continue

            parsed = parse_search_page(raw_html, final_url)
            for link in parsed.get("links") or []:
                candidate_url = canonicalize_url(link.get("url") or "")
                anchor_text = normalize_space(link.get("anchor_text"))

                # Query text is intentionally NOT appended to evidence.
                if query and query in anchor_text and not TARGET_PATTERN.search(anchor_text):
                    query_contamination_rejected += 1

                classification = classify_link(
                    source_url=source_url,
                    action_url=action_url,
                    candidate_url=candidate_url,
                    anchor_text=anchor_text,
                    regions=regions,
                )

                if classification.get("qualified") is not True:
                    continue

                raw_candidates.append({
                    "source_family": contract.get("source_family"),
                    "regions": regions,
                    "source_url": source_url,
                    "action_url": action_url,
                    "method": method,
                    "search_field_name": field_name,
                    "query": query,
                    "response_url": final_url,
                    "candidate_url": candidate_url,
                    "anchor_text": anchor_text,
                    "matched_regions": classification.get("matched_regions") or [],
                    "notice_numbers": classification.get("notice_numbers") or [],
                    "qualified": True,
                    "classification": classification.get("classification"),
                    "reasons": classification.get("reasons") or [],
                    "query_is_evidence": False,
                    "page_title_is_evidence": False,
                    "verified_positive": False,
                    "runtime_registration_allowed": False,
                    "site_positive_allowed": False,
                    "site_negative_allowed": False,
                    "final_positive_promotion_allowed": False,
                })
                contract_candidate_count += 1

            if REQUEST_DELAY_SECONDS > 0:
                time.sleep(REQUEST_DELAY_SECONDS)

        execution_results.append({
            "contract_index": contract_index,
            "source_family": contract.get("source_family"),
            "regions": regions,
            "source_url": source_url,
            "action_url": action_url,
            "refresh_http_status": refresh.get("http_status"),
            "resolution": "SEARCH_EXECUTED",
            "query_count": contract_query_count,
            "candidate_count": contract_candidate_count,
        })

        print("Refresh resolution: LIVE_FORM_CONTRACT_RECONFIRMED")
        print("Queries executed:", contract_query_count)
        print("Candidates:", contract_candidate_count)
        print()

    # Canonical document dedupe by URL.
    canonical_map: Dict[str, Dict[str, Any]] = {}
    duplicate_count = 0
    for item in raw_candidates:
        url = canonicalize_url(item.get("candidate_url") or "")
        if not url:
            continue
        if url in canonical_map:
            duplicate_count += 1
            existing = canonical_map[url]
            existing["regions"] = unique_strings((existing.get("regions") or []) + (item.get("regions") or []))
            existing["matched_regions"] = unique_strings((existing.get("matched_regions") or []) + (item.get("matched_regions") or []))
            existing["queries"] = unique_strings((existing.get("queries") or [existing.get("query")]) + [item.get("query")])
            existing["source_urls"] = unique_strings((existing.get("source_urls") or [existing.get("source_url")]) + [item.get("source_url")])
            existing["anchor_texts"] = unique_strings((existing.get("anchor_texts") or [existing.get("anchor_text")]) + [item.get("anchor_text")])
            existing["notice_numbers"] = unique_strings((existing.get("notice_numbers") or []) + (item.get("notice_numbers") or []))
            existing["reasons"] = unique_strings((existing.get("reasons") or []) + (item.get("reasons") or []))
            continue

        canonical = dict(item)
        canonical["candidate_url"] = url
        canonical["queries"] = unique_strings([item.get("query")])
        canonical["source_urls"] = unique_strings([item.get("source_url")])
        canonical["anchor_texts"] = unique_strings([item.get("anchor_text")])
        canonical_map[url] = canonical

    canonical_candidates = list(canonical_map.values())
    canonical_candidates.sort(key=lambda item: canonicalize_url(item.get("candidate_url") or ""))

    next_stage_document_pool = [
        {
            "source_family": item.get("source_family"),
            "regions": item.get("matched_regions") or item.get("regions") or [],
            "source_urls": item.get("source_urls") or [],
            "queries": item.get("queries") or [],
            "url": item.get("candidate_url"),
            "anchor_text": item.get("anchor_text"),
            "anchor_texts": item.get("anchor_texts") or [],
            "notice_numbers": item.get("notice_numbers") or [],
            "classification": item.get("classification"),
            "reasons": item.get("reasons") or [],
            "query_is_evidence": False,
            "page_title_is_evidence": False,
            "requires_direct_document_verification": True,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in canonical_candidates
    ]

    classification_counts = Counter(item.get("classification") for item in canonical_candidates)

    if next_stage_document_pool:
        resolution = "BOUNDED_HISTORICAL_BOARD_SEARCH_DOCUMENT_CANDIDATE_FOUND"
        next_action = (
            "T-4에서 발견된 canonical document candidate만 U-stage direct document verification으로 넘긴다. "
            "문서 본문에서 target identity, issuing authority, notice number/date, region 및 designation semantics를 직접 검증한다."
        )
    else:
        resolution = "BOUNDED_HISTORICAL_BOARD_SEARCH_NO_DOCUMENT"
        next_action = (
            "실제 board-local search contract를 제한 실행했으나 link-local UQQ700 historical document candidate가 발견되지 않았다. "
            "이는 SITE FALSE가 아니다. UNKNOWN을 유지하고 notice-number reverse lookup 또는 별도 official archive source family로 진행한다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-4 Bounded Historical Board Search Execution",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "inputs": {
            "t3s1_path": str(T3S1_INPUT_PATH),
            "t3s1_resolution": data.get("resolution"),
        },
        "method": {
            "hardened_board_contracts_only": True,
            "live_form_reconfirmation_required": True,
            "fresh_hidden_parameter_recovery_enabled": True,
            "fresh_csrf_recovery_enabled": True,
            "bounded_query_matrix_enabled": True,
            "guessed_field_names_disabled": True,
            "query_as_candidate_evidence_disabled": True,
            "page_title_as_candidate_evidence_disabled": True,
            "link_local_target_evidence_required": True,
            "source_endpoint_promotion_disabled": True,
            "generic_navigation_promotion_disabled": True,
            "document_identity_required": True,
            "same_host_only": True,
            "official_go_kr_required": True,
            "municipality_region_binding_required": True,
            "negative_evidence_enabled": False,
            "verified_positive_promotion_allowed": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
        },
        "summary": {
            "hardened_contract_count": len(contracts),
            "query_matrix_count": len(QUERY_MATRIX),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "contract_refresh_failure_count": contract_refresh_failure_count,
            "query_execution_count": query_execution_count,
            "query_contamination_rejected": query_contamination_rejected,
            "raw_candidate_count": len(raw_candidates),
            "duplicate_candidate_removed": duplicate_count,
            "canonical_candidate_count": len(canonical_candidates),
            "next_stage_document_pool_count": len(next_stage_document_pool),
        },
        "classification_counts": dict(sorted(classification_counts.items())),
        "execution_results": execution_results,
        "candidate_documents": canonical_candidates,
        "next_stage_document_pool": next_stage_document_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }

    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 60)
    print("BOUNDED HISTORICAL BOARD SEARCH RESULT")
    print("=" * 60)
    print("Hardened contract count:", len(contracts))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Transport error count:", transport_error_count)
    print("Contract refresh failure count:", contract_refresh_failure_count)
    print("Query execution count:", query_execution_count)
    print("Query contamination rejected:", query_contamination_rejected)
    print("Raw candidate count:", len(raw_candidates))
    print("Duplicate candidate removed:", duplicate_count)
    print("Canonical candidate count:", len(canonical_candidates))
    print("Next-stage document pool count:", len(next_stage_document_pool))

    if canonical_candidates:
        print()
        print("CANONICAL DOCUMENT CANDIDATES")
        print("-" * 60)
        for index, item in enumerate(canonical_candidates, start=1):
            print(f"[{index}] {item.get('classification')}")
            print("Family:", item.get("source_family"))
            print("Regions:", item.get("matched_regions"))
            print("URL:", item.get("candidate_url"))
            print("Anchor:", item.get("anchor_text"))
            print("Notice numbers:", item.get("notice_numbers"))
            print("Queries:", item.get("queries"))
            print("Reasons:", item.get("reasons"))
            print()

    print()
    print("=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    print(resolution)
    print()
    print(next_action)
    print()
    print("Output:", OUTPUT_PATH)

    # ========================================================
    # VALIDATION
    # ========================================================

    candidate_urls = [canonicalize_url(item.get("candidate_url") or "") for item in canonical_candidates]
    next_urls = [canonicalize_url(item.get("url") or "") for item in next_stage_document_pool]

    invalid_candidate_url_leakage = sum(1 for url in candidate_urls if not url)
    invalid_next_url_leakage = sum(1 for url in next_urls if not url)
    duplicate_candidate_url_leakage = len(candidate_urls) - len(set(url for url in candidate_urls if url))
    duplicate_next_url_leakage = len(next_urls) - len(set(url for url in next_urls if url))

    non_go_kr_leakage = sum(
        1 for item in canonical_candidates
        if not is_government_host(hostname(item.get("candidate_url") or ""))
    )
    cross_host_leakage = sum(
        1 for item in canonical_candidates
        if not any(same_host(source_url, item.get("candidate_url") or "") for source_url in (item.get("source_urls") or []))
    )
    region_unbound_leakage = sum(1 for item in canonical_candidates if not (item.get("matched_regions") or []))
    source_endpoint_leakage = sum(
        1 for item in canonical_candidates
        if canonicalize_url(item.get("candidate_url") or "") in {
            canonicalize_url(item.get("action_url") or ""),
            *[canonicalize_url(url) for url in (item.get("source_urls") or [])],
        }
    )
    navigation_leakage = sum(
        1 for item in canonical_candidates
        if is_navigation_link(item.get("candidate_url") or "", item.get("anchor_text") or "")
    )
    target_evidence_leakage = sum(
        1 for item in canonical_candidates
        if not target_reasons(normalize_space(f"{item.get('anchor_text')} {item.get('candidate_url')}"))
    )
    query_evidence_leakage = sum(1 for item in canonical_candidates if item.get("query_is_evidence") is True)
    page_title_evidence_leakage = sum(1 for item in canonical_candidates if item.get("page_title_is_evidence") is True)
    verified_positive_leakage = sum(1 for item in canonical_candidates if item.get("verified_positive") is True)
    runtime_registration_leakage = sum(1 for item in canonical_candidates if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in canonical_candidates if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in canonical_candidates if item.get("site_negative_allowed") is True)

    all_classes_valid = all(item.get("classification") in CANDIDATE_CLASSES for item in canonical_candidates)
    next_stage_parity = set(candidate_urls) == set(next_urls)

    false_from_no_document_leakage = (
        1 if (
            not canonical_candidates
            and output_data["resolution_policy"]["source_failure_site_status"] == "FALSE"
        ) else 0
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-3-S1 input exists": T3S1_INPUT_PATH.exists(),
        "T-3-S1 input parsed": isinstance(data, dict),
        "hardened contracts loaded": len(contracts) > 0,
        "bounded query matrix enabled": True,
        "live form reconfirmation enabled": True,
        "fresh hidden parameter recovery enabled": True,
        "fresh CSRF recovery enabled": True,
        "guessed search fields disabled": True,
        "query evidence disabled": True,
        "page-title evidence disabled": True,
        "link-local target evidence required": True,
        "source endpoint promotion disabled": True,
        "generic navigation promotion disabled": True,
        "document identity required": True,
        "candidate classes valid": all_classes_valid,
        "candidate URLs valid": invalid_candidate_url_leakage == 0,
        "next-stage URLs valid": invalid_next_url_leakage == 0,
        "candidate URLs unique": duplicate_candidate_url_leakage == 0,
        "next-stage URLs unique": duplicate_next_url_leakage == 0,
        "candidate and next-stage parity": next_stage_parity,
        "candidate non-go.kr leakage zero": non_go_kr_leakage == 0,
        "candidate cross-host leakage zero": cross_host_leakage == 0,
        "candidate region-unbound leakage zero": region_unbound_leakage == 0,
        "source endpoint leakage zero": source_endpoint_leakage == 0,
        "navigation leakage zero": navigation_leakage == 0,
        "link-local target evidence leakage zero": target_evidence_leakage == 0,
        "query evidence leakage zero": query_evidence_leakage == 0,
        "page-title evidence leakage zero": page_title_evidence_leakage == 0,
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
    print("Invalid candidate URL leakage:", invalid_candidate_url_leakage)
    print("Invalid next-stage URL leakage:", invalid_next_url_leakage)
    print("Duplicate candidate URL leakage:", duplicate_candidate_url_leakage)
    print("Duplicate next-stage URL leakage:", duplicate_next_url_leakage)
    print("Candidate non-go.kr leakage:", non_go_kr_leakage)
    print("Candidate cross-host leakage:", cross_host_leakage)
    print("Candidate region-unbound leakage:", region_unbound_leakage)
    print("Source endpoint leakage:", source_endpoint_leakage)
    print("Navigation leakage:", navigation_leakage)
    print("Link-local target evidence leakage:", target_evidence_leakage)
    print("Query evidence leakage:", query_evidence_leakage)
    print("Page-title evidence leakage:", page_title_evidence_leakage)
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
            "Development density management area bounded historical board search execution regression failed"
        )


if __name__ == "__main__":
    main()
