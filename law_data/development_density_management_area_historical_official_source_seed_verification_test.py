# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-R
Development Density Management Area
Historical Official Source Seed Verification

목표
======================================================================
Q-stage에서 확보한 historical official source verification seed를
실제 HTTP 재조회하여 document-local evidence만으로 검증한다.

입력:
    law_data/output/
    development_density_management_area_
    historical_official_source_endpoint_discovery.json

출력:
    law_data/output/
    development_density_management_area_
    historical_official_source_seed_verification.json

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700


핵심 목적
======================================================================
Q-stage next_stage_verification_pool의 다음 class만 사용한다.

    HISTORICAL_TARGET_DIRECT_DETAIL_SEED
    HISTORICAL_NOTICE_DETAIL_SEED
    HISTORICAL_GAZETTE_ISSUE_SEED
    HISTORICAL_ATTACHMENT_DOCUMENT_SEED
    HISTORICAL_EXTENSIONLESS_DOWNLOAD_SEED
    HISTORICAL_ARCHIVE_RECORD_SEED
    HISTORICAL_NOTICE_REVERSE_LOOKUP_SEED


핵심 원칙
======================================================================
1. Q-stage에서 허용된 verification seed만 입력으로 사용한다.

2. Q-stage의 다음 evidence는 R-stage에 상속하지 않는다.

    - target_local_evidence
    - action_terms
    - official_terms
    - urban_terms
    - gazette_terms
    - archive_terms
    - notice_numbers
    - dates
    - local_container_text_preview
    - score
    - classification evidence

3. Q-stage에서 허용되는 것은 discovery identity metadata뿐이다.

    - source family
    - source name
    - source URL / entry URL
    - seed URL
    - label
    - query provenance
    - source priority

4. 실제 HTTP response의 원문 text에서만 target을 검증한다.

5. archive record/detail HTML은 그 자체가 verified positive가 될 수 있다.
   단 아래 요건을 document-local evidence로 만족해야 한다.

    - 개발밀도관리구역 exact phrase
    - 지정/변경/해제/결정 action context
    - 고시번호
    - official context
    - geographic context

6. 고시일은 추출하지만 verified positive 필수조건은 아니다.
   오래된 archive record에서 날짜 형식이 깨질 수 있기 때문이다.

7. scope는 추출하지만 verified positive 필수조건은 아니다.

8. archive record에 원문/첨부파일이 있는 경우 child attachment identity를
   별도 next-stage seed로 추출한다.

9. parent archive record evidence를 child attachment에 상속하지 않는다.

10. PDF / HWP / HWPX / HTML을 지원한다.

11. 확장자 없는 download endpoint는 Content-Type / magic bytes로 판별한다.

12. 행정업무표 / 사무전결표 / 업무분장표 false positive를 차단한다.

13. 법률·조례·법령상의 단순 용어 언급을 차단한다.

14. 검색/list 페이지는 verified positive로 승격하지 않는다.

15. login / permission / error HTML을 positive로 승격하지 않는다.

16. verified positive가 존재해도 runtime registration은 차단한다.

17. SITE TRUE/FALSE 자동판정은 계속 차단한다.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import subprocess
import tempfile
import zipfile

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
# OPTIONAL PDF PARSER
# ============================================================

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


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
        "historical_official_source_endpoint_discovery.json"
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
        "historical_official_source_seed_verification.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# Q-STAGE ALLOWED INPUT CLASSES
# ============================================================

CLASS_TARGET_DIRECT = (
    "HISTORICAL_TARGET_DIRECT_DETAIL_SEED"
)

CLASS_NOTICE_DETAIL = (
    "HISTORICAL_NOTICE_DETAIL_SEED"
)

CLASS_GAZETTE_ISSUE = (
    "HISTORICAL_GAZETTE_ISSUE_SEED"
)

CLASS_ATTACHMENT = (
    "HISTORICAL_ATTACHMENT_DOCUMENT_SEED"
)

CLASS_EXTENSIONLESS = (
    "HISTORICAL_EXTENSIONLESS_DOWNLOAD_SEED"
)

CLASS_ARCHIVE_RECORD = (
    "HISTORICAL_ARCHIVE_RECORD_SEED"
)

CLASS_NOTICE_REVERSE = (
    "HISTORICAL_NOTICE_REVERSE_LOOKUP_SEED"
)

ALLOWED_INPUT_CLASSES = {
    CLASS_TARGET_DIRECT,
    CLASS_NOTICE_DETAIL,
    CLASS_GAZETTE_ISSUE,
    CLASS_ATTACHMENT,
    CLASS_EXTENSIONLESS,
    CLASS_ARCHIVE_RECORD,
    CLASS_NOTICE_REVERSE,
}


# ============================================================
# R-STAGE RESOLUTIONS
# ============================================================

RESOLUTION_VERIFIED = (
    "HISTORICAL_OFFICIAL_SOURCE_VERIFIED_TARGET_DOCUMENT"
)

RESOLUTION_TARGET_MENTION = (
    "HISTORICAL_OFFICIAL_SOURCE_TARGET_MENTION_ONLY"
)

RESOLUTION_ARCHIVE_NO_TARGET = (
    "HISTORICAL_ARCHIVE_RECORD_NO_TARGET"
)

RESOLUTION_UNRELATED = (
    "HISTORICAL_OFFICIAL_SOURCE_UNRELATED_DOCUMENT"
)

RESOLUTION_ADMIN_DUTY = (
    "HISTORICAL_OFFICIAL_SOURCE_ADMINISTRATIVE_DUTY_REFERENCE"
)

RESOLUTION_LEGAL_REFERENCE = (
    "HISTORICAL_OFFICIAL_SOURCE_LEGAL_REFERENCE_ONLY"
)

RESOLUTION_SEARCH_LIST = (
    "HISTORICAL_OFFICIAL_SOURCE_SEARCH_LIST_PAGE"
)

RESOLUTION_PERMISSION_HTML = (
    "HISTORICAL_OFFICIAL_SOURCE_PERMISSION_OR_ERROR_HTML"
)

RESOLUTION_DOWNLOAD_FAILED = (
    "HISTORICAL_OFFICIAL_SOURCE_DOWNLOAD_FAILED"
)

RESOLUTION_PARSE_FAILED = (
    "HISTORICAL_OFFICIAL_SOURCE_PARSE_FAILED"
)

VALID_RESOLUTIONS = {
    RESOLUTION_VERIFIED,
    RESOLUTION_TARGET_MENTION,
    RESOLUTION_ARCHIVE_NO_TARGET,
    RESOLUTION_UNRELATED,
    RESOLUTION_ADMIN_DUTY,
    RESOLUTION_LEGAL_REFERENCE,
    RESOLUTION_SEARCH_LIST,
    RESOLUTION_PERMISSION_HTML,
    RESOLUTION_DOWNLOAD_FAILED,
    RESOLUTION_PARSE_FAILED,
}


# ============================================================
# CHILD ATTACHMENT OUTPUT CLASSES
# ============================================================

CHILD_CLASS_DIRECT_ATTACHMENT = (
    "HISTORICAL_VERIFIED_RECORD_ATTACHMENT_SEED"
)

CHILD_CLASS_EXTENSIONLESS_DOWNLOAD = (
    "HISTORICAL_VERIFIED_RECORD_EXTENSIONLESS_DOWNLOAD_SEED"
)

VALID_CHILD_CLASSES = {
    CHILD_CLASS_DIRECT_ATTACHMENT,
    CHILD_CLASS_EXTENSIONLESS_DOWNLOAD,
}


# ============================================================
# HTTP
# ============================================================

TIMEOUT = 30

MAX_RESPONSE_BYTES = (
    30
    * 1024
    * 1024
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# DOCUMENT TYPES
# ============================================================

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".hwp",
    ".hwpx",
}

DOWNLOAD_HINTS = [
    "download",
    "filedown",
    "filedownload",
    "file.do",
    "filedown.do",
    "download.do",
    "down.do",
    "getfile",
    "atchfile",
    "attach",
    "cmm/fms",
    "original",
    "원문",
    "다운로드",
]

ATTACHMENT_LABEL_HINTS = [
    "첨부",
    "첨부파일",
    "원문",
    "원문보기",
    "다운로드",
    "파일",
    ".pdf",
    ".hwp",
    ".hwpx",
]


# ============================================================
# ACTION
# ============================================================

ACTION_PATTERNS = {
    "DESIGNATION": [
        r"개발밀도관리구역.{0,200}?지정",
        r"개발밀도관리구역을.{0,200}?지정",
        r"개발밀도관리구역으로.{0,200}?지정",
        r"지정.{0,200}?개발밀도관리구역",
    ],

    "CHANGE": [
        r"개발밀도관리구역.{0,200}?변경",
        r"개발밀도관리구역.{0,200}?변경결정",
        r"개발밀도관리구역.{0,200}?결정\s*\(\s*변경\s*\)",
        r"변경.{0,200}?개발밀도관리구역",
    ],

    "RELEASE": [
        r"개발밀도관리구역.{0,200}?해제",
        r"개발밀도관리구역.{0,200}?해지",
        r"해제.{0,200}?개발밀도관리구역",
    ],

    "DECISION": [
        r"개발밀도관리구역.{0,200}?결정",
        r"결정.{0,200}?개발밀도관리구역",
    ],
}


# ============================================================
# OFFICIAL CONTEXT
# ============================================================

OFFICIAL_CONTEXT_PATTERNS = [
    r"고\s*시",
    r"고시문",
    r"고시번호",
    r"공\s*고",
    r"관\s*보",
    r"시\s*보",
    r"군\s*보",
    r"구\s*보",
    r"공\s*보",
    r"도시관리계획",
    r"도시계획",
    r"지형도면",
    r"국토의\s*계획\s*및\s*이용에\s*관한\s*법률",
    r"국토계획법",
    r"특별시장",
    r"광역시장",
    r"특별자치시장",
    r"특별자치도지사",
    r"도지사",
    r"시장",
    r"군수",
    r"구청장",
]


