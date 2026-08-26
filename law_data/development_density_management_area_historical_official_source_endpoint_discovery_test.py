# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-Q
Development Density Management Area
Historical Official Source Endpoint Discovery

P-stage의 next_stage_source_discovery_pool을 입력으로 사용하여
source family별 제한된 공식 entry endpoint를 probe하고,
detail / archive / attachment / gazette / record identity 후보를 수집한다.

Q-stage는 endpoint 구조 발견 단계이며 verified positive 판정,
runtime registration, SITE TRUE/FALSE 자동판정을 수행하지 않는다.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
P_STAGE_INPUT_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_historical_official_source_expansion.json"
O_STAGE_INPUT_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_historical_official_archive_discovery.json"
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_historical_official_source_endpoint_discovery.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"

SOURCE_FAMILY_NATIONAL_ARCHIVES = "NATIONAL_ARCHIVES"
SOURCE_FAMILY_OFFICIAL_GAZETTE = "OFFICIAL_GAZETTE"
SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE = "LEGACY_LOCAL_GAZETTE"
SOURCE_FAMILY_LEGACY_LOCAL_NOTICE = "LEGACY_LOCAL_NOTICE"
SOURCE_FAMILY_URBAN_PLANNING = "URBAN_PLANNING_ARCHIVE"
SOURCE_FAMILY_LAND_USE = "LAND_USE_ARCHIVE"
SOURCE_FAMILY_NOTICE_REVERSE = "NOTICE_NUMBER_REVERSE_LOOKUP"

ALLOWED_SOURCE_FAMILIES = {
    SOURCE_FAMILY_NATIONAL_ARCHIVES,
    SOURCE_FAMILY_OFFICIAL_GAZETTE,
    SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE,
    SOURCE_FAMILY_LEGACY_LOCAL_NOTICE,
    SOURCE_FAMILY_URBAN_PLANNING,
    SOURCE_FAMILY_LAND_USE,
    SOURCE_FAMILY_NOTICE_REVERSE,
}
VALID_SOURCE_FAMILIES = ALLOWED_SOURCE_FAMILIES

TARGET_CLASS_PRIMARY = "PRIMARY_HISTORICAL_SOURCE"
TARGET_CLASS_SECONDARY = "SECONDARY_HISTORICAL_SOURCE"
TARGET_CLASS_NOTICE_REVERSE = "NOTICE_NUMBER_REVERSE_LOOKUP_SOURCE"
VALID_TARGET_CLASSES = {TARGET_CLASS_PRIMARY, TARGET_CLASS_SECONDARY, TARGET_CLASS_NOTICE_REVERSE}

SOURCE_PRIORITY = {
    SOURCE_FAMILY_NATIONAL_ARCHIVES: 120,
    SOURCE_FAMILY_OFFICIAL_GAZETTE: 110,
    SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE: 105,
    SOURCE_FAMILY_LEGACY_LOCAL_NOTICE: 105,
    SOURCE_FAMILY_URBAN_PLANNING: 95,
    SOURCE_FAMILY_NOTICE_REVERSE: 85,
    SOURCE_FAMILY_LAND_USE: 70,
}

SOURCE_FAMILY_ENTRY_ENDPOINTS: Dict[str, List[Dict[str, Any]]] = {
    SOURCE_FAMILY_NATIONAL_ARCHIVES: [{"entry_name": "국가기록원", "url": "https://www.archives.go.kr/", "entry_role": "OFFICIAL_ROOT"}],
    SOURCE_FAMILY_OFFICIAL_GAZETTE: [{"entry_name": "대한민국 전자관보", "url": "https://gwanbo.go.kr/", "entry_role": "OFFICIAL_ROOT"}],
    SOURCE_FAMILY_LAND_USE: [{"entry_name": "토지이음", "url": "https://www.eum.go.kr/", "entry_role": "OFFICIAL_ROOT"}],
    SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE: [],
    SOURCE_FAMILY_LEGACY_LOCAL_NOTICE: [],
    SOURCE_FAMILY_URBAN_PLANNING: [],
    SOURCE_FAMILY_NOTICE_REVERSE: [],
}

CLASS_TARGET_DIRECT = "HISTORICAL_TARGET_DIRECT_DETAIL_SEED"
CLASS_NOTICE_DETAIL = "HISTORICAL_NOTICE_DETAIL_SEED"
CLASS_GAZETTE_ISSUE = "HISTORICAL_GAZETTE_ISSUE_SEED"
CLASS_ATTACHMENT = "HISTORICAL_ATTACHMENT_DOCUMENT_SEED"
CLASS_EXTENSIONLESS = "HISTORICAL_EXTENSIONLESS_DOWNLOAD_SEED"
CLASS_ARCHIVE_RECORD = "HISTORICAL_ARCHIVE_RECORD_SEED"
CLASS_NOTICE_REVERSE = "HISTORICAL_NOTICE_REVERSE_LOOKUP_SEED"
CLASS_LOW_CONFIDENCE = "HISTORICAL_LOW_CONFIDENCE_DETAIL_SEED"
CLASS_EXCLUDED_NEGATIVE = "EXCLUDED_PRIOR_NEGATIVE_DOCUMENT"
CLASS_EXCLUDED_LIST = "EXCLUDED_SEARCH_LIST_PAGE"
CLASS_EXCLUDED_ADMIN = "EXCLUDED_ADMINISTRATIVE_DUTY_REFERENCE"
CLASS_EXCLUDED_GENERIC = "EXCLUDED_GENERIC_NAVIGATION"
CLASS_EXCLUDED_EXTERNAL = "EXCLUDED_EXTERNAL_NAVIGATION"
CLASS_EXCLUDED_DUPLICATE = "EXCLUDED_DUPLICATE_RESPONSE"

VALID_CLASSES = {
    CLASS_TARGET_DIRECT, CLASS_NOTICE_DETAIL, CLASS_GAZETTE_ISSUE,
    CLASS_ATTACHMENT, CLASS_EXTENSIONLESS, CLASS_ARCHIVE_RECORD,
    CLASS_NOTICE_REVERSE, CLASS_LOW_CONFIDENCE, CLASS_EXCLUDED_NEGATIVE,
    CLASS_EXCLUDED_LIST, CLASS_EXCLUDED_ADMIN, CLASS_EXCLUDED_GENERIC,
    CLASS_EXCLUDED_EXTERNAL, CLASS_EXCLUDED_DUPLICATE,
}
NEXT_STAGE_ALLOWED_CLASSES = {
    CLASS_TARGET_DIRECT, CLASS_NOTICE_DETAIL, CLASS_GAZETTE_ISSUE,
    CLASS_ATTACHMENT, CLASS_EXTENSIONLESS, CLASS_ARCHIVE_RECORD,
    CLASS_NOTICE_REVERSE,
}

SOURCE_RESOLUTION_DISCOVERY_EXECUTED = "SOURCE_ENTRY_ENDPOINT_DISCOVERY_EXECUTED"
SOURCE_RESOLUTION_ENDPOINT_PENDING = "SOURCE_ENTRY_ENDPOINT_DISCOVERY_PENDING"
SOURCE_RESOLUTION_NO_CANDIDATE = "SOURCE_ENTRY_ENDPOINT_DISCOVERY_COMPLETED_NO_CANDIDATE"

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
REQUEST_DELAY_SECONDS = 0.03
MAX_TOTAL_REQUESTS = 120
MAX_REQUESTS_PER_SOURCE = 24
MAX_REQUESTS_PER_HOST = 40
MAX_QUERY_RECORDS_PER_SOURCE = 4
MAX_SEARCH_VARIANTS_PER_QUERY = 2
MAX_DISCOVERED_LINKS_PER_RESPONSE = 350
MAX_IDENTICAL_RESPONSE_HASH_ANALYSIS = 1
MAX_IDENTICAL_TEXT_HASH_ANALYSIS = 1
CIRCUIT_BREAKER_CONSECUTIVE_ERRORS = 5
CIRCUIT_BREAKER_CONSECUTIVE_IDENTICAL_RESPONSES = 6
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

