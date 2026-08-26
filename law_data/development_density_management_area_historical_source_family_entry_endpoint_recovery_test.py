# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-S
Development Density Management Area
Historical Source Family Entry Endpoint Recovery

목표
======================================================================
Q-stage에서 실제 entry endpoint가 없어 PENDING 상태로 남은 historical
source family를 대상으로 기관별 공식 historical search/list/archive
endpoint를 복원한다.

입력 1:
    law_data/output/
    development_density_management_area_
    historical_official_source_endpoint_discovery.json

입력 2:
    law_data/output/
    development_density_management_area_
    historical_official_source_expansion.json

입력 3:
    law_data/output/
    development_density_management_area_
    historical_official_archive_discovery.json

입력 4:
    law_data/output/
    development_density_management_area_
    official_board_endpoint_refinement.json

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 대상 source family
======================================================================
Q-stage에서 entry endpoint가 없었던 다음 source family만 대상으로 한다.

    LEGACY_LOCAL_GAZETTE
    LEGACY_LOCAL_NOTICE
    URBAN_PLANNING_ARCHIVE
    NOTICE_NUMBER_REVERSE_LOOKUP

핵심 설계
======================================================================
이 단계는 target document 검색 단계가 아니다.

목적은:

    source family
        ↓
    기관 / 지역
        ↓
    official host
        ↓
    historical search/list/archive endpoint
        ↓
    endpoint capability 확인
        ↓
    T-stage query execution pool 생성

즉 S-stage에서는 검색/list/archive endpoint 자체가 정상적인 성공 결과가 될 수 있다.

그러나 다음은 금지한다.

    - verified positive 생성
    - SITE TRUE/FALSE 판정
    - runtime registration
    - search/list endpoint를 target document seed로 승격
    - endpoint page의 target text를 document evidence로 해석
    - 기존 modern endpoint 49개 전수 brute-force 반복
    - 검색엔진 scraping

S-stage 성공의 의미
======================================================================
개발밀도관리구역 문서를 발견했다는 뜻이 아니다.

다음 조건을 만족하는 official endpoint를 복원했다는 뜻이다.

    official host
    reachable endpoint
    expected endpoint role
    search/list/archive capability
    source family compatibility

출력 class
======================================================================

LEGACY_LOCAL_GAZETTE_ENTRY_ENDPOINT_RECOVERED

LEGACY_LOCAL_NOTICE_ENTRY_ENDPOINT_RECOVERED

URBAN_PLANNING_ARCHIVE_ENTRY_ENDPOINT_RECOVERED

NOTICE_NUMBER_REVERSE_LOOKUP_ENTRY_ENDPOINT_RECOVERED

SOURCE_FAMILY_ENTRY_ENDPOINT_CANDIDATE

SOURCE_FAMILY_ENTRY_ENDPOINT_UNRESOLVED

EXCLUDED_GENERIC_ROOT

EXCLUDED_NON_OFFICIAL_HOST

EXCLUDED_DUPLICATE_ENDPOINT

EXCLUDED_MODERN_ENDPOINT_REPEAT

EXCLUDED_DEAD_ENDPOINT

안전 정책
======================================================================
- verified positive 금지.
- target document final positive 금지.
- runtime registration 금지.
- SITE TRUE/FALSE 자동판정 금지.
- endpoint discovery와 document verification을 분리한다.
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
from urllib.parse import (
    parse_qsl,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)

import requests


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

Q_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_official_source_endpoint_discovery.json"
    )
)

P_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_official_source_expansion.json"
    )
)

O_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_official_archive_discovery.json"
    )
)

H_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "official_board_endpoint_refinement.json"
    )
)

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "historical_source_family_entry_endpoint_recovery.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# SOURCE FAMILY
# ============================================================

SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE = (
    "LEGACY_LOCAL_GAZETTE"
)

SOURCE_FAMILY_LEGACY_LOCAL_NOTICE = (
    "LEGACY_LOCAL_NOTICE"
)

SOURCE_FAMILY_URBAN_PLANNING = (
    "URBAN_PLANNING_ARCHIVE"
)

SOURCE_FAMILY_NOTICE_REVERSE = (
    "NOTICE_NUMBER_REVERSE_LOOKUP"
)

TARGET_SOURCE_FAMILIES = {
    SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE,
    SOURCE_FAMILY_LEGACY_LOCAL_NOTICE,
    SOURCE_FAMILY_URBAN_PLANNING,
    SOURCE_FAMILY_NOTICE_REVERSE,
}


# ============================================================
# OUTPUT CLASS
# ============================================================

CLASS_GAZETTE_RECOVERED = (
    "LEGACY_LOCAL_GAZETTE_ENTRY_ENDPOINT_RECOVERED"
)

CLASS_NOTICE_RECOVERED = (
    "LEGACY_LOCAL_NOTICE_ENTRY_ENDPOINT_RECOVERED"
)

CLASS_URBAN_RECOVERED = (
    "URBAN_PLANNING_ARCHIVE_ENTRY_ENDPOINT_RECOVERED"
)

CLASS_NOTICE_REVERSE_RECOVERED = (
    "NOTICE_NUMBER_REVERSE_LOOKUP_ENTRY_ENDPOINT_RECOVERED"
)

CLASS_ENDPOINT_CANDIDATE = (
    "SOURCE_FAMILY_ENTRY_ENDPOINT_CANDIDATE"
)

CLASS_ENDPOINT_UNRESOLVED = (
    "SOURCE_FAMILY_ENTRY_ENDPOINT_UNRESOLVED"
)

CLASS_EXCLUDED_GENERIC_ROOT = (
    "EXCLUDED_GENERIC_ROOT"
)

CLASS_EXCLUDED_NON_OFFICIAL = (
    "EXCLUDED_NON_OFFICIAL_HOST"
)

CLASS_EXCLUDED_DUPLICATE = (
    "EXCLUDED_DUPLICATE_ENDPOINT"
)

CLASS_EXCLUDED_MODERN_REPEAT = (
    "EXCLUDED_MODERN_ENDPOINT_REPEAT"
)

CLASS_EXCLUDED_DEAD = (
    "EXCLUDED_DEAD_ENDPOINT"
)

VALID_CLASSES = {
    CLASS_GAZETTE_RECOVERED,
    CLASS_NOTICE_RECOVERED,
    CLASS_URBAN_RECOVERED,
    CLASS_NOTICE_REVERSE_RECOVERED,
    CLASS_ENDPOINT_CANDIDATE,
    CLASS_ENDPOINT_UNRESOLVED,
    CLASS_EXCLUDED_GENERIC_ROOT,
    CLASS_EXCLUDED_NON_OFFICIAL,
    CLASS_EXCLUDED_DUPLICATE,
    CLASS_EXCLUDED_MODERN_REPEAT,
    CLASS_EXCLUDED_DEAD,
}

RECOVERED_CLASSES = {
    CLASS_GAZETTE_RECOVERED,
    CLASS_NOTICE_RECOVERED,
    CLASS_URBAN_RECOVERED,
    CLASS_NOTICE_REVERSE_RECOVERED,
}


# ============================================================
# ENDPOINT ROLE
# ============================================================

