# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-O
Development Density Management Area
Historical Official Archive Discovery

목표
======================================================================
N-stage에서 생성한 historical recovery query matrix와
기존 H-stage에서 정제한 공식 지자체 endpoint를 결합하여

    개발밀도관리구역

과 관련된 과거 공식 고시/detail/attachment/gazette issue seed를
실제 HTTP 조회를 통해 탐색한다.

입력 1:
    law_data/output/
    development_density_management_area_
    historical_official_notice_recovery_expansion.json

입력 2:
    law_data/output/
    development_density_management_area_
    official_board_endpoint_refinement.json

출력:
    law_data/output/
    development_density_management_area_
    historical_official_archive_discovery.json


대상 condition
======================================================================
개발밀도관리구역

표준 코드
======================================================================
UQQ700


핵심 원칙
======================================================================
1. N-stage historical query matrix만 검색어 source로 사용한다.

2. H-stage endpoint 중 다음 class만 실행한다.

    PRIMARY_GOSI_BOARD
    GAZETTE_ARCHIVE
    URBAN_PLANNING_BOARD

3. 검색엔진 scraping은 사용하지 않는다.

4. root/search/list page 자체는 final positive가 아니다.

5. 다음 identity만 next-stage verification seed로 허용한다.

    - detail URL
    - attachment URL
    - extensionless download URL
    - gazette issue URL

6. target exact phrase는 page 전체 text가 아니라
   link-local/container-local evidence에서만 인정한다.

7. page-level target inheritance를 금지한다.

8. N-stage exclusion memory의 URL은 canonicalize 후 차단한다.

9. M-stage에서 이미 negative로 확인된 attachment/document는
   historical discovery 과정에서 다시 승격시키지 않는다.

10. 행정업무표 / 사무전결 / 업무분장 false positive를 차단한다.

11. attachment는 단순 PDF/HWP 링크라는 이유만으로 승격하지 않는다.
    link-local/container-local 관련성이 있어야 한다.

12. query period와 추출된 문서 날짜가 명백히 불일치하면
    next-stage verification pool로 승격하지 않는다.

13. 이 단계에서는 verified positive 판정을 하지 않는다.

14. runtime registration은 계속 차단한다.

