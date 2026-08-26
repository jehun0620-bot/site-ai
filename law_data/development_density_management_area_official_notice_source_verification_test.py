# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-J
Development Density Management Area
Official Notice Source Verification

목표
======================================================================
I-stage에서 발견된 official notice recovery seed를 실제 원문 단위로
HTTP 조회하고, 개발밀도관리구역 지정·변경·해제 고시인지 검증한다.

입력:
    law_data/output/
    development_density_management_area_official_notice_recovery_discovery.json

출력:
    law_data/output/
    development_density_management_area_official_notice_source_verification.json

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 원칙
======================================================================
1. I-stage 검색/list page의 page-level evidence를 절대 상속하지 않는다.
2. 실제 candidate URL을 다시 HTTP 조회한다.
3. HTTP response body / 실제 attachment text만 verification evidence로 사용한다.
4. searchKeyword / q / query 등 discovery-only query parameter를 제거하고
   document identity를 다시 canonicalize한다.
5. PDF/HWP/HWPX 등 attachment는 실제 다운로드 후 parser로 읽는다.
6. Gazette issue container 자체는 verified positive로 승격하지 않는다.
7. 사무전결·업무분장·단위사무표 false positive를 차단한다.
8. 법령/조례의 단순 정의·인용도 차단한다.
9. VERIFIED_OFFICIAL_NOTICE는 다음을 모두 만족해야 한다.

    - target exact phrase
    - designation/change/release/decision action context
    - notice number
    - official context
    - geographic context
    - administrative-duty reference 아님
    - legal-reference-only 아님
    - gazette container 아님

