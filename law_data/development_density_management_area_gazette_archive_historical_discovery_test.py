# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-R

Development Density Management Area
Official Gazette Archive Historical Discovery

목표
======================================================================
개발밀도관리구역의 실제 지정 / 변경 / 해제 고시를 찾기 위해
앞 단계에서 확인된 공식 공보 / 시보 / 구보 archive를 직접 탐색한다.

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

입력
======================================================================
STEP 17-21-C-16-8-H 단계의
official board endpoint refinement 결과를 사용한다.

특히 classification == GAZETTE_ARCHIVE 인 endpoint를 대상으로 한다.

탐색 구조
======================================================================
GAZETTE_ARCHIVE endpoint
    ↓
archive 첫 페이지
    ↓
검색 form / pagination 구조
    ↓
과거 페이지 직접 탐색
    ↓
상세 게시물 URL
    ↓
PDF / HWP / HWPX / filePreview / download endpoint
    ↓
target text / 고시 문맥 seed 확보
    ↓
다음 원문 검증 단계

핵심 안전정책
======================================================================
1. archive 목록 페이지 자체는 최종 positive document가 아니다.

2. 목록/검색 페이지에 "개발밀도관리구역"이 있어도
   실제 상세 문서 또는 첨부 원문 검증 전에는
   VERIFIED_POSITIVE로 승격하지 않는다.

3. PDF / HWP / HWPX / download endpoint는
   원문 검증용 seed로만 저장한다.

4. 최근 페이지만 확인하고 SITE FALSE로 판단하지 않는다.

5. archive historical traversal에서 target을 발견하지 못해도
   SITE FALSE로 판단하지 않는다.

6. runtime spatial condition 등록은 계속 차단한다.

7. VWorld LT_C_UQ141을 UQQ700 dataset으로 확정하지 않는다.

8. 개발밀도관리구역은 실제 공식 원문이 확인될 때까지
   UNKNOWN / UNRESOLVED 상태를 유지한다.

이번 단계의 성공
======================================================================
다음 중 하나면 성공이다.

A.
공보 archive의 historical pagination 구조를 확인하고
실제 과거 상세 게시물 또는 첨부파일 seed를 확보

B.
공보 archive historical traversal 구조가 정상 실행되고
target candidate 0건 상태를 명시적으로 보존

