# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-D
Development Density Management Area Municipal Gazette Discovery

목표
======================================================================
광역자치단체 공식 홈페이지 직접 탐색에서도 발견되지 않은
개발밀도관리구역 실제 지정 / 변경 / 해제 사례를

    시 / 군 / 구

단위 공식 행정기관 웹사이트에서 탐색한다.

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700


배경
======================================================================
STEP 17-21-C-16-8-C에서

    17개 광역자치단체 공식 홈페이지 직접 탐색

을 수행했으나

    Positive candidate count: 0

이었다.

따라서 이번 단계에서는 탐색 범위를

    광역자치단체
        ↓
    기초자치단체 시 / 군 / 구

공식 홈페이지 및 고시/공고/공보/도시계획 관련 페이지로 확장한다.


중요
======================================================================
이 테스트는 discovery test이다.

따라서 positive candidate가 0건이어도 테스트 실패가 아니다.

또한 다음을 절대 수행하지 않는다.

1. 검색 결과 페이지에 TARGET_NAME이 단순 노출되었다는 이유만으로
   positive notice로 판단하지 않는다.

2. "검색결과 0건" 페이지를 positive로 판단하지 않는다.

3. 문서 evidence가 없는 페이지를 positive로 판단하지 않는다.

4. positive notice 미발견을 SITE FALSE로 해석하지 않는다.

5. runtime spatial condition registry에 즉시 등록하지 않는다.

실제 runtime 등록은 다음 evidence가 확보된 뒤에만 가능하다.

    공식 지정/변경/해제 원문
    +
    행정구역
    +
    현재 유효 여부
    +
    지정 범위
    +
    positive parcel/PNU
    +
    대응 가능한 spatial source 또는 공식 공간정보