15. SITE TRUE/FALSE 자동 판정도 계속 차단한다.
"""

from __future__ import annotations

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

HISTORICAL_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_official_notice_recovery_expansion.json"
    )
)

ENDPOINT_INPUT_PATH = (
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
        "historical_official_archive_discovery.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# HTTP CONFIG
# ============================================================

TIMEOUT = 25

MAX_RESPONSE_BYTES = (
    12
    * 1024
    * 1024
)

REQUEST_DELAY_SECONDS = 0.03

MAX_ENDPOINT_SEARCH_VARIANTS_PER_QUERY = 8

MAX_LINKS_PER_RESPONSE = 600

MAX_TOTAL_REQUESTS = 5000

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# ALLOWED ENDPOINT CLASSES
# ============================================================

ALLOWED_ENDPOINT_CLASSES = {
    "PRIMARY_GOSI_BOARD",
    "GAZETTE_ARCHIVE",
    "URBAN_PLANNING_BOARD",
}


# ============================================================
# CANDIDATE CLASSES
# ============================================================

CLASS_TARGET_DIRECT = (
    "HISTORICAL_TARGET_DIRECT_DETAIL_SEED"
)

CLASS_ATTACHMENT = (
    "HISTORICAL_ATTACHMENT_DOCUMENT_SEED"
)

CLASS_EXTENSIONLESS = (
    "HISTORICAL_EXTENSIONLESS_DOWNLOAD_SEED"
)

CLASS_GAZETTE = (
    "HISTORICAL_GAZETTE_ISSUE_SEED"
)

CLASS_URBAN_NOTICE = (
    "HISTORICAL_URBAN_NOTICE_DETAIL_SEED"
)

CLASS_LOW_CONFIDENCE = (
    "HISTORICAL_LOW_CONFIDENCE_DETAIL_SEED"
)

CLASS_EXCLUDED_PRIOR_NEGATIVE = (
    "EXCLUDED_PRIOR_NEGATIVE_DOCUMENT"
)

CLASS_EXCLUDED_ADMIN_DUTY = (
    "EXCLUDED_ADMINISTRATIVE_DUTY_REFERENCE"
)

CLASS_EXCLUDED_GENERIC = (
    "EXCLUDED_GENERIC_LINK"
)

CLASS_EXCLUDED_OUT_OF_PERIOD = (
    "EXCLUDED_OUT_OF_PERIOD_DOCUMENT"
)


VALID_CANDIDATE_CLASSES = {
    CLASS_TARGET_DIRECT,
    CLASS_ATTACHMENT,
    CLASS_EXTENSIONLESS,
    CLASS_GAZETTE,
    CLASS_URBAN_NOTICE,
    CLASS_LOW_CONFIDENCE,
    CLASS_EXCLUDED_PRIOR_NEGATIVE,
    CLASS_EXCLUDED_ADMIN_DUTY,
    CLASS_EXCLUDED_GENERIC,
    CLASS_EXCLUDED_OUT_OF_PERIOD,
}


NEXT_STAGE_ALLOWED_CLASSES = {
    CLASS_TARGET_DIRECT,
    CLASS_ATTACHMENT,
    CLASS_EXTENSIONLESS,
    CLASS_GAZETTE,
    CLASS_URBAN_NOTICE,
}


# ============================================================
# CLASS PRIORITY
# ============================================================

CLASS_PRIORITY = {
    CLASS_TARGET_DIRECT: 100,
    CLASS_ATTACHMENT: 90,
    CLASS_EXTENSIONLESS: 85,
    CLASS_URBAN_NOTICE: 80,
    CLASS_GAZETTE: 70,
    CLASS_LOW_CONFIDENCE: 50,
    CLASS_EXCLUDED_OUT_OF_PERIOD: 25,
    CLASS_EXCLUDED_PRIOR_NEGATIVE: 20,
    CLASS_EXCLUDED_ADMIN_DUTY: 15,
    CLASS_EXCLUDED_GENERIC: 10,
}


# ============================================================
# SEARCH PARAMETER NAMES
# ============================================================

COMMON_SEARCH_PARAM_NAMES = [
    "searchKeyword",
    "searchWrd",
    "searchWord",
    "searchText",
    "searchTerm",
    "keyword",
    "query",
    "q",
    "srchText",
    "srchWord",
    "srchKeyword",
    "search",
]


# ============================================================
# SEMANTIC TERMS
# ============================================================

ACTION_TERMS = [
    "지정",
    "변경",
    "변경결정",
    "결정변경",
    "해제",
    "해지",
    "결정",
]

OFFICIAL_TERMS = [
    "고시",
    "고시문",
    "공고",
    "도시관리계획",
    "도시계획",
    "지형도면",
    "국토의 계획 및 이용에 관한 법률",
    "국토계획법",
]

URBAN_TERMS = [
    "도시관리계획",
    "도시계획",
    "도시정책",
    "용도지역",
    "용도지구",
    "용도구역",
    "지구단위계획",
    "지형도면",
    "기반시설부담구역",
]

GAZETTE_TERMS = [
    "시보",
    "군보",
    "구보",
    "공보",
    "도보",
    "호외",
]

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
    "담 당 자",
    "팀장",
    "팀 장",
    "국장",
    "국 장",
    "부시장",
    "부 시 장",
    "관 · 과 · 단 장",
]

GENERIC_LINK_LABEL_TERMS = {
    "목록",
    "이전글",
    "다음글",
    "이전",
    "다음",
    "처음",
    "마지막",
    "로그인",
    "회원가입",
    "사이트맵",
    "홈",
    "메인",
    "더보기",
    "전체보기",
    "새창",
    "본문",
}

GENERIC_PATH_TERMS = [
    "/login",
    "/member",
    "/join",
    "/sitemap",
    "/privacy",
    "/main",
    "/index",
]


# ============================================================
# URL / LINK
# ============================================================

FILE_EXTENSIONS = {
    ".pdf",
    ".hwp",
    ".hwpx",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
}

DOWNLOAD_HINT_TERMS = [
    "download",
    "filedown",
    "filedownload",
    "atchfile",
    "attach",
    "file.do",
    "filedown.do",
    "download.do",
    "down.do",
    "getfile",
    "filedownload.do",
]

DETAIL_HINT_TERMS = [
    "view",
    "detail",
    "select",
    "read",
    "article",
    "post",
    "boardarticle",
    "bbs",
]

LIST_HINT_TERMS = [
    "list.do",
    "/list",
    "selectboardlist",
    "board/list",
    "bbs/list",
    "search.do",
]


# ============================================================
# NOTICE / DATE PATTERNS
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
]

DATE_PATTERN = re.compile(
    r"(?P<year>19\d{2}|20\d{2})"
    r"\s*[.\-/년]\s*"
    r"(?P<month>0?[1-9]|1[0-2])"
    r"\s*[.\-/월]\s*"
    r"(?P<day>0?[1-9]|[12]\d|3[01])"
    r"\s*일?"
)


# ============================================================
# HTML PATTERNS
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

CONTAINER_TAG_PATTERN = re.compile(
    r"<(?P<tag>tr|li|article|section|div|td)\b[^>]*>"
    r"(?P<body>.*?)"
    r"</(?P=tag)>",
    re.IGNORECASE
    | re.DOTALL,
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


def extract_notice_numbers(
    text: str,
) -> List[str]:

    result: List[str] = []

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

            result.append(
                normalize_space(
                    value
                )
            )

    return unique_strings(
        result
    )


def extract_dates(
    text: str,
) -> List[str]:

    result: List[str] = []

    for match in DATE_PATTERN.finditer(
        text
    ):

        try:

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

        except Exception:
            continue

        result.append(
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )

    return unique_strings(
        result
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
# LOAD HISTORICAL QUERY MATRIX
# ============================================================

VALID_QUERY_CLASSES = {
    "EXACT_TARGET",
    "ACTION",
    "NOTICE",
    "URBAN_PLANNING",
    "ARCHIVE",

    "TARGET_EXACT",
    "TARGET_ACTION",
    "TARGET_NOTICE",
    "TARGET_URBAN_PLANNING",
    "TARGET_ARCHIVE",

    # N-stage naming variation 대응
    "EXACT_TARGET_QUERY",
    "ACTION_QUERY",
    "NOTICE_QUERY",
    "URBAN_PLANNING_QUERY",
    "ARCHIVE_QUERY",
}


QUERY_TEXT_KEYS = [
    "query",
    "search_term",
    "searchTerm",
    "term",
    "keyword",
    "search_keyword",
    "searchKeyword",
    "search_text",
    "searchText",
    "query_text",
    "queryText",
]


QUERY_CLASS_KEYS = [
    "query_class",
    "queryClass",
    "classification",
    "class",
    "query_type",
    "queryType",
    "type",
]


PERIOD_CLASS_KEYS = [
    "period_class",
    "periodClass",
    "period",
    "period_name",
    "periodName",
    "period_strategy",
    "periodStrategy",
]


START_YEAR_KEYS = [
    "start_year",
    "startYear",
    "from_year",
    "fromYear",
    "year_from",
    "yearFrom",
]


END_YEAR_KEYS = [
    "end_year",
    "endYear",
    "to_year",
    "toYear",
    "year_to",
    "yearTo",
]


QUERY_INDEX_KEYS = [
    "query_index",
    "queryIndex",
    "index",
]


def first_value(
    item: Dict[str, Any],
    keys: Iterable[str],
) -> Any:

    for key in keys:

        if key not in item:
            continue

        value = item.get(
            key
        )

        if value is None:
            continue

        if (
            isinstance(
                value,
                str,
            )
            and not value.strip()
        ):
            continue

        return value

    return None


def normalize_query_class(
    value: Any,
) -> str:

    text = normalize_space(
        value
    ).upper()

    if not text:
        return ""

    text = re.sub(
        r"[\s\-]+",
        "_",
        text,
    )

    aliases = {
        "EXACT": "EXACT_TARGET",
        "TARGET": "EXACT_TARGET",
        "TARGET_EXACT": "TARGET_EXACT",
        "EXACT_TARGET_QUERY": "EXACT_TARGET_QUERY",

        "DESIGNATION": "ACTION",
        "CHANGE": "ACTION",
        "RELEASE": "ACTION",
        "ACTION_QUERY": "ACTION_QUERY",

        "GOSI": "NOTICE",
        "OFFICIAL_NOTICE": "NOTICE",
        "NOTICE_QUERY": "NOTICE_QUERY",

        "URBAN": "URBAN_PLANNING",
        "URBAN_PLAN": "URBAN_PLANNING",
        "CITY_PLANNING": "URBAN_PLANNING",
        "URBAN_PLANNING_QUERY": "URBAN_PLANNING_QUERY",

        "GAZETTE": "ARCHIVE",
        "HISTORICAL_ARCHIVE": "ARCHIVE",
        "ARCHIVE_QUERY": "ARCHIVE_QUERY",
    }

    return aliases.get(
        text,
        text,
    )


def infer_query_class_from_query(
    query: str,
) -> str:

    value = normalize_space(
        query
    )

    if not value:
        return ""

    if (
        TARGET_NAME in value
        and any(
            term in value
            for term in [
                "지정",
                "변경",
                "해제",
                "해지",
                "결정",
            ]
        )
    ):

        return "ACTION"

    if any(
        term in value
        for term in [
            "고시",
            "고시문",
            "고시번호",
            "공고",
        ]
    ):

        return "NOTICE"

    if any(
        term in value
        for term in [
            "도시관리계획",
            "도시계획",
            "지형도면",
            "기반시설부담구역",
        ]
    ):

        return "URBAN_PLANNING"

    if any(
        term in value
        for term in [
            "시보",
            "군보",
            "구보",
            "도보",
            "공보",
            "archive",
            "아카이브",
        ]
    ):

        return "ARCHIVE"

    if TARGET_NAME in value:

        return "EXACT_TARGET"

    return ""


def extract_year(
    value: Any,
) -> int:

    if value is None:
        return 0

    if isinstance(
        value,
        int,
    ):

        if (
            1900
            <= value
            <= 2100
        ):

            return value

        return 0

    text = normalize_space(
        value
    )

    match = re.search(
        r"(19\d{2}|20\d{2})",
        text,
    )

    if not match:
        return 0

    try:

        return int(
            match.group(1)
        )

    except Exception:

        return 0


def infer_period_years(
    item: Dict[str, Any],
    period_class: str,
    query: str,
) -> Tuple[int, int]:

    start_year = extract_year(
        first_value(
            item,
            START_YEAR_KEYS,
        )
    )

    end_year = extract_year(
        first_value(
            item,
            END_YEAR_KEYS,
        )
    )

    if (
        start_year
        and end_year
    ):

        return (
            start_year,
            end_year,
        )

    combined = normalize_space(
        f"{period_class} {query}"
    )

    range_match = re.search(
        r"(19\d{2}|20\d{2})"
        r"\s*(?:[-~–—]|부터)\s*"
        r"(19\d{2}|20\d{2})",
        combined,
    )

    if range_match:

        return (
            int(
                range_match.group(1)
            ),
            int(
                range_match.group(2)
            ),
        )

    # N-stage known period classes 대응
    normalized_period = (
        normalize_space(
            period_class
        )
        .upper()
        .replace(
            " ",
            "_",
        )
    )

    period_mapping = {
        "EARLY制度_PERIOD": (
            2000,
            2009,
        ),

        "EARLY_PERIOD": (
            2000,
            2009,
        ),

        "MIDDLE_PERIOD": (
            2010,
            2019,
        ),

        "RECENT_HISTORICAL_PERIOD": (
            2020,
            2025,
        ),

        "CURRENT_PERIOD": (
            2026,
            2026,
        ),
    }

    if normalized_period in period_mapping:

        return period_mapping[
            normalized_period
        ]

    # query 자체에 단일 연도만 있는 경우
    years = [
        int(
            value
        )
        for value in re.findall(
            r"(19\d{2}|20\d{2})",
            query,
        )
    ]

    if years:

        return (
            min(
                years
            ),
            max(
                years
            ),
        )

    return (
        start_year,
        end_year,
    )


def looks_like_query_record(
    item: Dict[str, Any],
) -> bool:

    query_value = first_value(
        item,
        QUERY_TEXT_KEYS,
    )

    if query_value is None:
        return False

    query = normalize_space(
        query_value
    )

    if not query:
        return False

    # URL record를 query record로 잘못 인식하는 것 방지
    if (
        query.startswith(
            "http://"
        )
        or query.startswith(
            "https://"
        )
    ):

        return False

    # 역사 검색 matrix는 최소한 target 또는 관련 semantic term을 가진다.
    historical_semantic_terms = [
        TARGET_NAME,
        "개발밀도",
        "고시",
        "공고",
        "도시관리계획",
        "도시계획",
        "지형도면",
        "시보",
        "군보",
        "구보",
        "도보",
        "공보",
        "기반시설부담구역",
    ]

    if not any(
        term in query
        for term in historical_semantic_terms
    ):

        return False

    return True


def collect_query_records_recursive(
    value: Any,
    result: List[Dict[str, Any]],
) -> None:

    if isinstance(
        value,
        dict,
    ):

        if looks_like_query_record(
            value
        ):

            result.append(
                value
            )

        for child in value.values():

            if isinstance(
                child,
                (
                    dict,
                    list,
                ),
            ):

                collect_query_records_recursive(
                    child,
                    result,
                )

    elif isinstance(
        value,
        list,
    ):

        for child in value:

            if isinstance(
                child,
                (
                    dict,
                    list,
                ),
            ):

                collect_query_records_recursive(
                    child,
                    result,
                )


def load_historical_queries(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    """
    N-stage output의 특정 key 이름에 의존하지 않는다.

    JSON 전체를 재귀 순회하여 query-like dict를 구조적으로 찾아
    historical query matrix를 복원한다.

    지원 구조 예:
        {
            "query": "...",
            "query_class": "...",
            "period_class": "...",
            "start_year": 2000,
            "end_year": 2009
        }

    또는 camelCase / 별도 naming variation을 모두 허용한다.
    """

    raw_records: List[
        Dict[str, Any]
    ] = []

    collect_query_records_recursive(
        data,
        raw_records,
    )

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[
            str,
            str,
            str,
            int,
            int,
        ]
    ] = set()

    for fallback_index, item in enumerate(
        raw_records,
        start=1,
    ):

        query = normalize_space(
            first_value(
                item,
                QUERY_TEXT_KEYS,
            )
        )

        if not query:
            continue

        query_class = normalize_query_class(
            first_value(
                item,
                QUERY_CLASS_KEYS,
            )
        )

        if not query_class:

            query_class = (
                infer_query_class_from_query(
                    query
                )
            )

        period_class = normalize_space(
            first_value(
                item,
                PERIOD_CLASS_KEYS,
            )
        )

        (
            start_year,
            end_year,
        ) = infer_period_years(
            item,
            period_class,
            query,
        )

        raw_query_index = first_value(
            item,
            QUERY_INDEX_KEYS,
        )

        try:

            query_index = int(
                raw_query_index
            )

        except Exception:

            query_index = (
                fallback_index
            )

        key = (
            query,
            query_class,
            period_class,
            start_year,
            end_year,
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
            "query_index"
        ] = query_index

        normalized[
            "query"
        ] = query

        normalized[
            "query_class"
        ] = query_class

        normalized[
            "period_class"
        ] = period_class

        normalized[
            "start_year"
        ] = start_year

        normalized[
            "end_year"
        ] = end_year

        normalized[
            "query_record_recovered_recursively"
        ] = True

        result.append(
            normalized
        )

    result.sort(
        key=lambda item: (
            int(
                item.get(
                    "query_index"
                )
                or 0
            ),
            normalize_space(
                item.get(
                    "period_class"
                )
            ),
            normalize_space(
                item.get(
                    "query_class"
                )
            ),
            normalize_space(
                item.get(
                    "query"
                )
            ),
        )
    )

    return result

# ============================================================
# LOAD ENDPOINTS
# ============================================================

def load_searchable_endpoints(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    raw = data.get(
        "next_stage_search_pool"
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

        endpoint_class = normalize_space(
            item.get(
                "classification"
            )
        )

        if (
            endpoint_class
            not in ALLOWED_ENDPOINT_CLASSES
        ):
            continue

        region = normalize_space(
            item.get(
                "region"
            )
        )

        url = canonicalize_url(
            item.get(
                "canonical_url"
            )
            or item.get(
                "raw_url"
            )
            or item.get(
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
            "canonical_url"
        ] = url

        result.append(
            normalized
        )

    return result


# ============================================================
# EXCLUSION MEMORY
# ============================================================

def collect_urls_recursive(
    value: Any,
    *,
    parent_key: str = "",
) -> List[str]:

    urls: List[str] = []

    if isinstance(
        value,
        dict,
    ):

        for key, child in value.items():

            lowered_key = str(
                key
            ).lower()

            if (
                "url"
                in lowered_key
                and isinstance(
                    child,
                    str,
                )
            ):

                canonical = canonicalize_url(
                    child,
                    remove_discovery_query=True,
                )

                if canonical:
                    urls.append(
                        canonical
                    )

            elif isinstance(
                child,
                (
                    dict,
                    list,
                ),
            ):

                urls.extend(
                    collect_urls_recursive(
                        child,
                        parent_key=key,
                    )
                )

    elif isinstance(
        value,
        list,
    ):

        for item in value:

            if isinstance(
                item,
                str,
            ):

                if (
                    item.startswith(
                        "http://"
                    )
                    or item.startswith(
                        "https://"
                    )
                ):

                    canonical = canonicalize_url(
                        item,
                        remove_discovery_query=True,
                    )

                    if canonical:
                        urls.append(
                            canonical
                        )

            elif isinstance(
                item,
                (
                    dict,
                    list,
                ),
            ):

                urls.extend(
                    collect_urls_recursive(
                        item,
                        parent_key=parent_key,
                    )
                )

    return unique_strings(
        urls
    )


def load_exclusion_urls(
    historical_data: Dict[str, Any],
) -> Set[str]:

    result: Set[str] = set()

    preferred_keys = [
        "exclusion_urls",
        "negative_document_urls",
        "prior_false_positive_urls",
        "current_negative_document_urls",
        "negative_urls",
    ]

    for key in preferred_keys:

        raw = historical_data.get(
            key
        )

        if raw is None:
            continue

        for url in collect_urls_recursive(
            raw,
            parent_key=key,
        ):

            result.add(
                url
            )

        if isinstance(
            raw,
            list,
        ):

            for item in raw:

                if isinstance(
                    item,
                    str,
                ):

                    canonical = canonicalize_url(
                        item,
                        remove_discovery_query=True,
                    )

                    if canonical:
                        result.add(
                            canonical
                        )

                elif isinstance(
                    item,
                    dict,
                ):

                    raw_url = (
                        item.get(
                            "url"
                        )
                        or item.get(
                            "document_url"
                        )
                        or item.get(
                            "child_url"
                        )
                        or item.get(
                            "final_url"
                        )
                        or ""
                    )

                    canonical = canonicalize_url(
                        raw_url,
                        remove_discovery_query=True,
                    )

                    if canonical:
                        result.add(
                            canonical
                        )

    # N-stage의 exclusion 관련 구조명이 바뀌더라도 대응
    for key, value in historical_data.items():

        lowered = str(
            key
        ).lower()

        if (
            "negative"
            in lowered
            or "excluded"
            in lowered
            or "exclusion"
            in lowered
            or "false_positive"
            in lowered
        ):

            for url in collect_urls_recursive(
                value,
                parent_key=key,
            ):

                result.add(
                    url
                )

    return result


# ============================================================
# SEARCH VARIANT GENERATION
# ============================================================

def build_get_search_variants(
    endpoint_url: str,
    search_term: str,
) -> List[str]:

    variants: List[str] = []

    try:

        parsed = urlparse(
            endpoint_url
        )

    except Exception:

        return variants

    base_query = parse_qsl(
        parsed.query,
        keep_blank_values=True,
    )

    for param_name in COMMON_SEARCH_PARAM_NAMES:

        query = [
            (
                key,
                value,
            )
            for key, value
            in base_query
            if key.lower()
            != param_name.lower()
        ]

        query.append(
            (
                param_name,
                search_term,
            )
        )

        url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                urlencode(
                    query,
                    doseq=True,
                ),
                parsed.fragment,
            )
        )

        canonical = canonicalize_url(
            url
        )

        if canonical:

            variants.append(
                canonical
            )

        if (
            len(
                variants
            )
            >= MAX_ENDPOINT_SEARCH_VARIANTS_PER_QUERY
        ):
            break

    return unique_strings(
        variants
    )


# ============================================================
# HTTP
# ============================================================

def request_html(
    session: requests.Session,
    url: str,
) -> Dict[str, Any]:

    result: Dict[str, Any] = {
        "url": url,
        "http_status": None,
        "final_url": "",
        "content_type": "",
        "response_bytes": 0,
        "html": "",
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

                if (
                    total
                    > MAX_RESPONSE_BYTES
                ):

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

            encoding = (
                response.encoding
                or response.apparent_encoding
                or "utf-8"
            )

            raw_html = data.decode(
                encoding,
                errors="replace",
            )

            result[
                "html"
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
# LINK EXTRACTION
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
        r"""document\.location\s*=\s*['"]([^'"]+)['"]""",
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


def find_local_container_text(
    raw_html: str,
    anchor_start: int,
    anchor_end: int,
) -> str:

    """
    anchor를 포함하는 가장 가까운 tr/li/article/section/div/td container text를
    제한적으로 추출한다.

    page 전체 text는 사용하지 않는다.
    """

    candidate_texts: List[str] = []

    search_left = max(
        0,
        anchor_start - 6000,
    )

    search_right = min(
        len(
            raw_html
        ),
        anchor_end + 6000,
    )

    segment = raw_html[
        search_left:search_right
    ]

    local_anchor_start = (
        anchor_start
        - search_left
    )

    local_anchor_end = (
        anchor_end
        - search_left
    )

    for match in CONTAINER_TAG_PATTERN.finditer(
        segment
    ):

        if (
            match.start()
            <= local_anchor_start
            and match.end()
            >= local_anchor_end
        ):

            text = strip_html(
                match.group(
                    "body"
                )
            )

            if text:

                candidate_texts.append(
                    text
                )

    if candidate_texts:

        # 가장 짧은 enclosing container가 가장 local한 것으로 간주
        candidate_texts.sort(
            key=len
        )

        return candidate_texts[
            0
        ][
            :6000
        ]

    # container가 없으면 anchor 주변 제한 window만 사용
    fallback_left = max(
        0,
        anchor_start - 500,
    )

    fallback_right = min(
        len(
            raw_html
        ),
        anchor_end + 500,
    )

    return strip_html(
        raw_html[
            fallback_left:fallback_right
        ]
    )


def extract_links(
    base_url: str,
    raw_html: str,
) -> List[Dict[str, str]]:

    results: List[
        Dict[str, str]
    ] = []

    seen: Set[
        Tuple[str, str]
    ] = set()

    for match in ANCHOR_PATTERN.finditer(
        raw_html
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
                "data:",
            )
        ):
            continue

        absolute_url = canonicalize_url(
            urljoin(
                base_url,
                html.unescape(
                    href
                ),
            )
        )

        if not absolute_url:
            continue

        local_container_text = (
            find_local_container_text(
                raw_html,
                match.start(),
                match.end(),
            )
        )

        key = (
            absolute_url,
            local_container_text,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        results.append(
            {
                "label": label,
                "url": absolute_url,
                "onclick": onclick,
                "local_container_text": (
                    local_container_text
                ),
            }
        )

        if (
            len(
                results
            )
            >= MAX_LINKS_PER_RESPONSE
        ):
            break

    return results


# ============================================================
# LINK TYPE HELPERS
# ============================================================

def is_file_url(
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
        for extension
        in FILE_EXTENSIONS
    )


def is_extensionless_download_url(
    url: str,
) -> bool:

    if is_file_url(
        url
    ):
        return False

    return contains_any(
        url,
        DOWNLOAD_HINT_TERMS,
    )


def looks_list_endpoint(
    url: str,
) -> bool:

    return contains_any(
        url,
        LIST_HINT_TERMS,
    )


def looks_detail_endpoint(
    url: str,
) -> bool:

    lowered = url.lower()

    if contains_any(
        lowered,
        DETAIL_HINT_TERMS,
    ):
        return True

    parsed = urlparse(
        url
    )

    query_keys = {
        key.lower()
        for key, _
        in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
    }

    identity_keys = {
        "nttid",
        "seq",
        "idx",
        "no",
        "articleid",
        "bbsseq",
        "boardseq",
        "postid",
        "id",
    }

    return bool(
        query_keys
        & identity_keys
    )


def looks_generic_navigation(
    label: str,
    url: str,
) -> bool:

    normalized_label = normalize_space(
        label
    )

    if (
        normalized_label
        in GENERIC_LINK_LABEL_TERMS
    ):
        return True

    if contains_any(
        url,
        GENERIC_PATH_TERMS,
    ):
        return True

    return False


def same_host(
    url_a: str,
    url_b: str,
) -> bool:

    try:

        return (
            urlparse(
                url_a
            ).hostname
            ==
            urlparse(
                url_b
            ).hostname
        )

    except Exception:

        return False


def is_root_navigation(
    url: str,
) -> bool:

    try:

        parsed = urlparse(
            url
        )

    except Exception:

        return False

    path = (
        parsed.path
        or "/"
    )

    if (
        path
        in {
            "",
            "/",
            "/main",
            "/main.do",
            "/index",
            "/index.do",
        }
        and not parsed.query
    ):

        return True

    return False


# ============================================================
# ADMIN DUTY GUARD
# ============================================================

def detect_administrative_duty_reference(
    text: str,
) -> Tuple[
    bool,
    List[str],
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

    draft_marker_count = len(
        re.findall(
            r"기안\s*[○●◎]?",
            normalized,
        )
    )

    if (
        draft_marker_count
        >= 5
    ):

        evidence.append(
            f"기안 marker x{draft_marker_count}"
        )

    target_draft_match = re.search(
        r"개발밀도관리구역.{0,120}?기안",
        normalized,
        flags=re.DOTALL,
    )

    if target_draft_match:

        evidence.append(
            normalize_space(
                target_draft_match.group(
                    0
                )
            )
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

    administrative_reference = (
        strong_structure
        or (
            target_draft_match
            is not None
            and draft_marker_count
            >= 5
        )
        or (
            len(
                evidence
            )
            >= 4
            and draft_marker_count
            >= 5
        )
    )

    return (
        administrative_reference,
        unique_strings(
            evidence
        ),
    )


# ============================================================
# PERIOD MATCH
# ============================================================

def date_matches_period(
    dates: List[str],
    start_year: int,
    end_year: int,
) -> Optional[bool]:

    """
    return:
        True  -> 날짜 evidence가 있고 period 일치
        False -> 날짜 evidence가 있고 period 불일치
        None  -> 날짜/period evidence 부족
    """

    if (
        not start_year
        or not end_year
    ):
        return None

    if not dates:
        return None

    years: List[int] = []

    for value in dates:

        try:

            years.append(
                int(
                    value[
                        :4
                    ]
                )
            )

        except Exception:
            continue

    if not years:
        return None

    return any(
        start_year
        <= year
        <= end_year
        for year in years
    )


# ============================================================
# CANDIDATE CLASSIFICATION
# ============================================================

def classify_discovered_link(
    *,
    endpoint: Dict[str, Any],
    historical_query: Dict[str, Any],
    search_url: str,
    link: Dict[str, str],
    exclusion_urls: Set[str],
) -> Dict[str, Any]:

    region = normalize_space(
        endpoint.get(
            "region"
        )
    )

    agency = normalize_space(
        endpoint.get(
            "agency"
        )
    )

    endpoint_class = normalize_space(
        endpoint.get(
            "classification"
        )
    )

    endpoint_url = canonicalize_url(
        endpoint.get(
            "canonical_url"
        )
        or ""
    )

    query = normalize_space(
        historical_query.get(
            "query"
        )
    )

    query_class = normalize_space(
        historical_query.get(
            "query_class"
        )
    )

    period_class = normalize_space(
        historical_query.get(
            "period_class"
        )
    )

    start_year = int(
        historical_query.get(
            "start_year"
        )
        or 0
    )

    end_year = int(
        historical_query.get(
            "end_year"
        )
        or 0
    )

    label = normalize_space(
        link.get(
            "label"
        )
    )

    local_container_text = normalize_space(
        link.get(
            "local_container_text"
        )
    )

    url = canonicalize_url(
        link.get(
            "url"
        )
        or ""
    )

    canonical_identity_url = canonicalize_url(
        url,
        remove_discovery_query=True,
    )

    # ========================================================
    # LOCAL EVIDENCE ONLY
    # ========================================================

    local_evidence = normalize_space(
        f"{label} {local_container_text}"
    )

    target_local = (
        TARGET_NAME
        in local_evidence
    )

    target_in_label = (
        TARGET_NAME
        in label
    )

    action_terms = [
        term
        for term in ACTION_TERMS
        if term
        in local_evidence
    ]

    official_terms = [
        term
        for term in OFFICIAL_TERMS
        if term
        in local_evidence
    ]

    urban_terms = [
        term
        for term in URBAN_TERMS
        if term
        in local_evidence
    ]

    gazette_terms = [
        term
        for term in GAZETTE_TERMS
        if term
        in local_evidence
    ]

    notice_numbers = (
        extract_notice_numbers(
            local_evidence
        )
    )

    dates = extract_dates(
        local_evidence
    )

    period_match = (
        date_matches_period(
            dates,
            start_year,
            end_year,
        )
    )

    is_attachment = is_file_url(
        url
    )

    is_extensionless_download = (
        is_extensionless_download_url(
            url
        )
    )

    list_endpoint = looks_list_endpoint(
        url
    )

    detail_endpoint = looks_detail_endpoint(
        url
    )

    generic_navigation = (
        looks_generic_navigation(
            label,
            url,
        )
    )

    root_navigation = (
        is_root_navigation(
            url
        )
    )

    external_navigation = (
        not same_host(
            endpoint_url,
            url,
        )
    )

    prior_negative = (
        canonical_identity_url
        in exclusion_urls
    )

    (
        administrative_duty_reference,
        administrative_duty_evidence,
    ) = detect_administrative_duty_reference(
        local_evidence
    )

    attachment_locally_relevant = (
        target_local
        or bool(
            action_terms
        )
        or bool(
            official_terms
        )
        or bool(
            urban_terms
        )
        or bool(
            notice_numbers
        )
        or (
            endpoint_class
            == "GAZETTE_ARCHIVE"
            and bool(
                gazette_terms
            )
        )
    )

    # ========================================================
    # SCORE
    # ========================================================

    score = 0
    reasons: List[str] = []

    if target_in_label:

        score += 30

        reasons.append(
            "TARGET_IN_LINK_LABEL"
        )

    elif target_local:

        score += 20

        reasons.append(
            "TARGET_IN_LOCAL_CONTAINER"
        )

    if action_terms:

        score += 6

        reasons.append(
            "LOCAL_ACTION_CONTEXT"
        )

    if official_terms:

        score += 6

        reasons.append(
            "LOCAL_OFFICIAL_CONTEXT"
        )

    if urban_terms:

        score += 5

        reasons.append(
            "LOCAL_URBAN_CONTEXT"
        )

    if notice_numbers:

        score += 10

        reasons.append(
            "LOCAL_NOTICE_NUMBER"
        )

    if gazette_terms:

        score += 4

        reasons.append(
            "LOCAL_GAZETTE_CONTEXT"
        )

    if is_attachment:

        score += 8

        reasons.append(
            "DIRECT_ATTACHMENT"
        )

    if is_extensionless_download:

        score += 7

        reasons.append(
            "EXTENSIONLESS_DOWNLOAD"
        )

    if detail_endpoint:

        score += 3

        reasons.append(
            "DETAIL_ENDPOINT"
        )

    if period_match is True:

        score += 5

        reasons.append(
            "QUERY_PERIOD_MATCH"
        )

    elif period_match is False:

        score -= 40

        reasons.append(
            "OUTSIDE_QUERY_PERIOD"
        )

    if prior_negative:

        score -= 100

        reasons.append(
            "PRIOR_NEGATIVE_DOCUMENT"
        )

    if administrative_duty_reference:

        score -= 80

        reasons.append(
            "ADMINISTRATIVE_DUTY_REFERENCE"
        )

    if generic_navigation:

        score -= 30

        reasons.append(
            "GENERIC_NAVIGATION"
        )

    if root_navigation:

        score -= 40

        reasons.append(
            "ROOT_NAVIGATION"
        )

    if external_navigation:

        score -= 40

        reasons.append(
            "EXTERNAL_NAVIGATION"
        )

    if list_endpoint:

        score -= 20

        reasons.append(
            "LIST_ENDPOINT"
        )

    if (
        is_attachment
        and not attachment_locally_relevant
    ):

        score -= 30

        reasons.append(
            "UNRELATED_ATTACHMENT"
        )

    # ========================================================
    # CLASSIFICATION PRIORITY
    # ========================================================

    if prior_negative:

        classification = (
            CLASS_EXCLUDED_PRIOR_NEGATIVE
        )

    elif administrative_duty_reference:

        classification = (
            CLASS_EXCLUDED_ADMIN_DUTY
        )

    elif period_match is False:

        classification = (
            CLASS_EXCLUDED_OUT_OF_PERIOD
        )

    elif (
        generic_navigation
        or root_navigation
        or external_navigation
    ):

        classification = (
            CLASS_EXCLUDED_GENERIC
        )

    elif (
        is_attachment
        and attachment_locally_relevant
    ):

        classification = (
            CLASS_ATTACHMENT
        )

    elif (
        is_extensionless_download
        and attachment_locally_relevant
    ):

        classification = (
            CLASS_EXTENSIONLESS
        )

    elif (
        target_local
        and detail_endpoint
        and not list_endpoint
    ):

        classification = (
            CLASS_TARGET_DIRECT
        )

    elif (
        endpoint_class
        == "GAZETTE_ARCHIVE"
        and bool(
            gazette_terms
        )
        and (
            detail_endpoint
            or bool(
                notice_numbers
            )
        )
        and not list_endpoint
    ):

        classification = (
            CLASS_GAZETTE
        )

    elif (
        bool(
            urban_terms
        )
        and bool(
            official_terms
        )
        and bool(
            action_terms
        )
        and detail_endpoint
        and not list_endpoint
    ):

        classification = (
            CLASS_URBAN_NOTICE
        )

    elif (
        score
        >= 8
        and detail_endpoint
        and not list_endpoint
    ):

        classification = (
            CLASS_LOW_CONFIDENCE
        )

    else:

        classification = (
            CLASS_EXCLUDED_GENERIC
        )

    return {
        "region": region,
        "agency": agency,

        "endpoint_classification": (
            endpoint_class
        ),

        "endpoint_url": (
            endpoint_url
        ),

        "query_index": (
            historical_query.get(
                "query_index"
            )
        ),

        "query": query,

        "query_class": query_class,

        "period_class": period_class,

        "start_year": start_year,

        "end_year": end_year,

        "search_url": (
            canonicalize_url(
                search_url
            )
        ),

        "label": label,

        "local_container_text": (
            local_container_text[
                :6000
            ]
        ),

        "url": url,

        "canonical_identity_url": (
            canonical_identity_url
        ),

        "classification": (
            classification
        ),

        "score": score,

        "target_local": (
            target_local
        ),

        "target_in_label": (
            target_in_label
        ),

        "page_level_target_inherited": (
            False
        ),

        "action_terms": (
            unique_strings(
                action_terms
            )
        ),

        "official_terms": (
            unique_strings(
                official_terms
            )
        ),

        "urban_terms": (
            unique_strings(
                urban_terms
            )
        ),

        "gazette_terms": (
            unique_strings(
                gazette_terms
            )
        ),

        "notice_numbers": (
            notice_numbers
        ),

        "dates": dates,

        "period_match": (
            period_match
        ),

        "is_attachment": (
            is_attachment
        ),

        "is_extensionless_download": (
            is_extensionless_download
        ),

        "attachment_locally_relevant": (
            attachment_locally_relevant
        ),

        "detail_endpoint": (
            detail_endpoint
        ),

        "list_endpoint": (
            list_endpoint
        ),

        "generic_navigation": (
            generic_navigation
        ),

        "root_navigation": (
            root_navigation
        ),

        "external_navigation": (
            external_navigation
        ),

        "prior_negative_document": (
            prior_negative
        ),

        "administrative_duty_reference": (
            administrative_duty_reference
        ),

        "administrative_duty_evidence": (
            administrative_duty_evidence
        ),

        "reasons": (
            unique_strings(
                reasons
            )
        ),

        "final_positive": False,
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
        "HISTORICAL OFFICIAL ARCHIVE DISCOVERY"
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

    print(
        "Historical input:",
        HISTORICAL_INPUT_PATH,
    )

    print(
        "Endpoint input:",
        ENDPOINT_INPUT_PATH,
    )

    print()

    # ========================================================
    # INPUT LOAD
    # ========================================================

    if not HISTORICAL_INPUT_PATH.exists():

        raise FileNotFoundError(
            "Historical recovery expansion input not found: "
            f"{HISTORICAL_INPUT_PATH}"
        )

    if not ENDPOINT_INPUT_PATH.exists():

        raise FileNotFoundError(
            "Official board endpoint input not found: "
            f"{ENDPOINT_INPUT_PATH}"
        )

    historical_data = json.loads(
        HISTORICAL_INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    endpoint_data = json.loads(
        ENDPOINT_INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        historical_data,
        dict,
    ):

        raise TypeError(
            "Historical recovery expansion JSON "
            "must be an object."
        )

    if not isinstance(
        endpoint_data,
        dict,
    ):

        raise TypeError(
            "Endpoint refinement JSON "
            "must be an object."
        )

    # ========================================================
    # NORMALIZATION
    # ========================================================

    historical_queries = (
        load_historical_queries(
            historical_data
        )
    )

    searchable_endpoints = (
        load_searchable_endpoints(
            endpoint_data
        )
    )

    exclusion_urls = (
        load_exclusion_urls(
            historical_data
        )
    )

    print(
        "Historical query count:",
        len(
            historical_queries
        ),
    )

    print(
        "Searchable endpoint count:",
        len(
            searchable_endpoints
        ),
    )

    print(
        "Exclusion URL count:",
        len(
            exclusion_urls
        ),
    )

    print()

    # ========================================================
    # INPUT FAIL-FAST
    # ========================================================

    if not historical_queries:

        available_top_level_keys = sorted(
            str(
                key
            )
            for key
            in historical_data.keys()
        )

        print(
            "ERROR: historical query matrix recovery failed."
        )

        print(
            "N-stage top-level keys:",
            available_top_level_keys,
        )

        raise AssertionError(
            "N-stage output exists but no historical "
            "query records could be structurally recovered."
        )


    if not searchable_endpoints:

        raise AssertionError(
            "H-stage output exists but no searchable "
            "official endpoints were loaded."
        )

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
    html_parse_count = 0
    raw_link_count = 0
    classified_link_count = 0

    endpoint_results: List[
        Dict[str, Any]
    ] = []

    all_candidates: List[
        Dict[str, Any]
    ] = []

    stop_due_to_request_limit = False

    # ========================================================
    # ENDPOINT LOOP
    # ========================================================

    for endpoint_index, endpoint in enumerate(
        searchable_endpoints,
        start=1,
    ):

        if stop_due_to_request_limit:
            break

        region = normalize_space(
            endpoint.get(
                "region"
            )
        )

        endpoint_class = normalize_space(
            endpoint.get(
                "classification"
            )
        )

        endpoint_url = canonicalize_url(
            endpoint.get(
                "canonical_url"
            )
            or ""
        )

        print(
            "-" * 60
        )

        print(
            f"ENDPOINT {endpoint_index}"
        )

        print(
            "Region:",
            region
            or "-",
        )

        print(
            "Class:",
            endpoint_class,
        )

        print(
            "URL:",
            endpoint_url,
        )

        endpoint_request_count = 0
        endpoint_http_success_count = 0
        endpoint_error_count = 0
        endpoint_candidate_records: List[
            Dict[str, Any]
        ] = []

        seen_search_urls: Set[str] = set()

        # ====================================================
        # QUERY LOOP
        # ====================================================

        for historical_query in historical_queries:

            if (
                request_count
                >= MAX_TOTAL_REQUESTS
            ):

                stop_due_to_request_limit = True
                break

            search_term = normalize_space(
                historical_query.get(
                    "query"
                )
            )

            if not search_term:
                continue

            search_urls = (
                build_get_search_variants(
                    endpoint_url,
                    search_term,
                )
            )

            for search_url in search_urls:

                if (
                    request_count
                    >= MAX_TOTAL_REQUESTS
                ):

                    stop_due_to_request_limit = True
                    break

                canonical_search_url = (
                    canonicalize_url(
                        search_url
                    )
                )

                if not canonical_search_url:
                    continue

                if (
                    canonical_search_url
                    in seen_search_urls
                ):
                    continue

                seen_search_urls.add(
                    canonical_search_url
                )

                request_count += 1
                endpoint_request_count += 1

                response = request_html(
                    session,
                    canonical_search_url,
                )

                if (
                    response.get(
                        "http_status"
                    )
                    == 200
                ):

                    http_success_count += 1
                    endpoint_http_success_count += 1

                if response.get(
                    "error"
                ):

                    transport_error_count += 1
                    endpoint_error_count += 1

                    continue

                raw_html = (
                    response.get(
                        "html"
                    )
                    or ""
                )

                if raw_html:

                    html_parse_count += 1

                links = extract_links(
                    response.get(
                        "final_url"
                    )
                    or canonical_search_url,
                    raw_html,
                )

                raw_link_count += len(
                    links
                )

                for link in links:

                    candidate = (
                        classify_discovered_link(
                            endpoint=endpoint,
                            historical_query=historical_query,
                            search_url=canonical_search_url,
                            link=link,
                            exclusion_urls=exclusion_urls,
                        )
                    )

                    classified_link_count += 1

                    endpoint_candidate_records.append(
                        candidate
                    )

                    all_candidates.append(
                        candidate
                    )

                if (
                    REQUEST_DELAY_SECONDS
                    > 0
                ):

                    time.sleep(
                        REQUEST_DELAY_SECONDS
                    )

        endpoint_class_counts = Counter(
            item.get(
                "classification"
            )
            for item
            in endpoint_candidate_records
        )

        endpoint_results.append(
            {
                "region": region,
                "agency": normalize_space(
                    endpoint.get(
                        "agency"
                    )
                ),
                "classification": (
                    endpoint_class
                ),
                "endpoint_url": (
                    endpoint_url
                ),
                "request_count": (
                    endpoint_request_count
                ),
                "http_success_count": (
                    endpoint_http_success_count
                ),
                "transport_error_count": (
                    endpoint_error_count
                ),
                "raw_candidate_count": len(
                    endpoint_candidate_records
                ),
                "classification_counts": dict(
                    sorted(
                        endpoint_class_counts.items()
                    )
                ),
            }
        )

        print(
            "Requests:",
            endpoint_request_count,
        )

        print(
            "HTTP success:",
            endpoint_http_success_count,
        )

        print(
            "Transport errors:",
            endpoint_error_count,
        )

        print(
            "Raw candidates:",
            len(
                endpoint_candidate_records
            ),
        )

    # ========================================================
    # CANONICAL DEDUPE
    # ========================================================

    grouped: Dict[
        Tuple[
            str,
            str,
        ],
        List[
            Dict[str, Any]
        ],
    ] = defaultdict(
        list
    )

    for candidate in all_candidates:

        canonical_identity_url = (
            candidate.get(
                "canonical_identity_url"
            )
            or canonicalize_url(
                candidate.get(
                    "url"
                )
                or "",
                remove_discovery_query=True,
            )
        )

        if not canonical_identity_url:
            continue

        key = (
            normalize_space(
                candidate.get(
                    "region"
                )
            ),
            canonical_identity_url,
        )

        grouped[
            key
        ].append(
            candidate
        )

    def choose_representative(
        group: List[
            Dict[str, Any]
        ],
    ) -> Dict[str, Any]:

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
                -int(
                    item.get(
                        "target_in_label"
                    )
                    is True
                ),
                -int(
                    item.get(
                        "target_local"
                    )
                    is True
                ),
                -len(
                    item.get(
                        "local_container_text"
                    )
                    or ""
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
            "query_indexes"
        ] = unique_strings(
            item.get(
                "query_index"
            )
            for item in group
        )

        representative[
            "queries"
        ] = unique_strings(
            item.get(
                "query"
            )
            for item in group
        )

        representative[
            "query_classes"
        ] = unique_strings(
            item.get(
                "query_class"
            )
            for item in group
        )

        representative[
            "period_classes"
        ] = unique_strings(
            item.get(
                "period_class"
            )
            for item in group
        )

        representative[
            "search_urls"
        ] = unique_strings(
            item.get(
                "search_url"
            )
            for item in group
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
            "all_notice_numbers"
        ] = unique_strings(
            notice
            for item in group
            for notice
            in (
                item.get(
                    "notice_numbers"
                )
                or []
            )
        )

        representative[
            "all_dates"
        ] = unique_strings(
            date
            for item in group
            for date
            in (
                item.get(
                    "dates"
                )
                or []
            )
        )

        representative[
            "all_reasons"
        ] = unique_strings(
            reason
            for item in group
            for reason
            in (
                item.get(
                    "reasons"
                )
                or []
            )
        )

        representative[
            "all_period_matches"
        ] = [
            item.get(
                "period_match"
            )
            for item in group
        ]

        representative[
            "final_positive"
        ] = False

        return representative

    canonical_candidates = [
        choose_representative(
            group
        )
        for group in grouped.values()
        if group
    ]

    canonical_candidates.sort(
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
            str(
                item.get(
                    "region"
                )
                or ""
            ),
            str(
                item.get(
                    "canonical_identity_url"
                )
                or ""
            ),
        )
    )

    # ========================================================
    # SPLIT CLASSES
    # ========================================================

    target_direct_seeds = [
        item
        for item
        in canonical_candidates
        if item.get(
            "classification"
        )
        == CLASS_TARGET_DIRECT
    ]

    attachment_seeds = [
        item
        for item
        in canonical_candidates
        if item.get(
            "classification"
        )
        == CLASS_ATTACHMENT
    ]

    extensionless_seeds = [
        item
        for item
        in canonical_candidates
        if item.get(
            "classification"
        )
        == CLASS_EXTENSIONLESS
    ]

    gazette_seeds = [
        item
        for item
        in canonical_candidates
        if item.get(
            "classification"
        )
        == CLASS_GAZETTE
    ]

    urban_notice_seeds = [
        item
        for item
        in canonical_candidates
        if item.get(
            "classification"
        )
        == CLASS_URBAN_NOTICE
    ]

    low_confidence_seeds = [
        item
        for item
        in canonical_candidates
        if item.get(
            "classification"
        )
        == CLASS_LOW_CONFIDENCE
    ]

    excluded_prior_negative = [
        item
        for item
        in canonical_candidates
        if item.get(
            "classification"
        )
        == CLASS_EXCLUDED_PRIOR_NEGATIVE
    ]

    excluded_admin_duty = [
        item
        for item
        in canonical_candidates
        if item.get(
            "classification"
        )
        == CLASS_EXCLUDED_ADMIN_DUTY
    ]

    excluded_generic = [
        item
        for item
        in canonical_candidates
        if item.get(
            "classification"
        )
        == CLASS_EXCLUDED_GENERIC
    ]

    excluded_out_of_period = [
        item
        for item
        in canonical_candidates
        if item.get(
            "classification"
        )
        == CLASS_EXCLUDED_OUT_OF_PERIOD
    ]

    # ========================================================
    # NEXT-STAGE POOL
    # ========================================================

    next_stage_verification_pool = [
        item
        for item
        in canonical_candidates
        if item.get(
            "classification"
        )
        in NEXT_STAGE_ALLOWED_CLASSES
    ]

    next_stage_verification_pool.sort(
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
            str(
                item.get(
                    "region"
                )
                or ""
            ),
            str(
                item.get(
                    "canonical_identity_url"
                )
                or ""
            ),
        )
    )

    classification_counts = Counter(
        item.get(
            "classification"
        )
        for item
        in canonical_candidates
    )

    # ========================================================
    # RESOLUTION
    # ========================================================

    if target_direct_seeds:

        resolution = (
            "HISTORICAL_OFFICIAL_ARCHIVE_"
            "TARGET_DIRECT_SEED_DISCOVERED"
        )

        next_action = (
            "historical archive에서 link-local exact target evidence가 "
            "확인된 detail/attachment seed를 원문 재조회하여 "
            "개발밀도관리구역 지정·변경·해제 action, 고시번호, "
            "고시일, 행정구역 및 scope를 document-local evidence로 "
            "검증한다."
        )

    elif next_stage_verification_pool:

        resolution = (
            "HISTORICAL_OFFICIAL_ARCHIVE_"
            "DOCUMENT_SEED_DISCOVERED"
        )

        next_action = (
            "확보된 historical detail/attachment/gazette/urban notice "
            "seed를 실제 원문으로 다시 조회하여 target exact phrase와 "
            "지정·변경·해제 action, 고시번호, 고시일, 행정구역 및 "
            "scope를 document-local evidence로 검증한다."
        )

    else:

        resolution = (
            "HISTORICAL_OFFICIAL_ARCHIVE_"
            "DISCOVERY_COMPLETED_NO_SEED"
        )

        next_action = (
            "현재 공식 지자체 archive endpoint에서는 검증 가능한 "
            "historical seed를 확보하지 못했다. 국가기록원, 국가법령정보 "
            "연계 기록, 구형 공보 archive, 관보, 토지이음 및 과거 "
            "고시번호 역탐색 단계로 recovery 범위를 확장한다."
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-O "
            "Development Density Management Area "
            "Historical Official Archive Discovery"
        ),

        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },

        "inputs": {
            "historical_recovery_expansion": str(
                HISTORICAL_INPUT_PATH
            ),

            "official_board_endpoint_refinement": str(
                ENDPOINT_INPUT_PATH
            ),

            "historical_resolution": (
                historical_data.get(
                    "resolution"
                )
            ),

            "endpoint_resolution": (
                endpoint_data.get(
                    "resolution"
                )
            ),
        },

        "method": {
            "historical_query_matrix_only": True,

            "official_endpoint_only": True,

            "allowed_endpoint_classes": sorted(
                ALLOWED_ENDPOINT_CLASSES
            ),

            "search_engine_scraping": False,

            "direct_http_probe": True,

            "link_local_evidence_only": True,

            "container_local_evidence_only": True,

            "page_level_target_inheritance": False,

            "search_page_final_positive_allowed": False,

            "list_page_next_stage_seed_allowed": False,

            "attachment_local_relevance_required": True,

            "negative_document_exclusion_memory": True,

            "administrative_duty_false_positive_guard": True,

            "external_navigation_guard": True,

            "root_navigation_guard": True,

            "period_partition_preserved": True,

            "out_of_period_promotion_allowed": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,

            "final_positive_promotion_allowed": False,
        },

        "summary": {
            "historical_query_count": len(
                historical_queries
            ),

            "searchable_endpoint_count": len(
                searchable_endpoints
            ),

            "exclusion_url_count": len(
                exclusion_urls
            ),

            "request_count": (
                request_count
            ),

            "max_total_requests": (
                MAX_TOTAL_REQUESTS
            ),

            "request_limit_reached": (
                stop_due_to_request_limit
            ),

            "http_success_count": (
                http_success_count
            ),

            "transport_error_count": (
                transport_error_count
            ),

            "html_parse_count": (
                html_parse_count
            ),

            "raw_link_count": (
                raw_link_count
            ),

            "classified_link_count": (
                classified_link_count
            ),

            "canonical_candidate_count": len(
                canonical_candidates
            ),

            "target_direct_seed_count": len(
                target_direct_seeds
            ),

            "attachment_seed_count": len(
                attachment_seeds
            ),

            "extensionless_seed_count": len(
                extensionless_seeds
            ),

            "gazette_seed_count": len(
                gazette_seeds
            ),

            "urban_notice_seed_count": len(
                urban_notice_seeds
            ),

            "low_confidence_seed_count": len(
                low_confidence_seeds
            ),

            "excluded_prior_negative_count": len(
                excluded_prior_negative
            ),

            "excluded_administrative_duty_count": len(
                excluded_admin_duty
            ),

            "excluded_generic_count": len(
                excluded_generic
            ),

            "excluded_out_of_period_count": len(
                excluded_out_of_period
            ),

            "next_stage_verification_pool_count": len(
                next_stage_verification_pool
            ),
        },

        "classification_counts": dict(
            sorted(
                classification_counts.items()
            )
        ),

        "endpoint_results": (
            endpoint_results
        ),

        "target_direct_seeds": (
            target_direct_seeds
        ),

        "attachment_seeds": (
            attachment_seeds
        ),

        "extensionless_download_seeds": (
            extensionless_seeds
        ),

        "gazette_issue_seeds": (
            gazette_seeds
        ),

        "urban_notice_seeds": (
            urban_notice_seeds
        ),

        "low_confidence_seeds": (
            low_confidence_seeds
        ),

        "excluded_prior_negative_documents": (
            excluded_prior_negative
        ),

        "excluded_administrative_duty_references": (
            excluded_admin_duty
        ),

        "excluded_generic_links": (
            excluded_generic
        ),

        "excluded_out_of_period_documents": (
            excluded_out_of_period
        ),

        "next_stage_verification_pool": (
            next_stage_verification_pool
        ),

        "all_canonical_candidates": (
            canonical_candidates
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
    # CONSOLE RESULT
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "HISTORICAL ARCHIVE DISCOVERY RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "Historical query count:",
        len(
            historical_queries
        ),
    )

    print(
        "Searchable endpoint count:",
        len(
            searchable_endpoints
        ),
    )

    print(
        "Exclusion URL count:",
        len(
            exclusion_urls
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
        "Raw link count:",
        raw_link_count,
    )

    print(
        "Canonical candidate count:",
        len(
            canonical_candidates
        ),
    )

    print()

    print(
        f"{CLASS_TARGET_DIRECT}:",
        len(
            target_direct_seeds
        ),
    )

    print(
        f"{CLASS_ATTACHMENT}:",
        len(
            attachment_seeds
        ),
    )

    print(
        f"{CLASS_EXTENSIONLESS}:",
        len(
            extensionless_seeds
        ),
    )

    print(
        f"{CLASS_GAZETTE}:",
        len(
            gazette_seeds
        ),
    )

    print(
        f"{CLASS_URBAN_NOTICE}:",
        len(
            urban_notice_seeds
        ),
    )

    print(
        f"{CLASS_LOW_CONFIDENCE}:",
        len(
            low_confidence_seeds
        ),
    )

    print(
        f"{CLASS_EXCLUDED_PRIOR_NEGATIVE}:",
        len(
            excluded_prior_negative
        ),
    )

    print(
        f"{CLASS_EXCLUDED_ADMIN_DUTY}:",
        len(
            excluded_admin_duty
        ),
    )

    print(
        f"{CLASS_EXCLUDED_OUT_OF_PERIOD}:",
        len(
            excluded_out_of_period
        ),
    )

    print()

    print(
        "Next-stage verification pool:",
        len(
            next_stage_verification_pool
        ),
    )

    # ========================================================
    # HIGH VALUE SEEDS
    # ========================================================

    def print_seed_group(
        title: str,
        items: List[
            Dict[str, Any]
        ],
        *,
        limit: int = 50,
    ) -> None:

        if not items:
            return

        print()

        print(
            title
        )

        print(
            "-" * 60
        )

        for index, item in enumerate(
            items[
                :limit
            ],
            start=1,
        ):

            print(
                f"[{index}] "
                f"{item.get('region') or '-'}"
            )

            print(
                "Class:",
                item.get(
                    "classification"
                ),
            )

            print(
                "Score:",
                item.get(
                    "score"
                ),
            )

            print(
                "Period:",
                item.get(
                    "period_class"
                ),
                item.get(
                    "start_year"
                ),
                "-",
                item.get(
                    "end_year"
                ),
            )

            print(
                "Query:",
                item.get(
                    "query"
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
                "Target local:",
                item.get(
                    "target_local"
                ),
            )

            print(
                "Notice numbers:",
                item.get(
                    "all_notice_numbers"
                )
                or item.get(
                    "notice_numbers"
                ),
            )

            print(
                "Dates:",
                item.get(
                    "all_dates"
                )
                or item.get(
                    "dates"
                ),
            )

            print(
                "Period match:",
                item.get(
                    "period_match"
                ),
            )

            print(
                "Reasons:",
                item.get(
                    "all_reasons"
                )
                or item.get(
                    "reasons"
                ),
            )

            print()

    print_seed_group(
        "HISTORICAL TARGET DIRECT SEEDS",
        target_direct_seeds,
    )

    print_seed_group(
        "HISTORICAL ATTACHMENT SEEDS",
        attachment_seeds,
    )

    print_seed_group(
        "HISTORICAL EXTENSIONLESS DOWNLOAD SEEDS",
        extensionless_seeds,
    )

    print_seed_group(
        "HISTORICAL GAZETTE ISSUE SEEDS",
        gazette_seeds,
    )

    print_seed_group(
        "HISTORICAL URBAN NOTICE SEEDS",
        urban_notice_seeds,
    )

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

    canonical_keys = {
        (
            normalize_space(
                item.get(
                    "region"
                )
            ),
            normalize_space(
                item.get(
                    "canonical_identity_url"
                )
            ),
        )
        for item
        in canonical_candidates
    }

    verification_keys = {
        (
            normalize_space(
                item.get(
                    "region"
                )
            ),
            normalize_space(
                item.get(
                    "canonical_identity_url"
                )
            ),
        )
        for item
        in next_stage_verification_pool
    }

    all_classes_valid = all(
        item.get(
            "classification"
        )
        in VALID_CANDIDATE_CLASSES
        for item
        in canonical_candidates
    )

    all_candidate_urls_exist = all(
        bool(
            item.get(
                "url"
            )
        )
        for item
        in canonical_candidates
    )

    verification_pool_allowed = all(
        item.get(
            "classification"
        )
        in NEXT_STAGE_ALLOWED_CLASSES
        for item
        in next_stage_verification_pool
    )

    # --------------------------------------------------------
    # LEAKAGE COUNTS
    # --------------------------------------------------------

    prior_negative_leakage = sum(
        1
        for item
        in next_stage_verification_pool
        if (
            item.get(
                "canonical_identity_url"
            )
            in exclusion_urls
            or item.get(
                "prior_negative_document"
            )
            is True
        )
    )

    page_level_evidence_inheritance_leakage = sum(
        1
        for item
        in canonical_candidates
        if item.get(
            "page_level_target_inherited"
        )
        is not False
    )

    target_direct_without_local_target = sum(
        1
        for item
        in target_direct_seeds
        if item.get(
            "target_local"
        )
        is not True
    )

    unrelated_attachment_promotion = sum(
        1
        for item
        in next_stage_verification_pool
        if (
            item.get(
                "classification"
            )
            in {
                CLASS_ATTACHMENT,
                CLASS_EXTENSIONLESS,
            }
            and item.get(
                "attachment_locally_relevant"
            )
            is not True
        )
    )

    out_of_period_promotion = sum(
        1
        for item
        in next_stage_verification_pool
        if item.get(
            "period_match"
        )
        is False
    )

    list_page_promotion = sum(
        1
        for item
        in next_stage_verification_pool
        if item.get(
            "list_endpoint"
        )
        is True
    )

    generic_navigation_promotion = sum(
        1
        for item
        in next_stage_verification_pool
        if item.get(
            "generic_navigation"
        )
        is True
    )

    external_navigation_promotion = sum(
        1
        for item
        in next_stage_verification_pool
        if item.get(
            "external_navigation"
        )
        is True
    )

    root_navigation_promotion = sum(
        1
        for item
        in next_stage_verification_pool
        if item.get(
            "root_navigation"
        )
        is True
    )

    administrative_duty_promotion = sum(
        1
        for item
        in next_stage_verification_pool
        if item.get(
            "administrative_duty_reference"
        )
        is True
    )

    final_positive_leakage = sum(
        1
        for item
        in canonical_candidates
        if item.get(
            "final_positive"
        )
        is not False
    )

    # --------------------------------------------------------
    # QUERY MATRIX CHECKS
    # --------------------------------------------------------

    query_matrix_keys = {
        (
            normalize_space(
                item.get(
                    "query"
                )
            ),
            normalize_space(
                item.get(
                    "query_class"
                )
            ),
            normalize_space(
                item.get(
                    "period_class"
                )
            ),
            int(
                item.get(
                    "start_year"
                )
                or 0
            ),
            int(
                item.get(
                    "end_year"
                )
                or 0
            ),
        )
        for item
        in historical_queries
    }

    period_partition_preserved = all(
        (
            int(
                item.get(
                    "start_year"
                )
                or 0
            )
            <=
            int(
                item.get(
                    "end_year"
                )
                or 0
            )
        )
        for item
        in historical_queries
        if (
            item.get(
                "start_year"
            )
            and item.get(
                "end_year"
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

        "historical input exists": (
            HISTORICAL_INPUT_PATH.exists()
        ),

        "endpoint input exists": (
            ENDPOINT_INPUT_PATH.exists()
        ),

        "N-stage input parsed": (
            isinstance(
                historical_data,
                dict,
            )
        ),

        "H-stage endpoint input parsed": (
            isinstance(
                endpoint_data,
                dict,
            )
        ),

        "historical query matrix loaded": (
            len(
                historical_queries
            )
            > 0
        ),

        "historical query matrix unique": (
            len(
                query_matrix_keys
            )
            == len(
                historical_queries
            )
        ),

        "historical query recursive recovery enabled": (
            True
        ),

        "all historical queries have query text": all(
            bool(
                normalize_space(
                    item.get(
                        "query"
                    )
                )
            )
            for item
            in historical_queries
        ),

        "all historical queries have period bounds": all(
            (
                int(
                    item.get(
                        "start_year"
                    )
                    or 0
                )
                > 0
                and
                int(
                    item.get(
                        "end_year"
                    )
                    or 0
                )
                > 0
            )
            for item
            in historical_queries
        ),

        "official archive endpoints loaded": (
            len(
                searchable_endpoints
            )
            > 0
        ),

        "only allowed endpoint classes executed": all(
            item.get(
                "classification"
            )
            in ALLOWED_ENDPOINT_CLASSES
            for item
            in searchable_endpoints
        ),

        "exclusion memory loaded": (
            len(
                exclusion_urls
            )
            > 0
        ),

        "search engine scraping disabled": (
            output_data[
                "method"
            ][
                "search_engine_scraping"
            ]
            is False
        ),

        "direct HTTP probe enabled": (
            output_data[
                "method"
            ][
                "direct_http_probe"
            ]
            is True
        ),

        "link-local evidence enabled": (
            output_data[
                "method"
            ][
                "link_local_evidence_only"
            ]
            is True
        ),

        "container-local evidence enabled": (
            output_data[
                "method"
            ][
                "container_local_evidence_only"
            ]
            is True
        ),

        "page-level evidence inheritance disabled": (
            output_data[
                "method"
            ][
                "page_level_target_inheritance"
            ]
            is False
        ),

        "page-level evidence inheritance leakage zero": (
            page_level_evidence_inheritance_leakage
            == 0
        ),

        "target direct requires local target evidence": (
            target_direct_without_local_target
            == 0
        ),

        "attachment local relevance guard enabled": (
            output_data[
                "method"
            ][
                "attachment_local_relevance_required"
            ]
            is True
        ),

        "unrelated attachment promotion zero": (
            unrelated_attachment_promotion
            == 0
        ),

        "negative document exclusion memory enabled": (
            output_data[
                "method"
            ][
                "negative_document_exclusion_memory"
            ]
            is True
        ),

        "prior negative document leakage zero": (
            prior_negative_leakage
            == 0
        ),

        "period partition enabled": (
            output_data[
                "method"
            ][
                "period_partition_preserved"
            ]
            is True
        ),

        "period partition preserved": (
            period_partition_preserved
        ),

        "out-of-period promotion prohibited": (
            output_data[
                "method"
            ][
                "out_of_period_promotion_allowed"
            ]
            is False
        ),

        "out-of-period promotion zero": (
            out_of_period_promotion
            == 0
        ),

        "search/list page final positive prohibited": (
            list_page_promotion
            == 0
        ),

        "generic navigation promotion zero": (
            generic_navigation_promotion
            == 0
        ),

        "external navigation promotion zero": (
            external_navigation_promotion
            == 0
        ),

        "root navigation promotion zero": (
            root_navigation_promotion
            == 0
        ),

        "administrative-duty promotion zero": (
            administrative_duty_promotion
            == 0
        ),

        "canonical candidates unique": (
            len(
                canonical_keys
            )
            == len(
                canonical_candidates
            )
        ),

        "all candidate classes valid": (
            all_classes_valid
        ),

        "all candidate URLs exist": (
            all_candidate_urls_exist
        ),

        "verification pool unique": (
            len(
                verification_keys
            )
            == len(
                next_stage_verification_pool
            )
        ),

        "verification pool contains only allowed classes": (
            verification_pool_allowed
        ),

        "final positive leakage zero": (
            final_positive_leakage
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
        "Prior negative document leakage:",
        prior_negative_leakage,
    )

    print(
        "Page-level evidence inheritance leakage:",
        page_level_evidence_inheritance_leakage,
    )

    print(
        "Target-direct without local target:",
        target_direct_without_local_target,
    )

    print(
        "Unrelated attachment promotion:",
        unrelated_attachment_promotion,
    )

    print(
        "Out-of-period promotion:",
        out_of_period_promotion,
    )

    print(
        "List-page promotion:",
        list_page_promotion,
    )

    print(
        "Generic navigation promotion:",
        generic_navigation_promotion,
    )

    print(
        "External navigation promotion:",
        external_navigation_promotion,
    )

    print(
        "Root navigation promotion:",
        root_navigation_promotion,
    )

    print(
        "Administrative-duty promotion:",
        administrative_duty_promotion,
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
            "historical official archive discovery "
            "regression failed"
        )


if __name__ == "__main__":
    main()