즉 discovery regression이므로
candidate 0건도 테스트 실패가 아니다.
"""

from __future__ import annotations

import html
import json
import re
import time

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
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

INPUT_PATH = (
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
        "gazette_archive_historical_discovery.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = (
    "개발밀도관리구역"
)

STANDARD_CODE = (
    "UQQ700"
)


# ============================================================
# REQUEST CONFIG
# ============================================================

REQUEST_TIMEOUT = 20

REQUEST_SLEEP = 0.20

MAX_CONTENT_LENGTH = (
    2_000_000
)

MAX_ARCHIVE_ENDPOINTS = (
    30
)

MAX_HISTORICAL_PAGES_PER_ENDPOINT = (
    20
)

MAX_LINKS_PER_PAGE = (
    300
)

MAX_DETAIL_SEEDS_PER_ENDPOINT = (
    80
)

MAX_ATTACHMENT_SEEDS_PER_ENDPOINT = (
    100
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": (
        "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
}


# ============================================================
# CONSTANTS
# ============================================================

ALLOWED_INPUT_CLASS = (
    "GAZETTE_ARCHIVE"
)

ATTACHMENT_EXTENSIONS = (
    ".pdf",
    ".hwp",
    ".hwpx",
)

DETAIL_URL_HINTS = [
    "/view",
    "view.do",
    "detail",
    "selectBoardArticle",
    "selectBoardArticle.do",
    "bbsMsgDetail",
    "post/view",
    "board/view",
    "article",
    "read",
    "content",
]

DOWNLOAD_HINTS = [
    "download",
    "filedownload",
    "fileDownload",
    "fileDown",
    "atchfile",
    "attach",
    "filePreview",
    "preview",
    "fileSn",
    "atchFileId",
]

PAGINATION_PARAM_HINTS = [
    "page",
    "pageindex",
    "pageidx",
    "pageno",
    "pagenum",
    "curpage",
    "cpage",
    "gotopage",
    "srchpage",
    "viewpage",
]

YEAR_PARAM_HINTS = [
    "year",
    "searchyear",
    "srchyear",
    "yyyy",
]

GAZETTE_TERMS = [
    "공보",
    "시보",
    "구보",
    "군보",
    "도보",
]

NOTICE_TERMS = [
    "고시",
    "공고",
    "지정",
    "변경",
    "해제",
    "도시관리계획",
    "도시계획",
    "결정",
    "지형도면",
]

SEARCH_URL_HINTS = [
    "/search",
    "search.",
    "search/",
    "search?",
    "totalsearch",
]

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "jsessionid",
    "timestamp",
    "_",
}


# ============================================================
# DATA CLASS
# ============================================================

@dataclass
class FetchResult:
    url: str
    http_status: Optional[int]
    content_type: str
    text: str
    error: Optional[str]
    final_url: Optional[str]


# ============================================================
# TEXT UTIL
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


def strip_html(
    source: str,
) -> str:

    value = re.sub(
        r"(?is)<script[^>]*>.*?</script>",
        " ",
        source,
    )

    value = re.sub(
        r"(?is)<style[^>]*>.*?</style>",
        " ",
        value,
    )

    value = re.sub(
        r"(?is)<[^>]+>",
        " ",
        value,
    )

    value = html.unescape(
        value
    )

    return normalize_space(
        value
    )


def compact_text(
    value: str,
) -> str:

    return re.sub(
        r"\s+",
        "",
        normalize_space(
            value
        ),
    )


def contains_target(
    value: str,
) -> bool:

    return (
        compact_text(
            TARGET_NAME
        )
        in compact_text(
            value
        )
    )


def contains_notice_context(
    value: str,
) -> bool:

    text = normalize_space(
        value
    )

    return any(
        term in text
        for term in NOTICE_TERMS
    )


def contains_gazette_context(
    value: str,
) -> bool:

    text = normalize_space(
        value
    )

    return any(
        term in text
        for term in GAZETTE_TERMS
    )


def build_preview(
    value: str,
    *,
    radius: int = 260,
) -> str:

    text = normalize_space(
        value
    )

    variants = [
        TARGET_NAME,
        "개발밀도 관리구역",
        "개발 밀도 관리구역",
    ]

    index = -1

    for variant in variants:

        index = text.find(
            variant
        )

        if index >= 0:
            break

    if index < 0:

        return text[
            : radius * 2
        ]

    start = max(
        0,
        index - radius,
    )

    end = min(
        len(text),
        index
        + len(TARGET_NAME)
        + radius,
    )

    return text[
        start:end
    ]


# ============================================================
# URL UTIL
# ============================================================

def normalize_url(
    url: str,
) -> str:

    value = html.unescape(
        str(
            url
            or ""
        )
    )

    value = value.replace(
        "&amp;",
        "&",
    )

    try:

        parsed = urlparse(
            value
        )

    except Exception:

        return value

    query_items = []

    for key, item_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        lowered = (
            key.lower()
        )

        if lowered in VOLATILE_QUERY_KEYS:

            continue

        if lowered.startswith(
            "utm_"
        ):

            continue

        query_items.append(
            (
                key,
                item_value,
            )
        )

    query_items.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    return urlunparse(
        parsed._replace(
            query=urlencode(
                query_items,
                doseq=True,
            ),
            fragment="",
        )
    )


def same_or_subdomain(
    url: str,
    base_url: str,
) -> bool:

    try:

        target_host = (
            urlparse(
                url
            ).hostname
            or ""
        ).lower()

        base_host = (
            urlparse(
                base_url
            ).hostname
            or ""
        ).lower()

    except Exception:

        return False

    if not (
        target_host
        and base_host
    ):

        return False

    return (
        target_host == base_host
        or target_host.endswith(
            "." + base_host
        )
        or base_host.endswith(
            "." + target_host
        )
    )


def is_search_url(
    url: str,
) -> bool:

    lower = (
        url.lower()
    )

    return any(
        hint.lower() in lower
        for hint in SEARCH_URL_HINTS
    )


def is_attachment_url(
    url: str,
) -> bool:

    parsed = urlparse(
        url
    )

    path = parsed.path.lower()

    if any(
        path.endswith(
            extension
        )
        for extension in ATTACHMENT_EXTENSIONS
    ):

        return True

    lower = url.lower()

    return any(
        hint.lower() in lower
        for hint in DOWNLOAD_HINTS
    )


def get_attachment_extension(
    url: str,
) -> Optional[str]:

    path = (
        urlparse(
            url
        ).path.lower()
    )

    for extension in ATTACHMENT_EXTENSIONS:

        if path.endswith(
            extension
        ):

            return extension[
                1:
            ]

    return None


def is_probably_detail_url(
    url: str,
) -> bool:

    lower = (
        url.lower()
    )

    if is_search_url(
        url
    ):

        return False

    if is_attachment_url(
        url
    ):

        return False

    return any(
        hint.lower() in lower
        for hint in DETAIL_URL_HINTS
    )


# ============================================================
# FETCH
# ============================================================

def fetch_url(
    url: str,
) -> FetchResult:

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

    except requests.RequestException as exc:

        return FetchResult(
            url=url,
            http_status=None,
            content_type="",
            text="",
            error=repr(
                exc
            ),
            final_url=None,
        )

    content_type = (
        response.headers.get(
            "Content-Type",
            "",
        )
        or ""
    )

    content_type_lower = (
        content_type.lower()
    )

    text = ""

    if (
        "text/" in content_type_lower
        or "html" in content_type_lower
        or "xml" in content_type_lower
        or "json" in content_type_lower
    ):

        text = (
            response.text
            or ""
        )

        if (
            len(text)
            > MAX_CONTENT_LENGTH
        ):

            text = text[
                :MAX_CONTENT_LENGTH
            ]

    return FetchResult(
        url=url,
        http_status=response.status_code,
        content_type=content_type,
        text=text,
        error=None,
        final_url=response.url,
    )


# ============================================================
# LINK EXTRACTION
# ============================================================

ANCHOR_PATTERN = re.compile(
    r"""
    <a
    \s+
    [^>]*?
    href
    \s*=\s*
    (?:
        "([^"]+)"
        |
        '([^']+)'
        |
        ([^\s>]+)
    )
    [^>]*>
    (.*?)
    </a>
    """,
    re.IGNORECASE
    | re.DOTALL
    | re.VERBOSE,
)


def extract_links(
    source: str,
    *,
    base_url: str,
) -> List[Dict[str, str]]:

    results = []

    seen = set()

    for match in ANCHOR_PATTERN.finditer(
        source
    ):

        href = (
            match.group(1)
            or match.group(2)
            or match.group(3)
            or ""
        ).strip()

        label = strip_html(
            match.group(4)
            or ""
        )

        if not href:

            continue

        lower = href.lower()

        if lower.startswith(
            (
                "javascript:",
                "mailto:",
                "tel:",
                "#",
            )
        ):

            continue

        absolute = normalize_url(
            urljoin(
                base_url,
                href,
            )
        )

        if not absolute.startswith(
            (
                "http://",
                "https://",
            )
        ):

            continue

        if absolute in seen:

            continue

        seen.add(
            absolute
        )

        results.append(
            {
                "url":
                    absolute,

                "label":
                    label,
            }
        )

        if (
            len(results)
            >= MAX_LINKS_PER_PAGE
        ):

            break

    return results


# ============================================================
# DATE / NOTICE EXTRACTION
# ============================================================

NOTICE_PATTERNS = [

    re.compile(
        r"("
        r"(?:"
        r"서울특별시|부산광역시|대구광역시|인천광역시|"
        r"광주광역시|대전광역시|울산광역시|"
        r"세종특별자치시|경기도|강원특별자치도|"
        r"충청북도|충청남도|전북특별자치도|"
        r"전라남도|경상북도|경상남도|제주특별자치도|"
        r"[가-힣]+시|[가-힣]+군|[가-힣]+구"
        r")"
        r"\s*"
        r"(?:고시|공고)"
        r"\s*제?\s*"
        r"\d{4}"
        r"\s*[-–]\s*"
        r"\d+"
        r"\s*호?"
        r")"
    ),

    re.compile(
        r"("
        r"(?:고시|공고)"
        r"\s*제?\s*"
        r"\d{4}"
        r"\s*[-–]\s*"
        r"\d+"
        r"\s*호?"
        r")"
    ),
]


DATE_PATTERN = re.compile(
    r"(20\d{2})"
    r"[.\-/년]\s*"
    r"(0?[1-9]|1[0-2])"
    r"[.\-/월]\s*"
    r"(0?[1-9]|[12]\d|3[01])"
    r"(?:일)?"
)


def extract_notice_numbers(
    text: str,
) -> List[str]:

    values = []

    seen = set()

    for pattern in NOTICE_PATTERNS:

        for match in pattern.finditer(
            text
        ):

            value = normalize_space(
                match.group(
                    1
                )
            )

            if not value:
                continue

            if value in seen:
                continue

            seen.add(
                value
            )

            values.append(
                value
            )

    return values


def extract_dates(
    text: str,
) -> List[str]:

    values = []

    seen = set()

    for match in DATE_PATTERN.finditer(
        text
    ):

        try:

            year = int(
                match.group(
                    1
                )
            )

            month = int(
                match.group(
                    2
                )
            )

            day = int(
                match.group(
                    3
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        if not (
            1 <= month <= 12
            and 1 <= day <= 31
        ):

            continue

        value = (
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )

        if value in seen:
            continue

        seen.add(
            value
        )

        values.append(
            value
        )

    return values


# ============================================================
# PAGINATION DISCOVERY
# ============================================================

def detect_pagination_params(
    source: str,
) -> List[str]:

    candidates = []

    seen = set()

    patterns = [

        re.compile(
            r"""[?&]([A-Za-z0-9_.-]*page[A-Za-z0-9_.-]*)=""",
            re.IGNORECASE,
        ),

        re.compile(
            r"""name=["']([^"']*page[^"']*)["']""",
            re.IGNORECASE,
        ),
    ]

    for pattern in patterns:

        for match in pattern.finditer(
            source
        ):

            name = (
                match.group(
                    1
                )
                or ""
            ).strip()

            if not name:
                continue

            lower = name.lower()

            if not any(
                hint in lower
                for hint in PAGINATION_PARAM_HINTS
            ):

                continue

            if name in seen:
                continue

            seen.add(
                name
            )

            candidates.append(
                name
            )

    return candidates


