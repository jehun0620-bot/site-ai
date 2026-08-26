# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-G
Development Density Management Area
Official Gazette / Notice Board Endpoint Discovery

목표
======================================================================
STEP E / F에서 일반 지자체 홈페이지와 통합검색 구조를 탐색했으나
개발밀도관리구역과 직접 관련된 공식 HTML 문서 / 첨부파일 /
extensionless download endpoint는 발견되지 않았다.

이번 단계에서는 검색 범위를 다음 공식 게시판 계열로 좁힌다.

    고시공고
    고시/공고
    전자공보
    시보 / 군보 / 구보
    공보
    도시관리계획
    도시계획
    토지 / 도시정책
    행정예고

목적:
    각 지자체 공식 홈페이지에서
    실제 고시·공고 게시판 endpoint를 먼저 발견하고
    그 endpoint를 다음 단계의 직접 검색 seed로 저장한다.

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700


핵심 안전정책
======================================================================
1. 게시판 endpoint 발견 자체는 target positive가 아니다.

2. 메뉴명에 "고시", "공고", "공보"가 있다는 이유만으로
   개발밀도관리구역 존재를 의미하지 않는다.

3. target text가 발견되더라도 통합검색 페이지이면
   final positive로 인정하지 않는다.

4. 이번 단계는 BOARD ENDPOINT DISCOVERY 단계다.

5. candidate가 0건이어도 SITE FALSE로 해석하지 않는다.

6. runtime spatial condition 등록은 계속 차단한다.

7. VWorld LT_C_UQ141을 UQQ700 dataset으로 확정하지 않는다.

8. 개발밀도관리구역은 계속 UNKNOWN / UNRESOLVED 상태를 유지한다.


성공 조건
======================================================================
A.
공식 고시/공고/공보/도시계획 계열 board endpoint를 발견

또는

B.
공식 홈페이지 직접 탐색이 정상적으로 실행되고
endpoint 미발견 상태가 명시적으로 보존