ROLE_SEARCH = "SEARCH"
ROLE_LIST = "LIST"
ROLE_ARCHIVE = "ARCHIVE"
ROLE_NOTICE = "NOTICE"
ROLE_GAZETTE = "GAZETTE"
ROLE_URBAN_PLANNING = "URBAN_PLANNING"
ROLE_DETAIL_TEMPLATE = "DETAIL_TEMPLATE"
ROLE_UNKNOWN = "UNKNOWN"

VALID_ENDPOINT_ROLES = {
    ROLE_SEARCH,
    ROLE_LIST,
    ROLE_ARCHIVE,
    ROLE_NOTICE,
    ROLE_GAZETTE,
    ROLE_URBAN_PLANNING,
    ROLE_DETAIL_TEMPLATE,
    ROLE_UNKNOWN,
}


# ============================================================
# HTTP CONFIG
# ============================================================

TIMEOUT = 15

MAX_RESPONSE_BYTES = (
    6
    * 1024
    * 1024
)

MAX_TOTAL_REQUESTS = 300

MAX_REQUESTS_PER_HOST = 30

MAX_REQUESTS_PER_SOURCE_FAMILY = 100

MAX_CANDIDATES_PER_HOST = 30

REQUEST_DELAY_SECONDS = 0.02

CIRCUIT_BREAKER_CONSECUTIVE_ERRORS = 4

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# OFFICIAL HOST / URL HINTS
# ============================================================

OFFICIAL_KR_HOST_SUFFIXES = (
    ".go.kr",
    ".or.kr",
    ".kr",
)

NON_OFFICIAL_HOST_TERMS = [
    "google.",
    "naver.",
    "daum.",
    "bing.",
    "facebook.",
    "instagram.",
    "youtube.",
    "blog.",
]

GENERIC_ROOT_PATHS = {
    "",
    "/",
    "/index.do",
    "/main.do",
    "/main",
    "/index",
}


# ============================================================
# ENDPOINT TERMS
# ============================================================

GAZETTE_TERMS = [
    "공보",
    "시보",
    "군보",
    "구보",
    "관보",
    "gazette",
]

NOTICE_TERMS = [
    "고시",
    "공고",
    "고시공고",
    "새올",
    "saeol",
    "eminwon",
    "publicnotice",
    "announce",
]

URBAN_TERMS = [
    "도시관리계획",
    "도시계획",
    "지형도면",
    "urban",
    "cityplan",
    "planning",
]

ARCHIVE_TERMS = [
    "archive",
    "archives",
    "기록",
    "과거",
    "old",
    "history",
]

LIST_TERMS = [
    "list",
    "selectboardlist",
    "board/list",
    "bbs/list",
]

SEARCH_TERMS = [
    "search",
    "query",
    "keyword",
    "search.do",
]

DETAIL_TERMS = [
    "view",
    "detail",
    "read",
    "selectboardarticle",
    "article",
    "post/view",
]

DOWNLOAD_TERMS = [
    "download",
    "filedown",
    "filedownload",
    "atchfile",
    "cmm/fms",
]


# ============================================================
# HTML
# ============================================================

ANCHOR_PATTERN = re.compile(
    r"<a\b(?P<attrs>[^>]*)>"
    r"(?P<body>.*?)"
    r"</a>",
    re.IGNORECASE | re.DOTALL,
)

HREF_PATTERN = re.compile(
    r"""href\s*=\s*["'](?P<href>[^"']+)["']""",
    re.IGNORECASE,
)

FORM_PATTERN = re.compile(
    r"<form\b(?P<attrs>[^>]*)>",
    re.IGNORECASE | re.DOTALL,
)

ACTION_PATTERN = re.compile(
    r"""action\s*=\s*["'](?P<action>[^"']+)["']""",
    re.IGNORECASE,
)

SCRIPT_STYLE_PATTERN = re.compile(
    r"<(?:script|style)\b.*?</(?:script|style)>",
    re.IGNORECASE | re.DOTALL,
)

TAG_PATTERN = re.compile(
    r"<[^>]+>",
    re.DOTALL,
)

HTML_COMMENT_PATTERN = re.compile(
    r"<!--.*?-->",
    re.DOTALL,
)


# ============================================================
# URL NORMALIZATION
# ============================================================

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "csrftoken",
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

def normalize_space(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()


def unique_strings(
    values: Iterable[Any],
) -> List[str]:

    result: List[str] = []
    seen: Set[str] = set()

    for value in values:

        text = normalize_space(
            value
        )

        if not text:
            continue

        if text in seen:
            continue

        seen.add(
            text
        )

        result.append(
            text
        )

    return result


def contains_any(
    value: str,
    terms: Iterable[str],
) -> bool:

    lowered = normalize_space(
        value
    ).lower()

    return any(
        normalize_space(term).lower()
        in lowered
        for term in terms
    )


def strip_html(
    raw_html: str,
) -> str:

    value = HTML_COMMENT_PATTERN.sub(
        " ",
        raw_html,
    )

    value = SCRIPT_STYLE_PATTERN.sub(
        " ",
        value,
    )

    value = TAG_PATTERN.sub(
        " ",
        value,
    )

    value = html.unescape(
        value
    )

    return normalize_space(
        value
    )


def sha256_bytes(
    data: bytes,
) -> str:

    return hashlib.sha256(
        data
    ).hexdigest()


def walk_dicts(
    value: Any,
) -> Iterable[Dict[str, Any]]:

    if isinstance(
        value,
        dict,
    ):

        yield value

        for child in value.values():

            if isinstance(
                child,
                (dict, list),
            ):

                yield from walk_dicts(
                    child
                )

    elif isinstance(
        value,
        list,
    ):

        for child in value:

            if isinstance(
                child,
                (dict, list),
            ):

                yield from walk_dicts(
                    child
                )


# ============================================================
# URL
# ============================================================

def canonicalize_url(
    url: str,
) -> str:

    value = html.unescape(
        normalize_space(
            url
        )
    )

    if not value:
        return ""

    try:

        parsed = urlparse(
            value
        )

    except Exception:

        return value

    if not parsed.hostname:

        return value

    scheme = (
        parsed.scheme
        or "https"
    ).lower()

    host = (
        parsed.hostname
        or ""
    ).lower()

    try:

        port = parsed.port

    except Exception:

        port = None

    if (
        port
        and not (
            scheme == "https"
            and port == 443
        )
        and not (
            scheme == "http"
            and port == 80
        )
    ):

        netloc = (
            f"{host}:{port}"
        )

    else:

        netloc = host

    path = (
        parsed.path
        or "/"
    )

    path = re.sub(
        r";jsessionid=[^/?]+",
        "",
        path,
        flags=re.IGNORECASE,
    )

    path = re.sub(
        r"/{2,}",
        "/",
        path,
    )

    query_items = []
    seen = set()

    for key, query_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        key = html.unescape(
            key
        )

        lowered = key.lower()

        if lowered in VOLATILE_QUERY_KEYS:
            continue

        if lowered in TRACKING_QUERY_KEYS:
            continue

        if "csrf" in lowered:
            continue

        if "session" in lowered:
            continue

        pair = (
            key,
            query_value,
        )

        if pair in seen:
            continue

        seen.add(
            pair
        )

        query_items.append(
            pair
        )

    query_items.sort(
        key=lambda item: (
            item[0].lower(),
            item[1],
        )
    )

    return urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            urlencode(
                query_items,
                doseq=True,
            ),
            "",
        )
    )


