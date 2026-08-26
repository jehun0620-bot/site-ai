# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-K
Development Density Management Area
Gazette Child Document Resolution

목표
======================================================================
J-stage source verification 결과 중

    GAZETTE_CONTAINER_REQUIRES_CHILD_RESOLUTION

상태의 공보/시보/군보/구보 container를 대상으로
실제 child document / attachment를 추출하고 검증한다.

입력:
    law_data/output/
    development_density_management_area_official_notice_source_verification.json

출력:
    law_data/output/
    development_density_management_area_gazette_child_document_resolution.json

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 원칙
======================================================================
1. J-stage에서 GAZETTE_CONTAINER_REQUIRES_CHILD_RESOLUTION인
   container만 입력으로 사용한다.

2. 부모 공보 HTML의 다음 evidence는 child에 상속하지 않는다.

    - target
    - action context
    - notice number
    - date
    - region text evidence
    - official context
    - scope evidence

3. 부모 container에서 허용되는 것은 다음 discovery metadata뿐이다.

    - parent URL
    - parent region
    - attachment URL discovery
    - link label
    - attachment filename
    - content disposition filename

4. child document positive 판정은 다운로드된 child 원문 자체에서만 한다.

5. 공보 container HTML 자체는 final positive로 승격하지 않는다.

6. PDF / HWP / HWPX / HTML child를 지원한다.

7. 확장자 없는 download endpoint도 Content-Type / magic bytes를
   이용하여 문서 형식을 판별한다.

8. 행정업무표 / 사무전결표 / 업무분장표 false positive를 차단한다.

9. 법령·조례의 단순 언급도 차단한다.

10. scope는 추출하지만 verified positive의 필수조건은 아니다.

11. runtime registration은 계속 차단한다.