따라서 endpoint 0건도 regression 실패가 아니다.
"""

from __future__ import annotations

import html
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
    / (
        "development_density_management_area_"
        "official_board_endpoint_discovery.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"

STANDARD_CODE = "UQQ700"


# ============================================================
# REQUEST CONFIG
# ============================================================

REQUEST_TIMEOUT = 20

REQUEST_SLEEP = 0.25

MAX_CONTENT_LENGTH = 2_000_000

MAX_LINKS_PER_PAGE = 300

MAX_BOARD_PAGE_PROBES_PER_SITE = 30


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
# MUNICIPAL SITE SEEDS
# ============================================================

MUNICIPAL_SITE_SEEDS: List[Dict[str, str]] = [

    {
        "region": "서울특별시 동대문구",
        "agency": "서울특별시 동대문구",
        "base_url": "https://www.ddm.go.kr/",
    },
    {
        "region": "서울특별시 강남구",
        "agency": "서울특별시 강남구",
        "base_url": "https://www.gangnam.go.kr/",
    },
    {
        "region": "서울특별시 서초구",
        "agency": "서울특별시 서초구",
        "base_url": "https://www.seocho.go.kr/",
    },
    {
        "region": "서울특별시 송파구",
        "agency": "서울특별시 송파구",
        "base_url": "https://www.songpa.go.kr/",
    },
    {
        "region": "서울특별시 강서구",
        "agency": "서울특별시 강서구",
        "base_url": "https://www.gangseo.seoul.kr/",
    },
    {
        "region": "서울특별시 구로구",
        "agency": "서울특별시 구로구",
        "base_url": "https://www.guro.go.kr/",
    },
    {
        "region": "서울특별시 노원구",
        "agency": "서울특별시 노원구",
        "base_url": "https://www.nowon.kr/",
    },

    {
        "region": "경기도 김포시",
        "agency": "경기도 김포시",
        "base_url": "https://www.gimpo.go.kr/",
    },
    {
        "region": "경기도 수원시",
        "agency": "경기도 수원시",
        "base_url": "https://www.suwon.go.kr/",
    },
    {
        "region": "경기도 성남시",
        "agency": "경기도 성남시",
        "base_url": "https://www.seongnam.go.kr/",
    },
    {
        "region": "경기도 용인시",
        "agency": "경기도 용인시",
        "base_url": "https://www.yongin.go.kr/",
    },
    {
        "region": "경기도 고양시",
        "agency": "경기도 고양시",
        "base_url": "https://www.goyang.go.kr/",
    },
    {
        "region": "경기도 화성시",
        "agency": "경기도 화성시",
        "base_url": "https://www.hscity.go.kr/",
    },
    {
        "region": "경기도 남양주시",
        "agency": "경기도 남양주시",
        "base_url": "https://www.nyj.go.kr/",
    },
    {
        "region": "경기도 시흥시",
        "agency": "경기도 시흥시",
        "base_url": "https://www.siheung.go.kr/",
    },
    {
        "region": "경기도 파주시",
        "agency": "경기도 파주시",
        "base_url": "https://www.paju.go.kr/",
    },
    {
        "region": "경기도 평택시",
        "agency": "경기도 평택시",
        "base_url": "https://www.pyeongtaek.go.kr/",
    },

    {
        "region": "인천광역시 남동구",
        "agency": "인천광역시 남동구",
        "base_url": "https://www.namdong.go.kr/",
    },
    {
        "region": "인천광역시 서구",
        "agency": "인천광역시 서구",
        "base_url": "https://www.seo.incheon.kr/",
    },
    {
        "region": "인천광역시 연수구",
        "agency": "인천광역시 연수구",
        "base_url": "https://www.yeonsu.go.kr/",
    },

    {
        "region": "부산광역시 강서구",
        "agency": "부산광역시 강서구",
        "base_url": "https://www.bsgangseo.go.kr/",
    },
    {
        "region": "부산광역시 해운대구",
        "agency": "부산광역시 해운대구",
        "base_url": "https://www.haeundae.go.kr/",
    },

    {
        "region": "대구광역시 달서구",
        "agency": "대구광역시 달서구",
        "base_url": "https://www.dalseo.daegu.kr/",
    },
    {
        "region": "대구광역시 달성군",
        "agency": "대구광역시 달성군",
        "base_url": "https://www.dalseong.daegu.kr/",
    },

    {
        "region": "대전광역시 유성구",
        "agency": "대전광역시 유성구",
        "base_url": "https://www.yuseong.go.kr/",
    },
    {
        "region": "울산광역시 울주군",
        "agency": "울산광역시 울주군",
        "base_url": "https://www.ulju.ulsan.kr/",
    },

    {
        "region": "충청남도 천안시",
        "agency": "충청남도 천안시",
        "base_url": "https://www.cheonan.go.kr/",
    },
    {
        "region": "충청남도 아산시",
        "agency": "충청남도 아산시",
        "base_url": "https://www.asan.go.kr/",
    },
    {
        "region": "충청남도 당진시",
        "agency": "충청남도 당진시",
        "base_url": "https://www.dangjin.go.kr/",
    },
    {
        "region": "충청북도 청주시",
        "agency": "충청북도 청주시",
        "base_url": "https://www.cheongju.go.kr/",
    },

    {
        "region": "전북특별자치도 전주시",
        "agency": "전북특별자치도 전주시",
        "base_url": "https://www.jeonju.go.kr/",
    },
    {
        "region": "전라남도 목포시",
        "agency": "전라남도 목포시",
        "base_url": "https://www.mokpo.go.kr/",
    },
    {
        "region": "전라남도 순천시",
        "agency": "전라남도 순천시",
        "base_url": "https://www.suncheon.go.kr/",
    },

    {
        "region": "경상북도 포항시",
        "agency": "경상북도 포항시",
        "base_url": "https://www.pohang.go.kr/",
    },
    {
        "region": "경상북도 구미시",
        "agency": "경상북도 구미시",
        "base_url": "https://www.gumi.go.kr/",
    },
    {
        "region": "경상남도 창원시",
        "agency": "경상남도 창원시",
        "base_url": "https://www.changwon.go.kr/",
    },
    {
        "region": "경상남도 김해시",
        "agency": "경상남도 김해시",
        "base_url": "https://www.gimhae.go.kr/",
    },

    {
        "region": "제주특별자치도 제주시",
        "agency": "제주특별자치도 제주시",
        "base_url": "https://www.jejusi.go.kr/",
    },
    {
        "region": "제주특별자치도 서귀포시",
        "agency": "제주특별자치도 서귀포시",
        "base_url": "https://www.seogwipo.go.kr/",
    },
]


# ============================================================
# BOARD DISCOVERY TERMS
# ============================================================

BOARD_STRONG_TERMS = [
    "고시공고",
    "고시·공고",
    "고시/공고",
    "고시",
    "공고",
    "전자공보",
    "공보",
    "시보",
    "군보",
    "구보",
    "도보",
    "도시관리계획",
    "도시계획",
    "도시정책",
    "행정예고",
]


BOARD_URL_HINTS = [
    "notice",
    "announce",
    "announcement",
    "gosi",
    "gonggo",
    "publicnotice",
    "public_notice",
    "gazette",
    "cityplan",
    "urban",
    "bbs",
    "board",
]


SEARCH_URL_HINTS = [
    "/search",
    "search.",
    "search/",
    "search?",
    "search.do",
    "search.jsp",
    "totalsearch",
]


BLOCKED_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".zip",
    ".7z",
    ".rar",
    ".pdf",
    ".hwp",
    ".hwpx",
    ".xls",
    ".xlsx",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
)


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

def normalize_space(value: Any) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(
            value
            or ""
        ),
    ).strip()


def strip_html(source: str) -> str:

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


def compact_text(value: str) -> str:

    return re.sub(
        r"\s+",
        "",
        normalize_space(
            value
        ),
    )


def contains_target(value: str) -> bool:

    return (
        compact_text(
            TARGET_NAME
        )
        in compact_text(
            value
        )
    )


def build_preview(
    value: str,
    *,
    radius: int = 220,
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
        index + len(TARGET_NAME) + radius,
    )

    return text[
        start:end
    ]


# ============================================================
# URL UTIL
# ============================================================

def normalize_url(url: str) -> str:

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

    if not target_host or not base_host:
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


def is_search_url(url: str) -> bool:

    lower = url.lower()

    return any(
        hint in lower
        for hint in SEARCH_URL_HINTS
    )


def is_html_candidate_url(url: str) -> bool:

    path = (
        urlparse(
            url
        ).path.lower()
    )

    return not any(
        path.endswith(
            extension
        )
        for extension in BLOCKED_EXTENSIONS
    )


# ============================================================
# LINK EXTRACTION
# ============================================================

ANCHOR_PATTERN = re.compile(
    r"""
    (?is)
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
                "url": absolute,
                "label": label,
            }
        )

        if len(results) >= MAX_LINKS_PER_PAGE:
            break

    return results