def detect_year_params(
    source: str,
) -> List[str]:

    candidates = []

    seen = set()

    pattern = re.compile(
        r"""name=["']([^"']+)["']""",
        re.IGNORECASE,
    )

    for match in pattern.finditer(
        source
    ):

        name = (
            match.group(
                1
            )
            or ""
        ).strip()

        lower = (
            name.lower()
        )

        if not any(
            hint in lower
            for hint in YEAR_PARAM_HINTS
        ):

            continue

        if name in seen:
            continue

        seen.add(
            name
        )

        candidates.append(
            name
        )

    return candidates


def replace_query_param(
    url: str,
    key: str,
    value: Any,
) -> str:

    parsed = urlparse(
        url
    )

    items = []

    found = False

    for item_key, item_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        if item_key == key:

            items.append(
                (
                    item_key,
                    str(
                        value
                    ),
                )
            )

            found = True

        else:

            items.append(
                (
                    item_key,
                    item_value,
                )
            )

    if not found:

        items.append(
            (
                key,
                str(
                    value
                ),
            )
        )

    return normalize_url(
        urlunparse(
            parsed._replace(
                query=urlencode(
                    items,
                    doseq=True,
                )
            )
        )
    )


def build_historical_page_urls(
    base_url: str,
    pagination_params: List[str],
    year_params: List[str],
) -> List[Dict[str, Any]]:

    plans = []

    seen = set()

    # --------------------------------------------------------
    # pagination
    # --------------------------------------------------------

    for parameter in pagination_params[
        :3
    ]:

        for page_number in range(
            2,
            MAX_HISTORICAL_PAGES_PER_ENDPOINT + 1,
        ):

            url = replace_query_param(
                base_url,
                parameter,
                page_number,
            )

            if url in seen:
                continue

            seen.add(
                url
            )

            plans.append(
                {
                    "url":
                        url,

                    "strategy":
                        "PAGINATION",

                    "parameter":
                        parameter,

                    "value":
                        page_number,
                }
            )

    # --------------------------------------------------------
    # year probe
    #
    # 개발밀도관리구역 제도 문서를 고려해
    # 2000년대 초중반까지 대표 연도를 직접 확인한다.
    # --------------------------------------------------------

    historical_years = [
        2020,
        2015,
        2010,
        2008,
        2005,
        2003,
        2000,
    ]

    for parameter in year_params[
        :2
    ]:

        for year in historical_years:

            url = replace_query_param(
                base_url,
                parameter,
                year,
            )

            if url in seen:
                continue

            seen.add(
                url
            )

            plans.append(
                {
                    "url":
                        url,

                    "strategy":
                        "YEAR",

                    "parameter":
                        parameter,

                    "value":
                        year,
                }
            )

    return plans


# ============================================================
# PAGE CLASSIFICATION
# ============================================================