def hostname(
    url: str,
) -> str:

    try:

        return (
            urlparse(url).hostname
            or ""
        ).lower()

    except Exception:

        return ""


def url_path(
    url: str,
) -> str:

    try:

        return (
            urlparse(url).path
            or "/"
        ).lower()

    except Exception:

        return ""


def same_host(
    first: str,
    second: str,
) -> bool:

    return (
        hostname(first)
        ==
        hostname(second)
    )


def is_generic_root(
    url: str,
) -> bool:

    return (
        url_path(url)
        in GENERIC_ROOT_PATHS
    )


# ============================================================
# SOURCE FAMILY MAPPING
# ============================================================

def infer_source_family_from_text(
    text: str,
) -> Set[str]:

    value = normalize_space(
        text
    )

    result: Set[str] = set()

    if contains_any(
        value,
        GAZETTE_TERMS,
    ):

        result.add(
            SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE
        )

    if contains_any(
        value,
        NOTICE_TERMS,
    ):

        result.add(
            SOURCE_FAMILY_LEGACY_LOCAL_NOTICE
        )

    if contains_any(
        value,
        URBAN_TERMS,
    ):

        result.add(
            SOURCE_FAMILY_URBAN_PLANNING
        )

    if re.search(
        r"(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+",
        value,
    ):

        result.add(
            SOURCE_FAMILY_NOTICE_REVERSE
        )

    return result


# ============================================================
# LOAD Q-STAGE PENDING TARGETS
# ============================================================

def load_pending_source_targets(
    q_data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    source_results = q_data.get(
        "source_results"
    )

    if not isinstance(
        source_results,
        list,
    ):

        source_results = []

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[str, str]
    ] = set()

    for item in source_results:

        if not isinstance(
            item,
            dict,
        ):

            continue

        source_family = normalize_space(
            item.get(
                "source_family"
            )
        )

        resolution = normalize_space(
            item.get(
                "resolution"
            )
        )

        if (
            source_family
            not in TARGET_SOURCE_FAMILIES
        ):

            continue

        if resolution != (
            "SOURCE_ENTRY_ENDPOINT_DISCOVERY_PENDING"
        ):

            continue

        search_strategy = normalize_space(
            item.get(
                "search_strategy"
            )
        )

        key = (
            source_family,
            search_strategy,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            dict(
                item
            )
        )

    return result


# ============================================================
# MODERN ENDPOINT MEMORY
# ============================================================

def load_modern_endpoint_urls(
    h_data: Dict[str, Any],
    o_data: Dict[str, Any],
) -> Set[str]:

    result: Set[str] = set()

    for data in (
        h_data,
        o_data,
    ):

        for item in walk_dicts(
            data
        ):

            for key in [
                "url",
                "endpoint_url",
                "source_url",
                "canonical_url",
            ]:

                value = canonicalize_url(
                    item.get(
                        key
                    )
                    or ""
                )

                if (
                    value
                    and hostname(
                        value
                    )
                ):

                    result.add(
                        value
                    )

    return result


# ============================================================
# OFFICIAL HOST SEED
# ============================================================

def load_official_host_seeds(
    *datasets: Dict[str, Any],
) -> List[Dict[str, Any]]:

    host_regions: Dict[
        str,
        Set[str],
    ] = defaultdict(
        set
    )

    host_urls: Dict[
        str,
        Set[str],
    ] = defaultdict(
        set
    )

    for data in datasets:

        for item in walk_dicts(
            data
        ):

            region = normalize_space(
                item.get(
                    "region"
                )
                or item.get(
                    "region_name"
                )
                or item.get(
                    "jurisdiction"
                )
                or ""
            )

            for key in [
                "url",
                "endpoint_url",
                "source_url",
                "canonical_url",
                "parent_url",
            ]:

                url = canonicalize_url(
                    item.get(
                        key
                    )
                    or ""
                )

                host = hostname(
                    url
                )

                if not host:
                    continue

                if not is_official_host(
                    host
                ):
                    continue

                host_urls[
                    host
                ].add(
                    url
                )

                if region:

                    host_regions[
                        host
                    ].add(
                        region
                    )

    result = []

    for host in sorted(
        host_urls
    ):

        result.append(
            {
                "host": host,
                "regions": sorted(
                    host_regions.get(
                        host,
                        set(),
                    )
                ),
                "seed_urls": sorted(
                    host_urls[
                        host
                    ]
                ),
            }
        )

    return result


def is_official_host(
    host: str,
) -> bool:

    value = normalize_space(
        host
    ).lower()

    if not value:
        return False

    if any(
        term in value
        for term in NON_OFFICIAL_HOST_TERMS
    ):

        return False

    return value.endswith(
        OFFICIAL_KR_HOST_SUFFIXES
    )


# ============================================================
# CANDIDATE PATH GENERATION
# ============================================================

COMMON_PATH_CANDIDATES = {
    SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE: [
        "/",
        "/board/list.do",
        "/bbs/list.do",
        "/cop/bbs/selectBoardList.do",
        "/cop/bbs/BBSMSTR_000000000017/selectBoardList.do",
        "/news/gazette",
        "/news/publication",
        "/gazette",
        "/archive",
    ],

    SOURCE_FAMILY_LEGACY_LOCAL_NOTICE: [
        "/",
        "/saeol/gosi/list.do",
        "/prog/publicNotice/list.do",
        "/eminwon/eminwonAnnounceList.do",
        "/news/announce",
        "/notice",
        "/gosi",
        "/publicNotice",
    ],

    SOURCE_FAMILY_URBAN_PLANNING: [
        "/",
        "/urban",
        "/urbanplanning",
        "/cityplan",
        "/cityplanning",
        "/plan",
        "/planning",
        "/urban/notice",
    ],

    SOURCE_FAMILY_NOTICE_REVERSE: [
        "/",
        "/saeol/gosi/list.do",
        "/prog/publicNotice/list.do",
        "/eminwon/eminwonAnnounceList.do",
        "/notice",
        "/gosi",
        "/archive",
    ],
}


def build_candidate_urls_for_host(
    host_seed: Dict[str, Any],
    source_family: str,
) -> List[str]:

    host = normalize_space(
        host_seed.get(
            "host"
        )
    )

    if not host:
        return []

    candidates: List[str] = []

    for seed_url in (
        host_seed.get(
            "seed_urls"
        )
        or []
    ):

        seed_url = canonicalize_url(
            seed_url
        )

        if seed_url:

            candidates.append(
                seed_url
            )

    base_urls = [
        f"https://{host}",
        f"http://{host}",
    ]

    for base_url in base_urls:

        for path in COMMON_PATH_CANDIDATES.get(
            source_family,
            [],
        ):

            candidates.append(
                canonicalize_url(
                    urljoin(
                        base_url,
                        path,
                    )
                )
            )

    return unique_strings(
        candidates
    )[
        :MAX_CANDIDATES_PER_HOST
    ]


# ============================================================
# HTTP
# ============================================================