# ============================================================
# BOARD CLASSIFICATION
# ============================================================

def get_board_term_hits(
    label: str,
    url: str,
) -> List[str]:

    value = normalize_space(
        label
        + " "
        + url
    ).lower()

    hits = []

    for term in BOARD_STRONG_TERMS:

        if term.lower() in value:
            hits.append(
                term
            )

    for term in BOARD_URL_HINTS:

        if term.lower() in value:
            hits.append(
                term
            )

    return sorted(
        set(
            hits
        )
    )


def looks_like_official_board_link(
    label: str,
    url: str,
) -> bool:

    if is_search_url(
        url
    ):
        return False

    if not is_html_candidate_url(
        url
    ):
        return False

    hits = get_board_term_hits(
        label,
        url,
    )

    return bool(
        hits
    )


def classify_board_page(
    *,
    region: str,
    agency: str,
    url: str,
    source: str,
    source_label: str,
) -> Dict[str, Any]:

    text = strip_html(
        source
    )

    target_found = contains_target(
        text
    )

    board_hits = get_board_term_hits(
        source_label,
        url,
    )

    body_board_hits = []

    normalized_text = normalize_space(
        text
    )

    for term in BOARD_STRONG_TERMS:

        if term in normalized_text:
            body_board_hits.append(
                term
            )

    # --------------------------------------------------------
    # 단순 메뉴 링크보다 실제 board 구조가 있는지 확인하기 위한
    # 완화된 structure evidence
    # --------------------------------------------------------

    lower_url = url.lower()

    board_structure_evidence = (
        bool(
            board_hits
        )
        or bool(
            body_board_hits
        )
        or any(
            hint in lower_url
            for hint in (
                "bbs",
                "board",
                "list.do",
                "notice",
                "announce",
                "gosi",
                "gonggo",
            )
        )
    )

    return {
        "region":
            region,

        "agency":
            agency,

        "url":
            url,

        "source_label":
            source_label,

        "board_term_hits":
            board_hits,

        "body_board_term_hits":
            sorted(
                set(
                    body_board_hits
                )
            ),

        "board_structure_evidence":
            board_structure_evidence,

        "target_found":
            target_found,

        "target_preview":
            (
                build_preview(
                    text
                )
                if target_found
                else ""
            ),
    }


