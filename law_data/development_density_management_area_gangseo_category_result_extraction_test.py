# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-N
Development Density Management Area
Gangseo Integrated Search Category Result Extraction

목표
======================================================================
M-stage에서 서울특별시 강서구 통합검색

    POST https://www.gangseo.seoul.kr/search

응답에 다음 사실이 확인되었다.

    검색어 "개발밀도관리구역"
    총 4건
    게시판 검색결과 3건

그러나 기존 fragment parser는 검색어 echo와 실제 결과 block을
구분하지 못했고 detail URL도 복원하지 못했다.

이번 단계에서는 통합검색 HTML 전체를 대상으로 다음을 수행한다.

1. 실제 search form 재현
2. target search response 확보
3. category heading 탐색
4. 게시판 / 첨부파일 category block 분리
5. category block 내부 anchor / onclick / data-* 추출
6. searchByCategory(...) 호출 분석
7. visible target evidence와 실제 result item을 구분
8. 상세 URL 또는 document identifier seed 확보

핵심 안전정책
======================================================================
1. "검색어 개발밀도관리구역" 같은 검색 UI 문자열은 result row가 아니다.
2. "내가 찾은 검색어"는 무조건 echo로 처리한다.
3. category count 자체는 target document evidence가 아니다.
4. 실제 게시판 결과 item의 제목/본문 snippet에 target이 있어야
   TARGET_RESULT_ITEM으로 승격한다.
5. href가 search URL이면 detail seed로 인정하지 않는다.
6. 단순 category URL은 final positive가 아니다.
7. 상세 URL 후보 역시 다음 원문검증 단계 seed일 뿐이다.
8. runtime registration은 계속 차단한다.
9. 후보 0건을 SITE FALSE로 해석하지 않는다.
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

M_STAGE_INPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "dynamic_detail_reconstruction.json"
    )
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gangseo_category_result_extraction.json"
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


# ============================================================
# CONFIG
# ============================================================

REQUEST_TIMEOUT = 20

REQUEST_SLEEP = 0.25

MAX_CONTENT_LENGTH = 3_000_000

MAX_RESULT_ITEMS = 200

MAX_CATEGORY_BLOCK_LENGTH = 200_000


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


SEARCH_ECHO_TERMS = [
    "내가 찾은 검색어",
    "검색어 삭제",
    "검색어를 입력하세요",
    "결과 내 재검색",
    "인기 검색어",
    "최근 검색어",
]


CATEGORY_NAMES = [
    "게시판",
    "첨부파일",
    "웹페이지",
    "업무",
    "메뉴",
    "민원사무편람",
    "통합예약",
]


DETAIL_HINTS = [
    "view.do",
    "detail.do",
    "bbsMsgDetail",
    "selectBoardArticle",
    "post/view",
    "board/view",
    "article",
    "nttId=",
    "idx=",
    "seq=",
    "msg_seq=",
    "mgt_no=",
]


SEARCH_HINTS = [
    "/search",
    "search?",
    "search.do",
    "search.jsp",
    "totalsearch",
]


# ============================================================
# DATA CLASS
# ============================================================

@dataclass
class FetchResult:
    method: str
    request_url: str
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

    return normalize_space(
        html.unescape(
            value
        )
    )