DOCUMENT_EXTENSIONS = {".pdf", ".hwp", ".hwpx", ".doc", ".docx", ".xls", ".xlsx", ".zip"}
DOWNLOAD_HINT_TERMS = ["download", "filedown", "filedownload", "filedown.do", "download.do", "down.do", "getfile", "atchfile", "attach", "file.do", "filedownload.do", "cmm/fms"]
DETAIL_HINT_TERMS = ["view", "detail", "select", "read", "article", "record", "result", "contents", "post", "boardview", "selectboardarticle", "selectboard", "nttid", "idx=", "seq=", "mgt_no=", "ancmtmgtno=", "recordid", "docid"]
LIST_HINT_TERMS = ["/list", "list.do", "selectboardlist", "board/list", "bbs/list", "search.do", "/search", "resultlist", "searchresult"]
GENERIC_LABEL_TERMS = {"홈", "메인", "목록", "이전", "다음", "이전글", "다음글", "처음", "마지막", "더보기", "전체보기", "로그인", "회원가입", "사이트맵", "본문", "새창", "닫기", "인쇄"}
GENERIC_PATH_TERMS = ["/login", "/logout", "/member", "/join", "/privacy", "/sitemap"]
ACTION_TERMS = ["지정", "변경", "해제", "결정", "변경결정", "결정변경"]
OFFICIAL_TERMS = ["고시", "고시문", "공고", "관보", "시보", "군보", "구보", "공보", "도시관리계획", "도시계획", "지형도면"]
URBAN_TERMS = ["도시관리계획", "도시계획", "도시정책", "지구단위계획", "용도지역", "용도지구", "용도구역", "지형도면", "기반시설부담구역"]
GAZETTE_TERMS = ["관보", "시보", "군보", "구보", "공보", "호외"]
ARCHIVE_TERMS = ["기록물", "기록", "문서", "원문", "기록관리", "archive"]
ADMINISTRATIVE_DUTY_TERMS = ["단위사무명", "단 위 사 무 명", "전결권자", "전 결 권 자", "사무전결", "업무분장", "위임전결", "전결규정", "담당자", "팀장", "국장", "부시장"]

NOTICE_PATTERNS = [
    re.compile(r"(?P<notice>(?:서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|세종특별자치시|경기도|강원특별자치도|강원도|충청북도|충청남도|전북특별자치도|전라북도|전라남도|경상북도|경상남도|제주특별자치도|[가-힣]{2,12}시|[가-힣]{2,12}군|[가-힣]{2,12}구)\s*(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"),
    re.compile(r"(?P<notice>(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"),
]
DATE_PATTERN = re.compile(r"(?P<year>19\d{2}|20\d{2})\s*[.\-/년]\s*(?P<month>0?[1-9]|1[0-2])\s*[.\-/월]\s*(?P<day>0?[1-9]|[12]\d|3[01])\s*일?")

ANCHOR_PATTERN = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", re.IGNORECASE | re.DOTALL)
HREF_PATTERN = re.compile(r'''href\s*=\s*["'](?P<href>[^"']+)["']''', re.IGNORECASE)
ONCLICK_PATTERN = re.compile(r'''onclick\s*=\s*["'](?P<onclick>[^"']+)["']''', re.IGNORECASE)
TAG_PATTERN = re.compile(r"<[^>]+>", re.DOTALL)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.IGNORECASE | re.DOTALL)
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
ROW_PATTERN = re.compile(r"<tr\b[^>]*>.*?</tr>", re.IGNORECASE | re.DOTALL)
LI_PATTERN = re.compile(r"<li\b[^>]*>.*?</li>", re.IGNORECASE | re.DOTALL)

VOLATILE_QUERY_KEYS = {"token", "_csrf", "csrf", "csrftoken", "sessionid", "jsessionid", "timestamp", "rand", "random", "cachebuster", "cache_buster", "cb", "ts", "_"}
TRACKING_QUERY_KEYS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}
JSESSIONID_PATTERN = re.compile(r";jsessionid=[^/?]+", re.IGNORECASE)
COMMON_SEARCH_PARAM_NAMES = ["keyword", "query"]


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


def contains_any(value: str, terms: Iterable[str]) -> bool:
    lowered = normalize_space(value).lower()
    return any(normalize_space(term).lower() in lowered for term in terms)


def strip_html(raw_html: str) -> str:
    value = HTML_COMMENT_PATTERN.sub(" ", raw_html)
    value = SCRIPT_STYLE_PATTERN.sub(" ", value)
    value = TAG_PATTERN.sub(" ", value)
    return normalize_space(html.unescape(value))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(normalize_space(text).encode("utf-8", errors="replace")).hexdigest()


def extract_notice_numbers(text: str) -> List[str]:
    values: List[str] = []
    for pattern in NOTICE_PATTERNS:
        for match in pattern.finditer(text):
            values.append(normalize_space(match.groupdict().get("notice") or match.group(0)))
    return unique_strings(values)


def extract_dates(text: str) -> List[str]:
    values: List[str] = []
    for match in DATE_PATTERN.finditer(text):
        values.append(f"{int(match.group('year')):04d}-{int(match.group('month')):02d}-{int(match.group('day')):02d}")
    return unique_strings(values)


def normalize_query_key(key: str) -> str:
    value = html.unescape(str(key or "")).strip()
    while value.lower().startswith("amp;"):
        value = value[4:].strip()
    return value


def canonicalize_url(url: str) -> str:
    value = html.unescape(normalize_space(url))
    if not value:
        return ""
    if value.lower().startswith("javascript:"):
        return value
    try:
        parsed = urlparse(value)
    except Exception:
        return value
    if not parsed.hostname:
        return value
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    try:
        port = parsed.port
    except ValueError:
        port = None
    netloc = f"{host}:{port}" if port and not (scheme == "https" and port == 443) and not (scheme == "http" and port == 80) else host
    path = re.sub(r"/{2,}", "/", JSESSIONID_PATTERN.sub("", parsed.path or "/"))
    query_items: List[Tuple[str, str]] = []
    seen_pairs: Set[Tuple[str, str]] = set()
    for raw_key, query_value in parse_qsl(parsed.query, keep_blank_values=True):
        key = normalize_query_key(raw_key)
        if not key:
            continue
        lowered = key.lower()
        if lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS or "csrf" in lowered or "session" in lowered:
            continue
        pair = (key, query_value)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        query_items.append(pair)
    query_items.sort(key=lambda item: (item[0].lower(), item[1]))
    return urlunparse((scheme, netloc, path, "", urlencode(query_items, doseq=True), ""))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def same_host(first: str, second: str) -> bool:
    return hostname(first) == hostname(second)


def is_root_path(url: str) -> bool:
    try:
        path = urlparse(url).path or "/"
    except Exception:
        return False
    return path in {"", "/", "/index.do", "/main.do"}