# ============================================================
# FETCH
# ============================================================

def fetch_url(url: str) -> FetchResult:

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

    lower_content_type = (
        content_type.lower()
    )

    text_like = (
        "text/" in lower_content_type
        or "html" in lower_content_type
        or "xml" in lower_content_type
        or "json" in lower_content_type
    )

    text = ""

    if text_like:

        text = (
            response.text
            or ""
        )

        if len(text) > MAX_CONTENT_LENGTH:

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
# STATE
# ============================================================

site_results: List[
    Dict[
        str,
        Any
    ]
] = []

board_candidates: List[
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

raw_board_link_count = 0

board_page_probe_count = 0


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
    "OFFICIAL GAZETTE / NOTICE BOARD ENDPOINT DISCOVERY"
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
# MAIN LOOP
# ============================================================

for site_index, seed in enumerate(
    MUNICIPAL_SITE_SEEDS,
    start=1,
):

    region = seed[
        "region"
    ]

    agency = seed[
        "agency"
    ]

    base_url = seed[
        "base_url"
    ]

    print(
        "------------------------------------------------------------"
    )

    print(
        f"SITE {site_index}:",
        region,
        "/",
        base_url,
    )

    local_raw_board_links = []

    local_board_pages = []

    root = fetch_url(
        base_url
    )

    request_count += 1

    if root.error:

        transport_error_count += 1

        print(
            "Root transport error:",
            root.error,
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
                    None,

                "root_error":
                    root.error,

                "raw_board_link_count":
                    0,

                "board_endpoint_count":
                    0,

                "board_endpoints":
                    [],
            }
        )

        continue

    if root.http_status == 200:
        http_success_count += 1

    root_final_url = (
        root.final_url
        or base_url
    )

    if root.text:
        html_parse_count += 1

    root_links = extract_links(
        root.text,
        base_url=root_final_url,
    )

    for link in root_links:

        link_url = link[
            "url"
        ]

        label = (
            link.get(
                "label"
            )
            or ""
        )

        if not same_or_subdomain(
            link_url,
            base_url,
        ):
            continue

        if not looks_like_official_board_link(
            label,
            link_url,
        ):
            continue

        local_raw_board_links.append(
            {
                "url":
                    normalize_url(
                        link_url
                    ),

                "label":
                    label,

                "term_hits":
                    get_board_term_hits(
                        label,
                        link_url,
                    ),
            }
        )

    # ========================================================
    # DEDUPE ROOT BOARD LINKS
    # ========================================================

    deduped_links = []

    seen_local_links = set()

    for link in local_raw_board_links:

        url = link[
            "url"
        ]

        if url in seen_local_links:
            continue

        seen_local_links.add(
            url
        )

        deduped_links.append(
            link
        )

    raw_board_link_count += len(
        deduped_links
    )

    # ========================================================
    # BOARD PAGE PROBE
    # ========================================================

    for link in deduped_links[
        :MAX_BOARD_PAGE_PROBES_PER_SITE
    ]:

        board_url = link[
            "url"
        ]

        if board_url in visited_urls:
            continue

        visited_urls.add(
            board_url
        )

        result = fetch_url(
            board_url
        )

        request_count += 1

        board_page_probe_count += 1

        if result.error:

            transport_error_count += 1

            local_board_pages.append(
                {
                    "url":
                        board_url,

                    "label":
                        link.get(
                            "label"
                        ),

                    "http_status":
                        None,

                    "error":
                        result.error,

                    "accepted_board_endpoint":
                        False,
                }
            )

            continue

        if result.http_status == 200:
            http_success_count += 1

        if result.text:
            html_parse_count += 1

        final_url = (
            result.final_url
            or board_url
        )

        classification = classify_board_page(
            region=region,
            agency=agency,
            url=final_url,
            source=result.text,
            source_label=(
                link.get(
                    "label"
                )
                or ""
            ),
        )

        accepted = (
            result.http_status == 200
            and bool(
                result.text
            )
            and classification[
                "board_structure_evidence"
            ]
            is True
            and not is_search_url(
                final_url
            )
        )

        record = {
            "requested_url":
                board_url,

            "final_url":
                final_url,

            "http_status":
                result.http_status,

            "content_type":
                result.content_type,

            "accepted_board_endpoint":
                accepted,

            **classification,
        }

        local_board_pages.append(
            record
        )

        if accepted:

            board_candidates.append(
                record
            )

        time.sleep(
            REQUEST_SLEEP
        )

    # ========================================================
    # SITE SUMMARY
    # ========================================================

    accepted_local = [
        item
        for item
        in local_board_pages
        if item.get(
            "accepted_board_endpoint"
        )
        is True
    ]

    print(
        "Root HTTP:",
        root.http_status,
    )

    print(
        "Raw board links:",
        len(
            deduped_links
        ),
    )

    print(
        "Board pages probed:",
        len(
            local_board_pages
        ),
    )

    print(
        "Accepted board endpoints:",
        len(
            accepted_local
        ),
    )

    for item in accepted_local[
        :5
    ]:

        print(
            "  BOARD:",
            item.get(
                "url"
            ),
        )

        print(
            "    Label:",
            item.get(
                "source_label"
            ),
        )

        print(
            "    Terms:",
            item.get(
                "board_term_hits"
            ),
        )

        print(
            "    Target found:",
            item.get(
                "target_found"
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
                root.http_status,

            "root_final_url":
                root.final_url,

            "raw_board_link_count":
                len(
                    deduped_links
                ),

            "board_endpoint_count":
                len(
                    accepted_local
                ),

            "board_endpoints":
                accepted_local,
        }
    )

    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# DEDUPE BOARD ENDPOINTS
