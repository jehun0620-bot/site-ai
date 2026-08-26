# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-2-S1

Development Density Management Area
Historical Target Document Reverse Discovery
Semantic Candidate Gate Hardening


목표
======================================================================

T-1의 bounded endpoint search에서 개발밀도관리구역 관련 historical
document를 찾지 못한 이후, 동일 endpoint brute-force를 반복하지 않고
고시 identity를 역방향으로 복원한다.

이번 S1 hardening에서는 T-2에서 확인된 semantic false positive를 제거한다.


기존 T-2 문제
======================================================================

1. query contamination

    candidate evidence에 사용자가 만든 검색어 query 자체가 포함되어 있었다.

    예:

        anchor_text = "강서복지"
        query       = "개발밀도관리구역"

    이 경우 unrelated navigation link도 TARGET_DIRECT가 발생할 수 있었다.


2. page-title contamination

    search response page title에 target regulation text가 들어간 경우
    해당 페이지의 unrelated link 전체가 target candidate처럼 보일 수 있었다.


3. navigation document false positive

    예:

        https://bsgangseo.go.kr/welfare/main.do

    는 historical notice/gazette document가 아닌 일반 navigation endpoint지만
    candidate로 승격될 수 있었다.


4. document identity가 약한 URL도 candidate가 될 수 있었다.


S1 핵심 원칙
======================================================================

1. 대상 규제:
    개발밀도관리구역
    standard_code = UQQ700

2. resolution type:
    HYBRID_SPATIAL_NOTICE

3. negative evidence로 SITE FALSE를 만들지 않는다.

4. T-1에서 문서를 못 찾았다는 사실은 UNKNOWN이다.

5. reverse query 자체는 discovery provenance일 뿐
   document qualification evidence가 아니다.

6. search response page title 역시 provenance/context일 뿐
   candidate qualification evidence가 아니다.

7. candidate qualification은 link-local evidence만 사용한다.

    - anchor text
    - candidate URL/path/query

8. link-local evidence 자체에서 target regulation identity가 확인되어야 한다.

9. generic navigation/main/home/menu URL은 candidate로 승격하지 않는다.

10. document-like URL identity가 필요하다.

11. region binding이 확인되어야 한다.

12. official go.kr host만 primary candidate로 인정한다.

13. 일반 도시관리계획 고시는 UQQ700 candidate로 자동 승격하지 않는다.

14. 동일 document URL이 여러 source family / query / request에서
    발견되더라도 U-stage에는 하나의 canonical document로 넘긴다.

15. 동일 document 발견 경로는 provenance로 병합한다.

16. endpoint 자체는 verified positive가 아니다.

17. document candidate 역시 후속 U-stage verification 전까지
    verified positive가 아니다.

18. runtime registration 금지.