def decode_bytes(
    data: bytes,
    content_type: str,
    response_encoding: str = "",
) -> str:

    charset_match = re.search(
        r"charset\s*=\s*[\"']?([^;\"'\s]+)",
        content_type or "",
        flags=re.IGNORECASE,
    )

    candidates = unique_strings(
        [
            charset_match.group(1)
            if charset_match
            else "",
            response_encoding,
            "utf-8",
            "cp949",
            "euc-kr",
        ]
    )

    for encoding in candidates:

        try:

            return data.decode(
                encoding
            )

        except Exception:
            continue

    return data.decode(
        "utf-8",
        errors="replace",
    )


def fetch_response(
    session: requests.Session,
    url: str,
) -> Dict[str, Any]:

    result = {
        "requested_url": canonicalize_url(
            url
        ),
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "response_bytes": 0,
        "response_sha256": "",
        "raw_html": "",
        "text": "",
        "error": "",
    }

    try:

        with session.get(
            url,
            timeout=TIMEOUT,
            allow_redirects=True,
            stream=True,
        ) as response:

            result[
                "http_status"
            ] = response.status_code

            result[
                "final_url"
            ] = canonicalize_url(
                str(
                    response.url
                )
            )

            result[
                "content_type"
            ] = normalize_space(
                response.headers.get(
                    "Content-Type"
                )
            )

            chunks = []
            total = 0

            for chunk in response.iter_content(
                chunk_size=128 * 1024,
            ):

                if not chunk:
                    continue

                total += len(
                    chunk
                )

                if total > MAX_RESPONSE_BYTES:

                    raise ValueError(
                        "response too large"
                    )

                chunks.append(
                    chunk
                )

            data = b"".join(
                chunks
            )

            result[
                "response_bytes"
            ] = len(
                data
            )

            result[
                "response_sha256"
            ] = sha256_bytes(
                data
            )

            if response.status_code >= 400:

                result[
                    "error"
                ] = (
                    f"HTTP {response.status_code}"
                )

                return result

            content_type = (
                result[
                    "content_type"
                ].lower()
            )

            prefix = (
                data[
                    :500
                ]
                .lstrip()
                .lower()
            )

            is_html = (
                "html"
                in content_type
                or "text/"
                in content_type
                or prefix.startswith(
                    b"<!doctype html"
                )
                or prefix.startswith(
                    b"<html"
                )
            )

            if is_html:

                raw_html = decode_bytes(
                    data,
                    result[
                        "content_type"
                    ],
                    response.encoding
                    or "",
                )

                result[
                    "raw_html"
                ] = raw_html

                result[
                    "text"
                ] = strip_html(
                    raw_html
                )

    except Exception as exc:

        result[
            "error"
        ] = repr(
            exc
        )

    return result


# ============================================================
# HTML ENDPOINT DISCOVERY
# ============================================================

def extract_endpoint_links(
    base_url: str,
    raw_html: str,
) -> List[Dict[str, Any]]:

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[str] = set()

    for match in ANCHOR_PATTERN.finditer(
        raw_html
    ):

        attrs = match.group(
            "attrs"
        )

        label = strip_html(
            match.group(
                "body"
            )
        )

        href_match = HREF_PATTERN.search(
            attrs
        )

        if not href_match:
            continue

        href = normalize_space(
            href_match.group(
                "href"
            )
        )

        if not href:
            continue

        if href.lower().startswith(
            (
                "javascript:",
                "mailto:",
                "tel:",
            )
        ):

            continue

        url = canonicalize_url(
            urljoin(
                base_url,
                href,
            )
        )

        if not hostname(
            url
        ):

            continue

        if url in seen:
            continue

        seen.add(
            url
        )

        result.append(
            {
                "label": label,
                "url": url,
                "source": "ANCHOR",
            }
        )

    for form_match in FORM_PATTERN.finditer(
        raw_html
    ):

        attrs = form_match.group(
            "attrs"
        )

        action_match = ACTION_PATTERN.search(
            attrs
        )

        if not action_match:
            continue

        action = normalize_space(
            action_match.group(
                "action"
            )
        )

        if not action:
            continue

        url = canonicalize_url(
            urljoin(
                base_url,
                action,
            )
        )

        if not hostname(
            url
        ):

            continue

        if url in seen:
            continue

        seen.add(
            url
        )

        result.append(
            {
                "label": "FORM ACTION",
                "url": url,
                "source": "FORM_ACTION",
            }
        )

    return result


# ============================================================
# ENDPOINT ROLE
# ============================================================

def classify_endpoint_role(
    url: str,
    text: str,
) -> str:

    evidence = normalize_space(
        f"{url} {text}"
    )

    if contains_any(
        evidence,
        GAZETTE_TERMS,
    ):

        return ROLE_GAZETTE

    if contains_any(
        evidence,
        URBAN_TERMS,
    ):

        return ROLE_URBAN_PLANNING

    if contains_any(
        evidence,
        ARCHIVE_TERMS,
    ):

        return ROLE_ARCHIVE

    if contains_any(
        evidence,
        NOTICE_TERMS,
    ):

        return ROLE_NOTICE

    if contains_any(
        url,
        SEARCH_TERMS,
    ):

        return ROLE_SEARCH

    if contains_any(
        url,
        LIST_TERMS,
    ):

        return ROLE_LIST

    if contains_any(
        url,
        DETAIL_TERMS,
    ):

        return ROLE_DETAIL_TEMPLATE

    return ROLE_UNKNOWN


def source_family_role_compatible(
    source_family: str,
    role: str,
    text: str,
    url: str,
) -> bool:

    evidence = normalize_space(
        f"{text} {url}"
    )

    if source_family == (
        SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE
    ):

        return (
            role
            in {
                ROLE_GAZETTE,
                ROLE_ARCHIVE,
                ROLE_LIST,
                ROLE_SEARCH,
            }
            and contains_any(
                evidence,
                GAZETTE_TERMS
                + ARCHIVE_TERMS,
            )
        )

    if source_family == (
        SOURCE_FAMILY_LEGACY_LOCAL_NOTICE
    ):

        return (
            role
            in {
                ROLE_NOTICE,
                ROLE_LIST,
                ROLE_SEARCH,
                ROLE_ARCHIVE,
            }
            and contains_any(
                evidence,
                NOTICE_TERMS
                + ARCHIVE_TERMS,
            )
        )

    if source_family == (
        SOURCE_FAMILY_URBAN_PLANNING
    ):

        return (
            role
            in {
                ROLE_URBAN_PLANNING,
                ROLE_ARCHIVE,
                ROLE_LIST,
                ROLE_SEARCH,
            }
            and contains_any(
                evidence,
                URBAN_TERMS,
            )
        )

    if source_family == (
        SOURCE_FAMILY_NOTICE_REVERSE
    ):

        return role in {
            ROLE_NOTICE,
            ROLE_SEARCH,
            ROLE_LIST,
            ROLE_ARCHIVE,
            ROLE_DETAIL_TEMPLATE,
        }

    return False


# ============================================================
# CLASSIFICATION
# ============================================================