def classify_archive_page(
    *,
    region: str,
    agency: str,
    url: str,
    source: str,
) -> Dict[str, Any]:

    text = strip_html(
        source
    )

    target_found = contains_target(
        text
    )

    notice_context = contains_notice_context(
        text
    )

    gazette_context = contains_gazette_context(
        text
    )

    notice_numbers = extract_notice_numbers(
        text
    )

    dates = extract_dates(
        text
    )

    return {
        "region":
            region,

        "agency":
            agency,

        "url":
            url,

        "target_found":
            target_found,

        "notice_context":
            notice_context,

        "gazette_context":
            gazette_context,

        "notice_numbers":
            notice_numbers,

        "dates":
            dates,

        "preview":
            (
                build_preview(
                    text
                )
                if target_found
                else ""
            ),

        # 중요:
        # archive page 자체는 final positive 불가.
        "final_positive":
            False,
    }


# ============================================================
# CANDIDATE EXTRACTION
# ============================================================

def extract_detail_candidates(
    *,
    source: str,
    page_url: str,
    archive_url: str,
    region: str,
    agency: str,
) -> List[Dict[str, Any]]:

    results = []

    seen = set()

    for link in extract_links(
        source,
        base_url=page_url,
    ):

        url = normalize_url(
            link[
                "url"
            ]
        )

        label = normalize_space(
            link.get(
                "label"
            )
        )

        if not same_or_subdomain(
            url,
            archive_url,
        ):

            continue

        if is_search_url(
            url
        ):

            continue

        if is_attachment_url(
            url
        ):

            continue

        structural_detail = (
            is_probably_detail_url(
                url
            )
        )

        semantic_detail = (
            contains_target(
                label
            )
            or contains_notice_context(
                label
            )
            or contains_gazette_context(
                label
            )
        )

        if not (
            structural_detail
            or semantic_detail
        ):

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

        results.append(
            {
                "region":
                    region,

                "agency":
                    agency,

                "archive_url":
                    archive_url,

                "source_page_url":
                    page_url,

                "url":
                    url,

                "label":
                    label,

                "target_in_label":
                    contains_target(
                        label
                    ),

                "notice_context_in_label":
                    contains_notice_context(
                        label
                    ),

                "gazette_context_in_label":
                    contains_gazette_context(
                        label
                    ),

                "structural_detail_evidence":
                    structural_detail,
            }
        )

        if (
            len(results)
            >= MAX_DETAIL_SEEDS_PER_ENDPOINT
        ):

            break

    return results