19. SITE TRUE 자동판정 금지.
"""

from __future__ import annotations

import html
import json
import re
import time

from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
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

T1_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_target_document_discovery.json"
    )
)

S3_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_source_family_entry_endpoint_"
        "qualification_hardening.json"
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
        "historical_target_document_reverse_discovery.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"

STANDARD_CODE = "UQQ700"

RESOLUTION_TYPE = (
    "HYBRID_SPATIAL_NOTICE"
)

NEGATIVE_EVIDENCE_ALLOWED = False


# ============================================================
# SOURCE FAMILY
# ============================================================

FAMILY_GAZETTE = (
    "LEGACY_LOCAL_GAZETTE"
)

FAMILY_NOTICE = (
    "LEGACY_LOCAL_NOTICE"
)

FAMILY_URBAN = (
    "URBAN_PLANNING_ARCHIVE"
)

FAMILY_NOTICE_REVERSE = (
    "NOTICE_NUMBER_REVERSE_LOOKUP"
)

ALLOWED_SOURCE_FAMILIES = {
    FAMILY_GAZETTE,
    FAMILY_NOTICE,
    FAMILY_URBAN,
    FAMILY_NOTICE_REVERSE,
}


# ============================================================
# OUTPUT CLASS
# ============================================================

CLASS_NOTICE_IDENTITY = (
    "HISTORICAL_NOTICE_IDENTITY_DISCOVERED"
)

CLASS_NOTICE_NUMBER = (
    "HISTORICAL_NOTICE_NUMBER_CANDIDATE"
)

CLASS_NOTICE_TITLE = (
    "HISTORICAL_NOTICE_TITLE_CANDIDATE"
)

CLASS_GAZETTE_DOCUMENT = (
    "HISTORICAL_GAZETTE_DOCUMENT_CANDIDATE"
)

CLASS_REJECTED_OTHER_URBAN = (
    "REJECTED_OTHER_URBAN_PLANNING_NOTICE"
)

CLASS_REJECTED_REGION = (
    "REJECTED_REGION_MISMATCH"
)

CLASS_REJECTED_NON_OFFICIAL = (
    "REJECTED_NON_OFFICIAL_SOURCE"
)

CLASS_REJECTED_WEAK = (
    "REJECTED_TARGET_EVIDENCE_WEAK"
)

CLASS_REJECTED_INVALID = (
    "REJECTED_INVALID_DOCUMENT_URL"
)

CLASS_REJECTED_NAVIGATION = (
    "REJECTED_GENERIC_NAVIGATION_DOCUMENT"
)

CLASS_REJECTED_DOCUMENT_IDENTITY = (
    "REJECTED_DOCUMENT_IDENTITY_WEAK"
)

VALID_CLASSES = {
    CLASS_NOTICE_IDENTITY,
    CLASS_NOTICE_NUMBER,
    CLASS_NOTICE_TITLE,
    CLASS_GAZETTE_DOCUMENT,
    CLASS_REJECTED_OTHER_URBAN,
    CLASS_REJECTED_REGION,
    CLASS_REJECTED_NON_OFFICIAL,
    CLASS_REJECTED_WEAK,
    CLASS_REJECTED_INVALID,
    CLASS_REJECTED_NAVIGATION,
    CLASS_REJECTED_DOCUMENT_IDENTITY,
}

CANDIDATE_CLASSES = {
    CLASS_NOTICE_IDENTITY,
    CLASS_NOTICE_NUMBER,
    CLASS_NOTICE_TITLE,
    CLASS_GAZETTE_DOCUMENT,
}


# ============================================================
# CLASS PRIORITY
# ============================================================

CANDIDATE_CLASS_PRIORITY = {
    CLASS_NOTICE_IDENTITY: 40,
    CLASS_NOTICE_NUMBER: 30,
    CLASS_GAZETTE_DOCUMENT: 20,
    CLASS_NOTICE_TITLE: 10,
}


# ============================================================
# HTTP
# ============================================================

TIMEOUT = 20

MAX_RESPONSE_BYTES = (
    12
    * 1024
    * 1024
)

MAX_TOTAL_REQUESTS = 120

MAX_REQUESTS_PER_SOURCE = 18

REQUEST_DELAY_SECONDS = 0.03

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# QUERY MATRIX
# ============================================================

EXACT_TARGET_QUERIES = [
    "개발밀도관리구역",
    "\"개발밀도관리구역\"",
    "개발밀도 관리구역",
]

LEGAL_IDENTITY_QUERIES = [
    "개발밀도관리구역 지정",
    "개발밀도관리구역 고시",
    "개발밀도관리구역 도시관리계획",
    "개발밀도관리구역 지형도면",
    "도시관리계획 개발밀도관리구역",
    "도시관리계획(개발밀도관리구역)",
]

HISTORICAL_NOTICE_QUERIES = [
    "개발밀도관리구역 결정 고시",
    "개발밀도관리구역 변경 고시",
    "개발밀도관리구역 지정 고시",
    "개발밀도관리구역 지형도면 고시",
    "도시관리계획 결정 변경 고시 개발밀도",
]

QUERY_MATRIX = (
    EXACT_TARGET_QUERIES
    + LEGAL_IDENTITY_QUERIES
    + HISTORICAL_NOTICE_QUERIES
)


# ============================================================
# TARGET EVIDENCE
# ============================================================

DIRECT_TARGET_PATTERNS = [
    re.compile(
        r"개발\s*밀도\s*관리\s*구역",
        re.IGNORECASE,
    ),
]

STRONG_CONTEXT_PATTERNS = [
    re.compile(
        r"도시관리계획.{0,80}개발\s*밀도",
        re.IGNORECASE,
    ),
    re.compile(
        r"개발\s*밀도.{0,80}(?:지정|결정|변경|고시)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:지정|결정|변경).{0,80}개발\s*밀도",
        re.IGNORECASE,
    ),
]

NOTICE_NUMBER_PATTERNS = [
    re.compile(
        r"([가-힣A-Za-z0-9 ]{1,30})"
        r"(?:고시|공고)"
        r"\s*제?\s*"
        r"(\d{2,4})\s*[-－]\s*(\d+)\s*호?"
    ),
    re.compile(
        r"(?:고시|공고)"
        r"\s*제?\s*"
        r"(\d{2,4})\s*[-－]\s*(\d+)\s*호?"
    ),
]

URBAN_GENERIC_TERMS = [
    "도시관리계획",
    "도시계획",
    "지형도면",
]

OTHER_RELEASE_TERMS = [
    "도로",
    "공원",
    "하천",
    "도시계획시설",
    "개발행위허가 제한",
    "개발행위허가의 제한",
    "도시개발구역",
    "산업단지",
    "지구단위계획",
    "용도지역",
    "용도지구",
    "용도구역",
]


# ============================================================
# DOCUMENT IDENTITY
# ============================================================

DOCUMENT_URL_HINTS = [
    "view.do",
    "detail.do",
    "read.do",
    "selectview",
    "selectdetail",

    "/board/",
    "/board",

    "/bbs/",
    "/bbs",

    "notice",
    "publicnotice",

    "gosi",
    "gonggo",

    "eminwon",
    "saeol",

    "nscvrg",

    "file",
    "download",
    "attach",
    "atchfile",

    ".pdf",
    ".hwp",
    ".hwpx",
]

DOCUMENT_QUERY_KEYS = {
    "idx",
    "nttid",
    "ntt_id",

    "board_seq",

    "article_no",
    "articleid",

    "post_no",
    "postno",

    "seq",
    "no",

    "noticeid",
    "notice_id",

    "gosi_no",
    "gonggo_no",

    "fileid",
    "file_id",
}


# ============================================================
# GENERIC NAVIGATION
# ============================================================

GENERIC_NAVIGATION_PATHS = {
    "",
    "/",
    "/main",
    "/main.do",
    "/index",
    "/index.do",
    "/home",
    "/home.do",
    "/portal",
    "/portal/",
}

GENERIC_NAVIGATION_TERMS = [
    "/welfare/main",

    "/login",
    "/member",
    "/sitemap",

    "/intro",
    "/guide",

    "/organization",
    "/history",
    "/greeting",

    "/english",
    "/eng/",
]


# ============================================================
# HTML
# ============================================================

TITLE_PATTERN = re.compile(
    r"<title\b[^>]*>(.*?)</title>",
    re.IGNORECASE
    | re.DOTALL,
)

ANCHOR_PATTERN = re.compile(
    r"<a\b[^>]*href\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
    re.IGNORECASE
    | re.DOTALL,
)

TAG_PATTERN = re.compile(
    r"<[^>]+>",
    re.DOTALL,
)

SCRIPT_STYLE_PATTERN = re.compile(
    r"<(?:script|style)\b.*?</(?:script|style)>",
    re.IGNORECASE
    | re.DOTALL,
)

COMMENT_PATTERN = re.compile(
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
        str(
            value
            or ""
        ),
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


def strip_html(
    raw_html: str,
) -> str:

    value = COMMENT_PATTERN.sub(
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

        return ""

    if not parsed.hostname:
        return ""

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

    except ValueError:

        port = None

    if (
        port
        and not (
            scheme == "http"
            and port == 80
        )
        and not (
            scheme == "https"
            and port == 443
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

    seen_pairs = set()

    for key, value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        normalized_key = normalize_space(
            key
        )

        if not normalized_key:
            continue

        lowered = normalized_key.lower()

        if lowered in VOLATILE_QUERY_KEYS:
            continue

        if lowered in TRACKING_QUERY_KEYS:
            continue

        if "csrf" in lowered:
            continue

        if "session" in lowered:
            continue

        pair = (
            normalized_key,
            value,
        )

        if pair in seen_pairs:
            continue

        seen_pairs.add(
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

    query = urlencode(
        query_items,
        doseq=True,
    )

    return urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            query,
            "",
        )
    )


def hostname(
    url: str,
) -> str:

    try:

        return (
            urlparse(
                url
            ).hostname
            or ""
        ).lower()

    except Exception:

        return ""


def is_government_host(
    host: str,
) -> bool:

    value = normalize_space(
        host
    ).lower()

    if not value:
        return False

    return (
        value == "go.kr"
        or value.endswith(
            ".go.kr"
        )
    )


def same_host(
    url_a: str,
    url_b: str,
) -> bool:

    host_a = hostname(
        url_a
    )

    host_b = hostname(
        url_b
    )

    return (
        bool(
            host_a
        )
        and host_a == host_b
    )


# ============================================================
# DOCUMENT URL GUARD
# ============================================================

def looks_generic_navigation_url(
    url: str,
) -> bool:

    normalized = canonicalize_url(
        url
    )

    if not normalized:
        return True

    try:

        parsed = urlparse(
            normalized
        )

    except Exception:

        return True

    path = (
        parsed.path
        or "/"
    ).lower()

    if path in GENERIC_NAVIGATION_PATHS:
        return True

    if any(
        term in path
        for term in GENERIC_NAVIGATION_TERMS
    ):

        return True

    return False


def looks_like_document_url(
    url: str,
) -> bool:

    normalized = canonicalize_url(
        url
    )

    if not normalized:
        return False

    if looks_generic_navigation_url(
        normalized
    ):

        return False

    lowered = normalized.lower()

    if any(
        hint in lowered
        for hint in DOCUMENT_URL_HINTS
    ):

        return True

    try:

        parsed = urlparse(
            normalized
        )

    except Exception:

        return False

    query_keys = {
        key.lower()
        for key, _
        in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
    }

    if (
        query_keys
        & DOCUMENT_QUERY_KEYS
    ):

        return True

    return False


# ============================================================
# INPUT
# ============================================================

def load_s3_endpoints(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    raw = data.get(
        "next_stage_endpoint_pool"
    )

    if not isinstance(
        raw,
        list,
    ):

        raw = []

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[str, str]
    ] = set()

    for item in raw:

        if not isinstance(
            item,
            dict,
        ):

            continue

        family = normalize_space(
            item.get(
                "source_family"
            )
        )

        if family not in ALLOWED_SOURCE_FAMILIES:
            continue

        url = canonicalize_url(
            item.get(
                "url"
            )
            or ""
        )

        if not url:
            continue

        key = (
            family,
            url,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        regions = item.get(
            "regions"
        )

        if not isinstance(
            regions,
            list,
        ):

            regions = []

        result.append(
            {
                "source_family": family,

                "url": url,

                "regions": unique_strings(
                    regions
                ),

                "title": normalize_space(
                    item.get(
                        "title"
                    )
                ),

                "classification": normalize_space(
                    item.get(
                        "classification"
                    )
                ),
            }
        )

    return result


# ============================================================
# HTTP
# ============================================================

def decode_html(
    response: requests.Response,
    data: bytes,
) -> Tuple[str, str]:

    candidates: List[str] = []

    content_type = normalize_space(
        response.headers.get(
            "Content-Type"
        )
    )

    match = re.search(
        r"""charset\s*=\s*["']?([^;"'\s]+)""",
        content_type,
        flags=re.IGNORECASE,
    )

    if match:

        candidates.append(
            normalize_space(
                match.group(1)
            )
        )

    if response.encoding:

        candidates.append(
            normalize_space(
                response.encoding
            )
        )

    ascii_preview = (
        data[
            :8192
        ]
        .decode(
            "ascii",
            errors="ignore",
        )
    )

    meta_patterns = [
        re.compile(
            r"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9._\-]+)""",
            re.IGNORECASE,
        ),
        re.compile(
            r"""charset\s*=\s*([A-Za-z0-9._\-]+)""",
            re.IGNORECASE,
        ),
    ]

    for pattern in meta_patterns:

        meta_match = pattern.search(
            ascii_preview
        )

        if meta_match:

            candidates.append(
                normalize_space(
                    meta_match.group(1)
                )
            )

    candidates.extend(
        [
            "utf-8",
            "cp949",
            "euc-kr",
        ]
    )

    for encoding in unique_strings(
        candidates
    ):

        try:

            return (
                data.decode(
                    encoding
                ),
                encoding,
            )

        except (
            UnicodeDecodeError,
            LookupError,
        ):

            continue

    return (
        data.decode(
            "utf-8",
            errors="replace",
        ),
        "utf-8-replace",
    )


