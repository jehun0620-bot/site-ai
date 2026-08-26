# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-C
Development Density Management Area Official Gazette Discovery

목표
======================================================================
개발밀도관리구역의 실제 지정 / 변경 / 해제 사례를
검색엔진 결과 개수에 의존하지 않고 공식 행정기관 웹 문서에서 탐색한다.

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

이 단계의 목적
======================================================================
1. 공식 지자체 / 공공기관 도메인을 대상으로 직접 검색
2. 제목 / 본문 / 링크에서 "개발밀도관리구역" 탐색
3. 지정 / 변경 / 해제 / 고시 관련 문맥 확인
4. positive notice candidate 확보
5. candidate의 행정구역 / 고시번호 / 날짜 / URL 저장
6. 이후 spatial source 역탐색용 seed 확보

중요
======================================================================
이 테스트에서 공식 고시를 발견하지 못했다고 해서

    SITE FALSE

로 판단하지 않는다.

또한 현재 VWorld LT_C_UQ141 dataset이 접근 가능하더라도
그 자체를 UQQ700 개발밀도관리구역 dataset으로 확정하지 않는다.

이번 단계의 성공은 다음 둘 중 하나다.

A.
공식 positive notice candidate를 1건 이상 발견

B.
공식 사이트 직접 탐색 구조가 정상 실행되고
positive candidate 미발견 상태를 명시적으로 보존

즉 discovery test이므로
positive candidate 0건도 테스트 실패가 아니다.

C-16-8-C 보강 정책
======================================================================
검색 페이지 자체에 검색어가 echo되는 경우를
실제 공식 고시 문서로 오인하지 않는다.

특히 다음과 같은 페이지는 positive candidate가 아니다.

    검색어 개발밀도관리구역에 대한 검색결과 0건

Positive candidate 최소 조건:

1. 개발밀도관리구역 target text 존재
2. 검색결과 0건 페이지가 아님
3. 지정 / 변경 / 해제 / 결정 / 고시 등 강한 문서 문맥 존재
4. 실제 문서 evidence 존재
   - 고시번호
   - 날짜
   - 또는 검색 페이지가 아닌 실제 문서 페이지
