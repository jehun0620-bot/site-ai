# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-E
Development Density Management Area
Municipal Official Notice / Attachment Discovery

목표
======================================================================
개발밀도관리구역의 실제 지정 / 변경 / 해제 고시 원문을 찾기 위해
전국 주요 시군구 공식 사이트에서 다음 구조를 탐색한다.

공식 시군구 사이트
    ↓
통합검색 / 게시판 / 고시공고 페이지
    ↓
실제 게시물 URL
    ↓
첨부파일 URL
    ↓
HWP / HWPX / PDF
    ↓
다음 원문 검증 단계의 seed

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 안전정책
======================================================================
1. 통합검색 결과 페이지는 최종 positive document로 인정하지 않는다.
2. 검색 결과 페이지에 target text가 있어도 실제 게시물 원문이 아니면
   VERIFIED_POSITIVE로 승격하지 않는다.
3. PDF / HWP / HWPX 첨부파일 URL은 원문 검증 후보로만 수집한다.
4. 첨부파일 확장자만으로 candidate에 승격하지 않는다.
5. attachment label / URL / parent page에서 target evidence가 있어야 한다.
6. 첨부파일이 발견되지 않았다고 SITE FALSE로 해석하지 않는다.
7. runtime spatial condition 등록은 계속 차단한다.
8. VWorld LT_C_UQ141을 UQQ700 dataset으로 확정하지 않는다.
9. positive 원문이 실제 검증되기 전까지
   개발밀도관리구역 condition은 UNKNOWN / UNRESOLVED 상태를 유지한다.

이번 단계의 성공
======================================================================
다음 중 하나면 성공이다.

A.
실제 게시물 또는 relevance가 확인된
HWP / HWPX / PDF 첨부파일 후보를 발견

B.
공식 시군구 탐색 구조가 정상 실행되며 후보가 0건인 상태를
명시적으로 보존

즉 discovery regression이므로 후보 0건도 테스트 실패가 아니다.
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
        "municipal_attachment_discovery.json"
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

REQUEST_SLEEP = 0.25

MAX_CONTENT_LENGTH = (
    2_000_000
)

MAX_LINKS_PER_PAGE = (
    180
)