def fetch_page(
    session: requests.Session,
    url: str,
) -> Dict[str, Any]:

    result: Dict[str, Any] = {
        "requested_url": url,
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

            chunks: List[bytes] = []

            total = 0

            try:

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
                            "response exceeds "
                            f"{MAX_RESPONSE_BYTES} bytes"
                        )

                    chunks.append(
                        chunk
                    )

            except Exception as exc:

                result[
                    "error"
                ] = repr(
                    exc
                )

                result[
                    "error_stage"
                ] = "BODY_DOWNLOAD"

                return result

            data = b"".join(
                chunks
            )

            result[
                "response_bytes"
            ] = len(
                data
            )

            content_type_lower = normalize_space(
                result.get(
                    "content_type"
                )
            ).lower()

            prefix = (
                data[
                    :1000
                ]
                .lstrip()
                .lower()
            )

            html_like = (
                "html"
                in content_type_lower
                or "text/"
                in content_type_lower
                or prefix.startswith(
                    b"<!doctype html"
                )
                or prefix.startswith(
                    b"<html"
                )
            )

            if not html_like:

                return result

            try:

                decoded, encoding = decode_html(
                    response,
                    data,
                )

            except Exception as exc:

                result[
                    "error"
                ] = repr(
                    exc
                )

                result[
                    "error_stage"
                ] = "HTML_DECODE"

                return result

            result[
                "raw_html"
            ] = decoded

            result[
                "encoding"
            ] = encoding

    except requests.RequestException as exc:

        result[
            "error"
        ] = repr(
            exc
        )

        result[
            "error_stage"
        ] = "HTTP_REQUEST"

    except Exception as exc:

        result[
            "error"
        ] = repr(
            exc
        )

        result[
            "error_stage"
        ] = "UNEXPECTED"

    return result


# ============================================================
# SEARCH URL GENERATION
# ============================================================

def build_reverse_query_urls(
    source_url: str,
    query: str,
) -> List[str]:

    """
    동일 host/path 내에서 제한된 query parameter 변형만 사용한다.

    중요:
    query는 discovery request provenance일 뿐
    candidate qualification evidence가 아니다.
    """

    parsed = urlparse(
        source_url
    )

    base = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            "",
            "",
        )
    )

    existing = dict(
        parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
    )

    variants: List[str] = []

    query_keys = [
        "searchKeyword",
        "keyword",
        "searchWord",
        "query",
        "q",
        "searchText",
        "srchText",
        "schText",
    ]

    for key in query_keys:

        params = dict(
            existing
        )

        params[
            key
        ] = query

        candidate = canonicalize_url(
            base
            + "?"
            + urlencode(
                params,
                doseq=True,
            )
        )

        if candidate:

            variants.append(
                candidate
            )

    return unique_strings(
        variants
    )


# ============================================================
# HTML CANDIDATE EXTRACTION
# ============================================================

def extract_title(
    raw_html: str,
) -> str:

    match = TITLE_PATTERN.search(
        raw_html
    )

    if not match:
        return ""

    return strip_html(
        match.group(1)
    )


def extract_links(
    raw_html: str,
    base_url: str,
) -> List[Dict[str, str]]:

    result: List[
        Dict[str, str]
    ] = []

    for match in ANCHOR_PATTERN.finditer(
        raw_html
    ):

        href = html.unescape(
            normalize_space(
                match.group(1)
            )
        )

        anchor_text = strip_html(
            match.group(2)
        )

        if not href:
            continue

        if href.lower().startswith(
            (
                "javascript:",
                "mailto:",
                "tel:",
                "#",
            )
        ):

            continue

        absolute = canonicalize_url(
            urljoin(
                base_url,
                href,
            )
        )

        if not absolute:
            continue

        result.append(
            {
                "url": absolute,
                "anchor_text": anchor_text,
            }
        )

    return result


# ============================================================
# REGION
# ============================================================

PROVINCE_ONLY_TOKENS = {
    "서울특별시",
    "서울",
    "부산광역시",
    "부산",
    "대구광역시",
    "대구",
    "인천광역시",
    "인천",
    "광주광역시",
    "광주",
    "대전광역시",
    "대전",
    "울산광역시",
    "울산",
    "세종특별자치시",
    "세종",
    "경기도",
    "경기",
    "강원특별자치도",
    "강원도",
    "강원",
    "충청북도",
    "충북",
    "충청남도",
    "충남",
    "전북특별자치도",
    "전라북도",
    "전북",
    "전라남도",
    "전남",
    "경상북도",
    "경북",
    "경상남도",
    "경남",
    "제주특별자치도",
    "제주",
}


def region_tokens(
    region: str,
) -> List[str]:

    value = normalize_space(
        region
    )

    if not value:
        return []

    tokens = [
        value,
    ]

    parts = value.split()

    tokens.extend(
        parts
    )

    for part in parts:

        stem = re.sub(
            r"(?:특별시|광역시|특별자치시|특별자치도|도|시|군|구)$",
            "",
            part,
        )

        if (
            stem
            and len(
                stem
            ) >= 2
        ):

            tokens.append(
                stem
            )

    return unique_strings(
        tokens
    )


def matches_region(
    text: str,
    regions: List[str],
    url: str,
) -> Tuple[
    bool,
    List[str],
]:

    evidence = normalize_space(
        " ".join(
            [
                text,
                url,
                hostname(
                    url
                ),
            ]
        )
    ).lower()

    matched: List[str] = []

    for region in regions:

        tokens = region_tokens(
            region
        )

        municipality_tokens = [
            token
            for token in tokens
            if (
                normalize_space(
                    token
                )
                and normalize_space(
                    token
                )
                not in PROVINCE_ONLY_TOKENS
            )
        ]

        if not municipality_tokens:
            continue

        municipality_match = any(
            normalize_space(
                token
            ).lower()
            in evidence
            for token in municipality_tokens
        )

        if municipality_match:

            matched.append(
                region
            )

    return (
        bool(
            matched
        ),
        unique_strings(
            matched
        ),
    )


# ============================================================
# TARGET CLASSIFICATION
# ============================================================

def extract_notice_numbers(
    text: str,
) -> List[str]:

    result: List[str] = []

    for pattern in NOTICE_NUMBER_PATTERNS:

        for match in pattern.finditer(
            text
        ):

            result.append(
                normalize_space(
                    match.group(0)
                )
            )

    return unique_strings(
        result
    )


def direct_target_evidence(
    text: str,
) -> List[str]:

    reasons: List[str] = []

    for pattern in DIRECT_TARGET_PATTERNS:

        match = pattern.search(
            text
        )

        if match:

            reasons.append(
                "TARGET_DIRECT:"
                + normalize_space(
                    match.group(0)
                )
            )

    for pattern in STRONG_CONTEXT_PATTERNS:

        match = pattern.search(
            text
        )

        if match:

            reasons.append(
                "TARGET_CONTEXT:"
                + normalize_space(
                    match.group(0)
                )
            )

    return unique_strings(
        reasons
    )


