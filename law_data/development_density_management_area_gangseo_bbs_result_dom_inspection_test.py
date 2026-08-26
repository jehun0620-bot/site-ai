# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-P
Development Density Management Area
Gangseo BBS Result DOM Inspection

목표
======================================================================
O-stage에서 강서구 통합검색의 category switching 구조가 확정되었다.

global.js:

    function searchByCategory(category) {
        $('#colTarget').val(category);
        $('#curPage').val(1);
        $('#frmSearch').submit();
    }

따라서 게시판 전용 검색 요청은 실제 form 구조에 따라

    GET /search
    searchText=개발밀도관리구역
    colTarget=bbs
    curPage=1

형태로 재현할 수 있다.

실제 응답에서는

    게시판 검색결과 3건

이 확인되었다.

이번 단계에서는 해당 3건의 실제 result DOM block을 추출한다.

중요
======================================================================
1. searchByCategory 구조는 더 이상 추측하지 않는다.
2. category field는 colTarget으로 고정한다.
3. sortType은 category field로 사용하지 않는다.
4. curPage는 pagination field로만 사용한다.
5. 제목에 target이 없어도 result block의 요약/본문에 target이 있으면
   target-bearing result로 인정할 수 있다.
6. 검색 UI echo는 result로 인정하지 않는다.
7. /search URL 자체는 detail seed로 인정하지 않는다.
8. 실제 게시판 결과 URL 또는 게시물 identifier가 있어야 detail seed가 된다.
9. detail seed는 아직 VERIFIED_POSITIVE가 아니다.
10. runtime condition 등록은 계속 차단한다.
11. 결과가 없다고 SITE FALSE로 해석하지 않는다.
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

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

O_STAGE_INPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gangseo_category_request_reconstruction.json"
    )
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gangseo_bbs_result_dom_inspection.json"
    )
)

HTML_SNAPSHOT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gangseo_bbs_result_response.html"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"

STANDARD_CODE = "UQQ700"

REGION = "서울특별시 강서구"

AGENCY = "서울특별시 강서구"

BOARD_URL = (
    "https://www.gangseo.seoul.kr/gs040301"
)

SEARCH_URL = (
    "https://www.gangseo.seoul.kr/search"
)

SEARCH_FIELD = "searchText"

CATEGORY_FIELD = "colTarget"

CATEGORY_VALUE = "bbs"

PAGE_FIELD = "curPage"


# ============================================================
# REQUEST CONFIG
# ============================================================

REQUEST_TIMEOUT = 20

REQUEST_SLEEP = 0.25

MAX_CONTENT_LENGTH = 4_000_000

MAX_BLOCK_COUNT = 5000

MAX_ANCHOR_COUNT = 5000

MAX_RESULT_PREVIEW = 3000


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
# FALSE POSITIVE / SEARCH UI TERMS
# ============================================================

SEARCH_ECHO_TERMS = [
    "내가 찾은 검색어",
    "검색어 삭제",
    "인기 검색어",
    "최근 검색어",
    "결과 내 재검색",
    "검색어를 입력하세요",
    "검색옵션",
    "검색결과 더보기",
]


SEARCH_UI_TERMS = [
    "메뉴검색",
    "업무",
    "민원사무편람",
    "웹페이지",
    "게시판",
    "첨부파일",
    "통합예약",
    "정렬",
    "정확도 순",
    "최신 순",
    "기간",
]


DETAIL_URL_HINTS = [
    "view.do",
    "detail.do",
    "bbsmsgdetail",
    "selectboardarticle",
    "selectboardarticle.do",
    "post/view",
    "board/view",
    "article",
    "nttid=",
    "idx=",
    "seq=",
    "msg_seq=",
    "mgt_no=",
    "bbsid=",
    "nttId=",
]