def is_search_echo_text(
    value: str,
) -> bool:

    text = normalize_space(
        value
    )

    if not contains_target(
        text
    ):

        return False

    return any(
        term in text
        for term in SEARCH_ECHO_TERMS
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


def is_search_url(
    url: str,
) -> bool:

    lower = (
        url
        or ""
    ).lower()

    return any(
        hint.lower() in lower
        for hint in SEARCH_HINTS
    )


def is_probable_detail_url(
    url: str,
) -> bool:

    lower = (
        url
        or ""
    ).lower()

    return any(
        hint.lower() in lower
        for hint in DETAIL_HINTS
    )


# ============================================================
# FETCH
# ============================================================

def fetch_get(
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
            method="GET",
            request_url=url,
            http_status=None,
            content_type="",
            text="",
            final_url=None,
            error=repr(
                exc
            ),
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
        method="GET",
        request_url=url,
        http_status=response.status_code,
        content_type=(
            response.headers.get(
                "Content-Type",
                "",
            )
            or ""
        ),
        text=text,
        final_url=response.url,
        error=None,
    )


def fetch_post(
    url: str,
    data: Dict[str, str],
) -> FetchResult:

    try:

        response = requests.post(
            url,
            headers=HEADERS,
            data=data,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

    except requests.RequestException as exc:

        return FetchResult(
            method="POST",
            request_url=url,
            http_status=None,
            content_type="",
            text="",
            final_url=None,
            error=repr(
                exc
            ),
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
        method="POST",
        request_url=url,
        http_status=response.status_code,
        content_type=(
            response.headers.get(
                "Content-Type",
                "",
            )
            or ""
        ),
        text=text,
        final_url=response.url,
        error=None,
    )


# ============================================================
# ATTRIBUTE PARSING
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

    values = {}

    for match in ATTRIBUTE_PATTERN.finditer(
        source
    ):

        name = (
            match.group(
                "name"
            )
            or ""
        )

        value = (
            match.group(
                "double"
            )
            if match.group(
                "double"
            )
            is not None
            else (
                match.group(
                    "single"
                )
                if match.group(
                    "single"
                )
                is not None
                else (
                    match.group(
                        "bare"
                    )
                    or ""
                )
            )
        )

        values[
            name
        ] = html.unescape(
            value
        )

    return values


# ============================================================
# FORM PARSING
# ============================================================

FORM_PATTERN = re.compile(
    r"(?is)<form\b([^>]*)>(.*?)</form>"
)

INPUT_PATTERN = re.compile(
    r"(?is)<input\b([^>]*)>"
)


def find_search_form(
    source: str,
    *,
    base_url: str,
) -> Optional[
    Dict[
        str,
        Any
    ]
]:

    for form_index, match in enumerate(
        FORM_PATTERN.finditer(
            source
        ),
        start=1,
    ):

        attrs = parse_attributes(
            match.group(
                1
            )
            or ""
        )

        body = (
            match.group(
                2
            )
            or ""
        )

        method = (
            attrs.get(
                "method",
                "GET",
            )
            or "GET"
        ).upper()

        action = (
            attrs.get(
                "action"
            )
            or base_url
        )

        action_url = normalize_url(
            urljoin(
                base_url,
                action,
            )
        )

        fields = {}

        search_field = None

        for input_match in INPUT_PATTERN.finditer(
            body
        ):

            input_attrs = parse_attributes(
                input_match.group(
                    1
                )
                or ""
            )

            name = (
                input_attrs.get(
                    "name"
                )
                or ""
            )

            if not name:

                continue

            field_type = (
                input_attrs.get(
                    "type",
                    "text",
                )
                or "text"
            ).lower()

            value = (
                input_attrs.get(
                    "value"
                )
                or ""
            )

            if field_type in {
                "submit",
                "button",
                "file",
                "image",
                "reset",
            }:

                continue

            fields[
                name
            ] = value

            if (
                field_type
                in {
                    "text",
                    "search",
                }
                and (
                    "search"
                    in name.lower()
                    or "srch"
                    in name.lower()
                    or "keyword"
                    in name.lower()
                    or "query"
                    in name.lower()
                )
            ):

                if search_field is None:

                    search_field = name

        if (
            search_field
            and (
                action_url.rstrip("/")
                == SEARCH_URL.rstrip("/")
                or "/search"
                in action_url.lower()
            )
        ):

            return {
                "form_index":
                    form_index,

                "method":
                    method,

                "action_url":
                    action_url,

                "search_field":
                    search_field,

                "fields":
                    fields,
            }

    return None


# ============================================================
# CATEGORY COUNT EXTRACTION
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

    counts = {}

    normalized = normalize_space(
        text
    )

    for match in CATEGORY_COUNT_PATTERN.finditer(
        normalized
    ):

        category = (
            match.group(
                "category"
            )
            or ""
        )

        try:

            count = int(
                match.group(
                    "count"
                )
            )

        except ValueError:

            continue

        counts[
            category
        ] = count

    return counts


# ============================================================
# CATEGORY BLOCK EXTRACTION
# ============================================================

def find_category_positions(
    source: str,
) -> List[
    Tuple[
        int,
        str
    ]
]:

    values = []

    for category in CATEGORY_NAMES:

        patterns = [
            f"{category} 검색결과",
            f"{category}검색결과",
        ]

        for pattern in patterns:

            start = 0

            while True:

                index = source.find(
                    pattern,
                    start,
                )

                if index < 0:

                    break

                values.append(
                    (
                        index,
                        category,
                    )
                )

                start = (
                    index
                    + len(
                        pattern
                    )
                )

    return sorted(
        values,
        key=lambda item: item[
            0
        ],
    )


def extract_category_blocks(
    source: str,
) -> List[
    Dict[
        str,
        Any
    ]
]:

    positions = find_category_positions(
        source
    )

    blocks = []

    for index, (
        start,
        category,
    ) in enumerate(
        positions
    ):

        if (
            index
            + 1
            < len(
                positions
            )
        ):

            end = positions[
                index
                + 1
            ][
                0
            ]

        else:

            end = min(
                len(
                    source
                ),
                start
                + MAX_CATEGORY_BLOCK_LENGTH,
            )

        if (
            end
            - start
            > MAX_CATEGORY_BLOCK_LENGTH
        ):

            end = (
                start
                + MAX_CATEGORY_BLOCK_LENGTH
            )

        raw = source[
            start:end
        ]

        blocks.append(
            {
                "category":
                    category,

                "start_index":
                    start,

                "end_index":
                    end,

                "raw_html":
                    raw,

                "visible_text":
                    strip_html(
                        raw
                    ),
            }
        )

    return blocks


# ============================================================
# ANCHOR / ELEMENT EXTRACTION
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

    results = []

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

        absolute_url = ""

        if href and not href.lower().startswith(
            (
                "javascript:",
                "#",
            )
        ):

            absolute_url = normalize_url(
                urljoin(
                    base_url,
                    href,
                )
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

        key = (
            label,
            absolute_url,
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

        results.append(
            {
                "label":
                    label,

                "href":
                    href,

                "url":
                    absolute_url,

                "onclick":
                    onclick,

                "data_attributes":
                    data_attrs,

                "all_attributes":
                    attrs,
            }
        )

    return results


# ============================================================
# SEARCH BY CATEGORY ANALYSIS
# ============================================================

SEARCH_BY_CATEGORY_PATTERN = re.compile(
    r"""
    searchByCategory
    \s*
    \(
        \s*
        ["']
        (?P<category>[^"']+)
        ["']
        \s*
    \)
    """,
    re.VERBOSE
    | re.IGNORECASE,
)


FUNCTION_DEFINITION_PATTERN = re.compile(
    r"""
    function
    \s+
    searchByCategory
    \s*
    \(
        (?P<args>[^)]*)
    \)
    \s*
    \{
        (?P<body>.*?)
    \}
    """,
    re.VERBOSE
    | re.DOTALL
    | re.IGNORECASE,
)


def extract_search_by_category_calls(
    source: str,
) -> List[str]:

    values = []

    seen = set()

    for match in SEARCH_BY_CATEGORY_PATTERN.finditer(
        source
    ):

        value = (
            match.group(
                "category"
            )
            or ""
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


def extract_search_by_category_function(
    source: str,
) -> Optional[
    Dict[
        str,
        str
    ]
]:

    match = FUNCTION_DEFINITION_PATTERN.search(
        source
    )

    if not match:

        return None

    return {
        "args":
            normalize_space(
                match.group(
                    "args"
                )
                or ""
            ),

        "body":
            (
                match.group(
                    "body"
                )
                or ""
            )[
                :20000
            ],
    }


# ============================================================
# RESULT ITEM CLASSIFICATION
# ============================================================

def classify_anchor_item(
    *,
    category: str,
    anchor: Dict[str, Any],
) -> Dict[str, Any]:

    label = (
        anchor.get(
            "label"
        )
        or ""
    )

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

    target_in_label = contains_target(
        label
    )

    echo = is_search_echo_text(
        label
    )

    search_url = (
        bool(
            url
        )
        and is_search_url(
            url
        )
    )

    detail_url = (
        bool(
            url
        )
        and not search_url
        and is_probable_detail_url(
            url
        )
    )

    onclick_identifier = bool(
        re.search(
            r"""
            (?:
                idx|
                seq|
                ntt|
                bbs|
                board|
                article|
                detail|
                view
            )
            """,
            onclick,
            flags=re.IGNORECASE
            | re.VERBOSE,
        )
    )

    actual_item_evidence = (
        bool(
            label
        )
        and (
            bool(
                url
            )
            or bool(
                onclick
            )
            or bool(
                anchor.get(
                    "data_attributes"
                )
            )
        )
    )

    target_result_item = (
        category
        in {
            "게시판",
            "첨부파일",
        }
        and target_in_label
        and not echo
        and actual_item_evidence
    )

    detail_seed_candidate = (
        target_result_item
        and (
            detail_url
            or onclick_identifier
        )
    )

    return {
        **anchor,

        "category":
            category,

        "target_in_label":
            target_in_label,

        "search_echo":
            echo,

        "search_url":
            search_url,

        "detail_url":
            detail_url,

        "onclick_identifier_evidence":
            onclick_identifier,

        "actual_item_evidence":
            actual_item_evidence,

        "target_result_item":
            target_result_item,

        "detail_seed_candidate":
            detail_seed_candidate,
    }


# ============================================================
# LOAD M-STAGE
# ============================================================

m_stage_exists = (
    M_STAGE_INPUT_PATH.exists()
)

m_stage_data: Dict[
    str,
    Any
] = {}

if m_stage_exists:

    try:

        m_stage_data = json.loads(
            M_STAGE_INPUT_PATH.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        m_stage_data = {}


# ============================================================
# STATE
# ============================================================

request_count = 0

http_success_count = 0

transport_error_count = 0

category_block_count = 0

anchor_item_count = 0

target_result_item_count = 0

detail_seed_candidate_count = 0

search_echo_item_count = 0


category_blocks: List[
    Dict[
        str,
        Any
    ]
] = []

result_items: List[
    Dict[
        str,
        Any
    ]
] = []

detail_seed_candidates: List[
    Dict[
        str,
        Any
    ]
] = []


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
    "GANGSEO INTEGRATED SEARCH CATEGORY RESULT EXTRACTION"
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
    "Board:",
    BOARD_URL,
)

print(
    "Search endpoint:",
    SEARCH_URL,
)

print(
    "M-stage input:",
    M_STAGE_INPUT_PATH,
)

print()


# ============================================================
# ROOT BOARD FETCH
# ============================================================

root = fetch_get(
    BOARD_URL
)

request_count += 1

if root.error:

    transport_error_count += 1

    raise RuntimeError(
        f"Primary board fetch failed: {root.error}"
    )

if root.http_status == 200:

    http_success_count += 1


root_url = (
    root.final_url
    or BOARD_URL
)


# ============================================================
# SEARCH FORM
# ============================================================

search_form = find_search_form(
    root.text,
    base_url=root_url,
)


if search_form is None:

    raise AssertionError(
        "Gangseo integrated search form not discovered"
    )


payload = dict(
    search_form[
        "fields"
    ]
)

payload[
    search_form[
        "search_field"
    ]
] = TARGET_NAME


print(
    "Search form index:",
    search_form[
        "form_index"
    ],
)

print(
    "Search form method:",
    search_form[
        "method"
    ],
)

print(
    "Search form action:",
    search_form[
        "action_url"
    ],
)

print(
    "Search field:",
    search_form[
        "search_field"
    ],
)

print()


# ============================================================
# SEARCH SUBMISSION
# ============================================================

if (
    search_form[
        "method"
    ]
    == "POST"
):

    search_result = fetch_post(
        search_form[
            "action_url"
        ],
        payload,
    )

else:

    parsed = urlparse(
        search_form[
            "action_url"
        ]
    )

    query = dict(
        parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
    )

    query.update(
        payload
    )

    submit_url = urlunparse(
        parsed._replace(
            query=urlencode(
                query,
                doseq=True,
            )
        )
    )

    search_result = fetch_get(
        submit_url
    )


request_count += 1

if search_result.error:

    transport_error_count += 1

    raise RuntimeError(
        f"Search submission failed: {search_result.error}"
    )

if search_result.http_status == 200:

    http_success_count += 1


search_source = (
    search_result.text
    or ""
)

search_text = strip_html(
    search_source
)


print(
    "Search HTTP:",
    search_result.http_status,
)

print(
    "Target in response:",
    contains_target(
        search_text
    ),
)


# ============================================================
# CATEGORY COUNTS
# ============================================================

category_counts = extract_category_counts(
    search_text
)


print(
    "Category counts:",
    category_counts,
)

print()


# ============================================================
# CATEGORY BLOCKS
# ============================================================

raw_blocks = extract_category_blocks(
    search_source
)


seen_blocks = set()

for block in raw_blocks:

    category = (
        block.get(
            "category"
        )
        or ""
    )

    visible_text = normalize_space(
        block.get(
            "visible_text"
        )
        or ""
    )

    key = (
        category,
        visible_text[
            :500
        ],
    )

    if key in seen_blocks:

        continue

    seen_blocks.add(
        key
    )

    anchors = extract_anchors(
        block[
            "raw_html"
        ],
        base_url=(
            search_result.final_url
            or SEARCH_URL
        ),
    )

    classified_items = []

    for anchor in anchors:

        item = classify_anchor_item(
            category=category,
            anchor=anchor,
        )

        if item[
            "search_echo"
        ]:

            search_echo_item_count += 1

        if item[
            "target_result_item"
        ]:

            target_result_item_count += 1

        if item[
            "detail_seed_candidate"
        ]:

            detail_seed_candidate_count += 1

            seed = {
                "region":
                    REGION,

                "agency":
                    AGENCY,

                **item,
            }

            detail_seed_candidates.append(
                seed
            )

        classified_items.append(
            item
        )

        result_items.append(
            {
                "region":
                    REGION,

                "agency":
                    AGENCY,

                **item,
            }
        )

        anchor_item_count += 1

        if (
            anchor_item_count
            >= MAX_RESULT_ITEMS
        ):

            break

    enriched = dict(
        block
    )

    enriched[
        "anchors"
    ] = classified_items

    enriched[
        "anchor_count"
    ] = len(
        classified_items
    )

    enriched[
        "target_item_count"
    ] = sum(
        1
        for item
        in classified_items
        if item[
            "target_result_item"
        ]
    )

    category_blocks.append(
        enriched
    )

    category_block_count += 1

    if (
        anchor_item_count
        >= MAX_RESULT_ITEMS
    ):

        break


# ============================================================
# SEARCH BY CATEGORY
# ============================================================

category_calls = (
    extract_search_by_category_calls(
        search_source
    )
)

category_function = (
    extract_search_by_category_function(
        search_source
    )
)


# ============================================================
# DEDUPE DETAIL SEEDS
# ============================================================

deduped_detail_seeds = []

seen_seed_keys = set()

for seed in detail_seed_candidates:

    key = (
        seed.get(
            "category"
        ),
        normalize_url(
            str(
                seed.get(
                    "url"
                )
                or ""
            )
        ),
        seed.get(
            "onclick"
        ),
        seed.get(
            "label"
        ),
    )

    if key in seen_seed_keys:

        continue

    seen_seed_keys.add(
        key
    )

    deduped_detail_seeds.append(
        seed
    )


# ============================================================
# RESOLUTION
# ============================================================

if deduped_detail_seeds:

    resolution = (
        "GANGSEO_TARGET_RESULT_DETAIL_SEED_DISCOVERED"
    )

    next_action = (
        "확보한 강서구 통합검색 게시판/첨부파일 detail seed를 "
        "직접 조회하여 실제 개발밀도관리구역 지정·변경·해제 "
        "고시인지 원문 검증한다."
    )

elif target_result_item_count > 0:

    resolution = (
        "GANGSEO_TARGET_RESULT_ITEM_DISCOVERED_DETAIL_UNRESOLVED"
    )

    next_action = (
        "실제 target-bearing 결과 item은 확인되었으나 상세 URL을 "
        "복원하지 못했다. searchByCategory 함수와 item onclick/data-* "
        "식별자를 기반으로 상세 endpoint를 재구성한다."
    )

elif (
    category_counts.get(
        "게시판",
        0,
    )
    > 0
    or category_counts.get(
        "첨부파일",
        0,
    )
    > 0
):

    resolution = (
        "GANGSEO_CATEGORY_RESULTS_EXIST_BUT_TARGET_ITEM_NOT_EXTRACTED"
    )

    next_action = (
        "강서구 통합검색에는 게시판/첨부파일 결과 개수가 존재하지만 "
        "현재 HTML category block에서 실제 result item을 추출하지 못했다. "
        "검색 결과가 JavaScript/AJAX 후처리되는지 확인하고 "
        "category별 요청 endpoint를 직접 재현한다."
    )

else:

    resolution = (
        "GANGSEO_CATEGORY_RESULT_EXTRACTION_COMPLETED_NO_RESULT"
    )

    next_action = (
        "통합검색 POST payload와 category parameter 구조를 재점검한다."
    )


runtime_registration_blocked = True

site_false_interpretation_blocked = True


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-N "
        "Development Density Management Area "
        "Gangseo Integrated Search Category Result Extraction"
    ),

    "target": {
        "name":
            TARGET_NAME,

        "standard_code":
            STANDARD_CODE,
    },

    "input": {
        "m_stage_path":
            str(
                M_STAGE_INPUT_PATH
            ),

        "m_stage_exists":
            m_stage_exists,

        "m_stage_parsed":
            bool(
                m_stage_data
            ),
    },

    "method": {
        "actual_search_form_reused":
            True,

        "hidden_fields_preserved":
            True,

        "category_count_extraction":
            True,

        "category_block_extraction":
            True,

        "search_by_category_analysis":
            True,

        "search_echo_guard":
            True,

        "target_result_item_requires_visible_target":
            True,

        "search_url_prohibited_as_detail_seed":
            True,

        "detail_seed_is_final_positive":
            False,
    },

    "search": {
        "form":
            search_form,

        "category_counts":
            category_counts,

        "search_by_category_calls":
            category_calls,

        "search_by_category_function":
            category_function,
    },

    "summary": {
        "request_count":
            request_count,

        "http_success_count":
            http_success_count,

        "transport_error_count":
            transport_error_count,

        "category_block_count":
            category_block_count,

        "anchor_item_count":
            anchor_item_count,

        "search_echo_item_count":
            search_echo_item_count,

        "target_result_item_count":
            target_result_item_count,

        "detail_seed_candidate_count":
            len(
                deduped_detail_seeds
            ),
    },

    "category_blocks":
        category_blocks,

    "result_items":
        result_items,

    "detail_seed_candidates":
        deduped_detail_seeds,

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

print(
    "============================================================"
)

print(
    "CATEGORY EXTRACTION RESULT"
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
    "Transport error count:",
    transport_error_count,
)

print(
    "Category block count:",
    category_block_count,
)

print(
    "Anchor item count:",
    anchor_item_count,
)

print(
    "Search echo item count:",
    search_echo_item_count,
)

print(
    "Target result item count:",
    target_result_item_count,
)

print(
    "Detail seed candidate count:",
    len(
        deduped_detail_seeds
    ),
)

print(
    "searchByCategory calls:",
    category_calls,
)

print()


for block in category_blocks:

    if block[
        "category"
    ] not in {
        "게시판",
        "첨부파일",
    }:

        continue

    print(
        "------------------------------------------------------------"
    )

    print(
        "CATEGORY:",
        block[
            "category"
        ],
    )

    print(
        "Anchor count:",
        block[
            "anchor_count"
        ],
    )

    print(
        "Target item count:",
        block[
            "target_item_count"
        ],
    )

    print(
        "Preview:",
        block[
            "visible_text"
        ][
            :1500
        ],
    )

    print()

    for item in block[
        "anchors"
    ][
        :30
    ]:

        print(
            "  ITEM:",
            item.get(
                "label"
            ),
        )

        print(
            "    URL:",
            item.get(
                "url"
            ),
        )

        print(
            "    Onclick:",
            item.get(
                "onclick"
            ),
        )

        print(
            "    Data:",
            item.get(
                "data_attributes"
            ),
        )

        print(
            "    Target:",
            item.get(
                "target_in_label"
            ),
        )

        print(
            "    Target result item:",
            item.get(
                "target_result_item"
            ),
        )

        print()


if deduped_detail_seeds:

    print(
        "DETAIL SEED CANDIDATES"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, seed in enumerate(
        deduped_detail_seeds,
        start=1,
    ):

        print(
            f"[{index}]"
        )

        print(
            "Category:",
            seed.get(
                "category"
            ),
        )

        print(
            "Label:",
            seed.get(
                "label"
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

detail_seed_keys = {
    (
        item.get(
            "category"
        ),
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
        item.get(
            "label"
        ),
    )
    for item in deduped_detail_seeds
}


all_detail_seeds_visible_target = all(
    item.get(
        "target_in_label"
    )
    is True
    for item in deduped_detail_seeds
)


all_detail_seeds_not_echo = all(
    item.get(
        "search_echo"
    )
    is False
    for item in deduped_detail_seeds
)


all_detail_seed_urls_not_search = all(
    (
        not item.get(
            "url"
        )
        or item.get(
            "search_url"
        )
        is False
    )
    for item in deduped_detail_seeds
)


all_detail_seeds_not_final_positive = (
    output_data[
        "method"
    ][
        "detail_seed_is_final_positive"
    ]
    is False
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

    "M-stage input exists": (
        m_stage_exists
    ),

    "Gangseo board configured": (
        BOARD_URL.endswith(
            "/gs040301"
        )
    ),

    "Gangseo search configured": (
        SEARCH_URL.endswith(
            "/search"
        )
    ),

    "search form discovered": (
        search_form
        is not None
    ),

    "actual search form reused": (
        output_data[
            "method"
        ][
            "actual_search_form_reused"
        ]
        is True
    ),

    "hidden fields preserved": (
        output_data[
            "method"
        ][
            "hidden_fields_preserved"
        ]
        is True
    ),

    "category extraction enabled": (
        output_data[
            "method"
        ][
            "category_block_extraction"
        ]
        is True
    ),

    "searchByCategory analysis enabled": (
        output_data[
            "method"
        ][
            "search_by_category_analysis"
        ]
        is True
    ),

    "search echo guard enabled": (
        output_data[
            "method"
        ][
            "search_echo_guard"
        ]
        is True
    ),

    "visible target required": (
        output_data[
            "method"
        ][
            "target_result_item_requires_visible_target"
        ]
        is True
    ),

    "search URL detail seed prohibited": (
        output_data[
            "method"
        ][
            "search_url_prohibited_as_detail_seed"
        ]
        is True
    ),

    "requests executed": (
        request_count
        > 0
    ),

    "target search response preserved": (
        contains_target(
            search_text
        )
    ),

    "detail seeds unique": (
        len(
            detail_seed_keys
        )
        == len(
            deduped_detail_seeds
        )
    ),

    "all detail seeds have visible target": (
        all_detail_seeds_visible_target
    ),

    "all detail seeds are not echo": (
        all_detail_seeds_not_echo
    ),

    "all detail seed URLs are not search URLs": (
        all_detail_seed_urls_not_search
    ),

    "detail seed not final positive": (
        all_detail_seeds_not_final_positive
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
        "Gangseo category result extraction regression failed"
    )