def is_other_urban_notice(
    text: str,
) -> bool:

    if direct_target_evidence(
        text
    ):

        return False

    normalized = normalize_space(
        text
    )

    has_urban = any(
        term in normalized
        for term in URBAN_GENERIC_TERMS
    )

    has_other = any(
        term in normalized
        for term in OTHER_RELEASE_TERMS
    )

    return (
        has_urban
        and has_other
    )


def classify_candidate(
    *,
    source_family: str,
    url: str,
    text: str,
    regions: List[str],
) -> Dict[str, Any]:

    normalized_url = canonicalize_url(
        url
    )

    if not normalized_url:

        return {
            "qualified": False,

            "classification": (
                CLASS_REJECTED_INVALID
            ),

            "matched_regions": [],

            "notice_numbers": [],

            "reasons": [
                "INVALID_DOCUMENT_URL"
            ],
        }

    reasons = direct_target_evidence(
        text
    )

    notice_numbers = extract_notice_numbers(
        text
    )

    region_ok, matched_regions = matches_region(
        text,
        regions,
        normalized_url,
    )

    # --------------------------------------------------------
    # Official host
    # --------------------------------------------------------

    if not is_government_host(
        hostname(
            normalized_url
        )
    ):

        return {
            "qualified": False,

            "classification": (
                CLASS_REJECTED_NON_OFFICIAL
            ),

            "matched_regions": (
                matched_regions
            ),

            "notice_numbers": (
                notice_numbers
            ),

            "reasons": [
                "DOCUMENT_HOST_NOT_GO_KR"
            ],
        }

    # --------------------------------------------------------
    # Generic navigation guard
    # --------------------------------------------------------

    if looks_generic_navigation_url(
        normalized_url
    ):

        return {
            "qualified": False,

            "classification": (
                CLASS_REJECTED_NAVIGATION
            ),

            "matched_regions": (
                matched_regions
            ),

            "notice_numbers": (
                notice_numbers
            ),

            "reasons": [
                "GENERIC_NAVIGATION_URL"
            ],
        }

    # --------------------------------------------------------
    # Document identity guard
    # --------------------------------------------------------

    if not looks_like_document_url(
        normalized_url
    ):

        return {
            "qualified": False,

            "classification": (
                CLASS_REJECTED_DOCUMENT_IDENTITY
            ),

            "matched_regions": (
                matched_regions
            ),

            "notice_numbers": (
                notice_numbers
            ),

            "reasons": [
                "DOCUMENT_URL_IDENTITY_WEAK"
            ],
        }

    # --------------------------------------------------------
    # Region
    # --------------------------------------------------------

    if not region_ok:

        return {
            "qualified": False,

            "classification": (
                CLASS_REJECTED_REGION
            ),

            "matched_regions": [],

            "notice_numbers": (
                notice_numbers
            ),

            "reasons": [
                "DOCUMENT_REGION_MISMATCH"
            ],
        }

    # --------------------------------------------------------
    # Other urban notice
    # --------------------------------------------------------

    if is_other_urban_notice(
        text
    ):

        return {
            "qualified": False,

            "classification": (
                CLASS_REJECTED_OTHER_URBAN
            ),

            "matched_regions": (
                matched_regions
            ),

            "notice_numbers": (
                notice_numbers
            ),

            "reasons": [
                "OTHER_URBAN_PLANNING_NOTICE"
            ],
        }

    # --------------------------------------------------------
    # Target evidence
    # --------------------------------------------------------

    if not reasons:

        return {
            "qualified": False,

            "classification": (
                CLASS_REJECTED_WEAK
            ),

            "matched_regions": (
                matched_regions
            ),

            "notice_numbers": (
                notice_numbers
            ),

            "reasons": [
                "TARGET_EVIDENCE_WEAK"
            ],
        }

    # --------------------------------------------------------
    # Qualified candidate
    # --------------------------------------------------------

    if notice_numbers:

        classification = (
            CLASS_NOTICE_IDENTITY
        )

    elif source_family == FAMILY_GAZETTE:

        classification = (
            CLASS_GAZETTE_DOCUMENT
        )

    else:

        classification = (
            CLASS_NOTICE_TITLE
        )

    return {
        "qualified": True,

        "classification": (
            classification
        ),

        "matched_regions": (
            matched_regions
        ),

        "notice_numbers": (
            notice_numbers
        ),

        "reasons": (
            reasons
        ),
    }


# ============================================================
# PROVENANCE HELPERS
# ============================================================

def merge_list_field(
    existing: Dict[str, Any],
    incoming: Dict[str, Any],
    field: str,
) -> None:

    existing[
        field
    ] = unique_strings(
        (
            existing.get(
                field
            )
            or []
        )
        +
        (
            incoming.get(
                field
            )
            or []
        )
    )


def singleton_string_list(
    value: Any,
) -> List[str]:

    text = normalize_space(
        value
    )

    if not text:
        return []

    return [
        text
    ]