def extract_attachment_candidates(
    *,
    source: str,
    page_url: str,
    archive_url: str,
    region: str,
    agency: str,
) -> List[Dict[str, Any]]:

    page_text = strip_html(
        source
    )

    parent_target = contains_target(
        page_text
    )

    parent_notice_context = (
        contains_notice_context(
            page_text
        )
    )

    results = []

    seen = set()

    for link in extract_links(
        source,
        base_url=page_url,
    ):

        url = normalize_url(
            link[
                "url"
            ]
        )

        label = normalize_space(
            link.get(
                "label"
            )
        )

        if not same_or_subdomain(
            url,
            archive_url,
        ):

            continue

        if not is_attachment_url(
            url
        ):

            continue

        target_in_label = contains_target(
            label
        )

        target_in_url = contains_target(
            requests.utils.unquote(
                url
            )
        )

        notice_in_label = (
            contains_notice_context(
                label
            )
        )

        relevant = (
            target_in_label
            or target_in_url
            or (
                parent_target
                and parent_notice_context
            )
        )

        key = (
            region,
            url,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        results.append(
            {
                "region":
                    region,

                "agency":
                    agency,

                "archive_url":
                    archive_url,

                "parent_page_url":
                    page_url,

                "url":
                    url,

                "label":
                    label,

                "extension":
                    get_attachment_extension(
                        url
                    ),

                "target_in_label":
                    target_in_label,

                "target_in_url":
                    target_in_url,

                "notice_context_in_label":
                    notice_in_label,

                "target_in_parent_page":
                    parent_target,

                "notice_context_in_parent_page":
                    parent_notice_context,

                "relevant_attachment_candidate":
                    relevant,

                "final_positive":
                    False,
            }
        )

        if (
            len(results)
            >= MAX_ATTACHMENT_SEEDS_PER_ENDPOINT
        ):

            break

    return results


# ============================================================
# LOAD INPUT
# ============================================================

if not INPUT_PATH.exists():

    raise FileNotFoundError(
        f"Input not found: {INPUT_PATH}"
    )


input_data = json.loads(
    INPUT_PATH.read_text(
        encoding="utf-8"
    )
)


raw_candidates = (
    input_data.get(
        "canonical_endpoints"
    )
    or input_data.get(
        "classified_endpoints"
    )
    or input_data.get(
        "next_stage_search_pool"
    )
    or []
)


gazette_endpoints = []

seen_endpoint_urls = set()

for item in raw_candidates:

    classification = (
        item.get(
            "classification"
        )
        or item.get(
            "class"
        )
        or ""
    )

    if classification != ALLOWED_INPUT_CLASS:

        continue

    url = normalize_url(
        str(
            item.get(
                "canonical_url"
            )
            or item.get(
                "url"
            )
            or ""
        )
    )

    if not url:

        continue

    key = (
        item.get(
            "region"
        ),
        url,
    )

    if key in seen_endpoint_urls:

        continue

    seen_endpoint_urls.add(
        key
    )

    gazette_endpoints.append(
        {
            "region":
                item.get(
                    "region"
                ),

            "agency":
                (
                    item.get(
                        "agency"
                    )
                    or item.get(
                        "region"
                    )
                ),

            "classification":
                ALLOWED_INPUT_CLASS,

            "label":
                item.get(
                    "label"
                )
                or "",

            "url":
                url,

            "score":
                item.get(
                    "score"
                ),

            "reasons":
                item.get(
                    "reasons"
                )
                or [],
        }
    )


gazette_endpoints = gazette_endpoints[
    :MAX_ARCHIVE_ENDPOINTS
]


# ============================================================
# DISCOVERY STATE
# ============================================================

endpoint_results: List[
    Dict[
        str,
        Any
    ]
] = []

detail_candidates: List[
    Dict[
        str,
        Any
    ]
] = []

attachment_candidates: List[
    Dict[
        str,
        Any
    ]
] = []

target_archive_pages: List[
    Dict[
        str,
        Any
    ]
] = []

visited_urls: Set[str] = set()

request_count = 0

http_success_count = 0

transport_error_count = 0

html_parse_count = 0

historical_page_probe_count = 0

pagination_page_probe_count = 0

year_page_probe_count = 0


# ============================================================
# HEADER
# ============================================================

print(
    "============================================================"
)

print(
    "DEVELOPMENT DENSITY MANAGEMENT AREA"
)

print(
    "OFFICIAL GAZETTE ARCHIVE HISTORICAL DISCOVERY"
)

print(
    "============================================================"
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
    "Input:",
    INPUT_PATH,
)

print(
    "Gazette archive endpoint count:",
    len(
        gazette_endpoints
    ),
)

print()


# ============================================================
# MAIN LOOP
# ============================================================

for endpoint_index, endpoint in enumerate(
    gazette_endpoints,
    start=1,
):

    region = (
        endpoint.get(
            "region"
        )
        or ""
    )

    agency = (
        endpoint.get(
            "agency"
        )
        or region
    )

    label = (
        endpoint.get(
            "label"
        )
        or ""
    )

    archive_url = (
        endpoint[
            "url"
        ]
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        f"ARCHIVE {endpoint_index}:",
        region,
    )

    print(
        "Label:",
        label,
    )

    print(
        "URL:",
        archive_url,
    )

    local_pages = []

    local_details = []

    local_attachments = []

    # ========================================================
    # FIRST PAGE
    # ========================================================

    first = fetch_url(
        archive_url
    )

    request_count += 1

    if first.error:

        transport_error_count += 1

        print(
            "Transport error:",
            first.error,
        )

        endpoint_results.append(
            {
                **endpoint,
                "http_status":
                    None,

                "error":
                    first.error,

                "pagination_params":
                    [],

                "year_params":
                    [],

                "historical_pages":
                    [],

                "detail_candidate_count":
                    0,

                "attachment_candidate_count":
                    0,
            }
        )

        continue

    if first.http_status == 200:

        http_success_count += 1

    first_url = (
        first.final_url
        or archive_url
    )

    if first.text:

        html_parse_count += 1

    first_classification = (
        classify_archive_page(
            region=region,
            agency=agency,
            url=first_url,
            source=first.text,
        )
    )

    if first_classification[
        "target_found"
    ]:

        target_archive_pages.append(
            first_classification
        )

    pagination_params = (
        detect_pagination_params(
            first.text
        )
    )

    year_params = (
        detect_year_params(
            first.text
        )
    )

    first_details = (
        extract_detail_candidates(
            source=first.text,
            page_url=first_url,
            archive_url=archive_url,
            region=region,
            agency=agency,
        )
    )

    first_attachments = (
        extract_attachment_candidates(
            source=first.text,
            page_url=first_url,
            archive_url=archive_url,
            region=region,
            agency=agency,
        )
    )

    local_details.extend(
        first_details
    )

    local_attachments.extend(
        first_attachments
    )

    # ========================================================
    # HISTORICAL PAGE PLAN
    # ========================================================

    historical_plans = (
        build_historical_page_urls(
            first_url,
            pagination_params,
            year_params,
        )
    )

    for plan in historical_plans:

        page_url = (
            plan[
                "url"
            ]
        )

        if page_url in visited_urls:

            continue

        visited_urls.add(
            page_url
        )

        historical_page_probe_count += 1

        if (
            plan.get(
                "strategy"
            )
            == "PAGINATION"
        ):

            pagination_page_probe_count += 1

        elif (
            plan.get(
                "strategy"
            )
            == "YEAR"
        ):

            year_page_probe_count += 1

        result = fetch_url(
            page_url
        )

        request_count += 1

        if result.error:

            transport_error_count += 1

            local_pages.append(
                {
                    **plan,
                    "http_status":
                        None,

                    "error":
                        result.error,

                    "target_found":
                        False,

                    "detail_candidate_count":
                        0,

                    "attachment_candidate_count":
                        0,
                }
            )

            continue

        if result.http_status == 200:

            http_success_count += 1

        final_url = (
            result.final_url
            or page_url
        )

        if result.text:

            html_parse_count += 1

        classification = (
            classify_archive_page(
                region=region,
                agency=agency,
                url=final_url,
                source=result.text,
            )
        )

        if classification[
            "target_found"
        ]:

            target_archive_pages.append(
                classification
            )

        details = (
            extract_detail_candidates(
                source=result.text,
                page_url=final_url,
                archive_url=archive_url,
                region=region,
                agency=agency,
            )
        )

        attachments = (
            extract_attachment_candidates(
                source=result.text,
                page_url=final_url,
                archive_url=archive_url,
                region=region,
                agency=agency,
            )
        )

        local_details.extend(
            details
        )

        local_attachments.extend(
            attachments
        )

        local_pages.append(
            {
                **plan,

                "final_url":
                    result.final_url,

                "http_status":
                    result.http_status,

                "content_type":
                    result.content_type,

                "target_found":
                    classification[
                        "target_found"
                    ],

                "notice_context":
                    classification[
                        "notice_context"
                    ],

                "gazette_context":
                    classification[
                        "gazette_context"
                    ],

                "notice_numbers":
                    classification[
                        "notice_numbers"
                    ],

                "dates":
                    classification[
                        "dates"
                    ],

                "preview":
                    classification[
                        "preview"
                    ],

                "detail_candidate_count":
                    len(
                        details
                    ),

                "attachment_candidate_count":
                    len(
                        attachments
                    ),
            }
        )

        time.sleep(
            REQUEST_SLEEP
        )

    # ========================================================
    # LOCAL DEDUPE
    # ========================================================

    deduped_local_details = []

    local_detail_seen = set()

    for item in local_details:

        key = (
            item.get(
                "region"
            ),
            normalize_url(
                str(
                    item.get(
                        "url"
                    )
                    or ""
                )
            ),
        )

        if key in local_detail_seen:
            continue

        local_detail_seen.add(
            key
        )

        deduped_local_details.append(
            item
        )

    deduped_local_attachments = []

    local_attachment_seen = set()

    for item in local_attachments:

        key = (
            item.get(
                "region"
            ),
            normalize_url(
                str(
                    item.get(
                        "url"
                    )
                    or ""
                )
            ),
        )

        if key in local_attachment_seen:
            continue

        local_attachment_seen.add(
            key
        )

        deduped_local_attachments.append(
            item
        )

    detail_candidates.extend(
        deduped_local_details
    )

    attachment_candidates.extend(
        deduped_local_attachments
    )

    print(
        "HTTP:",
        first.http_status,
    )

    print(
        "Pagination params:",
        pagination_params,
    )

    print(
        "Year params:",
        year_params,
    )

    print(
        "Historical pages probed:",
        len(
            local_pages
        ),
    )

    print(
        "Target-bearing archive pages:",
        sum(
            1
            for page
            in local_pages
            if page.get(
                "target_found"
            )
            is True
        )
        + (
            1
            if first_classification[
                "target_found"
            ]
            else 0
        ),
    )

    print(
        "Detail candidates:",
        len(
            deduped_local_details
        ),
    )

    print(
        "Attachment candidates:",
        len(
            deduped_local_attachments
        ),
    )

    endpoint_results.append(
        {
            **endpoint,

            "http_status":
                first.http_status,

            "final_url":
                first.final_url,

            "pagination_params":
                pagination_params,

            "year_params":
                year_params,

            "first_page_target_found":
                first_classification[
                    "target_found"
                ],

            "historical_pages":
                local_pages,

            "detail_candidate_count":
                len(
                    deduped_local_details
                ),

            "attachment_candidate_count":
                len(
                    deduped_local_attachments
                ),
        }
    )

    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# GLOBAL DEDUPE
# ============================================================

deduped_details = []

seen_details = set()

for item in detail_candidates:

    normalized = normalize_url(
        str(
            item.get(
                "url"
            )
            or ""
        )
    )

    key = (
        item.get(
            "region"
        ),
        normalized,
    )

    if key in seen_details:

        continue

    seen_details.add(
        key
    )

    normalized_item = dict(
        item
    )

    normalized_item[
        "url"
    ] = normalized

    deduped_details.append(
        normalized_item
    )


deduped_attachments = []

seen_attachments = set()

for item in attachment_candidates:

    normalized = normalize_url(
        str(
            item.get(
                "url"
            )
            or ""
        )
    )

    key = (
        item.get(
            "region"
        ),
        normalized,
    )

    if key in seen_attachments:

        continue

    seen_attachments.add(
        key
    )

    normalized_item = dict(
        item
    )

    normalized_item[
        "url"
    ] = normalized

    deduped_attachments.append(
        normalized_item
    )


deduped_target_pages = []

seen_target_pages = set()

for item in target_archive_pages:

    normalized = normalize_url(
        str(
            item.get(
                "url"
            )
            or ""
        )
    )

    key = (
        item.get(
            "region"
        ),
        normalized,
    )

    if key in seen_target_pages:

        continue

    seen_target_pages.add(
        key
    )

    deduped_target_pages.append(
        item
    )


# ============================================================
# PRIORITIZE SEEDS
# ============================================================

for item in deduped_details:

    score = 0

    if item.get(
        "target_in_label"
    ) is True:

        score += 5

    if item.get(
        "notice_context_in_label"
    ) is True:

        score += 3

    if item.get(
        "gazette_context_in_label"
    ) is True:

        score += 2

    if item.get(
        "structural_detail_evidence"
    ) is True:

        score += 1

    item[
        "priority_score"
    ] = score


deduped_details.sort(
    key=lambda item: (
        -int(
            item.get(
                "priority_score",
                0,
            )
        ),
        str(
            item.get(
                "region",
                "",
            )
        ),
        str(
            item.get(
                "url",
                "",
            )
        ),
    )
)


for item in deduped_attachments:

    score = 0

    if item.get(
        "target_in_label"
    ) is True:

        score += 5

    if item.get(
        "target_in_url"
    ) is True:

        score += 5

    if item.get(
        "notice_context_in_label"
    ) is True:

        score += 3

    if (
        item.get(
            "target_in_parent_page"
        )
        is True
        and item.get(
            "notice_context_in_parent_page"
        )
        is True
    ):

        score += 2

    if item.get(
        "extension"
    ) in {
        "pdf",
        "hwp",
        "hwpx",
    }:

        score += 1

    item[
        "priority_score"
    ] = score


deduped_attachments.sort(
    key=lambda item: (
        -int(
            item.get(
                "priority_score",
                0,
            )
        ),
        str(
            item.get(
                "region",
                "",
            )
        ),
        str(
            item.get(
                "url",
                "",
            )
        ),
    )
)


# ============================================================
# RELEVANT SEEDS
# ============================================================

relevant_detail_candidates = [
    item
    for item in deduped_details
    if (
        item.get(
            "target_in_label"
        )
        is True
        or item.get(
            "notice_context_in_label"
        )
        is True
    )
]


relevant_attachment_candidates = [
    item
    for item in deduped_attachments
    if item.get(
        "relevant_attachment_candidate"
    )
    is True
]


# ============================================================
# RESOLUTION
# ============================================================

historical_structure_confirmed = any(
    (
        item.get(
            "pagination_params"
        )
        or item.get(
            "year_params"
        )
        or item.get(
            "historical_pages"
        )
    )
    for item in endpoint_results
)


if (
    deduped_target_pages
    or relevant_detail_candidates
    or relevant_attachment_candidates
):

    resolution = (
        "GAZETTE_ARCHIVE_HISTORICAL_TARGET_OR_DOCUMENT_SEED_DISCOVERED"
    )

    next_action = (
        "target-bearing archive page 및 우선순위 detail/attachment seed를 "
        "개별 조회하여 실제 개발밀도관리구역 지정·변경·해제 고시인지 "
        "원문 검증하고, 고시번호·고시일·지정 범위·현재 유효 여부를 "
        "확정한 뒤 positive PNU와 spatial source를 역탐색한다."
    )

elif historical_structure_confirmed:

    resolution = (
        "GAZETTE_ARCHIVE_HISTORICAL_TRAVERSAL_COMPLETED_NO_TARGET"
    )

    next_action = (
        "현재 확인한 GET historical archive에서는 target을 발견하지 못했다. "
        "POST 기반 pagination, JavaScript pagination, archive 첨부파일 본문, "
        "국가기록원·관보·토지이음 및 과거 행정전자민원 고시공고 자료원으로 "
        "탐색 범위를 확장한다."
    )

else:

    resolution = (
        "GAZETTE_ARCHIVE_HISTORICAL_STRUCTURE_UNRESOLVED"
    )

    next_action = (
        "공보 archive의 POST form, JavaScript pagination, AJAX endpoint 및 "
        "site-specific 연도/호수 탐색 구조를 분석한다."
    )


runtime_registration_blocked = (
    True
)

site_false_interpretation_blocked = (
    True
)


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-R "
        "Development Density Management Area "
        "Official Gazette Archive Historical Discovery"
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

        "required_class":
            ALLOWED_INPUT_CLASS,

        "gazette_archive_endpoint_count":
            len(
                gazette_endpoints
            ),
    },

    "method": {
        "official_archive_direct_probe":
            True,

        "search_engine_scraping":
            False,

        "historical_pagination_probe":
            True,

        "historical_year_probe":
            True,

        "archive_page_final_positive_allowed":
            False,

        "attachment_final_positive_allowed":
            False,

        "runtime_registration_allowed":
            False,

        "site_false_interpretation_allowed":
            False,

        "max_historical_pages_per_endpoint":
            MAX_HISTORICAL_PAGES_PER_ENDPOINT,
    },

    "summary": {
        "request_count":
            request_count,

        "http_success_count":
            http_success_count,

        "transport_error_count":
            transport_error_count,

        "html_parse_count":
            html_parse_count,

        "historical_page_probe_count":
            historical_page_probe_count,

        "pagination_page_probe_count":
            pagination_page_probe_count,

        "year_page_probe_count":
            year_page_probe_count,

        "target_archive_page_count":
            len(
                deduped_target_pages
            ),

        "detail_candidate_count":
            len(
                deduped_details
            ),

        "relevant_detail_candidate_count":
            len(
                relevant_detail_candidates
            ),

        "attachment_candidate_count":
            len(
                deduped_attachments
            ),

        "relevant_attachment_candidate_count":
            len(
                relevant_attachment_candidates
            ),

        "historical_structure_confirmed":
            historical_structure_confirmed,
    },

    "gazette_archive_endpoints":
        gazette_endpoints,

    "endpoint_results":
        endpoint_results,

    "target_archive_pages":
        deduped_target_pages,

    "detail_candidates":
        deduped_details,

    "relevant_detail_candidates":
        relevant_detail_candidates,

    "attachment_candidates":
        deduped_attachments,

    "relevant_attachment_candidates":
        relevant_attachment_candidates,

    "resolution":
        resolution,

    "runtime_registration_blocked":
        runtime_registration_blocked,

    "site_false_interpretation_blocked":
        site_false_interpretation_blocked,

    "next_action":
        next_action,
}