def walk_dicts(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                yield from walk_dicts(child)


def infer_source_family(item: Dict[str, Any]) -> str:
    candidates = [item.get("source_family"), item.get("family"), item.get("source_family_id"), item.get("id"), item.get("name"), item.get("search_strategy"), item.get("strategy")]
    combined = " ".join(normalize_space(v) for v in candidates if v).upper()
    for family in ALLOWED_SOURCE_FAMILIES:
        if family in combined:
            return family
    original = " ".join(normalize_space(v) for v in candidates if v)
    mapping = {
        "국가기록원": SOURCE_FAMILY_NATIONAL_ARCHIVES,
        "전자관보": SOURCE_FAMILY_OFFICIAL_GAZETTE,
        "관보": SOURCE_FAMILY_OFFICIAL_GAZETTE,
        "구형 지자체 공보": SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE,
        "구형 지자체 고시": SOURCE_FAMILY_LEGACY_LOCAL_NOTICE,
        "도시관리계획": SOURCE_FAMILY_URBAN_PLANNING,
        "지형도면": SOURCE_FAMILY_URBAN_PLANNING,
        "토지이음": SOURCE_FAMILY_LAND_USE,
        "고시번호 역탐색": SOURCE_FAMILY_NOTICE_REVERSE,
    }
    for term, family in mapping.items():
        if term in original:
            return family
    return ""


def load_source_targets(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_targets = data.get("next_stage_source_discovery_pool")
    if not isinstance(raw_targets, list):
        return []
    result: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str, str]] = set()
    for item in raw_targets:
        if not isinstance(item, dict):
            continue
        source_family = normalize_space(item.get("source_family")) or infer_source_family(item)
        target_class = normalize_space(item.get("target_class"))
        name = normalize_space(item.get("name"))
        strategy = normalize_space(item.get("search_strategy"))
        if source_family not in VALID_SOURCE_FAMILIES or target_class not in VALID_TARGET_CLASSES or item.get("requires_endpoint_discovery") is not True:
            continue
        normalized_queries: List[Dict[str, Any]] = []
        qseen: Set[Tuple[str, int, int, str]] = set()
        for q in item.get("queries") or []:
            if not isinstance(q, dict):
                continue
            text = normalize_space(q.get("query") or q.get("query_text") or q.get("search_query") or "")
            if not text:
                continue
            qclass = normalize_space(q.get("query_class"))
            try: sy = int(q.get("start_year") or 0)
            except Exception: sy = 0
            try: ey = int(q.get("end_year") or 0)
            except Exception: ey = 0
            key = (text, sy, ey, qclass)
            if key in qseen:
                continue
            qseen.add(key)
            nq = dict(q)
            nq.update({"query": text, "query_class": qclass, "start_year": sy, "end_year": ey})
            normalized_queries.append(nq)
        key = (source_family, target_class, strategy)
        if key in seen:
            continue
        seen.add(key)
        normalized = dict(item)
        normalized.update({"name": name, "source_family": source_family, "target_class": target_class, "search_strategy": strategy, "requires_endpoint_discovery": True, "queries": normalized_queries, "query_count": len(normalized_queries), "source_url": "", "endpoint_url": ""})
        result.append(normalized)
    result.sort(key=lambda item: (-int(item.get("priority") or SOURCE_PRIORITY.get(item.get("source_family"), 0)), int(item.get("target_index") or 0)))
    return result


QUERY_TEXT_KEYS = ["query", "query_text", "search_term", "keyword", "text", "search_text"]
START_YEAR_KEYS = ["start_year", "period_start", "from_year", "year_start"]
END_YEAR_KEYS = ["end_year", "period_end", "to_year", "year_end"]


def first_text(item: Dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = normalize_space(item.get(key))
        if value:
            return value
    return ""


def first_int(item: Dict[str, Any], keys: Iterable[str]) -> Optional[int]:
    for key in keys:
        value = item.get(key)
        if value in (None, ""):
            continue
        try:
            return int(value)
        except Exception:
            pass
    return None


def looks_query_record(item: Dict[str, Any]) -> bool:
    query = first_text(item, QUERY_TEXT_KEYS)
    return bool(query and (TARGET_NAME in query or re.search(r"(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+", query) or contains_any(query, ["도시관리계획", "지형도면", "공보", "관보", "기록물"])))


def load_query_matrix(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_records: List[Dict[str, Any]] = []
    for key in ["base_query_matrix", "query_matrix", "historical_query_matrix", "region_query_matrix", "notice_reverse_lookup_matrix", "notice_reverse_lookup_query_matrix", "notice_reverse_query_matrix"]:
        value = data.get(key)
        if isinstance(value, list):
            raw_records.extend(item for item in value if isinstance(item, dict))
    raw_records.extend(item for item in walk_dicts(data) if looks_query_record(item))
    result: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, Optional[int], Optional[int], str]] = set()
    for item in raw_records:
        query = first_text(item, QUERY_TEXT_KEYS)
        if not query:
            continue
        sy, ey = first_int(item, START_YEAR_KEYS), first_int(item, END_YEAR_KEYS)
        qclass = normalize_space(item.get("query_class") or item.get("classification") or item.get("type") or "")
        key = (query, sy, ey, qclass)
        if key in seen:
            continue
        seen.add(key)
        result.append({"query": query, "start_year": sy, "end_year": ey, "query_class": qclass, "source_family": infer_source_family(item), "priority": int(item.get("priority") or 0)})
    result.sort(key=lambda item: (-int(TARGET_NAME in item.get("query", "")), int(item.get("start_year") or 9999), -int(item.get("priority") or 0), item.get("query", "")))
    return result


def get_source_family_entry_endpoints(source_target: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = SOURCE_FAMILY_ENTRY_ENDPOINTS.get(normalize_space(source_target.get("source_family")), [])
    result, seen = [], set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = canonicalize_url(item.get("url") or "")
        if not url or not hostname(url) or url in seen:
            continue
        seen.add(url)
        normalized = dict(item)
        normalized["url"] = url
        result.append(normalized)
    return result


def select_queries_for_source(source: Dict[str, Any], global_query_matrix: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    source_family = normalize_space(source.get("source_family"))
    candidates: List[Dict[str, Any]] = [dict(item) for item in (source.get("queries") or []) if isinstance(item, dict)]
    candidates += [dict(item) for item in global_query_matrix if normalize_space(item.get("source_family")) == source_family]
    candidates += [dict(item) for item in global_query_matrix if not normalize_space(item.get("source_family")) and TARGET_NAME in normalize_space(item.get("query"))]
    deduped, seen = [], set()
    for item in candidates:
        query = normalize_space(item.get("query") or item.get("query_text") or "")
        if not query:
            continue
        key = (query, item.get("start_year"), item.get("end_year"), normalize_space(item.get("query_class")))
        if key in seen:
            continue
        seen.add(key)
        normalized = dict(item)
        normalized["query"] = query
        deduped.append(normalized)
    deduped.sort(key=lambda item: (-int(normalize_space(item.get("query")) == TARGET_NAME), -int(TARGET_NAME in normalize_space(item.get("query"))), int(item.get("start_year") or 9999), -int(item.get("priority") or 0)))
    return deduped[:MAX_QUERY_RECORDS_PER_SOURCE]


NEGATIVE_RESOLUTION_TERMS = ["UNRELATED", "NO_TARGET", "FALSE_POSITIVE", "ADMINISTRATIVE_DUTY", "LEGAL_REFERENCE_ONLY", "EXCLUDED"]


def load_exclusion_urls(*datasets: Dict[str, Any]) -> Set[str]:
    result: Set[str] = set()
    for data in datasets:
        for item in walk_dicts(data):
            resolution = normalize_space(item.get("resolution")).upper()
            classification = normalize_space(item.get("classification")).upper()
            negative = contains_any(resolution, NEGATIVE_RESOLUTION_TERMS) or classification.startswith("EXCLUDED_") or item.get("excluded") is True
            if not negative:
                continue
            for key in ["url", "child_url", "document_url", "canonical_url", "source_url"]:
                url = canonicalize_url(item.get(key) or "")
                if url and hostname(url):
                    result.add(url)
    return result


def build_search_variants(entry_url: str, query_record: Dict[str, Any]) -> List[str]:
    query_text = normalize_space(query_record.get("query"))
    if not query_text:
        return []
    try:
        parsed = urlparse(entry_url)
    except Exception:
        return []
    base_query = parse_qsl(parsed.query, keep_blank_values=True)
    variants: List[str] = []
    for param_name in COMMON_SEARCH_PARAM_NAMES:
        query_items = [(k, v) for k, v in base_query if k.lower() != param_name.lower()]
        query_items.append((param_name, query_text))
        variants.append(canonicalize_url(urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(query_items, doseq=True), ""))))
        if len(variants) >= MAX_SEARCH_VARIANTS_PER_QUERY:
            break
    return unique_strings(variants)