"""

from __future__ import annotations

import json
import re
import time

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
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
    / "development_density_management_area_official_gazette_discovery.json"
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

REQUEST_SLEEP = 0.4

MAX_CONTENT_LENGTH = (
    2_000_000
)

MAX_LINKS_PER_PAGE = (
    120
)

MAX_SECONDARY_PAGES_PER_SITE = (
    40
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
        "application/xml;q=0.9,"
        "*/*;q=0.8"
    ),

    "Accept-Language": (
        "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
}


# ============================================================
# OFFICIAL SITE SEEDS
# ============================================================

OFFICIAL_SITE_SEEDS: List[Dict[str, str]] = [

    {
        "region": "서울특별시",
        "agency": "서울특별시",
        "base_url": "https://www.seoul.go.kr/",
    },

    {
        "region": "부산광역시",
        "agency": "부산광역시",
        "base_url": "https://www.busan.go.kr/",
    },

    {
        "region": "대구광역시",
        "agency": "대구광역시",
        "base_url": "https://www.daegu.go.kr/",
    },

    {
        "region": "인천광역시",
        "agency": "인천광역시",
        "base_url": "https://www.incheon.go.kr/",
    },

    {
        "region": "광주광역시",
        "agency": "광주광역시",
        "base_url": "https://www.gwangju.go.kr/",
    },

    {
        "region": "대전광역시",
        "agency": "대전광역시",
        "base_url": "https://www.daejeon.go.kr/",
    },

    {
        "region": "울산광역시",
        "agency": "울산광역시",
        "base_url": "https://www.ulsan.go.kr/",
    },

    {
        "region": "세종특별자치시",
        "agency": "세종특별자치시",
        "base_url": "https://www.sejong.go.kr/",
    },

    {
        "region": "경기도",
        "agency": "경기도",
        "base_url": "https://www.gg.go.kr/",
    },

    {
        "region": "강원특별자치도",
        "agency": "강원특별자치도",
        "base_url": "https://state.gwd.go.kr/",
    },

    {
        "region": "충청북도",
        "agency": "충청북도",
        "base_url": "https://www.chungbuk.go.kr/",
    },

    {
        "region": "충청남도",
        "agency": "충청남도",
        "base_url": "https://www.chungnam.go.kr/",
    },

    {
        "region": "전북특별자치도",
        "agency": "전북특별자치도",
        "base_url": "https://www.jeonbuk.go.kr/",
    },

    {
        "region": "전라남도",
        "agency": "전라남도",
        "base_url": "https://www.jeonnam.go.kr/",
    },

    {
        "region": "경상북도",
        "agency": "경상북도",
        "base_url": "https://www.gb.go.kr/",
    },

    {
        "region": "경상남도",
        "agency": "경상남도",
        "base_url": "https://www.gyeongnam.go.kr/",
    },

    {
        "region": "제주특별자치도",
        "agency": "제주특별자치도",
        "base_url": "https://www.jeju.go.kr/",
    },
]


# ============================================================
# DISCOVERY TERMS
# ============================================================

DISCOVERY_TERMS = [

    TARGET_NAME,

    f"{TARGET_NAME} 지정",

    f"{TARGET_NAME} 고시",

    f"{TARGET_NAME} 변경",

    f"{TARGET_NAME} 해제",

    f"{TARGET_NAME} 도시관리계획",

    f"{TARGET_NAME} 결정",

    "개발밀도 관리구역",
]


NOTICE_CONTEXT_TERMS = [

    "고시",

    "공고",

    "지정",

    "변경",

    "해제",

    "도시관리계획",

    "결정",

    "지형도면",

    "도시계획",
]


LINK_HINT_TERMS = [

    "고시",

    "공고",

    "공보",

    "도시계획",

    "도시관리",

    "토지",

    "개발",

    "검색",

    "notice",

    "announce",

    "board",

    "bbs",

    "news",

    "cityplan",
]


# ============================================================
# SEARCH PAGE / ZERO RESULT PATTERNS
# ============================================================

SEARCH_PAGE_PATTERNS = [

    re.compile(
        r"검색어\s*.+?\s*에\s*대한\s*검색결과",
        re.IGNORECASE,
    ),

    re.compile(
        r"통합검색",
        re.IGNORECASE,
    ),

    re.compile(
        r"검색결과\s*\d+\s*건",
        re.IGNORECASE,
    ),
]


ZERO_RESULT_PATTERNS = [

    re.compile(
        r"검색결과\s*0\s*건",
        re.IGNORECASE,
    ),

    re.compile(
        r"검색\s*결과가\s*없",
        re.IGNORECASE,
    ),

    re.compile(
        r"검색된\s*(?:자료|게시물|문서|결과)가\s*없",
        re.IGNORECASE,
    ),

    re.compile(
        r"조회된\s*(?:자료|게시물|문서|결과)가\s*없",
        re.IGNORECASE,
    ),

    re.compile(
        r"총\s*0\s*건",
        re.IGNORECASE,
    ),
]


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


def strip_html(
    html: str,
) -> str:

    value = re.sub(
        r"(?is)<script[^>]*>.*?</script>",
        " ",
        html,
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

    value = (
        value
        .replace(
            "&nbsp;",
            " ",
        )
        .replace(
            "&amp;",
            "&",
        )
        .replace(
            "&lt;",
            "<",
        )
        .replace(
            "&gt;",
            ">",
        )
        .replace(
            "&#39;",
            "'",
        )
        .replace(
            "&quot;",
            "\"",
        )
    )

    return normalize_space(
        value
    )


def normalize_target_text(
    value: str,
) -> str:

    return re.sub(
        r"\s+",
        "",
        value,
    )


def contains_target(
    value: str,
) -> bool:

    normalized = (
        normalize_target_text(
            value
        )
    )

    return (
        normalize_target_text(
            TARGET_NAME
        )
        in normalized
    )


def contains_notice_context(
    value: str,
) -> bool:

    text = normalize_space(
        value
    )

    return any(
        term in text
        for term
        in NOTICE_CONTEXT_TERMS
    )


def has_strong_notice_context(
    value: str,
) -> bool:

    """
    페이지 어딘가에 '고시'라는 단어가 있다는 이유만으로
    positive 처리하지 않는다.

    target 주변 또는 target과 직접 연결된
    지정 / 변경 / 해제 / 결정 / 고시 문맥을 요구한다.
    """

    text = normalize_space(
        value
    )

    patterns = [

        r"개발밀도\s*관리구역.{0,160}지정",

        r"개발밀도\s*관리구역.{0,160}변경",

        r"개발밀도\s*관리구역.{0,160}해제",

        r"개발밀도\s*관리구역.{0,160}결정",

        r"개발밀도\s*관리구역.{0,160}고시",

        r"개발밀도\s*관리구역.{0,160}지형도면",

        r"지정.{0,160}개발밀도\s*관리구역",

        r"변경.{0,160}개발밀도\s*관리구역",

        r"해제.{0,160}개발밀도\s*관리구역",

        r"고시.{0,160}개발밀도\s*관리구역",

        r"도시관리계획.{0,200}개발밀도\s*관리구역",

        r"개발밀도\s*관리구역.{0,200}도시관리계획",
    ]

    return any(
        re.search(
            pattern,
            text,
            re.IGNORECASE,
        )
        for pattern
        in patterns
    )


def is_search_page(
    text: str,
    url: str,
) -> bool:

    normalized = (
        normalize_space(
            text
        )
    )

    lower_url = (
        str(
            url
            or ""
        )
        .lower()
    )

    url_hint = any(
        token in lower_url
        for token in (
            "/search",
            "search.do",
            "search?",
            "query=",
            "keyword=",
            "searchkeyword=",
        )
    )

    text_hint = any(
        pattern.search(
            normalized
        )
        for pattern
        in SEARCH_PAGE_PATTERNS
    )

    return (
        url_hint
        or text_hint
    )


def has_zero_search_result(
    text: str,
) -> bool:

    normalized = (
        normalize_space(
            text
        )
    )

    return any(
        pattern.search(
            normalized
        )
        for pattern
        in ZERO_RESULT_PATTERNS
    )


def build_preview(
    text: str,
    *,
    keyword: str = TARGET_NAME,
    radius: int = 220,
) -> str:

    normalized = normalize_space(
        text
    )

    compact_target = (
        normalize_target_text(
            keyword
        )
    )

    compact_text = (
        normalize_target_text(
            normalized
        )
    )

    compact_index = (
        compact_text.find(
            compact_target
        )
    )

    if compact_index < 0:

        return normalized[
            : (
                radius
                * 2
            )
        ]

    candidates = [

        TARGET_NAME,

        "개발밀도 관리구역",

        "개발 밀도 관리구역",
    ]

    index = -1

    for candidate in candidates:

        index = (
            normalized.find(
                candidate
            )
        )

        if (
            index
            >= 0
        ):

            break

    if (
        index
        < 0
    ):

        return normalized[
            : (
                radius
                * 2
            )
        ]

    start = max(
        0,
        index
        - radius,
    )

    end = min(
        len(
            normalized
        ),
        index
        + len(
            keyword
        )
        + radius,
    )

    return normalized[
        start:end
    ]


def normalize_url(
    url: str,
) -> str:

    try:

        parsed = (
            urlparse(
                url
            )
        )

    except Exception:

        return url

    query_items = []

    for key, value in (
        parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
    ):

        lowered = (
            key.lower()
        )

        if lowered in {

            "utm_source",

            "utm_medium",

            "utm_campaign",

            "utm_term",

            "utm_content",

            "fbclid",

            "gclid",
        }:

            continue

        query_items.append(
            (
                key,
                value,
            )
        )

    cleaned = (
        parsed._replace(
            query=(
                urlencode(
                    query_items,
                    doseq=True,
                )
            ),
            fragment="",
        )
    )

    return urlunparse(
        cleaned
    )


def same_or_subdomain(
    url: str,
    base_url: str,
) -> bool:

    try:

        target_host = (
            urlparse(
                url
            )
            .hostname
            or ""
        ).lower()

        base_host = (
            urlparse(
                base_url
            )
            .hostname
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
        target_host
        == base_host
        or target_host.endswith(
            "."
            + base_host
        )
        or base_host.endswith(
            "."
            + target_host
        )
    )


def is_probably_html_url(
    url: str,
) -> bool:

    lower = (
        url.lower()
    )

    blocked_extensions = (

        ".jpg",

        ".jpeg",

        ".png",

        ".gif",

        ".svg",

        ".webp",

        ".zip",

        ".hwp",

        ".hwpx",

        ".pdf",

        ".xls",

        ".xlsx",

        ".doc",

        ".docx",

        ".ppt",

        ".pptx",
    )

    return not any(
        lower.endswith(
            extension
        )
        for extension
        in blocked_extensions
    )


def link_has_discovery_hint(
    label: str,
    href: str,
) -> bool:

    haystack = (
        normalize_space(
            label
            + " "
            + href
        )
        .lower()
    )

    if contains_target(
        haystack
    ):

        return True

    return any(
        term.lower()
        in haystack
        for term
        in LINK_HINT_TERMS
    )


def extract_links(
    html: str,
    *,
    base_url: str,
) -> List[
    Dict[
        str,
        str
    ]
]:

    pattern = re.compile(
        r"""(?is)
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
        re.VERBOSE,
    )

    results = []

    seen = set()

    for match in (
        pattern.finditer(
            html
        )
    ):

        href = (

            match.group(
                1
            )

            or match.group(
                2
            )

            or match.group(
                3
            )

            or ""
        ).strip()

        label_html = (
            match.group(
                4
            )
            or ""
        )

        label = (
            strip_html(
                label_html
            )
        )

        if not href:

            continue

        lowered = (
            href.lower()
        )

        if lowered.startswith(
            (
                "javascript:",
                "mailto:",
                "tel:",
                "#",
            )
        ):

            continue

        absolute = (
            normalize_url(
                urljoin(
                    base_url,
                    href,
                )
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
            len(
                results
            )
            >= MAX_LINKS_PER_PAGE
        ):

            break

    return results


# ============================================================
# FETCH
# ============================================================

def fetch_url(
    url: str,
) -> FetchResult:

    try:

        response = (
            requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
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
    )

    text = (
        response.text
        or ""
    )

    if (
        len(
            text
        )
        > MAX_CONTENT_LENGTH
    ):

        text = (
            text[
                :MAX_CONTENT_LENGTH
            ]
        )

    return FetchResult(

        url=url,

        http_status=(
            response.status_code
        ),

        content_type=(
            content_type
        ),

        text=text,

        error=None,

        final_url=(
            response.url
        ),
    )


# ============================================================
# SEARCH URL CANDIDATES
# ============================================================

def build_site_search_candidates(
    base_url: str,
) -> List[str]:

    """
    지자체 사이트마다 검색 endpoint가 다르므로
    일반적으로 많이 쓰이는 검색 URL 형태를 후보로 만든다.

    이 단계에서는 특정 사이트 구조를 하드코딩 확정하지 않는다.
    실제 response에서 target text / 관련 링크가 확인될 때만
    의미 있는 endpoint로 취급한다.
    """

    encoded = (
        requests.utils.quote(
            TARGET_NAME
        )
    )

    candidates = [

        urljoin(
            base_url,
            f"search/search.do?query={encoded}",
        ),

        urljoin(
            base_url,
            f"search.do?query={encoded}",
        ),

        urljoin(
            base_url,
            f"search?query={encoded}",
        ),

        urljoin(
            base_url,
            f"search?keyword={encoded}",
        ),

        urljoin(
            base_url,
            f"search?searchKeyword={encoded}",
        ),

        urljoin(
            base_url,
            f"portal/search/search.do?query={encoded}",
        ),

        urljoin(
            base_url,
            f"common/search.do?query={encoded}",
        ),

        urljoin(
            base_url,
            f"search/search.jsp?query={encoded}",
        ),
    ]

    result = []

    seen = set()

    for url in candidates:

        normalized = (
            normalize_url(
                url
            )
        )

        if normalized in seen:

            continue

        seen.add(
            normalized
        )

        result.append(
            normalized
        )

    return result


# ============================================================
# NOTICE NUMBER EXTRACTION
# ============================================================

NOTICE_PATTERNS = [

    re.compile(
        r"((?:서울특별시|부산광역시|대구광역시|인천광역시|"
        r"광주광역시|대전광역시|울산광역시|세종특별자치시|"
        r"경기도|강원특별자치도|충청북도|충청남도|"
        r"전북특별자치도|전라남도|경상북도|경상남도|"
        r"제주특별자치도|"
        r"[가-힣]+시|[가-힣]+군|[가-힣]+구)"
        r"\s*고시\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호?)"
    ),

    re.compile(
        r"(고시\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호?)"
    ),

    re.compile(
        r"((?:제)?\d{4}\s*[-–]\s*\d+\s*호)"
    ),
]


DATE_PATTERNS = [

    re.compile(
        r"(20\d{2})[.\-/년]\s*"
        r"(0?[1-9]|1[0-2])[.\-/월]\s*"
        r"(0?[1-9]|[12]\d|3[01])(?:일)?"
    ),

    re.compile(
        r"(20\d{2})(0[1-9]|1[0-2])([0-3]\d)"
    ),
]


def extract_notice_numbers(
    text: str,
) -> List[str]:

    values = []

    seen = set()

    for pattern in (
        NOTICE_PATTERNS
    ):

        for match in (
            pattern.finditer(
                text
            )
        ):

            value = (
                normalize_space(
                    match.group(
                        1
                    )
                )
            )

            if (
                value
                and value
                not in seen
            ):

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

    for pattern in (
        DATE_PATTERNS
    ):

        for match in (
            pattern.finditer(
                text
            )
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

            except Exception:

                continue

            if not (
                1
                <= month
                <= 12
                and 1
                <= day
                <= 31
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
# PAGE CLASSIFICATION
# ============================================================

def classify_page(
    *,
    region: str,
    agency: str,
    url: str,
    html: str,
) -> Dict[str, Any]:

    text = (
        strip_html(
            html
        )
    )

    target_found = (
        contains_target(
            text
        )
    )

    notice_context = (
        contains_notice_context(
            text
        )
    )

    strong_notice_context = (
        has_strong_notice_context(
            text
        )
    )

    notice_numbers = (
        extract_notice_numbers(
            text
        )
    )

    dates = (
        extract_dates(
            text
        )
    )

    search_page = (
        is_search_page(
            text,
            url,
        )
    )

    zero_search_result = (
        has_zero_search_result(
            text
        )
    )

    notice_number_evidence = (
        bool(
            notice_numbers
        )
    )

    date_evidence = (
        bool(
            dates
        )
    )

    # --------------------------------------------------------
    # 실제 문서 evidence
    #
    # 검색결과 페이지가 아니라면 자체적으로 document page
    # 후보로 인정할 수 있다.
    #
    # 검색결과 페이지는 최소한 고시번호 또는 날짜가 있어야
    # document evidence를 가진 것으로 본다.
    # --------------------------------------------------------

    document_evidence = (
        notice_number_evidence
        or date_evidence
        or (
            not search_page
        )
    )

    # --------------------------------------------------------
    # Positive policy
    # --------------------------------------------------------

    positive = (
        target_found
        and not zero_search_result
        and strong_notice_context
        and document_evidence
    )

    # 검색어 echo만 있는 search page 방어
    if (
        search_page
        and not notice_number_evidence
        and not date_evidence
    ):

        positive = False

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

        "strong_notice_context":
            strong_notice_context,

        "search_page":
            search_page,

        "zero_search_result":
            zero_search_result,

        "notice_numbers":
            notice_numbers,

        "notice_number_evidence":
            notice_number_evidence,

        "dates":
            dates,

        "date_evidence":
            date_evidence,

        "document_evidence":
            document_evidence,

        "positive":
            positive,

        "preview":
            (
                build_preview(
                    text
                )
                if target_found
                else ""
            ),
    }


# ============================================================
# RESULT RECORD HELPER
# ============================================================

def build_page_record(
    *,
    requested_url: str,
    result: FetchResult,
    classification: Dict[str, Any],
    label: Optional[str] = None,
) -> Dict[str, Any]:

    record: Dict[str, Any] = {

        "url":
            requested_url,

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

        "strong_notice_context":
            classification[
                "strong_notice_context"
            ],

        "search_page":
            classification[
                "search_page"
            ],

        "zero_search_result":
            classification[
                "zero_search_result"
            ],

        "document_evidence":
            classification[
                "document_evidence"
            ],

        "positive":
            classification[
                "positive"
            ],

        "notice_numbers":
            classification[
                "notice_numbers"
            ],

        "notice_number_evidence":
            classification[
                "notice_number_evidence"
            ],

        "dates":
            classification[
                "dates"
            ],

        "date_evidence":
            classification[
                "date_evidence"
            ],

        "preview":
            classification[
                "preview"
            ],
    }

    if label is not None:

        record[
            "label"
        ] = label

    return record


# ============================================================
# DISCOVERY
# ============================================================

site_results: List[
    Dict[
        str,
        Any
    ]
] = []

positive_candidates: List[
    Dict[
        str,
        Any
    ]
] = []

visited_urls: Set[str] = set()

request_count = 0

http_success_count = 0

page_parse_count = 0

transport_error_count = 0


print(
    "============================================================"
)

print(
    "DEVELOPMENT DENSITY MANAGEMENT AREA OFFICIAL GAZETTE DISCOVERY"
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

print()


for site_index, site_seed in enumerate(
    OFFICIAL_SITE_SEEDS,
    start=1,
):

    region = (
        site_seed[
            "region"
        ]
    )

    agency = (
        site_seed[
            "agency"
        ]
    )

    base_url = (
        site_seed[
            "base_url"
        ]
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        f"SITE {site_index}:",
        region,
        "/",
        base_url,
    )

    # ========================================================
    # 1. Root page
    # ========================================================

    root_result = (
        fetch_url(
            base_url
        )
    )

    request_count += 1

    if (
        root_result.error
    ):

        transport_error_count += 1

        print(
            "Root transport error:",
            root_result.error,
        )

        site_results.append(
            {
                "region":
                    region,

                "agency":
                    agency,

                "base_url":
                    base_url,

                "root_http":
                    root_result.http_status,

                "root_error":
                    root_result.error,

                "search_attempts":
                    [],

                "secondary_pages":
                    [],

                "positive_candidate_count":
                    0,
            }
        )

        continue

    if (
        root_result.http_status
        == 200
    ):

        http_success_count += 1

    root_html = (
        root_result.text
    )

    root_classification = (
        classify_page(
            region=region,
            agency=agency,
            url=(
                root_result.final_url
                or base_url
            ),
            html=root_html,
        )
    )

    page_parse_count += 1

    root_links = (
        extract_links(
            root_html,
            base_url=(
                root_result.final_url
                or base_url
            ),
        )
    )

    search_attempts = []

    secondary_page_records = []

    local_positive = []

    # ========================================================
    # 2. Generic site search endpoint probes
    # ========================================================

    search_urls = (
        build_site_search_candidates(
            base_url
        )
    )

    for search_url in (
        search_urls
    ):

        normalized_search_url = (
            normalize_url(
                search_url
            )
        )

        if (
            normalized_search_url
            in visited_urls
        ):

            continue

        visited_urls.add(
            normalized_search_url
        )

        result = (
            fetch_url(
                normalized_search_url
            )
        )

        request_count += 1

        if (
            result.error
        ):

            transport_error_count += 1

            search_attempts.append(
                {
                    "url":
                        normalized_search_url,

                    "http_status":
                        None,

                    "error":
                        result.error,

                    "target_found":
                        False,

                    "notice_context":
                        False,

                    "strong_notice_context":
                        False,

                    "search_page":
                        True,

                    "zero_search_result":
                        False,

                    "document_evidence":
                        False,

                    "positive":
                        False,

                    "notice_numbers":
                        [],

                    "dates":
                        [],
                }
            )

            continue

        if (
            result.http_status
            == 200
        ):

            http_success_count += 1

        classification = (
            classify_page(
                region=region,
                agency=agency,
                url=(
                    result.final_url
                    or normalized_search_url
                ),
                html=(
                    result.text
                ),
            )
        )

        page_parse_count += 1

        search_attempts.append(
            build_page_record(
                requested_url=(
                    normalized_search_url
                ),
                result=result,
                classification=classification,
            )
        )

        if (
            classification[
                "positive"
            ]
        ):

            local_positive.append(
                classification
            )

            positive_candidates.append(
                classification
            )

        # ----------------------------------------------------
        # search result page 내부 링크에서 후보 추출
        # ----------------------------------------------------

        links = (
            extract_links(
                result.text,
                base_url=(
                    result.final_url
                    or normalized_search_url
                ),
            )
        )

        candidate_links = []

        for link in links:

            if not (
                same_or_subdomain(
                    link[
                        "url"
                    ],
                    base_url,
                )
            ):

                continue

            if not (
                is_probably_html_url(
                    link[
                        "url"
                    ]
                )
            ):

                continue

            if not (
                link_has_discovery_hint(
                    link[
                        "label"
                    ],
                    link[
                        "url"
                    ],
                )
            ):

                continue

            candidate_links.append(
                link
            )

        # ----------------------------------------------------
        # 최대 secondary page 제한
        # ----------------------------------------------------

        for link in (
            candidate_links[
                :MAX_SECONDARY_PAGES_PER_SITE
            ]
        ):

            candidate_url = (
                normalize_url(
                    link[
                        "url"
                    ]
                )
            )

            if (
                candidate_url
                in visited_urls
            ):

                continue

            visited_urls.add(
                candidate_url
            )

            secondary_result = (
                fetch_url(
                    candidate_url
                )
            )

            request_count += 1

            if (
                secondary_result.error
            ):

                transport_error_count += 1

                secondary_page_records.append(
                    {
                        "url":
                            candidate_url,

                        "label":
                            link[
                                "label"
                            ],

                        "http_status":
                            None,

                        "error":
                            secondary_result.error,

                        "target_found":
                            False,

                        "notice_context":
                            False,

                        "strong_notice_context":
                            False,

                        "search_page":
                            False,

                        "zero_search_result":
                            False,

                        "document_evidence":
                            False,

                        "positive":
                            False,

                        "notice_numbers":
                            [],

                        "dates":
                            [],
                    }
                )

                continue

            if (
                secondary_result.http_status
                == 200
            ):

                http_success_count += 1

            secondary_classification = (
                classify_page(
                    region=region,
                    agency=agency,
                    url=(
                        secondary_result.final_url
                        or candidate_url
                    ),
                    html=(
                        secondary_result.text
                    ),
                )
            )

            page_parse_count += 1

            secondary_record = (
                build_page_record(
                    requested_url=(
                        candidate_url
                    ),
                    result=(
                        secondary_result
                    ),
                    classification=(
                        secondary_classification
                    ),
                    label=(
                        link[
                            "label"
                        ]
                    ),
                )
            )

            secondary_page_records.append(
                secondary_record
            )

            if (
                secondary_classification[
                    "positive"
                ]
            ):

                local_positive.append(
                    secondary_classification
                )

                positive_candidates.append(
                    secondary_classification
                )

            time.sleep(
                REQUEST_SLEEP
            )

        time.sleep(
            REQUEST_SLEEP
        )

    # ========================================================
    # 3. Root page links 직접 탐색
    # ========================================================

    root_candidate_links = []

    for link in root_links:

        if not (
            same_or_subdomain(
                link[
                    "url"
                ],
                base_url,
            )
        ):

            continue

        if not (
            is_probably_html_url(
                link[
                    "url"
                ]
            )
        ):

            continue

        if not (
            link_has_discovery_hint(
                link[
                    "label"
                ],
                link[
                    "url"
                ],
            )
        ):

            continue

        root_candidate_links.append(
            link
        )

    remaining = max(
        0,
        MAX_SECONDARY_PAGES_PER_SITE
        - len(
            secondary_page_records
        ),
    )

    for link in (
        root_candidate_links[
            :remaining
        ]
    ):

        candidate_url = (
            normalize_url(
                link[
                    "url"
                ]
            )
        )

        if (
            candidate_url
            in visited_urls
        ):

            continue

        visited_urls.add(
            candidate_url
        )

        result = (
            fetch_url(
                candidate_url
            )
        )

        request_count += 1

        if (
            result.error
        ):

            transport_error_count += 1

            secondary_page_records.append(
                {
                    "url":
                        candidate_url,

                    "label":
                        link[
                            "label"
                        ],

                    "http_status":
                        None,

                    "error":
                        result.error,

                    "target_found":
                        False,

                    "notice_context":
                        False,

                    "strong_notice_context":
                        False,

                    "search_page":
                        False,

                    "zero_search_result":
                        False,

                    "document_evidence":
                        False,

                    "positive":
                        False,

                    "notice_numbers":
                        [],

                    "dates":
                        [],
                }
            )

            continue

        if (
            result.http_status
            == 200
        ):

            http_success_count += 1

        classification = (
            classify_page(
                region=region,
                agency=agency,
                url=(
                    result.final_url
                    or candidate_url
                ),
                html=(
                    result.text
                ),
            )
        )

        page_parse_count += 1

        record = (
            build_page_record(
                requested_url=(
                    candidate_url
                ),
                result=result,
                classification=classification,
                label=(
                    link[
                        "label"
                    ]
                ),
            )
        )

        secondary_page_records.append(
            record
        )

        if (
            classification[
                "positive"
            ]
        ):

            local_positive.append(
                classification
            )

            positive_candidates.append(
                classification
            )

        time.sleep(
            REQUEST_SLEEP
        )

    print(
        "Root HTTP:",
        root_result.http_status,
    )

    print(
        "Search attempts:",
        len(
            search_attempts
        ),
    )

    print(
        "Secondary pages:",
        len(
            secondary_page_records
        ),
    )

    print(
        "Positive candidates:",
        len(
            local_positive
        ),
    )

    for candidate in (
        local_positive[
            :5
        ]
    ):

        print(
            "  POSITIVE:",
            candidate.get(
                "url"
            ),
        )

        print(
            "    Notice:",
            candidate.get(
                "notice_numbers"
            ),
        )

        print(
            "    Dates:",
            candidate.get(
                "dates"
            ),
        )

        print(
            "    Search page:",
            candidate.get(
                "search_page"
            ),
        )

        print(
            "    Zero result:",
            candidate.get(
                "zero_search_result"
            ),
        )

        print(
            "    Strong context:",
            candidate.get(
                "strong_notice_context"
            ),
        )

        print(
            "    Preview:",
            candidate.get(
                "preview"
            ),
        )

    site_results.append(
        {
            "region":
                region,

            "agency":
                agency,

            "base_url":
                base_url,

            "root_http":
                root_result.http_status,

            "root_final_url":
                root_result.final_url,

            "root_content_type":
                root_result.content_type,

            "root_target_found":
                root_classification[
                    "target_found"
                ],

            "root_search_page":
                root_classification[
                    "search_page"
                ],

            "root_zero_search_result":
                root_classification[
                    "zero_search_result"
                ],

            "search_attempts":
                search_attempts,

            "secondary_pages":
                secondary_page_records,

            "positive_candidate_count":
                len(
                    local_positive
                ),
        }
    )

    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# DEDUPLICATE POSITIVE
# ============================================================

deduped_positive = []

seen_positive = set()

for candidate in (
    positive_candidates
):

    key = (

        candidate.get(
            "region"
        ),

        normalize_url(
            str(
                candidate.get(
                    "url"
                )
                or ""
            )
        ),
    )

    if key in seen_positive:

        continue

    seen_positive.add(
        key
    )

    deduped_positive.append(
        candidate
    )


# ============================================================
# FALSE POSITIVE DIAGNOSTICS
# ============================================================

zero_result_positive_pages = []

for site in site_results:

    combined_records = (

        site.get(
            "search_attempts",
            []
        )

        + site.get(
            "secondary_pages",
            []
        )
    )

    for record in combined_records:

        if (
            record.get(
                "zero_search_result"
            )
            is True
            and record.get(
                "positive"
            )
            is True
        ):

            zero_result_positive_pages.append(
                {
                    "region":
                        site.get(
                            "region"
                        ),

                    "url":
                        record.get(
                            "final_url"
                        )
                        or record.get(
                            "url"
                        ),

                    "preview":
                        record.get(
                            "preview"
                        ),
                }
            )


# ============================================================
# RESOLUTION
# ============================================================

if deduped_positive:

    resolution = (
        "OFFICIAL_POSITIVE_NOTICE_CANDIDATE_DISCOVERED"
    )

    runtime_registration_blocked = (
        True
    )

    next_action = (
        "공식 문서 원문을 개별 검증하고 "
        "지정 범위 / 현재 유효 여부 / 행정구역을 확정한 뒤 "
        "positive PNU 및 spatial dataset을 역탐색한다."
    )

else:

    resolution = (
        "OFFICIAL_GAZETTE_DIRECT_DISCOVERY_COMPLETED_NO_POSITIVE"
    )

    runtime_registration_blocked = (
        True
    )

    next_action = (
        "시군구 단위 공보 시스템 또는 "
        "국가기록 / 토지이음 / 지자체 도시계획 고시 DB로 "
        "탐색 범위를 확장한다."
    )


# ============================================================
# OUTPUT DATA
# ============================================================

output_data = {

    "step":
        (
            "STEP 17-21-C-16-8-C "
            "Development Density Management Area "
            "Official Gazette Discovery"
        ),

    "target": {

        "name":
            TARGET_NAME,

        "standard_code":
            STANDARD_CODE,
    },

    "method": {

        "search_engine_scraping":
            False,

        "official_site_direct_probe":
            True,

        "official_site_count":
            len(
                OFFICIAL_SITE_SEEDS
            ),

        "request_timeout":
            REQUEST_TIMEOUT,

        "max_secondary_pages_per_site":
            MAX_SECONDARY_PAGES_PER_SITE,

        "positive_policy": {

            "target_required":
                True,

            "zero_result_search_page_rejected":
                True,

            "strong_notice_context_required":
                True,

            "document_evidence_required":
                True,

            "search_echo_only_rejected":
                True,
        },
    },

    "summary": {

        "request_count":
            request_count,

        "http_success_count":
            http_success_count,

        "page_parse_count":
            page_parse_count,

        "transport_error_count":
            transport_error_count,

        "positive_candidate_count":
            len(
                deduped_positive
            ),

        "zero_result_positive_page_count":
            len(
                zero_result_positive_pages
            ),
    },

    "positive_candidates":
        deduped_positive,

    "false_positive_diagnostics": {

        "zero_result_positive_pages":
            zero_result_positive_pages,
    },

    "site_results":
        site_results,

    "resolution":
        resolution,

    "runtime_registration_blocked":
        runtime_registration_blocked,

    "site_false_interpretation_blocked":
        True,

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
    "Official site count:",
    len(
        OFFICIAL_SITE_SEEDS
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
    "Parsed page count:",
    page_parse_count,
)

print(
    "Transport error count:",
    transport_error_count,
)

print(
    "Positive candidate count:",
    len(
        deduped_positive
    ),
)

print(
    "Zero-result positive leakage:",
    len(
        zero_result_positive_pages
    ),
)

print()


if deduped_positive:

    print(
        "POSITIVE NOTICE CANDIDATES"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, candidate in enumerate(
        deduped_positive,
        start=1,
    ):

        print(
            f"[{index}]",
            candidate.get(
                "region"
            ),
        )

        print(
            "URL:",
            candidate.get(
                "url"
            ),
        )

        print(
            "Notice numbers:",
            candidate.get(
                "notice_numbers"
            ),
        )

        print(
            "Dates:",
            candidate.get(
                "dates"
            ),
        )

        print(
            "Search page:",
            candidate.get(
                "search_page"
            ),
        )

        print(
            "Zero result:",
            candidate.get(
                "zero_search_result"
            ),
        )

        print(
            "Strong notice context:",
            candidate.get(
                "strong_notice_context"
            ),
        )

        print(
            "Document evidence:",
            candidate.get(
                "document_evidence"
            ),
        )

        print(
            "Preview:",
            candidate.get(
                "preview"
            ),
        )

        print()

else:

    print(
        "No official positive notice candidate confirmed."
    )


if zero_result_positive_pages:

    print()

    print(
        "WARNING: ZERO-RESULT POSITIVE LEAKAGE"
    )

    print(
        "------------------------------------------------------------"
    )

    for item in zero_result_positive_pages:

        print(
            item
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

    "official site seeds exist": (
        len(
            OFFICIAL_SITE_SEEDS
        )
        >= 10
    ),

    "official sites include Seoul": (
        any(
            item.get(
                "region"
            )
            == "서울특별시"
            for item
            in OFFICIAL_SITE_SEEDS
        )
    ),

    "official direct probe used": (
        output_data[
            "method"
        ][
            "official_site_direct_probe"
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

    "requests executed": (
        request_count
        > 0
    ),

    "at least one page parsed": (
        page_parse_count
        > 0
    ),

    "site result accounting": (
        len(
            site_results
        )
        == len(
            OFFICIAL_SITE_SEEDS
        )
    ),

    "positive candidates unique": (
        len(
            {
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
                for item
                in deduped_positive
            }
        )
        == len(
            deduped_positive
        )
    ),

    # --------------------------------------------------------
    # False-positive regression
    # --------------------------------------------------------

    "zero-result search pages never positive": (
        len(
            zero_result_positive_pages
        )
        == 0
    ),

    "positive candidates have target": (
        all(
            item.get(
                "target_found"
            )
            is True
            for item
            in deduped_positive
        )
    ),

    "positive candidates have strong context": (
        all(
            item.get(
                "strong_notice_context"
            )
            is True
            for item
            in deduped_positive
        )
    ),

    "positive candidates have document evidence": (
        all(
            item.get(
                "document_evidence"
            )
            is True
            for item
            in deduped_positive
        )
    ),

    "positive candidates are not zero-result pages": (
        all(
            item.get(
                "zero_search_result"
            )
            is not True
            for item
            in deduped_positive
        )
    ),

    "runtime registration remains blocked": (
        runtime_registration_blocked
        is True
    ),

    "SITE FALSE remains blocked": (
        output_data[
            "site_false_interpretation_blocked"
        ]
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


for name, passed in (
    validations.items()
):

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

    raise AssertionError(
        "Development density management area "
        "official gazette discovery regression failed"
    )