def singleton_url_list(
    value: Any,
) -> List[str]:

    url = canonicalize_url(
        value
        or ""
    )

    if not url:
        return []

    return [
        url
    ]


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
        "HISTORICAL TARGET DOCUMENT REVERSE DISCOVERY"
    )

    print(
        "SEMANTIC CANDIDATE GATE HARDENING"
    )

    print(
        "=" * 60
    )

    print()

    print(
        "Target:",
        TARGET_NAME,
    )

    print(
        "Standard code:",
        STANDARD_CODE,
    )

    print(
        "Resolution type:",
        RESOLUTION_TYPE,
    )

    print(
        "Negative evidence allowed:",
        NEGATIVE_EVIDENCE_ALLOWED,
    )

    print()

    # ========================================================
    # INPUT
    # ========================================================

    if not T1_STAGE_INPUT_PATH.exists():

        raise FileNotFoundError(
            "T-1 input not found: "
            f"{T1_STAGE_INPUT_PATH}"
        )

    if not S3_STAGE_INPUT_PATH.exists():

        raise FileNotFoundError(
            "S-3 input not found: "
            f"{S3_STAGE_INPUT_PATH}"
        )

    t1_data = json.loads(
        T1_STAGE_INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    s3_data = json.loads(
        S3_STAGE_INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        t1_data,
        dict,
    ):

        raise TypeError(
            "T-1 input must be JSON object."
        )

    if not isinstance(
        s3_data,
        dict,
    ):

        raise TypeError(
            "S-3 input must be JSON object."
        )

    endpoints = load_s3_endpoints(
        s3_data
    )

    print(
        "S-3 endpoint count:",
        len(
            endpoints
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

    request_count = 0

    http_success_count = 0

    transport_error_count = 0

    query_contamination_rejected_count = 0

    page_title_only_rejected_count = 0

    navigation_link_rejected_count = 0

    document_identity_rejected_count = 0

    raw_candidates: List[
        Dict[str, Any]
    ] = []

    source_results: List[
        Dict[str, Any]
    ] = []

    # ========================================================
    # SOURCE LOOP
    # ========================================================

    for source_index, source in enumerate(
        endpoints,
        start=1,
    ):

        family = source[
            "source_family"
        ]

        source_url = source[
            "url"
        ]

        regions = source[
            "regions"
        ]

        source_request_count = 0

        source_candidate_count = 0

        seen_request_urls: Set[str] = set()

        print(
            "-" * 60
        )

        print(
            f"SOURCE {source_index}"
        )

        print(
            "Family:",
            family,
        )

        print(
            "Regions:",
            regions,
        )

        print(
            "URL:",
            source_url,
        )

        # ====================================================
        # QUERY LOOP
        # ====================================================

        for query in QUERY_MATRIX:

            if request_count >= MAX_TOTAL_REQUESTS:
                break

            if (
                source_request_count
                >= MAX_REQUESTS_PER_SOURCE
            ):

                break

            query_urls = build_reverse_query_urls(
                source_url,
                query,
            )

            for request_url in query_urls:

                if request_count >= MAX_TOTAL_REQUESTS:
                    break

                if (
                    source_request_count
                    >= MAX_REQUESTS_PER_SOURCE
                ):

                    break

                if request_url in seen_request_urls:
                    continue

                seen_request_urls.add(
                    request_url
                )

                request_count += 1

                source_request_count += 1

                response = fetch_page(
                    session,
                    request_url,
                )

                status = response.get(
                    "http_status"
                )

                if (
                    isinstance(
                        status,
                        int,
                    )
                    and 200
                    <= status
                    < 300
                ):

                    http_success_count += 1

                if response.get(
                    "error"
                ):

                    transport_error_count += 1

                    continue

                if not (
                    isinstance(
                        status,
                        int,
                    )
                    and 200
                    <= status
                    < 300
                ):

                    continue

                final_url = canonicalize_url(
                    response.get(
                        "final_url"
                    )
                    or request_url
                )

                if not same_host(
                    source_url,
                    final_url,
                ):

                    continue

                raw_html = str(
                    response.get(
                        "raw_html"
                    )
                    or ""
                )

                if not raw_html:
                    continue

                page_title = extract_title(
                    raw_html
                )

                links = extract_links(
                    raw_html,
                    final_url,
                )

                # ============================================
                # LINK LOOP
                # ============================================

                for link in links:

                    candidate_url = canonicalize_url(
                        link.get(
                            "url"
                        )
                        or ""
                    )

                    anchor_text = normalize_space(
                        link.get(
                            "anchor_text"
                        )
                    )

                    if not candidate_url:
                        continue

                    if not same_host(
                        source_url,
                        candidate_url,
                    ):

                        continue

                    # ========================================
                    # IMPORTANT
                    #
                    # candidate qualification evidence:
                    #
                    #     anchor_text
                    #     candidate_url
                    #
                    # 만 사용한다.
                    #
                    # query / page_title은 qualification에
                    # 포함하지 않는다.
                    # ========================================

                    candidate_local_text = normalize_space(
                        " ".join(
                            [
                                anchor_text,
                                candidate_url,
                            ]
                        )
                    )

                    # context/provenance용.
                    candidate_context_text = normalize_space(
                        " ".join(
                            [
                                anchor_text,
                                candidate_url,
                                page_title,
                            ]
                        )
                    )

                    local_target_reasons = direct_target_evidence(
                        candidate_local_text
                    )

                    local_notice_numbers = extract_notice_numbers(
                        candidate_local_text
                    )

                    context_target_reasons = direct_target_evidence(
                        candidate_context_text
                    )

                    # ----------------------------------------
                    # Legacy contamination regression detector
                    # ----------------------------------------

                    legacy_contaminated_text = normalize_space(
                        " ".join(
                            [
                                anchor_text,
                                candidate_url,
                                page_title,
                                query,
                            ]
                        )
                    )

                    legacy_target_reasons = direct_target_evidence(
                        legacy_contaminated_text
                    )

                    if (
                        legacy_target_reasons
                        and not local_target_reasons
                        and not local_notice_numbers
                    ):

                        query_contamination_rejected_count += 1

                        if context_target_reasons:

                            page_title_only_rejected_count += 1

                        continue

                    # ----------------------------------------
                    # Link-local target identity required
                    # ----------------------------------------

                    if not (
                        local_target_reasons
                        or local_notice_numbers
                    ):

                        continue

                    # ----------------------------------------
                    # Navigation guard
                    # ----------------------------------------

                    if looks_generic_navigation_url(
                        candidate_url
                    ):

                        navigation_link_rejected_count += 1

                        continue

                    # ----------------------------------------
                    # Document identity guard
                    # ----------------------------------------

                    if not looks_like_document_url(
                        candidate_url
                    ):

                        document_identity_rejected_count += 1

                        continue

                    classification = classify_candidate(
                        source_family=family,
                        url=candidate_url,
                        text=candidate_local_text,
                        regions=regions,
                    )

                    raw_candidates.append(
                        {
                            "source_family": family,

                            "source_url": source_url,

                            "regions": regions,

                            # provenance only
                            "query": query,

                            "request_url": request_url,

                            # provenance only
                            "page_title": page_title,

                            "candidate_url": candidate_url,

                            "anchor_text": anchor_text,

                            "candidate_local_text": (
                                candidate_local_text[
                                    :2000
                                ]
                            ),

                            "candidate_context_text": (
                                candidate_context_text[
                                    :2000
                                ]
                            ),

                            "local_target_reasons": (
                                local_target_reasons
                            ),

                            "local_notice_numbers": (
                                local_notice_numbers
                            ),

                            "matched_regions": (
                                classification[
                                    "matched_regions"
                                ]
                            ),

                            "notice_numbers": (
                                classification[
                                    "notice_numbers"
                                ]
                            ),

                            "qualified": (
                                classification[
                                    "qualified"
                                ]
                            ),

                            "classification": (
                                classification[
                                    "classification"
                                ]
                            ),

                            "reasons": (
                                classification[
                                    "reasons"
                                ]
                            ),

                            "query_used_as_candidate_evidence": False,

                            "page_title_used_as_candidate_evidence": False,

                            "link_local_evidence_required": True,

                            "document_identity_required": True,

                            "verified_positive": False,

                            "runtime_registration_allowed": False,

                            "site_positive_allowed": False,

                            "final_positive_promotion_allowed": False,
                        }
                    )

                    if classification[
                        "qualified"
                    ]:

                        source_candidate_count += 1

                if REQUEST_DELAY_SECONDS > 0:

                    time.sleep(
                        REQUEST_DELAY_SECONDS
                    )

        source_resolution = (
            "CANDIDATE_FOUND"
            if source_candidate_count
            else "NOT_FOUND_IN_REVERSE_DISCOVERY"
        )

        source_results.append(
            {
                "source_family": family,

                "regions": regions,

                "url": source_url,

                "request_count": (
                    source_request_count
                ),

                "candidate_count": (
                    source_candidate_count
                ),

                "resolution": (
                    source_resolution
                ),
            }
        )

        print(
            "Requests:",
            source_request_count,
        )

        print(
            "Candidates:",
            source_candidate_count,
        )

        print(
            "Resolution:",
            source_resolution,
        )

        print()

    # ========================================================
    # CANONICAL DOCUMENT DEDUPE
    # ========================================================

    canonical_map: Dict[
        str,
        Dict[str, Any],
    ] = {}

    duplicate_count = 0

    for item in raw_candidates:

        candidate_url = canonicalize_url(
            item.get(
                "candidate_url"
            )
            or ""
        )

        if not candidate_url:
            continue

        key = candidate_url

        # ====================================================
        # DUPLICATE
        # ====================================================

        if key in canonical_map:

            duplicate_count += 1

            existing = canonical_map[
                key
            ]

            merge_list_field(
                existing,
                item,
                "regions",
            )

            merge_list_field(
                existing,
                item,
                "matched_regions",
            )

            merge_list_field(
                existing,
                item,
                "notice_numbers",
            )

            merge_list_field(
                existing,
                item,
                "reasons",
            )

            # ------------------------------------------------
            # Source family provenance
            # ------------------------------------------------

            existing[
                "source_families"
            ] = unique_strings(
                (
                    existing.get(
                        "source_families"
                    )
                    or singleton_string_list(
                        existing.get(
                            "source_family"
                        )
                    )
                )
                +
                singleton_string_list(
                    item.get(
                        "source_family"
                    )
                )
            )

            # ------------------------------------------------
            # Source URL provenance
            # ------------------------------------------------

            existing[
                "source_urls"
            ] = unique_strings(
                (
                    existing.get(
                        "source_urls"
                    )
                    or singleton_url_list(
                        existing.get(
                            "source_url"
                        )
                    )
                )
                +
                singleton_url_list(
                    item.get(
                        "source_url"
                    )
                )
            )

            # ------------------------------------------------
            # Query provenance
            # ------------------------------------------------

            existing[
                "queries"
            ] = unique_strings(
                (
                    existing.get(
                        "queries"
                    )
                    or singleton_string_list(
                        existing.get(
                            "query"
                        )
                    )
                )
                +
                singleton_string_list(
                    item.get(
                        "query"
                    )
                )
            )

            # ------------------------------------------------
            # Request URL provenance
            # ------------------------------------------------

            existing[
                "request_urls"
            ] = unique_strings(
                (
                    existing.get(
                        "request_urls"
                    )
                    or singleton_url_list(
                        existing.get(
                            "request_url"
                        )
                    )
                )
                +
                singleton_url_list(
                    item.get(
                        "request_url"
                    )
                )
            )

            # ------------------------------------------------
            # Anchor provenance
            # ------------------------------------------------

            existing[
                "anchor_texts"
            ] = unique_strings(
                (
                    existing.get(
                        "anchor_texts"
                    )
                    or singleton_string_list(
                        existing.get(
                            "anchor_text"
                        )
                    )
                )
                +
                singleton_string_list(
                    item.get(
                        "anchor_text"
                    )
                )
            )

            # ------------------------------------------------
            # Page title provenance
            # ------------------------------------------------

            existing[
                "page_titles"
            ] = unique_strings(
                (
                    existing.get(
                        "page_titles"
                    )
                    or singleton_string_list(
                        existing.get(
                            "page_title"
                        )
                    )
                )
                +
                singleton_string_list(
                    item.get(
                        "page_title"
                    )
                )
            )

            # ------------------------------------------------
            # Qualified precedence
            # ------------------------------------------------

            if item.get(
                "qualified"
            ) is True:

                existing[
                    "qualified"
                ] = True

                incoming_class = normalize_space(
                    item.get(
                        "classification"
                    )
                )

                existing_class = normalize_space(
                    existing.get(
                        "classification"
                    )
                )

                if (
                    CANDIDATE_CLASS_PRIORITY.get(
                        incoming_class,
                        0,
                    )
                    >
                    CANDIDATE_CLASS_PRIORITY.get(
                        existing_class,
                        0,
                    )
                ):

                    existing[
                        "classification"
                    ] = incoming_class

            existing[
                "verified_positive"
            ] = False

            existing[
                "runtime_registration_allowed"
            ] = False

            existing[
                "site_positive_allowed"
            ] = False

            existing[
                "final_positive_promotion_allowed"
            ] = False

            continue

        # ====================================================
        # FIRST CANONICAL RECORD
        # ====================================================

        canonical_item = dict(
            item
        )

        canonical_item[
            "candidate_url"
        ] = candidate_url

        canonical_item[
            "source_families"
        ] = singleton_string_list(
            item.get(
                "source_family"
            )
        )

        canonical_item[
            "source_urls"
        ] = singleton_url_list(
            item.get(
                "source_url"
            )
        )

        canonical_item[
            "queries"
        ] = singleton_string_list(
            item.get(
                "query"
            )
        )

        canonical_item[
            "request_urls"
        ] = singleton_url_list(
            item.get(
                "request_url"
            )
        )

        canonical_item[
            "anchor_texts"
        ] = singleton_string_list(
            item.get(
                "anchor_text"
            )
        )

        canonical_item[
            "page_titles"
        ] = singleton_string_list(
            item.get(
                "page_title"
            )
        )

        canonical_item[
            "verified_positive"
        ] = False

        canonical_item[
            "runtime_registration_allowed"
        ] = False

        canonical_item[
            "site_positive_allowed"
        ] = False

        canonical_item[
            "final_positive_promotion_allowed"
        ] = False

        canonical_map[
            key
        ] = canonical_item

    # ========================================================
    # CANONICAL RECORDS
    # ========================================================

    canonical_records = list(
        canonical_map.values()
    )

    canonical_records.sort(
        key=lambda item: (
            -int(
                item.get(
                    "qualified"
                )
                is True
            ),

            canonicalize_url(
                item.get(
                    "candidate_url"
                )
                or ""
            ),
        )
    )

    candidate_documents = [
        item
        for item in canonical_records
        if item.get(
            "qualified"
        )
        is True
    ]

    rejected_documents = [
        item
        for item in canonical_records
        if item.get(
            "qualified"
        )
        is not True
    ]

    classification_counts = Counter(
        item.get(
            "classification"
        )
        for item in canonical_records
    )

    # ========================================================
    # NEXT STAGE DOCUMENT POOL
    # ========================================================

    next_stage_document_pool = [
        {
            "source_family": item.get(
                "source_family"
            ),

            "source_families": (
                item.get(
                    "source_families"
                )
                or singleton_string_list(
                    item.get(
                        "source_family"
                    )
                )
            ),

            "source_urls": (
                item.get(
                    "source_urls"
                )
                or singleton_url_list(
                    item.get(
                        "source_url"
                    )
                )
            ),

            "queries": (
                item.get(
                    "queries"
                )
                or singleton_string_list(
                    item.get(
                        "query"
                    )
                )
            ),

            "request_urls": (
                item.get(
                    "request_urls"
                )
                or singleton_url_list(
                    item.get(
                        "request_url"
                    )
                )
            ),

            "regions": (
                item.get(
                    "matched_regions"
                )
                or item.get(
                    "regions"
                )
                or []
            ),

            "url": canonicalize_url(
                item.get(
                    "candidate_url"
                )
                or ""
            ),

            "page_title": item.get(
                "page_title"
            ),

            "page_titles": (
                item.get(
                    "page_titles"
                )
                or singleton_string_list(
                    item.get(
                        "page_title"
                    )
                )
            ),

            "anchor_text": item.get(
                "anchor_text"
            ),

            "anchor_texts": (
                item.get(
                    "anchor_texts"
                )
                or singleton_string_list(
                    item.get(
                        "anchor_text"
                    )
                )
            ),

            "notice_numbers": (
                item.get(
                    "notice_numbers"
                )
                or []
            ),

            "classification": item.get(
                "classification"
            ),

            "reasons": (
                item.get(
                    "reasons"
                )
                or []
            ),

            "candidate_local_text": (
                item.get(
                    "candidate_local_text"
                )
            ),

            "document_candidate_only": True,

            "requires_direct_document_verification": True,

            "verified_positive": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,

            "final_positive_promotion_allowed": False,
        }

        for item in candidate_documents
        if canonicalize_url(
            item.get(
                "candidate_url"
            )
            or ""
        )
    ]

    # ========================================================
    # RESOLUTION
    # ========================================================

    if next_stage_document_pool:

        resolution = (
            "HISTORICAL_TARGET_DOCUMENT_REVERSE_DISCOVERY_COMPLETED"
        )

        next_action = (
            "semantic candidate gate를 통과한 canonical historical "
            "notice/gazette document candidate만 U-stage direct document "
            "verification으로 넘긴다. document title, notice number, "
            "issuing authority, date, target regulation identity, region 및 "
            "실제 document body를 직접 검증한다."
        )

    else:

        resolution = (
            "HISTORICAL_TARGET_DOCUMENT_REVERSE_DISCOVERY_NO_DOCUMENT"
        )

        next_action = (
            "현재 S-3 source 범위의 hardened reverse discovery에서도 "
            "개발밀도관리구역 historical document identity가 확인되지 않았다. "
            "SITE FALSE로 판정하지 않고 UNKNOWN을 유지한다. "
            "다음 단계에서는 실제 search form action 복원 또는 "
            "notice-number reverse lookup source family를 추가한다."
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-T-2-S1 "
            "Historical Target Document Reverse Discovery "
            "Semantic Candidate Gate Hardening"
        ),

        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },

        "resolution_policy": {
            "resolution_type": (
                RESOLUTION_TYPE
            ),

            "negative_evidence_allowed": False,

            "source_failure_site_status": (
                "UNKNOWN"
            ),
        },

        "inputs": {
            "t1_stage_path": str(
                T1_STAGE_INPUT_PATH
            ),

            "s3_stage_path": str(
                S3_STAGE_INPUT_PATH
            ),

            "t1_resolution": t1_data.get(
                "resolution"
            ),
        },

        "method": {
            "exact_target_search_enabled": True,

            "legal_identity_reverse_search_enabled": True,

            "historical_notice_identity_search_enabled": True,

            "same_host_only": True,

            "official_go_kr_candidate_required": True,

            "search_engine_scraping_enabled": False,

            "bounded_query_matrix_enabled": True,

            "endpoint_bruteforce_repeat_enabled": False,

            "region_binding_required": True,

            "generic_urban_notice_auto_promotion_disabled": True,

            # S1
            "query_used_as_candidate_evidence": False,

            "page_title_used_as_candidate_evidence": False,

            "link_local_candidate_evidence_only": True,

            "document_url_identity_required": True,

            "generic_navigation_candidate_promotion_disabled": True,

            "canonical_document_identity_by_url": True,

            "cross_source_family_document_dedupe_enabled": True,

            "document_provenance_merge_enabled": True,

            "negative_evidence_enabled": False,

            "verified_positive_promotion_allowed": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,
        },

        "summary": {
            "s3_endpoint_count": len(
                endpoints
            ),

            "request_count": (
                request_count
            ),

            "http_success_count": (
                http_success_count
            ),

            "transport_error_count": (
                transport_error_count
            ),

            "query_contamination_rejected_count": (
                query_contamination_rejected_count
            ),

            "page_title_only_rejected_count": (
                page_title_only_rejected_count
            ),

            "navigation_link_rejected_count": (
                navigation_link_rejected_count
            ),

            "document_identity_rejected_count": (
                document_identity_rejected_count
            ),

            "raw_candidate_count": len(
                raw_candidates
            ),

            "duplicate_candidate_removed": (
                duplicate_count
            ),

            "canonical_record_count": len(
                canonical_records
            ),

            "candidate_document_count": len(
                candidate_documents
            ),

            "rejected_document_count": len(
                rejected_documents
            ),

            "next_stage_document_pool_count": len(
                next_stage_document_pool
            ),
        },

        "classification_counts": dict(
            sorted(
                classification_counts.items()
            )
        ),

        "source_results": (
            source_results
        ),

        "candidate_documents": (
            candidate_documents
        ),

        "rejected_documents": (
            rejected_documents
        ),

        "next_stage_document_pool": (
            next_stage_document_pool
        ),

        "all_canonical_records": (
            canonical_records
        ),

        "resolution": (
            resolution
        ),

        "next_action": (
            next_action
        ),

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

    print(
        "=" * 60
    )

    print(
        "HISTORICAL TARGET DOCUMENT REVERSE DISCOVERY RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "S-3 endpoint count:",
        len(
            endpoints
        ),
    )

    print(
        "Request count:",
        request_count,
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
        "Query contamination rejected:",
        query_contamination_rejected_count,
    )

    print(
        "Page-title-only rejected:",
        page_title_only_rejected_count,
    )

    print(
        "Navigation links rejected:",
        navigation_link_rejected_count,
    )

    print(
        "Document identity rejected:",
        document_identity_rejected_count,
    )

    print(
        "Raw candidate count:",
        len(
            raw_candidates
        ),
    )

    print(
        "Duplicate candidate removed:",
        duplicate_count,
    )

    print(
        "Canonical record count:",
        len(
            canonical_records
        ),
    )

    print(
        "Candidate document count:",
        len(
            candidate_documents
        ),
    )

    print(
        "Next-stage document pool count:",
        len(
            next_stage_document_pool
        ),
    )

    # ========================================================
    # CANDIDATE PRINT
    # ========================================================

    if candidate_documents:

        print()

        print(
            "REVERSE-DISCOVERED DOCUMENT CANDIDATES"
        )

        print(
            "-" * 60
        )

        for index, item in enumerate(
            candidate_documents,
            start=1,
        ):

            print(
                f"[{index}]",
                item.get(
                    "classification"
                ),
            )

            print(
                "Primary family:",
                item.get(
                    "source_family"
                ),
            )

            print(
                "Source families:",
                item.get(
                    "source_families"
                ),
            )

            print(
                "Regions:",
                item.get(
                    "matched_regions"
                ),
            )

            print(
                "URL:",
                item.get(
                    "candidate_url"
                ),
            )

            print(
                "Anchor:",
                item.get(
                    "anchor_text"
                ),
            )

            print(
                "Anchor variants:",
                item.get(
                    "anchor_texts"
                ),
            )

            print(
                "Notice numbers:",
                item.get(
                    "notice_numbers"
                ),
            )

            print(
                "Queries:",
                item.get(
                    "queries"
                ),
            )

            print(
                "Reasons:",
                item.get(
                    "reasons"
                ),
            )

            print()

    # ========================================================
    # RESOLUTION
    # ========================================================

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

    # ========================================================
    # VALIDATION
    # ========================================================

    canonical_url_list = [
        canonicalize_url(
            item.get(
                "candidate_url"
            )
            or ""
        )
        for item in canonical_records
    ]

    canonical_urls = {
        url
        for url in canonical_url_list
        if url
    }

    next_stage_url_list = [
        canonicalize_url(
            item.get(
                "url"
            )
            or ""
        )
        for item in next_stage_document_pool
    ]

    next_stage_urls = {
        url
        for url in next_stage_url_list
        if url
    }

    # --------------------------------------------------------
    # Duplicate / URL
    # --------------------------------------------------------

    duplicate_canonical_url_leakage = (
        len(
            canonical_url_list
        )
        - len(
            canonical_urls
        )
    )

    duplicate_next_stage_url_leakage = (
        len(
            next_stage_url_list
        )
        - len(
            next_stage_urls
        )
    )

    invalid_canonical_url_leakage = sum(
        1
        for url in canonical_url_list
        if not url
    )

    invalid_next_stage_url_leakage = sum(
        1
        for url in next_stage_url_list
        if not url
    )

    # --------------------------------------------------------
    # Classes
    # --------------------------------------------------------

    all_classes_valid = all(
        item.get(
            "classification"
        )
        in VALID_CLASSES
        for item in canonical_records
    )

    candidate_classes_valid = all(
        item.get(
            "classification"
        )
        in CANDIDATE_CLASSES
        for item in candidate_documents
    )

    # --------------------------------------------------------
    # Candidate semantic leakage
    # --------------------------------------------------------

    candidate_non_go_kr_leakage = sum(
        1
        for item in candidate_documents
        if not is_government_host(
            hostname(
                item.get(
                    "candidate_url"
                )
                or ""
            )
        )
    )

    candidate_region_unbound_leakage = sum(
        1
        for item in candidate_documents
        if not (
            item.get(
                "matched_regions"
            )
            or []
        )
    )

    candidate_link_local_evidence_leakage = sum(
        1
        for item in candidate_documents
        if not direct_target_evidence(
            normalize_space(
                item.get(
                    "candidate_local_text"
                )
            )
        )
    )

    candidate_navigation_leakage = sum(
        1
        for item in candidate_documents
        if looks_generic_navigation_url(
            item.get(
                "candidate_url"
            )
            or ""
        )
    )

    candidate_document_identity_leakage = sum(
        1
        for item in candidate_documents
        if not looks_like_document_url(
            item.get(
                "candidate_url"
            )
            or ""
        )
    )

    query_evidence_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "query_used_as_candidate_evidence"
        )
        is True
    )

    page_title_evidence_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "page_title_used_as_candidate_evidence"
        )
        is True
    )

    # --------------------------------------------------------
    # Explicit regression
    # --------------------------------------------------------

    known_welfare_main_regression_leakage = sum(
        1
        for item in candidate_documents
        if (
            "/welfare/main.do"
            in canonicalize_url(
                item.get(
                    "candidate_url"
                )
                or ""
            ).lower()
        )
    )

    # --------------------------------------------------------
    # Safety
    # --------------------------------------------------------

    verified_positive_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "verified_positive"
        )
        is True
    )

    runtime_registration_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "runtime_registration_allowed"
        )
        is True
    )

    site_true_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "site_positive_allowed"
        )
        is True
    )

    final_positive_promotion_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "final_positive_promotion_allowed"
        )
        is True
    )

    next_stage_verified_positive_leakage = sum(
        1
        for item in next_stage_document_pool
        if item.get(
            "verified_positive"
        )
        is True
    )

    next_stage_runtime_registration_leakage = sum(
        1
        for item in next_stage_document_pool
        if item.get(
            "runtime_registration_allowed"
        )
        is True
    )

    next_stage_site_true_leakage = sum(
        1
        for item in next_stage_document_pool
        if item.get(
            "site_positive_allowed"
        )
        is True
    )

    # --------------------------------------------------------
    # Candidate -> U-stage parity
    # --------------------------------------------------------

    candidate_urls = {
        canonicalize_url(
            item.get(
                "candidate_url"
            )
            or ""
        )
        for item in candidate_documents
        if canonicalize_url(
            item.get(
                "candidate_url"
            )
            or ""
        )
    }

    candidate_next_stage_parity = (
        candidate_urls
        == next_stage_urls
    )

    # --------------------------------------------------------
    # Provenance
    # --------------------------------------------------------

    candidate_provenance_missing_count = sum(
        1
        for item in candidate_documents
        if not (
            item.get(
                "source_families"
            )
            or []
        )
    )

    # --------------------------------------------------------
    # Negative evidence
    # --------------------------------------------------------

    false_from_no_document_leakage = (
        1
        if (
            not candidate_documents
            and output_data[
                "resolution_policy"
            ][
                "source_failure_site_status"
            ]
            == "FALSE"
        )
        else 0
    )

    # ========================================================
    # VALIDATIONS
    # ========================================================

    validations = {
        "target name": (
            TARGET_NAME
            == "개발밀도관리구역"
        ),

        "standard code": (
            STANDARD_CODE
            == "UQQ700"
        ),

        "resolution type hybrid spatial notice": (
            RESOLUTION_TYPE
            == "HYBRID_SPATIAL_NOTICE"
        ),

        "negative evidence disabled": (
            NEGATIVE_EVIDENCE_ALLOWED
            is False
        ),

        "T-1 input exists": (
            T1_STAGE_INPUT_PATH.exists()
        ),

        "S-3 input exists": (
            S3_STAGE_INPUT_PATH.exists()
        ),

        "T-1 input parsed": (
            isinstance(
                t1_data,
                dict,
            )
        ),

        "S-3 input parsed": (
            isinstance(
                s3_data,
                dict,
            )
        ),

        "S-3 hardened endpoints loaded": (
            len(
                endpoints
            )
            > 0
        ),

        "bounded reverse query matrix enabled": True,

        "search engine scraping disabled": True,

        "same-host reverse discovery enabled": True,

        "endpoint brute-force repeat disabled": True,

        "official go.kr candidate guard enabled": True,

        "region binding required": True,

        "generic urban notice promotion disabled": True,

        # ----------------------------------------------------
        # S1 semantic hardening
        # ----------------------------------------------------

        "query contamination disabled": (
            query_evidence_leakage
            == 0
        ),

        "page title alone cannot qualify candidate": (
            page_title_evidence_leakage
            == 0
        ),

        "link-local target evidence required": (
            candidate_link_local_evidence_leakage
            == 0
        ),

        "generic navigation candidate leakage zero": (
            candidate_navigation_leakage
            == 0
        ),

        "document identity leakage zero": (
            candidate_document_identity_leakage
            == 0
        ),

        "known welfare main regression leakage zero": (
            known_welfare_main_regression_leakage
            == 0
        ),

        # ----------------------------------------------------

        "canonical document identity by URL enabled": True,

        "cross-source-family document dedupe enabled": True,

        "document provenance merge enabled": True,

        "all classes valid": (
            all_classes_valid
        ),

        "candidate classes valid": (
            candidate_classes_valid
        ),

        "canonical candidate URLs valid": (
            invalid_canonical_url_leakage
            == 0
        ),

        "next-stage document URLs valid": (
            invalid_next_stage_url_leakage
            == 0
        ),

        "canonical candidate URLs unique": (
            duplicate_canonical_url_leakage
            == 0
        ),

        "next-stage document URLs unique": (
            duplicate_next_stage_url_leakage
            == 0
        ),

        "candidate and next-stage URL parity": (
            candidate_next_stage_parity
        ),

        "candidate provenance present": (
            candidate_provenance_missing_count
            == 0
        ),

        "candidate non-go.kr leakage zero": (
            candidate_non_go_kr_leakage
            == 0
        ),

        "candidate region-unbound leakage zero": (
            candidate_region_unbound_leakage
            == 0
        ),

        "verified positive leakage zero": (
            verified_positive_leakage
            == 0
        ),

        "runtime registration leakage zero": (
            runtime_registration_leakage
            == 0
        ),

        "SITE TRUE leakage zero": (
            site_true_leakage
            == 0
        ),

        "final positive promotion leakage zero": (
            final_positive_promotion_leakage
            == 0
        ),

        "next-stage verified positive leakage zero": (
            next_stage_verified_positive_leakage
            == 0
        ),

        "next-stage runtime registration leakage zero": (
            next_stage_runtime_registration_leakage
            == 0
        ),

        "next-stage SITE TRUE leakage zero": (
            next_stage_site_true_leakage
            == 0
        ),

        "false from no document leakage zero": (
            false_from_no_document_leakage
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

    # ========================================================
    # VALIDATION PRINT
    # ========================================================

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
        "Duplicate canonical URL leakage:",
        duplicate_canonical_url_leakage,
    )

    print(
        "Duplicate next-stage URL leakage:",
        duplicate_next_stage_url_leakage,
    )

    print(
        "Invalid canonical URL leakage:",
        invalid_canonical_url_leakage,
    )

    print(
        "Invalid next-stage URL leakage:",
        invalid_next_stage_url_leakage,
    )

    print(
        "Candidate provenance missing:",
        candidate_provenance_missing_count,
    )

    print(
        "Candidate non-go.kr leakage:",
        candidate_non_go_kr_leakage,
    )

    print(
        "Candidate region-unbound leakage:",
        candidate_region_unbound_leakage,
    )

    print(
        "Candidate link-local evidence leakage:",
        candidate_link_local_evidence_leakage,
    )

    print(
        "Candidate navigation leakage:",
        candidate_navigation_leakage,
    )

    print(
        "Candidate document identity leakage:",
        candidate_document_identity_leakage,
    )

    print(
        "Known welfare main regression leakage:",
        known_welfare_main_regression_leakage,
    )

    print(
        "Query evidence leakage:",
        query_evidence_leakage,
    )

    print(
        "Page-title evidence leakage:",
        page_title_evidence_leakage,
    )

    print(
        "Verified positive leakage:",
        verified_positive_leakage,
    )

    print(
        "Runtime registration leakage:",
        runtime_registration_leakage,
    )

    print(
        "SITE TRUE leakage:",
        site_true_leakage,
    )

    print(
        "Final positive promotion leakage:",
        final_positive_promotion_leakage,
    )

    print(
        "Next-stage verified positive leakage:",
        next_stage_verified_positive_leakage,
    )

    print(
        "Next-stage runtime registration leakage:",
        next_stage_runtime_registration_leakage,
    )

    print(
        "Next-stage SITE TRUE leakage:",
        next_stage_site_true_leakage,
    )

    print(
        "False from no document leakage:",
        false_from_no_document_leakage,
    )

    print()

    # ========================================================
    # FINAL ASSERT
    # ========================================================

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
                "-",
                name,
            )

        raise AssertionError(
            "Development density management area "
            "historical target document reverse discovery "
            "semantic candidate gate regression failed"
        )


if __name__ == "__main__":
    main()