# ============================================================
# NOTICE NUMBER
# ============================================================

NOTICE_PATTERNS = [
    re.compile(
        r"(?P<notice>"
        r"(?:서울특별시|부산광역시|대구광역시|인천광역시|"
        r"광주광역시|대전광역시|울산광역시|세종특별자치시|"
        r"경기도|강원특별자치도|강원도|충청북도|충청남도|"
        r"전북특별자치도|전라북도|전라남도|경상북도|경상남도|"
        r"제주특별자치도|"
        r"[가-힣]{2,15}시|[가-힣]{2,15}군|[가-힣]{2,15}구)"
        r"\s*(?:고시|공고)\s*제?\s*\d{2,4}\s*[-–]\s*\d+\s*호)"
    ),

    re.compile(
        r"(?P<notice>"
        r"(?:고시|공고)\s*제?\s*\d{2,4}\s*[-–]\s*\d+\s*호)"
    ),

    re.compile(
        r"(?P<notice>"
        r"(?:건설교통부|국토해양부|국토교통부)"
        r"\s*고시\s*제?\s*\d{2,4}\s*[-–]\s*\d+\s*호)"
    ),
]


# ============================================================
# DATE
# ============================================================

DATE_PATTERN = re.compile(
    r"(?P<year>19\d{2}|20\d{2})"
    r"\s*[.\-/년]\s*"
    r"(?P<month>0?[1-9]|1[0-2])"
    r"\s*[.\-/월]\s*"
    r"(?P<day>0?[1-9]|[12]\d|3[01])"
    r"\s*일?"
)


# ============================================================
# REGION
# ============================================================