"""

from __future__ import annotations

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
    / "development_density_management_area_municipal_gazette_discovery.json"
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

REQUEST_SLEEP = 0.25

MAX_CONTENT_LENGTH = (
    2_000_000
)

MAX_LINKS_PER_PAGE = (
    120
)

MAX_SECONDARY_PAGES_PER_SITE = (
    30
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
# MUNICIPAL SITE SEEDS
# ============================================================
#
# 1차 탐색용 시/군/구 공식 사이트 seed.
#
# 모든 전국 기초자치단체를 한 번에 넣으면
# 요청 수가 지나치게 커질 수 있으므로,
#
# - 수도권
# - 광역시 주요 자치구
# - 개발압력이 높은 주요 도시
#
# 중심으로 시작한다.
#
# positive가 없으면 이후 E 단계에서 전국 시군구 seed를
# 행정구역 코드 기반으로 자동 생성/확장한다.
# ============================================================

MUNICIPAL_SITE_SEEDS: List[Dict[str, str]] = [

    # --------------------------------------------------------
    # 서울
    # --------------------------------------------------------

    {
        "region": "서울특별시",
        "municipality": "강남구",
        "agency": "서울특별시 강남구",
        "base_url": "https://www.gangnam.go.kr/",
    },

    {
        "region": "서울특별시",
        "municipality": "서초구",
        "agency": "서울특별시 서초구",
        "base_url": "https://www.seocho.go.kr/",
    },

    {
        "region": "서울특별시",
        "municipality": "송파구",
        "agency": "서울특별시 송파구",
        "base_url": "https://www.songpa.go.kr/",
    },

    {
        "region": "서울특별시",
        "municipality": "강서구",
        "agency": "서울특별시 강서구",
        "base_url": "https://www.gangseo.seoul.kr/",
    },

    {
        "region": "서울특별시",
        "municipality": "구로구",
        "agency": "서울특별시 구로구",
        "base_url": "https://www.guro.go.kr/",
    },

    {
        "region": "서울특별시",
        "municipality": "동대문구",
        "agency": "서울특별시 동대문구",
        "base_url": "https://www.ddm.go.kr/",
    },

    {
        "region": "서울특별시",
        "municipality": "노원구",
        "agency": "서울특별시 노원구",
        "base_url": "https://www.nowon.kr/",
    },

    # --------------------------------------------------------
    # 경기
    # --------------------------------------------------------

    {
        "region": "경기도",
        "municipality": "수원시",
        "agency": "경기도 수원시",
        "base_url": "https://www.suwon.go.kr/",
    },

    {
        "region": "경기도",
        "municipality": "성남시",
        "agency": "경기도 성남시",
        "base_url": "https://www.seongnam.go.kr/",
    },

    {
        "region": "경기도",
        "municipality": "용인시",
        "agency": "경기도 용인시",
        "base_url": "https://www.yongin.go.kr/",
    },

    {
        "region": "경기도",
        "municipality": "고양시",
        "agency": "경기도 고양시",
        "base_url": "https://www.goyang.go.kr/",
    },

    {
        "region": "경기도",
        "municipality": "화성시",
        "agency": "경기도 화성시",
        "base_url": "https://www.hscity.go.kr/",
    },

    {
        "region": "경기도",
        "municipality": "남양주시",
        "agency": "경기도 남양주시",
        "base_url": "https://www.nyj.go.kr/",
    },

    {
        "region": "경기도",
        "municipality": "시흥시",
        "agency": "경기도 시흥시",
        "base_url": "https://www.siheung.go.kr/",
    },

    {
        "region": "경기도",
        "municipality": "김포시",
        "agency": "경기도 김포시",
        "base_url": "https://www.gimpo.go.kr/",
    },

    {
        "region": "경기도",
        "municipality": "파주시",
        "agency": "경기도 파주시",
        "base_url": "https://www.paju.go.kr/",
    },

    {
        "region": "경기도",
        "municipality": "평택시",
        "agency": "경기도 평택시",
        "base_url": "https://www.pyeongtaek.go.kr/",
    },

    # --------------------------------------------------------
    # 인천
    # --------------------------------------------------------

    {
        "region": "인천광역시",
        "municipality": "남동구",
        "agency": "인천광역시 남동구",
        "base_url": "https://www.namdong.go.kr/",
    },

    {
        "region": "인천광역시",
        "municipality": "서구",
        "agency": "인천광역시 서구",
        "base_url": "https://www.seo.incheon.kr/",
    },

    {
        "region": "인천광역시",
        "municipality": "연수구",
        "agency": "인천광역시 연수구",
        "base_url": "https://www.yeonsu.go.kr/",
    },

    # --------------------------------------------------------
    # 부산
    # --------------------------------------------------------

    {
        "region": "부산광역시",
        "municipality": "강서구",
        "agency": "부산광역시 강서구",
        "base_url": "https://www.bsgangseo.go.kr/",
    },

    {
        "region": "부산광역시",
        "municipality": "해운대구",
        "agency": "부산광역시 해운대구",
        "base_url": "https://www.haeundae.go.kr/",
    },

    # --------------------------------------------------------
    # 대구
    # --------------------------------------------------------

    {
        "region": "대구광역시",
        "municipality": "달서구",
        "agency": "대구광역시 달서구",
        "base_url": "https://www.dalseo.daegu.kr/",
    },

    {
        "region": "대구광역시",
        "municipality": "달성군",
        "agency": "대구광역시 달성군",
        "base_url": "https://www.dalseong.daegu.kr/",
    },

    # --------------------------------------------------------
    # 대전
    # --------------------------------------------------------

    {
        "region": "대전광역시",
        "municipality": "유성구",
        "agency": "대전광역시 유성구",
        "base_url": "https://www.yuseong.go.kr/",
    },

    # --------------------------------------------------------
    # 울산
    # --------------------------------------------------------

    {
        "region": "울산광역시",
        "municipality": "울주군",
        "agency": "울산광역시 울주군",
        "base_url": "https://www.ulju.ulsan.kr/",
    },

    # --------------------------------------------------------
    # 충남
    # --------------------------------------------------------

    {
        "region": "충청남도",
        "municipality": "천안시",
        "agency": "충청남도 천안시",
        "base_url": "https://www.cheonan.go.kr/",
    },

    {
        "region": "충청남도",
        "municipality": "아산시",
        "agency": "충청남도 아산시",
        "base_url": "https://www.asan.go.kr/",
    },

    {
        "region": "충청남도",
        "municipality": "당진시",
        "agency": "충청남도 당진시",
        "base_url": "https://www.dangjin.go.kr/",
    },

    # --------------------------------------------------------
    # 충북
    # --------------------------------------------------------

    {
        "region": "충청북도",
        "municipality": "청주시",
        "agency": "충청북도 청주시",
        "base_url": "https://www.cheongju.go.kr/",
    },

    # --------------------------------------------------------
    # 전북
    # --------------------------------------------------------

    {
        "region": "전북특별자치도",
        "municipality": "전주시",
        "agency": "전북특별자치도 전주시",
        "base_url": "https://www.jeonju.go.kr/",
    },

    # --------------------------------------------------------
    # 전남
    # --------------------------------------------------------

    {
        "region": "전라남도",
        "municipality": "목포시",
        "agency": "전라남도 목포시",
        "base_url": "https://www.mokpo.go.kr/",
    },

    {
        "region": "전라남도",
        "municipality": "순천시",
        "agency": "전라남도 순천시",
        "base_url": "https://www.suncheon.go.kr/",
    },

    # --------------------------------------------------------
    # 경북
    # --------------------------------------------------------

    {
        "region": "경상북도",
        "municipality": "포항시",
        "agency": "경상북도 포항시",
        "base_url": "https://www.pohang.go.kr/",
    },

    {
        "region": "경상북도",
        "municipality": "구미시",
        "agency": "경상북도 구미시",
        "base_url": "https://www.gumi.go.kr/",
    },

    # --------------------------------------------------------
    # 경남
    # --------------------------------------------------------

    {
        "region": "경상남도",
        "municipality": "창원시",
        "agency": "경상남도 창원시",
        "base_url": "https://www.changwon.go.kr/",
    },

    {
        "region": "경상남도",
        "municipality": "김해시",
        "agency": "경상남도 김해시",
        "base_url": "https://www.gimhae.go.kr/",
    },

    # --------------------------------------------------------
    # 제주
    # --------------------------------------------------------

    {
        "region": "제주특별자치도",
        "municipality": "제주시",
        "agency": "제주특별자치도 제주시",
        "base_url": "https://www.jejusi.go.kr/",
    },

    {
        "region": "제주특별자치도",
        "municipality": "서귀포시",
        "agency": "제주특별자치도 서귀포시",
        "base_url": "https://www.seogwipo.go.kr/",
    },
]


# ============================================================
# DISCOVERY TERMS
# ============================================================

NOTICE_CONTEXT_TERMS = [

    "고시",
    "공고",
    "지정",
    "변경",
    "해제",
    "결정",
    "도시관리계획",
    "도시계획",
    "지형도면",
]


STRONG_NOTICE_CONTEXT_TERMS = [

    "지정",
    "변경",
    "해제",
    "도시관리계획 결정",
    "도시관리계획",
    "지형도면",
]


DOCUMENT_EVIDENCE_TERMS = [

    "고시 제",
    "고시제",
    "공고 제",
    "공고제",
    "첨부파일",
    "담당부서",
    "작성일",
    "등록일",
    "게시일",
    "고시일",
]


ZERO_RESULT_TERMS = [

    "검색결과 0건",
    "검색 결과 0건",
    "검색결과가 없습니다",
    "검색 결과가 없습니다",
    "검색된 결과가 없습니다",
    "검색 결과 없음",
    "검색결과 없음",
    "총 0건",
    "총0건",
    "0건 검색",
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
    "cityplan",
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
        str(
            value
            or ""
        ),
    )


def contains_target(
    value: str,
) -> bool:

    return (
        normalize_target_text(
            TARGET_NAME
        )
        in normalize_target_text(
            value
        )
    )


def contains_any(
    value: str,
    terms: List[str],
) -> bool:

    text = normalize_space(
        value
    )

    return any(
        term
        in text
        for term
        in terms
    )


def is_zero_result_page(
    value: str,
) -> bool:

    return contains_any(
        value,
        ZERO_RESULT_TERMS,
    )


def has_notice_context(
    value: str,
) -> bool:

    return contains_any(
        value,
        NOTICE_CONTEXT_TERMS,
    )


def has_strong_notice_context(
    value: str,
) -> bool:

    return contains_any(
        value,
        STRONG_NOTICE_CONTEXT_TERMS,
    )


def has_document_evidence(
    value: str,
) -> bool:

    return contains_any(
        value,
        DOCUMENT_EVIDENCE_TERMS,
    )


def build_preview(
    text: str,
    *,
    radius: int = 240,
) -> str:

    normalized = normalize_space(
        text
    )

    variants = [

        "개발밀도관리구역",
        "개발밀도 관리구역",
        "개발 밀도 관리구역",
    ]

    index = -1

    matched = ""

    for variant in variants:

        index = normalized.find(
            variant
        )

        if index >= 0:

            matched = variant

            break

    if index < 0:

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
            matched
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

        parsed = urlparse(
            url
        )

    except Exception:

        return url

    query_items = []

    for key, value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        if key.lower() in {

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

    cleaned = parsed._replace(
        query=urlencode(
            query_items,
            doseq=True,
        ),
        fragment="",
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
        .split(
            "?",
            1,
        )[0]
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

    haystack = normalize_space(
        (
            label
            or ""
        )
        + " "
        + (
            href
            or ""
        )
    ).lower()

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


# ============================================================
# LINK EXTRACTION
# ============================================================

def extract_links(
    html: str,
    *,
    base_url: str,
) -> List[Dict[str, str]]:

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

    for match in pattern.finditer(
        html
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

        label = strip_html(
            label_html
        )

        if not href:

            continue

        lowered = href.lower()

        if lowered.startswith(
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

    content_type = response.headers.get(
        "Content-Type",
        "",
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
# SEARCH URL CANDIDATES
# ============================================================

def build_site_search_candidates(
    base_url: str,
) -> List[str]:

    encoded = requests.utils.quote(
        TARGET_NAME
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

        normalized = normalize_url(
            url
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
# NOTICE EXTRACTION
# ============================================================

NOTICE_PATTERNS = [

    re.compile(
        r"("
        r"(?:서울특별시|부산광역시|대구광역시|인천광역시|"
        r"광주광역시|대전광역시|울산광역시|세종특별자치시|"
        r"경기도|강원특별자치도|충청북도|충청남도|"
        r"전북특별자치도|전라남도|경상북도|경상남도|"
        r"제주특별자치도|"
        r"[가-힣]+시|[가-힣]+군|[가-힣]+구)"
        r"\s*고시\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호?"
        r")"
    ),

    re.compile(
        r"(고시\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호?)"
    ),

    re.compile(
        r"(공고\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호?)"
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

    for pattern in NOTICE_PATTERNS:

        for match in pattern.finditer(
            text
        ):

            value = normalize_space(
                match.group(
                    1
                )
            )

            if (
                value
                and value not in seen
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

    for pattern in DATE_PATTERNS:

        for match in pattern.finditer(
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

            except Exception:

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
# PAGE CLASSIFICATION
# ============================================================

def classify_page(
    *,
    region: str,
    municipality: str,
    agency: str,
    url: str,
    html: str,
) -> Dict[str, Any]:

    text = strip_html(
        html
    )

    target_found = contains_target(
        text
    )

    zero_result = is_zero_result_page(
        text
    )

    notice_context = has_notice_context(
        text
    )

    strong_notice_context = has_strong_notice_context(
        text
    )

    document_evidence = has_document_evidence(
        text
    )

    notice_numbers = extract_notice_numbers(
        text
    )

    dates = extract_dates(
        text
    )

    has_structured_document_evidence = bool(
        notice_numbers
        or document_evidence
    )

    # ========================================================
    # POSITIVE RULE
    # ========================================================
    #
    # 단순 target 노출만으로 positive 금지.
    #
    # 필수:
    #
    # 1. target 존재
    # 2. zero-result 페이지 아님
    # 3. strong notice context
    # 4. 문서 evidence
    #
    # ========================================================

    positive = (
        target_found
        and not zero_result
        and strong_notice_context
        and has_structured_document_evidence
    )

    return {

        "region":
            region,

        "municipality":
            municipality,

        "agency":
            agency,

        "url":
            url,

        "target_found":
            target_found,

        "zero_result":
            zero_result,

        "notice_context":
            notice_context,

        "strong_notice_context":
            strong_notice_context,

        "document_evidence":
            document_evidence,

        "notice_numbers":
            notice_numbers,

        "dates":
            dates,

        "has_structured_document_evidence":
            has_structured_document_evidence,

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
# DISCOVERY STATE
# ============================================================

site_results: List[
    Dict[str, Any]
] = []

positive_candidates: List[
    Dict[str, Any]
] = []

visited_urls: Set[str] = set()

request_count = 0

http_success_count = 0

page_parse_count = 0

transport_error_count = 0

zero_result_positive_leakage = 0


# ============================================================
# CONSOLE HEADER
# ============================================================

print(
    "============================================================"
)

print(
    "DEVELOPMENT DENSITY MANAGEMENT AREA MUNICIPAL GAZETTE DISCOVERY"
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
    "Municipal seed count:",
    len(
        MUNICIPAL_SITE_SEEDS
    ),
)

print()


# ============================================================
# MAIN DISCOVERY LOOP
# ============================================================

for site_index, site_seed in enumerate(
    MUNICIPAL_SITE_SEEDS,
    start=1,
):

    region = site_seed[
        "region"
    ]

    municipality = site_seed[
        "municipality"
    ]

    agency = site_seed[
        "agency"
    ]

    base_url = site_seed[
        "base_url"
    ]

    print(
        "------------------------------------------------------------"
    )

    print(
        f"SITE {site_index}:",
        region,
        municipality,
        "/",
        base_url,
    )

    # ========================================================
    # ROOT
    # ========================================================

    root_result = fetch_url(
        base_url
    )

    request_count += 1

    if root_result.error:

        transport_error_count += 1

        print(
            "Root transport error:",
            root_result.error,
        )

        site_results.append(
            {
                "region":
                    region,

                "municipality":
                    municipality,

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

    root_html = root_result.text

    root_classification = classify_page(
        region=region,
        municipality=municipality,
        agency=agency,
        url=(
            root_result.final_url
            or base_url
        ),
        html=root_html,
    )

    page_parse_count += 1

    if (
        root_classification[
            "zero_result"
        ]
        and root_classification[
            "positive"
        ]
    ):

        zero_result_positive_leakage += 1

    root_links = extract_links(
        root_html,
        base_url=(
            root_result.final_url
            or base_url
        ),
    )

    search_attempts = []

    secondary_page_records = []

    local_positive = []

    # ========================================================
    # SEARCH ENDPOINT PROBES
    # ========================================================

    search_urls = build_site_search_candidates(
        base_url
    )

    for search_url in search_urls:

        normalized_search_url = normalize_url(
            search_url
        )

        if (
            normalized_search_url
            in visited_urls
        ):

            continue

        visited_urls.add(
            normalized_search_url
        )

        result = fetch_url(
            normalized_search_url
        )

        request_count += 1

        if result.error:

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

                    "zero_result":
                        False,

                    "positive":
                        False,
                }
            )

            continue

        if (
            result.http_status
            == 200
        ):

            http_success_count += 1

        classification = classify_page(
            region=region,
            municipality=municipality,
            agency=agency,
            url=(
                result.final_url
                or normalized_search_url
            ),
            html=result.text,
        )

        page_parse_count += 1

        if (
            classification[
                "zero_result"
            ]
            and classification[
                "positive"
            ]
        ):

            zero_result_positive_leakage += 1

        search_attempts.append(
            {
                "url":
                    normalized_search_url,

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

                "zero_result":
                    classification[
                        "zero_result"
                    ],

                "notice_context":
                    classification[
                        "notice_context"
                    ],

                "strong_notice_context":
                    classification[
                        "strong_notice_context"
                    ],

                "document_evidence":
                    classification[
                        "document_evidence"
                    ],

                "notice_numbers":
                    classification[
                        "notice_numbers"
                    ],

                "dates":
                    classification[
                        "dates"
                    ],

                "positive":
                    classification[
                        "positive"
                    ],

                "preview":
                    classification[
                        "preview"
                    ],
            }
        )

        if classification[
            "positive"
        ]:

            local_positive.append(
                classification
            )

            positive_candidates.append(
                classification
            )

        # ----------------------------------------------------
        # Search page 내부 링크
        # ----------------------------------------------------

        links = extract_links(
            result.text,
            base_url=(
                result.final_url
                or normalized_search_url
            ),
        )

        candidate_links = []

        for link in links:

            if not same_or_subdomain(
                link[
                    "url"
                ],
                base_url,
            ):

                continue

            if not is_probably_html_url(
                link[
                    "url"
                ]
            ):

                continue

            if not link_has_discovery_hint(
                link[
                    "label"
                ],
                link[
                    "url"
                ],
            ):

                continue

            candidate_links.append(
                link
            )

        for link in candidate_links[
            :MAX_SECONDARY_PAGES_PER_SITE
        ]:

            candidate_url = normalize_url(
                link[
                    "url"
                ]
            )

            if candidate_url in visited_urls:

                continue

            visited_urls.add(
                candidate_url
            )

            secondary_result = fetch_url(
                candidate_url
            )

            request_count += 1

            if secondary_result.error:

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

                        "zero_result":
                            False,

                        "positive":
                            False,
                    }
                )

                continue

            if (
                secondary_result.http_status
                == 200
            ):

                http_success_count += 1

            secondary_classification = classify_page(
                region=region,
                municipality=municipality,
                agency=agency,
                url=(
                    secondary_result.final_url
                    or candidate_url
                ),
                html=secondary_result.text,
            )

            page_parse_count += 1

            if (
                secondary_classification[
                    "zero_result"
                ]
                and secondary_classification[
                    "positive"
                ]
            ):

                zero_result_positive_leakage += 1

            secondary_record = {

                "url":
                    candidate_url,

                "final_url":
                    secondary_result.final_url,

                "label":
                    link[
                        "label"
                    ],

                "http_status":
                    secondary_result.http_status,

                "content_type":
                    secondary_result.content_type,

                "target_found":
                    secondary_classification[
                        "target_found"
                    ],

                "zero_result":
                    secondary_classification[
                        "zero_result"
                    ],

                "notice_context":
                    secondary_classification[
                        "notice_context"
                    ],

                "strong_notice_context":
                    secondary_classification[
                        "strong_notice_context"
                    ],

                "document_evidence":
                    secondary_classification[
                        "document_evidence"
                    ],

                "notice_numbers":
                    secondary_classification[
                        "notice_numbers"
                    ],

                "dates":
                    secondary_classification[
                        "dates"
                    ],

                "positive":
                    secondary_classification[
                        "positive"
                    ],

                "preview":
                    secondary_classification[
                        "preview"
                    ],
            }

            secondary_page_records.append(
                secondary_record
            )

            if secondary_classification[
                "positive"
            ]:

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
    # ROOT PAGE HINT LINKS
    # ========================================================

    root_candidate_links = []

    for link in root_links:

        if not same_or_subdomain(
            link[
                "url"
            ],
            base_url,
        ):

            continue

        if not is_probably_html_url(
            link[
                "url"
            ]
        ):

            continue

        if not link_has_discovery_hint(
            link[
                "label"
            ],
            link[
                "url"
            ],
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

    for link in root_candidate_links[
        :remaining
    ]:

        candidate_url = normalize_url(
            link[
                "url"
            ]
        )

        if candidate_url in visited_urls:

            continue

        visited_urls.add(
            candidate_url
        )

        result = fetch_url(
            candidate_url
        )

        request_count += 1

        if result.error:

            transport_error_count += 1

            continue

        if (
            result.http_status
            == 200
        ):

            http_success_count += 1

        classification = classify_page(
            region=region,
            municipality=municipality,
            agency=agency,
            url=(
                result.final_url
                or candidate_url
            ),
            html=result.text,
        )

        page_parse_count += 1

        if (
            classification[
                "zero_result"
            ]
            and classification[
                "positive"
            ]
        ):

            zero_result_positive_leakage += 1

        record = {

            "url":
                candidate_url,

            "final_url":
                result.final_url,

            "label":
                link[
                    "label"
                ],

            "http_status":
                result.http_status,

            "content_type":
                result.content_type,

            "target_found":
                classification[
                    "target_found"
                ],

            "zero_result":
                classification[
                    "zero_result"
                ],

            "notice_context":
                classification[
                    "notice_context"
                ],

            "strong_notice_context":
                classification[
                    "strong_notice_context"
                ],

            "document_evidence":
                classification[
                    "document_evidence"
                ],

            "notice_numbers":
                classification[
                    "notice_numbers"
                ],

            "dates":
                    classification[
                        "dates"
                    ],

            "positive":
                classification[
                    "positive"
                ],

            "preview":
                classification[
                    "preview"
                ],
        }

        secondary_page_records.append(
            record
        )

        if classification[
            "positive"
        ]:

            local_positive.append(
                classification
            )

            positive_candidates.append(
                classification
            )

        time.sleep(
            REQUEST_SLEEP
        )

    # ========================================================
    # SITE SUMMARY
    # ========================================================

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

    for candidate in local_positive[
        :5
    ]:

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
            "    Preview:",
            candidate.get(
                "preview"
            ),
        )

    site_results.append(
        {
            "region":
                region,

            "municipality":
                municipality,

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

            "root_zero_result":
                root_classification[
                    "zero_result"
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

for candidate in positive_candidates:

    key = (

        candidate.get(
            "region"
        ),

        candidate.get(
            "municipality"
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
# RESOLUTION
# ============================================================

if deduped_positive:

    resolution = (
        "MUNICIPAL_OFFICIAL_POSITIVE_NOTICE_CANDIDATE_DISCOVERED"
    )

    runtime_registration_blocked = (
        True
    )

    next_action = (
        "positive candidate 원문을 개별 검증하고 "
        "고시번호 / 지정일 / 행정구역 / 현재 유효 여부 / "
        "도면 또는 지정 범위를 확정한 뒤 "
        "positive PNU와 spatial source를 역탐색한다."
    )

else:

    resolution = (
        "MUNICIPAL_GAZETTE_DISCOVERY_COMPLETED_NO_POSITIVE"
    )

    runtime_registration_blocked = (
        True
    )

    next_action = (
        "전국 시군구 전체 행정구역 목록으로 탐색 seed를 확대하고, "
        "토지이음 / 국가기록원 / 지자체 도시계획 공고 DB / "
        "첨부 HWP·PDF 원문 검색 단계로 확장한다."
    )


# ============================================================
# OUTPUT
# ============================================================

output_data = {

    "step":
        (
            "STEP 17-21-C-16-8-D "
            "Development Density Management Area "
            "Municipal Gazette Discovery"
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

        "municipal_official_site_direct_probe":
            True,

        "municipal_site_count":
            len(
                MUNICIPAL_SITE_SEEDS
            ),

        "request_timeout":
            REQUEST_TIMEOUT,

        "max_secondary_pages_per_site":
            MAX_SECONDARY_PAGES_PER_SITE,

        "false_positive_guard": {

            "zero_result_pages_blocked":
                True,

            "strong_notice_context_required":
                True,

            "document_evidence_required":
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

        "zero_result_positive_leakage":
            zero_result_positive_leakage,
    },

    "positive_candidates":
        deduped_positive,

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
# CONSOLE RESULT
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
    "Municipal site count:",
    len(
        MUNICIPAL_SITE_SEEDS
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
    zero_result_positive_leakage,
)

print()


if deduped_positive:

    print(
        "POSITIVE MUNICIPAL NOTICE CANDIDATES"
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
            candidate.get(
                "municipality"
            ),
        )

        print(
            "Agency:",
            candidate.get(
                "agency"
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
            "Preview:",
            candidate.get(
                "preview"
            ),
        )

        print()

else:

    print(
        "No municipal official positive notice candidate confirmed."
    )


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

    "municipal seeds exist": (
        len(
            MUNICIPAL_SITE_SEEDS
        )
        >= 20
    ),

    "Seoul municipality included": (
        any(
            item.get(
                "region"
            )
            == "서울특별시"
            for item
            in MUNICIPAL_SITE_SEEDS
        )
    ),

    "Gyeonggi municipality included": (
        any(
            item.get(
                "region"
            )
            == "경기도"
            for item
            in MUNICIPAL_SITE_SEEDS
        )
    ),

    "municipal direct probe used": (
        output_data[
            "method"
        ][
            "municipal_official_site_direct_probe"
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
            MUNICIPAL_SITE_SEEDS
        )
    ),

    "positive candidates unique": (
        len(
            {
                (
                    item.get(
                        "region"
                    ),
                    item.get(
                        "municipality"
                    ),
                    item.get(
                        "url"
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

    "zero-result search pages never positive": (
        zero_result_positive_leakage
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
                "has_structured_document_evidence"
            )
            is True
            for item
            in deduped_positive
        )
    ),

    "positive candidates are not zero-result pages": (
        all(
            item.get(
                "zero_result"
            )
            is False
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

    raise AssertionError(
        "Development density management area "
        "municipal gazette discovery regression failed"
    )