MAX_DOCUMENT_PAGES_PER_SITE = (
    20
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
# MUNICIPAL SITE SEEDS
# ============================================================

MUNICIPAL_SITE_SEEDS: List[Dict[str, str]] = [

    # --------------------------------------------------------
    # 서울
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 경기
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 인천
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 부산
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 대구
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 대전 / 울산
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 충청
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 전라
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 경상
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 제주
    # --------------------------------------------------------

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
# DISCOVERY TERMS
# ============================================================

STRONG_NOTICE_TERMS = [
    "고시",
    "고시문",
    "고시번호",
    "공고",
    "지정",
    "변경",
    "해제",
    "도시관리계획",
    "도시계획",
    "결정",
    "지형도면",
]


BOARD_HINT_TERMS = [
    "고시",
    "공고",
    "공보",
    "게시판",
    "도시계획",
    "도시관리",
    "도시정책",
    "토지",
    "개발",
    "notice",
    "announce",
    "board",
    "bbs",
    "cityplan",
]


SEARCH_PAGE_HINT_TERMS = [
    "/search",
    "search.",
    "search/",
    "search?",
    "search.do",
    "search.jsp",
    "totalsearch",
]


ATTACHMENT_EXTENSIONS = (
    ".pdf",
    ".hwp",
    ".hwpx",
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


def contains_strong_notice_context(
    value: str,
) -> bool:

    text = normalize_space(
        value
    )

    return any(
        term in text
        for term
        in STRONG_NOTICE_TERMS
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

    if not (
        target_host
        and base_host
    ):

        return False

    return (
        target_host
        == base_host
        or target_host.endswith(
            "." + base_host
        )
        or base_host.endswith(
            "." + target_host
        )
    )


def is_search_page_url(
    url: str,
) -> bool:

    lower = url.lower()

    return any(
        hint.lower() in lower
        for hint
        in SEARCH_PAGE_HINT_TERMS
    )


def is_attachment_url(
    url: str,
) -> bool:

    lower_path = (
        urlparse(
            url
        ).path.lower()
    )

    return any(
        lower_path.endswith(
            extension
        )
        for extension
        in ATTACHMENT_EXTENSIONS
    )


def get_attachment_extension(
    url: str,
) -> Optional[str]:

    lower_path = (
        urlparse(
            url
        ).path.lower()
    )

    for extension in ATTACHMENT_EXTENSIONS:

        if lower_path.endswith(
            extension
        ):

            return extension[
                1:
            ]

    return None


def is_probably_html_url(
    url: str,
) -> bool:

    lower_path = (
        urlparse(
            url
        ).path.lower()
    )

    blocked_extensions = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".webp",
        ".zip",
        ".7z",
        ".rar",
        ".xls",
        ".xlsx",
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
    )

    if is_attachment_url(
        url
    ):

        return False

    return not any(
        lower_path.endswith(
            extension
        )
        for extension
        in blocked_extensions
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

        if (
            len(results)
            >= MAX_LINKS_PER_PAGE
        ):

            break

    return results


def link_has_board_hint(
    label: str,
    url: str,
) -> bool:

    value = normalize_space(
        label
        + " "
        + url
    ).lower()

    if contains_target(
        value
    ):

        return True

    return any(
        term.lower() in value
        for term
        in BOARD_HINT_TERMS
    )


# ============================================================
# ATTACHMENT RELEVANCE
# ============================================================

def attachment_has_target_in_url(
    url: str,
) -> bool:

    decoded = requests.utils.unquote(
        url
    )

    return contains_target(
        decoded
    )


def build_attachment_candidate(
    *,
    region: str,
    agency: str,
    parent_page_url: str,
    parent_page_text: str,
    url: str,
    label: str,
) -> Dict[str, Any]:

    normalized_url = normalize_url(
        url
    )

    target_in_label = contains_target(
        label
    )

    target_in_url = (
        attachment_has_target_in_url(
            normalized_url
        )
    )

    target_in_parent_page = (
        contains_target(
            parent_page_text
        )
    )

    notice_context_in_label = (
        contains_strong_notice_context(
            label
        )
    )

    notice_context_in_parent_page = (
        contains_strong_notice_context(
            parent_page_text
        )
    )

    relevant_attachment_candidate = (
        target_in_label
        or target_in_url
        or (
            target_in_parent_page
            and notice_context_in_parent_page
        )
    )

    return {
        "region":
            region,

        "agency":
            agency,

        "parent_page_url":
            parent_page_url,

        "url":
            normalized_url,

        "label":
            label,

        "extension":
            get_attachment_extension(
                normalized_url
            ),

        "target_in_label":
            target_in_label,

        "target_in_url":
            target_in_url,

        "target_in_parent_page":
            target_in_parent_page,

        "notice_context_in_label":
            notice_context_in_label,

        "notice_context_in_parent_page":
            notice_context_in_parent_page,

        "relevant_attachment_candidate":
            relevant_attachment_candidate,
    }


def collect_attachment_links(
    *,
    source: str,
    page_url: str,
    region: str,
    agency: str,
) -> List[Dict[str, Any]]:

    attachments = []

    seen = set()

    parent_page_text = strip_html(
        source
    )

    for link in extract_links(
        source,
        base_url=page_url,
    ):

        url = link[
            "url"
        ]

        if not is_attachment_url(
            url
        ):

            continue

        normalized = normalize_url(
            url
        )

        if normalized in seen:

            continue

        seen.add(
            normalized
        )

        candidate = build_attachment_candidate(
            region=region,
            agency=agency,
            parent_page_url=page_url,
            parent_page_text=parent_page_text,
            url=normalized,
            label=(
                link.get(
                    "label"
                )
                or ""
            ),
        )

        attachments.append(
            candidate
        )

    return attachments


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

    text = ""

    content_type_lower = (
        content_type.lower()
    )

    text_like = (
        "text/" in content_type_lower
        or "html" in content_type_lower
        or "xml" in content_type_lower
        or "json" in content_type_lower
    )

    if text_like:

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
# SEARCH URL BUILDING
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
            f"search/search.jsp?query={encoded}",
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
    ]

    results = []

    seen = set()

    for candidate in candidates:

        normalized = normalize_url(
            candidate
        )

        if normalized in seen:

            continue

        seen.add(
            normalized
        )

        results.append(
            normalized
        )

    return results


# ============================================================
# SEARCH RESULT COUNT
# ============================================================

ZERO_RESULT_PATTERNS = [
    re.compile(
        r"검색결과\s*0\s*건"
    ),
    re.compile(
        r"검색\s*결과\s*0\s*건"
    ),
    re.compile(
        r"총\s*0\s*건"
    ),
    re.compile(
        r"""전체\s*[“"']?0[”"']?\s*개의?\s*결과"""
    ),
    re.compile(
        r"결과를\s*찾을\s*수\s*없"
    ),
]


def is_zero_result_page(
    text: str,
) -> bool:

    value = normalize_space(
        text
    )

    return any(
        pattern.search(
            value
        )
        is not None
        for pattern
        in ZERO_RESULT_PATTERNS
    )


# ============================================================
# NOTICE / DATE EXTRACTION
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
# PAGE CLASSIFICATION
# ============================================================

def classify_html_page(
    *,
    region: str,
    agency: str,
    url: str,
    source: str,
    request_url: Optional[str] = None,
) -> Dict[str, Any]:

    text = strip_html(
        source
    )

    target_found = contains_target(
        text
    )

    strong_context = (
        contains_strong_notice_context(
            text
        )
    )

    zero_result = (
        is_zero_result_page(
            text
        )
    )

    search_page = (
        is_search_page_url(
            url
        )
        or (
            bool(
                request_url
            )
            and is_search_page_url(
                str(
                    request_url
                )
            )
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

    # --------------------------------------------------------
    # 검색페이지는 절대 document_positive로 승격하지 않음.
    # --------------------------------------------------------

    document_positive = (
        target_found
        and strong_context
        and not zero_result
        and not search_page
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

        "strong_notice_context":
            strong_context,

        "zero_result_page":
            zero_result,

        "search_page":
            search_page,

        "notice_numbers":
            notice_numbers,

        "dates":
            dates,

        "document_positive":
            document_positive,

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
    Dict[
        str,
        Any
    ]
] = []

document_candidates: List[
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

visited_urls: Set[str] = set()

request_count = 0

http_success_count = 0

transport_error_count = 0

html_parse_count = 0

search_page_positive_leakage = 0

irrelevant_attachment_filtered_count = 0


# ============================================================
# CONSOLE HEADER
# ============================================================

print(
    "============================================================"
)

print(
    "DEVELOPMENT DENSITY MANAGEMENT AREA"
)

print(
    "MUNICIPAL OFFICIAL NOTICE / ATTACHMENT DISCOVERY"
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

    local_search_records = []

    local_page_records = []

    local_document_candidates = []

    local_attachment_candidates = []

    # ========================================================
    # ROOT
    # ========================================================

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

                "search_attempts":
                    [],

                "visited_document_pages":
                    [],

                "html_document_candidate_count":
                    0,

                "attachment_candidate_count":
                    0,
            }
        )

        continue

    if root.http_status == 200:

        http_success_count += 1

    root_final_url = (
        root.final_url
        or base_url
    )

    root_links = extract_links(
        root.text,
        base_url=root_final_url,
    )

    root_text = strip_html(
        root.text
    )

    if root.text:

        html_parse_count += 1

    # ========================================================
    # GENERIC SEARCH ENDPOINTS
    # ========================================================

    search_urls = (
        build_site_search_candidates(
            base_url
        )
    )

    candidate_page_links: List[
        Dict[
            str,
            str
        ]
    ] = []

    for search_url in search_urls:

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

        result = fetch_url(
            normalized_search_url
        )

        request_count += 1

        if result.error:

            transport_error_count += 1

            local_search_records.append(
                {
                    "url":
                        normalized_search_url,

                    "http_status":
                        None,

                    "error":
                        result.error,

                    "target_found":
                        False,

                    "zero_result_page":
                        False,

                    "search_page":
                        True,

                    "document_positive":
                        False,
                }
            )

            continue

        if result.http_status == 200:

            http_success_count += 1

        final_url = (
            result.final_url
            or normalized_search_url
        )

        classification = classify_html_page(
            region=region,
            agency=agency,
            url=final_url,
            request_url=normalized_search_url,
            source=result.text,
        )

        if result.text:

            html_parse_count += 1

        if (
            classification[
                "search_page"
            ]
            and classification[
                "document_positive"
            ]
        ):

            search_page_positive_leakage += 1

        local_search_records.append(
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

                "strong_notice_context":
                    classification[
                        "strong_notice_context"
                    ],

                "zero_result_page":
                    classification[
                        "zero_result_page"
                    ],

                "search_page":
                    classification[
                        "search_page"
                    ],

                "document_positive":
                    classification[
                        "document_positive"
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
            }
        )

        # ----------------------------------------------------
        # 검색 페이지 첨부파일 직접 노출
        #
        # 이것은 verified positive가 아니다.
        # relevance가 있는 파일만 다음 original verification
        # 단계의 seed로 저장한다.
        # ----------------------------------------------------

        attachments = (
            collect_attachment_links(
                source=result.text,
                page_url=final_url,
                region=region,
                agency=agency,
            )
        )

        for attachment in attachments:

            if not attachment.get(
                "relevant_attachment_candidate"
            ):

                irrelevant_attachment_filtered_count += 1

                continue

            local_attachment_candidates.append(
                attachment
            )

            attachment_candidates.append(
                attachment
            )

        # ----------------------------------------------------
        # 실제 게시물 후보 링크 수집
        # ----------------------------------------------------

        links = extract_links(
            result.text,
            base_url=final_url,
        )

        for link in links:

            link_url = link[
                "url"
            ]

            if not same_or_subdomain(
                link_url,
                base_url,
            ):

                continue

            if is_attachment_url(
                link_url
            ):

                continue

            if not is_probably_html_url(
                link_url
            ):

                continue

            # 검색 페이지 재귀 방문 방지
            if is_search_page_url(
                link_url
            ):

                continue

            label = (
                link.get(
                    "label"
                )
                or ""
            )

            if not (
                contains_target(
                    label
                )
                or link_has_board_hint(
                    label,
                    link_url,
                )
            ):

                continue

            candidate_page_links.append(
                link
            )

        time.sleep(
            REQUEST_SLEEP
        )

    # ========================================================
    # ROOT BOARD / ATTACHMENT LINKS
    # ========================================================

    for link in root_links:

        link_url = link[
            "url"
        ]

        if not same_or_subdomain(
            link_url,
            base_url,
        ):

            continue

        if is_attachment_url(
            link_url
        ):

            root_attachment = (
                build_attachment_candidate(
                    region=region,
                    agency=agency,
                    parent_page_url=root_final_url,
                    parent_page_text=root_text,
                    url=link_url,
                    label=(
                        link.get(
                            "label"
                        )
                        or ""
                    ),
                )
            )

            if not root_attachment.get(
                "relevant_attachment_candidate"
            ):

                irrelevant_attachment_filtered_count += 1

                continue

            local_attachment_candidates.append(
                root_attachment
            )

            attachment_candidates.append(
                root_attachment
            )

            continue

        if not is_probably_html_url(
            link_url
        ):

            continue

        if is_search_page_url(
            link_url
        ):

            continue

        if not link_has_board_hint(
            link.get(
                "label",
                ""
            ),
            link_url,
        ):

            continue

        candidate_page_links.append(
            link
        )

    # ========================================================
    # DEDUPE PAGE CANDIDATES
    # ========================================================

    deduped_page_links = []

    local_seen_pages = set()

    for link in candidate_page_links:

        normalized_page_url = normalize_url(
            link[
                "url"
            ]
        )

        if (
            normalized_page_url
            in local_seen_pages
        ):

            continue

        local_seen_pages.add(
            normalized_page_url
        )

        deduped_page_links.append(
            {
                "url":
                    normalized_page_url,

                "label":
                    link.get(
                        "label",
                        ""
                    ),
            }
        )

    # ========================================================
    # FETCH ACTUAL DOCUMENT / BOARD PAGES
    # ========================================================

    for link in deduped_page_links[
        :MAX_DOCUMENT_PAGES_PER_SITE
    ]:

        page_url = link[
            "url"
        ]

        if page_url in visited_urls:

            continue

        visited_urls.add(
            page_url
        )

        result = fetch_url(
            page_url
        )

        request_count += 1

        if result.error:

            transport_error_count += 1

            local_page_records.append(
                {
                    "url":
                        page_url,

                    "label":
                        link.get(
                            "label"
                        ),

                    "http_status":
                        None,

                    "error":
                        result.error,
                }
            )

            continue

        if result.http_status == 200:

            http_success_count += 1

        final_url = (
            result.final_url
            or page_url
        )

        classification = classify_html_page(
            region=region,
            agency=agency,
            url=final_url,
            request_url=page_url,
            source=result.text,
        )

        if result.text:

            html_parse_count += 1

        all_page_attachments = (
            collect_attachment_links(
                source=result.text,
                page_url=final_url,
                region=region,
                agency=agency,
            )
        )

        relevant_page_attachments = []

        for attachment in all_page_attachments:

            if not attachment.get(
                "relevant_attachment_candidate"
            ):

                irrelevant_attachment_filtered_count += 1

                continue

            relevant_page_attachments.append(
                attachment
            )

        page_record = {
            "url":
                page_url,

            "final_url":
                result.final_url,

            "label":
                link.get(
                    "label"
                ),

            "http_status":
                result.http_status,

            "content_type":
                result.content_type,

            "target_found":
                classification[
                    "target_found"
                ],

            "strong_notice_context":
                classification[
                    "strong_notice_context"
                ],

            "zero_result_page":
                classification[
                    "zero_result_page"
                ],

            "search_page":
                classification[
                    "search_page"
                ],

            "document_positive":
                classification[
                    "document_positive"
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

            "raw_attachment_count":
                len(
                    all_page_attachments
                ),

            "attachment_count":
                len(
                    relevant_page_attachments
                ),

            "attachments":
                relevant_page_attachments,
        }

        local_page_records.append(
            page_record
        )

        # ----------------------------------------------------
        # actual HTML document candidate
        # ----------------------------------------------------

        if classification[
            "document_positive"
        ]:

            candidate = {
                "candidate_type":
                    "HTML_DOCUMENT",

                **classification,

                "attachment_count":
                    len(
                        relevant_page_attachments
                    ),

                "attachments":
                    relevant_page_attachments,
            }

            local_document_candidates.append(
                candidate
            )

            document_candidates.append(
                candidate
            )

        # ----------------------------------------------------
        # relevant attachment candidate
        # ----------------------------------------------------

        for attachment in relevant_page_attachments:

            local_attachment_candidates.append(
                attachment
            )

            attachment_candidates.append(
                attachment
            )

        time.sleep(
            REQUEST_SLEEP
        )

    # ========================================================
    # SITE SUMMARY
    # ========================================================

    print(
        "Root HTTP:",
        root.http_status,
    )

    print(
        "Search attempts:",
        len(
            local_search_records
        ),
    )

    print(
        "Actual pages visited:",
        len(
            local_page_records
        ),
    )

    print(
        "HTML document candidates:",
        len(
            local_document_candidates
        ),
    )

    print(
        "Relevant attachment candidates:",
        len(
            local_attachment_candidates
        ),
    )

    for candidate in local_document_candidates[
        :3
    ]:

        print(
            "  DOCUMENT:",
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

    for attachment in local_attachment_candidates[
        :5
    ]:

        print(
            "  ATTACHMENT:",
            attachment.get(
                "extension"
            ),
            "/",
            attachment.get(
                "url"
            ),
        )

        print(
            "    Target evidence:",
            {
                "label":
                    attachment.get(
                        "target_in_label"
                    ),

                "url":
                    attachment.get(
                        "target_in_url"
                    ),

                "parent":
                    attachment.get(
                        "target_in_parent_page"
                    ),

                "parent_notice":
                    attachment.get(
                        "notice_context_in_parent_page"
                    ),
            },
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

            "search_attempts":
                local_search_records,

            "visited_document_pages":
                local_page_records,

            "html_document_candidate_count":
                len(
                    local_document_candidates
                ),

            "attachment_candidate_count":
                len(
                    local_attachment_candidates
                ),
        }
    )

    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# DEDUPE HTML DOCUMENT CANDIDATES
# ============================================================

deduped_documents = []

seen_documents = set()

for candidate in document_candidates:

    normalized_candidate_url = normalize_url(
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
        normalized_candidate_url,
    )

    if key in seen_documents:

        continue

    seen_documents.add(
        key
    )

    normalized_candidate = dict(
        candidate
    )

    normalized_candidate[
        "url"
    ] = normalized_candidate_url

    deduped_documents.append(
        normalized_candidate
    )


# ============================================================
# DEDUPE ATTACHMENTS
# ============================================================

deduped_attachments = []

seen_attachments = set()

for attachment in attachment_candidates:

    # 안전장치:
    # 전역 collection 단계에서 누락이 있어도
    # 최종 결과에는 irrelevant attachment를 통과시키지 않는다.
    if not attachment.get(
        "relevant_attachment_candidate"
    ):

        continue

    normalized_attachment_url = normalize_url(
        str(
            attachment.get(
                "url"
            )
            or ""
        )
    )

    key = (
        attachment.get(
            "region"
        ),
        normalized_attachment_url,
    )

    if key in seen_attachments:

        continue

    seen_attachments.add(
        key
    )

    normalized_attachment = dict(
        attachment
    )

    normalized_attachment[
        "url"
    ] = normalized_attachment_url

    deduped_attachments.append(
        normalized_attachment
    )


# ============================================================
# PRIORITIZE ATTACHMENTS
# ============================================================

for attachment in deduped_attachments:

    score = 0

    if (
        attachment.get(
            "target_in_label"
        )
        is True
    ):

        score += 5

    if (
        attachment.get(
            "target_in_url"
        )
        is True
    ):

        score += 4

    if (
        attachment.get(
            "target_in_parent_page"
        )
        is True
    ):

        score += 3

    if (
        attachment.get(
            "notice_context_in_label"
        )
        is True
    ):

        score += 2

    if (
        attachment.get(
            "notice_context_in_parent_page"
        )
        is True
    ):

        score += 2

    if attachment.get(
        "extension"
    ) in {
        "hwp",
        "hwpx",
        "pdf",
    }:

        score += 1

    attachment[
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
# RESOLUTION
# ============================================================

if (
    deduped_documents
    or deduped_attachments
):

    resolution = (
        "MUNICIPAL_OFFICIAL_DOCUMENT_OR_ATTACHMENT_CANDIDATE_DISCOVERED"
    )

    next_action = (
        "후보 HTML 게시물과 relevance가 확인된 "
        "HWP/HWPX/PDF 첨부파일을 개별 원문 검증하여 "
        "실제 개발밀도관리구역 지정·변경·해제 고시인지 확정하고, "
        "고시번호·지정일·범위·현재 유효 여부를 추출한 뒤 "
        "positive PNU 및 spatial source를 역탐색한다."
    )

else:

    resolution = (
        "MUNICIPAL_OFFICIAL_ATTACHMENT_DISCOVERY_COMPLETED_NO_CANDIDATE"
    )

    next_action = (
        "시군구 공보 전용 시스템, 국가기록원, 토지이음, "
        "국가법령정보/관보 및 지자체 첨부파일 검색 endpoint로 "
        "탐색 범위를 확장한다."
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
        "STEP 17-21-C-16-8-E "
        "Development Density Management Area "
        "Municipal Official Notice / Attachment Discovery"
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

        "search_pages_final_positive_allowed":
            False,

        "html_document_discovery":
            True,

        "attachment_discovery":
            True,

        "attachment_relevance_guard":
            True,

        "attachment_extension_only_candidate_allowed":
            False,

        "attachment_extensions":
            list(
                ATTACHMENT_EXTENSIONS
            ),

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

        "search_page_positive_leakage":
            search_page_positive_leakage,

        "irrelevant_attachment_filtered_count":
            irrelevant_attachment_filtered_count,

        "html_document_candidate_count":
            len(
                deduped_documents
            ),

        "attachment_candidate_count":
            len(
                deduped_attachments
            ),
    },

    "html_document_candidates":
        deduped_documents,

    "attachment_candidates":
        deduped_attachments,

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
    "Search-page positive leakage:",
    search_page_positive_leakage,
)

print(
    "Irrelevant attachment filtered:",
    irrelevant_attachment_filtered_count,
)

print(
    "HTML document candidate count:",
    len(
        deduped_documents
    ),
)

print(
    "Attachment candidate count:",
    len(
        deduped_attachments
    ),
)

print()


if deduped_documents:

    print(
        "HTML DOCUMENT CANDIDATES"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, candidate in enumerate(
        deduped_documents,
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
            "Attachments:",
            candidate.get(
                "attachment_count"
            ),
        )

        print(
            "Preview:",
            candidate.get(
                "preview"
            ),
        )

        print()


if deduped_attachments:

    print(
        "ATTACHMENT CANDIDATES"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, attachment in enumerate(
        deduped_attachments[
            :50
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            attachment.get(
                "region"
            ),
        )

        print(
            "Type:",
            attachment.get(
                "extension"
            ),
        )

        print(
            "Score:",
            attachment.get(
                "priority_score"
            ),
        )

        print(
            "Label:",
            attachment.get(
                "label"
            ),
        )

        print(
            "Parent:",
            attachment.get(
                "parent_page_url"
            ),
        )

        print(
            "URL:",
            attachment.get(
                "url"
            ),
        )

        print(
            "Target evidence:",
            {
                "label":
                    attachment.get(
                        "target_in_label"
                    ),

                "url":
                    attachment.get(
                        "target_in_url"
                    ),

                "parent":
                    attachment.get(
                        "target_in_parent_page"
                    ),

                "parent_notice":
                    attachment.get(
                        "notice_context_in_parent_page"
                    ),
            },
        )

        print()


if not (
    deduped_documents
    or deduped_attachments
):

    print(
        "No official municipal document or "
        "relevant attachment candidate discovered."
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

html_document_candidate_keys = {
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
    in deduped_documents
}


attachment_candidate_keys = {
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
    in deduped_attachments
}


html_candidates_contain_target = all(
    item.get(
        "target_found"
    )
    is True
    for item
    in deduped_documents
)


html_candidates_have_strong_context = all(
    item.get(
        "strong_notice_context"
    )
    is True
    for item
    in deduped_documents
)


html_candidates_not_search_pages = all(
    item.get(
        "search_page"
    )
    is False
    for item
    in deduped_documents
)


html_candidates_not_zero_result_pages = all(
    item.get(
        "zero_result_page"
    )
    is False
    for item
    in deduped_documents
)


attachment_candidates_supported_extension = all(
    item.get(
        "extension"
    )
    in {
        "pdf",
        "hwp",
        "hwpx",
    }
    for item
    in deduped_attachments
)


attachment_candidates_have_parent_page = all(
    bool(
        item.get(
            "parent_page_url"
        )
    )
    for item
    in deduped_attachments
)


attachment_candidates_have_urls = all(
    bool(
        item.get(
            "url"
        )
    )
    for item
    in deduped_attachments
)


attachment_candidates_relevant = all(
    item.get(
        "relevant_attachment_candidate"
    )
    is True
    for item
    in deduped_attachments
)


attachment_candidates_have_target_evidence = all(
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
    for item
    in deduped_attachments
)


attachment_candidates_not_extension_only = all(
    (
        item.get(
            "target_in_label"
        )
        is True
        or item.get(
            "target_in_url"
        )
        is True
        or item.get(
            "target_in_parent_page"
        )
        is True
    )
    for item
    in deduped_attachments
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

    "search pages prohibited as final positive": (
        output_data[
            "method"
        ][
            "search_pages_final_positive_allowed"
        ]
        is False
    ),

    "attachment relevance guard enabled": (
        output_data[
            "method"
        ][
            "attachment_relevance_guard"
        ]
        is True
    ),

    "extension-only candidate prohibited": (
        output_data[
            "method"
        ][
            "attachment_extension_only_candidate_allowed"
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

    "search-page positive leakage zero": (
        search_page_positive_leakage
        == 0
    ),

    "HTML document candidates unique": (
        len(
            html_document_candidate_keys
        )
        == len(
            deduped_documents
        )
    ),

    "attachment candidates unique": (
        len(
            attachment_candidate_keys
        )
        == len(
            deduped_attachments
        )
    ),

    "all HTML document candidates contain target": (
        html_candidates_contain_target
    ),

    "all HTML document candidates have strong context": (
        html_candidates_have_strong_context
    ),

    "all HTML document candidates are not search pages": (
        html_candidates_not_search_pages
    ),

    "all HTML document candidates are not zero-result pages": (
        html_candidates_not_zero_result_pages
    ),

    "all attachment candidates have supported extension": (
        attachment_candidates_supported_extension
    ),

    "all attachment candidates have parent page": (
        attachment_candidates_have_parent_page
    ),

    "all attachment candidates have URL": (
        attachment_candidates_have_urls
    ),

    "all attachment candidates are relevant": (
        attachment_candidates_relevant
    ),

    "all attachment candidates have target evidence": (
        attachment_candidates_have_target_evidence
    ),

    "no attachment candidate is extension-only": (
        attachment_candidates_not_extension_only
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
        "municipal attachment discovery regression failed"
    )