WIDE_AREA_REGIONS = [
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
# ADMINISTRATIVE DUTY
# ============================================================

ADMINISTRATIVE_DUTY_TERMS = [
    "단위사무명",
    "단 위 사 무 명",
    "전결권자",
    "전 결 권 자",
    "사무전결",
    "업무분장",
    "위임전결",
    "전결규정",
    "담당자",
    "팀장",
    "국장",
    "부시장",
    "관 · 과 · 단 장",
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
# SCOPE
# ============================================================

SCOPE_PATTERNS = [
    r"[가-힣]{1,20}(?:동|읍|면|리)\s+\d+(?:-\d+)?\s*번지",
    r"[가-힣]{1,20}(?:동|읍|면|리)\s+일원",
    r"\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:㎡|m²|m2)",
    r"면적\s*[:：]?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?",
    r"위치\s*[:：]",
    r"구역\s*면적",
    r"지정\s*면적",
]


# ============================================================
# SEARCH/LIST GUARD
# ============================================================

LIST_URL_HINTS = [
    "/list",
    "list.do",
    "search.do",
    "/search",
    "searchresult",
    "resultlist",
]

LIST_PAGE_TEXT_HINTS = [
    "검색결과",
    "검색 결과",
    "총 게시물",
    "전체 게시물",
    "페이지당",
    "검색어",
]


# ============================================================
# ERROR/PERMISSION HTML
# ============================================================

ERROR_HTML_TERMS = [
    "접근권한이 없습니다",
    "접근 권한이 없습니다",
    "permission-error",
    "권한이 없습니다",
    "페이지를 찾을 수 없습니다",
    "존재하지 않는 페이지",
    "오류가 발생",
    "잘못된 접근",
    "서비스 이용에 불편",
    "로그인이 필요",
    "로그인 후 이용",
    "forbidden",
    "access denied",
]


# ============================================================
# HTML
# ============================================================

ANCHOR_PATTERN = re.compile(
    r"<a\b(?P<attrs>[^>]*)>"
    r"(?P<body>.*?)"
    r"</a>",
    re.IGNORECASE
    | re.DOTALL,
)

HREF_PATTERN = re.compile(
    r"""href\s*=\s*["'](?P<href>[^"']+)["']""",
    re.IGNORECASE,
)

ONCLICK_PATTERN = re.compile(
    r"""onclick\s*=\s*["'](?P<onclick>[^"']+)["']""",
    re.IGNORECASE,
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

HTML_COMMENT_PATTERN = re.compile(
    r"<!--.*?-->",
    re.DOTALL,
)

ROW_PATTERN = re.compile(
    r"<tr\b[^>]*>.*?</tr>",
    re.IGNORECASE
    | re.DOTALL,
)

LI_PATTERN = re.compile(
    r"<li\b[^>]*>.*?</li>",
    re.IGNORECASE
    | re.DOTALL,
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
    "cachebuster",
    "cache_buster",
    "cb",
    "ts",
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

JSESSIONID_PATTERN = re.compile(
    r";jsessionid=[^/?]+",
    re.IGNORECASE,
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
    value: str,
    terms: Iterable[str],
) -> bool:

    lowered = normalize_space(
        value
    ).lower()

    return any(
        normalize_space(
            term
        ).lower()
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


# ============================================================
# URL
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

    if value.lower().startswith(
        "javascript:"
    ):
        return value

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

    path = JSESSIONID_PATTERN.sub(
        "",
        path,
    )

    path = re.sub(
        r"/{2,}",
        "/",
        path,
    )

    query_items = []
    seen_pairs = set()

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


def same_host(
    first: str,
    second: str,
) -> bool:

    return (
        hostname(
            first
        )
        ==
        hostname(
            second
        )
    )


# ============================================================
# Q-STAGE INPUT LOAD
# ============================================================

def load_verification_pool(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    raw_pool = data.get(
        "next_stage_verification_pool"
    )

    if not isinstance(
        raw_pool,
        list,
    ):

        raw_pool = []

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[str, str]
    ] = set()

    for item in raw_pool:

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

        if (
            classification
            not in ALLOWED_INPUT_CLASSES
        ):

            continue

        url = canonicalize_url(
            item.get(
                "url"
            )
            or ""
        )

        if (
            not url
            or not hostname(
                url
            )
        ):

            continue

        source_family = normalize_space(
            item.get(
                "source_family"
            )
        )

        key = (
            source_family,
            url,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        normalized = {
            # discovery identity only
            "source_family": source_family,

            "source_name": normalize_space(
                item.get(
                    "source_name"
                )
            ),

            "source_priority": int(
                item.get(
                    "source_priority"
                )
                or 0
            ),

            "input_classification": (
                classification
            ),

            "url": url,

            "label": normalize_space(
                item.get(
                    "label"
                )
            ),

            "entry_urls": unique_strings(
                item.get(
                    "entry_urls"
                )
                or [
                    item.get(
                        "entry_url"
                    )
                ]
            ),

            "request_urls": unique_strings(
                item.get(
                    "request_urls"
                )
                or [
                    item.get(
                        "request_url"
                    )
                ]
            ),

            "queries": unique_strings(
                item.get(
                    "queries"
                )
                or [
                    item.get(
                        "query"
                    )
                ]
            ),

            # Explicitly DO NOT inherit Q-stage evidence
            "q_stage_target_evidence_inherited": False,

            "q_stage_action_evidence_inherited": False,

            "q_stage_notice_number_inherited": False,

            "q_stage_date_inherited": False,

            "q_stage_local_container_evidence_inherited": False,

            "q_stage_score_inherited_for_verification": False,
        }

        result.append(
            normalized
        )

    result.sort(
        key=lambda item: (
            -int(
                item.get(
                    "source_priority"
                )
                or 0
            ),
            normalize_space(
                item.get(
                    "source_family"
                )
            ),
            normalize_space(
                item.get(
                    "url"
                )
            ),
        )
    )

    return result


# ============================================================
# HTTP
# ============================================================

def fetch_bytes(
    session: requests.Session,
    url: str,
    *,
    referer: str = "",
) -> Dict[str, Any]:

    result = {
        "requested_url": url,
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "content_disposition": "",
        "data": b"",
        "response_bytes": 0,
        "sha256": "",
        "error": "",
    }

    headers: Dict[str, str] = {}

    if referer:
        headers[
            "Referer"
        ] = referer

    try:

        with session.get(
            url,
            headers=headers,
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
                "data"
            ] = data

            result[
                "response_bytes"
            ] = len(
                data
            )

            result[
                "sha256"
            ] = sha256_bytes(
                data
            )

    except Exception as exc:

        result[
            "error"
        ] = repr(
            exc
        )

    return result


# ============================================================
# CONTENT DISPOSITION
# ============================================================

def extract_filename_from_content_disposition(
    value: str,
) -> str:

    text = normalize_space(
        value
    )

    if not text:
        return ""

    patterns = [
        re.compile(
            r"""filename\*\s*=\s*UTF-8''([^;]+)""",
            re.IGNORECASE,
        ),

        re.compile(
            r'''filename\s*=\s*"([^"]+)"''',
            re.IGNORECASE,
        ),

        re.compile(
            r"""filename\s*=\s*'([^']+)'""",
            re.IGNORECASE,
        ),

        re.compile(
            r"""filename\s*=\s*([^;]+)""",
            re.IGNORECASE,
        ),
    ]

    for pattern in patterns:

        match = pattern.search(
            text
        )

        if not match:
            continue

        filename = normalize_space(
            match.group(1)
        )

        if filename:
            return filename

    return ""


# ============================================================
# DOCUMENT TYPE
# ============================================================

def detect_document_type(
    *,
    url: str,
    content_type: str,
    content_disposition: str,
    data: bytes,
) -> str:

    filename = (
        extract_filename_from_content_disposition(
            content_disposition
        )
    )

    path = (
        urlparse(
            url
        ).path
        or ""
    ).lower()

    filename_lower = (
        filename.lower()
    )

    content_type_lower = (
        content_type.lower()
    )

    for source in [
        path,
        filename_lower,
    ]:

        if source.endswith(
            ".pdf"
        ):
            return "PDF"

        if source.endswith(
            ".hwpx"
        ):
            return "HWPX"

        if source.endswith(
            ".hwp"
        ):
            return "HWP"

        if source.endswith(
            ".html"
        ) or source.endswith(
            ".htm"
        ):
            return "HTML"

    if (
        "application/pdf"
        in content_type_lower
    ):
        return "PDF"

    if (
        "application/haansofthwp"
        in content_type_lower
        or "application/x-hwp"
        in content_type_lower
    ):
        return "HWP"

    if (
        "application/vnd.hancom.hwpx"
        in content_type_lower
    ):
        return "HWPX"

    if (
        "text/html"
        in content_type_lower
        or "application/xhtml"
        in content_type_lower
    ):
        return "HTML"

    if data.startswith(
        b"%PDF"
    ):
        return "PDF"

    if data.startswith(
        b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
    ):
        return "HWP"

    if data.startswith(
        b"PK\x03\x04"
    ):

        try:

            with zipfile.ZipFile(
                io.BytesIO(
                    data
                )
            ) as archive:

                names = {
                    name.lower()
                    for name in archive.namelist()
                }

                if any(
                    name.startswith(
                        "contents/"
                    )
                    for name in names
                ):
                    return "HWPX"

        except Exception:
            pass

    prefix = (
        data[
            :4096
        ]
        .lstrip()
        .lower()
    )

    if (
        prefix.startswith(
            b"<!doctype html"
        )
        or prefix.startswith(
            b"<html"
        )
    ):
        return "HTML"

    return "UNKNOWN"


# ============================================================
# HTML DECODE
# ============================================================

def extract_charset_from_content_type(
    content_type: str,
) -> str:

    match = re.search(
        r"""charset\s*=\s*["']?([^;"'\s]+)""",
        content_type,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    return normalize_space(
        match.group(1)
    )


def decode_html_bytes(
    data: bytes,
    *,
    content_type: str = "",
) -> Tuple[str, str]:

    encodings = unique_strings(
        [
            extract_charset_from_content_type(
                content_type
            ),
            "utf-8",
            "cp949",
            "euc-kr",
        ]
    )

    for encoding in encodings:

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


# ============================================================
# PDF
# ============================================================

def parse_pdf_text(
    data: bytes,
) -> Tuple[
    str,
    str,
    str,
]:

    if PdfReader is None:

        return (
            "",
            "",
            "pypdf is not available",
        )

    try:

        reader = PdfReader(
            io.BytesIO(
                data
            )
        )

        pages: List[str] = []

        for page in reader.pages:

            text = (
                page.extract_text()
                or ""
            )

            if text:

                pages.append(
                    text
                )

        return (
            normalize_space(
                "\n".join(
                    pages
                )
            ),
            "pypdf",
            "",
        )

    except Exception as exc:

        return (
            "",
            "pypdf",
            repr(
                exc
            ),
        )


# ============================================================
# HWPX
# ============================================================

def parse_hwpx_text(
    data: bytes,
) -> Tuple[
    str,
    str,
    str,
]:

    try:

        texts: List[str] = []

        with zipfile.ZipFile(
            io.BytesIO(
                data
            )
        ) as archive:

            names = sorted(
                archive.namelist()
            )

            target_names = [
                name
                for name in names
                if (
                    name.lower().startswith(
                        "contents/"
                    )
                    and name.lower().endswith(
                        ".xml"
                    )
                )
            ]

            if not target_names:

                target_names = [
                    name
                    for name in names
                    if name.lower().endswith(
                        ".xml"
                    )
                ]

            for name in target_names:

                try:

                    raw = archive.read(
                        name
                    )

                except Exception:
                    continue

                xml_text = raw.decode(
                    "utf-8",
                    errors="replace",
                )

                plain = re.sub(
                    r"<[^>]+>",
                    " ",
                    xml_text,
                )

                plain = html.unescape(
                    plain
                )

                plain = normalize_space(
                    plain
                )

                if plain:

                    texts.append(
                        plain
                    )

        return (
            normalize_space(
                "\n".join(
                    texts
                )
            ),
            "hwpx-zip-xml",
            "",
        )

    except Exception as exc:

        return (
            "",
            "hwpx-zip-xml",
            repr(
                exc
            ),
        )


# ============================================================
# HWP
# ============================================================

def parse_hwp_text(
    data: bytes,
) -> Tuple[
    str,
    str,
    str,
]:

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

        process = subprocess.run(
            [
                "hwp5txt",
                str(
                    temp_path
                ),
            ],
            capture_output=True,
            timeout=30,
        )

        if process.returncode != 0:

            stderr = process.stderr.decode(
                "utf-8",
                errors="replace",
            )

            return (
                "",
                "hwp5txt",
                normalize_space(
                    stderr
                ),
            )

        output = process.stdout.decode(
            "utf-8",
            errors="replace",
        )

        return (
            normalize_space(
                output
            ),
            "hwp5txt",
            "",
        )

    except FileNotFoundError:

        return (
            "",
            "hwp5txt",
            "hwp5txt executable not found",
        )

    except Exception as exc:

        return (
            "",
            "hwp5txt",
            repr(
                exc
            ),
        )

    finally:

        if (
            temp_path
            and temp_path.exists()
        ):

            try:
                temp_path.unlink()
            except Exception:
                pass


# ============================================================
# DOCUMENT PARSER
# ============================================================

def parse_document(
    *,
    document_type: str,
    data: bytes,
    content_type: str = "",
) -> Dict[str, Any]:

    raw_html = ""
    html_encoding = ""

    if document_type == "PDF":

        (
            text,
            parser,
            error,
        ) = parse_pdf_text(
            data
        )

    elif document_type == "HWPX":

        (
            text,
            parser,
            error,
        ) = parse_hwpx_text(
            data
        )

    elif document_type == "HWP":

        (
            text,
            parser,
            error,
        ) = parse_hwp_text(
            data
        )

    elif document_type == "HTML":

        (
            raw_html,
            html_encoding,
        ) = decode_html_bytes(
            data,
            content_type=content_type,
        )

        text = strip_html(
            raw_html
        )

        parser = (
            f"html:{html_encoding}"
        )

        error = ""

    else:

        text = ""
        parser = ""
        error = (
            "unsupported or unknown document type"
        )

    return {
        "text": normalize_space(
            text
        ),
        "parser": parser,
        "error": error,
        "raw_html": raw_html,
        "html_encoding": html_encoding,
    }


# ============================================================
# TARGET CONTEXT
# ============================================================

def extract_target_contexts(
    text: str,
    radius: int = 1400,
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
            index
            + len(
                TARGET_NAME
            )
            + radius,
        )

        contexts.append(
            text[
                left:right
            ]
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
        radius=1600,
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
# NOTICE
# ============================================================

def extract_notice_numbers(
    text: str,
) -> List[str]:

    result: List[str] = []

    contexts = extract_target_contexts(
        text,
        radius=2500,
    )

    corpus = (
        "\n".join(
            contexts
        )
        if contexts
        else text
    )

    for pattern in NOTICE_PATTERNS:

        for match in pattern.finditer(
            corpus
        ):

            result.append(
                normalize_space(
                    match.groupdict().get(
                        "notice"
                    )
                    or match.group(0)
                )
            )

    return unique_strings(
        result
    )


# ============================================================
# DATE
# ============================================================

def extract_dates(
    text: str,
) -> List[str]:

    result: List[str] = []

    contexts = extract_target_contexts(
        text,
        radius=2500,
    )

    corpus = (
        "\n".join(
            contexts
        )
        if contexts
        else text
    )

    for match in DATE_PATTERN.finditer(
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

        result.append(
            f"{year:04d}-{month:02d}-{day:02d}"
        )

    return unique_strings(
        result
    )


# ============================================================
# REGION
# ============================================================

def extract_regions(
    text: str,
) -> List[str]:

    contexts = extract_target_contexts(
        text,
        radius=3500,
    )

    corpus = (
        "\n".join(
            contexts
        )
        if contexts
        else text
    )

    regions: List[str] = []

    for region in WIDE_AREA_REGIONS:

        if region in corpus:

            regions.append(
                region
            )

    local_patterns = [
        r"([가-힣]{2,15}시)\s*(?:고시|공고|시장|일원|도시)",
        r"([가-힣]{2,15}군)\s*(?:고시|공고|군수|일원|도시)",
        r"([가-힣]{2,15}구)\s*(?:고시|공고|구청장|일원|도시)",
        r"([가-힣]{2,15}(?:시|군|구))\s+[가-힣]{1,15}(?:동|읍|면)",
    ]

    for pattern in local_patterns:

        for match in re.finditer(
            pattern,
            corpus,
        ):

            regions.append(
                match.group(1)
            )

    return unique_strings(
        regions
    )


# ============================================================
# OFFICIAL CONTEXT
# ============================================================

def extract_official_context(
    text: str,
) -> List[str]:

    contexts = extract_target_contexts(
        text,
        radius=2200,
    )

    corpus = "\n".join(
        contexts
    )

    evidence: List[str] = []

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
# ADMIN DUTY
# ============================================================

def detect_administrative_duty_reference(
    text: str,
) -> Tuple[
    bool,
    List[str],
    Dict[str, Any],
]:

    normalized = normalize_space(
        text
    )

    evidence: List[str] = []

    for term in ADMINISTRATIVE_DUTY_TERMS:

        if term in normalized:

            evidence.append(
                term
            )

    draft_matches = re.findall(
        r"기안\s*[○●◎]?",
        normalized,
    )

    draft_marker_count = len(
        draft_matches
    )

    target_draft_match = re.search(
        r"개발밀도관리구역.{0,120}?기안\s*[○●◎]?",
        normalized,
        flags=re.DOTALL,
    )

    target_draft_evidence = ""

    if target_draft_match:

        target_draft_evidence = normalize_space(
            target_draft_match.group(0)
        )

        evidence.append(
            target_draft_evidence
        )

    strong_structure = (
        (
            "단위사무명"
            in normalized
            or "단 위 사 무 명"
            in normalized
        )
        and (
            "전결권자"
            in normalized
            or "전 결 권 자"
            in normalized
        )
    )

    repeated_draft = (
        draft_marker_count
        >= 5
    )

    result = (
        strong_structure
        or (
            target_draft_match
            is not None
            and repeated_draft
        )
        or (
            len(
                evidence
            )
            >= 4
            and repeated_draft
        )
    )

    diagnostics = {
        "strong_structure": strong_structure,
        "draft_marker_count": (
            draft_marker_count
        ),
        "repeated_draft_markers": (
            repeated_draft
        ),
        "target_is_draft_duty": (
            target_draft_match
            is not None
        ),
        "target_draft_evidence": (
            target_draft_evidence
        ),
    }

    return (
        result,
        unique_strings(
            evidence
        ),
        diagnostics,
    )


# ============================================================
# LEGAL REFERENCE
# ============================================================

def detect_legal_reference_only(
    text: str,
    *,
    action_types: List[str],
    notice_numbers: List[str],
    official_context: List[str],
) -> Tuple[
    bool,
    List[str],
]:

    contexts = extract_target_contexts(
        text,
        radius=1400,
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

    substantial_official_evidence = (
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

    result = (
        bool(
            evidence
        )
        and not substantial_official_evidence
    )

    return (
        result,
        unique_strings(
            evidence
        ),
    )


# ============================================================
# SCOPE
# ============================================================

def extract_scope_evidence(
    text: str,
) -> List[str]:

    contexts = extract_target_contexts(
        text,
        radius=4000,
    )

    corpus = "\n".join(
        contexts
    )

    evidence: List[str] = []

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
# SEARCH LIST / ERROR HTML
# ============================================================

def looks_search_list_page(
    url: str,
    text: str,
) -> bool:

    url_lower = (
        url.lower()
    )

    path_hit = contains_any(
        url_lower,
        LIST_URL_HINTS,
    )

    text_hits = sum(
        1
        for term in LIST_PAGE_TEXT_HINTS
        if term in text
    )

    return (
        path_hit
        and text_hits >= 1
    )


def detect_permission_or_error_html(
    text: str,
) -> Tuple[
    bool,
    List[str],
]:

    evidence = [
        term
        for term in ERROR_HTML_TERMS
        if term.lower()
        in text.lower()
    ]

    return (
        bool(
            evidence
        ),
        unique_strings(
            evidence
        ),
    )


# ============================================================
# JS URL
# ============================================================

def extract_js_url(
    onclick: str,
) -> str:

    value = normalize_space(
        onclick
    )

    if not value:
        return ""

    patterns = [
        r"""location\.href\s*=\s*['"]([^'"]+)['"]""",
        r"""window\.open\s*\(\s*['"]([^'"]+)['"]""",
        r"""location\s*=\s*['"]([^'"]+)['"]""",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            value,
            flags=re.IGNORECASE,
        )

        if match:

            return normalize_space(
                match.group(1)
            )

    return ""


# ============================================================
# LOCAL CONTAINER
# ============================================================

def find_local_container(
    raw_html: str,
    anchor_start: int,
    anchor_end: int,
) -> str:

    for match in ROW_PATTERN.finditer(
        raw_html
    ):

        if (
            match.start()
            <= anchor_start
            and match.end()
            >= anchor_end
        ):

            return match.group(0)

    for match in LI_PATTERN.finditer(
        raw_html
    ):

        if (
            match.start()
            <= anchor_start
            and match.end()
            >= anchor_end
        ):

            return match.group(0)

    left = max(
        0,
        anchor_start - 1000,
    )

    right = min(
        len(
            raw_html
        ),
        anchor_end + 1000,
    )

    return raw_html[
        left:right
    ]


# ============================================================
# CHILD ATTACHMENT DISCOVERY
# ============================================================

def is_direct_document_url(
    url: str,
) -> bool:

    try:

        path = (
            urlparse(
                url
            ).path
            or ""
        ).lower()

    except Exception:

        return False

    return any(
        path.endswith(
            extension
        )
        for extension in DOCUMENT_EXTENSIONS
    )


def is_extensionless_download_url(
    url: str,
) -> bool:

    if is_direct_document_url(
        url
    ):

        return False

    return contains_any(
        url,
        DOWNLOAD_HINTS,
    )


def extract_child_attachment_seeds(
    *,
    parent_url: str,
    raw_html: str,
) -> List[Dict[str, Any]]:

    """
    Historical archive/detail HTML에서 child attachment identity를 추출한다.

    중요 원칙
    ============================================================
    - attachment 존재 자체는 relevance evidence가 아니다.
    - .pdf/.hwp/.hwpx 확장자만으로 next-stage 승격하지 않는다.
    - "첨부", "다운로드", "원문" label만으로 승격하지 않는다.
    - parent document의 target/action/notice/date/scope evidence를 상속하지 않는다.
    - 오직 anchor label + anchor local container에서 확인되는
      child-local relevance evidence만 사용한다.

    다음 중 하나를 만족해야 next-stage child seed가 된다.

    1. 개발밀도관리구역 exact phrase

    2. 고시번호 + 도시계획/도시관리계획/지형도면 등
       target-compatible official context

    3. 개발밀도/밀도관리 관련 target-family phrase +
       지정/변경/해제/결정 + official context

    단순 일반 첨부파일은 발견은 가능하지만 verification pool에는 넣지 않는다.
    """

    results: List[
        Dict[str, Any]
    ] = []

    seen: Set[str] = set()

    parent_host = hostname(
        parent_url
    )

    target_family_terms = [
        TARGET_NAME,
        "개발밀도",
        "밀도관리구역",
    ]

    target_compatible_urban_terms = [
        "도시관리계획",
        "도시계획",
        "지형도면",
        "용도지역",
        "용도지구",
        "용도구역",
        "기반시설부담구역",
    ]

    target_compatible_official_terms = [
        "고시",
        "고시문",
        "공고",
        "관보",
        "시보",
        "군보",
        "구보",
        "공보",
    ]

    target_compatible_action_terms = [
        "지정",
        "변경",
        "해제",
        "결정",
    ]

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

        href = (
            normalize_space(
                href_match.group(
                    "href"
                )
            )
            if href_match
            else ""
        )

        onclick_match = ONCLICK_PATTERN.search(
            attrs
        )

        onclick = (
            normalize_space(
                onclick_match.group(
                    "onclick"
                )
            )
            if onclick_match
            else ""
        )

        # ----------------------------------------------------
        # javascript download URL recovery
        # ----------------------------------------------------

        if (
            not href
            or href == "#"
            or href.lower().startswith(
                "javascript:"
            )
        ):

            js_url = extract_js_url(
                onclick
            )

            if js_url:

                href = js_url

        if not href:

            continue

        if href.lower().startswith(
            (
                "mailto:",
                "tel:",
            )
        ):

            continue

        url = canonicalize_url(
            urljoin(
                parent_url,
                html.unescape(
                    href
                ),
            )
        )

        if (
            not url
            or not hostname(
                url
            )
        ):

            continue

        # ----------------------------------------------------
        # external attachment 기본 차단
        # ----------------------------------------------------

        if (
            hostname(
                url
            )
            != parent_host
        ):

            continue

        direct_document = (
            is_direct_document_url(
                url
            )
        )

        extensionless = (
            is_extensionless_download_url(
                url
            )
        )

        if (
            not direct_document
            and not extensionless
        ):

            continue

        # ----------------------------------------------------
        # anchor-local container
        # ----------------------------------------------------

        local_container = strip_html(
            find_local_container(
                raw_html,
                match.start(),
                match.end(),
            )
        )

        local_evidence = normalize_space(
            f"{label} {local_container}"
        )

        # ----------------------------------------------------
        # child-local semantic evidence
        # ----------------------------------------------------

        exact_target_local = (
            TARGET_NAME
            in local_evidence
        )

        target_family_local = any(
            term in local_evidence
            for term in target_family_terms
        )

        urban_local_terms = [
            term
            for term
            in target_compatible_urban_terms
            if term in local_evidence
        ]

        official_local_terms = [
            term
            for term
            in target_compatible_official_terms
            if term in local_evidence
        ]

        action_local_terms = [
            term
            for term
            in target_compatible_action_terms
            if term in local_evidence
        ]

        notice_numbers = (
            extract_notice_numbers(
                local_evidence
            )
        )

        # ----------------------------------------------------
        # Attachment label은 identity evidence일 뿐,
        # relevance evidence로 사용하지 않는다.
        # ----------------------------------------------------

        attachment_identity_hint = (
            contains_any(
                label,
                ATTACHMENT_LABEL_HINTS,
            )
            or contains_any(
                local_container,
                ATTACHMENT_LABEL_HINTS,
            )
        )

        # ----------------------------------------------------
        # Strong relevance conditions
        # ----------------------------------------------------

        relevance_reason: List[str] = []

        if exact_target_local:

            relevance_reason.append(
                "EXACT_TARGET_IN_CHILD_LOCAL_EVIDENCE"
            )

        if (
            notice_numbers
            and urban_local_terms
            and official_local_terms
        ):

            relevance_reason.append(
                "NOTICE_URBAN_OFFICIAL_CHILD_LOCAL_EVIDENCE"
            )

        if (
            target_family_local
            and action_local_terms
            and official_local_terms
        ):

            relevance_reason.append(
                "TARGET_FAMILY_ACTION_OFFICIAL_CHILD_LOCAL_EVIDENCE"
            )

        child_relevant = bool(
            relevance_reason
        )

        # ----------------------------------------------------
        # 중요:
        # 파일/첨부 identity만 존재하고 semantic relevance가 없으면
        # next-stage verification pool로 승격하지 않는다.
        # ----------------------------------------------------

        if not child_relevant:

            continue

        if url in seen:

            continue

        seen.add(
            url
        )

        if direct_document:

            classification = (
                CHILD_CLASS_DIRECT_ATTACHMENT
            )

        else:

            classification = (
                CHILD_CLASS_EXTENSIONLESS_DOWNLOAD
            )

        results.append(
            {
                "parent_url": (
                    canonicalize_url(
                        parent_url
                    )
                ),

                "label": label,

                "url": url,

                "classification": (
                    classification
                ),

                "attachment_identity_hint": (
                    attachment_identity_hint
                ),

                "exact_target_local_evidence": (
                    exact_target_local
                ),

                "target_family_local_evidence": (
                    target_family_local
                ),

                "notice_numbers_local": (
                    notice_numbers
                ),

                "urban_terms_local": (
                    unique_strings(
                        urban_local_terms
                    )
                ),

                "official_terms_local": (
                    unique_strings(
                        official_local_terms
                    )
                ),

                "action_terms_local": (
                    unique_strings(
                        action_local_terms
                    )
                ),

                "relevance_reasons": (
                    unique_strings(
                        relevance_reason
                    )
                ),

                "local_container_text_preview": (
                    local_container[
                        :1200
                    ]
                ),

                # --------------------------------------------
                # Parent evidence inheritance prohibition
                # --------------------------------------------

                "parent_target_evidence_inherited": False,

                "parent_action_evidence_inherited": False,

                "parent_notice_number_inherited": False,

                "parent_date_inherited": False,

                "parent_scope_inherited": False,

                "verified_positive": False,

                "runtime_registration_allowed": False,

                "site_positive_allowed": False,
            }
        )

    return results


# ============================================================
# DOCUMENT VERIFY
# ============================================================

def verify_document(
    *,
    seed_index: int,
    seed: Dict[str, Any],
    fetch_result: Dict[str, Any],
    document_type: str,
    parsed: Dict[str, Any],
) -> Dict[str, Any]:

    text = normalize_space(
        parsed.get(
            "text"
        )
    )

    url = canonicalize_url(
        fetch_result.get(
            "final_url"
        )
        or seed.get(
            "url"
        )
        or ""
    )

    target_found = (
        TARGET_NAME
        in text
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
        text
    )

    official_context_evidence = (
        extract_official_context(
            text
        )
    )

    (
        admin_duty,
        admin_evidence,
        admin_diagnostics,
    ) = detect_administrative_duty_reference(
        text
    )

    (
        legal_reference_only,
        legal_reference_evidence,
    ) = detect_legal_reference_only(
        text,
        action_types=action_types,
        notice_numbers=notice_numbers,
        official_context=(
            official_context_evidence
        ),
    )

    scope_evidence = extract_scope_evidence(
        text
    )

    search_list_page = (
        document_type == "HTML"
        and looks_search_list_page(
            url,
            text,
        )
    )

    (
        permission_or_error_html,
        permission_error_evidence,
    ) = detect_permission_or_error_html(
        text
    )

    if document_type != "HTML":

        permission_or_error_html = False
        permission_error_evidence = []

    has_action = bool(
        action_types
    )

    has_notice = bool(
        notice_numbers
    )

    has_official = bool(
        official_context_evidence
    )

    has_geographic = bool(
        regions
    )

    has_scope = bool(
        scope_evidence
    )

    verified_positive = (
        target_found
        and has_action
        and has_notice
        and has_official
        and has_geographic
        and not admin_duty
        and not legal_reference_only
        and not search_list_page
        and not permission_or_error_html
    )

    reasons: List[str] = []

    if not target_found:

        reasons.append(
            "TARGET_NOT_IN_DOCUMENT"
        )

    if not has_action:

        reasons.append(
            "NO_ACTION_CONTEXT"
        )

    if not has_notice:

        reasons.append(
            "NO_NOTICE_NUMBER"
        )

    if not has_official:

        reasons.append(
            "NO_OFFICIAL_CONTEXT"
        )

    if not has_geographic:

        reasons.append(
            "NO_GEOGRAPHIC_CONTEXT"
        )

    if admin_duty:

        reasons.append(
            "ADMINISTRATIVE_DUTY_REFERENCE"
        )

    if legal_reference_only:

        reasons.append(
            "LEGAL_REFERENCE_ONLY"
        )

    if search_list_page:

        reasons.append(
            "SEARCH_LIST_PAGE"
        )

    if permission_or_error_html:

        reasons.append(
            "PERMISSION_OR_ERROR_HTML"
        )

    if not has_scope:

        reasons.append(
            "SCOPE_NOT_EXTRACTED"
        )

    if verified_positive:

        resolution = (
            RESOLUTION_VERIFIED
        )

    elif permission_or_error_html:

        resolution = (
            RESOLUTION_PERMISSION_HTML
        )

    elif search_list_page:

        resolution = (
            RESOLUTION_SEARCH_LIST
        )

    elif admin_duty:

        resolution = (
            RESOLUTION_ADMIN_DUTY
        )

    elif legal_reference_only:

        resolution = (
            RESOLUTION_LEGAL_REFERENCE
        )

    elif target_found:

        resolution = (
            RESOLUTION_TARGET_MENTION
        )

    elif (
        seed.get(
            "input_classification"
        )
        == CLASS_ARCHIVE_RECORD
    ):

        resolution = (
            RESOLUTION_ARCHIVE_NO_TARGET
        )

    else:

        resolution = (
            RESOLUTION_UNRELATED
        )

    target_contexts = (
        extract_target_contexts(
            text,
            radius=1400,
        )
    )

    return {
        "seed_index": seed_index,

        "source_family": normalize_space(
            seed.get(
                "source_family"
            )
        ),

        "source_name": normalize_space(
            seed.get(
                "source_name"
            )
        ),

        "source_priority": int(
            seed.get(
                "source_priority"
            )
            or 0
        ),

        "input_classification": normalize_space(
            seed.get(
                "input_classification"
            )
        ),

        "seed_url": canonicalize_url(
            seed.get(
                "url"
            )
            or ""
        ),

        "final_url": url,

        "label": normalize_space(
            seed.get(
                "label"
            )
        ),

        "http_status": fetch_result.get(
            "http_status"
        ),

        "content_type": fetch_result.get(
            "content_type"
        ),

        "content_disposition": (
            fetch_result.get(
                "content_disposition"
            )
        ),

        "response_bytes": fetch_result.get(
            "response_bytes"
        ),

        "response_sha256": fetch_result.get(
            "sha256"
        ),

        "document_type": document_type,

        "parser": parsed.get(
            "parser"
        ),

        "parse_error": parsed.get(
            "error"
        ),

        "text_length": len(
            text
        ),

        "target_in_document": (
            target_found
        ),

        "target_contexts": (
            target_contexts[
                :20
            ]
        ),

        "action_context": has_action,

        "action_types": action_types,

        "action_evidence": (
            action_evidence
        ),

        "notice_numbers": (
            notice_numbers
        ),

        "dates": dates,

        "administrative_regions": (
            regions
        ),

        "official_context": has_official,

        "official_context_evidence": (
            official_context_evidence
        ),

        "administrative_duty_reference": (
            admin_duty
        ),

        "administrative_duty_evidence": (
            admin_evidence
        ),

        "administrative_duty_diagnostics": (
            admin_diagnostics
        ),

        "legal_reference_only": (
            legal_reference_only
        ),

        "legal_reference_evidence": (
            legal_reference_evidence
        ),

        "search_list_page": (
            search_list_page
        ),

        "permission_or_error_html": (
            permission_or_error_html
        ),

        "permission_or_error_evidence": (
            permission_error_evidence
        ),

        "scope_extraction_status": (
            "SCOPE_EVIDENCE_EXTRACTED"
            if has_scope
            else "SCOPE_NOT_EXTRACTED"
        ),

        "scope_evidence": (
            scope_evidence
        ),

        "verified_positive": (
            verified_positive
        ),

        "resolution": resolution,

        "reasons": reasons,

        # Explicit Q-stage inheritance diagnostics
        "q_stage_target_evidence_inherited": False,

        "q_stage_action_evidence_inherited": False,

        "q_stage_notice_number_inherited": False,

        "q_stage_date_inherited": False,

        "q_stage_local_container_evidence_inherited": False,

        "q_stage_score_inherited_for_verification": False,

        "runtime_registration_allowed": False,

        "site_positive_allowed": False,
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
        "HISTORICAL OFFICIAL SOURCE SEED VERIFICATION"
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
            "Q-stage output not found: "
            f"{INPUT_PATH}"
        )

    input_data = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        input_data,
        dict,
    ):

        raise TypeError(
            "Q-stage output must be JSON object."
        )

    verification_pool = (
        load_verification_pool(
            input_data
        )
    )

    print(
        "Verification seed count:",
        len(
            verification_pool
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
                "application/pdf,"
                "application/octet-stream,"
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
    download_failed_count = 0
    parse_failed_count = 0

    child_attachment_discovered_count = 0

    verification_records: List[
        Dict[str, Any]
    ] = []

    child_attachment_records: List[
        Dict[str, Any]
    ] = []

    # ========================================================
    # VERIFICATION LOOP
    # ========================================================

    for seed_index, seed in enumerate(
        verification_pool,
        start=1,
    ):

        seed_url = canonicalize_url(
            seed.get(
                "url"
            )
            or ""
        )

        input_classification = (
            normalize_space(
                seed.get(
                    "input_classification"
                )
            )
        )

        print(
            "-" * 60
        )

        print(
            f"DOCUMENT {seed_index}"
        )

        print(
            "Source family:",
            seed.get(
                "source_family"
            ),
        )

        print(
            "Input class:",
            input_classification,
        )

        print(
            "URL:",
            seed_url,
        )

        request_count += 1

        referer = ""

        entry_urls = seed.get(
            "entry_urls"
        )

        if (
            isinstance(
                entry_urls,
                list,
            )
            and entry_urls
        ):

            referer = normalize_space(
                entry_urls[
                    0
                ]
            )

        fetch_result = fetch_bytes(
            session,
            seed_url,
            referer=referer,
        )

        if (
            fetch_result.get(
                "http_status"
            )
            == 200
        ):

            http_success_count += 1

        if fetch_result.get(
            "error"
        ):

            download_failed_count += 1

            record = {
                "seed_index": seed_index,

                "source_family": seed.get(
                    "source_family"
                ),

                "source_name": seed.get(
                    "source_name"
                ),

                "input_classification": (
                    input_classification
                ),

                "seed_url": seed_url,

                "final_url": (
                    fetch_result.get(
                        "final_url"
                    )
                    or seed_url
                ),

                "http_status": fetch_result.get(
                    "http_status"
                ),

                "verified_positive": False,

                "resolution": (
                    RESOLUTION_DOWNLOAD_FAILED
                ),

                "reasons": [
                    "DOWNLOAD_FAILED"
                ],

                "error": fetch_result.get(
                    "error"
                ),

                "q_stage_target_evidence_inherited": False,

                "q_stage_action_evidence_inherited": False,

                "q_stage_notice_number_inherited": False,

                "q_stage_date_inherited": False,

                "q_stage_local_container_evidence_inherited": False,

                "q_stage_score_inherited_for_verification": False,

                "runtime_registration_allowed": False,

                "site_positive_allowed": False,
            }

            verification_records.append(
                record
            )

            print(
                "Resolution:",
                RESOLUTION_DOWNLOAD_FAILED,
            )

            print(
                "Error:",
                fetch_result.get(
                    "error"
                ),
            )

            continue

        document_type = detect_document_type(
            url=(
                fetch_result.get(
                    "final_url"
                )
                or seed_url
            ),
            content_type=(
                fetch_result.get(
                    "content_type"
                )
                or ""
            ),
            content_disposition=(
                fetch_result.get(
                    "content_disposition"
                )
                or ""
            ),
            data=(
                fetch_result.get(
                    "data"
                )
                or b""
            ),
        )

        parsed = parse_document(
            document_type=document_type,
            data=(
                fetch_result.get(
                    "data"
                )
                or b""
            ),
            content_type=(
                fetch_result.get(
                    "content_type"
                )
                or ""
            ),
        )

        if (
            parsed.get(
                "error"
            )
            and not parsed.get(
                "text"
            )
        ):

            parse_failed_count += 1

            record = {
                "seed_index": seed_index,

                "source_family": seed.get(
                    "source_family"
                ),

                "source_name": seed.get(
                    "source_name"
                ),

                "input_classification": (
                    input_classification
                ),

                "seed_url": seed_url,

                "final_url": (
                    fetch_result.get(
                        "final_url"
                    )
                    or seed_url
                ),

                "http_status": fetch_result.get(
                    "http_status"
                ),

                "content_type": fetch_result.get(
                    "content_type"
                ),

                "content_disposition": (
                    fetch_result.get(
                        "content_disposition"
                    )
                ),

                "response_bytes": (
                    fetch_result.get(
                        "response_bytes"
                    )
                ),

                "response_sha256": (
                    fetch_result.get(
                        "sha256"
                    )
                ),

                "document_type": document_type,

                "parser": parsed.get(
                    "parser"
                ),

                "parse_error": parsed.get(
                    "error"
                ),

                "verified_positive": False,

                "resolution": (
                    RESOLUTION_PARSE_FAILED
                ),

                "reasons": [
                    "PARSE_FAILED"
                ],

                "q_stage_target_evidence_inherited": False,

                "q_stage_action_evidence_inherited": False,

                "q_stage_notice_number_inherited": False,

                "q_stage_date_inherited": False,

                "q_stage_local_container_evidence_inherited": False,

                "q_stage_score_inherited_for_verification": False,

                "runtime_registration_allowed": False,

                "site_positive_allowed": False,
            }

            verification_records.append(
                record
            )

            print(
                "Document type:",
                document_type,
            )

            print(
                "Resolution:",
                RESOLUTION_PARSE_FAILED,
            )

            print(
                "Parse error:",
                parsed.get(
                    "error"
                ),
            )

            continue

        record = verify_document(
            seed_index=seed_index,
            seed=seed,
            fetch_result=fetch_result,
            document_type=document_type,
            parsed=parsed,
        )

        verification_records.append(
            record
        )

        # ====================================================
        # CHILD ATTACHMENT DISCOVERY
        # ====================================================

        if (
            document_type == "HTML"
            and parsed.get(
                "raw_html"
            )
        ):

            child_seeds = (
                extract_child_attachment_seeds(
                    parent_url=(
                        fetch_result.get(
                            "final_url"
                        )
                        or seed_url
                    ),
                    raw_html=parsed.get(
                        "raw_html"
                    ),
                )
            )

            for child in child_seeds:

                child[
                    "source_family"
                ] = seed.get(
                    "source_family"
                )

                child[
                    "source_name"
                ] = seed.get(
                    "source_name"
                )

                child[
                    "parent_seed_index"
                ] = seed_index

                child_attachment_records.append(
                    child
                )

            child_attachment_discovered_count += len(
                child_seeds
            )

        print(
            "Document type:",
            record.get(
                "document_type"
            ),
        )

        print(
            "Parser:",
            record.get(
                "parser"
            ),
        )

        print(
            "Text length:",
            record.get(
                "text_length"
            ),
        )

        print(
            "Target:",
            record.get(
                "target_in_document"
            ),
        )

        print(
            "Action:",
            record.get(
                "action_types"
            ),
        )

        print(
            "Notice numbers:",
            record.get(
                "notice_numbers"
            ),
        )

        print(
            "Dates:",
            record.get(
                "dates"
            ),
        )

        print(
            "Regions:",
            record.get(
                "administrative_regions"
            ),
        )

        print(
            "Official context:",
            record.get(
                "official_context"
            ),
        )

        print(
            "Search/list page:",
            record.get(
                "search_list_page"
            ),
        )

        print(
            "Permission/error HTML:",
            record.get(
                "permission_or_error_html"
            ),
        )

        print(
            "Scope:",
            record.get(
                "scope_extraction_status"
            ),
        )

        print(
            "Verified positive:",
            record.get(
                "verified_positive"
            ),
        )

        print(
            "Resolution:",
            record.get(
                "resolution"
            ),
        )

    # ========================================================
    # VERIFICATION RECORD DEDUPE
    # ========================================================

    grouped_records: Dict[
        Tuple[str, str],
        List[Dict[str, Any]],
    ] = defaultdict(
        list
    )

    for item in verification_records:

        url = canonicalize_url(
            item.get(
                "final_url"
            )
            or item.get(
                "seed_url"
            )
            or ""
        )

        key = (
            normalize_space(
                item.get(
                    "source_family"
                )
            ),
            url,
        )

        grouped_records[
            key
        ].append(
            item
        )

    RESOLUTION_PRIORITY = {
        RESOLUTION_VERIFIED: 100,
        RESOLUTION_ADMIN_DUTY: 80,
        RESOLUTION_LEGAL_REFERENCE: 75,
        RESOLUTION_TARGET_MENTION: 70,
        RESOLUTION_ARCHIVE_NO_TARGET: 60,
        RESOLUTION_UNRELATED: 55,
        RESOLUTION_SEARCH_LIST: 40,
        RESOLUTION_PERMISSION_HTML: 30,
        RESOLUTION_PARSE_FAILED: 20,
        RESOLUTION_DOWNLOAD_FAILED: 10,
    }

    def choose_verification_record(
        group: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        ordered = sorted(
            group,
            key=lambda item: (
                -RESOLUTION_PRIORITY.get(
                    item.get(
                        "resolution"
                    ),
                    0,
                ),
                -int(
                    item.get(
                        "text_length"
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
            "duplicate_seed_count"
        ] = len(
            group
        )

        representative[
            "seed_urls"
        ] = unique_strings(
            item.get(
                "seed_url"
            )
            for item in group
        )

        return representative

    canonical_records = [
        choose_verification_record(
            group
        )
        for group in grouped_records.values()
    ]

    canonical_records.sort(
        key=lambda item: (
            -RESOLUTION_PRIORITY.get(
                item.get(
                    "resolution"
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
                    "final_url"
                )
            ),
        )
    )

    # ========================================================
    # CHILD ATTACHMENT DEDUPE
    # ========================================================

    child_grouped: Dict[
        Tuple[str, str],
        List[Dict[str, Any]],
    ] = defaultdict(
        list
    )

    for item in child_attachment_records:

        url = canonicalize_url(
            item.get(
                "url"
            )
            or ""
        )

        if not url:
            continue

        key = (
            normalize_space(
                item.get(
                    "source_family"
                )
            ),
            url,
        )

        child_grouped[
            key
        ].append(
            item
        )

    canonical_child_seeds: List[
        Dict[str, Any]
    ] = []

    for group in child_grouped.values():

        representative = dict(
            group[
                0
            ]
        )

        representative[
            "discovery_count"
        ] = len(
            group
        )

        representative[
            "labels"
        ] = unique_strings(
            item.get(
                "label"
            )
            for item in group
        )

        representative[
            "parent_urls"
        ] = unique_strings(
            item.get(
                "parent_url"
            )
            for item in group
        )

        canonical_child_seeds.append(
            representative
        )

    canonical_child_seeds.sort(
        key=lambda item: (
            normalize_space(
                item.get(
                    "source_family"
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
    # SUMMARY
    # ========================================================

    verified_positive_documents = [
        item
        for item in canonical_records
        if item.get(
            "verified_positive"
        )
        is True
    ]

    target_mention_only = [
        item
        for item in canonical_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_TARGET_MENTION
    ]

    archive_no_target = [
        item
        for item in canonical_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_ARCHIVE_NO_TARGET
    ]

    administrative_duty = [
        item
        for item in canonical_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_ADMIN_DUTY
    ]

    legal_reference = [
        item
        for item in canonical_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_LEGAL_REFERENCE
    ]

    unrelated_documents = [
        item
        for item in canonical_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_UNRELATED
    ]

    search_list_pages = [
        item
        for item in canonical_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_SEARCH_LIST
    ]

    permission_error_pages = [
        item
        for item in canonical_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_PERMISSION_HTML
    ]

    canonical_download_failed = [
        item
        for item in canonical_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_DOWNLOAD_FAILED
    ]

    canonical_parse_failed = [
        item
        for item in canonical_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_PARSE_FAILED
    ]

    scope_extracted_count = sum(
        1
        for item in canonical_records
        if item.get(
            "scope_extraction_status"
        )
        == "SCOPE_EVIDENCE_EXTRACTED"
    )

    resolution_counts = Counter(
        item.get(
            "resolution"
        )
        for item in canonical_records
    )

    # ========================================================
    # RESOLUTION
    # ========================================================

    if verified_positive_documents:

        resolution = (
            "HISTORICAL_OFFICIAL_SOURCE_TARGET_DOCUMENT_VERIFIED"
        )

        next_action = (
            "검증된 historical official document의 고시번호·고시일·"
            "행정구역·scope를 정규화하고 후속 변경·해제 고시를 역추적한다. "
            "동시에 발견된 원문/첨부 child seed는 별도 document-local "
            "verification 단계에서 재검증한다."
        )

    elif canonical_child_seeds:

        resolution = (
            "HISTORICAL_OFFICIAL_SOURCE_CHILD_ATTACHMENT_VERIFICATION_REQUIRED"
        )

        next_action = (
            "archive record 자체에서는 verified positive를 확보하지 못했으나 "
            "원문/첨부 child identity를 확보했다. parent evidence를 상속하지 않고 "
            "child attachment 원문만 재조회하여 target/action/고시번호를 검증한다."
        )

    elif canonical_parse_failed:

        resolution = (
            "HISTORICAL_OFFICIAL_SOURCE_PARSE_RETRY_REQUIRED"
        )

        next_action = (
            "일부 historical source 문서 parsing이 실패했다. "
            "실패 문서 형식별 parser를 보강하고 parse-failed URL만 재검증한다."
        )

    elif canonical_download_failed:

        resolution = (
            "HISTORICAL_OFFICIAL_SOURCE_DOWNLOAD_RETRY_REQUIRED"
        )

        next_action = (
            "일부 historical source URL 다운로드가 실패했다. "
            "실패 URL만 선택적으로 재조회하고 archive session/referer/"
            "download endpoint 조건을 분석한다."
        )

    else:

        resolution = (
            "HISTORICAL_OFFICIAL_SOURCE_VERIFICATION_COMPLETED_NO_TARGET"
        )

        next_action = (
            "Q-stage에서 확보한 historical source seed에서는 "
            "개발밀도관리구역 verified positive를 확인하지 못했다. "
            "Q-stage에서 pending 상태였던 LEGACY_LOCAL_GAZETTE, "
            "LEGACY_LOCAL_NOTICE, URBAN_PLANNING_ARCHIVE, "
            "NOTICE_NUMBER_REVERSE_LOOKUP의 기관별 entry endpoint "
            "recovery 단계로 진행한다."
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-R "
            "Development Density Management Area "
            "Historical Official Source Seed Verification"
        ),

        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },

        "input": {
            "path": str(
                INPUT_PATH
            ),

            "q_stage_resolution": (
                input_data.get(
                    "resolution"
                )
            ),
        },

        "method": {
            "q_stage_verification_pool_only": True,

            "q_stage_evidence_inheritance": False,

            "document_local_evidence_only": True,

            "network_requery_enabled": True,

            "pdf_parser_enabled": True,

            "hwp_parser_enabled": True,

            "hwpx_parser_enabled": True,

            "html_parser_enabled": True,

            "extensionless_document_detection_enabled": True,

            "archive_record_child_attachment_discovery_enabled": True,

            "parent_child_evidence_inheritance": False,

            "administrative_duty_guard_enabled": True,

            "legal_reference_guard_enabled": True,

            "search_list_positive_prohibited": True,

            "permission_error_html_positive_prohibited": True,

            "scope_extraction_enabled": True,

            "date_required_for_positive": False,

            "scope_required_for_positive": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,

            "final_site_decision_allowed": False,
        },

        "summary": {
            "verification_input_count": len(
                verification_pool
            ),

            "request_count": request_count,

            "http_success_count": (
                http_success_count
            ),

            "download_failed_count": (
                download_failed_count
            ),

            "parse_failed_count": (
                parse_failed_count
            ),

            "raw_verification_record_count": len(
                verification_records
            ),

            "canonical_verification_record_count": len(
                canonical_records
            ),

            "verified_positive_count": len(
                verified_positive_documents
            ),

            "target_mention_only_count": len(
                target_mention_only
            ),

            "archive_no_target_count": len(
                archive_no_target
            ),

            "administrative_duty_reference_count": len(
                administrative_duty
            ),

            "legal_reference_only_count": len(
                legal_reference
            ),

            "unrelated_document_count": len(
                unrelated_documents
            ),

            "search_list_page_count": len(
                search_list_pages
            ),

            "permission_error_page_count": len(
                permission_error_pages
            ),

            "scope_evidence_extracted_count": (
                scope_extracted_count
            ),

            "raw_child_attachment_seed_count": (
                child_attachment_discovered_count
            ),

            "canonical_child_attachment_seed_count": len(
                canonical_child_seeds
            ),
        },

        "resolution_counts": dict(
            sorted(
                resolution_counts.items()
            )
        ),

        "verification_records": (
            canonical_records
        ),

        "verified_positive_documents": (
            verified_positive_documents
        ),

        "child_attachment_seeds": (
            canonical_child_seeds
        ),

        "next_stage_child_verification_pool": (
            canonical_child_seeds
        ),

        "resolution": resolution,

        "next_action": next_action,

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
    # PRINT RESULT
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "HISTORICAL SOURCE SEED VERIFICATION RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "Verification input count:",
        len(
            verification_pool
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
        "Download failed count:",
        len(
            canonical_download_failed
        ),
    )

    print(
        "Parse failed count:",
        len(
            canonical_parse_failed
        ),
    )

    print(
        "Canonical record count:",
        len(
            canonical_records
        ),
    )

    print(
        "Verified positive count:",
        len(
            verified_positive_documents
        ),
    )

    print(
        "Target mention only count:",
        len(
            target_mention_only
        ),
    )

    print(
        "Archive no-target count:",
        len(
            archive_no_target
        ),
    )

    print(
        "Administrative-duty-reference count:",
        len(
            administrative_duty
        ),
    )

    print(
        "Legal-reference-only count:",
        len(
            legal_reference
        ),
    )

    print(
        "Unrelated document count:",
        len(
            unrelated_documents
        ),
    )

    print(
        "Search/list page count:",
        len(
            search_list_pages
        ),
    )

    print(
        "Permission/error page count:",
        len(
            permission_error_pages
        ),
    )

    print(
        "Child attachment seed count:",
        len(
            canonical_child_seeds
        ),
    )

    print(
        "Scope evidence extracted count:",
        scope_extracted_count,
    )

    # ========================================================
    # POSITIVE PRINT
    # ========================================================

    if verified_positive_documents:

        print()

        print(
            "VERIFIED HISTORICAL DOCUMENTS"
        )

        print(
            "-" * 60
        )

        for index, item in enumerate(
            verified_positive_documents,
            start=1,
        ):

            print(
                f"[{index}] "
                f"{item.get('source_family')}"
            )

            print(
                "URL:",
                item.get(
                    "final_url"
                ),
            )

            print(
                "Input class:",
                item.get(
                    "input_classification"
                ),
            )

            print(
                "Document type:",
                item.get(
                    "document_type"
                ),
            )

            print(
                "Action types:",
                item.get(
                    "action_types"
                ),
            )

            print(
                "Notice numbers:",
                item.get(
                    "notice_numbers"
                ),
            )

            print(
                "Dates:",
                item.get(
                    "dates"
                ),
            )

            print(
                "Regions:",
                item.get(
                    "administrative_regions"
                ),
            )

            print(
                "Scope:",
                item.get(
                    "scope_evidence"
                ),
            )

            print()

    # ========================================================
    # CHILD SEED PRINT
    # ========================================================

    if canonical_child_seeds:

        print()

        print(
            "DISCOVERED CHILD ATTACHMENT SEEDS"
        )

        print(
            "-" * 60
        )

        for index, item in enumerate(
            canonical_child_seeds[
                :100
            ],
            start=1,
        ):

            print(
                f"[{index}] "
                f"{item.get('source_family')}"
            )

            print(
                "Class:",
                item.get(
                    "classification"
                ),
            )

            print(
                "Label:",
                item.get(
                    "label"
                ),
            )

            print(
                "URL:",
                item.get(
                    "url"
                ),
            )

            print(
                "Parent URL:",
                item.get(
                    "parent_url"
                ),
            )

            print()

    # ========================================================
    # RESOLUTION PRINT
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

    verification_keys = {
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
        for item in verification_pool
    }

    canonical_keys = {
        (
            normalize_space(
                item.get(
                    "source_family"
                )
            ),
            canonicalize_url(
                item.get(
                    "final_url"
                )
                or item.get(
                    "seed_url"
                )
                or ""
            ),
        )
        for item in canonical_records
    }

    child_keys = {
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
        for item in canonical_child_seeds
    }

    all_input_classes_valid = all(
        item.get(
            "input_classification"
        )
        in ALLOWED_INPUT_CLASSES
        for item in verification_pool
    )

    all_resolutions_valid = all(
        item.get(
            "resolution"
        )
        in VALID_RESOLUTIONS
        for item in canonical_records
    )

    all_child_classes_valid = all(
        item.get(
            "classification"
        )
        in VALID_CHILD_CLASSES
        for item in canonical_child_seeds
    )

    q_stage_inheritance_leakage = sum(
        1
        for item in canonical_records
        if (
            item.get(
                "q_stage_target_evidence_inherited"
            )
            is not False
            or item.get(
                "q_stage_action_evidence_inherited"
            )
            is not False
            or item.get(
                "q_stage_notice_number_inherited"
            )
            is not False
            or item.get(
                "q_stage_date_inherited"
            )
            is not False
            or item.get(
                "q_stage_local_container_evidence_inherited"
            )
            is not False
            or item.get(
                "q_stage_score_inherited_for_verification"
            )
            is not False
        )
    )

    child_parent_inheritance_leakage = sum(
        1
        for item in canonical_child_seeds
        if (
            item.get(
                "parent_target_evidence_inherited"
            )
            is not False
            or item.get(
                "parent_action_evidence_inherited"
            )
            is not False
            or item.get(
                "parent_notice_number_inherited"
            )
            is not False
            or item.get(
                "parent_date_inherited"
            )
            is not False
            or item.get(
                "parent_scope_inherited"
            )
            is not False
        )
    )

    target_missing_positive_leakage = sum(
        1
        for item in canonical_records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and item.get(
                "target_in_document"
            )
            is not True
        )
    )

    no_action_positive_leakage = sum(
        1
        for item in canonical_records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and not item.get(
                "action_types"
            )
        )
    )

    no_notice_positive_leakage = sum(
        1
        for item in canonical_records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and not item.get(
                "notice_numbers"
            )
        )
    )

    no_official_positive_leakage = sum(
        1
        for item in canonical_records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and item.get(
                "official_context"
            )
            is not True
        )
    )

    no_region_positive_leakage = sum(
        1
        for item in canonical_records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and not item.get(
                "administrative_regions"
            )
        )
    )

    admin_positive_leakage = sum(
        1
        for item in canonical_records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and item.get(
                "administrative_duty_reference"
            )
            is True
        )
    )

    legal_positive_leakage = sum(
        1
        for item in canonical_records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and item.get(
                "legal_reference_only"
            )
            is True
        )
    )

    search_list_positive_leakage = sum(
        1
        for item in canonical_records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and item.get(
                "search_list_page"
            )
            is True
        )
    )

    permission_html_positive_leakage = sum(
        1
        for item in canonical_records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and item.get(
                "permission_or_error_html"
            )
            is True
        )
    )

    child_without_local_relevance_leakage = sum(
        1
        for item in canonical_child_seeds
        if not (
            item.get(
                "exact_target_local_evidence"
            )
            is True
            or bool(
                item.get(
                    "relevance_reasons"
                )
            )
        )
    )

    attachment_identity_only_promotion = sum(
        1
        for item in canonical_child_seeds
        if (
            item.get(
                "attachment_identity_hint"
            )
            is True
            and not item.get(
                "relevance_reasons"
            )
        )
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

        "input exists": (
            INPUT_PATH.exists()
        ),

        "Q-stage input parsed": (
            isinstance(
                input_data,
                dict,
            )
        ),

        "Q-stage verification pool loaded": (
            len(
                verification_pool
            )
            > 0
        ),

        "verification pool unique": (
            len(
                verification_keys
            )
            == len(
                verification_pool
            )
        ),

        "only allowed Q-stage classes loaded": (
            all_input_classes_valid
        ),

        "network requery enabled": (
            output_data[
                "method"
            ][
                "network_requery_enabled"
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

        "Q-stage evidence inheritance disabled": (
            output_data[
                "method"
            ][
                "q_stage_evidence_inheritance"
            ]
            is False
        ),

        "Q-stage evidence inheritance leakage zero": (
            q_stage_inheritance_leakage
            == 0
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

        "HTML parser enabled": (
            output_data[
                "method"
            ][
                "html_parser_enabled"
            ]
            is True
        ),

        "extensionless document detection enabled": (
            output_data[
                "method"
            ][
                "extensionless_document_detection_enabled"
            ]
            is True
        ),

        "archive child attachment discovery enabled": (
            output_data[
                "method"
            ][
                "archive_record_child_attachment_discovery_enabled"
            ]
            is True
        ),

        "parent-child evidence inheritance disabled": (
            output_data[
                "method"
            ][
                "parent_child_evidence_inheritance"
            ]
            is False
        ),

        "child parent evidence inheritance leakage zero": (
            child_parent_inheritance_leakage
            == 0
        ),

        "administrative-duty guard enabled": (
            output_data[
                "method"
            ][
                "administrative_duty_guard_enabled"
            ]
            is True
        ),

        "legal-reference guard enabled": (
            output_data[
                "method"
            ][
                "legal_reference_guard_enabled"
            ]
            is True
        ),

        "search/list positive prohibited": (
            output_data[
                "method"
            ][
                "search_list_positive_prohibited"
            ]
            is True
        ),

        "permission/error HTML positive prohibited": (
            output_data[
                "method"
            ][
                "permission_error_html_positive_prohibited"
            ]
            is True
        ),

        "date not mandatory for positive": (
            output_data[
                "method"
            ][
                "date_required_for_positive"
            ]
            is False
        ),

        "scope not mandatory for positive": (
            output_data[
                "method"
            ][
                "scope_required_for_positive"
            ]
            is False
        ),

        "canonical verification records unique": (
            len(
                canonical_keys
            )
            == len(
                canonical_records
            )
        ),

        "all resolutions valid": (
            all_resolutions_valid
        ),

        "canonical child seeds unique": (
            len(
                child_keys
            )
            == len(
                canonical_child_seeds
            )
        ),

        "all child classes valid": (
            all_child_classes_valid
        ),

        "all verified documents contain target": all(
            item.get(
                "target_in_document"
            )
            is True
            for item
            in verified_positive_documents
        ),

        "all verified documents have action": all(
            bool(
                item.get(
                    "action_types"
                )
            )
            for item
            in verified_positive_documents
        ),

        "all verified documents have notice number": all(
            bool(
                item.get(
                    "notice_numbers"
                )
            )
            for item
            in verified_positive_documents
        ),

        "all verified documents have official context": all(
            item.get(
                "official_context"
            )
            is True
            for item
            in verified_positive_documents
        ),

        "all verified documents have geographic context": all(
            bool(
                item.get(
                    "administrative_regions"
                )
            )
            for item
            in verified_positive_documents
        ),

        "target-missing positive leakage zero": (
            target_missing_positive_leakage
            == 0
        ),

        "no-action positive leakage zero": (
            no_action_positive_leakage
            == 0
        ),

        "no-notice positive leakage zero": (
            no_notice_positive_leakage
            == 0
        ),

        "no-official-context positive leakage zero": (
            no_official_positive_leakage
            == 0
        ),

        "no-geographic-context positive leakage zero": (
            no_region_positive_leakage
            == 0
        ),

        "administrative-duty positive leakage zero": (
            admin_positive_leakage
            == 0
        ),

        "legal-reference positive leakage zero": (
            legal_positive_leakage
            == 0
        ),

        "search/list positive leakage zero": (
            search_list_positive_leakage
            == 0
        ),

        "permission/error HTML positive leakage zero": (
            permission_html_positive_leakage
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

        "child local relevance guard enabled": True,

        "child without local relevance leakage zero": (
            child_without_local_relevance_leakage
            == 0
        ),

        "attachment identity-only promotion zero": (
            attachment_identity_only_promotion
            == 0
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
        "Q-stage evidence inheritance leakage:",
        q_stage_inheritance_leakage,
    )

    print(
        "Child parent evidence inheritance leakage:",
        child_parent_inheritance_leakage,
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

    print(
        "No-official-context positive leakage:",
        no_official_positive_leakage,
    )

    print(
        "No-geographic-context positive leakage:",
        no_region_positive_leakage,
    )

    print(
        "Administrative-duty positive leakage:",
        admin_positive_leakage,
    )

    print(
        "Legal-reference positive leakage:",
        legal_positive_leakage,
    )

    print(
        "Search/list positive leakage:",
        search_list_positive_leakage,
    )

    print(
        "Permission/error HTML positive leakage:",
        permission_html_positive_leakage,
    )

    print(
        "Child without local relevance leakage:",
        child_without_local_relevance_leakage,
    )

    print(
        "Attachment identity-only promotion:",
        attachment_identity_only_promotion,
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
            "historical official source seed verification "
            "regression failed"
        )


if __name__ == "__main__":
    main()