OUTPUT_PATH.write_text(
    json.dumps(
        output_data,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


# ============================================================
# CONSOLE SUMMARY
# ============================================================

print()

print(
    "============================================================"
)

print(
    "DISCOVERY RESULT"
)

print(
    "============================================================"
)

print(
    "Gazette archive endpoint count:",
    len(
        gazette_endpoints
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
    "HTML parse count:",
    html_parse_count,
)

print(
    "Historical page probe count:",
    historical_page_probe_count,
)

print(
    "Pagination page probe count:",
    pagination_page_probe_count,
)

print(
    "Year page probe count:",
    year_page_probe_count,
)

print(
    "Target archive page count:",
    len(
        deduped_target_pages
    ),
)

print(
    "Detail candidate count:",
    len(
        deduped_details
    ),
)

print(
    "Relevant detail candidate count:",
    len(
        relevant_detail_candidates
    ),
)

print(
    "Attachment candidate count:",
    len(
        deduped_attachments
    ),
)

print(
    "Relevant attachment candidate count:",
    len(
        relevant_attachment_candidates
    ),
)

print()


if deduped_target_pages:

    print(
        "TARGET-BEARING ARCHIVE PAGES"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, item in enumerate(
        deduped_target_pages[
            :30
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            item.get(
                "region"
            ),
        )

        print(
            "URL:",
            item.get(
                "url"
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
            "Preview:",
            item.get(
                "preview"
            ),
        )

        print()


if relevant_detail_candidates:

    print(
        "RELEVANT DETAIL SEEDS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, item in enumerate(
        relevant_detail_candidates[
            :50
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            item.get(
                "region"
            ),
        )

        print(
            "Score:",
            item.get(
                "priority_score"
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

        print()


if relevant_attachment_candidates:

    print(
        "RELEVANT ATTACHMENT SEEDS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, item in enumerate(
        relevant_attachment_candidates[
            :50
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            item.get(
                "region"
            ),
        )

        print(
            "Score:",
            item.get(
                "priority_score"
            ),
        )

        print(
            "Type:",
            item.get(
                "extension"
            ),
        )

        print(
            "Label:",
            item.get(
                "label"
            ),
        )

        print(
            "Parent:",
            item.get(
                "parent_page_url"
            ),
        )

        print(
            "URL:",
            item.get(
                "url"
            ),
        )

        print()


if not (
    deduped_target_pages
    or relevant_detail_candidates
    or relevant_attachment_candidates
):

    print(
        "No target-bearing official gazette archive seed discovered."
    )

    print()


print(
    "============================================================"
)

print(
    "RESOLUTION"
)

print(
    "============================================================"
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


# ============================================================
# VALIDATION HELPERS
# ============================================================

endpoint_keys = {
    (
        item.get(
            "region"
        ),
        normalize_url(
            str(
                item.get(
                    "url"
                )
                or ""
            )
        ),
    )
    for item in gazette_endpoints
}


detail_keys = {
    (
        item.get(
            "region"
        ),
        normalize_url(
            str(
                item.get(
                    "url"
                )
                or ""
            )
        ),
    )
    for item in deduped_details
}


attachment_keys = {
    (
        item.get(
            "region"
        ),
        normalize_url(
            str(
                item.get(
                    "url"
                )
                or ""
            )
        ),
    )
    for item in deduped_attachments
}


target_page_keys = {
    (
        item.get(
            "region"
        ),
        normalize_url(
            str(
                item.get(
                    "url"
                )
                or ""
            )
        ),
    )
    for item in deduped_target_pages
}


all_input_classes_valid = all(
    item.get(
        "classification"
    )
    == ALLOWED_INPUT_CLASS
    for item in gazette_endpoints
)


all_archive_urls_exist = all(
    bool(
        item.get(
            "url"
        )
    )
    for item in gazette_endpoints
)


all_target_pages_have_target = all(
    item.get(
        "target_found"
    )
    is True
    for item in deduped_target_pages
)


all_target_pages_not_final_positive = all(
    item.get(
        "final_positive"
    )
    is False
    for item in deduped_target_pages
)


all_detail_urls_exist = all(
    bool(
        item.get(
            "url"
        )
    )
    for item in deduped_details
)


all_detail_urls_not_search = all(
    not is_search_url(
        str(
            item.get(
                "url"
            )
            or ""
        )
    )
    for item in deduped_details
)


all_attachment_urls_exist = all(
    bool(
        item.get(
            "url"
        )
    )
    for item in deduped_attachments
)


all_relevant_attachments_have_evidence = all(
    (
        item.get(
            "target_in_label"
        )
        is True
        or item.get(
            "target_in_url"
        )
        is True
        or (
            item.get(
                "target_in_parent_page"
            )
            is True
            and item.get(
                "notice_context_in_parent_page"
            )
            is True
        )
    )
    for item in relevant_attachment_candidates
)


# ============================================================
# VALIDATION
# ============================================================

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

    "H-stage input parsed": (
        isinstance(
            input_data,
            dict,
        )
    ),

    "gazette archive endpoints loaded": (
        len(
            gazette_endpoints
        )
        > 0
    ),

    "only GAZETTE_ARCHIVE executed": (
        all_input_classes_valid
    ),

    "archive endpoints unique": (
        len(
            endpoint_keys
        )
        == len(
            gazette_endpoints
        )
    ),

    "all archive URLs exist": (
        all_archive_urls_exist
    ),

    "official archive direct probe enabled": (
        output_data[
            "method"
        ][
            "official_archive_direct_probe"
        ]
        is True
    ),

    "search engine scraping disabled": (
        output_data[
            "method"
        ][
            "search_engine_scraping"
        ]
        is False
    ),

    "historical pagination enabled": (
        output_data[
            "method"
        ][
            "historical_pagination_probe"
        ]
        is True
    ),

    "historical year probe enabled": (
        output_data[
            "method"
        ][
            "historical_year_probe"
        ]
        is True
    ),

    "archive page final positive prohibited": (
        output_data[
            "method"
        ][
            "archive_page_final_positive_allowed"
        ]
        is False
    ),

    "attachment final positive prohibited": (
        output_data[
            "method"
        ][
            "attachment_final_positive_allowed"
        ]
        is False
    ),

    "requests executed": (
        request_count
        > 0
    ),

    "endpoint result accounting": (
        len(
            endpoint_results
        )
        == len(
            gazette_endpoints
        )
    ),

    "target archive pages unique": (
        len(
            target_page_keys
        )
        == len(
            deduped_target_pages
        )
    ),

    "all target archive pages contain target": (
        all_target_pages_have_target
    ),

    "target archive pages are not final positive": (
        all_target_pages_not_final_positive
    ),

    "detail candidates unique": (
        len(
            detail_keys
        )
        == len(
            deduped_details
        )
    ),

    "all detail candidates have URL": (
        all_detail_urls_exist
    ),

    "all detail candidates are not search URLs": (
        all_detail_urls_not_search
    ),

    "attachment candidates unique": (
        len(
            attachment_keys
        )
        == len(
            deduped_attachments
        )
    ),

    "all attachment candidates have URL": (
        all_attachment_urls_exist
    ),

    "all relevant attachments have target evidence": (
        all_relevant_attachments_have_evidence
    ),

    "runtime registration remains blocked": (
        runtime_registration_blocked
        is True
    ),

    "SITE FALSE remains blocked": (
        site_false_interpretation_blocked
        is True
    ),

    "output written": (
        OUTPUT_PATH.exists()
        and OUTPUT_PATH.stat().st_size
        > 0
    ),
}


print()

print(
    "============================================================"
)

print(
    "VALIDATION"
)

print(
    "============================================================"
)


for name, passed in validations.items():

    print(
        f"{name}:",
        passed,
    )


all_pass = all(
    validations.values()
)


print()

print(
    "all_pass:",
    all_pass,
)


if not all_pass:

    print()

    print(
        "FAILED:"
    )

    for name, passed in validations.items():

        if not passed:

            print(
                "-",
                name,
            )

    raise AssertionError(
        "Development density management area "
        "gazette archive historical discovery regression failed"
    )