10. scope evidence는 추출하되 이번 단계의 verified positive 필수조건은 아니다.
11. verified notice가 발견되어도 runtime registration / SITE TRUE는 계속 차단한다.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import zipfile

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import (
    parse_qsl,
    urlencode,
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

INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "official_notice_recovery_discovery.json"
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
        "official_notice_source_verification.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# HTTP
# ============================================================

TIMEOUT = 30

MAX_RESPONSE_BYTES = (
    30
    * 1024
    * 1024
)

REQUEST_DELAY_SECONDS = 0.03

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# I-STAGE INPUT CLASSES
# ============================================================

ALLOWED_INPUT_CLASSES = {
    "TARGET_DIRECT_DETAIL_SEED",
    "URBAN_NOTICE_DETAIL_SEED",
    "GAZETTE_ISSUE_SEED",
    "ATTACHMENT_DOCUMENT_SEED",
    "EXTENSIONLESS_DOWNLOAD_SEED",
}


# ============================================================
# J-STAGE RESOLUTIONS
# ============================================================

RESOLUTION_VERIFIED = (
    "VERIFIED_OFFICIAL_NOTICE"
)

RESOLUTION_TARGET_NO_ACTION = (
    "TARGET_PRESENT_NO_ACTION"
)

RESOLUTION_ACTION_NO_NOTICE = (
    "ACTION_PRESENT_NO_NOTICE_NUMBER"
)

RESOLUTION_TARGET_NO_OFFICIAL = (
    "TARGET_PRESENT_NO_OFFICIAL_CONTEXT"
)

RESOLUTION_TARGET_NO_GEO = (
    "TARGET_PRESENT_NO_GEOGRAPHIC_CONTEXT"
)

RESOLUTION_ADMIN_DUTY = (
    "ADMINISTRATIVE_DUTY_REFERENCE_ONLY"
)

RESOLUTION_LEGAL_REFERENCE = (
    "LEGAL_REFERENCE_ONLY"
)

RESOLUTION_GAZETTE_CONTAINER = (
    "GAZETTE_CONTAINER_REQUIRES_CHILD_RESOLUTION"
)

RESOLUTION_UNRELATED = (
    "UNRELATED_DOCUMENT"
)

RESOLUTION_DOWNLOAD_FAILED = (
    "DOWNLOAD_FAILED"
)

RESOLUTION_PARSE_FAILED = (
    "DOWNLOAD_OR_PARSE_FAILED"
)

VALID_RESOLUTIONS = {
    RESOLUTION_VERIFIED,
    RESOLUTION_TARGET_NO_ACTION,
    RESOLUTION_ACTION_NO_NOTICE,
    RESOLUTION_TARGET_NO_OFFICIAL,
    RESOLUTION_TARGET_NO_GEO,
    RESOLUTION_ADMIN_DUTY,
    RESOLUTION_LEGAL_REFERENCE,
    RESOLUTION_GAZETTE_CONTAINER,
    RESOLUTION_UNRELATED,
    RESOLUTION_DOWNLOAD_FAILED,
    RESOLUTION_PARSE_FAILED,
}


# ============================================================
# SEARCH / DISCOVERY QUERY KEYS
# ============================================================

DISCOVERY_ONLY_QUERY_KEYS = {
    "searchkeyword",
    "searchwrd",
    "searchword",
    "searchtext",
    "searchterm",
    "keyword",
    "query",
    "q",
    "srchtext",
    "srchword",
    "srchkeyword",
    "search",
    "searchcondition",
    "searchtype",
    "searchcnd",
    "page",
    "pageno",
    "pageindex",
    "currentpage",
}

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "csrftoken",
    "sessionid",
    "jsessionid",
    "_",
    "timestamp",
    "rand",
    "random",
    "cachebuster",
    "cache_buster",
    "cb",
    "ts",
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

JSESSIONID_PATTERN = re.compile(
    r";jsessionid=[^/?]+",
    re.IGNORECASE,
)


# ============================================================
# ACTION
# ============================================================

ACTION_PATTERNS = {
    "DESIGNATION": [
        r"개발밀도관리구역.{0,150}?지정",
        r"개발밀도관리구역을.{0,150}?지정",
        r"개발밀도관리구역으로.{0,150}?지정",
        r"지정.{0,150}?개발밀도관리구역",
    ],

    "CHANGE": [
        r"개발밀도관리구역.{0,150}?변경",
        r"개발밀도관리구역.{0,150}?변경결정",
        r"개발밀도관리구역.{0,150}?결정\s*\(\s*변경\s*\)",
        r"변경.{0,150}?개발밀도관리구역",
    ],

    "RELEASE": [
        r"개발밀도관리구역.{0,150}?해제",
        r"개발밀도관리구역.{0,150}?해지",
        r"해제.{0,150}?개발밀도관리구역",
    ],

    "DECISION": [
        r"개발밀도관리구역.{0,150}?결정",
        r"결정.{0,150}?개발밀도관리구역",
    ],
}


# ============================================================
# OFFICIAL CONTEXT
# ============================================================

OFFICIAL_CONTEXT_PATTERNS = [
    r"고\s*시",
    r"고시문",
    r"고시번호",
    r"고시일",
    r"도시관리계획",
    r"도시계획",
    r"지형도면",
    r"국토의\s*계획\s*및\s*이용에\s*관한\s*법률",
    r"국토계획법",
    r"특별시장",
    r"광역시장",
    r"특별자치시장",
    r"도지사",
    r"특별자치도지사",
    r"시장",
    r"군수",
    r"구청장",
]


# ============================================================
# NOTICE NUMBER
# ============================================================

NOTICE_NUMBER_PATTERNS = [
    re.compile(
        r"(?P<notice>"
        r"(?:서울특별시|부산광역시|대구광역시|인천광역시|"
        r"광주광역시|대전광역시|울산광역시|세종특별자치시|"
        r"경기도|강원특별자치도|강원도|충청북도|충청남도|"
        r"전북특별자치도|전라북도|전라남도|경상북도|경상남도|"
        r"제주특별자치도|"
        r"[가-힣]{2,12}시|[가-힣]{2,12}군|[가-힣]{2,12}구)"
        r"\s*(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
    ),

    re.compile(
        r"(?P<notice>"
        r"(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
    ),

    # OCR / PDF spacing 보완
    re.compile(
        r"(?P<notice>"
        r"(?:고\s*시|공\s*고)\s*제?\s*"
        r"\d{4}\s*[-–]\s*\d+\s*호)"
    ),
]


# ============================================================
# DATE
# ============================================================

DATE_PATTERNS = [
    re.compile(
        r"(?P<year>19\d{2}|20\d{2})"
        r"\s*[.\-/년]\s*"
        r"(?P<month>0?[1-9]|1[0-2])"
        r"\s*[.\-/월]\s*"
        r"(?P<day>0?[1-9]|[12]\d|3[01])"
        r"\s*일?"
    ),
]


# ============================================================
# REGION
# ============================================================

REGION_PATTERNS = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "강원도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라북도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]


# ============================================================
# LEGAL REFERENCE
# ============================================================

LEGAL_REFERENCE_PATTERNS = [
    r"법\s*제\s*\d+\s*조",
    r"법률\s*제\s*\d+\s*호",
    r"시행령\s*제\s*\d+\s*조",
    r"조례\s*제\s*\d+\s*조",
    r"용어의\s*뜻",
    r"정의는\s*다음과",
    r"다음\s*각\s*호",
]


# ============================================================
# ADMINISTRATIVE DUTY FALSE POSITIVE
# ============================================================

ADMIN_DUTY_STRUCTURE_TERMS = [
    "단위사무명",
    "단 위 사 무 명",
    "전결권자",
    "전 결 권 자",
    "사무전결",
    "위임전결",
    "업무분장",
    "전결규정",
]

ADMIN_DUTY_TABLE_TERMS = [
    "부 서 명",
    "담 당 자",
    "팀 장",
    "과 장",
    "국 장",
    "부 시 장",
    "관 · 과 · 단 장",
    "관·과·단장",
]


# ============================================================
# SCOPE
# ============================================================

SCOPE_PATTERNS = [
    r"[가-힣]{1,15}(?:동|읍|면|리)\s+\d+(?:-\d+)?\s*번지",
    r"[가-힣]{1,15}(?:동|읍|면|리)\s+일원",
    r"\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:㎡|m²|m2)",
    r"면적\s*[:：]?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?",
    r"위치\s*[:：]\s*[^,\n]{1,120}",
    r"구역\s*면적",
    r"지정\s*면적",
    r"대상\s*지역",
]


# ============================================================
# GAZETTE CONTAINER
# ============================================================

GAZETTE_TERMS = [
    "시보",
    "군보",
    "구보",
    "공보",
    "호외",
]

GAZETTE_CONTAINER_HINTS = [
    "gazette",
    "word.asp",
    "bbs010308",
    "공보",
    "시보",
    "군보",
    "구보",
]


# ============================================================
# FILE TYPES
# ============================================================

FILE_EXTENSIONS = {
    ".pdf",
    ".hwp",
    ".hwpx",
    ".txt",
    ".doc",
    ".docx",
}

HTML_CONTENT_TYPES = [
    "text/html",
    "application/xhtml+xml",
]

PDF_CONTENT_TYPES = [
    "application/pdf",
]

HWP_CONTENT_TYPES = [
    "application/x-hwp",
    "application/haansofthwp",
]

HWPX_CONTENT_TYPES = [
    "application/hwp+zip",
    "application/vnd.hancom.hwpx",
    "application/zip",
]


# ============================================================
# HTML
# ============================================================

SCRIPT_STYLE_PATTERN = re.compile(
    r"<(?:script|style|noscript)\b.*?</(?:script|style|noscript)>",
    re.IGNORECASE
    | re.DOTALL,
)

HTML_COMMENT_PATTERN = re.compile(
    r"<!--.*?-->",
    re.DOTALL,
)

TAG_PATTERN = re.compile(
    r"<[^>]+>",
    re.DOTALL,
)


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


def contains_any(
    text: str,
    terms: Iterable[str],
) -> bool:

    lowered = normalize_space(
        text
    ).lower()

    return any(
        term.lower()
        in lowered
        for term in terms
    )


def strip_html(
    raw_html: str,
) -> str:

    text = HTML_COMMENT_PATTERN.sub(
        " ",
        raw_html,
    )

    text = SCRIPT_STYLE_PATTERN.sub(
        " ",
        text,
    )

    text = TAG_PATTERN.sub(
        " ",
        text,
    )

    text = html.unescape(
        text
    )

    return normalize_space(
        text
    )


def stable_hash(
    value: str,
) -> str:

    return hashlib.sha256(
        value.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()


# ============================================================
# CANONICAL URL
# ============================================================

def normalize_query_key(
    key: str,
) -> str:

    value = html.unescape(
        str(
            key
            or ""
        )
    ).strip()

    while value.lower().startswith(
        "amp;"
    ):
        value = value[
            4:
        ].strip()

    return value


def is_volatile_query_key(
    key: str,
) -> bool:

    lowered = normalize_query_key(
        key
    ).lower()

    if lowered in VOLATILE_QUERY_KEYS:
        return True

    if lowered in TRACKING_QUERY_KEYS:
        return True

    if "csrf" in lowered:
        return True

    if "session" in lowered:
        return True

    if re.search(
        r"(?:^|[_\-])token$",
        lowered,
    ):
        return True

    return False


def canonicalize_url(
    url: str,
    *,
    remove_discovery_query: bool = False,
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

    except ValueError:
        port = None

    if (
        port is not None
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

    path = JSESSIONID_PATTERN.sub(
        "",
        path,
    )

    path = re.sub(
        r"/{2,}",
        "/",
        path,
    )

    query_items: List[
        Tuple[str, str]
    ] = []

    seen_pairs: Set[
        Tuple[str, str]
    ] = set()

    for raw_key, query_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        key = normalize_query_key(
            raw_key
        )

        if not key:
            continue

        lowered = key.lower()

        if is_volatile_query_key(
            key
        ):
            continue

        if (
            remove_discovery_query
            and lowered
            in DISCOVERY_ONLY_QUERY_KEYS
        ):
            continue

        pair = (
            key,
            query_value,
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


# ============================================================
# INPUT
# ============================================================

def load_input_seeds(
    input_data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    raw = input_data.get(
        "next_stage_verification_pool"
    )

    if not isinstance(
        raw,
        list,
    ):
        raw = []

    result: List[
        Dict[str, Any]
    ] = []

    for item in raw:

        if not isinstance(
            item,
            dict,
        ):
            continue

        classification = normalize_space(
            item.get(
                "classification"
            )
        )

        if classification not in ALLOWED_INPUT_CLASSES:
            continue

        raw_url = normalize_space(
            item.get(
                "url"
            )
        )

        if not raw_url:
            continue

        canonical_url = canonicalize_url(
            raw_url,
            remove_discovery_query=True,
        )

        if not canonical_url:
            continue

        normalized = dict(
            item
        )

        normalized[
            "raw_seed_url"
        ] = raw_url

        normalized[
            "verification_url"
        ] = canonical_url

        result.append(
            normalized
        )

    return result


# ============================================================
# DOCUMENT IDENTITY / DEDUPE
# ============================================================

def seed_identity(
    seed: Dict[str, Any],
) -> str:

    region = normalize_space(
        seed.get(
            "region"
        )
    )

    url = normalize_space(
        seed.get(
            "verification_url"
        )
    )

    return (
        f"{region}::{url}"
    )


INPUT_CLASS_PRIORITY = {
    "TARGET_DIRECT_DETAIL_SEED": 100,
    "ATTACHMENT_DOCUMENT_SEED": 90,
    "EXTENSIONLESS_DOWNLOAD_SEED": 85,
    "URBAN_NOTICE_DETAIL_SEED": 80,
    "GAZETTE_ISSUE_SEED": 70,
}


def dedupe_input_seeds(
    seeds: List[
        Dict[str, Any]
    ],
) -> Tuple[
    List[Dict[str, Any]],
    int,
]:

    grouped: Dict[
        str,
        List[
            Dict[str, Any]
        ],
    ] = defaultdict(
        list
    )

    for seed in seeds:

        grouped[
            seed_identity(
                seed
            )
        ].append(
            seed
        )

    result: List[
        Dict[str, Any]
    ] = []

    for identity, group in grouped.items():

        ordered = sorted(
            group,
            key=lambda item: (
                -INPUT_CLASS_PRIORITY.get(
                    normalize_space(
                        item.get(
                            "classification"
                        )
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
            "verification_identity"
        ] = identity

        representative[
            "merged_seed_count"
        ] = len(
            group
        )

        representative[
            "merged_input_classes"
        ] = unique_strings(
            item.get(
                "classification"
            )
            for item in group
        )

        representative[
            "merged_raw_urls"
        ] = unique_strings(
            item.get(
                "raw_seed_url"
            )
            or item.get(
                "url"
            )
            for item in group
        )

        representative[
            "merged_labels"
        ] = unique_strings(
            item.get(
                "label"
            )
            for item in group
        )

        result.append(
            representative
        )

    result.sort(
        key=lambda item: (
            -INPUT_CLASS_PRIORITY.get(
                normalize_space(
                    item.get(
                        "classification"
                    )
                ),
                0,
            ),
            -int(
                item.get(
                    "score"
                )
                or 0
            ),
            normalize_space(
                item.get(
                    "region"
                )
            ),
            normalize_space(
                item.get(
                    "verification_url"
                )
            ),
        )
    )

    duplicate_removed = (
        len(
            seeds
        )
        - len(
            result
        )
    )

    return (
        result,
        duplicate_removed,
    )


# ============================================================
# HTTP DOWNLOAD
# ============================================================

def request_document(
    session: requests.Session,
    url: str,
) -> Dict[str, Any]:

    result: Dict[str, Any] = {
        "requested_url": url,
        "http_status": None,
        "final_url": "",
        "content_type": "",
        "content_disposition": "",
        "response_bytes": 0,
        "data": b"",
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
                ),
                remove_discovery_query=True,
            )

            result[
                "content_type"
            ] = normalize_space(
                response.headers.get(
                    "Content-Type"
                )
            )

            result[
                "content_disposition"
            ] = normalize_space(
                response.headers.get(
                    "Content-Disposition"
                )
            )

            response.raise_for_status()

            chunks: List[bytes] = []

            total = 0

            for chunk in response.iter_content(
                chunk_size=256 * 1024,
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

            data = b"".join(
                chunks
            )

            result[
                "response_bytes"
            ] = len(
                data
            )

            result[
                "data"
            ] = data

    except Exception as exc:

        result[
            "error"
        ] = repr(
            exc
        )

    return result


# ============================================================
# TYPE DETECTION
# ============================================================

def filename_from_headers(
    content_disposition: str,
) -> str:

    if not content_disposition:
        return ""

    patterns = [
        r"""filename\*=UTF-8''([^;]+)""",
        r"""filename\s*=\s*"([^"]+)""",
        r"""filename\s*=\s*([^;]+)""",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            content_disposition,
            flags=re.IGNORECASE,
        )

        if match:

            return normalize_space(
                match.group(1)
            )

    return ""


def detect_document_type(
    *,
    url: str,
    content_type: str,
    content_disposition: str,
    data: bytes,
) -> str:

    path = (
        urlparse(
            url
        ).path
        or ""
    ).lower()

    filename = filename_from_headers(
        content_disposition
    ).lower()

    candidates = (
        path,
        filename,
    )

    for value in candidates:

        if value.endswith(
            ".pdf"
        ):
            return "PDF"

        if value.endswith(
            ".hwpx"
        ):
            return "HWPX"

        if value.endswith(
            ".hwp"
        ):
            return "HWP"

        if value.endswith(
            ".txt"
        ):
            return "TEXT"

        if value.endswith(
            ".docx"
        ):
            return "DOCX"

    lowered_type = (
        content_type
        or ""
    ).lower()

    if any(
        item in lowered_type
        for item in HTML_CONTENT_TYPES
    ):
        return "HTML"

    if any(
        item in lowered_type
        for item in PDF_CONTENT_TYPES
    ):
        return "PDF"

    if any(
        item in lowered_type
        for item in HWP_CONTENT_TYPES
    ):
        return "HWP"

    if (
        "hwpx"
        in lowered_type
    ):
        return "HWPX"

    # --------------------------------------------------------
    # Magic bytes
    # --------------------------------------------------------

    if data.startswith(
        b"%PDF"
    ):
        return "PDF"

    # HWP OLE
    if data.startswith(
        bytes.fromhex(
            "D0CF11E0A1B11AE1"
        )
    ):
        return "HWP"

    # ZIP-based formats
    if data.startswith(
        b"PK\x03\x04"
    ):

        try:

            with zipfile.ZipFile(
                io.BytesIO(
                    data
                )
            ) as zf:

                names = [
                    name.lower()
                    for name in zf.namelist()
                ]

                if any(
                    "contents/section"
                    in name
                    for name in names
                ):
                    return "HWPX"

                if (
                    "word/document.xml"
                    in names
                ):
                    return "DOCX"

        except Exception:
            pass

        return "ZIP"

    # HTML sniff
    head = data[
        :4096
    ].lstrip().lower()

    if (
        head.startswith(
            b"<!doctype html"
        )
        or b"<html"
        in head
    ):
        return "HTML"

    return "UNKNOWN"


# ============================================================
# TEXT DECODING
# ============================================================

def decode_text_bytes(
    data: bytes,
) -> Tuple[
    str,
    str,
]:

    encodings = [
        "utf-8",
        "cp949",
        "euc-kr",
    ]

    for encoding in encodings:

        try:

            text = data.decode(
                encoding
            )

            return (
                normalize_space(
                    text
                ),
                encoding,
            )

        except UnicodeDecodeError:
            continue

    return (
        normalize_space(
            data.decode(
                "utf-8",
                errors="replace",
            )
        ),
        "utf-8-replace",
    )


# ============================================================
# PDF PARSER
# ============================================================

def parse_pdf(
    data: bytes,
) -> Tuple[
    str,
    str,
]:

    try:

        from pypdf import PdfReader

        reader = PdfReader(
            io.BytesIO(
                data
            )
        )

        pages: List[str] = []

        for page in reader.pages:

            try:
                page_text = (
                    page.extract_text()
                    or ""
                )

            except Exception:
                page_text = ""

            if page_text:
                pages.append(
                    page_text
                )

        text = normalize_space(
            "\n".join(
                pages
            )
        )

        if text:
            return (
                text,
                "pypdf",
            )

    except Exception:
        pass

    return (
        "",
        "",
    )


# ============================================================
# HWPX PARSER
# ============================================================

def parse_hwpx(
    data: bytes,
) -> Tuple[
    str,
    str,
]:

    try:

        with zipfile.ZipFile(
            io.BytesIO(
                data
            )
        ) as zf:

            section_names = sorted(
                [
                    name
                    for name in zf.namelist()
                    if re.search(
                        r"(?:^|/)Contents/section\d+\.xml$",
                        name,
                        flags=re.IGNORECASE,
                    )
                ]
            )

            if not section_names:

                section_names = sorted(
                    [
                        name
                        for name in zf.namelist()
                        if (
                            name.lower().endswith(
                                ".xml"
                            )
                            and "section"
                            in name.lower()
                        )
                    ]
                )

            texts: List[str] = []

            for name in section_names:

                raw = zf.read(
                    name
                )

                decoded = raw.decode(
                    "utf-8",
                    errors="replace",
                )

                # XML text node 단순 추출
                decoded = re.sub(
                    r"<[^>]+>",
                    " ",
                    decoded,
                )

                decoded = html.unescape(
                    decoded
                )

                decoded = normalize_space(
                    decoded
                )

                if decoded:
                    texts.append(
                        decoded
                    )

            text = normalize_space(
                "\n".join(
                    texts
                )
            )

            if text:
                return (
                    text,
                    "zip-xml-hwpx",
                )

    except Exception:
        pass

    return (
        "",
        "",
    )


# ============================================================
# DOCX PARSER
# ============================================================

def parse_docx(
    data: bytes,
) -> Tuple[
    str,
    str,
]:

    try:

        with zipfile.ZipFile(
            io.BytesIO(
                data
            )
        ) as zf:

            document_xml = zf.read(
                "word/document.xml"
            )

            text = document_xml.decode(
                "utf-8",
                errors="replace",
            )

            text = re.sub(
                r"<[^>]+>",
                " ",
                text,
            )

            text = html.unescape(
                text
            )

            text = normalize_space(
                text
            )

            if text:

                return (
                    text,
                    "docx-xml",
                )

    except Exception:
        pass

    return (
        "",
        "",
    )


# ============================================================
# HWP PARSER
# ============================================================

def parse_hwp(
    data: bytes,
) -> Tuple[
    str,
    str,
]:

    """
    우선 pyhwp의 hwp5txt executable을 사용한다.

    Windows 환경에서:
        pip install pyhwp

    후 hwp5txt command가 PATH에 존재하면 사용한다.

    parser가 없다면 빈 결과를 반환하여
    DOWNLOAD_OR_PARSE_FAILED로 안전하게 남긴다.
    """

    executable = shutil.which(
        "hwp5txt"
    )

    if not executable:
        executable = shutil.which(
            "hwp5txt.exe"
        )

    if not executable:
        return (
            "",
            "",
        )

    temp_path: Optional[
        Path
    ] = None

    try:

        with tempfile.NamedTemporaryFile(
            suffix=".hwp",
            delete=False,
        ) as temp_file:

            temp_file.write(
                data
            )

            temp_path = Path(
                temp_file.name
            )

        completed = subprocess.run(
            [
                executable,
                str(
                    temp_path
                ),
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )

        if completed.returncode != 0:
            return (
                "",
                "",
            )

        raw = (
            completed.stdout
            or b""
        )

        text, encoding = (
            decode_text_bytes(
                raw
            )
        )

        if text:

            return (
                text,
                f"hwp5txt:{encoding}",
            )

    except Exception:
        pass

    finally:

        if (
            temp_path
            and temp_path.exists()
        ):

            try:
                temp_path.unlink()

            except OSError:
                pass

    return (
        "",
        "",
    )


# ============================================================
# PARSE DOCUMENT
# ============================================================

def parse_document(
    *,
    document_type: str,
    data: bytes,
) -> Tuple[
    str,
    str,
]:

    if document_type == "HTML":

        text, encoding = (
            decode_text_bytes(
                data
            )
        )

        return (
            strip_html(
                text
            ),
            f"html:{encoding}",
        )

    if document_type == "PDF":

        return parse_pdf(
            data
        )

    if document_type == "HWPX":

        return parse_hwpx(
            data
        )

    if document_type == "HWP":

        return parse_hwp(
            data
        )

    if document_type == "DOCX":

        return parse_docx(
            data
        )

    if document_type == "TEXT":

        text, encoding = (
            decode_text_bytes(
                data
            )
        )

        return (
            text,
            f"text:{encoding}",
        )

    # unknown도 text sniff는 해본다.
    text, encoding = decode_text_bytes(
        data
    )

    printable_ratio = 0.0

    if text:

        printable = sum(
            1
            for char in text
            if (
                char.isprintable()
                or char.isspace()
            )
        )

        printable_ratio = (
            printable
            / max(
                len(
                    text
                ),
                1,
            )
        )

    if printable_ratio >= 0.90:

        return (
            text,
            f"fallback-text:{encoding}",
        )

    return (
        "",
        "",
    )


# ============================================================
# TARGET CONTEXT
# ============================================================

def extract_target_contexts(
    text: str,
    radius: int = 1000,
) -> List[str]:

    contexts: List[str] = []

    start = 0

    while True:

        index = text.find(
            TARGET_NAME,
            start,
        )

        if index < 0:
            break

        left = max(
            0,
            index - radius,
        )

        right = min(
            len(
                text
            ),
            (
                index
                + len(
                    TARGET_NAME
                )
                + radius
            ),
        )

        contexts.append(
            normalize_space(
                text[
                    left:right
                ]
            )
        )

        start = (
            index
            + len(
                TARGET_NAME
            )
        )

    return unique_strings(
        contexts
    )


# ============================================================
# ACTION
# ============================================================

def extract_action_context(
    text: str,
) -> Tuple[
    List[str],
    List[str],
]:

    contexts = extract_target_contexts(
        text,
        radius=1200,
    )

    corpus = "\n".join(
        contexts
    )

    action_types: List[str] = []

    evidence: List[str] = []

    for (
        action_type,
        patterns,
    ) in ACTION_PATTERNS.items():

        for pattern in patterns:

            match = re.search(
                pattern,
                corpus,
                flags=(
                    re.IGNORECASE
                    | re.DOTALL
                ),
            )

            if not match:
                continue

            action_types.append(
                action_type
            )

            evidence.append(
                normalize_space(
                    match.group(0)
                )
            )

    return (
        unique_strings(
            action_types
        ),
        unique_strings(
            evidence
        ),
    )


# ============================================================
# NOTICE NUMBER
# ============================================================

def extract_notice_numbers(
    text: str,
) -> List[str]:

    values: List[str] = []

    # target 주변을 우선한다.
    target_contexts = (
        extract_target_contexts(
            text,
            radius=3000,
        )
    )

    corpus = (
        "\n".join(
            target_contexts
        )
        if target_contexts
        else text[
            :10000
        ]
    )

    for pattern in NOTICE_NUMBER_PATTERNS:

        for match in pattern.finditer(
            corpus
        ):

            value = (
                match.groupdict().get(
                    "notice"
                )
                or match.group(0)
            )

            values.append(
                normalize_space(
                    value
                )
            )

    return unique_strings(
        values
    )


# ============================================================
# DATES
# ============================================================

def extract_dates(
    text: str,
) -> List[str]:

    values: List[str] = []

    contexts = extract_target_contexts(
        text,
        radius=4000,
    )

    corpus = (
        "\n".join(
            contexts
        )
        if contexts
        else text[
            :12000
        ]
    )

    for pattern in DATE_PATTERNS:

        for match in pattern.finditer(
            corpus
        ):

            year = int(
                match.group(
                    "year"
                )
            )

            month = int(
                match.group(
                    "month"
                )
            )

            day = int(
                match.group(
                    "day"
                )
            )

            values.append(
                f"{year:04d}-"
                f"{month:02d}-"
                f"{day:02d}"
            )

    return unique_strings(
        values
    )


# ============================================================
# REGION
# ============================================================

def extract_regions(
    text: str,
    metadata_region: str,
) -> List[str]:

    values: List[str] = []

    if metadata_region:
        values.append(
            metadata_region
        )

    contexts = extract_target_contexts(
        text,
        radius=4000,
    )

    corpus = (
        "\n".join(
            contexts
        )
        if contexts
        else text[
            :12000
        ]
    )

    for region in REGION_PATTERNS:

        if region in corpus:

            values.append(
                region
            )

    local_patterns = [
        r"([가-힣]{2,12}시)\s*(?:고시|공고|시장)",
        r"([가-힣]{2,12}군)\s*(?:고시|공고|군수)",
        r"([가-힣]{2,12}구)\s*(?:고시|공고|구청장)",
    ]

    for pattern in local_patterns:

        for match in re.finditer(
            pattern,
            corpus,
        ):

            values.append(
                match.group(1)
            )

    return unique_strings(
        values
    )


# ============================================================
# OFFICIAL CONTEXT
# ============================================================

def extract_official_context(
    text: str,
) -> List[str]:

    evidence: List[str] = []

    contexts = extract_target_contexts(
        text,
        radius=2000,
    )

    corpus = "\n".join(
        contexts
    )

    for pattern in OFFICIAL_CONTEXT_PATTERNS:

        match = re.search(
            pattern,
            corpus,
            flags=re.IGNORECASE,
        )

        if match:

            evidence.append(
                normalize_space(
                    match.group(0)
                )
            )

    return unique_strings(
        evidence
    )


# ============================================================
# SCOPE
# ============================================================

def extract_scope_evidence(
    text: str,
) -> List[str]:

    evidence: List[str] = []

    contexts = extract_target_contexts(
        text,
        radius=5000,
    )

    corpus = "\n".join(
        contexts
    )

    for pattern in SCOPE_PATTERNS:

        for match in re.finditer(
            pattern,
            corpus,
            flags=re.IGNORECASE,
        ):

            evidence.append(
                normalize_space(
                    match.group(0)
                )
            )

    return unique_strings(
        evidence
    )


# ============================================================
# ADMINISTRATIVE DUTY
# ============================================================

def detect_administrative_duty_reference(
    text: str,
) -> Tuple[
    bool,
    List[str],
    Dict[str, Any],
]:

    contexts = extract_target_contexts(
        text,
        radius=2500,
    )

    corpus = (
        "\n".join(
            contexts
        )
        if contexts
        else text[
            :10000
        ]
    )

    structure_evidence = [
        term
        for term in ADMIN_DUTY_STRUCTURE_TERMS
        if term in corpus
    ]

    table_evidence = [
        term
        for term in ADMIN_DUTY_TABLE_TERMS
        if term in corpus
    ]

    draft_marker_count = len(
        re.findall(
            r"기안\s*[○●◎]?",
            corpus,
        )
    )

    target_draft_match = re.search(
        r"개발밀도관리구역.{0,120}?기안\s*[○●◎]?",
        corpus,
        flags=re.DOTALL,
    )

    target_draft_evidence = (
        normalize_space(
            target_draft_match.group(0)
        )
        if target_draft_match
        else ""
    )

    strong_structure = (
        (
            "단위사무명"
            in corpus
            or "단 위 사 무 명"
            in corpus
        )
        and (
            "전결권자"
            in corpus
            or "전 결 권 자"
            in corpus
        )
    )

    repeated_draft_markers = (
        draft_marker_count
        >= 5
    )

    heavy_draft_table_signature = (
        draft_marker_count
        >= 10
        and (
            len(
                structure_evidence
            )
            >= 1
            or len(
                table_evidence
            )
            >= 3
        )
    )

    administrative_reference = (
        strong_structure
        or heavy_draft_table_signature
        or (
            bool(
                target_draft_evidence
            )
            and repeated_draft_markers
        )
    )

    evidence = (
        structure_evidence
        + table_evidence
    )

    if repeated_draft_markers:

        evidence.append(
            f"기안 marker x{draft_marker_count}"
        )

    if target_draft_evidence:

        evidence.append(
            target_draft_evidence
        )

    diagnostics = {
        "strong_structure":
            strong_structure,

        "structure_evidence":
            unique_strings(
                structure_evidence
            ),

        "table_evidence":
            unique_strings(
                table_evidence
            ),

        "draft_marker_count":
            draft_marker_count,

        "repeated_draft_markers":
            repeated_draft_markers,

        "heavy_draft_table_signature":
            heavy_draft_table_signature,

        "target_is_draft_duty":
            bool(
                target_draft_evidence
            ),

        "target_draft_evidence":
            target_draft_evidence,
    }

    return (
        administrative_reference,
        unique_strings(
            evidence
        ),
        diagnostics,
    )


# ============================================================
# LEGAL REFERENCE
# ============================================================

def detect_legal_reference_only(
    *,
    text: str,
    action_types: List[str],
    notice_numbers: List[str],
    official_context: List[str],
) -> Tuple[
    bool,
    List[str],
]:

    contexts = extract_target_contexts(
        text,
        radius=1500,
    )

    corpus = "\n".join(
        contexts
    )

    evidence: List[str] = []

    for pattern in LEGAL_REFERENCE_PATTERNS:

        match = re.search(
            pattern,
            corpus,
            flags=re.IGNORECASE,
        )

        if match:

            evidence.append(
                normalize_space(
                    match.group(0)
                )
            )

    substantial_notice_evidence = (
        bool(
            action_types
        )
        and bool(
            notice_numbers
        )
        and bool(
            official_context
        )
    )

    legal_reference_only = (
        bool(
            evidence
        )
        and not substantial_notice_evidence
    )

    return (
        legal_reference_only,
        unique_strings(
            evidence
        ),
    )


# ============================================================
# GAZETTE CONTAINER GUARD
# ============================================================

def detect_gazette_container(
    *,
    input_classification: str,
    url: str,
    text: str,
    notice_numbers: List[str],
) -> Tuple[
    bool,
    List[str],
]:

    evidence: List[str] = []

    if (
        input_classification
        == "GAZETTE_ISSUE_SEED"
    ):

        evidence.append(
            "INPUT_CLASS_GAZETTE_ISSUE_SEED"
        )

    lowered_url = url.lower()

    for term in GAZETTE_CONTAINER_HINTS:

        if term.lower() in lowered_url:

            evidence.append(
                f"URL:{term}"
            )

    target_contexts = extract_target_contexts(
        text,
        radius=3000,
    )

    target_corpus = "\n".join(
        target_contexts
    )

    for term in GAZETTE_TERMS:

        if term in target_corpus:

            evidence.append(
                term
            )

    # 하나의 issue 안에 다수의 notice가 섞여 있으면 container 가능성이 높다.
    multiple_notice_container = (
        len(
            notice_numbers
        )
        >= 4
    )

    if multiple_notice_container:

        evidence.append(
            "MULTIPLE_NOTICE_NUMBERS_IN_CONTAINER"
        )

    gazette_container = (
        input_classification
        == "GAZETTE_ISSUE_SEED"
        and (
            bool(
                evidence
            )
            or multiple_notice_container
        )
    )

    return (
        gazette_container,
        unique_strings(
            evidence
        ),
    )


# ============================================================
# VERIFY ONE DOCUMENT
# ============================================================

def verify_document(
    *,
    seed: Dict[str, Any],
    response: Dict[str, Any],
    document_type: str,
    text: str,
    parser_name: str,
    index: int,
) -> Dict[str, Any]:

    region = normalize_space(
        seed.get(
            "region"
        )
    )

    input_classification = normalize_space(
        seed.get(
            "classification"
        )
    )

    requested_url = normalize_space(
        seed.get(
            "verification_url"
        )
    )

    final_url = normalize_space(
        response.get(
            "final_url"
        )
    ) or requested_url

    target_in_document = (
        TARGET_NAME
        in text
    )

    target_contexts = (
        extract_target_contexts(
            text,
            radius=1500,
        )
    )

    (
        action_types,
        action_evidence,
    ) = extract_action_context(
        text
    )

    notice_numbers = (
        extract_notice_numbers(
            text
        )
    )

    dates = extract_dates(
        text
    )

    regions = extract_regions(
        text,
        region,
    )

    official_context_evidence = (
        extract_official_context(
            text
        )
    )

    scope_evidence = (
        extract_scope_evidence(
            text
        )
    )

    (
        administrative_duty_reference,
        administrative_duty_evidence,
        administrative_duty_diagnostics,
    ) = detect_administrative_duty_reference(
        text
    )

    (
        legal_reference_only,
        legal_reference_evidence,
    ) = detect_legal_reference_only(
        text=text,
        action_types=action_types,
        notice_numbers=notice_numbers,
        official_context=(
            official_context_evidence
        ),
    )

    (
        gazette_container,
        gazette_container_evidence,
    ) = detect_gazette_container(
        input_classification=(
            input_classification
        ),
        url=final_url,
        text=text,
        notice_numbers=notice_numbers,
    )

    has_action = bool(
        action_types
    )

    has_notice_number = bool(
        notice_numbers
    )

    has_official_context = bool(
        official_context_evidence
    )

    has_geographic_context = bool(
        regions
    )

    has_scope_evidence = bool(
        scope_evidence
    )

    # ========================================================
    # VERIFIED POSITIVE
    # ========================================================

    verified_positive = (
        target_in_document
        and has_action
        and has_notice_number
        and has_official_context
        and has_geographic_context
        and not administrative_duty_reference
        and not legal_reference_only
        and not gazette_container
    )

    reasons: List[str] = []

    if not target_in_document:

        reasons.append(
            "TARGET_NOT_IN_DOCUMENT"
        )

    if not has_action:

        reasons.append(
            "NO_ACTION_CONTEXT"
        )

    if not has_notice_number:

        reasons.append(
            "NO_NOTICE_NUMBER"
        )

    if not has_official_context:

        reasons.append(
            "NO_OFFICIAL_CONTEXT"
        )

    if not has_geographic_context:

        reasons.append(
            "NO_GEOGRAPHIC_CONTEXT"
        )

    if administrative_duty_reference:

        reasons.append(
            "ADMINISTRATIVE_DUTY_REFERENCE"
        )

    if legal_reference_only:

        reasons.append(
            "LEGAL_REFERENCE_ONLY"
        )

    if gazette_container:

        reasons.append(
            "GAZETTE_CONTAINER_REQUIRES_CHILD_RESOLUTION"
        )

    if not has_scope_evidence:

        reasons.append(
            "SCOPE_NOT_EXTRACTED"
        )

    # ========================================================
    # RESOLUTION PRIORITY
    # ========================================================

    if verified_positive:

        resolution = (
            RESOLUTION_VERIFIED
        )

    elif administrative_duty_reference:

        resolution = (
            RESOLUTION_ADMIN_DUTY
        )

    elif legal_reference_only:

        resolution = (
            RESOLUTION_LEGAL_REFERENCE
        )

    elif gazette_container:

        resolution = (
            RESOLUTION_GAZETTE_CONTAINER
        )

    elif not target_in_document:

        resolution = (
            RESOLUTION_UNRELATED
        )

    elif not has_action:

        resolution = (
            RESOLUTION_TARGET_NO_ACTION
        )

    elif not has_notice_number:

        resolution = (
            RESOLUTION_ACTION_NO_NOTICE
        )

    elif not has_official_context:

        resolution = (
            RESOLUTION_TARGET_NO_OFFICIAL
        )

    elif not has_geographic_context:

        resolution = (
            RESOLUTION_TARGET_NO_GEO
        )

    else:

        resolution = (
            RESOLUTION_UNRELATED
        )

    return {
        "candidate_index":
            index,

        "verification_identity":
            seed.get(
                "verification_identity"
            ),

        "region":
            region,

        "agency":
            normalize_space(
                seed.get(
                    "agency"
                )
            ),

        "input_classification":
            input_classification,

        "input_score":
            int(
                seed.get(
                    "score"
                )
                or 0
            ),

        "input_label":
            normalize_space(
                seed.get(
                    "label"
                )
            ),

        "merged_input_classes":
            seed.get(
                "merged_input_classes"
            )
            or [],

        "merged_seed_count":
            int(
                seed.get(
                    "merged_seed_count"
                )
                or 1
            ),

        "raw_seed_urls":
            seed.get(
                "merged_raw_urls"
            )
            or [
                normalize_space(
                    seed.get(
                        "raw_seed_url"
                    )
                )
            ],

        "requested_url":
            requested_url,

        "final_url":
            final_url,

        "http_status":
            response.get(
                "http_status"
            ),

        "content_type":
            response.get(
                "content_type"
            ),

        "content_disposition":
            response.get(
                "content_disposition"
            ),

        "response_bytes":
            int(
                response.get(
                    "response_bytes"
                )
                or 0
            ),

        "document_type":
            document_type,

        "parser":
            parser_name,

        "document_text_length":
            len(
                text
            ),

        "document_text_sha256":
            (
                stable_hash(
                    text
                )
                if text
                else ""
            ),

        "target_in_document":
            target_in_document,

        "target_contexts":
            target_contexts[
                :20
            ],

        "action_context":
            has_action,

        "action_types":
            action_types,

        "action_evidence":
            action_evidence,

        "notice_numbers":
            notice_numbers,

        "dates":
            dates,

        "administrative_regions":
            regions,

        "official_context":
            has_official_context,

        "official_context_evidence":
            official_context_evidence,

        "administrative_duty_reference":
            administrative_duty_reference,

        "administrative_duty_evidence":
            administrative_duty_evidence,

        "administrative_duty_diagnostics":
            administrative_duty_diagnostics,

        "legal_reference_only":
            legal_reference_only,

        "legal_reference_evidence":
            legal_reference_evidence,

        "gazette_container":
            gazette_container,

        "gazette_container_evidence":
            gazette_container_evidence,

        "scope_extraction_status":
            (
                "SCOPE_EVIDENCE_EXTRACTED"
                if has_scope_evidence
                else "SCOPE_NOT_EXTRACTED"
            ),

        "scope_evidence":
            scope_evidence,

        "verified_positive":
            verified_positive,

        "resolution":
            resolution,

        "reasons":
            unique_strings(
                reasons
            ),

        # J-stage도 runtime 등록은 금지
        "runtime_registration_allowed":
            False,

        "site_positive_allowed":
            False,
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
        "OFFICIAL NOTICE SOURCE VERIFICATION"
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

    print(
        f"Input: {INPUT_PATH}"
    )

    print()

    # ========================================================
    # INPUT
    # ========================================================

    if not INPUT_PATH.exists():

        raise FileNotFoundError(
            "I-stage output not found: "
            f"{INPUT_PATH}"
        )

    input_data = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    raw_seeds = load_input_seeds(
        input_data
    )

    (
        seeds,
        duplicate_seed_removed_count,
    ) = dedupe_input_seeds(
        raw_seeds
    )

    # ========================================================
    # INPUT SUMMARY
    # ========================================================

    raw_class_counts = Counter(
        normalize_space(
            item.get(
                "classification"
            )
        )
        for item in raw_seeds
    )

    print(
        "I-stage input verification pool:",
        len(
            raw_seeds
        ),
    )

    print(
        "Discovery-query / canonical dedupe result:",
        len(
            seeds
        ),
    )

    print(
        "Duplicate/search variants removed:",
        duplicate_seed_removed_count,
    )

    print()

    print(
        "TARGET_DIRECT_DETAIL_SEED:",
        raw_class_counts.get(
            "TARGET_DIRECT_DETAIL_SEED",
            0,
        ),
    )

    print(
        "URBAN_NOTICE_DETAIL_SEED:",
        raw_class_counts.get(
            "URBAN_NOTICE_DETAIL_SEED",
            0,
        ),
    )

    print(
        "GAZETTE_ISSUE_SEED:",
        raw_class_counts.get(
            "GAZETTE_ISSUE_SEED",
            0,
        ),
    )

    print(
        "ATTACHMENT_DOCUMENT_SEED:",
        raw_class_counts.get(
            "ATTACHMENT_DOCUMENT_SEED",
            0,
        ),
    )

    print(
        "EXTENSIONLESS_DOWNLOAD_SEED:",
        raw_class_counts.get(
            "EXTENSIONLESS_DOWNLOAD_SEED",
            0,
        ),
    )

    print()

    # ========================================================
    # SESSION
    # ========================================================

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent":
                USER_AGENT,

            "Accept":
                (
                    "text/html,"
                    "application/xhtml+xml,"
                    "application/pdf,"
                    "application/octet-stream,"
                    "*/*;q=0.8"
                ),

            "Accept-Language":
                (
                    "ko-KR,ko;q=0.9,"
                    "en-US;q=0.7,en;q=0.5"
                ),
        }
    )

    # ========================================================
    # EXECUTE
    # ========================================================

    verified_records: List[
        Dict[str, Any]
    ] = []

    request_count = 0

    http_success_count = 0

    download_failed_count = 0

    parse_failed_count = 0

    for index, seed in enumerate(
        seeds,
        start=1,
    ):

        verification_url = normalize_space(
            seed.get(
                "verification_url"
            )
        )

        print(
            "-" * 60
        )

        print(
            f"CANDIDATE {index}"
        )

        print(
            "Region:",
            seed.get(
                "region"
            )
            or "-",
        )

        print(
            "Input class:",
            seed.get(
                "classification"
            ),
        )

        print(
            "URL:",
            verification_url,
        )

        request_count += 1

        response = request_document(
            session,
            verification_url,
        )

        if response.get(
            "http_status"
        ) == 200:

            http_success_count += 1

        # ====================================================
        # DOWNLOAD FAILURE
        # ====================================================

        if (
            response.get(
                "error"
            )
            or not response.get(
                "data"
            )
        ):

            download_failed_count += 1

            result = {
                "candidate_index":
                    index,

                "verification_identity":
                    seed.get(
                        "verification_identity"
                    ),

                "region":
                    normalize_space(
                        seed.get(
                            "region"
                        )
                    ),

                "agency":
                    normalize_space(
                        seed.get(
                            "agency"
                        )
                    ),

                "input_classification":
                    normalize_space(
                        seed.get(
                            "classification"
                        )
                    ),

                "input_label":
                    normalize_space(
                        seed.get(
                            "label"
                        )
                    ),

                "requested_url":
                    verification_url,

                "final_url":
                    response.get(
                        "final_url"
                    )
                    or "",

                "http_status":
                    response.get(
                        "http_status"
                    ),

                "content_type":
                    response.get(
                        "content_type"
                    )
                    or "",

                "response_bytes":
                    int(
                        response.get(
                            "response_bytes"
                        )
                        or 0
                    ),

                "document_type":
                    "",

                "parser":
                    "",

                "document_text_length":
                    0,

                "target_in_document":
                    False,

                "target_contexts":
                    [],

                "action_context":
                    False,

                "action_types":
                    [],

                "action_evidence":
                    [],

                "notice_numbers":
                    [],

                "dates":
                    [],

                "administrative_regions":
                    [],

                "official_context":
                    False,

                "official_context_evidence":
                    [],

                "administrative_duty_reference":
                    False,

                "administrative_duty_evidence":
                    [],

                "legal_reference_only":
                    False,

                "legal_reference_evidence":
                    [],

                "gazette_container":
                    False,

                "gazette_container_evidence":
                    [],

                "scope_extraction_status":
                    "SCOPE_NOT_EXTRACTED",

                "scope_evidence":
                    [],

                "verified_positive":
                    False,

                "resolution":
                    RESOLUTION_DOWNLOAD_FAILED,

                "reasons": [
                    "HTTP_DOWNLOAD_FAILED",
                    normalize_space(
                        response.get(
                            "error"
                        )
                    ),
                ],

                "runtime_registration_allowed":
                    False,

                "site_positive_allowed":
                    False,
            }

            verified_records.append(
                result
            )

            print(
                "HTTP status:",
                result[
                    "http_status"
                ],
            )

            print(
                "Resolution:",
                result[
                    "resolution"
                ],
            )

            print(
                "Error:",
                response.get(
                    "error"
                ),
            )

            continue

        # ====================================================
        # TYPE
        # ====================================================

        data = response[
            "data"
        ]

        document_type = detect_document_type(
            url=(
                response.get(
                    "final_url"
                )
                or verification_url
            ),
            content_type=(
                response.get(
                    "content_type"
                )
                or ""
            ),
            content_disposition=(
                response.get(
                    "content_disposition"
                )
                or ""
            ),
            data=data,
        )

        # ====================================================
        # PARSE
        # ====================================================

        (
            text,
            parser_name,
        ) = parse_document(
            document_type=document_type,
            data=data,
        )

        if not text:

            parse_failed_count += 1

            result = {
                "candidate_index":
                    index,

                "verification_identity":
                    seed.get(
                        "verification_identity"
                    ),

                "region":
                    normalize_space(
                        seed.get(
                            "region"
                        )
                    ),

                "agency":
                    normalize_space(
                        seed.get(
                            "agency"
                        )
                    ),

                "input_classification":
                    normalize_space(
                        seed.get(
                            "classification"
                        )
                    ),

                "input_label":
                    normalize_space(
                        seed.get(
                            "label"
                        )
                    ),

                "requested_url":
                    verification_url,

                "final_url":
                    response.get(
                        "final_url"
                    )
                    or verification_url,

                "http_status":
                    response.get(
                        "http_status"
                    ),

                "content_type":
                    response.get(
                        "content_type"
                    )
                    or "",

                "response_bytes":
                    int(
                        response.get(
                            "response_bytes"
                        )
                        or 0
                    ),

                "document_type":
                    document_type,

                "parser":
                    parser_name,

                "document_text_length":
                    0,

                "target_in_document":
                    False,

                "target_contexts":
                    [],

                "action_context":
                    False,

                "action_types":
                    [],

                "action_evidence":
                    [],

                "notice_numbers":
                    [],

                "dates":
                    [],

                "administrative_regions":
                    [],

                "official_context":
                    False,

                "official_context_evidence":
                    [],

                "administrative_duty_reference":
                    False,

                "administrative_duty_evidence":
                    [],

                "legal_reference_only":
                    False,

                "legal_reference_evidence":
                    [],

                "gazette_container":
                    False,

                "gazette_container_evidence":
                    [],

                "scope_extraction_status":
                    "SCOPE_NOT_EXTRACTED",

                "scope_evidence":
                    [],

                "verified_positive":
                    False,

                "resolution":
                    RESOLUTION_PARSE_FAILED,

                "reasons": [
                    "DOCUMENT_TEXT_EXTRACTION_FAILED",
                ],

                "runtime_registration_allowed":
                    False,

                "site_positive_allowed":
                    False,
            }

            verified_records.append(
                result
            )

            print(
                "HTTP status:",
                result[
                    "http_status"
                ],
            )

            print(
                "Document type:",
                document_type,
            )

            print(
                "Resolution:",
                result[
                    "resolution"
                ],
            )

            continue

        # ====================================================
        # VERIFY
        # ====================================================

        result = verify_document(
            seed=seed,
            response=response,
            document_type=document_type,
            text=text,
            parser_name=parser_name,
            index=index,
        )

        verified_records.append(
            result
        )

        print(
            "HTTP status:",
            result[
                "http_status"
            ],
        )

        print(
            "Document type:",
            result[
                "document_type"
            ],
        )

        print(
            "Parser:",
            result[
                "parser"
            ],
        )

        print(
            "Text length:",
            result[
                "document_text_length"
            ],
        )

        print(
            "Target:",
            result[
                "target_in_document"
            ],
        )

        print(
            "Action:",
            result[
                "action_types"
            ],
        )

        print(
            "Notice numbers:",
            result[
                "notice_numbers"
            ],
        )

        print(
            "Dates:",
            result[
                "dates"
            ],
        )

        print(
            "Regions:",
            result[
                "administrative_regions"
            ],
        )

        print(
            "Admin duty:",
            result[
                "administrative_duty_reference"
            ],
        )

        print(
            "Legal reference only:",
            result[
                "legal_reference_only"
            ],
        )

        print(
            "Gazette container:",
            result[
                "gazette_container"
            ],
        )

        print(
            "Scope:",
            result[
                "scope_extraction_status"
            ],
        )

        print(
            "Verified positive:",
            result[
                "verified_positive"
            ],
        )

        print(
            "Resolution:",
            result[
                "resolution"
            ],
        )

        print(
            "Reasons:",
            result[
                "reasons"
            ],
        )

        if result[
            "target_contexts"
        ]:

            print(
                "Target context preview:"
            )

            print(
                result[
                    "target_contexts"
                ][0][
                    :2000
                ]
            )

        if REQUEST_DELAY_SECONDS > 0:

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

    # ========================================================
    # SPLIT RESULT
    # ========================================================

    verified_positive_records = [
        item
        for item in verified_records
        if item.get(
            "verified_positive"
        )
        is True
    ]

    admin_duty_records = [
        item
        for item in verified_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_ADMIN_DUTY
    ]

    legal_reference_records = [
        item
        for item in verified_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_LEGAL_REFERENCE
    ]

    gazette_container_records = [
        item
        for item in verified_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_GAZETTE_CONTAINER
    ]

    target_no_action_records = [
        item
        for item in verified_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_TARGET_NO_ACTION
    ]

    action_no_notice_records = [
        item
        for item in verified_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_ACTION_NO_NOTICE
    ]

    unrelated_records = [
        item
        for item in verified_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_UNRELATED
    ]

    scope_extracted_count = sum(
        1
        for item in verified_records
        if item.get(
            "scope_extraction_status"
        )
        == "SCOPE_EVIDENCE_EXTRACTED"
    )

    resolution_counts = Counter(
        item.get(
            "resolution"
        )
        for item in verified_records
    )

    # ========================================================
    # RESOLUTION
    # ========================================================

    if verified_positive_records:

        resolution = (
            "OFFICIAL_NOTICE_SOURCE_VERIFICATION_"
            "VERIFIED_POSITIVE_DISCOVERED"
        )

        next_action = (
            "VERIFIED_OFFICIAL_NOTICE에서 고시번호·고시일·행정구역·"
            "지정/변경/해제 action 및 scope evidence를 정규화하고, "
            "후속 변경·해제 고시를 추적하여 현재 유효 상태를 판정한다. "
            "그 이후에만 PNU/spatial dataset 역탐색 단계로 진행한다."
        )

    elif gazette_container_records:

        resolution = (
            "OFFICIAL_NOTICE_SOURCE_VERIFICATION_"
            "GAZETTE_CHILD_RESOLUTION_REQUIRED"
        )

        next_action = (
            "공보/시보 issue container 자체는 positive로 승격하지 않는다. "
            "target context 인접 고시번호와 issue 내부 개별 고시/첨부파일 "
            "identity를 추출하여 child document verification 단계로 진행한다."
        )

    elif (
        target_no_action_records
        or action_no_notice_records
    ):

        resolution = (
            "OFFICIAL_NOTICE_SOURCE_VERIFICATION_"
            "TARGET_DOCUMENT_INCOMPLETE_EVIDENCE"
        )

        next_action = (
            "target exact phrase는 원문에서 확인되었으나 "
            "action 또는 고시번호 evidence가 부족하다. "
            "동일 문서의 상단 header, 원문 첨부파일, 인접 고시번호, "
            "공보 child document를 추적한다."
        )

    else:

        resolution = (
            "OFFICIAL_NOTICE_SOURCE_VERIFICATION_"
            "COMPLETED_NO_POSITIVE"
        )

        next_action = (
            "현재 recovery seed에서는 verified official notice를 "
            "확정하지 못했다. false-positive는 종결하고, "
            "공보 child-document resolution 또는 공식 고시번호 "
            "역탐색 단계로 확장한다."
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-J "
            "Development Density Management Area "
            "Official Notice Source Verification"
        ),

        "target": {
            "name":
                TARGET_NAME,

            "standard_code":
                STANDARD_CODE,
        },

        "input": {
            "path":
                str(
                    INPUT_PATH
                ),

            "i_stage_resolution":
                input_data.get(
                    "resolution"
                ),
        },

        "method": {
            "network_requery":
                True,

            "document_local_evidence_only":
                True,

            "i_stage_page_evidence_inheritance":
                False,

            "discovery_query_parameter_removal":
                True,

            "document_identity_recanonicalization":
                True,

            "pdf_parser_enabled":
                True,

            "hwp_parser_enabled":
                True,

            "hwpx_parser_enabled":
                True,

            "gazette_container_positive_prohibited":
                True,

            "administrative_duty_false_positive_guard":
                True,

            "legal_reference_false_positive_guard":
                True,

            "scope_extraction_enabled":
                True,

            "scope_required_for_verified_positive":
                False,

            "runtime_registration_allowed":
                False,

            "site_positive_allowed":
                False,
        },

        "summary": {
            "raw_i_stage_seed_count":
                len(
                    raw_seeds
                ),

            "canonical_verification_seed_count":
                len(
                    seeds
                ),

            "duplicate_or_search_variant_removed_count":
                duplicate_seed_removed_count,

            "request_count":
                request_count,

            "http_success_count":
                http_success_count,

            "download_failed_count":
                download_failed_count,

            "parse_failed_count":
                parse_failed_count,

            "verified_record_count":
                len(
                    verified_records
                ),

            "verified_positive_count":
                len(
                    verified_positive_records
                ),

            "administrative_duty_reference_count":
                len(
                    admin_duty_records
                ),

            "legal_reference_only_count":
                len(
                    legal_reference_records
                ),

            "gazette_container_count":
                len(
                    gazette_container_records
                ),

            "target_no_action_count":
                len(
                    target_no_action_records
                ),

            "action_no_notice_count":
                len(
                    action_no_notice_records
                ),

            "unrelated_document_count":
                len(
                    unrelated_records
                ),

            "scope_extracted_count":
                scope_extracted_count,
        },

        "input_class_counts":
            dict(
                sorted(
                    raw_class_counts.items()
                )
            ),

        "resolution_counts":
            dict(
                sorted(
                    resolution_counts.items()
                )
            ),

        "verified_records":
            verified_records,

        "verified_positive_documents":
            verified_positive_records,

        "gazette_container_candidates":
            gazette_container_records,

        "administrative_duty_references":
            admin_duty_records,

        "legal_reference_only_documents":
            legal_reference_records,

        "resolution":
            resolution,

        "next_action":
            next_action,

        "runtime_registration_allowed":
            False,

        "site_positive_allowed":
            False,
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
    # SUMMARY PRINT
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "VERIFICATION RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "Raw I-stage seed count:",
        len(
            raw_seeds
        ),
    )

    print(
        "Canonical verification seed count:",
        len(
            seeds
        ),
    )

    print(
        "Duplicate/search variants removed:",
        duplicate_seed_removed_count,
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
        "Download failed count:",
        download_failed_count,
    )

    print(
        "Parse failed count:",
        parse_failed_count,
    )

    print(
        "Verified positive count:",
        len(
            verified_positive_records
        ),
    )

    print(
        "Administrative-duty-reference count:",
        len(
            admin_duty_records
        ),
    )

    print(
        "Legal-reference-only count:",
        len(
            legal_reference_records
        ),
    )

    print(
        "Gazette-container count:",
        len(
            gazette_container_records
        ),
    )

    print(
        "Target-no-action count:",
        len(
            target_no_action_records
        ),
    )

    print(
        "Action-no-notice count:",
        len(
            action_no_notice_records
        ),
    )

    print(
        "Scope evidence extracted count:",
        scope_extracted_count,
    )

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

    canonical_seed_keys = {
        seed_identity(
            item
        )
        for item in seeds
    }

    verified_identity_keys = {
        item.get(
            "verification_identity"
        )
        for item in verified_records
    }

    verified_positive_urls = [
        item.get(
            "final_url"
        )
        or item.get(
            "requested_url"
        )
        for item in verified_positive_records
    ]

    duplicate_positive_urls = (
        len(
            verified_positive_urls
        )
        - len(
            set(
                verified_positive_urls
            )
        )
    )

    admin_duty_positive_leakage = sum(
        1
        for item in verified_positive_records
        if item.get(
            "administrative_duty_reference"
        )
        is True
    )

    legal_reference_positive_leakage = sum(
        1
        for item in verified_positive_records
        if item.get(
            "legal_reference_only"
        )
        is True
    )

    gazette_container_positive_leakage = sum(
        1
        for item in verified_positive_records
        if item.get(
            "gazette_container"
        )
        is True
    )

    target_missing_positive_leakage = sum(
        1
        for item in verified_positive_records
        if item.get(
            "target_in_document"
        )
        is not True
    )

    no_action_positive_leakage = sum(
        1
        for item in verified_positive_records
        if item.get(
            "action_context"
        )
        is not True
    )

    no_notice_positive_leakage = sum(
        1
        for item in verified_positive_records
        if not item.get(
            "notice_numbers"
        )
    )

    no_official_positive_leakage = sum(
        1
        for item in verified_positive_records
        if item.get(
            "official_context"
        )
        is not True
    )

    no_geography_positive_leakage = sum(
        1
        for item in verified_positive_records
        if not item.get(
            "administrative_regions"
        )
    )

    discovery_query_leakage = 0

    for seed in seeds:

        parsed = urlparse(
            seed.get(
                "verification_url"
            )
            or ""
        )

        keys = {
            normalize_query_key(
                key
            ).lower()
            for key, _ in parse_qsl(
                parsed.query,
                keep_blank_values=True,
            )
        }

        if (
            keys
            & DISCOVERY_ONLY_QUERY_KEYS
        ):

            discovery_query_leakage += 1

    validations = {
        "target name": (
            TARGET_NAME
            == "개발밀도관리구역"
        ),

        "standard code": (
            STANDARD_CODE
            == "UQQ700"
        ),

        "input exists": (
            INPUT_PATH.exists()
        ),

        "I-stage input parsed": (
            isinstance(
                input_data,
                dict,
            )
        ),

        "verification seeds loaded": (
            len(
                raw_seeds
            )
            > 0
        ),

        "only allowed I-stage classes loaded": all(
            normalize_space(
                item.get(
                    "classification"
                )
            )
            in ALLOWED_INPUT_CLASSES
            for item in raw_seeds
        ),

        "discovery query removal enabled": (
            output_data[
                "method"
            ][
                "discovery_query_parameter_removal"
            ]
            is True
        ),

        "discovery query leakage zero": (
            discovery_query_leakage
            == 0
        ),

        "canonical verification seeds unique": (
            len(
                canonical_seed_keys
            )
            == len(
                seeds
            )
        ),

        "network requery enabled": (
            output_data[
                "method"
            ][
                "network_requery"
            ]
            is True
        ),

        "document-local evidence only": (
            output_data[
                "method"
            ][
                "document_local_evidence_only"
            ]
            is True
        ),

        "I-stage page evidence inheritance disabled": (
            output_data[
                "method"
            ][
                "i_stage_page_evidence_inheritance"
            ]
            is False
        ),

        "PDF parser enabled": (
            output_data[
                "method"
            ][
                "pdf_parser_enabled"
            ]
            is True
        ),

        "HWP parser enabled": (
            output_data[
                "method"
            ][
                "hwp_parser_enabled"
            ]
            is True
        ),

        "HWPX parser enabled": (
            output_data[
                "method"
            ][
                "hwpx_parser_enabled"
            ]
            is True
        ),

        "administrative-duty false-positive guard enabled": (
            output_data[
                "method"
            ][
                "administrative_duty_false_positive_guard"
            ]
            is True
        ),

        "legal-reference false-positive guard enabled": (
            output_data[
                "method"
            ][
                "legal_reference_false_positive_guard"
            ]
            is True
        ),

        "gazette container final positive prohibited": (
            output_data[
                "method"
            ][
                "gazette_container_positive_prohibited"
            ]
            is True
        ),

        "scope extraction enabled": (
            output_data[
                "method"
            ][
                "scope_extraction_enabled"
            ]
            is True
        ),

        "scope not mandatory for verified positive": (
            output_data[
                "method"
            ][
                "scope_required_for_verified_positive"
            ]
            is False
        ),

        "all verification records have valid resolution": all(
            item.get(
                "resolution"
            )
            in VALID_RESOLUTIONS
            for item in verified_records
        ),

        "verification identity preserved": (
            len(
                verified_identity_keys
            )
            == len(
                verified_records
            )
        ),

        "verified documents unique": (
            duplicate_positive_urls
            == 0
        ),

        "all verified documents contain target": (
            target_missing_positive_leakage
            == 0
        ),

        "all verified documents have action context": (
            no_action_positive_leakage
            == 0
        ),

        "all verified documents have notice number": (
            no_notice_positive_leakage
            == 0
        ),

        "all verified documents have official context": (
            no_official_positive_leakage
            == 0
        ),

        "all verified documents have geographic context": (
            no_geography_positive_leakage
            == 0
        ),

        "administrative-duty positive leakage zero": (
            admin_duty_positive_leakage
            == 0
        ),

        "legal-reference positive leakage zero": (
            legal_reference_positive_leakage
            == 0
        ),

        "gazette-container positive leakage zero": (
            gazette_container_positive_leakage
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
        "Discovery-query leakage:",
        discovery_query_leakage,
    )

    print(
        "Administrative-duty positive leakage:",
        admin_duty_positive_leakage,
    )

    print(
        "Legal-reference positive leakage:",
        legal_reference_positive_leakage,
    )

    print(
        "Gazette-container positive leakage:",
        gazette_container_positive_leakage,
    )

    print(
        "Target-missing positive leakage:",
        target_missing_positive_leakage,
    )

    print(
        "No-action positive leakage:",
        no_action_positive_leakage,
    )

    print(
        "No-notice positive leakage:",
        no_notice_positive_leakage,
    )

    all_pass = all(
        validations.values()
    )

    print()

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
            "official notice source verification "
            "regression failed"
        )


if __name__ == "__main__":
    main()