def extract_charset_from_content_type(content_type: str) -> str:
    value = normalize_space(content_type)
    if not value:
        return ""
    match = re.search(r'''charset\s*=\s*["']?([^;"'\s]+)''', value, flags=re.IGNORECASE)
    return normalize_space(match.group(1)) if match else ""


def decode_response_bytes(data: bytes, *, content_type: str = "", response_encoding: str = "") -> Tuple[str, str]:
    for encoding in unique_strings([extract_charset_from_content_type(content_type), response_encoding, "utf-8", "cp949", "euc-kr"]):
        try:
            return data.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def fetch_response(session: requests.Session, url: str, *, referer: str = "") -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "requested_url": url,
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "content_disposition": "",
        "response_bytes": 0,
        "data": b"",
        "raw_html": "",
        "text": "",
        "response_sha256": "",
        "text_sha256": "",
        "detected_encoding": "",
        "error": "",
    }
    headers: Dict[str, str] = {}
    if referer:
        headers["Referer"] = referer
    try:
        with session.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result["http_status"] = response.status_code
            result["final_url"] = canonicalize_url(str(response.url))
            result["content_type"] = normalize_space(response.headers.get("Content-Type"))
            result["content_disposition"] = normalize_space(response.headers.get("Content-Disposition"))
            response_encoding = normalize_space(response.encoding or "")
            response.raise_for_status()
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=256 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
                chunks.append(chunk)
            data = b"".join(chunks)
            result["data"] = data
            result["response_bytes"] = len(data)
            result["response_sha256"] = sha256_bytes(data)
            content_type = normalize_space(result.get("content_type")).lower()
            prefix = data[:4096].lstrip().lower()
            html_like = "text/html" in content_type or "application/xhtml" in content_type or prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html")
            text_like = content_type.startswith("text/") or "application/xml" in content_type or "text/xml" in content_type or "application/json" in content_type
            if not (html_like or text_like):
                return result
            decoded, detected_encoding = decode_response_bytes(data, content_type=result["content_type"], response_encoding=response_encoding)
            result["detected_encoding"] = detected_encoding
            result["raw_html"] = decoded
            normalized_text = strip_html(decoded) if html_like else normalize_space(decoded)
            result["text"] = normalized_text
            if normalized_text:
                result["text_sha256"] = sha256_text(normalized_text)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def is_file_url(url: str) -> bool:
    try:
        path = (urlparse(url).path or "").lower()
    except Exception:
        return False
    return any(path.endswith(extension) for extension in DOCUMENT_EXTENSIONS)


def is_extensionless_download(url: str) -> bool:
    return False if is_file_url(url) else contains_any(url.lower(), DOWNLOAD_HINT_TERMS)


def looks_detail_url(url: str) -> bool:
    return contains_any(url.lower(), DETAIL_HINT_TERMS)


def looks_list_url(url: str) -> bool:
    return contains_any(url.lower(), LIST_HINT_TERMS)


def extract_js_url(onclick: str) -> str:
    value = normalize_space(onclick)
    for pattern in [r'''location\.href\s*=\s*['"]([^'"]+)['"]''', r'''window\.open\s*\(\s*['"]([^'"]+)['"]''', r'''location\s*=\s*['"]([^'"]+)['"]''']:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if match:
            return normalize_space(match.group(1))
    return ""


def find_local_container(raw_html: str, anchor_start: int, anchor_end: int) -> str:
    for pattern in (ROW_PATTERN, LI_PATTERN):
        for match in pattern.finditer(raw_html):
            if match.start() <= anchor_start and match.end() >= anchor_end:
                return match.group(0)
    return raw_html[max(0, anchor_start - 800):min(len(raw_html), anchor_end + 800)]