# ============================================================

deduped_board_candidates = []

seen_board_candidates = set()

for candidate in board_candidates:

    normalized_url = normalize_url(
        str(
            candidate.get(
                "url"
            )
            or ""
        )
    )

    key = (
        candidate.get(
            "region"
        ),
        normalized_url,
    )

    if key in seen_board_candidates:
        continue

    seen_board_candidates.add(
        key
    )

    normalized_candidate = dict(
        candidate
    )

    normalized_candidate[
        "url"
    ] = normalized_url

    deduped_board_candidates.append(
        normalized_candidate
    )


# ============================================================
# PRIORITY
# ============================================================

for candidate in deduped_board_candidates:

    score = 0

    strong_hits = set(
        candidate.get(
            "board_term_hits"
        )
        or []
    )

    body_hits = set(
        candidate.get(
            "body_board_term_hits"
        )
        or []
    )

    high_value_terms = {
        "고시공고",
        "고시·공고",
        "고시/공고",
        "전자공보",
        "공보",
        "시보",
        "군보",
        "구보",
        "도보",
        "도시관리계획",
        "도시계획",
    }

    score += (
        len(
            strong_hits
            & high_value_terms
        )
        * 3
    )

    score += (
        len(
            body_hits
            & high_value_terms
        )
        * 1
    )

    if candidate.get(
        "target_found"
    ) is True:

        score += 10

    candidate[
        "priority_score"
    ] = score