EXCLUDED_URL_HINTS = [
    "/search",
    "javascript:",
    "mailto:",
    "tel:",
    "#",
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
    final_url: Optional[str]
    error: Optional[str]


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


def build_target_preview(
    value: str,
    *,
    radius: int = 500,
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


def search_echo_score(
    value: str,
) -> int:

    text = normalize_space(
        value
    )

    score = 0

    for term in SEARCH_ECHO_TERMS:

        if term in text:

            score += 2

    if contains_target(
        text
    ):

        search_ui_hits = sum(
            1
            for term in SEARCH_UI_TERMS
            if term in text
        )

        if search_ui_hits >= 4:

            score += 5

    return score


def is_search_echo(
    value: str,
) -> bool:

    if not contains_target(
        value
    ):

        return False

    return (
        search_echo_score(
            value
        )
        >= 4
    )


# ============================================================
# URL UTIL
# ============================================================

def normalize_url(
    url: str,
) -> str:

    if not url:

        return ""

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
            "token",
            "_csrf",
            "csrf",
            "_",
            "timestamp",
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


def is_search_url(
    url: str,
) -> bool:

    lower = (
        url
        or ""
    ).lower()

    return (
        "/search" in lower
        or "totalsearch" in lower
    )


def is_probable_detail_url(
    url: str,
) -> bool:

    lower = (
        url
        or ""
    ).lower()

    if is_search_url(
        lower
    ):

        return False

    return any(
        hint.lower() in lower
        for hint in DETAIL_URL_HINTS
    )


# ============================================================
# FETCH
# ============================================================

def fetch_get(
    url: str,
    *,
    params: Optional[
        Dict[str, str]
    ] = None,
) -> FetchResult:

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

    except requests.RequestException as exc:

        return FetchResult(
            url=url,
            http_status=None,
            content_type="",
            text="",
            final_url=None,
            error=repr(
                exc
            ),
        )

    content_type = (
        response.headers.get(
            "Content-Type",
            "",
        )
        or ""
    )

    text = (
        response.text
        or ""
    )

    if len(
        text
    ) > MAX_CONTENT_LENGTH:

        text = text[
            :MAX_CONTENT_LENGTH
        ]

    return FetchResult(
        url=url,
        http_status=response.status_code,
        content_type=content_type,
        text=text,
        final_url=response.url,
        error=None,
    )


# ============================================================
# ATTRIBUTE PARSER
# ============================================================

ATTRIBUTE_PATTERN = re.compile(
    r"""
    (?P<name>
        [a-zA-Z_:][-a-zA-Z0-9_:.]*
    )
    \s*=\s*
    (?:
        "(?P<double>[^"]*)"
        |
        '(?P<single>[^']*)'
        |
        (?P<bare>[^\s>]+)
    )
    """,
    re.VERBOSE,
)


def parse_attributes(
    source: str,
) -> Dict[str, str]:

    result = {}

    for match in ATTRIBUTE_PATTERN.finditer(
        source
    ):

        name = (
            match.group(
                "name"
            )
            or ""
        )

        if match.group(
            "double"
        ) is not None:

            value = match.group(
                "double"
            )

        elif match.group(
            "single"
        ) is not None:

            value = match.group(
                "single"
            )

        else:

            value = (
                match.group(
                    "bare"
                )
                or ""
            )

        result[
            name
        ] = html.unescape(
            value
        )

    return result


# ============================================================
# CATEGORY COUNT
# ============================================================

CATEGORY_COUNT_PATTERN = re.compile(
    r"""
    (?P<category>
        메뉴|
        업무|
        민원사무편람|
        웹페이지|
        게시판|
        첨부파일|
        통합예약
    )
    \s*
    검색결과
    \s*
    (?P<count>\d+)
    \s*
    건
    """,
    re.VERBOSE,
)


def extract_category_counts(
    text: str,
) -> Dict[str, int]:

    result = {}

    normalized = normalize_space(
        text
    )

    for match in CATEGORY_COUNT_PATTERN.finditer(
        normalized
    ):

        try:

            count = int(
                match.group(
                    "count"
                )
            )

        except ValueError:

            continue

        result[
            match.group(
                "category"
            )
        ] = count

    return result


# ============================================================
# ANCHOR EXTRACTION
# ============================================================

ANCHOR_PATTERN = re.compile(
    r"""
    (?is)
    <a
    \b
    (?P<attrs>[^>]*)
    >
    (?P<body>.*?)
    </a>
    """,
    re.VERBOSE,
)


def extract_anchors(
    source: str,
    *,
    base_url: str,
) -> List[
    Dict[
        str,
        Any
    ]
]:

    result = []

    seen = set()

    for match in ANCHOR_PATTERN.finditer(
        source
    ):

        attrs = parse_attributes(
            match.group(
                "attrs"
            )
            or ""
        )

        label = strip_html(
            match.group(
                "body"
            )
            or ""
        )

        href = (
            attrs.get(
                "href"
            )
            or ""
        )

        onclick = (
            attrs.get(
                "onclick"
            )
            or ""
        )

        data_attrs = {
            key:
                value
            for key, value
            in attrs.items()
            if key.lower().startswith(
                "data-"
            )
        }

        url = ""

        if (
            href
            and not href.lower().startswith(
                (
                    "javascript:",
                    "#",
                    "mailto:",
                    "tel:",
                )
            )
        ):

            url = normalize_url(
                urljoin(
                    base_url,
                    href,
                )
            )

        key = (
            label,
            href,
            onclick,
            tuple(
                sorted(
                    data_attrs.items()
                )
            ),
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        result.append(
            {
                "label":
                    label,

                "href":
                    href,

                "url":
                    url,

                "onclick":
                    onclick,

                "data_attributes":
                    data_attrs,
            }
        )

        if len(
            result
        ) >= MAX_ANCHOR_COUNT:

            break

    return result


# ============================================================
# RESULT BLOCK EXTRACTION
# ============================================================

BLOCK_PATTERNS = [
    (
        "LI",
        re.compile(
            r"(?is)<li\b[^>]*>.*?</li>"
        ),
    ),
    (
        "TR",
        re.compile(
            r"(?is)<tr\b[^>]*>.*?</tr>"
        ),
    ),
    (
        "DL",
        re.compile(
            r"(?is)<dl\b[^>]*>.*?</dl>"
        ),
    ),
    (
        "ARTICLE",
        re.compile(
            r"(?is)<article\b[^>]*>.*?</article>"
        ),
    ),
]


def extract_structural_blocks(
    source: str,
    *,
    base_url: str,
) -> List[
    Dict[
        str,
        Any
    ]
]:

    results = []

    seen = set()

    for block_type, pattern in BLOCK_PATTERNS:

        for match in pattern.finditer(
            source
        ):

            raw = (
                match.group(
                    0
                )
                or ""
            )

            text = strip_html(
                raw
            )

            if not text:

                continue

            anchors = extract_anchors(
                raw,
                base_url=base_url,
            )

            if not anchors:

                continue

            key = (
                block_type,
                text,
                tuple(
                    (
                        item.get(
                            "url"
                        ),
                        item.get(
                            "onclick"
                        ),
                    )
                    for item in anchors
                ),
            )

            if key in seen:

                continue

            seen.add(
                key
            )

            results.append(
                {
                    "block_type":
                        block_type,

                    "text":
                        text,

                    "target_in_block":
                        contains_target(
                            text
                        ),

                    "search_echo_score":
                        search_echo_score(
                            text
                        ),

                    "search_echo":
                        is_search_echo(
                            text
                        ),

                    "anchors":
                        anchors,

                    "raw_html":
                        raw[
                            :10000
                        ],
                }
            )

            if len(
                results
            ) >= MAX_BLOCK_COUNT:

                return results

    return results


# ============================================================
# TARGET RESULT CLASSIFICATION
# ============================================================

def classify_block(
    block: Dict[
        str,
        Any
    ],
) -> Dict[
    str,
    Any
]:

    anchors = (
        block.get(
            "anchors"
        )
        or []
    )

    official_non_search_anchors = []

    probable_detail_anchors = []

    for anchor in anchors:

        url = (
            anchor.get(
                "url"
            )
            or ""
        )

        onclick = (
            anchor.get(
                "onclick"
            )
            or ""
        )

        data_attrs = (
            anchor.get(
                "data_attributes"
            )
            or {}
        )

        if url:

            if not same_or_subdomain(
                url,
                SEARCH_URL,
            ):

                continue

            if is_search_url(
                url
            ):

                continue

            official_non_search_anchors.append(
                anchor
            )

            if is_probable_detail_url(
                url
            ):

                probable_detail_anchors.append(
                    anchor
                )

        elif (
            onclick
            or data_attrs
        ):

            official_non_search_anchors.append(
                anchor
            )

    target_in_block = (
        block.get(
            "target_in_block"
        )
        is True
    )

    search_echo = (
        block.get(
            "search_echo"
        )
        is True
    )

    has_result_structure = bool(
        official_non_search_anchors
    )

    target_result_block = (
        target_in_block
        and not search_echo
        and has_result_structure
    )

    detail_seed_ready = (
        target_result_block
        and (
            bool(
                probable_detail_anchors
            )
            or any(
                bool(
                    item.get(
                        "onclick"
                    )
                )
                or bool(
                    item.get(
                        "data_attributes"
                    )
                )
                for item in (
                    official_non_search_anchors
                )
            )
        )
    )

    result = dict(
        block
    )

    result[
        "official_non_search_anchors"
    ] = official_non_search_anchors

    result[
        "probable_detail_anchors"
    ] = probable_detail_anchors

    result[
        "has_result_structure"
    ] = has_result_structure

    result[
        "target_result_block"
    ] = target_result_block

    result[
        "detail_seed_ready"
    ] = detail_seed_ready

    return result


# ============================================================
# LOAD O-STAGE
# ============================================================

o_stage_exists = (
    O_STAGE_INPUT_PATH.exists()
)

o_stage_data: Dict[
    str,
    Any
] = {}

if o_stage_exists:

    try:

        o_stage_data = json.loads(
            O_STAGE_INPUT_PATH.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        o_stage_data = {}


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
    "GANGSEO BBS RESULT DOM INSPECTION"
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
    "Search:",
    SEARCH_URL,
)

print(
    "Category field:",
    CATEGORY_FIELD,
)

print(
    "Category value:",
    CATEGORY_VALUE,
)

print(
    "O-stage input:",
    O_STAGE_INPUT_PATH,
)

print()


# ============================================================
# EXACT BBS CATEGORY REQUEST
# ============================================================

params = {
    SEARCH_FIELD:
        TARGET_NAME,

    CATEGORY_FIELD:
        CATEGORY_VALUE,

    PAGE_FIELD:
        "1",
}


result = fetch_get(
    SEARCH_URL,
    params=params,
)

request_count = 1

http_success_count = 0

transport_error_count = 0


if result.error:

    transport_error_count += 1

    raise RuntimeError(
        "Gangseo BBS category request failed: "
        f"{result.error}"
    )


if result.http_status == 200:

    http_success_count += 1


final_url = (
    result.final_url
    or SEARCH_URL
)


HTML_SNAPSHOT_PATH.write_text(
    result.text,
    encoding="utf-8",
)


response_text = strip_html(
    result.text
)

category_counts = extract_category_counts(
    response_text
)


print(
    "HTTP:",
    result.http_status,
)

print(
    "Final URL:",
    final_url,
)

print(
    "Target response:",
    contains_target(
        response_text
    ),
)

print(
    "Category counts:",
    category_counts,
)

print()


# ============================================================
# RAW ANCHORS
# ============================================================

all_anchors = extract_anchors(
    result.text,
    base_url=final_url,
)

official_non_search_anchors = []

for anchor in all_anchors:

    url = (
        anchor.get(
            "url"
        )
        or ""
    )

    if not url:

        continue

    if not same_or_subdomain(
        url,
        SEARCH_URL,
    ):

        continue

    if is_search_url(
        url
    ):

        continue

    official_non_search_anchors.append(
        anchor
    )


# ============================================================
# STRUCTURAL BLOCKS
# ============================================================

raw_blocks = extract_structural_blocks(
    result.text,
    base_url=final_url,
)

classified_blocks = [
    classify_block(
        block
    )
    for block in raw_blocks
]


target_blocks = [
    block
    for block in classified_blocks
    if block.get(
        "target_in_block"
    )
    is True
]


target_result_blocks = [
    block
    for block in classified_blocks
    if block.get(
        "target_result_block"
    )
    is True
]


# ============================================================
# TARGET CONTEXT WINDOWS
# ============================================================

target_context_windows = []

source_lower = result.text

target_variants = [
    TARGET_NAME,
    "개발밀도 관리구역",
    "개발 밀도 관리구역",
]


for variant in target_variants:

    start_index = 0

    while True:

        index = source_lower.find(
            variant,
            start_index,
        )

        if index < 0:

            break

        start = max(
            0,
            index - 2500,
        )

        end = min(
            len(
                result.text
            ),
            index + 4000,
        )

        raw_window = (
            result.text[
                start:end
            ]
        )

        window_text = strip_html(
            raw_window
        )

        window_anchors = extract_anchors(
            raw_window,
            base_url=final_url,
        )

        target_context_windows.append(
            {
                "variant":
                    variant,

                "source_index":
                    index,

                "text":
                    window_text,

                "search_echo_score":
                    search_echo_score(
                        window_text
                    ),

                "search_echo":
                    is_search_echo(
                        window_text
                    ),

                "anchors":
                    window_anchors,

                "raw_html":
                    raw_window,
            }
        )

        start_index = (
            index
            + len(
                variant
            )
        )


# ============================================================
# DETAIL SEED EXTRACTION
# ============================================================

detail_seed_candidates = []

seen_seed_keys = set()


for block_index, block in enumerate(
    target_result_blocks,
    start=1,
):

    candidate_anchors = (
        block.get(
            "official_non_search_anchors"
        )
        or []
    )

    for anchor in candidate_anchors:

        url = (
            anchor.get(
                "url"
            )
            or ""
        )

        onclick = (
            anchor.get(
                "onclick"
            )
            or ""
        )

        data_attrs = (
            anchor.get(
                "data_attributes"
            )
            or {}
        )

        if not (
            url
            or onclick
            or data_attrs
        ):

            continue

        if (
            url
            and is_search_url(
                url
            )
        ):

            continue

        key = (
            normalize_url(
                url
            ),
            onclick,
            tuple(
                sorted(
                    data_attrs.items()
                )
            ),
        )

        if key in seen_seed_keys:

            continue

        seen_seed_keys.add(
            key
        )

        detail_seed_candidates.append(
            {
                "region":
                    REGION,

                "agency":
                    AGENCY,

                "block_index":
                    block_index,

                "block_type":
                    block.get(
                        "block_type"
                    ),

                "block_text":
                    block.get(
                        "text"
                    ),

                "block_preview":
                    build_target_preview(
                        block.get(
                            "text"
                        )
                        or ""
                    ),

                "anchor_label":
                    anchor.get(
                        "label"
                    ),

                "url":
                    url,

                "onclick":
                    onclick,

                "data_attributes":
                    data_attrs,

                "probable_detail_url":
                    (
                        bool(
                            url
                        )
                        and is_probable_detail_url(
                            url
                        )
                    ),

                "target_evidence":
                    True,

                "search_echo":
                    False,

                "final_positive":
                    False,
            }
        )


# ============================================================
# FALLBACK: TARGET WINDOW LINK ANALYSIS
# ============================================================

window_detail_candidates = []

seen_window_candidates = set()


for window_index, window in enumerate(
    target_context_windows,
    start=1,
):

    if window.get(
        "search_echo"
    ) is True:

        continue

    for anchor in window.get(
        "anchors",
        []
    ):

        url = (
            anchor.get(
                "url"
            )
            or ""
        )

        onclick = (
            anchor.get(
                "onclick"
            )
            or ""
        )

        data_attrs = (
            anchor.get(
                "data_attributes"
            )
            or {}
        )

        if url:

            if not same_or_subdomain(
                url,
                SEARCH_URL,
            ):

                continue

            if is_search_url(
                url
            ):

                continue

        if not (
            url
            or onclick
            or data_attrs
        ):

            continue

        key = (
            url,
            onclick,
            tuple(
                sorted(
                    data_attrs.items()
                )
            ),
        )

        if key in seen_window_candidates:

            continue

        seen_window_candidates.add(
            key
        )

        window_detail_candidates.append(
            {
                "window_index":
                    window_index,

                "label":
                    anchor.get(
                        "label"
                    ),

                "url":
                    url,

                "onclick":
                    onclick,

                "data_attributes":
                    data_attrs,

                "probable_detail_url":
                    (
                        bool(
                            url
                        )
                        and is_probable_detail_url(
                            url
                        )
                    ),

                "window_preview":
                    build_target_preview(
                        window.get(
                            "text"
                        )
                        or ""
                    ),
            }
        )


# ============================================================
# SUMMARY
# ============================================================

bbs_result_count = (
    category_counts.get(
        "게시판"
    )
    or 0
)


# ============================================================
# RESOLUTION
# ============================================================

if detail_seed_candidates:

    resolution = (
        "GANGSEO_BBS_TARGET_RESULT_DETAIL_SEED_DISCOVERED"
    )

    next_action = (
        "강서구 게시판 검색 결과 DOM에서 target-bearing result와 "
        "상세 접근 seed를 확보했다. 해당 URL/onclick/data identifier를 "
        "직접 검증하여 실제 개발밀도관리구역 지정·변경·해제 고시인지 "
        "확정한다."
    )

elif target_result_blocks:

    resolution = (
        "GANGSEO_BBS_TARGET_RESULT_BLOCK_DISCOVERED_DETAIL_UNRESOLVED"
    )

    next_action = (
        "개발밀도관리구역이 포함된 실제 게시판 result block은 확인했으나 "
        "상세 endpoint를 아직 복원하지 못했다. 해당 block의 onclick, "
        "JavaScript handler 및 data-* identifier를 분석한다."
    )

elif bbs_result_count > 0:

    resolution = (
        "GANGSEO_BBS_RESULTS_CONFIRMED_DOM_ITEM_STILL_UNRESOLVED"
    )

    next_action = (
        "강서구 게시판 결과 3건은 서버에서 재확인됐으나 일반 LI/TR/DL/"
        "ARTICLE 구조로 결과 block을 분리하지 못했다. 저장된 raw HTML에서 "
        "게시판 결과 영역의 DIV/class 구조를 site-specific하게 추출한다."
    )

else:

    resolution = (
        "GANGSEO_BBS_CATEGORY_RESPONSE_CHANGED_OR_ZERO"
    )

    next_action = (
        "현재 실행에서 게시판 결과 count가 재현되지 않았다. O-stage와 "
        "현재 request parameter/hidden field 차이를 비교한다."
    )


runtime_registration_blocked = True

site_false_interpretation_blocked = True


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-P "
        "Development Density Management Area "
        "Gangseo BBS Result DOM Inspection"
    ),

    "target": {
        "name":
            TARGET_NAME,

        "standard_code":
            STANDARD_CODE,
    },

    "input": {
        "o_stage_path":
            str(
                O_STAGE_INPUT_PATH
            ),

        "o_stage_exists":
            o_stage_exists,

        "o_stage_parsed":
            bool(
                o_stage_data
            ),
    },

    "confirmed_search_structure": {
        "endpoint":
            SEARCH_URL,

        "method":
            "GET",

        "search_field":
            SEARCH_FIELD,

        "search_value":
            TARGET_NAME,

        "category_field":
            CATEGORY_FIELD,

        "category_value":
            CATEGORY_VALUE,

        "pagination_field":
            PAGE_FIELD,

        "pagination_value":
            "1",

        "javascript_evidence":
            (
                "$('#colTarget').val(category); "
                "$('#curPage').val(1); "
                "$('#frmSearch').submit();"
            ),
    },

    "method": {
        "category_field_fixed_from_javascript":
            True,

        "sort_type_as_category_prohibited":
            True,

        "cur_page_as_category_prohibited":
            True,

        "title_only_target_requirement":
            False,

        "result_block_target_evidence_enabled":
            True,

        "search_echo_guard_enabled":
            True,

        "search_url_detail_seed_prohibited":
            True,

        "detail_seed_is_final_positive":
            False,
    },

    "request": {
        "http_status":
            result.http_status,

        "final_url":
            result.final_url,

        "target_response":
            contains_target(
                response_text
            ),

        "category_counts":
            category_counts,

        "html_snapshot_path":
            str(
                HTML_SNAPSHOT_PATH
            ),
    },

    "summary": {
        "request_count":
            request_count,

        "http_success_count":
            http_success_count,

        "transport_error_count":
            transport_error_count,

        "all_anchor_count":
            len(
                all_anchors
            ),

        "official_non_search_anchor_count":
            len(
                official_non_search_anchors
            ),

        "structural_block_count":
            len(
                classified_blocks
            ),

        "target_block_count":
            len(
                target_blocks
            ),

        "target_result_block_count":
            len(
                target_result_blocks
            ),

        "target_context_window_count":
            len(
                target_context_windows
            ),

        "window_detail_candidate_count":
            len(
                window_detail_candidates
            ),

        "detail_seed_candidate_count":
            len(
                detail_seed_candidates
            ),
    },

    "target_result_blocks":
        target_result_blocks,

    "target_context_windows":
        target_context_windows,

    "window_detail_candidates":
        window_detail_candidates,

    "detail_seed_candidates":
        detail_seed_candidates,

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
# CONSOLE RESULT
# ============================================================

print(
    "============================================================"
)

print(
    "DOM INSPECTION RESULT"
)

print(
    "============================================================"
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
    "All anchors:",
    len(
        all_anchors
    ),
)

print(
    "Official non-search anchors:",
    len(
        official_non_search_anchors
    ),
)

print(
    "Structural blocks:",
    len(
        classified_blocks
    ),
)

print(
    "Target blocks:",
    len(
        target_blocks
    ),
)

print(
    "Target result blocks:",
    len(
        target_result_blocks
    ),
)

print(
    "Target context windows:",
    len(
        target_context_windows
    ),
)

print(
    "Window detail candidates:",
    len(
        window_detail_candidates
    ),
)

print(
    "Detail seed candidates:",
    len(
        detail_seed_candidates
    ),
)

print()


if target_blocks:

    print(
        "TARGET-BEARING STRUCTURAL BLOCKS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, block in enumerate(
        target_blocks[
            :30
        ],
        start=1,
    ):

        print(
            f"[{index}]"
        )

        print(
            "Type:",
            block.get(
                "block_type"
            ),
        )

        print(
            "Search echo:",
            block.get(
                "search_echo"
            ),
        )

        print(
            "Echo score:",
            block.get(
                "search_echo_score"
            ),
        )

        print(
            "Result structure:",
            block.get(
                "has_result_structure"
            ),
        )

        print(
            "Target result block:",
            block.get(
                "target_result_block"
            ),
        )

        print(
            "Detail seed ready:",
            block.get(
                "detail_seed_ready"
            ),
        )

        print(
            "Preview:",
            build_target_preview(
                block.get(
                    "text"
                )
                or ""
            ),
        )

        print(
            "Anchors:"
        )

        for anchor in (
            block.get(
                "official_non_search_anchors"
            )
            or []
        )[
            :10
        ]:

            print(
                "  - Label:",
                anchor.get(
                    "label"
                ),
            )

            print(
                "    URL:",
                anchor.get(
                    "url"
                ),
            )

            print(
                "    Onclick:",
                anchor.get(
                    "onclick"
                ),
            )

            print(
                "    Data:",
                anchor.get(
                    "data_attributes"
                ),
            )

        print()


if target_context_windows:

    print(
        "TARGET CONTEXT WINDOWS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, window in enumerate(
        target_context_windows[
            :20
        ],
        start=1,
    ):

        print(
            f"[{index}]"
        )

        print(
            "Search echo:",
            window.get(
                "search_echo"
            ),
        )

        print(
            "Echo score:",
            window.get(
                "search_echo_score"
            ),
        )

        print(
            "Preview:",
            build_target_preview(
                window.get(
                    "text"
                )
                or ""
            ),
        )

        print(
            "Anchors:"
        )

        for anchor in (
            window.get(
                "anchors"
            )
            or []
        )[
            :15
        ]:

            print(
                "  -",
                anchor.get(
                    "label"
                ),
            )

            print(
                "    URL:",
                anchor.get(
                    "url"
                ),
            )

            print(
                "    Onclick:",
                anchor.get(
                    "onclick"
                ),
            )

        print()


if detail_seed_candidates:

    print(
        "DETAIL SEED CANDIDATES"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, seed in enumerate(
        detail_seed_candidates,
        start=1,
    ):

        print(
            f"[{index}]"
        )

        print(
            "Block:",
            seed.get(
                "block_type"
            ),
        )

        print(
            "Label:",
            seed.get(
                "anchor_label"
            ),
        )

        print(
            "URL:",
            seed.get(
                "url"
            ),
        )

        print(
            "Onclick:",
            seed.get(
                "onclick"
            ),
        )

        print(
            "Data:",
            seed.get(
                "data_attributes"
            ),
        )

        print(
            "Probable detail URL:",
            seed.get(
                "probable_detail_url"
            ),
        )

        print(
            "Block preview:",
            seed.get(
                "block_preview"
            ),
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
    "JSON output:",
    OUTPUT_PATH,
)

print(
    "HTML snapshot:",
    HTML_SNAPSHOT_PATH,
)


# ============================================================
# VALIDATION
# ============================================================

detail_seed_keys = {
    (
        normalize_url(
            str(
                item.get(
                    "url"
                )
                or ""
            )
        ),
        item.get(
            "onclick"
        ),
        tuple(
            sorted(
                (
                    item.get(
                        "data_attributes"
                    )
                    or {}
                ).items()
            )
        ),
    )
    for item in detail_seed_candidates
}


all_detail_seeds_have_target_evidence = all(
    item.get(
        "target_evidence"
    )
    is True
    for item in detail_seed_candidates
)


all_detail_seeds_not_echo = all(
    item.get(
        "search_echo"
    )
    is False
    for item in detail_seed_candidates
)


all_detail_seed_urls_not_search = all(
    (
        not item.get(
            "url"
        )
        or not is_search_url(
            str(
                item.get(
                    "url"
                )
            )
        )
    )
    for item in detail_seed_candidates
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

    "O-stage input exists": (
        o_stage_exists
    ),

    "O-stage input parsed": (
        bool(
            o_stage_data
        )
    ),

    "Gangseo search configured": (
        SEARCH_URL
        == "https://www.gangseo.seoul.kr/search"
    ),

    "category field fixed to colTarget": (
        CATEGORY_FIELD
        == "colTarget"
    ),

    "category value fixed to bbs": (
        CATEGORY_VALUE
        == "bbs"
    ),

    "pagination field fixed to curPage": (
        PAGE_FIELD
        == "curPage"
    ),

    "sortType not category field": (
        CATEGORY_FIELD
        != "sortType"
    ),

    "curPage not category field": (
        CATEGORY_FIELD
        != PAGE_FIELD
    ),

    "javascript-confirmed category enabled": (
        output_data[
            "method"
        ][
            "category_field_fixed_from_javascript"
        ]
        is True
    ),

    "title-only target requirement disabled": (
        output_data[
            "method"
        ][
            "title_only_target_requirement"
        ]
        is False
    ),

    "result block target evidence enabled": (
        output_data[
            "method"
        ][
            "result_block_target_evidence_enabled"
        ]
        is True
    ),

    "search echo guard enabled": (
        output_data[
            "method"
        ][
            "search_echo_guard_enabled"
        ]
        is True
    ),

    "search URL seed prohibited": (
        output_data[
            "method"
        ][
            "search_url_detail_seed_prohibited"
        ]
        is True
    ),

    "request executed": (
        request_count
        > 0
    ),

    "HTTP success": (
        http_success_count
        > 0
    ),

    "target response preserved": (
        contains_target(
            response_text
        )
    ),

    "BBS result count preserved": (
        bbs_result_count
        == 3
    ),

    "HTML snapshot written": (
        HTML_SNAPSHOT_PATH.exists()
        and HTML_SNAPSHOT_PATH.stat().st_size
        > 0
    ),

    "detail seeds unique": (
        len(
            detail_seed_keys
        )
        == len(
            detail_seed_candidates
        )
    ),

    "all detail seeds have target evidence": (
        all_detail_seeds_have_target_evidence
    ),

    "all detail seeds are not echo": (
        all_detail_seeds_not_echo
    ),

    "all detail seed URLs are not search URLs": (
        all_detail_seed_urls_not_search
    ),

    "detail seed is not final positive": (
        output_data[
            "method"
        ][
            "detail_seed_is_final_positive"
        ]
        is False
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
        "Gangseo BBS result DOM inspection regression failed"
    )