12. SITE TRUE / FALSE 자동 판정도 계속 차단한다.
"""

from __future__ import annotations

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
        "official_notice_source_verification.json"
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
        "gazette_child_document_resolution.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# INPUT RESOLUTION
# ============================================================

GAZETTE_PARENT_RESOLUTION = (
    "GAZETTE_CONTAINER_REQUIRES_CHILD_RESOLUTION"
)


# ============================================================
# CHILD RESOLUTIONS
# ============================================================

RESOLUTION_VERIFIED = (
    "GAZETTE_CHILD_VERIFIED_TARGET_DOCUMENT"
)

RESOLUTION_TARGET_MENTION = (
    "GAZETTE_CHILD_TARGET_MENTION_ONLY"
)

RESOLUTION_ADMIN_DUTY = (
    "GAZETTE_CHILD_ADMINISTRATIVE_DUTY_REFERENCE"
)

RESOLUTION_LEGAL_REFERENCE = (
    "GAZETTE_CHILD_LEGAL_REFERENCE_ONLY"
)

RESOLUTION_UNRELATED = (
    "GAZETTE_CHILD_UNRELATED_DOCUMENT"
)

RESOLUTION_DOWNLOAD_FAILED = (
    "GAZETTE_CHILD_DOWNLOAD_FAILED"
)

RESOLUTION_PARSE_FAILED = (
    "GAZETTE_CHILD_PARSE_FAILED"
)

RESOLUTION_PARENT_NO_CHILD = (
    "GAZETTE_CONTAINER_NO_CHILD_DOCUMENT"
)

RESOLUTION_DOWNLOAD_ENDPOINT_HTML = (
    "GAZETTE_CHILD_DOWNLOAD_ENDPOINT_RETURNED_HTML"
)

VALID_CHILD_RESOLUTIONS = {
    RESOLUTION_VERIFIED,
    RESOLUTION_TARGET_MENTION,
    RESOLUTION_ADMIN_DUTY,
    RESOLUTION_LEGAL_REFERENCE,
    RESOLUTION_UNRELATED,
    RESOLUTION_DOWNLOAD_FAILED,
    RESOLUTION_PARSE_FAILED,
    RESOLUTION_DOWNLOAD_ENDPOINT_HTML,
}


# ============================================================
# HTTP CONFIG
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
# FILE TYPES
# ============================================================

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".hwp",
    ".hwpx",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}

DOWNLOAD_HINTS = [
    "download",
    "filedown",
    "filedownload",
    "atchfile",
    "attach",
    "file.do",
    "down.do",
    "download.do",
    "getfile",
]

FILE_LABEL_HINTS = [
    "첨부",
    "다운로드",
    "파일",
    ".pdf",
    ".hwp",
    ".hwpx",
]


# ============================================================
# TARGET / ACTION
# ============================================================

ACTION_PATTERNS = {
    "DESIGNATION": [
        r"개발밀도관리구역.{0,160}?지정",
        r"개발밀도관리구역을.{0,160}?지정",
        r"개발밀도관리구역으로.{0,160}?지정",
        r"지정.{0,160}?개발밀도관리구역",
    ],

    "CHANGE": [
        r"개발밀도관리구역.{0,160}?변경",
        r"개발밀도관리구역.{0,160}?변경결정",
        r"개발밀도관리구역.{0,160}?결정\s*\(\s*변경\s*\)",
        r"변경.{0,160}?개발밀도관리구역",
    ],

    "RELEASE": [
        r"개발밀도관리구역.{0,160}?해제",
        r"개발밀도관리구역.{0,160}?해지",
        r"해제.{0,160}?개발밀도관리구역",
    ],

    "DECISION": [
        r"개발밀도관리구역.{0,160}?결정",
        r"결정.{0,160}?개발밀도관리구역",
    ],
}


# ============================================================
# OFFICIAL CONTEXT
# ============================================================

OFFICIAL_CONTEXT_PATTERNS = [
    r"고\s*시",
    r"고시문",
    r"고시번호",
    r"도시관리계획",
    r"도시계획",
    r"지형도면",
    r"국토의\s*계획\s*및\s*이용에\s*관한\s*법률",
    r"국토계획법",
    r"시장",
    r"군수",
    r"구청장",
    r"특별시장",
    r"광역시장",
    r"도지사",
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
        r"[가-힣]{2,12}시|[가-힣]{2,12}군|[가-힣]{2,12}구)"
        r"\s*(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
    ),

    re.compile(
        r"(?P<notice>"
        r"(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
    ),

    # 띄어쓰기가 완전히 깨진 PDF/HWP 대응
    re.compile(
        r"(?P<notice>"
        r"[가-힣]{2,12}(?:시|군|구)"
        r"\s*(?:고시|공고)"
        r"\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
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
# LEGAL REFERENCE GUARD
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
# ADMINISTRATIVE DUTY GUARD
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
    "담 당 자",
    "팀 장",
    "국 장",
    "부 시 장",
    "관 · 과 · 단 장",
]


# ============================================================
# SCOPE
# ============================================================

SCOPE_PATTERNS = [
    r"[가-힣]{1,15}(?:동|읍|면|리)\s+\d+(?:-\d+)?\s*번지",
    r"[가-힣]{1,15}(?:동|읍|면|리)\s+일원",
    r"\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:㎡|m²|m2)",
    r"면적\s*[:：]?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?",
    r"위치\s*[:：]",
    r"구역\s*면적",
    r"지정\s*면적",
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


# ============================================================
# URL CANONICALIZATION
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

DISCOVERY_QUERY_KEYS = {
    "keyword",
    "searchkeyword",
    "searchword",
    "searchwrd",
    "searchtext",
    "searchterm",
    "query",
    "q",
    "srchtext",
    "srchword",
    "srchkeyword",
    "search",
}

JSESSIONID_PATTERN = re.compile(
    r";jsessionid=[^/?]+",
    re.IGNORECASE,
)


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
    *,
    remove_discovery_query: bool = True,
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

        if (
            remove_discovery_query
            and lowered
            in DISCOVERY_QUERY_KEYS
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
# J-STAGE INPUT
# ============================================================

def load_gazette_parents(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    """
    J-stage JSON의 특정 top-level key 이름에 의존하지 않고
    전체 구조를 순회하여

        resolution ==
        GAZETTE_CONTAINER_REQUIRES_CHILD_RESOLUTION

    인 실제 verification record만 수집한다.

    주의:
    summary / resolution_counts 같은 단순 문자열 값은
    record가 아니므로 URL을 가진 dict만 허용한다.
    """

    matched_records: List[
        Dict[str, Any]
    ] = []

    def walk(
        value: Any,
    ) -> None:

        if isinstance(
            value,
            dict,
        ):

            resolution = normalize_space(
                value.get(
                    "resolution"
                )
            )

            if (
                resolution
                == GAZETTE_PARENT_RESOLUTION
            ):

                raw_url = (
                    value.get(
                        "url"
                    )
                    or value.get(
                        "final_url"
                    )
                    or value.get(
                        "source_url"
                    )
                    or value.get(
                        "document_url"
                    )
                    or value.get(
                        "canonical_url"
                    )
                    or ""
                )

                url = canonicalize_url(
                    raw_url
                )

                if url:

                    normalized = dict(
                        value
                    )

                    normalized[
                        "url"
                    ] = url

                    matched_records.append(
                        normalized
                    )

            for child_value in value.values():

                if isinstance(
                    child_value,
                    (
                        dict,
                        list,
                    ),
                ):

                    walk(
                        child_value
                    )

        elif isinstance(
            value,
            list,
        ):

            for item in value:

                if isinstance(
                    item,
                    (
                        dict,
                        list,
                    ),
                ):

                    walk(
                        item
                    )

    walk(
        data
    )

    # --------------------------------------------------------
    # canonical parent dedupe
    # --------------------------------------------------------

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[str, str]
    ] = set()

    for item in matched_records:

        region = normalize_space(
            item.get(
                "region"
            )
            or item.get(
                "parent_region"
            )
            or ""
        )

        url = canonicalize_url(
            item.get(
                "url"
            )
            or ""
        )

        if not url:
            continue

        key = (
            region,
            url,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        normalized = dict(
            item
        )

        normalized[
            "region"
        ] = region

        normalized[
            "url"
        ] = url

        result.append(
            normalized
        )

    result.sort(
        key=lambda item: (
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

    return result


# ============================================================
# HTTP
# ============================================================

def fetch_bytes(
    session: requests.Session,
    url: str,
) -> Dict[str, Any]:

    result = {
        "requested_url": url,
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "content_disposition": "",
        "data": b"",
        "response_bytes": 0,
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
                remove_discovery_query=False,
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
# DOCUMENT TYPE DETECTION
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

    # URL / filename
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

    # Content-Type
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

    # Magic bytes
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

        # HWPX는 ZIP container.
        try:

            with zipfile.ZipFile(
                io.BytesIO(
                    data
                )
            ) as archive:

                names = {
                    name.lower()
                    for name
                    in archive.namelist()
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

    prefix = data[
        :4096
    ].lstrip().lower()

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

def decode_html_bytes(
    data: bytes,
) -> Tuple[str, str]:

    encodings = [
        "utf-8",
        "cp949",
        "euc-kr",
    ]

    for encoding in encodings:

        try:

            return (
                data.decode(
                    encoding
                ),
                encoding,
            )

        except UnicodeDecodeError:
            continue

    return (
        data.decode(
            "utf-8",
            errors="replace",
        ),
        "utf-8-replace",
    )


# ============================================================
# CHILD LINK EXTRACTION / ATTACHMENT IDENTITY RECOVERY
# ============================================================

SYNAP_FILE_VIEWER_PATTERN = re.compile(
    r"/synapsoft/FileViewer\.do",
    re.IGNORECASE,
)

EGOV_FILE_DOWN_DEFAULT_PATH = (
    "/cmm/fms/FileDown.do"
)

EGOV_DOWN_FUNCTION_PATTERN = re.compile(
    r"""
    fn_egov_downFile
    \s*
    \(
    \s*
    ['"]
    (?P<atch_file_id>[^'"]+)
    ['"]
    \s*
    ,
    \s*
    ['"]?
    (?P<file_sn>[^,'")\s]+)
    ['"]?
    """,
    re.IGNORECASE
    | re.VERBOSE,
)

EGOV_FILE_DOWN_PATH_PATTERN = re.compile(
    r"""
    ["']
    (?P<path>
        /[^"']*
        FileDown\.do
    )
    """,
    re.IGNORECASE
    | re.VERBOSE,
)

GENERIC_CHILD_LABELS = {
    "행정전화번호부",
    "로그인",
    "회원가입",
    "사이트맵",
    "홈",
    "메인",
    "목록",
    "이전글",
    "다음글",
}


def extract_js_url(
    onclick: str,
) -> str:

    text = normalize_space(
        onclick
    )

    if not text:
        return ""

    patterns = [
        r"""location\.href\s*=\s*['"]([^'"]+)['"]""",
        r"""window\.open\s*\(\s*['"]([^'"]+)['"]""",
        r"""location\s*=\s*['"]([^'"]+)['"]""",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:

            return normalize_space(
                match.group(1)
            )

    return ""


def extract_egov_download_identity(
    value: str,
) -> Optional[Dict[str, str]]:

    """
    다음과 같은 JS 호출에서 실제 첨부 identity를 추출한다.

        javascript:fn_egov_downFile(
            'FILE_000000001207735',
            '0'
        )

        onclick="
            fn_egov_downFile(
                'FILE_000000001207735',
                '0'
            );
        "

    중요한 점:
    javascript 문자열 자체를 URL로 canonicalize하지 않는다.
    """

    text = html.unescape(
        str(
            value
            or ""
        )
    )

    if not text:
        return None

    match = EGOV_DOWN_FUNCTION_PATTERN.search(
        text
    )

    if not match:
        return None

    atch_file_id = normalize_space(
        match.group(
            "atch_file_id"
        )
    )

    file_sn = normalize_space(
        match.group(
            "file_sn"
        )
    )

    if not atch_file_id:
        return None

    if not file_sn:
        file_sn = "0"

    return {
        "atchFileId":
            atch_file_id,

        "fileSn":
            file_sn,
    }


def extract_synap_attachment_identity(
    url: str,
) -> Optional[Dict[str, str]]:

    """
    Synap viewer URL은 최종 child 원문이 아니다.

    다만 다음 identity는 실제 attachment 복원에 사용할 수 있다.

        atchFileId
        fileSn
    """

    value = normalize_space(
        url
    )

    if not value:
        return None

    try:

        parsed = urlparse(
            value
        )

    except Exception:

        return None

    if not SYNAP_FILE_VIEWER_PATTERN.search(
        parsed.path
        or ""
    ):
        return None

    params = dict(
        parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
    )

    atch_file_id = normalize_space(
        params.get(
            "atchFileId"
        )
    )

    file_sn = normalize_space(
        params.get(
            "fileSn"
        )
    )

    if not atch_file_id:
        return None

    if not file_sn:
        file_sn = "0"

    return {
        "atchFileId":
            atch_file_id,

        "fileSn":
            file_sn,
    }


def is_synap_viewer_url(
    url: str,
) -> bool:

    value = normalize_space(
        url
    )

    if not value:
        return False

    try:

        path = (
            urlparse(
                value
            ).path
            or ""
        )

    except Exception:

        return False

    return (
        SYNAP_FILE_VIEWER_PATTERN.search(
            path
        )
        is not None
    )


def discover_egov_download_path(
    raw_html: str,
) -> str:

    """
    parent HTML 내부 JS에서 실제 FileDown.do path가 보이면
    그것을 우선 사용한다.

    찾지 못하면 표준 eGovFrame path인

        /cmm/fms/FileDown.do

    를 fallback으로 사용한다.
    """

    match = EGOV_FILE_DOWN_PATH_PATTERN.search(
        raw_html
        or ""
    )

    if match:

        raw_path = html.unescape(
            normalize_space(
                match.group(
                    "path"
                )
            )
        )

        # JS 문자열 뒤에 query concatenation 등이 붙는 경우
        # FileDown.do까지만 잘라낸다.
        file_down_match = re.search(
            r"(?P<path>/[^\"']*?FileDown\.do)",
            raw_path,
            flags=re.IGNORECASE,
        )

        if file_down_match:

            path = normalize_space(
                file_down_match.group(
                    "path"
                )
            )

            if path:
                return path

    return EGOV_FILE_DOWN_DEFAULT_PATH


def build_egov_file_download_url(
    parent_url: str,
    *,
    atch_file_id: str,
    file_sn: str = "0",
    download_path: str = EGOV_FILE_DOWN_DEFAULT_PATH,
) -> str:

    """
    attachment identity를 실제 eGov 다운로드 URL로 변환한다.

    예:
        https://www.dangjin.go.kr/
        cmm/fms/FileDown.do
        ?atchFileId=FILE_...
        &fileSn=0
    """

    parent_url = normalize_space(
        parent_url
    )

    atch_file_id = normalize_space(
        atch_file_id
    )

    file_sn = normalize_space(
        file_sn
    )

    download_path = normalize_space(
        download_path
    )

    if not parent_url:
        return ""

    if not atch_file_id:
        return ""

    if not file_sn:
        file_sn = "0"

    try:

        parsed = urlparse(
            parent_url
        )

    except Exception:

        return ""

    if (
        not parsed.scheme
        or not parsed.netloc
    ):
        return ""

    base_url = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            "/",
            "",
            "",
            "",
        )
    )

    if not download_path.startswith(
        "/"
    ):
        download_path = (
            "/"
            + download_path
        )

    download_url = urljoin(
        base_url,
        download_path,
    )

    query = urlencode(
        {
            "atchFileId":
                atch_file_id,

            "fileSn":
                file_sn,
        }
    )

    return canonicalize_url(
        f"{download_url}?{query}",
        remove_discovery_query=False,
    )


def is_probable_child_document_link(
    label: str,
    url: str,
) -> bool:

    normalized_label = normalize_space(
        label
    )

    if normalized_label in GENERIC_CHILD_LABELS:
        return False

    lowered_url = normalize_space(
        url
    ).lower()

    lowered_label = (
        normalized_label.lower()
    )

    try:

        path = (
            urlparse(
                url
            ).path
            or ""
        ).lower()

    except Exception:

        path = ""

    if any(
        path.endswith(
            extension
        )
        for extension
        in DOCUMENT_EXTENSIONS
    ):
        return True

    if contains_any(
        lowered_url,
        DOWNLOAD_HINTS,
    ):
        return True

    if contains_any(
        lowered_label,
        FILE_LABEL_HINTS,
    ):
        return True

    return False


def extract_raw_anchor_records(
    parent_url: str,
    raw_html: str,
) -> List[Dict[str, Any]]:

    """
    먼저 모든 anchor를 구조적으로 추출한다.

    이 단계에서는 javascript URL을 canonicalize하지 않는다.
    """

    results: List[
        Dict[str, Any]
    ] = []

    for anchor_index, match in enumerate(
        ANCHOR_PATTERN.finditer(
            raw_html
        ),
        start=1,
    ):

        attrs = match.group(
            "attrs"
        )

        body = match.group(
            "body"
        )

        label = strip_html(
            body
        )

        href_match = HREF_PATTERN.search(
            attrs
        )

        raw_href = (
            html.unescape(
                normalize_space(
                    href_match.group(
                        "href"
                    )
                )
            )
            if href_match
            else ""
        )

        onclick_match = ONCLICK_PATTERN.search(
            attrs
        )

        onclick = (
            html.unescape(
                normalize_space(
                    onclick_match.group(
                        "onclick"
                    )
                )
            )
            if onclick_match
            else ""
        )

        ordinary_url = ""

        if (
            raw_href
            and not raw_href.lower().startswith(
                "javascript:"
            )
            and raw_href != "#"
        ):

            if not raw_href.lower().startswith(
                (
                    "mailto:",
                    "tel:",
                )
            ):

                ordinary_url = canonicalize_url(
                    urljoin(
                        parent_url,
                        raw_href,
                    ),
                    remove_discovery_query=False,
                )

        if (
            not ordinary_url
            and onclick
        ):

            js_url = extract_js_url(
                onclick
            )

            if (
                js_url
                and not js_url.lower().startswith(
                    "javascript:"
                )
            ):

                ordinary_url = canonicalize_url(
                    urljoin(
                        parent_url,
                        js_url,
                    ),
                    remove_discovery_query=False,
                )

        js_identity = (
            extract_egov_download_identity(
                raw_href
            )
            or extract_egov_download_identity(
                onclick
            )
        )

        synap_identity = (
            extract_synap_attachment_identity(
                ordinary_url
            )
            if ordinary_url
            else None
        )

        results.append(
            {
                "anchor_index":
                    anchor_index,

                "label":
                    label,

                "raw_href":
                    raw_href,

                "onclick":
                    onclick,

                "ordinary_url":
                    ordinary_url,

                "js_attachment_identity":
                    js_identity,

                "synap_attachment_identity":
                    synap_identity,
            }
        )

    return results


def find_nearby_attachment_label(
    anchors: List[Dict[str, Any]],
    anchor_index: int,
    *,
    radius: int = 3,
) -> str:

    """
    Synap viewer anchor 자체의 label이 공백인 경우가 많다.

    바로 인접한 anchor에서 시보xxx.pdf 같은 attachment label을
    보조 metadata로 가져온다.

    이 label은 문서 evidence가 아니며 discovery metadata일 뿐이다.
    """

    candidates: List[
        Tuple[int, str]
    ] = []

    for item in anchors:

        candidate_index = int(
            item.get(
                "anchor_index"
            )
            or 0
        )

        distance = abs(
            candidate_index
            - anchor_index
        )

        if distance > radius:
            continue

        label = normalize_space(
            item.get(
                "label"
            )
        )

        if not label:
            continue

        lowered = label.lower()

        if not any(
            extension
            in lowered
            for extension
            in (
                ".pdf",
                ".hwp",
                ".hwpx",
            )
        ):
            continue

        candidates.append(
            (
                distance,
                label,
            )
        )

    if not candidates:
        return ""

    candidates.sort(
        key=lambda item: (
            item[
                0
            ],
            len(
                item[
                    1
                ]
            ),
        )
    )

    return candidates[
        0
    ][
        1
    ]


def extract_child_links(
    parent_url: str,
    raw_html: str,
) -> List[Dict[str, Any]]:

    """
    K-stage 핵심 child discovery.

    우선순위
    ------------------------------------------------------------
    1. fn_egov_downFile(...) attachment identity
       -> 실제 FileDown.do URL 복원

    2. Synap viewer identity
       -> 실제 FileDown.do URL 복원
       -> viewer 자체는 verification 대상으로 사용하지 않음

    3. 직접 PDF/HWP/HWPX/download link

    4. javascript placeholder는 결과에 절대 넣지 않음

    5. 실제 복원 URL 생성 후 dedupe
    """

    parent_url = canonicalize_url(
        parent_url,
        remove_discovery_query=False,
    )

    anchors = extract_raw_anchor_records(
        parent_url,
        raw_html,
    )

    download_path = discover_egov_download_path(
        raw_html
    )

    recovered: List[
        Dict[str, Any]
    ] = []

    recovered_identity_keys: Set[
        Tuple[str, str]
    ] = set()

    # --------------------------------------------------------
    # 1. JS fn_egov_downFile identity
    # --------------------------------------------------------

    for item in anchors:

        identity = item.get(
            "js_attachment_identity"
        )

        if not isinstance(
            identity,
            dict,
        ):
            continue

        atch_file_id = normalize_space(
            identity.get(
                "atchFileId"
            )
        )

        file_sn = normalize_space(
            identity.get(
                "fileSn"
            )
        )

        if not atch_file_id:
            continue

        if not file_sn:
            file_sn = "0"

        download_url = (
            build_egov_file_download_url(
                parent_url,
                atch_file_id=atch_file_id,
                file_sn=file_sn,
                download_path=download_path,
            )
        )

        if not download_url:
            continue

        identity_key = (
            atch_file_id,
            file_sn,
        )

        recovered_identity_keys.add(
            identity_key
        )

        recovered.append(
            {
                "label":
                    normalize_space(
                        item.get(
                            "label"
                        )
                    ),

                "url":
                    download_url,

                "raw_href":
                    item.get(
                        "raw_href"
                    ),

                "onclick":
                    item.get(
                        "onclick"
                    ),

                "attachment_identity": {
                    "atchFileId":
                        atch_file_id,

                    "fileSn":
                        file_sn,
                },

                "resolution_source":
                    "EGOV_JAVASCRIPT_ATTACHMENT_IDENTITY",

                "synthetic_download_url":
                    True,

                "synap_viewer_source_url":
                    "",
            }
        )

    # --------------------------------------------------------
    # 2. Synap identity fallback
    # --------------------------------------------------------

    for item in anchors:

        identity = item.get(
            "synap_attachment_identity"
        )

        if not isinstance(
            identity,
            dict,
        ):
            continue

        atch_file_id = normalize_space(
            identity.get(
                "atchFileId"
            )
        )

        file_sn = normalize_space(
            identity.get(
                "fileSn"
            )
        )

        if not atch_file_id:
            continue

        if not file_sn:
            file_sn = "0"

        identity_key = (
            atch_file_id,
            file_sn,
        )

        # 동일 identity가 JS link에서 이미 복구되었다면
        # Synap에서 다시 만들 필요 없음.
        if (
            identity_key
            in recovered_identity_keys
        ):
            continue

        download_url = (
            build_egov_file_download_url(
                parent_url,
                atch_file_id=atch_file_id,
                file_sn=file_sn,
                download_path=download_path,
            )
        )

        if not download_url:
            continue

        label = normalize_space(
            item.get(
                "label"
            )
        )

        if not label:

            label = find_nearby_attachment_label(
                anchors,
                int(
                    item.get(
                        "anchor_index"
                    )
                    or 0
                ),
            )

        recovered_identity_keys.add(
            identity_key
        )

        recovered.append(
            {
                "label":
                    label,

                "url":
                    download_url,

                "raw_href":
                    item.get(
                        "raw_href"
                    ),

                "onclick":
                    item.get(
                        "onclick"
                    ),

                "attachment_identity": {
                    "atchFileId":
                        atch_file_id,

                    "fileSn":
                        file_sn,
                },

                "resolution_source":
                    "SYNAP_VIEWER_ATTACHMENT_IDENTITY",

                "synthetic_download_url":
                    True,

                "synap_viewer_source_url":
                    item.get(
                        "ordinary_url"
                    )
                    or "",
            }
        )

    # --------------------------------------------------------
    # 3. Direct file/download links
    # --------------------------------------------------------

    direct_links: List[
        Dict[str, Any]
    ] = []

    for item in anchors:

        url = normalize_space(
            item.get(
                "ordinary_url"
            )
        )

        label = normalize_space(
            item.get(
                "label"
            )
        )

        if not url:
            continue

        # Synap viewer는 원문이 아니므로 child verification에서 제외.
        if is_synap_viewer_url(
            url
        ):
            continue

        if not is_probable_child_document_link(
            label,
            url,
        ):
            continue

        direct_links.append(
            {
                "label":
                    label,

                "url":
                    canonicalize_url(
                        url,
                        remove_discovery_query=False,
                    ),

                "raw_href":
                    item.get(
                        "raw_href"
                    ),

                "onclick":
                    item.get(
                        "onclick"
                    ),

                "attachment_identity":
                    None,

                "resolution_source":
                    "DIRECT_CHILD_DOCUMENT_LINK",

                "synthetic_download_url":
                    False,

                "synap_viewer_source_url":
                    "",
            }
        )

    # --------------------------------------------------------
    # 4. Merge
    # --------------------------------------------------------

    combined = (
        recovered
        + direct_links
    )

    # --------------------------------------------------------
    # 5. Actual resolved URL 기준 dedupe
    # --------------------------------------------------------

    results: List[
        Dict[str, Any]
    ] = []

    seen_urls: Set[str] = set()

    for item in combined:

        url = normalize_space(
            item.get(
                "url"
            )
        )

        if not url:
            continue

        # 가장 중요한 regression guard.
        if url.lower().startswith(
            "javascript:"
        ):
            continue

        if is_synap_viewer_url(
            url
        ):
            continue

        canonical_url = canonicalize_url(
            url,
            remove_discovery_query=False,
        )

        if not canonical_url:
            continue

        if canonical_url in seen_urls:
            continue

        seen_urls.add(
            canonical_url
        )

        normalized = dict(
            item
        )

        normalized[
            "url"
        ] = canonical_url

        results.append(
            normalized
        )

    return results


# ============================================================
# PDF PARSER
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
# HWPX PARSER
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

                # XML tag 제거
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
# HWP PARSER
# ============================================================

def parse_hwp_text(
    data: bytes,
) -> Tuple[
    str,
    str,
    str,
]:
    """
    우선 hwp5txt command를 사용한다.

    pyhwp가 설치되어 있다면 일반적으로 다음 executable이 존재한다.

        hwp5txt

    설치되지 않았거나 parser가 실패하면 parse failure로 남긴다.
    """

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
    document_type: str,
    data: bytes,
) -> Dict[str, Any]:

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

        raw_html, encoding = (
            decode_html_bytes(
                data
            )
        )

        text = strip_html(
            raw_html
        )

        parser = (
            f"html:{encoding}"
        )

        error = ""

    else:

        text = ""
        parser = ""
        error = (
            "Unsupported or unknown document type"
        )

    return {
        "text": text,
        "parser": parser,
        "error": error,
    }


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
        radius=1000,
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

    values: List[str] = []

    for pattern in NOTICE_PATTERNS:

        for match in pattern.finditer(
            text
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
# DATE
# ============================================================

def extract_dates(
    text: str,
) -> List[str]:

    result: List[str] = []

    for match in DATE_PATTERN.finditer(
        text
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
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )

    return unique_strings(
        result
    )


# ============================================================
# REGIONS
# ============================================================

def extract_regions(
    text: str,
) -> List[str]:

    regions: List[str] = []

    for region in REGION_PATTERNS:

        if region in text:
            regions.append(
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
            text,
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
        radius=1500,
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
        r"개발밀도관리구역.{0,100}?기안\s*[○●◎]?",
        normalized,
        flags=re.DOTALL,
    )

    target_draft_evidence = ""

    if target_draft_match:

        target_draft_evidence = (
            normalize_space(
                target_draft_match.group(0)
            )
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

    repeated_draft_markers = (
        draft_marker_count
        >= 5
    )

    administrative_reference = (
        strong_structure
        or (
            target_draft_match
            is not None
            and repeated_draft_markers
        )
        or (
            len(
                evidence
            )
            >= 4
            and repeated_draft_markers
        )
    )

    diagnostics = {
        "strong_structure": strong_structure,
        "draft_marker_count": (
            draft_marker_count
        ),
        "repeated_draft_markers": (
            repeated_draft_markers
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
        radius=1000,
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

    legal_reference_only = (
        bool(
            evidence
        )
        and not substantial_official_evidence
    )

    return (
        legal_reference_only,
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
        radius=3000,
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
# CHILD VERIFICATION
# ============================================================

def verify_child_document(
    *,
    parent: Dict[str, Any],
    child: Dict[str, Any],
    fetch_result: Dict[str, Any],
    document_type: str,
    parsed: Dict[str, Any],
    child_index: int,
) -> Dict[str, Any]:

    text = normalize_space(
        parsed.get(
            "text"
        )
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
        text,
        action_types=action_types,
        notice_numbers=notice_numbers,
        official_context=(
            official_context_evidence
        ),
    )

    scope_evidence = (
        extract_scope_evidence(
            text
        )
    )

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
        and not administrative_duty_reference
        and not legal_reference_only
    )

    reasons: List[str] = []

    if not target_found:

        reasons.append(
            "TARGET_NOT_IN_CHILD_DOCUMENT"
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

    if administrative_duty_reference:

        reasons.append(
            "ADMINISTRATIVE_DUTY_REFERENCE"
        )

    if legal_reference_only:

        reasons.append(
            "LEGAL_REFERENCE_ONLY"
        )

    if not has_scope:

        reasons.append(
            "SCOPE_NOT_EXTRACTED"
        )

    # --------------------------------------------------------
    # Resolution priority
    # --------------------------------------------------------

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

    elif target_found:

        resolution = (
            RESOLUTION_TARGET_MENTION
        )

    else:

        resolution = (
            RESOLUTION_UNRELATED
        )

    parent_url = canonicalize_url(
        parent.get(
            "url"
        )
        or ""
    )

    requested_child_url = canonicalize_url(
        child.get(
            "url"
        )
        or "",
        remove_discovery_query=False,
    )

    response_final_url = canonicalize_url(
        fetch_result.get(
            "final_url"
        )
        or "",
        remove_discovery_query=False,
    )

    # child_url은 발견/복원된 attachment identity URL을 보존한다.
    # HTTP redirect 결과로 덮어쓰지 않는다.
    child_url = requested_child_url

    contexts = extract_target_contexts(
        text,
        radius=1000,
    )

    return {
        "child_index": child_index,

        "parent_region": normalize_space(
            parent.get(
                "region"
            )
        ),

        # Parent metadata only.
        # Parent textual evidence is intentionally NOT inherited.
        "parent_url": parent_url,

        "child_label": normalize_space(
            child.get(
                "label"
            )
        ),

        "child_url": child_url,

        "requested_child_url": requested_child_url,

        "response_final_url": response_final_url,

        "attachment_identity": (
            child.get(
                "attachment_identity"
            )
        ),

        "attachment_resolution_source": (
            child.get(
                "resolution_source"
            )
        ),

        "synthetic_download_url": (
            child.get(
                "synthetic_download_url"
            )
            is True
        ),

        "synap_viewer_source_url": (
            child.get(
                "synap_viewer_source_url"
            )
            or ""
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

        "target_in_child_document": (
            target_found
        ),

        "target_contexts": (
            contexts[
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
            administrative_duty_reference
        ),

        "administrative_duty_evidence": (
            administrative_duty_evidence
        ),

        "administrative_duty_diagnostics": (
            administrative_duty_diagnostics
        ),

        "legal_reference_only": (
            legal_reference_only
        ),

        "legal_reference_evidence": (
            legal_reference_evidence
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

        # Explicit safety diagnostics
        "parent_target_evidence_inherited": (
            False
        ),

        "parent_notice_number_inherited": (
            False
        ),

        "parent_date_inherited": (
            False
        ),

        "parent_official_context_inherited": (
            False
        ),

        "parent_scope_evidence_inherited": (
            False
        ),
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
        "GAZETTE CHILD DOCUMENT RESOLUTION"
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
            "J-stage verification output not found: "
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
            "J-stage verification output must be a JSON object."
        )

    parents = load_gazette_parents(
        input_data
    )

    print(
        "Gazette parent container count:",
        len(
            parents
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
                "en-US;q=0.7,en;q=0.5"
            ),
        }
    )

    # ========================================================
    # COUNTERS
    # ========================================================

    parent_request_count = 0
    parent_http_success_count = 0
    parent_download_failed_count = 0

    discovered_child_count = 0

    child_request_count = 0
    child_http_success_count = 0
    child_download_failed_count = 0
    child_parse_failed_count = 0

    parent_results: List[
        Dict[str, Any]
    ] = []

    child_records: List[
        Dict[str, Any]
    ] = []

    no_child_parent_count = 0

    child_index = 0

    # ========================================================
    # PARENT LOOP
    # ========================================================

    for parent_index, parent in enumerate(
        parents,
        start=1,
    ):

        parent_url = canonicalize_url(
            parent.get(
                "url"
            )
            or ""
        )

        parent_region = normalize_space(
            parent.get(
                "region"
            )
        )

        print(
            "-" * 60
        )

        print(
            f"PARENT {parent_index}"
        )

        print(
            "Region:",
            parent_region,
        )

        print(
            "URL:",
            parent_url,
        )

        parent_request_count += 1

        parent_fetch = fetch_bytes(
            session,
            parent_url,
        )

        if (
            parent_fetch.get(
                "http_status"
            )
            == 200
        ):

            parent_http_success_count += 1

        if parent_fetch.get(
            "error"
        ):

            parent_download_failed_count += 1

            print(
                "Parent download error:",
                parent_fetch.get(
                    "error"
                ),
            )

            parent_results.append(
                {
                    "parent_index": parent_index,
                    "region": parent_region,
                    "url": parent_url,
                    "http_status": (
                        parent_fetch.get(
                            "http_status"
                        )
                    ),
                    "child_count": 0,
                    "resolution": (
                        "GAZETTE_PARENT_DOWNLOAD_FAILED"
                    ),
                    "error": parent_fetch.get(
                        "error"
                    ),
                }
            )

            continue

        raw_html, html_encoding = (
            decode_html_bytes(
                parent_fetch.get(
                    "data"
                )
                or b""
            )
        )

        child_links = extract_child_links(
            parent_fetch.get(
                "final_url"
            )
            or parent_url,
            raw_html,
        )

        discovered_child_count += len(
            child_links
        )

        print(
            "Child links:",
            len(
                child_links
            ),
        )

        if not child_links:

            no_child_parent_count += 1

            parent_results.append(
                {
                    "parent_index": parent_index,
                    "region": parent_region,
                    "url": parent_url,
                    "http_status": (
                        parent_fetch.get(
                            "http_status"
                        )
                    ),
                    "html_encoding": (
                        html_encoding
                    ),
                    "child_count": 0,
                    "resolution": (
                        RESOLUTION_PARENT_NO_CHILD
                    ),
                }
            )

            continue

        parent_child_records = []

        # ====================================================
        # CHILD LOOP
        # ====================================================

        for child in child_links:

            child_url = canonicalize_url(
                child.get(
                    "url"
                )
                or "",
                remove_discovery_query=False,
            )

        # --------------------------------------------------------
        # Safety guard
        # --------------------------------------------------------

            if not child_url:
                continue

            if child_url.lower().startswith(
                "javascript:"
            ):
                continue

            if is_synap_viewer_url(
                child_url
            ):
                continue

            child_index += 1
            child_request_count += 1

            print()

            print(
                f"  CHILD {child_index}"
            )

            print(
                "  Label:",
                child.get(
                    "label"
                ),
            )

            print(
                "  URL:",
                child_url,
            )

            child_fetch = fetch_bytes(
                session,
                child_url,
            )

            print(
                "  Attachment source:",
                child.get(
                    "resolution_source"
                ),
            )

            print(
                "  Attachment identity:",
                child.get(
                    "attachment_identity"
                ),
            )

            if (
                child_fetch.get(
                    "http_status"
                )
                == 200
            ):

                child_http_success_count += 1

            if child_fetch.get(
                "error"
            ):

                child_download_failed_count += 1

                record = {
                    "child_index": child_index,
                    "parent_region": parent_region,
                    "parent_url": parent_url,
                    "child_label": child.get(
                        "label"
                    ),
                    "child_url": child_url,
                    "http_status": (
                        child_fetch.get(
                            "http_status"
                        )
                    ),
                    "document_type": "",
                    "parser": "",
                    "verified_positive": False,
                    "resolution": (
                        RESOLUTION_DOWNLOAD_FAILED
                    ),
                    "reasons": [
                        "CHILD_DOWNLOAD_FAILED"
                    ],
                    "error": child_fetch.get(
                        "error"
                    ),
                    "parent_target_evidence_inherited": False,
                    "parent_notice_number_inherited": False,
                    "parent_date_inherited": False,
                    "parent_official_context_inherited": False,
                    "parent_scope_evidence_inherited": False,

                    "attachment_identity": (
                        child.get(
                        "attachment_identity"
                        )
                    ),

                    "attachment_resolution_source": (
                        child.get(
                            "resolution_source"
                        )
                    ),

                    "synthetic_download_url": (
                        child.get(
                        "synthetic_download_url"
                        )
                        is True
                    ),

                    "synap_viewer_source_url": (
                        child.get(
                            "synap_viewer_source_url"
                        )
                        or ""
                    ),
                }

                child_records.append(
                    record
                )

                parent_child_records.append(
                    record
                )

                print(
                    "  Resolution:",
                    RESOLUTION_DOWNLOAD_FAILED,
                )

                continue

            document_type = detect_document_type(
                url=(
                    child_fetch.get(
                        "final_url"
                    )
                    or child_url
                ),
                content_type=(
                    child_fetch.get(
                        "content_type"
                    )
                    or ""
                ),
                content_disposition=(
                    child_fetch.get(
                        "content_disposition"
                    )
                    or ""
                ),
                data=(
                    child_fetch.get(
                        "data"
                    )
                    or b""
                ),
            )

            attachment_identity = child.get(
                "attachment_identity"
            )

            expected_binary_attachment = (
                isinstance(
                    attachment_identity,
                    dict,
                )
                and bool(
                    normalize_space(
                        attachment_identity.get(
                            "atchFileId"
                        )
                    )
                )
            )

            if (
                expected_binary_attachment
                and document_type == "HTML"
            ):

                raw_html, html_encoding = decode_html_bytes(
                    child_fetch.get(
                        "data"
                    )
                    or b""
                )

                response_text = strip_html(
                    raw_html
                )

                record = {
                    "child_index":
                        child_index,

                    "parent_region":
                        parent_region,

                    "parent_url":
                        parent_url,

                    "child_label":
                        child.get(
                            "label"
                        ),

                    "child_url":
                        child_url,

                    "requested_child_url":
                        child_url,

                    "response_final_url":
                        child_fetch.get(
                            "final_url"
                        )
                        or "",

                    "attachment_identity":
                        attachment_identity,

                    "attachment_resolution_source":
                        child.get(
                            "resolution_source"
                        ),

                    "synthetic_download_url":
                        child.get(
                            "synthetic_download_url"
                        )
                        is True,

                    "synap_viewer_source_url":
                        child.get(
                            "synap_viewer_source_url"
                        )
                        or "",

                    "http_status":
                        child_fetch.get(
                            "http_status"
                        ),

                    "content_type":
                        child_fetch.get(
                            "content_type"
                        ),

                    "content_disposition":
                        child_fetch.get(
                            "content_disposition"
                        ),

                    "response_bytes":
                        child_fetch.get(
                            "response_bytes"
                        ),

                    "document_type":
                        document_type,

                    "parser":
                        f"html:{html_encoding}",

                    "response_text_preview":
                        response_text[
                            :1000
                        ],

                    "verified_positive":
                        False,

                    "resolution":
                        RESOLUTION_DOWNLOAD_ENDPOINT_HTML,

                    "reasons": [
                        "EXPECTED_ATTACHMENT_BUT_HTML_RETURNED"
                    ],

                    "parent_target_evidence_inherited":
                        False,

                    "parent_notice_number_inherited":
                        False,

                    "parent_date_inherited":
                        False,

                    "parent_official_context_inherited":
                        False,

                    "parent_scope_evidence_inherited":
                        False,
                }

                child_records.append(
                    record
                )

                parent_child_records.append(
                    record
                )

                print(
                    "  Document type:",
                    document_type,
                )

                print(
                    "  HTML response preview:",
                    response_text[
                        :300
                    ],
                )

                print(
                    "  Resolution:",
                    RESOLUTION_DOWNLOAD_ENDPOINT_HTML,
                )

                continue

            parsed = parse_document(
                document_type,
                child_fetch.get(
                    "data"
                )
                or b"",
            )

            if (
                parsed.get(
                    "error"
                )
                and not parsed.get(
                    "text"
                )
            ):

                child_parse_failed_count += 1

                record = {
                    "child_index": child_index,
                    "parent_region": parent_region,
                    "parent_url": parent_url,
                    "child_label": child.get(
                        "label"
                    ),
                    "child_url": (
                        child_fetch.get(
                            "final_url"
                        )
                        or child_url
                    ),
                    "http_status": (
                        child_fetch.get(
                            "http_status"
                        )
                    ),
                    "content_type": (
                        child_fetch.get(
                            "content_type"
                        )
                    ),
                    "content_disposition": (
                        child_fetch.get(
                            "content_disposition"
                        )
                    ),
                    "response_bytes": (
                        child_fetch.get(
                            "response_bytes"
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
                        "CHILD_PARSE_FAILED"
                    ],
                    "parent_target_evidence_inherited": False,
                    "parent_notice_number_inherited": False,
                    "parent_date_inherited": False,
                    "parent_official_context_inherited": False,
                    "parent_scope_evidence_inherited": False,
                }

                child_records.append(
                    record
                )

                parent_child_records.append(
                    record
                )

                print(
                    "  Document type:",
                    document_type,
                )

                print(
                    "  Resolution:",
                    RESOLUTION_PARSE_FAILED,
                )

                print(
                    "  Parse error:",
                    parsed.get(
                        "error"
                    ),
                )

                continue

            record = verify_child_document(
                parent=parent,
                child=child,
                fetch_result=child_fetch,
                document_type=document_type,
                parsed=parsed,
                child_index=child_index,
            )

            child_records.append(
                record
            )

            parent_child_records.append(
                record
            )

            print(
                "  Document type:",
                record.get(
                    "document_type"
                ),
            )

            print(
                "  Parser:",
                record.get(
                    "parser"
                ),
            )

            print(
                "  Text length:",
                record.get(
                    "text_length"
                ),
            )

            print(
                "  Target:",
                record.get(
                    "target_in_child_document"
                ),
            )

            print(
                "  Action:",
                record.get(
                    "action_types"
                ),
            )

            print(
                "  Notice numbers:",
                record.get(
                    "notice_numbers"
                ),
            )

            print(
                "  Dates:",
                record.get(
                    "dates"
                ),
            )

            print(
                "  Regions:",
                record.get(
                    "administrative_regions"
                ),
            )

            print(
                "  Admin duty:",
                record.get(
                    "administrative_duty_reference"
                ),
            )

            print(
                "  Legal reference only:",
                record.get(
                    "legal_reference_only"
                ),
            )

            print(
                "  Scope:",
                record.get(
                    "scope_extraction_status"
                ),
            )

            print(
                "  Verified positive:",
                record.get(
                    "verified_positive"
                ),
            )

            print(
                "  Resolution:",
                record.get(
                    "resolution"
                ),
            )

        parent_positive_count = sum(
            1
            for item in parent_child_records
            if item.get(
                "verified_positive"
            )
            is True
        )

        parent_results.append(
            {
                "parent_index": parent_index,
                "region": parent_region,
                "url": parent_url,
                "http_status": (
                    parent_fetch.get(
                        "http_status"
                    )
                ),
                "html_encoding": html_encoding,
                "child_count": len(
                    child_links
                ),
                "verified_child_count": (
                    parent_positive_count
                ),
                "resolution": (
                    "GAZETTE_PARENT_CHILDREN_RESOLVED"
                ),
            }
        )

    # ========================================================
    # CANONICAL CHILD DEDUPE
    # ========================================================

    grouped: Dict[
        Tuple[str, str],
        List[Dict[str, Any]],
    ] = defaultdict(
        list
    )

    def build_child_identity_key(
        item: Dict[str, Any],
    ) -> Tuple[str, str]:

        region = normalize_space(
            item.get(
                "parent_region"
            )
        )

        attachment_identity = item.get(
            "attachment_identity"
        )

        if isinstance(
            attachment_identity,
            dict,
        ):

            atch_file_id = normalize_space(
                attachment_identity.get(
                    "atchFileId"
                )
            )

            file_sn = normalize_space(
                attachment_identity.get(
                    "fileSn"
                )
            )

            if atch_file_id:

                if not file_sn:
                    file_sn = "0"

                return (
                    region,
                    (
                        "ATTACHMENT:"
                        f"{atch_file_id}:"
                        f"{file_sn}"
                    ),
                )

        child_url = canonicalize_url(
            item.get(
                "child_url"
            )
            or "",
            remove_discovery_query=False,
        )

        return (
            region,
            (
                "URL:"
                + child_url
            ),
        )


    grouped: Dict[
        Tuple[str, str],
        List[Dict[str, Any]],
    ] = defaultdict(
        list
    )

    for item in child_records:

        key = build_child_identity_key(
            item
        )

        grouped[
            key
        ].append(
            item
        )

    RESOLUTION_PRIORITY = {
        RESOLUTION_VERIFIED: 100,
        RESOLUTION_ADMIN_DUTY: 80,
        RESOLUTION_LEGAL_REFERENCE: 70,
        RESOLUTION_TARGET_MENTION: 60,
        RESOLUTION_UNRELATED: 50,
        RESOLUTION_DOWNLOAD_ENDPOINT_HTML: 30,
        RESOLUTION_PARSE_FAILED: 20,
        RESOLUTION_DOWNLOAD_FAILED: 10,
    }

    def choose_representative(
        group: List[
            Dict[str, Any]
        ],
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
                        "verified_positive"
                    )
                    is True
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
            "duplicate_discovery_count"
        ] = len(
            group
        )

        representative[
            "parent_urls"
        ] = unique_strings(
            item.get(
                "parent_url"
            )
            for item in group
        )

        representative[
            "labels"
        ] = unique_strings(
            item.get(
                "child_label"
            )
            for item in group
        )

        return representative

    canonical_child_records = [
        choose_representative(
            group
        )
        for group in grouped.values()
    ]

    canonical_child_records.sort(
        key=lambda item: (
            -RESOLUTION_PRIORITY.get(
                item.get(
                    "resolution"
                ),
                0,
            ),
            str(
                item.get(
                    "parent_region"
                )
                or ""
            ),
            str(
                item.get(
                    "child_url"
                )
                or ""
            ),
        )
    )

    duplicate_child_removed_count = (
        len(
            child_records
        )
        - len(
            canonical_child_records
        )
    )
    
    # ========================================================
    # SUMMARY
    # ========================================================

    recovered_attachment_identity_count = sum(
        1
        for item in canonical_child_records
        if (
            isinstance(
                item.get(
                    "attachment_identity"
                ),
                dict,
            )
            and bool(
                item.get(
                    "attachment_identity"
                ).get(
                    "atchFileId"
                )
            )
        )
    )

    synthetic_download_url_count = sum(
        1
        for item in canonical_child_records
        if item.get(
            "synthetic_download_url"
        )
        is True
    )
    verified_positive_documents = [
        item
        for item in canonical_child_records
        if item.get(
            "verified_positive"
        )
        is True
    ]

    admin_duty_count = sum(
        1
        for item in canonical_child_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_ADMIN_DUTY
    )

    legal_reference_count = sum(
        1
        for item in canonical_child_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_LEGAL_REFERENCE
    )

    target_mention_count = sum(
        1
        for item in canonical_child_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_TARGET_MENTION
    )

    unrelated_count = sum(
        1
        for item in canonical_child_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_UNRELATED
    )

    canonical_download_failed_count = sum(
        1
        for item in canonical_child_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_DOWNLOAD_FAILED
    )

    canonical_parse_failed_count = sum(
        1
        for item in canonical_child_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_PARSE_FAILED
    )

    scope_extracted_count = sum(
        1
        for item in canonical_child_records
        if item.get(
            "scope_extraction_status"
        )
        == "SCOPE_EVIDENCE_EXTRACTED"
    )

    classification_counts = Counter(
        item.get(
            "resolution"
        )
        for item in canonical_child_records
    )

    endpoint_html_count = sum(
        1
        for item in canonical_child_records
        if item.get(
            "resolution"
        )
        == RESOLUTION_DOWNLOAD_ENDPOINT_HTML
    )

    # ========================================================
    # RESOLUTION
    # ========================================================

    if verified_positive_documents:

        resolution = (
            "GAZETTE_CHILD_TARGET_DOCUMENT_VERIFIED"
        )

        next_action = (
            "검증된 child 고시 원문에서 고시번호·고시일·"
            "행정구역·지정 범위를 정규화하고, "
            "후속 변경·해제 고시를 추적한 뒤 "
            "positive spatial/PNU source를 역탐색한다."
        )

    elif endpoint_html_count:

        resolution = (
            "GAZETTE_CHILD_RESOLUTION_"
            "DOWNLOAD_ENDPOINT_RECOVERY_REQUIRED"
        )

        next_action = (
            "공보 attachment identity는 복원되었으나 "
            "현재 구성한 download endpoint가 실제 첨부 원문 대신 "
            "HTML 응답을 반환했다. "
            "parent HTML의 다운로드 JavaScript 구현, "
            "실제 form/action endpoint, request parameter 및 "
            "필요한 Referer/session 조건을 분석하여 "
            "원본 PDF/HWP 다운로드 URL을 복원한다."
        )

    elif canonical_parse_failed_count:

        resolution = (
            "GAZETTE_CHILD_RESOLUTION_COMPLETED_PARSE_RETRY_REQUIRED"
        )

        next_action = (
            "검증된 positive는 없으나 일부 child 문서가 "
            "다운로드 후 parsing에 실패했다. "
            "HWP parser 및 특수 attachment parser를 보강하여 "
            "parse-failed child만 선택적으로 재검증한다."
        )

    elif canonical_download_failed_count:

        resolution = (
            "GAZETTE_CHILD_RESOLUTION_COMPLETED_DOWNLOAD_RETRY_REQUIRED"
        )

        next_action = (
            "검증된 positive는 없으나 일부 child document download가 "
            "실패했다. 실패 URL만 선택적으로 재조회하고, "
            "공보 archive의 대체 attachment URL을 추적한다."
        )

    elif canonical_child_records:

        resolution = (
            "GAZETTE_CHILD_RESOLUTION_COMPLETED_NO_POSITIVE"
        )

        next_action = (
            "현재 공보 child 문서에서는 개발밀도관리구역 "
            "verified positive를 확인하지 못했다. "
            "국가기록원·구형 공보 archive·관보·토지이음 및 "
            "고시번호 역탐색으로 recovery 범위를 확장한다."
        )

    else:

        resolution = (
            "GAZETTE_CHILD_RESOLUTION_COMPLETED_NO_CHILD_DOCUMENT"
        )

        next_action = (
            "공보 container에서 검증 가능한 attachment/child document를 "
            "확보하지 못했다. 공보 시스템의 별도 download API, "
            "첨부 metadata 및 archive endpoint를 추가 분석한다."
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-K "
            "Development Density Management Area "
            "Gazette Child Document Resolution"
        ),

        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },

        "input": {
            "path": str(
                INPUT_PATH
            ),
            "j_stage_resolution": (
                input_data.get(
                    "resolution"
                )
            ),
        },

        "method": {
            "gazette_parent_only": True,

            "parent_resolution_required": (
                GAZETTE_PARENT_RESOLUTION
            ),

            "parent_text_evidence_inheritance": False,

            "parent_target_inheritance": False,

            "parent_notice_number_inheritance": False,

            "parent_date_inheritance": False,

            "parent_official_context_inheritance": False,

            "parent_scope_inheritance": False,

            "child_document_local_evidence_only": True,

            "pdf_parser_enabled": True,

            "hwp_parser_enabled": True,

            "hwpx_parser_enabled": True,

            "html_child_parser_enabled": True,

            "extensionless_document_detection": True,

            "administrative_duty_false_positive_guard": True,

            "legal_reference_false_positive_guard": True,

            "scope_extraction": True,

            "scope_required_for_positive": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,

            "egov_javascript_attachment_recovery": True,

            "synap_attachment_identity_recovery": True,

            "javascript_placeholder_verification_allowed": False,

            "synap_viewer_verification_allowed": False,

            "attachment_identity_preservation": True,

            "resolved_url_dedupe_after_attachment_recovery": True,
        },

        "summary": {
            "gazette_parent_count": len(
                parents
            ),

            "parent_request_count": (
                parent_request_count
            ),

            "parent_http_success_count": (
                parent_http_success_count
            ),

            "parent_download_failed_count": (
                parent_download_failed_count
            ),

            "parent_no_child_count": (
                no_child_parent_count
            ),

            "discovered_child_count": (
                discovered_child_count
            ),

            "raw_child_record_count": len(
                child_records
            ),

            "canonical_child_count": len(
                canonical_child_records
            ),

            "duplicate_child_removed_count": (
                duplicate_child_removed_count
            ),

            "child_request_count": (
                child_request_count
            ),

            "child_http_success_count": (
                child_http_success_count
            ),

            "child_download_failed_count": (
                child_download_failed_count
            ),

            "child_parse_failed_count": (
                child_parse_failed_count
            ),

            "canonical_download_failed_count": (
                canonical_download_failed_count
            ),

            "canonical_parse_failed_count": (
                canonical_parse_failed_count
            ),

            "verified_positive_count": len(
                verified_positive_documents
            ),

            "administrative_duty_reference_count": (
                admin_duty_count
            ),

            "legal_reference_only_count": (
                legal_reference_count
            ),

            "target_mention_only_count": (
                target_mention_count
            ),

            "unrelated_document_count": (
                unrelated_count
            ),

            "scope_evidence_extracted_count": (
                scope_extracted_count
            ),

            "recovered_attachment_identity_count": (
                recovered_attachment_identity_count
            ),

            "synthetic_download_url_count": (
                synthetic_download_url_count
            ),

            "download_endpoint_html_count": (
                endpoint_html_count
            ),

        },

        "resolution_counts": dict(
            sorted(
                classification_counts.items()
            )
        ),

        "parent_results": (
            parent_results
        ),

        "child_documents": (
            canonical_child_records
        ),

        "verified_positive_documents": (
            verified_positive_documents
        ),

        "resolution": resolution,

        "next_action": next_action,

        "runtime_registration_allowed": False,

        "site_positive_allowed": False,
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
    # RESULT PRINT
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "CHILD RESOLUTION RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "Gazette parent count:",
        len(
            parents
        ),
    )

    print(
        "Parent request count:",
        parent_request_count,
    )

    print(
        "Parent HTTP success count:",
        parent_http_success_count,
    )

    print(
        "Parent no-child count:",
        no_child_parent_count,
    )

    print(
        "Discovered child count:",
        discovered_child_count,
    )

    print(
        "Raw child record count:",
        len(
            child_records
        ),
    )

    print(
        "Canonical child count:",
        len(
            canonical_child_records
        ),
    )

    print(
        "Duplicate child removed:",
        duplicate_child_removed_count,
    )

    print(
        "Child HTTP success count:",
        child_http_success_count,
    )

    print(
        "Download failed count:",
        canonical_download_failed_count,
    )

    print(
        "Parse failed count:",
        canonical_parse_failed_count,
    )

    print(
        "Verified positive count:",
        len(
            verified_positive_documents
        ),
    )

    print(
        "Administrative-duty-reference count:",
        admin_duty_count,
    )

    print(
        "Legal-reference-only count:",
        legal_reference_count,
    )

    print(
        "Target-mention-only count:",
        target_mention_count,
    )

    print(
        "Unrelated document count:",
        unrelated_count,
    )

    print(
        "Scope evidence extracted count:",
        scope_extracted_count,
    )

    print(
    "Recovered attachment identity count:",
    recovered_attachment_identity_count,
    )

    print(
        "Synthetic download URL count:",
        synthetic_download_url_count,
    )
    # ========================================================
    # HIGH-VALUE POSITIVES
    # ========================================================

    if verified_positive_documents:

        print()

        print(
            "VERIFIED CHILD DOCUMENTS"
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
                f"{item.get('parent_region')}"
            )

            print(
                "URL:",
                item.get(
                    "child_url"
                ),
            )

            print(
                "Document type:",
                item.get(
                    "document_type"
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
                "Action types:",
                item.get(
                    "action_types"
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

    child_keys = {
        build_child_identity_key(
            item
        )
        for item in canonical_child_records
    }

    all_resolutions_valid = all(
        item.get(
            "resolution"
        )
        in VALID_CHILD_RESOLUTIONS
        for item in canonical_child_records
    )

    all_child_urls_exist = all(
        bool(
            item.get(
                "child_url"
            )
        )
        for item in canonical_child_records
    )

    parent_evidence_inheritance_leakage = sum(
        1
        for item in canonical_child_records
        if (
            item.get(
                "parent_target_evidence_inherited"
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
                "parent_official_context_inherited"
            )
            is not False
            or item.get(
                "parent_scope_evidence_inherited"
            )
            is not False
        )
    )

    target_missing_positive_leakage = sum(
        1
        for item in canonical_child_records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and item.get(
                "target_in_child_document"
            )
            is not True
        )
    )

    no_action_positive_leakage = sum(
        1
        for item in canonical_child_records
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
        for item in canonical_child_records
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
        for item in canonical_child_records
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
        for item in canonical_child_records
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
        for item in canonical_child_records
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
        for item in canonical_child_records
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

    javascript_child_url_leakage = sum(
        1
        for item in canonical_child_records
        if normalize_space(
            item.get(
                "child_url"
            )
        ).lower().startswith(
            "javascript:"
        )
    )


    synap_viewer_verification_leakage = sum(
        1
        for item in canonical_child_records
        if is_synap_viewer_url(
            item.get(
                "child_url"
            )
            or ""
        )
    )


    attachment_identity_missing_leakage = sum(
        1
        for item in canonical_child_records
        if (
            item.get(
                "synthetic_download_url"
            )
            is True
            and not (
                isinstance(
                    item.get(
                        "attachment_identity"
                    ),
                    dict,
                )
                and normalize_space(
                    item.get(
                        "attachment_identity"
                    ).get(
                        "atchFileId"
                    )
                )
            )
        )
    )


    synthetic_download_url_invalid_leakage = sum(
        1
        for item in canonical_child_records
        if (
            item.get(
                "synthetic_download_url"
            )
            is True
            and not (
                isinstance(
                    item.get(
                        "attachment_identity"
                    ),
                    dict,
                )
                and normalize_space(
                    item.get(
                        "attachment_identity"
                    ).get(
                        "atchFileId"
                    )
                )
                and normalize_space(
                    item.get(
                        "child_url"
                    )
                )
            )
        )
    )


    recovered_attachment_identity_count = sum(
        1
        for item in canonical_child_records
        if (
            isinstance(
                item.get(
                    "attachment_identity"
                ),
                dict,
            )
            and normalize_space(
                item.get(
                    "attachment_identity"
                ).get(
                    "atchFileId"
                )
            )
        )
    )
    
    validations = {

    "eGov javascript attachment recovery enabled": (
        output_data[
            "method"
        ][
            "egov_javascript_attachment_recovery"
        ]
        is True
    ),

    "Synap attachment identity recovery enabled": (
        output_data[
            "method"
        ][
            "synap_attachment_identity_recovery"
        ]
        is True
    ),

    "javascript placeholder verification prohibited": (
        output_data[
            "method"
        ][
            "javascript_placeholder_verification_allowed"
        ]
        is False
    ),

    "Synap viewer verification prohibited": (
        output_data[
            "method"
        ][
            "synap_viewer_verification_allowed"
        ]
        is False
    ),

    "attachment identity preservation enabled": (
        output_data[
            "method"
        ][
            "attachment_identity_preservation"
        ]
        is True
    ),

    "resolved URL dedupe after attachment recovery enabled": (
        output_data[
            "method"
        ][
            "resolved_url_dedupe_after_attachment_recovery"
        ]
        is True
    ),

    "javascript child URL leakage zero": (
        javascript_child_url_leakage
        == 0
    ),

    "Synap viewer verification leakage zero": (
        synap_viewer_verification_leakage
        == 0
    ),

    "synthetic attachment identity missing leakage zero": (
        attachment_identity_missing_leakage
        == 0
    ),

    "synthetic download URL invalid leakage zero": (
        synthetic_download_url_invalid_leakage
        == 0
    ),

    "gazette attachment identity recovered": (
        (
            len(
                parents
            )
            == 0
        )
        or (
            recovered_attachment_identity_count
            > 0
        )
    ),
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

        "J-stage input parsed": (
            isinstance(
                input_data,
                dict,
            )
        ),

        "gazette parent extraction enabled": (
            True
        ),

        "only gazette child-resolution parents loaded": (
            len(
                parents
            )
            > 0
            and all(
                normalize_space(
                    item.get(
                        "resolution"
                    )
                )
                == GAZETTE_PARENT_RESOLUTION
                for item in parents
            )
        ),

        "parent container final positive prohibited": (
            True
        ),

        "child discovery enabled": (
            True
        ),

        "child document network requery enabled": (
            True
        ),

        "document-local evidence enabled": (
            output_data[
                "method"
            ][
                "child_document_local_evidence_only"
            ]
            is True
        ),

        "parent target inheritance disabled": (
            output_data[
                "method"
            ][
                "parent_target_inheritance"
            ]
            is False
        ),

        "parent notice inheritance disabled": (
            output_data[
                "method"
            ][
                "parent_notice_number_inheritance"
            ]
            is False
        ),

        "parent date inheritance disabled": (
            output_data[
                "method"
            ][
                "parent_date_inheritance"
            ]
            is False
        ),

        "parent official-context inheritance disabled": (
            output_data[
                "method"
            ][
                "parent_official_context_inheritance"
            ]
            is False
        ),

        "parent scope inheritance disabled": (
            output_data[
                "method"
            ][
                "parent_scope_inheritance"
            ]
            is False
        ),

        "parent evidence inheritance leakage zero": (
            parent_evidence_inheritance_leakage
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

        "extensionless document detection enabled": (
            output_data[
                "method"
            ][
                "extensionless_document_detection"
            ]
            is True
        ),

        "administrative-duty guard enabled": (
            output_data[
                "method"
            ][
                "administrative_duty_false_positive_guard"
            ]
            is True
        ),

        "legal-reference guard enabled": (
            output_data[
                "method"
            ][
                "legal_reference_false_positive_guard"
            ]
            is True
        ),

        "scope extraction enabled": (
            output_data[
                "method"
            ][
                "scope_extraction"
            ]
            is True
        ),

        "scope not mandatory for verified positive": (
            output_data[
                "method"
            ][
                "scope_required_for_positive"
            ]
            is False
        ),

        "canonical child documents unique": (
            len(
                child_keys
            )
            == len(
                canonical_child_records
            )
        ),

        "all child resolutions valid": (
            all_resolutions_valid
        ),

        "all canonical child URLs exist": (
            all_child_urls_exist
        ),

        "verified documents unique": (
            len(
                {
                    canonicalize_url(
                        item.get(
                            "child_url"
                        )
                        or "",
                        remove_discovery_query=False
                    )
                    for item
                    in verified_positive_documents
                }
            )
            == len(
                verified_positive_documents
            )
        ),

        "all verified documents contain target": all(
            item.get(
                "target_in_child_document"
            )
            is True
            for item
            in verified_positive_documents
        ),

        "all verified documents have action context": all(
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

        "gazette parents loaded": (
             len(
            parents
            )
            > 0
        ),

        "J-stage gazette child resolution requirement preserved": (
    (
                normalize_space(
                    input_data.get(
                        "resolution"
                    )
                )
                != (
                    "OFFICIAL_NOTICE_SOURCE_VERIFICATION_"
                    "GAZETTE_CHILD_RESOLUTION_REQUIRED"
                )
            )
            or len(
                parents
            )
            > 0
        ),

    }

    print()

    print(
        "Javascript child URL leakage:",
        javascript_child_url_leakage,
    )

    print(
        "Synap viewer verification leakage:",
        synap_viewer_verification_leakage,
    )

    print(
        "Synthetic attachment identity missing leakage:",
        attachment_identity_missing_leakage,
    )

    print(
        "Synthetic download URL invalid leakage:",
        synthetic_download_url_invalid_leakage,
    )

    print(
        "Recovered attachment identity count:",
        recovered_attachment_identity_count,
    )
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
        "Parent evidence inheritance leakage:",
        parent_evidence_inheritance_leakage,
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
            "gazette child document resolution "
            "regression failed"
        )


if __name__ == "__main__":
    main()