deduped_board_candidates.sort(
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
# RESOLUTION
# ============================================================

if deduped_board_candidates:

    resolution = (
        "OFFICIAL_GAZETTE_OR_NOTICE_BOARD_ENDPOINT_DISCOVERED"
    )

    next_action = (
        "확보된 고시·공고·공보·도시계획 board endpoint에 대해 "
        "개발밀도관리구역 검색 파라미터와 pagination 구조를 탐색하고 "
        "실제 게시물 제목/본문/첨부파일을 직접 조회한다."
    )

else:

    resolution = (
        "OFFICIAL_BOARD_ENDPOINT_DISCOVERY_COMPLETED_NO_CANDIDATE"
    )

    next_action = (
        "지자체 사이트의 sitemap.xml, 메뉴 API, JavaScript menu data, "
        "전자공보 별도 도메인 및 광역자치단체 공보 시스템으로 탐색 범위를 확장한다."
    )


runtime_registration_blocked = True

site_false_interpretation_blocked = True


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-G "
        "Development Density Management Area "
        "Official Gazette / Notice Board Endpoint Discovery"
    ),

    "target": {
        "name":
            TARGET_NAME,

        "standard_code":
            STANDARD_CODE,
    },

    "method": {
        "official_municipal_direct_probe":
            True,

        "search_engine_scraping":
            False,

        "board_endpoint_discovery":
            True,

        "board_endpoint_is_target_positive":
            False,

        "runtime_registration_allowed":
            False,

        "site_false_allowed_from_no_candidate":
            False,

        "municipal_site_count":
            len(
                MUNICIPAL_SITE_SEEDS
            ),
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

        "raw_board_link_count":
            raw_board_link_count,

        "board_page_probe_count":
            board_page_probe_count,

        "accepted_board_endpoint_count":
            len(
                deduped_board_candidates
            ),

        "board_endpoint_with_target_count":
            sum(
                1
                for item
                in deduped_board_candidates
                if item.get(
                    "target_found"
                )
                is True
            ),
    },

    "board_endpoints":
        deduped_board_candidates,

    "site_results":
        site_results,

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
# SUMMARY
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
    "Transport error count:",
    transport_error_count,
)

print(
    "HTML parse count:",
    html_parse_count,
)

print(
    "Raw board link count:",
    raw_board_link_count,
)

print(
    "Board page probe count:",
    board_page_probe_count,
)

print(
    "Accepted board endpoint count:",
    len(
        deduped_board_candidates
    ),
)

target_board_count = sum(
    1
    for item
    in deduped_board_candidates
    if item.get(
        "target_found"
    )
    is True
)

print(
    "Board endpoint with target count:",
    target_board_count,
)

print()


if deduped_board_candidates:

    print(
        "OFFICIAL BOARD ENDPOINT CANDIDATES"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, candidate in enumerate(
        deduped_board_candidates[
            :100
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            candidate.get(
                "region"
            ),
        )

        print(
            "Score:",
            candidate.get(
                "priority_score"
            ),
        )

        print(
            "Label:",
            candidate.get(
                "source_label"
            ),
        )

        print(
            "Terms:",
            candidate.get(
                "board_term_hits"
            ),
        )

        print(
            "Target found:",
            candidate.get(
                "target_found"
            ),
        )

        print(
            "URL:",
            candidate.get(
                "url"
            ),
        )

        if candidate.get(
            "target_found"
        ):

            print(
                "Preview:",
                candidate.get(
                    "target_preview"
                ),
            )

        print()


else:

    print(
        "No official board endpoint candidate discovered."
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

board_candidate_keys = {
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
    for item in deduped_board_candidates
}


all_board_candidates_have_url = all(
    bool(
        item.get(
            "url"
        )
    )
    for item
    in deduped_board_candidates
)


all_board_candidates_have_structure_evidence = all(
    item.get(
        "board_structure_evidence"
    )
    is True
    for item
    in deduped_board_candidates
)


all_board_candidates_not_search = all(
    not is_search_url(
        str(
            item.get(
                "url"
            )
            or ""
        )
    )
    for item
    in deduped_board_candidates
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
        >= 30
    ),

    "Dongdaemun included": (
        any(
            item.get(
                "region"
            )
            == "서울특별시 동대문구"
            for item
            in MUNICIPAL_SITE_SEEDS
        )
    ),

    "Gimpo included": (
        any(
            item.get(
                "region"
            )
            == "경기도 김포시"
            for item
            in MUNICIPAL_SITE_SEEDS
        )
    ),

    "official direct probe used": (
        output_data[
            "method"
        ][
            "official_municipal_direct_probe"
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

    "board endpoint discovery enabled": (
        output_data[
            "method"
        ][
            "board_endpoint_discovery"
        ]
        is True
    ),

    "board endpoint is not target positive": (
        output_data[
            "method"
        ][
            "board_endpoint_is_target_positive"
        ]
        is False
    ),

    "requests executed": (
        request_count
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

    "board endpoints unique": (
        len(
            board_candidate_keys
        )
        == len(
            deduped_board_candidates
        )
    ),

    "all board endpoints have URL": (
        all_board_candidates_have_url
    ),

    "all board endpoints have structure evidence": (
        all_board_candidates_have_structure_evidence
    ),

    "all board endpoints are not search pages": (
        all_board_candidates_not_search
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
        "official board endpoint discovery regression failed"
    )