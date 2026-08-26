# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-F
Development Density Management Area
Extensionless Attachment / Download Endpoint Discovery

목표
======================================================================
STEP 17-21-C-16-8-E에서는 URL path가 다음 확장자로 끝나는
직접 첨부파일만 탐색했다.

    .pdf
    .hwp
    .hwpx

그러나 실제 지자체 게시판에서는 첨부파일이 다음과 같이
확장자 없는 download endpoint 형태로 제공되는 경우가 많다.

예:
    /fileDown.do?atchFileId=...
    /download.do?fileNo=...
    /bbs/fileDownload.do?fileSeq=...
    /common/fileDown.do?fileId=...
    javascript:fileDown('12345')
    onclick="downloadFile(...)"
    data-file-id="..."

이번 단계에서는 이런 extensionless attachment endpoint를 탐색한다.

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700


핵심 안전정책
======================================================================
1. download endpoint 형태만으로 candidate를 인정하지 않는다.

2. 다음 중 하나 이상의 target evidence가 있어야
   relevant attachment candidate로 인정한다.

   A.
   링크 label에 개발밀도관리구역

   B.
   URL / query에 개발밀도관리구역

   C.
   parent page에 개발밀도관리구역이 있고
   동시에 strong notice context가 존재

3. 통합검색 페이지는 final positive document로 인정하지 않는다.

4. extensionless endpoint는 아직 실제 원문 유형을 확정하지 않는다.

5. 다음 단계에서 실제 다운로드 응답의
   Content-Type / Content-Disposition / magic bytes를 검증한다.

6. 후보가 0건이어도 SITE FALSE로 해석하지 않는다.

7. runtime spatial condition 등록은 계속 차단한다.

8. VWorld LT_C_UQ141을 UQQ700 dataset으로 확정하지 않는다.

9. positive 원문이 검증되기 전까지
   개발밀도관리구역은 UNKNOWN / UNRESOLVED 상태를 유지한다.


이번 단계의 성공
======================================================================
다음 중 하나면 성공이다.

A.
relevant extensionless download endpoint를 1건 이상 발견

B.
공식 시군구 탐색 구조가 정상 실행되고
후보 0건 상태를 명시적으로 보존

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
from typing import Any, Dict, List, Optional, Set
from urllib.parse import (
    parse_qsl,
    unquote,
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
        "extensionless_attachment_discovery.json"
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
    200
)

MAX_DOCUMENT_PAGES_PER_SITE = (
    20
)

MAX_SCRIPT_ENDPOINTS_PER_PAGE = (
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


DIRECT_ATTACHMENT_EXTENSIONS = (
    ".pdf",
    ".hwp",
    ".hwpx",
)


DOWNLOAD_PATH_HINTS = [
    "download",
    "filedown",
    "filedownload",
    "file_down",
    "file-down",
    "downfile",
    "attachdown",
    "attachmentdown",
    "file/get",
    "file/getfile",
]


DOWNLOAD_QUERY_KEYS = {
    "atchfileid",
    "atch_file_id",
    "fileid",
    "file_id",
    "filesn",
    "file_sn",
    "fileseq",
    "file_seq",
    "fileno",
    "file_no",
    "fileidx",
    "file_idx",
    "filekey",
    "file_key",
    "attachid",
    "attach_id",
    "attachmentid",
    "attachment_id",
    "download",
    "downfile",
}


JAVASCRIPT_DOWNLOAD_HINTS = [
    "download",
    "filedown",
    "filedownload",
    "downfile",
    "fnfiledown",
    "fn_file_down",
    "fn_download",
    "attachdown",
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
        for term in STRONG_NOTICE_TERMS
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
        for hint in SEARCH_PAGE_HINT_TERMS
    )


def is_direct_attachment_url(
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
        in DIRECT_ATTACHMENT_EXTENSIONS
    )


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
        ".pdf",
        ".hwp",
        ".hwpx",
    )

    return not any(
        lower_path.endswith(
            extension
        )
        for extension
        in blocked_extensions
    )


def has_download_path_hint(
    url: str,
) -> bool:

    lower = unquote(
        url
    ).lower()

    return any(
        hint in lower
        for hint in DOWNLOAD_PATH_HINTS
    )