def recovered_class_for_family(
    source_family: str,
) -> str:

    mapping = {
        SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE: (
            CLASS_GAZETTE_RECOVERED
        ),
        SOURCE_FAMILY_LEGACY_LOCAL_NOTICE: (
            CLASS_NOTICE_RECOVERED
        ),
        SOURCE_FAMILY_URBAN_PLANNING: (
            CLASS_URBAN_RECOVERED
        ),
        SOURCE_FAMILY_NOTICE_REVERSE: (
            CLASS_NOTICE_REVERSE_RECOVERED
        ),
    }

    return mapping.get(
        source_family,
        CLASS_ENDPOINT_CANDIDATE,
    )


def classify_endpoint(
    *,
    source_family: str,
    region: str,
    url: str,
    response: Dict[str, Any],
    modern_endpoint_urls: Set[str],
) -> Dict[str, Any]:

    canonical_url = canonicalize_url(
        response.get(
            "final_url"
        )
        or url
    )

    host = hostname(
        canonical_url
    )

    text = normalize_space(
        response.get(
            "text"
        )
    )

    role = classify_endpoint_role(
        canonical_url,
        text,
    )

    official_host = is_official_host(
        host
    )

    reachable = (
        response.get(
            "http_status"
        )
        == 200
        and not response.get(
            "error"
        )
    )

    modern_repeat = (
        canonical_url
        in modern_endpoint_urls
    )

    generic_root = is_generic_root(
        canonical_url
    )

    compatible = source_family_role_compatible(
        source_family,
        role,
        text,
        canonical_url,
    )

    score = 0
    reasons: List[str] = []

    if official_host:

        score += 20
        reasons.append(
            "OFFICIAL_HOST"
        )

    if reachable:

        score += 20
        reasons.append(
            "HTTP_REACHABLE"
        )

    if role != ROLE_UNKNOWN:

        score += 10
        reasons.append(
            f"ROLE_{role}"
        )

    if compatible:

        score += 30
        reasons.append(
            "SOURCE_FAMILY_ROLE_COMPATIBLE"
        )

    if generic_root:

        score -= 25
        reasons.append(
            "GENERIC_ROOT"
        )

    if modern_repeat:

        score -= 40
        reasons.append(
            "MODERN_ENDPOINT_REPEAT"
        )

    if not official_host:

        classification = (
            CLASS_EXCLUDED_NON_OFFICIAL
        )

    elif not reachable:

        classification = (
            CLASS_EXCLUDED_DEAD
        )

    elif modern_repeat:

        classification = (
            CLASS_EXCLUDED_MODERN_REPEAT
        )

    elif generic_root and not compatible:

        classification = (
            CLASS_EXCLUDED_GENERIC_ROOT
        )

    elif compatible:

        classification = (
            recovered_class_for_family(
                source_family
            )
        )

    elif (
        role
        in VALID_ENDPOINT_ROLES
        and role != ROLE_UNKNOWN
    ):

        classification = (
            CLASS_ENDPOINT_CANDIDATE
        )

    else:

        classification = (
            CLASS_ENDPOINT_UNRESOLVED
        )

    return {
        "source_family": source_family,
        "region": region,
        "url": canonical_url,
        "host": host,
        "classification": classification,
        "endpoint_role": role,
        "official_host": official_host,
        "reachable": reachable,
        "http_status": response.get(
            "http_status"
        ),
        "content_type": response.get(
            "content_type"
        ),
        "response_sha256": response.get(
            "response_sha256"
        ),
        "response_bytes": response.get(
            "response_bytes"
        ),
        "modern_endpoint_repeat": modern_repeat,
        "generic_root": generic_root,
        "source_family_role_compatible": (
            compatible
        ),
        "score": score,
        "reasons": unique_strings(
            reasons
        ),
        "text_preview": text[
            :1200
        ],
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "final_positive_promotion_allowed": False,
    }


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print(
        "=" * 60
    )

    print(
        "DEVELOPMENT DENSITY MANAGEMENT AREA"
    )

    print(
        "HISTORICAL SOURCE FAMILY ENTRY ENDPOINT RECOVERY"
    )

    print(
        "=" * 60
    )

    print()

    print(
        f"Target: {TARGET_NAME}"
    )

    print(
        f"Standard code: {STANDARD_CODE}"
    )

    print()

    # ========================================================
    # INPUT
    # ========================================================

    required_paths = [
        Q_STAGE_INPUT_PATH,
        P_STAGE_INPUT_PATH,
        O_STAGE_INPUT_PATH,
        H_STAGE_INPUT_PATH,
    ]

    for path in required_paths:

        if not path.exists():

            raise FileNotFoundError(
                f"Input not found: {path}"
            )

    q_data = json.loads(
        Q_STAGE_INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    p_data = json.loads(
        P_STAGE_INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    o_data = json.loads(
        O_STAGE_INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    h_data = json.loads(
        H_STAGE_INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    pending_source_targets = (
        load_pending_source_targets(
            q_data
        )
    )

    modern_endpoint_urls = (
        load_modern_endpoint_urls(
            h_data,
            o_data,
        )
    )

    official_host_seeds = (
        load_official_host_seeds(
            p_data,
            o_data,
            h_data,
        )
    )

    print(
        "Pending source target count:",
        len(
            pending_source_targets
        ),
    )

    print(
        "Official host seed count:",
        len(
            official_host_seeds
        ),
    )

    print(
        "Modern endpoint exclusion count:",
        len(
            modern_endpoint_urls
        ),
    )

    print()

    # ========================================================
    # SESSION
    # ========================================================

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),
            "Accept-Language": (
                "ko-KR,ko;q=0.9,"
                "en-US;q=0.7,"
                "en;q=0.5"
            ),
        }
    )

    # ========================================================
    # COUNTERS
    # ========================================================

    total_request_count = 0

    http_success_count = 0

    transport_error_count = 0

    host_request_counts: Counter = Counter()

    source_family_request_counts: Counter = (
        Counter()
    )

    circuit_breaker_count = 0

    # ========================================================
    # RESULTS
    # ========================================================

    raw_records: List[
        Dict[str, Any]
    ] = []

    source_results: List[
        Dict[str, Any]
    ] = []

    stop_all = False

    # ========================================================
    # SOURCE FAMILY LOOP
    # ========================================================

    for source_index, source in enumerate(
        pending_source_targets,
        start=1,
    ):

        if stop_all:
            break

        source_family = normalize_space(
            source.get(
                "source_family"
            )
        )

        source_name = normalize_space(
            source.get(
                "source_name"
            )
            or source.get(
                "name"
            )
        )

        print(
            "-" * 60
        )

        print(
            f"SOURCE {source_index}"
        )

        print(
            "Family:",
            source_family,
        )

        print(
            "Name:",
            source_name or "-",
        )

        family_request_count = 0
        family_success_count = 0
        family_error_count = 0
        family_recovered_count = 0
        family_candidate_count = 0

        # ====================================================
        # HOST LOOP
        # ====================================================

        for host_seed in official_host_seeds:

            if stop_all:
                break

            if (
                source_family_request_counts[
                    source_family
                ]
                >= MAX_REQUESTS_PER_SOURCE_FAMILY
            ):

                break

            host = normalize_space(
                host_seed.get(
                    "host"
                )
            )

            if not host:
                continue

            candidate_urls = (
                build_candidate_urls_for_host(
                    host_seed,
                    source_family,
                )
            )

            consecutive_errors = 0

            for candidate_url in candidate_urls:

                if (
                    total_request_count
                    >= MAX_TOTAL_REQUESTS
                ):

                    stop_all = True
                    break

                if (
                    host_request_counts[
                        host
                    ]
                    >= MAX_REQUESTS_PER_HOST
                ):

                    break

                if (
                    source_family_request_counts[
                        source_family
                    ]
                    >= MAX_REQUESTS_PER_SOURCE_FAMILY
                ):

                    break

                total_request_count += 1
                family_request_count += 1

                host_request_counts[
                    host
                ] += 1

                source_family_request_counts[
                    source_family
                ] += 1

                response = fetch_response(
                    session,
                    candidate_url,
                )

                if response.get(
                    "error"
                ):

                    transport_error_count += 1
                    family_error_count += 1

                    consecutive_errors += 1

                    if (
                        consecutive_errors
                        >= CIRCUIT_BREAKER_CONSECUTIVE_ERRORS
                    ):

                        circuit_breaker_count += 1
                        break

                else:

                    consecutive_errors = 0

                    if (
                        response.get(
                            "http_status"
                        )
                        == 200
                    ):

                        http_success_count += 1
                        family_success_count += 1

                region = " / ".join(
                    host_seed.get(
                        "regions"
                    )
                    or []
                )

                record = classify_endpoint(
                    source_family=source_family,
                    region=region,
                    url=candidate_url,
                    response=response,
                    modern_endpoint_urls=(
                        modern_endpoint_urls
                    ),
                )

                raw_records.append(
                    record
                )

                if record.get(
                    "classification"
                ) in RECOVERED_CLASSES:

                    family_recovered_count += 1

                elif record.get(
                    "classification"
                ) == CLASS_ENDPOINT_CANDIDATE:

                    family_candidate_count += 1

                # --------------------------------------------
                # 현재 page에서 추가 endpoint 구조 발견
                # --------------------------------------------

                raw_html = (
                    response.get(
                        "raw_html"
                    )
                    or ""
                )

                if raw_html:

                    discovered_links = (
                        extract_endpoint_links(
                            response.get(
                                "final_url"
                            )
                            or candidate_url,
                            raw_html,
                        )
                    )

                    for discovered in (
                        discovered_links
                    ):

                        discovered_url = (
                            canonicalize_url(
                                discovered.get(
                                    "url"
                                )
                                or ""
                            )
                        )

                        if (
                            not discovered_url
                            or hostname(
                                discovered_url
                            )
                            != host
                        ):

                            continue

                        role = classify_endpoint_role(
                            discovered_url,
                            normalize_space(
                                discovered.get(
                                    "label"
                                )
                            ),
                        )

                        if role == ROLE_UNKNOWN:
                            continue

                        compatibility = (
                            source_family_role_compatible(
                                source_family,
                                role,
                                discovered.get(
                                    "label"
                                )
                                or "",
                                discovered_url,
                            )
                        )

                        if not compatibility:
                            continue

                        raw_records.append(
                            {
                                "source_family": (
                                    source_family
                                ),
                                "region": region,
                                "url": discovered_url,
                                "host": host,
                                "classification": (
                                    recovered_class_for_family(
                                        source_family
                                    )
                                ),
                                "endpoint_role": role,
                                "official_host": True,
                                "reachable": None,
                                "http_status": None,
                                "content_type": "",
                                "response_sha256": "",
                                "response_bytes": 0,
                                "modern_endpoint_repeat": (
                                    discovered_url
                                    in modern_endpoint_urls
                                ),
                                "generic_root": (
                                    is_generic_root(
                                        discovered_url
                                    )
                                ),
                                "source_family_role_compatible": True,
                                "score": 35,
                                "reasons": [
                                    "DISCOVERED_FROM_OFFICIAL_HTML",
                                    "SOURCE_FAMILY_ROLE_COMPATIBLE",
                                ],
                                "text_preview": (
                                    normalize_space(
                                        discovered.get(
                                            "label"
                                        )
                                    )
                                ),
                                "verified_positive": False,
                                "runtime_registration_allowed": False,
                                "site_positive_allowed": False,
                                "final_positive_promotion_allowed": False,
                            }
                        )

                if REQUEST_DELAY_SECONDS > 0:

                    time.sleep(
                        REQUEST_DELAY_SECONDS
                    )

        source_results.append(
            {
                "source_index": source_index,
                "source_family": source_family,
                "source_name": source_name,
                "request_count": (
                    family_request_count
                ),
                "http_success_count": (
                    family_success_count
                ),
                "transport_error_count": (
                    family_error_count
                ),
                "recovered_endpoint_count": (
                    family_recovered_count
                ),
                "candidate_endpoint_count": (
                    family_candidate_count
                ),
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "final_positive_promotion_allowed": False,
            }
        )

        print(
            "Requests:",
            family_request_count,
        )

        print(
            "HTTP success:",
            family_success_count,
        )

        print(
            "Errors:",
            family_error_count,
        )

        print(
            "Recovered endpoints:",
            family_recovered_count,
        )

    # ========================================================
    # DEDUPE
    # ========================================================

    grouped: Dict[
        Tuple[str, str],
        List[Dict[str, Any]],
    ] = defaultdict(
        list
    )

    for item in raw_records:

        source_family = normalize_space(
            item.get(
                "source_family"
            )
        )

        url = canonicalize_url(
            item.get(
                "url"
            )
            or ""
        )

        if not url:
            continue

        grouped[
            (
                source_family,
                url,
            )
        ].append(
            item
        )

    CLASS_PRIORITY = {
        CLASS_GAZETTE_RECOVERED: 100,
        CLASS_NOTICE_RECOVERED: 100,
        CLASS_URBAN_RECOVERED: 100,
        CLASS_NOTICE_REVERSE_RECOVERED: 100,
        CLASS_ENDPOINT_CANDIDATE: 60,
        CLASS_ENDPOINT_UNRESOLVED: 40,
        CLASS_EXCLUDED_GENERIC_ROOT: 10,
        CLASS_EXCLUDED_NON_OFFICIAL: 5,
        CLASS_EXCLUDED_DUPLICATE: 4,
        CLASS_EXCLUDED_MODERN_REPEAT: 3,
        CLASS_EXCLUDED_DEAD: 2,
    }

    canonical_records: List[
        Dict[str, Any]
    ] = []

    for group in grouped.values():

        ordered = sorted(
            group,
            key=lambda item: (
                -CLASS_PRIORITY.get(
                    item.get(
                        "classification"
                    ),
                    0,
                ),
                -int(
                    item.get(
                        "score"
                    )
                    or 0
                ),
            ),
        )

        representative = dict(
            ordered[
                0
            ]
        )

        representative[
            "discovery_variant_count"
        ] = len(
            group
        )

        representative[
            "all_reasons"
        ] = unique_strings(
            reason
            for item in group
            for reason in (
                item.get(
                    "reasons"
                )
                or []
            )
        )

        canonical_records.append(
            representative
        )

    canonical_records.sort(
        key=lambda item: (
            -CLASS_PRIORITY.get(
                item.get(
                    "classification"
                ),
                0,
            ),
            normalize_space(
                item.get(
                    "source_family"
                )
            ),
            normalize_space(
                item.get(
                    "region"
                )
            ),
            normalize_space(
                item.get(
                    "url"
                )
            ),
        )
    )

    # ========================================================
    # RECOVERED POOL
    # ========================================================

    recovered_endpoints = [
        item
        for item in canonical_records
        if item.get(
            "classification"
        )
        in RECOVERED_CLASSES
        and item.get(
            "modern_endpoint_repeat"
        )
        is not True
        and item.get(
            "official_host"
        )
        is True
    ]

    candidate_endpoints = [
        item
        for item in canonical_records
        if item.get(
            "classification"
        )
        == CLASS_ENDPOINT_CANDIDATE
    ]

    unresolved_endpoints = [
        item
        for item in canonical_records
        if item.get(
            "classification"
        )
        == CLASS_ENDPOINT_UNRESOLVED
    ]

    classification_counts = Counter(
        item.get(
            "classification"
        )
        for item in canonical_records
    )

    family_recovered_counts = Counter(
        item.get(
            "source_family"
        )
        for item in recovered_endpoints
    )

    # ========================================================
    # NEXT STAGE
    # ========================================================

    next_stage_endpoint_pool = []

    for item in recovered_endpoints:

        endpoint = dict(
            item
        )

        endpoint[
            "query_execution_allowed_next_stage"
        ] = True

        endpoint[
            "verified_positive"
        ] = False

        endpoint[
            "runtime_registration_allowed"
        ] = False

        endpoint[
            "site_positive_allowed"
        ] = False

        endpoint[
            "final_positive_promotion_allowed"
        ] = False

        next_stage_endpoint_pool.append(
            endpoint
        )

    # ========================================================
    # RESOLUTION
    # ========================================================

    recovered_family_count = len(
        {
            item.get(
                "source_family"
            )
            for item in recovered_endpoints
        }
    )

    if recovered_endpoints:

        resolution = (
            "HISTORICAL_SOURCE_FAMILY_ENTRY_ENDPOINT_RECOVERY_COMPLETED"
        )

        next_action = (
            "복원된 official historical endpoint에 대해 P-stage query matrix를 "
            "source-family 및 지역별로 제한 실행하여 실제 detail/archive/"
            "gazette/notice identity를 수집한다. T-stage에서도 endpoint 자체를 "
            "positive로 승격하지 않고 document seed만 별도로 검증한다."
        )

    else:

        resolution = (
            "HISTORICAL_SOURCE_FAMILY_ENTRY_ENDPOINT_RECOVERY_COMPLETED_NO_ENDPOINT"
        )

        next_action = (
            "현재 공식 host memory와 제한된 path discovery만으로는 "
            "historical endpoint를 복원하지 못했다. 기관별 현재 게시판 HTML의 "
            "form action, JavaScript routing, legacy path 및 archive migration "
            "redirect를 추가 분석한다."
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-S "
            "Development Density Management Area "
            "Historical Source Family Entry Endpoint Recovery"
        ),

        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },

        "inputs": {
            "q_stage_path": str(
                Q_STAGE_INPUT_PATH
            ),
            "p_stage_path": str(
                P_STAGE_INPUT_PATH
            ),
            "o_stage_path": str(
                O_STAGE_INPUT_PATH
            ),
            "h_stage_path": str(
                H_STAGE_INPUT_PATH
            ),
            "q_stage_resolution": (
                q_data.get(
                    "resolution"
                )
            ),
        },

        "method": {
            "pending_source_family_only": True,
            "official_host_memory_enabled": True,
            "institution_specific_endpoint_recovery_enabled": True,
            "generic_path_probe_limited": True,
            "modern_endpoint_bruteforce_repeat": False,
            "search_engine_scraping": False,
            "endpoint_document_role_separation": True,
            "search_list_endpoint_positive_allowed": False,
            "verified_positive_promotion_allowed": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "global_request_budget_enabled": True,
            "host_request_budget_enabled": True,
            "source_family_request_budget_enabled": True,
            "circuit_breaker_enabled": True,
        },

        "summary": {
            "pending_source_target_count": len(
                pending_source_targets
            ),
            "official_host_seed_count": len(
                official_host_seeds
            ),
            "modern_endpoint_exclusion_count": len(
                modern_endpoint_urls
            ),
            "request_count": (
                total_request_count
            ),
            "http_success_count": (
                http_success_count
            ),
            "transport_error_count": (
                transport_error_count
            ),
            "circuit_breaker_count": (
                circuit_breaker_count
            ),
            "raw_record_count": len(
                raw_records
            ),
            "canonical_endpoint_count": len(
                canonical_records
            ),
            "recovered_endpoint_count": len(
                recovered_endpoints
            ),
            "candidate_endpoint_count": len(
                candidate_endpoints
            ),
            "unresolved_endpoint_count": len(
                unresolved_endpoints
            ),
            "recovered_source_family_count": (
                recovered_family_count
            ),
            "next_stage_endpoint_pool_count": len(
                next_stage_endpoint_pool
            ),
        },

        "classification_counts": dict(
            sorted(
                classification_counts.items()
            )
        ),

        "family_recovered_counts": dict(
            sorted(
                family_recovered_counts.items()
            )
        ),

        "source_results": source_results,

        "official_host_seeds": (
            official_host_seeds
        ),

        "recovered_endpoints": (
            recovered_endpoints
        ),

        "candidate_endpoints": (
            candidate_endpoints
        ),

        "unresolved_endpoints": (
            unresolved_endpoints
        ),

        "next_stage_endpoint_pool": (
            next_stage_endpoint_pool
        ),

        "all_canonical_endpoints": (
            canonical_records
        ),

        "resolution": resolution,

        "next_action": next_action,

        "verified_positive": False,

        "runtime_registration_allowed": False,

        "site_positive_allowed": False,

        "final_positive_promotion_allowed": False,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            output_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ========================================================
    # RESULT
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "HISTORICAL SOURCE FAMILY ENTRY ENDPOINT RECOVERY RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "Pending source target count:",
        len(
            pending_source_targets
        ),
    )

    print(
        "Official host seed count:",
        len(
            official_host_seeds
        ),
    )

    print(
        "Request count:",
        total_request_count,
    )

    print(
        "HTTP success count:",
        http_success_count,
    )

    print(
        "Transport error count:",
        transport_error_count,
    )

    print(
        "Canonical endpoint count:",
        len(
            canonical_records
        ),
    )

    print(
        "Recovered endpoint count:",
        len(
            recovered_endpoints
        ),
    )

    print(
        "Recovered source family count:",
        recovered_family_count,
    )

    print()

    for source_family in sorted(
        TARGET_SOURCE_FAMILIES
    ):

        print(
            f"{source_family}:",
            family_recovered_counts.get(
                source_family,
                0,
            ),
        )

    if recovered_endpoints:

        print()

        print(
            "RECOVERED HISTORICAL ENTRY ENDPOINTS"
        )

        print(
            "-" * 60
        )

        for index, item in enumerate(
            recovered_endpoints[
                :150
            ],
            start=1,
        ):

            print(
                f"[{index}] "
                f"{item.get('source_family')}"
            )

            print(
                "Region:",
                item.get(
                    "region"
                )
                or "-",
            )

            print(
                "Role:",
                item.get(
                    "endpoint_role"
                ),
            )

            print(
                "URL:",
                item.get(
                    "url"
                ),
            )

            print(
                "HTTP:",
                item.get(
                    "http_status"
                ),
            )

            print(
                "Score:",
                item.get(
                    "score"
                ),
            )

            print()

    # ========================================================
    # VALIDATION
    # ========================================================

    canonical_keys = {
        (
            normalize_space(
                item.get(
                    "source_family"
                )
            ),
            canonicalize_url(
                item.get(
                    "url"
                )
                or ""
            ),
        )
        for item in canonical_records
    }

    next_stage_keys = {
        (
            normalize_space(
                item.get(
                    "source_family"
                )
            ),
            canonicalize_url(
                item.get(
                    "url"
                )
                or ""
            ),
        )
        for item in next_stage_endpoint_pool
    }

    all_classes_valid = all(
        item.get(
            "classification"
        )
        in VALID_CLASSES
        for item in canonical_records
    )

    all_roles_valid = all(
        item.get(
            "endpoint_role"
        )
        in VALID_ENDPOINT_ROLES
        for item in canonical_records
    )

    all_recovered_official = all(
        item.get(
            "official_host"
        )
        is True
        for item in recovered_endpoints
    )

    recovered_modern_repeat_leakage = sum(
        1
        for item in recovered_endpoints
        if item.get(
            "modern_endpoint_repeat"
        )
        is True
    )

    recovered_non_official_leakage = sum(
        1
        for item in recovered_endpoints
        if item.get(
            "official_host"
        )
        is not True
    )

    recovered_role_incompatible_leakage = sum(
        1
        for item in recovered_endpoints
        if item.get(
            "source_family_role_compatible"
        )
        is not True
    )

    positive_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "verified_positive"
        )
        is not False
    )

    runtime_registration_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "runtime_registration_allowed"
        )
        is not False
    )

    site_positive_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "site_positive_allowed"
        )
        is not False
    )

    global_budget_preserved = (
        total_request_count
        <= MAX_TOTAL_REQUESTS
    )

    host_budget_preserved = all(
        count
        <= MAX_REQUESTS_PER_HOST
        for count in host_request_counts.values()
    )

    source_family_budget_preserved = all(
        count
        <= MAX_REQUESTS_PER_SOURCE_FAMILY
        for count
        in source_family_request_counts.values()
    )

    validations = {
        "target name": (
            TARGET_NAME
            == "개발밀도관리구역"
        ),

        "standard code": (
            STANDARD_CODE
            == "UQQ700"
        ),

        "Q-stage input exists": (
            Q_STAGE_INPUT_PATH.exists()
        ),

        "P-stage input exists": (
            P_STAGE_INPUT_PATH.exists()
        ),

        "O-stage input exists": (
            O_STAGE_INPUT_PATH.exists()
        ),

        "H-stage input exists": (
            H_STAGE_INPUT_PATH.exists()
        ),

        "Q-stage input parsed": (
            isinstance(
                q_data,
                dict,
            )
        ),

        "pending source targets loaded": (
            len(
                pending_source_targets
            )
            > 0
        ),

        "only pending source families loaded": all(
            item.get(
                "source_family"
            )
            in TARGET_SOURCE_FAMILIES
            for item in pending_source_targets
        ),

        "official host memory enabled": True,

        "institution endpoint recovery enabled": True,

        "modern endpoint brute-force repeat disabled": (
            output_data[
                "method"
            ][
                "modern_endpoint_bruteforce_repeat"
            ]
            is False
        ),

        "search engine scraping disabled": (
            output_data[
                "method"
            ][
                "search_engine_scraping"
            ]
            is False
        ),

        "endpoint-document role separation enabled": (
            output_data[
                "method"
            ][
                "endpoint_document_role_separation"
            ]
            is True
        ),

        "global request budget preserved": (
            global_budget_preserved
        ),

        "host request budget preserved": (
            host_budget_preserved
        ),

        "source family request budget preserved": (
            source_family_budget_preserved
        ),

        "canonical endpoints unique": (
            len(
                canonical_keys
            )
            == len(
                canonical_records
            )
        ),

        "all endpoint classes valid": (
            all_classes_valid
        ),

        "all endpoint roles valid": (
            all_roles_valid
        ),

        "all recovered endpoints official": (
            all_recovered_official
        ),

        "recovered modern endpoint repeat leakage zero": (
            recovered_modern_repeat_leakage
            == 0
        ),

        "recovered non-official leakage zero": (
            recovered_non_official_leakage
            == 0
        ),

        "recovered role incompatible leakage zero": (
            recovered_role_incompatible_leakage
            == 0
        ),

        "next-stage endpoint pool unique": (
            len(
                next_stage_keys
            )
            == len(
                next_stage_endpoint_pool
            )
        ),

        "verified positive leakage zero": (
            positive_leakage
            == 0
        ),

        "runtime registration leakage zero": (
            runtime_registration_leakage
            == 0
        ),

        "SITE TRUE leakage zero": (
            site_positive_leakage
            == 0
        ),

        "runtime registration remains blocked": (
            output_data[
                "runtime_registration_allowed"
            ]
            is False
        ),

        "SITE TRUE remains blocked": (
            output_data[
                "site_positive_allowed"
            ]
            is False
        ),

        "final positive promotion remains blocked": (
            output_data[
                "final_positive_promotion_allowed"
            ]
            is False
        ),

        "output written": (
            OUTPUT_PATH.exists()
            and OUTPUT_PATH.stat().st_size
            > 0
        ),
    }

    print()

    print(
        "=" * 60
    )

    print(
        "RESOLUTION"
    )

    print(
        "=" * 60
    )

    print(
        resolution
    )

    print()

    print(
        next_action
    )

    print()

    print(
        "Output:",
        OUTPUT_PATH,
    )

    print()

    print(
        "=" * 60
    )

    print(
        "VALIDATION"
    )

    print(
        "=" * 60
    )

    for name, passed in validations.items():

        print(
            f"{name}: {passed}"
        )

    print()

    print(
        "Recovered modern endpoint repeat leakage:",
        recovered_modern_repeat_leakage,
    )

    print(
        "Recovered non-official leakage:",
        recovered_non_official_leakage,
    )

    print(
        "Recovered role incompatible leakage:",
        recovered_role_incompatible_leakage,
    )

    print(
        "Verified positive leakage:",
        positive_leakage,
    )

    print(
        "Runtime registration leakage:",
        runtime_registration_leakage,
    )

    print(
        "SITE TRUE leakage:",
        site_positive_leakage,
    )

    print()

    all_pass = all(
        validations.values()
    )

    print(
        f"all_pass: {all_pass}"
    )

    if not all_pass:

        failed = [
            name
            for name, passed
            in validations.items()
            if not passed
        ]

        print()

        print(
            "FAILED:"
        )

        for name in failed:

            print(
                f"- {name}"
            )

        raise AssertionError(
            "Development density management area "
            "historical source family entry endpoint recovery "
            "regression failed"
        )


if __name__ == "__main__":
    main()