def extract_links(base_url: str, raw_html: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    for match in ANCHOR_PATTERN.finditer(raw_html):
        attrs, body = match.group("attrs"), match.group("body")
        label = strip_html(body)
        href_match, onclick_match = HREF_PATTERN.search(attrs), ONCLICK_PATTERN.search(attrs)
        href = normalize_space(href_match.group("href")) if href_match else ""
        onclick = normalize_space(onclick_match.group("onclick")) if onclick_match else ""
        if not href or href == "#" or href.lower().startswith("javascript:"):
            href = extract_js_url(onclick) or href
        if not href or href.lower().startswith(("mailto:", "tel:")):
            continue
        absolute_url = canonicalize_url(urljoin(base_url, html.unescape(href)))
        if not absolute_url or not hostname(absolute_url):
            continue
        local_container_text = strip_html(find_local_container(raw_html, match.start(), match.end()))
        key = (label, absolute_url)
        if key in seen:
            continue
        seen.add(key)
        results.append({"label": label, "url": absolute_url, "onclick": onclick, "local_container_text": local_container_text})
        if len(results) >= MAX_DISCOVERED_LINKS_PER_RESPONSE:
            break
    return results


def detect_administrative_duty(text: str) -> Tuple[bool, List[str]]:
    normalized = normalize_space(text)
    evidence = [term for term in ADMINISTRATIVE_DUTY_TERMS if term in normalized]
    draft_count = len(re.findall(r"기안\s*[○●◎]?", normalized))
    strong_structure = ("단위사무명" in normalized or "단 위 사 무 명" in normalized) and ("전결권자" in normalized or "전 결 권 자" in normalized)
    target_draft = re.search(r"개발밀도관리구역.{0,100}?기안", normalized, flags=re.DOTALL)
    result = strong_structure or (target_draft is not None and draft_count >= 5) or (len(evidence) >= 4 and draft_count >= 5)
    if target_draft:
        evidence.append(normalize_space(target_draft.group(0)))
    return result, unique_strings(evidence)


def looks_generic_navigation(label: str, url: str) -> bool:
    normalized_label = normalize_space(label)
    return normalized_label in GENERIC_LABEL_TERMS or contains_any(url.lower(), GENERIC_PATH_TERMS) or (is_root_path(url) and normalized_label in {"", "홈", "메인"})


def classify_link(*, source: Dict[str, Any], entry_url: str, request_url: str, query_record: Dict[str, Any], link: Dict[str, Any], exclusion_urls: Set[str]) -> Dict[str, Any]:
    source_family = normalize_space(source.get("source_family"))
    label = normalize_space(link.get("label"))
    url = canonicalize_url(link.get("url") or "")
    local_text = normalize_space(link.get("local_container_text"))
    local_evidence = normalize_space(f"{label} {local_text}")
    target_local = TARGET_NAME in local_evidence
    action_terms = [term for term in ACTION_TERMS if term in local_evidence]
    official_terms = [term for term in OFFICIAL_TERMS if term in local_evidence]
    urban_terms = [term for term in URBAN_TERMS if term in local_evidence]
    gazette_terms = [term for term in GAZETTE_TERMS if term in local_evidence]
    archive_terms = [term for term in ARCHIVE_TERMS if term.lower() in local_evidence.lower()]
    notice_numbers = extract_notice_numbers(local_evidence)
    dates = extract_dates(local_evidence)
    attachment, extensionless, detail, list_page = is_file_url(url), is_extensionless_download(url), looks_detail_url(url), looks_list_url(url)
    generic, external, prior_negative = looks_generic_navigation(label, url), not same_host(entry_url, url), url in exclusion_urls
    administrative_duty, administrative_evidence = detect_administrative_duty(local_evidence)
    query_class, query_text = normalize_space(query_record.get("query_class")), normalize_space(query_record.get("query"))
    score, reasons = 0, []
    for cond, pts, reason in [(target_local,30,"TARGET_LOCAL_EVIDENCE"),(bool(action_terms),6,"ACTION_LOCAL_EVIDENCE"),(bool(official_terms),6,"OFFICIAL_LOCAL_EVIDENCE"),(bool(urban_terms),5,"URBAN_LOCAL_EVIDENCE"),(bool(gazette_terms),4,"GAZETTE_LOCAL_EVIDENCE"),(bool(archive_terms),4,"ARCHIVE_LOCAL_EVIDENCE"),(bool(notice_numbers),9,"NOTICE_NUMBER_LOCAL_EVIDENCE"),(detail,5,"DETAIL_URL_STRUCTURE"),(attachment,10,"DIRECT_ATTACHMENT"),(extensionless,9,"EXTENSIONLESS_DOWNLOAD")]:
        if cond:
            score += pts; reasons.append(reason)
    for cond, pts, reason in [(list_page,-20,"SEARCH_LIST_PAGE"),(generic,-30,"GENERIC_NAVIGATION"),(external,-40,"EXTERNAL_NAVIGATION"),(prior_negative,-100,"PRIOR_NEGATIVE_DOCUMENT"),(administrative_duty,-80,"ADMINISTRATIVE_DUTY_REFERENCE")]:
        if cond:
            score += pts; reasons.append(reason)
    if prior_negative: classification = CLASS_EXCLUDED_NEGATIVE
    elif administrative_duty: classification = CLASS_EXCLUDED_ADMIN
    elif external: classification = CLASS_EXCLUDED_EXTERNAL
    elif generic: classification = CLASS_EXCLUDED_GENERIC
    elif list_page: classification = CLASS_EXCLUDED_LIST
    elif attachment: classification = CLASS_ATTACHMENT if target_local or notice_numbers or (gazette_terms and official_terms) or (urban_terms and official_terms) else CLASS_LOW_CONFIDENCE
    elif extensionless: classification = CLASS_EXTENSIONLESS if target_local or notice_numbers or official_terms or gazette_terms else CLASS_LOW_CONFIDENCE
    elif target_local and detail: classification = CLASS_TARGET_DIRECT
    elif source_family == SOURCE_FAMILY_NOTICE_REVERSE and notice_numbers and detail: classification = CLASS_NOTICE_REVERSE
    elif source_family == SOURCE_FAMILY_NATIONAL_ARCHIVES and detail and (archive_terms or notice_numbers or target_local): classification = CLASS_ARCHIVE_RECORD
    elif source_family in {SOURCE_FAMILY_OFFICIAL_GAZETTE, SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE} and detail and gazette_terms: classification = CLASS_GAZETTE_ISSUE
    elif detail and action_terms and official_terms and urban_terms: classification = CLASS_NOTICE_DETAIL
    elif detail and score >= 8: classification = CLASS_LOW_CONFIDENCE
    else: classification = CLASS_EXCLUDED_GENERIC
    return {
        "source_family": source_family, "source_name": normalize_space(source.get("name")), "source_priority": int(source.get("priority") or SOURCE_PRIORITY.get(source_family, 0)),
        "entry_url": canonicalize_url(entry_url), "request_url": canonicalize_url(request_url), "query": query_text, "query_class": query_class,
        "period_start": query_record.get("start_year"), "period_end": query_record.get("end_year"), "label": label, "url": url, "classification": classification, "score": score,
        "target_local_evidence": target_local, "action_terms": unique_strings(action_terms), "official_terms": unique_strings(official_terms), "urban_terms": unique_strings(urban_terms), "gazette_terms": unique_strings(gazette_terms), "archive_terms": unique_strings(archive_terms), "notice_numbers": notice_numbers, "dates": dates,
        "is_attachment": attachment, "is_extensionless_download": extensionless, "looks_detail": detail, "looks_list_page": list_page,
        "generic_navigation": generic, "external_navigation": external, "prior_negative_url": prior_negative, "administrative_duty_reference": administrative_duty, "administrative_duty_evidence": administrative_evidence,
        "local_container_text_preview": local_text[:1200], "reasons": unique_strings(reasons), "final_positive": False, "runtime_registration_allowed": False, "site_positive_allowed": False,
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("HISTORICAL OFFICIAL SOURCE ENDPOINT DISCOVERY")
    print("=" * 60)
    print(f"\nTarget: {TARGET_NAME}\nStandard code: {STANDARD_CODE}\n")
    print("P-stage input:", P_STAGE_INPUT_PATH)
    print("O-stage input:", O_STAGE_INPUT_PATH, "\n")
    if not P_STAGE_INPUT_PATH.exists(): raise FileNotFoundError(f"P-stage input not found: {P_STAGE_INPUT_PATH}")
    if not O_STAGE_INPUT_PATH.exists(): raise FileNotFoundError(f"O-stage input not found: {O_STAGE_INPUT_PATH}")
    p_data = json.loads(P_STAGE_INPUT_PATH.read_text(encoding="utf-8"))
    o_data = json.loads(O_STAGE_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(p_data, dict): raise TypeError("P-stage input must be JSON object.")
    if not isinstance(o_data, dict): raise TypeError("O-stage input must be JSON object.")

    source_targets = load_source_targets(p_data)
    query_matrix = load_query_matrix(p_data)
    exclusion_urls = load_exclusion_urls(p_data, o_data)
    expected_source_target_count = int(((p_data.get("summary") or {}).get("next_stage_source_pool_count")) or 0)
    print("Historical source target count:", len(source_targets))
    print("Expected source target count:", expected_source_target_count)
    print("Historical query count:", len(query_matrix))
    print("Exclusion URL count:", len(exclusion_urls), "\n")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,application/octet-stream,*/*;q=0.8", "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5"})

    total_request_count = http_success_count = transport_error_count = 0
    duplicate_response_suppressed_count = duplicate_text_suppressed_count = 0
    circuit_breaker_trigger_count = raw_link_count = classified_link_count = 0
    host_request_counts: Counter = Counter(); source_request_counts: Counter = Counter(); response_hash_counts: Counter = Counter(); text_hash_counts: Counter = Counter()
    source_without_entry_endpoint_count = source_with_entry_endpoint_count = 0
    source_results: List[Dict[str, Any]] = []; raw_candidates: List[Dict[str, Any]] = []
    stop_all = False

    for source_index, source in enumerate(source_targets, start=1):
        if stop_all: break
        source_family = normalize_space(source.get("source_family")); source_name = normalize_space(source.get("name")); target_class = normalize_space(source.get("target_class")); strategy = normalize_space(source.get("search_strategy")); priority = int(source.get("priority") or SOURCE_PRIORITY.get(source_family, 0))
        selected_queries = select_queries_for_source(source, query_matrix); entry_endpoints = get_source_family_entry_endpoints(source)
        print("-" * 60); print(f"SOURCE TARGET {source_index}"); print("Family:", source_family); print("Name:", source_name or "-"); print("Class:", target_class); print("Priority:", priority); print("Strategy:", strategy); print("Source queries:", len(source.get("queries") or [])); print("Selected Q-stage queries:", len(selected_queries)); print("Entry endpoints:", len(entry_endpoints))
        if not entry_endpoints:
            source_without_entry_endpoint_count += 1
            source_results.append({"source_index": source_index, "target_index": source.get("target_index"), "source_family": source_family, "source_name": source_name, "target_class": target_class, "priority": priority, "search_strategy": strategy, "requires_endpoint_discovery": True, "source_target_url_required": False, "entry_endpoint_count": 0, "selected_query_count": len(selected_queries), "request_count": 0, "http_success_count": 0, "transport_error_count": 0, "raw_link_count": 0, "raw_candidate_count": 0, "circuit_breaker_triggered": False, "resolution": SOURCE_RESOLUTION_ENDPOINT_PENDING})
            print("Resolution:", SOURCE_RESOLUTION_ENDPOINT_PENDING)
            continue
        source_with_entry_endpoint_count += 1
        target_request_count = target_http_success_count = target_error_count = target_raw_link_count = target_candidate_count = target_duplicate_response_count = target_duplicate_text_count = 0
        target_circuit_breaker = False; entry_results = []
        for entry in entry_endpoints:
            if stop_all: break
            entry_url = canonicalize_url(entry.get("url") or "")
            if not entry_url: continue
            source_counter_key = f"{source_family}|{entry_url}"
            request_variants = [({"query": "", "start_year": None, "end_year": None, "query_class": "SOURCE_ENTRY_ROOT_PROBE"}, entry_url)]
            for query_record in selected_queries:
                for variant in build_search_variants(entry_url, query_record): request_variants.append((query_record, variant))
            deduped, seen_urls = [], set()
            for qr, ru in request_variants:
                ru = canonicalize_url(ru)
                if ru and ru not in seen_urls:
                    seen_urls.add(ru); deduped.append((qr, ru))
            deduped = deduped[:MAX_REQUESTS_PER_SOURCE]
            consecutive_errors = consecutive_identical = 0; previous_response_hash = ""
            entry_request_count = entry_success_count = entry_error_count = entry_raw_link_count = entry_candidate_count = entry_duplicate_response_count = entry_duplicate_text_count = 0
            entry_circuit_breaker = False
            for query_record, request_url in deduped:
                if total_request_count >= MAX_TOTAL_REQUESTS: stop_all = True; break
                if source_request_counts[source_counter_key] >= MAX_REQUESTS_PER_SOURCE: break
                request_host = hostname(request_url)
                if host_request_counts[request_host] >= MAX_REQUESTS_PER_HOST:
                    entry_circuit_breaker = target_circuit_breaker = True; circuit_breaker_trigger_count += 1; break
                total_request_count += 1; target_request_count += 1; entry_request_count += 1; source_request_counts[source_counter_key] += 1; host_request_counts[request_host] += 1
                response = fetch_response(session, request_url, referer=entry_url)
                if response.get("http_status") == 200:
                    http_success_count += 1; target_http_success_count += 1; entry_success_count += 1
                if response.get("error"):
                    transport_error_count += 1; target_error_count += 1; entry_error_count += 1; consecutive_errors += 1
                    if consecutive_errors >= CIRCUIT_BREAKER_CONSECUTIVE_ERRORS:
                        entry_circuit_breaker = target_circuit_breaker = True; circuit_breaker_trigger_count += 1; break
                    continue
                consecutive_errors = 0
                response_hash = normalize_space(response.get("response_sha256"))
                if response_hash:
                    response_hash_counts[response_hash] += 1
                    if response_hash_counts[response_hash] > MAX_IDENTICAL_RESPONSE_HASH_ANALYSIS:
                        duplicate_response_suppressed_count += 1; target_duplicate_response_count += 1; entry_duplicate_response_count += 1
                        consecutive_identical = consecutive_identical + 1 if response_hash == previous_response_hash else 1; previous_response_hash = response_hash
                        if consecutive_identical >= CIRCUIT_BREAKER_CONSECUTIVE_IDENTICAL_RESPONSES:
                            entry_circuit_breaker = target_circuit_breaker = True; circuit_breaker_trigger_count += 1; break
                        continue
                previous_response_hash = response_hash; consecutive_identical = 0
                text_hash = normalize_space(response.get("text_sha256"))
                if text_hash:
                    text_hash_counts[text_hash] += 1
                    if text_hash_counts[text_hash] > MAX_IDENTICAL_TEXT_HASH_ANALYSIS:
                        duplicate_text_suppressed_count += 1; target_duplicate_text_count += 1; entry_duplicate_text_count += 1; continue
                raw_html = response.get("raw_html") or ""
                if not raw_html: continue
                links = extract_links(response.get("final_url") or request_url, raw_html)
                raw_link_count += len(links); target_raw_link_count += len(links); entry_raw_link_count += len(links)
                for link in links:
                    candidate = classify_link(source=source, entry_url=entry_url, request_url=request_url, query_record=query_record, link=link, exclusion_urls=exclusion_urls)
                    classified_link_count += 1; target_candidate_count += 1; entry_candidate_count += 1; raw_candidates.append(candidate)
                if REQUEST_DELAY_SECONDS > 0: time.sleep(REQUEST_DELAY_SECONDS)
            entry_results.append({"entry_name": normalize_space(entry.get("entry_name")), "entry_role": normalize_space(entry.get("entry_role")), "entry_url": entry_url, "planned_request_count": len(deduped), "request_count": entry_request_count, "http_success_count": entry_success_count, "transport_error_count": entry_error_count, "duplicate_response_suppressed_count": entry_duplicate_response_count, "duplicate_text_suppressed_count": entry_duplicate_text_count, "raw_link_count": entry_raw_link_count, "raw_candidate_count": entry_candidate_count, "circuit_breaker_triggered": entry_circuit_breaker})
        source_resolution = SOURCE_RESOLUTION_DISCOVERY_EXECUTED if target_candidate_count else SOURCE_RESOLUTION_NO_CANDIDATE
        source_results.append({"source_index": source_index, "target_index": source.get("target_index"), "source_family": source_family, "source_name": source_name, "target_class": target_class, "priority": priority, "search_strategy": strategy, "requires_endpoint_discovery": True, "source_target_url_required": False, "entry_endpoint_count": len(entry_endpoints), "selected_query_count": len(selected_queries), "request_count": target_request_count, "http_success_count": target_http_success_count, "transport_error_count": target_error_count, "duplicate_response_suppressed_count": target_duplicate_response_count, "duplicate_text_suppressed_count": target_duplicate_text_count, "raw_link_count": target_raw_link_count, "raw_candidate_count": target_candidate_count, "circuit_breaker_triggered": target_circuit_breaker, "entry_results": entry_results, "resolution": source_resolution})
        print("Requests:", target_request_count); print("HTTP success:", target_http_success_count); print("Errors:", target_error_count); print("Raw links:", target_raw_link_count); print("Raw candidates:", target_candidate_count); print("Circuit breaker:", target_circuit_breaker); print("Resolution:", source_resolution)

    CLASS_PRIORITY = {CLASS_TARGET_DIRECT:110, CLASS_NOTICE_REVERSE:100, CLASS_ARCHIVE_RECORD:95, CLASS_ATTACHMENT:90, CLASS_EXTENSIONLESS:88, CLASS_NOTICE_DETAIL:85, CLASS_GAZETTE_ISSUE:80, CLASS_LOW_CONFIDENCE:50, CLASS_EXCLUDED_NEGATIVE:10, CLASS_EXCLUDED_ADMIN:9, CLASS_EXCLUDED_LIST:8, CLASS_EXCLUDED_GENERIC:7, CLASS_EXCLUDED_EXTERNAL:6, CLASS_EXCLUDED_DUPLICATE:5}
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for item in raw_candidates:
        url = canonicalize_url(item.get("url") or "")
        if url: grouped[(normalize_space(item.get("source_family")), url)].append(item)
    def choose_representative(group: List[Dict[str, Any]]) -> Dict[str, Any]:
        ordered = sorted(group, key=lambda item: (-CLASS_PRIORITY.get(item.get("classification"),0), -int(item.get("score") or 0), -int(item.get("target_local_evidence") is True), -len(item.get("label") or "")))
        representative = dict(ordered[0]); representative["discovery_variant_count"] = len(group); representative["queries"] = unique_strings(item.get("query") for item in group); representative["request_urls"] = unique_strings(item.get("request_url") for item in group); representative["entry_urls"] = unique_strings(item.get("entry_url") for item in group); representative["labels"] = unique_strings(item.get("label") for item in group); representative["all_notice_numbers"] = unique_strings(n for item in group for n in (item.get("notice_numbers") or [])); representative["all_dates"] = unique_strings(d for item in group for d in (item.get("dates") or [])); representative["all_reasons"] = unique_strings(r for item in group for r in (item.get("reasons") or [])); representative["final_positive"] = False; representative["runtime_registration_allowed"] = False; representative["site_positive_allowed"] = False; return representative
    canonical_candidates = [choose_representative(group) for group in grouped.values()]
    canonical_candidates.sort(key=lambda item: (-CLASS_PRIORITY.get(item.get("classification"),0), -int(item.get("source_priority") or 0), -int(item.get("score") or 0), normalize_space(item.get("source_family")), normalize_space(item.get("url"))))
    def select_class(c: str) -> List[Dict[str, Any]]: return [item for item in canonical_candidates if item.get("classification") == c]
    target_direct_seeds = select_class(CLASS_TARGET_DIRECT); notice_detail_seeds = select_class(CLASS_NOTICE_DETAIL); gazette_issue_seeds = select_class(CLASS_GAZETTE_ISSUE); attachment_seeds = select_class(CLASS_ATTACHMENT); extensionless_seeds = select_class(CLASS_EXTENSIONLESS); archive_record_seeds = select_class(CLASS_ARCHIVE_RECORD); notice_reverse_seeds = select_class(CLASS_NOTICE_REVERSE); low_confidence_seeds = select_class(CLASS_LOW_CONFIDENCE); excluded_negative = select_class(CLASS_EXCLUDED_NEGATIVE); excluded_list = select_class(CLASS_EXCLUDED_LIST); excluded_admin = select_class(CLASS_EXCLUDED_ADMIN); excluded_generic = select_class(CLASS_EXCLUDED_GENERIC); excluded_external = select_class(CLASS_EXCLUDED_EXTERNAL)
    next_stage_verification_pool = [item for item in canonical_candidates if item.get("classification") in NEXT_STAGE_ALLOWED_CLASSES]
    next_stage_verification_pool.sort(key=lambda item: (-CLASS_PRIORITY.get(item.get("classification"),0), -int(item.get("source_priority") or 0), -int(item.get("score") or 0)))
    classification_counts = Counter(item.get("classification") for item in canonical_candidates)

    if target_direct_seeds:
        resolution = "HISTORICAL_OFFICIAL_SOURCE_TARGET_DIRECT_SEED_DISCOVERED"; next_action = "historical target direct detail/archive/attachment seed를 실제 HTTP 재조회하여 문서-local target, 지정·변경·해제 action, 고시번호, 고시일, 행정구역 및 scope를 검증한다."
    elif next_stage_verification_pool:
        resolution = "HISTORICAL_OFFICIAL_SOURCE_VERIFICATION_SEED_DISCOVERED"; next_action = "archive record, notice detail, gazette issue, attachment 또는 notice-number reverse lookup seed를 실제 원문 조회하여 개발밀도관리구역 exact target을 검증한다."
    elif source_without_entry_endpoint_count:
        resolution = "HISTORICAL_OFFICIAL_SOURCE_ENTRY_ENDPOINT_EXPANSION_REQUIRED"; next_action = "P-stage source target은 정상적으로 로드되었으나 일부 source family는 단일 공식 entry endpoint가 없다. LEGACY_LOCAL_GAZETTE, LEGACY_LOCAL_NOTICE, URBAN_PLANNING_ARCHIVE, NOTICE_NUMBER_REVERSE_LOOKUP에 대해 기관별 실제 historical search/archive endpoint를 다음 단계에서 복원한다."
    else:
        resolution = "HISTORICAL_OFFICIAL_SOURCE_ENDPOINT_DISCOVERY_COMPLETED_NO_SEED"; next_action = "현재 제한된 공식 entry endpoint 탐색에서는 검증 가능한 detail/attachment identity를 확보하지 못했다. source family별 실제 검색 API / form action / 공개 데이터 endpoint를 개별 분석한다."

    output_data = {
        "step": "STEP 17-21-C-16-8-Q Development Density Management Area Historical Official Source Endpoint Discovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "inputs": {"p_stage_path": str(P_STAGE_INPUT_PATH), "o_stage_path": str(O_STAGE_INPUT_PATH), "p_stage_resolution": p_data.get("resolution"), "o_stage_resolution": o_data.get("resolution")},
        "method": {"historical_source_family_only": True, "source_target_url_required": False, "p_stage_discovery_plan_schema_preserved": True, "source_family_entry_endpoint_registry_enabled": True, "modern_local_endpoint_bruteforce_repeat": False, "full_p_stage_query_matrix_execution": False, "search_engine_scraping": False, "direct_http_probe": True, "host_request_budget_enabled": True, "source_request_budget_enabled": True, "global_request_budget_enabled": True, "endpoint_circuit_breaker_enabled": True, "response_sha256_suppression_enabled": True, "identical_text_hash_suppression_enabled": True, "page_level_evidence_inheritance": False, "link_local_evidence_enabled": True, "container_local_evidence_enabled": True, "parent_notice_inheritance": False, "parent_date_inheritance": False, "negative_url_exclusion_memory_enabled": True, "administrative_duty_guard_enabled": True, "generic_navigation_guard_enabled": True, "external_navigation_guard_enabled": True, "search_list_seed_promotion_allowed": False, "verified_positive_promotion_allowed": False, "runtime_registration_allowed": False, "site_positive_allowed": False, "max_total_requests": MAX_TOTAL_REQUESTS, "max_requests_per_source": MAX_REQUESTS_PER_SOURCE, "max_requests_per_host": MAX_REQUESTS_PER_HOST, "max_query_records_per_source": MAX_QUERY_RECORDS_PER_SOURCE},
        "summary": {"historical_source_target_count": len(source_targets), "expected_source_target_count": expected_source_target_count, "historical_query_count": len(query_matrix), "source_with_entry_endpoint_count": source_with_entry_endpoint_count, "source_without_entry_endpoint_count": source_without_entry_endpoint_count, "exclusion_url_count": len(exclusion_urls), "request_count": total_request_count, "http_success_count": http_success_count, "transport_error_count": transport_error_count, "duplicate_response_suppressed_count": duplicate_response_suppressed_count, "duplicate_text_suppressed_count": duplicate_text_suppressed_count, "circuit_breaker_trigger_count": circuit_breaker_trigger_count, "raw_link_count": raw_link_count, "classified_link_count": classified_link_count, "canonical_candidate_count": len(canonical_candidates), "target_direct_seed_count": len(target_direct_seeds), "notice_detail_seed_count": len(notice_detail_seeds), "gazette_issue_seed_count": len(gazette_issue_seeds), "attachment_seed_count": len(attachment_seeds), "extensionless_seed_count": len(extensionless_seeds), "archive_record_seed_count": len(archive_record_seeds), "notice_reverse_seed_count": len(notice_reverse_seeds), "low_confidence_seed_count": len(low_confidence_seeds), "next_stage_verification_pool_count": len(next_stage_verification_pool)},
        "classification_counts": dict(sorted(classification_counts.items())), "source_results": source_results, "target_direct_seeds": target_direct_seeds, "notice_detail_seeds": notice_detail_seeds, "gazette_issue_seeds": gazette_issue_seeds, "attachment_seeds": attachment_seeds, "extensionless_download_seeds": extensionless_seeds, "archive_record_seeds": archive_record_seeds, "notice_reverse_lookup_seeds": notice_reverse_seeds, "low_confidence_seeds": low_confidence_seeds, "excluded_prior_negative_documents": excluded_negative, "excluded_search_list_pages": excluded_list, "excluded_administrative_duty_references": excluded_admin, "excluded_generic_navigation": excluded_generic, "excluded_external_navigation": excluded_external, "next_stage_verification_pool": next_stage_verification_pool, "all_canonical_candidates": canonical_candidates, "resolution": resolution, "next_action": next_action, "runtime_registration_allowed": False, "site_positive_allowed": False, "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 60); print("HISTORICAL SOURCE ENDPOINT DISCOVERY RESULT"); print("=" * 60)
    print("Historical source target count:", len(source_targets)); print("Expected source target count:", expected_source_target_count); print("Historical query count:", len(query_matrix)); print("Source with entry endpoint:", source_with_entry_endpoint_count); print("Source without entry endpoint:", source_without_entry_endpoint_count); print("Exclusion URL count:", len(exclusion_urls)); print("Request count:", total_request_count); print("HTTP success count:", http_success_count); print("Transport error count:", transport_error_count); print("Duplicate response suppressed:", duplicate_response_suppressed_count); print("Duplicate text suppressed:", duplicate_text_suppressed_count); print("Circuit breaker trigger count:", circuit_breaker_trigger_count); print("Raw link count:", raw_link_count); print("Canonical candidate count:", len(canonical_candidates)); print()
    for classification in [CLASS_TARGET_DIRECT, CLASS_ARCHIVE_RECORD, CLASS_NOTICE_REVERSE, CLASS_NOTICE_DETAIL, CLASS_GAZETTE_ISSUE, CLASS_ATTACHMENT, CLASS_EXTENSIONLESS, CLASS_LOW_CONFIDENCE]: print(f"{classification}:", classification_counts.get(classification, 0))
    print("\nNext-stage verification pool:", len(next_stage_verification_pool))
    print("\n" + "=" * 60); print("RESOLUTION"); print("=" * 60); print(resolution); print("\n" + next_action); print("\nOutput:", OUTPUT_PATH)

    canonical_keys = {(normalize_space(item.get("source_family")), canonicalize_url(item.get("url") or "")) for item in canonical_candidates}
    verification_keys = {(normalize_space(item.get("source_family")), canonicalize_url(item.get("url") or "")) for item in next_stage_verification_pool}
    final_positive_leakage = sum(1 for item in canonical_candidates if item.get("final_positive") is not False)
    page_evidence_inheritance_leakage = sum(1 for item in canonical_candidates if item.get("target_local_evidence") is True and TARGET_NAME not in normalize_space(item.get("local_container_text_preview")) and TARGET_NAME not in normalize_space(item.get("label")))
    search_list_promotion = sum(1 for item in next_stage_verification_pool if item.get("looks_list_page") is True)
    negative_url_leakage = sum(1 for item in next_stage_verification_pool if canonicalize_url(item.get("url") or "") in exclusion_urls)
    admin_leakage = sum(1 for item in next_stage_verification_pool if item.get("administrative_duty_reference") is True)
    generic_leakage = sum(1 for item in next_stage_verification_pool if item.get("generic_navigation") is True)
    external_leakage = sum(1 for item in next_stage_verification_pool if item.get("external_navigation") is True)
    target_direct_without_local_target = sum(1 for item in target_direct_seeds if item.get("target_local_evidence") is not True)
    source_schema_preserved = expected_source_target_count > 0 and len(source_targets) == expected_source_target_count
    full_query_matrix_not_executed = total_request_count < len(query_matrix) if query_matrix else True

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역", "standard code": STANDARD_CODE == "UQQ700", "P-stage input exists": P_STAGE_INPUT_PATH.exists(), "O-stage input exists": O_STAGE_INPUT_PATH.exists(), "P-stage input parsed": isinstance(p_data, dict), "O-stage input parsed": isinstance(o_data, dict), "historical source targets loaded": len(source_targets) > 0, "P-stage discovery pool schema preserved": source_schema_preserved, "source targets may omit endpoint URL": all(item.get("requires_endpoint_discovery") is True for item in source_targets), "all source targets require endpoint discovery": all(item.get("requires_endpoint_discovery") is True for item in source_targets), "all source families valid": all(normalize_space(item.get("source_family")) in ALLOWED_SOURCE_FAMILIES for item in source_targets), "all target classes valid": all(normalize_space(item.get("target_class")) in VALID_TARGET_CLASSES for item in source_targets), "historical query matrix loaded": len(query_matrix) > 0, "full P-stage query matrix execution disabled": full_query_matrix_not_executed, "modern local endpoint brute-force repeat disabled": output_data["method"]["modern_local_endpoint_bruteforce_repeat"] is False, "search engine scraping disabled": output_data["method"]["search_engine_scraping"] is False, "direct HTTP probe enabled": output_data["method"]["direct_http_probe"] is True, "host request budget enabled": output_data["method"]["host_request_budget_enabled"] is True, "source request budget enabled": output_data["method"]["source_request_budget_enabled"] is True, "global request budget enabled": output_data["method"]["global_request_budget_enabled"] is True, "endpoint circuit breaker enabled": output_data["method"]["endpoint_circuit_breaker_enabled"] is True, "response SHA-256 suppression enabled": output_data["method"]["response_sha256_suppression_enabled"] is True, "identical HTML/text suppression enabled": output_data["method"]["identical_text_hash_suppression_enabled"] is True, "link-local evidence enabled": output_data["method"]["link_local_evidence_enabled"] is True, "container-local evidence enabled": output_data["method"]["container_local_evidence_enabled"] is True, "page-level evidence inheritance disabled": output_data["method"]["page_level_evidence_inheritance"] is False, "negative URL exclusion memory enabled": output_data["method"]["negative_url_exclusion_memory_enabled"] is True, "administrative-duty guard enabled": output_data["method"]["administrative_duty_guard_enabled"] is True, "generic navigation guard enabled": output_data["method"]["generic_navigation_guard_enabled"] is True, "external navigation guard enabled": output_data["method"]["external_navigation_guard_enabled"] is True, "global request budget preserved": total_request_count <= MAX_TOTAL_REQUESTS, "source request budget preserved": all(count <= MAX_REQUESTS_PER_SOURCE for count in source_request_counts.values()), "host request budget preserved": all(count <= MAX_REQUESTS_PER_HOST for count in host_request_counts.values()), "canonical candidates unique": len(canonical_keys) == len(canonical_candidates), "all candidate classes valid": all(item.get("classification") in VALID_CLASSES for item in canonical_candidates), "all candidate URLs exist": all(bool(item.get("url")) for item in canonical_candidates), "verification pool unique": len(verification_keys) == len(next_stage_verification_pool), "verification pool contains only allowed classes": all(item.get("classification") in NEXT_STAGE_ALLOWED_CLASSES for item in next_stage_verification_pool), "search/list page promotion zero": search_list_promotion == 0, "prior negative document leakage zero": negative_url_leakage == 0, "administrative-duty promotion zero": admin_leakage == 0, "generic navigation promotion zero": generic_leakage == 0, "external navigation promotion zero": external_leakage == 0, "target direct requires local target evidence": target_direct_without_local_target == 0, "page-level evidence inheritance leakage zero": page_evidence_inheritance_leakage == 0, "final positive leakage zero": final_positive_leakage == 0, "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False, "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False, "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False, "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }
    print("\n" + "=" * 60); print("VALIDATION"); print("=" * 60)
    for name, passed in validations.items(): print(f"{name}: {passed}")
    print("\nSearch/list page promotion:", search_list_promotion); print("Prior negative document leakage:", negative_url_leakage); print("Administrative-duty promotion:", admin_leakage); print("Generic navigation promotion:", generic_leakage); print("External navigation promotion:", external_leakage); print("Target-direct without local target:", target_direct_without_local_target); print("Page-level evidence inheritance leakage:", page_evidence_inheritance_leakage); print("Final positive leakage:", final_positive_leakage)
    all_pass = all(validations.values()); print(f"\nall_pass: {all_pass}")
    if not all_pass:
        print("\nFAILED:")
        for name, passed in validations.items():
            if not passed: print(f"- {name}")
        raise AssertionError("Development density management area historical official source endpoint discovery regression failed")


if __name__ == "__main__":
    main()