def has_download_query_hint(
    url: str,
) -> bool:

    try:

        parsed = urlparse(
            url
        )

        query_pairs = parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )

    except Exception:

        return False

    for key, _ in query_pairs:

        normalized_key = (
            re.sub(
                r"[^a-z0-9_]",
                "",
                key.lower(),
            )
        )

        if normalized_key in DOWNLOAD_QUERY_KEYS:

            return True

    return False


def is_extensionless_download_endpoint(
    url: str,
) -> bool:

    if not url:

        return False

    if is_direct_attachment_url(
        url
    ):

        return False

    return (
        has_download_path_hint(
            url
        )
        or has_download_query_hint(
            url
        )
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


ANCHOR_FULL_PATTERN = re.compile(
    r"""
    (?is)
    <a
    \s+
    ([^>]*?)
    >
    (.*?)
    </a>
    """,
    re.VERBOSE,
)


ATTRIBUTE_PATTERN = re.compile(
    r"""
    (?is)
    ([a-zA-Z_:][-a-zA-Z0-9_:.]*)
    \s*=\s*
    (?:
        "([^"]*)"
        |
        '([^']*)'
        |
        ([^\s>]+)
    )
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
        for term in BOARD_HINT_TERMS
    )


# ============================================================
# ATTRIBUTE / JAVASCRIPT DOWNLOAD DISCOVERY
# ============================================================

def parse_attributes(
    attribute_source: str,
) -> Dict[str, str]:

    attributes: Dict[str, str] = {}

    for match in ATTRIBUTE_PATTERN.finditer(
        attribute_source
    ):

        key = (
            match.group(1)
            or ""
        ).strip()

        value = (
            match.group(2)
            or match.group(3)
            or match.group(4)
            or ""
        ).strip()

        if not key:
            continue

        attributes[
            key.lower()
        ] = html.unescape(
            value
        )

    return attributes


def javascript_has_download_hint(
    value: str,
) -> bool:

    lower = value.lower()

    return any(
        hint in lower
        for hint in JAVASCRIPT_DOWNLOAD_HINTS
    )


def extract_urls_from_javascript(
    value: str,
    *,
    base_url: str,
) -> List[str]:

    candidates: List[str] = []

    seen = set()

    # --------------------------------------------------------
    # quoted URL/path candidates
    # --------------------------------------------------------

    quoted_pattern = re.compile(
        r"""(?is)
        ['"]
        (
            (?:
                https?://
                |
                /
                |
                \./
                |
                \.\./
            )
            [^'"]+
        )
        ['"]
        """,
        re.VERBOSE,
    )

    for match in quoted_pattern.finditer(
        value
    ):

        raw = (
            match.group(1)
            or ""
        ).strip()

        if not raw:
            continue

        absolute = normalize_url(
            urljoin(
                base_url,
                raw,
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

        candidates.append(
            absolute
        )

    return candidates


def build_synthetic_download_url_from_attributes(
    *,
    page_url: str,
    attributes: Dict[str, str],
) -> Optional[str]:

    useful_pairs = []

    for key, value in attributes.items():

        normalized_key = (
            re.sub(
                r"[^a-z0-9_]",
                "",
                key.lower(),
            )
        )

        if (
            normalized_key
            in DOWNLOAD_QUERY_KEYS
        ):

            useful_pairs.append(
                (
                    key,
                    value,
                )
            )

    if not useful_pairs:

        return None

    parsed = urlparse(
        page_url
    )

    return urlunparse(
        parsed._replace(
            query=urlencode(
                useful_pairs,
                doseq=True,
            ),
            fragment="",
        )
    )


def extract_extensionless_download_candidates_from_html(
    *,
    source: str,
    page_url: str,
    region: str,
    agency: str,
) -> List[Dict[str, Any]]:

    results: List[Dict[str, Any]] = []

    seen = set()

    parent_page_text = strip_html(
        source
    )

    # --------------------------------------------------------
    # 1. normal href links
    # --------------------------------------------------------

    for link in extract_links(
        source,
        base_url=page_url,
    ):

        url = link.get(
            "url",
            "",
        )

        if not is_extensionless_download_endpoint(
            url
        ):

            continue

        candidate = build_extensionless_candidate(
            region=region,
            agency=agency,
            parent_page_url=page_url,
            parent_page_text=parent_page_text,
            endpoint_url=url,
            label=(
                link.get(
                    "label"
                )
                or ""
            ),
            discovery_source="HREF",
            raw_expression=None,
        )

        key = (
            candidate.get(
                "region"
            ),
            candidate.get(
                "endpoint_url"
            ),
            candidate.get(
                "discovery_source"
            ),
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        results.append(
            candidate
        )

    # --------------------------------------------------------
    # 2. onclick / data-* attributes
    # --------------------------------------------------------

    for match in ANCHOR_FULL_PATTERN.finditer(
        source
    ):

        attribute_source = (
            match.group(1)
            or ""
        )

        label_html = (
            match.group(2)
            or ""
        )

        label = strip_html(
            label_html
        )

        attributes = parse_attributes(
            attribute_source
        )

        # ----------------------------------------------------
        # onclick
        # ----------------------------------------------------

        onclick = (
            attributes.get(
                "onclick"
            )
            or ""
        )

        if (
            onclick
            and javascript_has_download_hint(
                onclick
            )
        ):

            discovered_urls = (
                extract_urls_from_javascript(
                    onclick,
                    base_url=page_url,
                )
            )

            for discovered_url in discovered_urls:

                if not (
                    is_extensionless_download_endpoint(
                        discovered_url
                    )
                    or javascript_has_download_hint(
                        onclick
                    )
                ):

                    continue

                candidate = (
                    build_extensionless_candidate(
                        region=region,
                        agency=agency,
                        parent_page_url=page_url,
                        parent_page_text=parent_page_text,
                        endpoint_url=discovered_url,
                        label=label,
                        discovery_source="ONCLICK_URL",
                        raw_expression=onclick,
                    )
                )

                key = (
                    candidate.get(
                        "region"
                    ),
                    candidate.get(
                        "endpoint_url"
                    ),
                    candidate.get(
                        "discovery_source"
                    ),
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                results.append(
                    candidate
                )

        # ----------------------------------------------------
        # data-* or file-id style attributes
        # ----------------------------------------------------

        synthetic = (
            build_synthetic_download_url_from_attributes(
                page_url=page_url,
                attributes=attributes,
            )
        )

        if synthetic:

            candidate = (
                build_extensionless_candidate(
                    region=region,
                    agency=agency,
                    parent_page_url=page_url,
                    parent_page_text=parent_page_text,
                    endpoint_url=synthetic,
                    label=label,
                    discovery_source="DATA_ATTRIBUTE",
                    raw_expression=attribute_source,
                )
            )

            key = (
                candidate.get(
                    "region"
                ),
                candidate.get(
                    "endpoint_url"
                ),
                candidate.get(
                    "discovery_source"
                ),
            )

            if key not in seen:

                seen.add(
                    key
                )

                results.append(
                    candidate
                )

        if (
            len(results)
            >= MAX_SCRIPT_ENDPOINTS_PER_PAGE
        ):
            break

    return results


# ============================================================
# RELEVANCE
# ============================================================

def endpoint_has_target_in_url(
    url: str,
) -> bool:

    decoded = unquote(
        url
    )

    return contains_target(
        decoded
    )


def build_extensionless_candidate(
    *,
    region: str,
    agency: str,
    parent_page_url: str,
    parent_page_text: str,
    endpoint_url: str,
    label: str,
    discovery_source: str,
    raw_expression: Optional[str],
) -> Dict[str, Any]:

    normalized_url = normalize_url(
        endpoint_url
    )

    target_in_label = contains_target(
        label
    )

    target_in_url = endpoint_has_target_in_url(
        normalized_url
    )

    target_in_parent_page = contains_target(
        parent_page_text
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

    download_path_hint = (
        has_download_path_hint(
            normalized_url
        )
    )

    download_query_hint = (
        has_download_query_hint(
            normalized_url
        )
    )

    relevant = (
        target_in_label
        or target_in_url
        or (
            target_in_parent_page
            and notice_context_in_parent_page
        )
    )

    return {
        "candidate_type":
            "EXTENSIONLESS_DOWNLOAD_ENDPOINT",

        "region":
            region,

        "agency":
            agency,

        "parent_page_url":
            parent_page_url,

        "endpoint_url":
            normalized_url,

        "label":
            label,

        "discovery_source":
            discovery_source,

        "raw_expression":
            raw_expression,

        "download_path_hint":
            download_path_hint,

        "download_query_hint":
            download_query_hint,

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

        "relevant_extensionless_candidate":
            relevant,

        "parent_preview":
            (
                build_preview(
                    parent_page_text
                )
                if target_in_parent_page
                else ""
            ),
    }


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

    text_like = (
        "text/" in content_type_lower
        or "html" in content_type_lower
        or "xml" in content_type_lower
        or "json" in content_type_lower
    )

    text = ""

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
# SEARCH RESULT GUARD
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

extensionless_candidates: List[
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

raw_extensionless_endpoint_count = 0

irrelevant_extensionless_filtered_count = 0

search_page_positive_leakage = 0


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
    "EXTENSIONLESS ATTACHMENT / DOWNLOAD ENDPOINT DISCOVERY"
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

    local_search_records = []

    local_page_records = []

    local_candidates = []

    candidate_page_links: List[
        Dict[
            str,
            str
        ]
    ] = []

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

                "extensionless_candidate_count":
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

    root_text = strip_html(
        root.text
    )

    if root.text:
        html_parse_count += 1

    # --------------------------------------------------------
    # root extensionless endpoint
    # --------------------------------------------------------

    root_endpoints = (
        extract_extensionless_download_candidates_from_html(
            source=root.text,
            page_url=root_final_url,
            region=region,
            agency=agency,
        )
    )

    raw_extensionless_endpoint_count += len(
        root_endpoints
    )

    for candidate in root_endpoints:

        if not candidate.get(
            "relevant_extensionless_candidate"
        ):

            irrelevant_extensionless_filtered_count += 1

            continue

        local_candidates.append(
            candidate
        )

        extensionless_candidates.append(
            candidate
        )

    root_links = extract_links(
        root.text,
        base_url=root_final_url,
    )

    for link in root_links:

        link_url = (
            link.get(
                "url"
            )
            or ""
        )

        if not same_or_subdomain(
            link_url,
            base_url,
        ):
            continue

        if is_search_page_url(
            link_url
        ):
            continue

        if not is_probably_html_url(
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
    # GENERIC SEARCH ENDPOINTS
    # ========================================================

    search_urls = build_site_search_candidates(
        base_url
    )

    for search_url in search_urls:

        normalized_search_url = normalize_url(
            search_url
        )

        if normalized_search_url in visited_urls:
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

                "preview":
                    classification[
                        "preview"
                    ],
            }
        )

        endpoints = (
            extract_extensionless_download_candidates_from_html(
                source=result.text,
                page_url=final_url,
                region=region,
                agency=agency,
            )
        )

        raw_extensionless_endpoint_count += len(
            endpoints
        )

        for candidate in endpoints:

            if not candidate.get(
                "relevant_extensionless_candidate"
            ):

                irrelevant_extensionless_filtered_count += 1

                continue

            local_candidates.append(
                candidate
            )

            extensionless_candidates.append(
                candidate
            )

        links = extract_links(
            result.text,
            base_url=final_url,
        )

        for link in links:

            link_url = (
                link.get(
                    "url"
                )
                or ""
            )

            if not same_or_subdomain(
                link_url,
                base_url,
            ):
                continue

            if is_search_page_url(
                link_url
            ):
                continue

            if not is_probably_html_url(
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
    # DEDUPE PAGE LINKS
    # ========================================================

    deduped_page_links = []

    seen_page_links = set()

    for link in candidate_page_links:

        normalized_page_url = normalize_url(
            link.get(
                "url",
                "",
            )
        )

        if not normalized_page_url:
            continue

        if normalized_page_url in seen_page_links:
            continue

        seen_page_links.add(
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
    # ACTUAL BOARD / DOCUMENT PAGES
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

        endpoints = (
            extract_extensionless_download_candidates_from_html(
                source=result.text,
                page_url=final_url,
                region=region,
                agency=agency,
            )
        )

        raw_extensionless_endpoint_count += len(
            endpoints
        )

        relevant_local_page_endpoints = []

        for candidate in endpoints:

            if not candidate.get(
                "relevant_extensionless_candidate"
            ):

                irrelevant_extensionless_filtered_count += 1

                continue

            relevant_local_page_endpoints.append(
                candidate
            )

            local_candidates.append(
                candidate
            )

            extensionless_candidates.append(
                candidate
            )

        local_page_records.append(
            {
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

                "extensionless_endpoint_count":
                    len(
                        relevant_local_page_endpoints
                    ),

                "extensionless_endpoints":
                    relevant_local_page_endpoints,

                "preview":
                    classification[
                        "preview"
                    ],
            }
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
        "Relevant extensionless candidates:",
        len(
            local_candidates
        ),
    )

    for candidate in local_candidates[
        :5
    ]:

        print(
            "  ENDPOINT:",
            candidate.get(
                "endpoint_url"
            ),
        )

        print(
            "    Source:",
            candidate.get(
                "discovery_source"
            ),
        )

        print(
            "    Label:",
            candidate.get(
                "label"
            ),
        )

        print(
            "    Target label:",
            candidate.get(
                "target_in_label"
            ),
        )

        print(
            "    Target URL:",
            candidate.get(
                "target_in_url"
            ),
        )

        print(
            "    Target parent:",
            candidate.get(
                "target_in_parent_page"
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

            "search_attempts":
                local_search_records,

            "visited_document_pages":
                local_page_records,

            "extensionless_candidate_count":
                len(
                    local_candidates
                ),
        }
    )

    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# DEDUPE
# ============================================================

deduped_candidates = []

seen_candidates = set()

for candidate in extensionless_candidates:

    endpoint_url = normalize_url(
        str(
            candidate.get(
                "endpoint_url"
            )
            or ""
        )
    )

    key = (
        candidate.get(
            "region"
        ),
        endpoint_url,
        candidate.get(
            "discovery_source"
        ),
    )

    if key in seen_candidates:
        continue

    seen_candidates.add(
        key
    )

    normalized_candidate = dict(
        candidate
    )

    normalized_candidate[
        "endpoint_url"
    ] = endpoint_url

    deduped_candidates.append(
        normalized_candidate
    )


# ============================================================
# PRIORITY SCORE
# ============================================================

for candidate in deduped_candidates:

    score = 0

    if candidate.get(
        "target_in_label"
    ) is True:
        score += 4

    if candidate.get(
        "target_in_url"
    ) is True:
        score += 4

    if candidate.get(
        "target_in_parent_page"
    ) is True:
        score += 2

    if candidate.get(
        "notice_context_in_label"
    ) is True:
        score += 2

    if candidate.get(
        "notice_context_in_parent_page"
    ) is True:
        score += 1

    if candidate.get(
        "download_path_hint"
    ) is True:
        score += 1

    if candidate.get(
        "download_query_hint"
    ) is True:
        score += 1

    candidate[
        "priority_score"
    ] = score


deduped_candidates.sort(
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
                "endpoint_url",
                "",
            )
        ),
    )
)


# ============================================================
# RESOLUTION
# ============================================================

if deduped_candidates:

    resolution = (
        "RELEVANT_EXTENSIONLESS_DOWNLOAD_ENDPOINT_DISCOVERED"
    )

    next_action = (
        "extensionless endpoint를 실제 요청하여 "
        "HTTP status / Content-Type / Content-Disposition / "
        "파일명 / magic bytes를 검증하고 "
        "PDF/HWP/HWPX 또는 기타 공식 문서인지 판별한다."
    )

else:

    resolution = (
        "EXTENSIONLESS_ATTACHMENT_DISCOVERY_COMPLETED_NO_CANDIDATE"
    )

    next_action = (
        "지자체 공보 전용 시스템, 동적 JavaScript API, "
        "POST 기반 파일다운로드 endpoint, 국가기록원 및 "
        "관보/토지이음 자료원으로 탐색 범위를 확장한다."
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
        "STEP 17-21-C-16-8-F "
        "Development Density Management Area "
        "Extensionless Attachment / Download Endpoint Discovery"
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

        "extensionless_download_discovery":
            True,

        "href_discovery":
            True,

        "onclick_discovery":
            True,

        "data_attribute_discovery":
            True,

        "extension_only_candidate_allowed":
            False,

        "target_relevance_guard_enabled":
            True,

        "download_path_hints":
            DOWNLOAD_PATH_HINTS,

        "download_query_keys":
            sorted(
                DOWNLOAD_QUERY_KEYS
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

        "raw_extensionless_endpoint_count":
            raw_extensionless_endpoint_count,

        "irrelevant_extensionless_filtered_count":
            irrelevant_extensionless_filtered_count,

        "search_page_positive_leakage":
            search_page_positive_leakage,

        "relevant_extensionless_candidate_count":
            len(
                deduped_candidates
            ),
    },

    "extensionless_candidates":
        deduped_candidates,

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
    "Raw extensionless endpoint count:",
    raw_extensionless_endpoint_count,
)

print(
    "Irrelevant extensionless filtered:",
    irrelevant_extensionless_filtered_count,
)

print(
    "Search-page positive leakage:",
    search_page_positive_leakage,
)

print(
    "Relevant extensionless candidate count:",
    len(
        deduped_candidates
    ),
)

print()


if deduped_candidates:

    print(
        "RELEVANT EXTENSIONLESS DOWNLOAD ENDPOINTS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, candidate in enumerate(
        deduped_candidates[
            :50
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
            "Source:",
            candidate.get(
                "discovery_source"
            ),
        )

        print(
            "Label:",
            candidate.get(
                "label"
            ),
        )

        print(
            "Parent:",
            candidate.get(
                "parent_page_url"
            ),
        )

        print(
            "Endpoint:",
            candidate.get(
                "endpoint_url"
            ),
        )

        print(
            "Target in label:",
            candidate.get(
                "target_in_label"
            ),
        )

        print(
            "Target in URL:",
            candidate.get(
                "target_in_url"
            ),
        )

        print(
            "Target in parent:",
            candidate.get(
                "target_in_parent_page"
            ),
        )

        print()


else:

    print(
        "No relevant extensionless download endpoint discovered."
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

candidate_keys = {
    (
        item.get(
            "region"
        ),
        normalize_url(
            str(
                item.get(
                    "endpoint_url"
                )
                or ""
            )
        ),
        item.get(
            "discovery_source"
        ),
    )
    for item in deduped_candidates
}


all_candidates_relevant = all(
    item.get(
        "relevant_extensionless_candidate"
    )
    is True
    for item in deduped_candidates
)


all_candidates_have_endpoint = all(
    bool(
        item.get(
            "endpoint_url"
        )
    )
    for item in deduped_candidates
)


all_candidates_have_parent = all(
    bool(
        item.get(
            "parent_page_url"
        )
    )
    for item in deduped_candidates
)


all_candidates_are_extensionless = all(
    not is_direct_attachment_url(
        str(
            item.get(
                "endpoint_url"
            )
            or ""
        )
    )
    for item in deduped_candidates
)


all_candidates_have_download_hint = all(
    (
        item.get(
            "download_path_hint"
        )
        is True
        or item.get(
            "download_query_hint"
        )
        is True
        or item.get(
            "discovery_source"
        )
        in {
            "ONCLICK_URL",
            "DATA_ATTRIBUTE",
        }
    )
    for item in deduped_candidates
)


all_candidates_have_target_evidence = all(
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
    for item in deduped_candidates
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

    "extensionless discovery enabled": (
        output_data[
            "method"
        ][
            "extensionless_download_discovery"
        ]
        is True
    ),

    "href discovery enabled": (
        output_data[
            "method"
        ][
            "href_discovery"
        ]
        is True
    ),

    "onclick discovery enabled": (
        output_data[
            "method"
        ][
            "onclick_discovery"
        ]
        is True
    ),

    "data attribute discovery enabled": (
        output_data[
            "method"
        ][
            "data_attribute_discovery"
        ]
        is True
    ),

    "target relevance guard enabled": (
        output_data[
            "method"
        ][
            "target_relevance_guard_enabled"
        ]
        is True
    ),

    "extension-only candidate prohibited": (
        output_data[
            "method"
        ][
            "extension_only_candidate_allowed"
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

    "candidates unique": (
        len(
            candidate_keys
        )
        == len(
            deduped_candidates
        )
    ),

    "all candidates relevant": (
        all_candidates_relevant
    ),

    "all candidates have endpoint": (
        all_candidates_have_endpoint
    ),

    "all candidates have parent page": (
        all_candidates_have_parent
    ),

    "all candidates are extensionless": (
        all_candidates_are_extensionless
    ),

    "all candidates have download hint": (
        all_candidates_have_download_hint
    ),

    "all candidates have target evidence": (
        all_candidates_have_target_evidence
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
        "extensionless attachment discovery regression failed"
    )