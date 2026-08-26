# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-O
Development Density Management Area
Gangseo searchByCategory Request Reconstruction

목표
======================================================================
N-stage에서 서울특별시 강서구 통합검색

    POST https://www.gangseo.seoul.kr/search

응답에 다음 사실이 확인되었다.

    게시판 검색결과 3건
    첨부파일 검색결과 0건

또한 다음 JavaScript 호출이 확인되었다.

    searchByCategory('TOTAL')
    searchByCategory('menu')
    searchByCategory('employee')
    searchByCategory('cvlcpt')
    searchByCategory('webpage')
    searchByCategory('bbs')
    searchByCategory('attach')
    searchByCategory('reserve')

그러나 초기 HTML에는 실제 게시판 result block이 존재하지 않았다.

이번 단계에서는 searchByCategory 함수 또는 관련 form 구조를 분석하여

    category = bbs

요청을 실제 사이트 구조로 재구성한다.

핵심 원칙
======================================================================
1. 임의의 category parameter 이름을 추측해서 주입하지 않는다.
2. 실제 form field / JavaScript assignment / function body 증거가 있어야 한다.
3. inline script와 동일 공식 도메인의 external JS를 분석한다.
4. 발견된 category field에만 "bbs"를 적용한다.
5. 검색어 field에는 TARGET_NAME만 적용한다.
6. 재구성된 category response 자체는 final positive가 아니다.
7. 실제 게시판 result item에서 visible target evidence가 있어야
   다음 detail seed로 승격할 수 있다.
8. 검색어 echo는 result item으로 인정하지 않는다.
9. runtime registration은 계속 차단한다.
10. 결과 0건도 SITE FALSE로 해석하지 않는다.
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

N_STAGE_INPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gangseo_category_result_extraction.json"
    )
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gangseo_category_request_reconstruction.json"
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

TARGET_CATEGORY = "bbs"


# ============================================================
# REQUEST CONFIG
# ============================================================

REQUEST_TIMEOUT = 20

REQUEST_SLEEP = 0.25

MAX_CONTENT_LENGTH = (
    3_000_000
)

MAX_EXTERNAL_JS_FILES = 30

MAX_EXTERNAL_JS_LENGTH = (
    2_000_000
)

MAX_CANDIDATE_SUBMISSIONS = 20

MAX_RESULT_ITEMS = 300


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
# SAFETY / SEARCH DEFINITIONS
# ============================================================

SEARCH_ECHO_TERMS = [
    "내가 찾은 검색어",
    "검색어 삭제",
    "검색어를 입력하세요",
    "결과 내 재검색",
    "인기 검색어",
    "최근 검색어",
]


SEARCH_FIELD_HINTS = [
    "searchtext",
    "search_text",
    "searchword",
    "search_word",
    "searchkeyword",
    "search_keyword",
    "keyword",
    "query",
    "srchtext",
    "srchword",
]


CATEGORY_FIELD_HINTS = [
    "category",
    "cate",
    "searchcategory",
    "search_category",
    "searchtype",
    "search_type",
    "type",
    "collection",
    "section",
    "tab",
]


DETAIL_URL_HINTS = [
    "view.do",
    "detail.do",
    "bbsmsgdetail",
    "selectboardarticle",
    "post/view",
    "board/view",
    "article",
    "nttid=",
    "idx=",
    "seq=",
    "msg_seq=",
    "mgt_no=",
]


SEARCH_URL_HINTS = [
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

    return any(
        hint in lower
        for hint in SEARCH_URL_HINTS
    )


def is_probable_detail_url(
    url: str,
) -> bool:

    lower = (
        url
        or ""
    ).lower()

    return any(
        hint in lower
        for hint in DETAIL_URL_HINTS
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
        method="GET",
        request_url=url,
        http_status=response.status_code,
        content_type=content_type,
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
        method="POST",
        request_url=url,
        http_status=response.status_code,
        content_type=content_type,
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

SELECT_PATTERN = re.compile(
    r"(?is)<select\b([^>]*)>(.*?)</select>"
)

OPTION_PATTERN = re.compile(
    r"(?is)<option\b([^>]*)>(.*?)</option>"
)


def parse_forms(
    source: str,
    *,
    base_url: str,
) -> List[
    Dict[
        str,
        Any
    ]
]:

    forms = []

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

        field_types = {}

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

            if field_type in {
                "submit",
                "button",
                "file",
                "image",
                "reset",
            }:

                continue

            value = (
                input_attrs.get(
                    "value"
                )
                or ""
            )

            fields[
                name
            ] = value

            field_types[
                name
            ] = field_type

        select_records = []

        for select_match in SELECT_PATTERN.finditer(
            body
        ):

            select_attrs = parse_attributes(
                select_match.group(
                    1
                )
                or ""
            )

            name = (
                select_attrs.get(
                    "name"
                )
                or ""
            )

            if not name:

                continue

            options = []

            selected_value = ""

            for option_match in OPTION_PATTERN.finditer(
                select_match.group(
                    2
                )
                or ""
            ):

                option_attrs = parse_attributes(
                    option_match.group(
                        1
                    )
                    or ""
                )

                label = strip_html(
                    option_match.group(
                        2
                    )
                    or ""
                )

                value = (
                    option_attrs.get(
                        "value"
                    )
                    or label
                )

                options.append(
                    {
                        "value":
                            value,

                        "label":
                            label,

                        "selected":
                            (
                                "selected"
                                in {
                                    key.lower()
                                    for key
                                    in option_attrs
                                }
                            ),
                    }
                )

                if (
                    not selected_value
                    or options[
                        -1
                    ][
                        "selected"
                    ]
                ):

                    selected_value = value

            fields[
                name
            ] = selected_value

            field_types[
                name
            ] = "select"

            select_records.append(
                {
                    "name":
                        name,

                    "options":
                        options,
                }
            )

        forms.append(
            {
                "form_index":
                    form_index,

                "id":
                    attrs.get(
                        "id",
                        "",
                    ),

                "name":
                    attrs.get(
                        "name",
                        "",
                    ),

                "method":
                    method,

                "action_url":
                    action_url,

                "fields":
                    fields,

                "field_types":
                    field_types,

                "selects":
                    select_records,

                "raw_start_tag":
                    match.group(
                        1
                    )
                    or "",

                "raw_body":
                    body,
            }
        )

    return forms


def field_name_matches_search(
    name: str,
) -> bool:

    lower = (
        name
        or ""
    ).lower()

    return any(
        hint == lower
        or hint in lower
        for hint in SEARCH_FIELD_HINTS
    )


def field_name_matches_category(
    name: str,
) -> bool:

    lower = (
        name
        or ""
    ).lower()

    return any(
        hint == lower
        or hint in lower
        for hint in CATEGORY_FIELD_HINTS
    )


# ============================================================
# SCRIPT EXTRACTION
# ============================================================

SCRIPT_PATTERN = re.compile(
    r"""
    (?is)
    <script
    \b
    (?P<attrs>[^>]*)
    >
    (?P<body>.*?)
    </script>
    """,
    re.VERBOSE,
)


def extract_scripts(
    source: str,
    *,
    base_url: str,
) -> Dict[str, Any]:

    inline_scripts = []

    external_scripts = []

    seen_external = set()

    for match in SCRIPT_PATTERN.finditer(
        source
    ):

        attrs = parse_attributes(
            match.group(
                "attrs"
            )
            or ""
        )

        body = (
            match.group(
                "body"
            )
            or ""
        )

        src = (
            attrs.get(
                "src"
            )
            or ""
        )

        if src:

            absolute = normalize_url(
                urljoin(
                    base_url,
                    src,
                )
            )

            if (
                absolute
                and absolute not in seen_external
                and same_or_subdomain(
                    absolute,
                    SEARCH_URL,
                )
            ):

                seen_external.add(
                    absolute
                )

                external_scripts.append(
                    absolute
                )

            continue

        if body.strip():

            inline_scripts.append(
                body
            )

    return {
        "inline_scripts":
            inline_scripts,

        "external_scripts":
            external_scripts[
                :MAX_EXTERNAL_JS_FILES
            ],
    }


# ============================================================
# JAVASCRIPT EVIDENCE
# ============================================================

SEARCH_BY_CATEGORY_FUNCTION_PATTERN = re.compile(
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
        (?P<body>
            .*?
        )
    \}
    """,
    re.VERBOSE
    | re.DOTALL
    | re.IGNORECASE,
)


SEARCH_BY_CATEGORY_ASSIGN_PATTERN = re.compile(
    r"""
    (?:
        document
        \.
        (?P<form1>[A-Za-z_$][A-Za-z0-9_$]*)
        \.
        (?P<field1>[A-Za-z_$][A-Za-z0-9_$]*)
        \.
        value

        |

        document
        \.
        getElementById
        \(
            ["']
            (?P<id1>[^"']+)
            ["']
        \)
        \.
        value

        |

        \$\(
            ["']
            \#
            (?P<id2>[^"']+)
            ["']
        \)
        \.
        val
        \(
    )
    """,
    re.VERBOSE
    | re.IGNORECASE,
)


GENERIC_VALUE_ASSIGN_PATTERN = re.compile(
    r"""
    (?P<lhs>
        [A-Za-z_$][A-Za-z0-9_.$\[\]"']*
    )
    \s*
    =
    \s*
    (?P<rhs>
        [A-Za-z_$][A-Za-z0-9_$]*
    )
    """,
    re.VERBOSE,
)


FORM_SUBMIT_PATTERN = re.compile(
    r"""
    (?:
        \.
        submit
        \s*
        \(
        \s*
        \)

        |

        submit
        \s*
        \(
    )
    """,
    re.VERBOSE
    | re.IGNORECASE,
)


AJAX_URL_PATTERN = re.compile(
    r"""
    (?:
        url
        \s*:
        \s*

        |

        fetch
        \s*
        \(

        |

        \.
        ajax
        \s*
        \(
    )
    [^"'`]*
    ["'`]
    (?P<url>
        /[^"'`]+
    )
    ["'`]
    """,
    re.VERBOSE
    | re.IGNORECASE,
)


def extract_function_evidence(
    script_text: str,
    *,
    source_name: str,
) -> List[
    Dict[
        str,
        Any
    ]
]:

    records = []

    for match in SEARCH_BY_CATEGORY_FUNCTION_PATTERN.finditer(
        script_text
    ):

        args_text = normalize_space(
            match.group(
                "args"
            )
            or ""
        )

        body = (
            match.group(
                "body"
            )
            or ""
        )

        arg_names = [
            value.strip()
            for value in args_text.split(
                ","
            )
            if value.strip()
        ]

        category_arg = (
            arg_names[
                0
            ]
            if arg_names
            else ""
        )

        assignment_candidates = []

        for assignment_match in (
            SEARCH_BY_CATEGORY_ASSIGN_PATTERN.finditer(
                body
            )
        ):

            field_name = (
                assignment_match.group(
                    "field1"
                )
                or assignment_match.group(
                    "id1"
                )
                or assignment_match.group(
                    "id2"
                )
                or ""
            )

            if not field_name:

                continue

            assignment_candidates.append(
                field_name
            )

        generic_assignments = []

        for generic_match in (
            GENERIC_VALUE_ASSIGN_PATTERN.finditer(
                body
            )
        ):

            lhs = (
                generic_match.group(
                    "lhs"
                )
                or ""
            )

            rhs = (
                generic_match.group(
                    "rhs"
                )
                or ""
            )

            if (
                category_arg
                and rhs == category_arg
            ):

                generic_assignments.append(
                    lhs
                )

        ajax_urls = []

        for ajax_match in AJAX_URL_PATTERN.finditer(
            body
        ):

            value = (
                ajax_match.group(
                    "url"
                )
                or ""
            )

            if value:

                ajax_urls.append(
                    value
                )

        records.append(
            {
                "source":
                    source_name,

                "args":
                    arg_names,

                "category_argument":
                    category_arg,

                "body":
                    body[
                        :30000
                    ],

                "assignment_candidates":
                    list(
                        dict.fromkeys(
                            assignment_candidates
                        )
                    ),

                "generic_assignments":
                    list(
                        dict.fromkeys(
                            generic_assignments
                        )
                    ),

                "form_submit_detected":
                    (
                        FORM_SUBMIT_PATTERN.search(
                            body
                        )
                        is not None
                    ),

                "ajax_urls":
                    list(
                        dict.fromkeys(
                            ajax_urls
                        )
                    ),
            }
        )

    return records


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

    results = {}

    value = normalize_space(
        text
    )

    for match in CATEGORY_COUNT_PATTERN.finditer(
        value
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

        results[
            category
        ] = count

    return results


# ============================================================
# RESULT ELEMENT EXTRACTION
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


def extract_result_anchors(
    source: str,
    *,
    base_url: str,
) -> List[
    Dict[
        str,
        Any
    ]
]:

    records = []

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

        absolute_url = ""

        if (
            href
            and not href.lower().startswith(
                (
                    "javascript:",
                    "#",
                )
            )
        ):

            absolute_url = normalize_url(
                urljoin(
                    base_url,
                    href,
                )
            )

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

        target_in_label = contains_target(
            label
        )

        search_echo = is_search_echo_text(
            label
        )

        search_url = (
            bool(
                absolute_url
            )
            and is_search_url(
                absolute_url
            )
        )

        actual_result_evidence = (
            bool(
                label
            )
            and (
                bool(
                    absolute_url
                )
                or bool(
                    onclick
                )
                or bool(
                    data_attrs
                )
            )
        )

        target_result_item = (
            target_in_label
            and not search_echo
            and actual_result_evidence
        )

        detail_seed_candidate = (
            target_result_item
            and (
                (
                    bool(
                        absolute_url
                    )
                    and not search_url
                    and is_probable_detail_url(
                        absolute_url
                    )
                )
                or bool(
                    onclick
                )
                or bool(
                    data_attrs
                )
            )
        )

        records.append(
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

                "target_in_label":
                    target_in_label,

                "search_echo":
                    search_echo,

                "search_url":
                    search_url,

                "actual_result_evidence":
                    actual_result_evidence,

                "target_result_item":
                    target_result_item,

                "detail_seed_candidate":
                    detail_seed_candidate,
            }
        )

        if len(
            records
        ) >= MAX_RESULT_ITEMS:

            break

    return records


# ============================================================
# CATEGORY FIELD DISCOVERY
# ============================================================

def discover_category_fields_from_forms(
    forms: List[
        Dict[
            str,
            Any
        ]
    ],
) -> List[
    Dict[
        str,
        Any
    ]
]:

    results = []

    seen = set()

    for form in forms:

        for field_name, value in (
            form.get(
                "fields",
                {}
            ).items()
        ):

            field_type = (
                form.get(
                    "field_types",
                    {}
                ).get(
                    field_name,
                    ""
                )
            )

            evidence = []

            if field_name_matches_category(
                field_name
            ):

                evidence.append(
                    "CATEGORY_FIELD_NAME_HINT"
                )

            if (
                str(
                    value
                ).lower()
                in {
                    "total",
                    "menu",
                    "employee",
                    "cvlcpt",
                    "webpage",
                    "bbs",
                    "attach",
                    "reserve",
                }
            ):

                evidence.append(
                    "KNOWN_CATEGORY_VALUE"
                )

            for select in form.get(
                "selects",
                []
            ):

                if (
                    select.get(
                        "name"
                    )
                    != field_name
                ):

                    continue

                option_values = {
                    str(
                        item.get(
                            "value",
                            ""
                        )
                    ).lower()
                    for item
                    in select.get(
                        "options",
                        []
                    )
                }

                if "bbs" in option_values:

                    evidence.append(
                        "SELECT_HAS_BBS_VALUE"
                    )

            if not evidence:

                continue

            key = (
                form.get(
                    "form_index"
                ),
                field_name,
            )

            if key in seen:

                continue

            seen.add(
                key
            )

            results.append(
                {
                    "form_index":
                        form.get(
                            "form_index"
                        ),

                    "form_id":
                        form.get(
                            "id"
                        ),

                    "form_name":
                        form.get(
                            "name"
                        ),

                    "method":
                        form.get(
                            "method"
                        ),

                    "action_url":
                        form.get(
                            "action_url"
                        ),

                    "field_name":
                        field_name,

                    "current_value":
                        value,

                    "field_type":
                        field_type,

                    "evidence":
                        evidence,
                }
            )

    return results


def discover_search_fields_from_forms(
    forms: List[
        Dict[
            str,
            Any
        ]
    ],
) -> List[
    Dict[
        str,
        Any
    ]
]:

    results = []

    seen = set()

    for form in forms:

        for field_name, value in (
            form.get(
                "fields",
                {}
            ).items()
        ):

            if not field_name_matches_search(
                field_name
            ):

                continue

            key = (
                form.get(
                    "form_index"
                ),
                field_name,
            )

            if key in seen:

                continue

            seen.add(
                key
            )

            results.append(
                {
                    "form_index":
                        form.get(
                            "form_index"
                        ),

                    "method":
                        form.get(
                            "method"
                        ),

                    "action_url":
                        form.get(
                            "action_url"
                        ),

                    "field_name":
                        field_name,

                    "current_value":
                        value,
                }
            )

    return results


# ============================================================
# LOAD N-STAGE
# ============================================================

n_stage_exists = (
    N_STAGE_INPUT_PATH.exists()
)

n_stage_data: Dict[
    str,
    Any
] = {}

if n_stage_exists:

    try:

        n_stage_data = json.loads(
            N_STAGE_INPUT_PATH.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        n_stage_data = {}


# ============================================================
# STATE
# ============================================================

request_count = 0

http_success_count = 0

transport_error_count = 0

external_js_request_count = 0

function_evidence_records: List[
    Dict[
        str,
        Any
    ]
] = []

submission_records: List[
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
    "GANGSEO searchByCategory REQUEST RECONSTRUCTION"
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
    "Target category:",
    TARGET_CATEGORY,
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
    "N-stage input:",
    N_STAGE_INPUT_PATH,
)

print()


# ============================================================
# FETCH BOARD
# ============================================================

board_result = fetch_get(
    BOARD_URL
)

request_count += 1

if board_result.error:

    transport_error_count += 1

    raise RuntimeError(
        f"Gangseo board fetch failed: {board_result.error}"
    )

if board_result.http_status == 200:

    http_success_count += 1


board_final_url = (
    board_result.final_url
    or BOARD_URL
)


# ============================================================
# PARSE BOARD FORMS
# ============================================================

board_forms = parse_forms(
    board_result.text,
    base_url=board_final_url,
)

search_field_records = (
    discover_search_fields_from_forms(
        board_forms
    )
)


# ============================================================
# FIND PRIMARY SEARCH FORM
# ============================================================

primary_search_form = None

primary_search_field = None

for form in board_forms:

    for field_name in form.get(
        "fields",
        {}
    ):

        if not field_name_matches_search(
            field_name
        ):

            continue

        action_url = (
            form.get(
                "action_url"
            )
            or ""
        )

        if (
            action_url.rstrip("/")
            == SEARCH_URL.rstrip("/")
            or "/search"
            in action_url.lower()
        ):

            primary_search_form = form

            primary_search_field = (
                field_name
            )

            break

    if primary_search_form:

        break


if (
    primary_search_form is None
    or primary_search_field is None
):

    raise AssertionError(
        "Primary Gangseo integrated search form not discovered"
    )


# ============================================================
# INITIAL TARGET SEARCH
# ============================================================

initial_payload = dict(
    primary_search_form[
        "fields"
    ]
)

initial_payload[
    primary_search_field
] = TARGET_NAME


if (
    primary_search_form[
        "method"
    ]
    == "POST"
):

    initial_search_result = fetch_post(
        primary_search_form[
            "action_url"
        ],
        initial_payload,
    )

else:

    parsed = urlparse(
        primary_search_form[
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
        initial_payload
    )

    initial_search_url = urlunparse(
        parsed._replace(
            query=urlencode(
                query,
                doseq=True,
            )
        )
    )

    initial_search_result = fetch_get(
        initial_search_url
    )


request_count += 1

if initial_search_result.error:

    transport_error_count += 1

    raise RuntimeError(
        "Initial target search failed: "
        f"{initial_search_result.error}"
    )

if initial_search_result.http_status == 200:

    http_success_count += 1


initial_source = (
    initial_search_result.text
    or ""
)

initial_text = strip_html(
    initial_source
)

initial_final_url = (
    initial_search_result.final_url
    or SEARCH_URL
)


# ============================================================
# INITIAL SEARCH FORMS
# ============================================================

search_page_forms = parse_forms(
    initial_source,
    base_url=initial_final_url,
)

category_field_records = (
    discover_category_fields_from_forms(
        search_page_forms
    )
)


# ============================================================
# SCRIPT ANALYSIS
# ============================================================

script_data = extract_scripts(
    initial_source,
    base_url=initial_final_url,
)


for index, script_body in enumerate(
    script_data[
        "inline_scripts"
    ],
    start=1,
):

    records = extract_function_evidence(
        script_body,
        source_name=(
            f"INLINE_SCRIPT_{index}"
        ),
    )

    function_evidence_records.extend(
        records
    )


external_js_records = []

for js_url in script_data[
    "external_scripts"
]:

    js_result = fetch_get(
        js_url
    )

    request_count += 1

    external_js_request_count += 1

    if js_result.error:

        transport_error_count += 1

        external_js_records.append(
            {
                "url":
                    js_url,

                "http_status":
                    None,

                "error":
                    js_result.error,

                "search_by_category_found":
                    False,
            }
        )

        continue

    if js_result.http_status == 200:

        http_success_count += 1

    js_text = (
        js_result.text
        or ""
    )

    if len(
        js_text
    ) > MAX_EXTERNAL_JS_LENGTH:

        js_text = js_text[
            :MAX_EXTERNAL_JS_LENGTH
        ]

    records = extract_function_evidence(
        js_text,
        source_name=js_url,
    )

    function_evidence_records.extend(
        records
    )

    external_js_records.append(
        {
            "url":
                js_url,

            "http_status":
                js_result.http_status,

            "search_by_category_found":
                bool(
                    records
                ),
        }
    )

    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# JAVASCRIPT FIELD EVIDENCE → FORM FIELD MATCHING
# ============================================================

js_field_names = []

for record in function_evidence_records:

    for value in record.get(
        "assignment_candidates",
        []
    ):

        if value:

            js_field_names.append(
                value
            )

    for expression in record.get(
        "generic_assignments",
        []
    ):

        cleaned = re.sub(
            r"""
            .*?
            (?:
                \.|
                \[
                    ["']?
            )
            ([A-Za-z_$][A-Za-z0-9_$]*)
            ["']?
            \]?
            $
            """,
            r"\1",
            expression,
            flags=re.VERBOSE,
        )

        if cleaned:

            js_field_names.append(
                cleaned
            )


js_field_names = list(
    dict.fromkeys(
        js_field_names
    )
)


for form in search_page_forms:

    for field_name in form.get(
        "fields",
        {}
    ):

        if (
            field_name
            in js_field_names
        ):

            existing = next(
                (
                    record
                    for record
                    in category_field_records
                    if (
                        record.get(
                            "form_index"
                        )
                        == form.get(
                            "form_index"
                        )
                        and record.get(
                            "field_name"
                        )
                        == field_name
                    )
                ),
                None,
            )

            if existing:

                if (
                    "JAVASCRIPT_ASSIGNMENT_EVIDENCE"
                    not in existing[
                        "evidence"
                    ]
                ):

                    existing[
                        "evidence"
                    ].append(
                        "JAVASCRIPT_ASSIGNMENT_EVIDENCE"
                    )

            else:

                category_field_records.append(
                    {
                        "form_index":
                            form.get(
                                "form_index"
                            ),

                        "form_id":
                            form.get(
                                "id"
                            ),

                        "form_name":
                            form.get(
                                "name"
                            ),

                        "method":
                            form.get(
                                "method"
                            ),

                        "action_url":
                            form.get(
                                "action_url"
                            ),

                        "field_name":
                            field_name,

                        "current_value":
                            form.get(
                                "fields",
                                {}
                            ).get(
                                field_name,
                                ""
                            ),

                        "field_type":
                            form.get(
                                "field_types",
                                {}
                            ).get(
                                field_name,
                                ""
                            ),

                        "evidence": [
                            "JAVASCRIPT_ASSIGNMENT_EVIDENCE",
                        ],
                    }
                )


# ============================================================
# SUBMISSION PLAN GENERATION
# ============================================================

submission_plans = []

seen_plan_keys = set()

for category_record in category_field_records:

    form_index = (
        category_record.get(
            "form_index"
        )
    )

    matching_form = next(
        (
            form
            for form
            in search_page_forms
            if form.get(
                "form_index"
            )
            == form_index
        ),
        None,
    )

    if matching_form is None:

        continue

    search_fields = [
        field_name
        for field_name
        in matching_form.get(
            "fields",
            {}
        )
        if field_name_matches_search(
            field_name
        )
    ]

    if not search_fields:

        continue

    category_field = (
        category_record.get(
            "field_name"
        )
        or ""
    )

    if not category_field:

        continue

    for search_field in search_fields:

        payload = dict(
            matching_form.get(
                "fields",
                {}
            )
        )

        payload[
            search_field
        ] = TARGET_NAME

        payload[
            category_field
        ] = TARGET_CATEGORY

        key = (
            matching_form.get(
                "method"
            ),
            matching_form.get(
                "action_url"
            ),
            search_field,
            category_field,
        )

        if key in seen_plan_keys:

            continue

        seen_plan_keys.add(
            key
        )

        submission_plans.append(
            {
                "form_index":
                    matching_form.get(
                        "form_index"
                    ),

                "method":
                    matching_form.get(
                        "method"
                    ),

                "action_url":
                    matching_form.get(
                        "action_url"
                    ),

                "search_field":
                    search_field,

                "category_field":
                    category_field,

                "category_field_evidence":
                    category_record.get(
                        "evidence",
                        []
                    ),

                "payload":
                    payload,
            }
        )


submission_plans = submission_plans[
    :MAX_CANDIDATE_SUBMISSIONS
]


# ============================================================
# EXECUTE EVIDENCE-BASED CATEGORY REQUESTS
# ============================================================

for submission_index, plan in enumerate(
    submission_plans,
    start=1,
):

    method = (
        plan.get(
            "method"
        )
        or "GET"
    ).upper()

    action_url = (
        plan.get(
            "action_url"
        )
        or SEARCH_URL
    )

    payload = dict(
        plan.get(
            "payload",
            {}
        )
    )

    if method == "POST":

        result = fetch_post(
            action_url,
            payload,
        )

    else:

        parsed = urlparse(
            action_url
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

        request_url = urlunparse(
            parsed._replace(
                query=urlencode(
                    query,
                    doseq=True,
                )
            )
        )

        result = fetch_get(
            request_url
        )

    request_count += 1

    if result.error:

        transport_error_count += 1

        submission_records.append(
            {
                "submission_index":
                    submission_index,

                **plan,

                "http_status":
                    None,

                "error":
                    result.error,

                "target_response":
                    False,

                "category_counts":
                    {},

                "target_result_item_count":
                    0,

                "detail_seed_count":
                    0,
            }
        )

        continue

    if result.http_status == 200:

        http_success_count += 1

    final_url = (
        result.final_url
        or action_url
    )

    response_text = strip_html(
        result.text
    )

    category_counts = extract_category_counts(
        response_text
    )

    anchors = extract_result_anchors(
        result.text,
        base_url=final_url,
    )

    target_items = [
        item
        for item
        in anchors
        if item.get(
            "target_result_item"
        )
        is True
    ]

    seeds = [
        item
        for item
        in target_items
        if item.get(
            "detail_seed_candidate"
        )
        is True
    ]

    for seed in seeds:

        detail_seed_candidates.append(
            {
                "region":
                    REGION,

                "agency":
                    AGENCY,

                "submission_index":
                    submission_index,

                "search_field":
                    plan.get(
                        "search_field"
                    ),

                "category_field":
                    plan.get(
                        "category_field"
                    ),

                "category_field_evidence":
                    plan.get(
                        "category_field_evidence"
                    ),

                **seed,
            }
        )

    submission_records.append(
        {
            "submission_index":
                submission_index,

            "form_index":
                plan.get(
                    "form_index"
                ),

            "method":
                method,

            "action_url":
                action_url,

            "search_field":
                plan.get(
                    "search_field"
                ),

            "category_field":
                plan.get(
                    "category_field"
                ),

            "category_field_evidence":
                plan.get(
                    "category_field_evidence"
                ),

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

            "anchor_count":
                len(
                    anchors
                ),

            "target_result_item_count":
                len(
                    target_items
                ),

            "detail_seed_count":
                len(
                    seeds
                ),

            "target_items":
                target_items[
                    :50
                ],

            "response_preview":
                response_text[
                    :2500
                ],
        }
    )

    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# DEDUPE DETAIL SEEDS
# ============================================================

deduped_detail_seeds = []

seen_detail_seed_keys = set()

for seed in detail_seed_candidates:

    key = (
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
        tuple(
            sorted(
                (
                    seed.get(
                        "data_attributes"
                    )
                    or {}
                ).items()
            )
        ),
    )

    if key in seen_detail_seed_keys:

        continue

    seen_detail_seed_keys.add(
        key
    )

    deduped_detail_seeds.append(
        seed
    )


# ============================================================
# RESULTS
# ============================================================

category_request_reconstructed = (
    len(
        submission_plans
    )
    > 0
)

successful_category_submission_count = sum(
    1
    for item
    in submission_records
    if item.get(
        "http_status"
    )
    == 200
)

bbs_count_confirmed_submission_count = sum(
    1
    for item
    in submission_records
    if (
        item.get(
            "category_counts",
            {}
        ).get(
            "게시판"
        )
        or 0
    )
    > 0
)

target_result_submission_count = sum(
    1
    for item
    in submission_records
    if (
        item.get(
            "target_result_item_count",
            0
        )
        or 0
    )
    > 0
)


# ============================================================
# RESOLUTION
# ============================================================

if deduped_detail_seeds:

    resolution = (
        "GANGSEO_BBS_CATEGORY_DETAIL_SEED_DISCOVERED"
    )

    next_action = (
        "복원된 강서구 게시판 category search에서 확보한 "
        "target-bearing 상세 seed를 직접 조회하여 "
        "개발밀도관리구역 지정·변경·해제 고시 원문인지 검증한다."
    )

elif target_result_submission_count > 0:

    resolution = (
        "GANGSEO_BBS_CATEGORY_TARGET_ITEM_FOUND_DETAIL_UNRESOLVED"
    )

    next_action = (
        "category=bbs 요청 재구성에 성공했고 target-bearing item도 "
        "확인했으나 상세 URL을 확정하지 못했다. 해당 item의 "
        "onclick/data-*와 JavaScript detail handler를 추가 분석한다."
    )

elif category_request_reconstructed:

    resolution = (
        "GANGSEO_BBS_CATEGORY_REQUEST_RECONSTRUCTED_NO_TARGET_ITEM"
    )

    next_action = (
        "searchByCategory 구조를 근거로 bbs category 요청은 복원했으나 "
        "실제 target-bearing result item이 아직 확인되지 않았다. "
        "category response의 AJAX fragment 또는 후속 detail handler를 분석한다."
    )

elif function_evidence_records:

    resolution = (
        "SEARCH_BY_CATEGORY_FUNCTION_FOUND_REQUEST_FIELD_UNRESOLVED"
    )

    next_action = (
        "searchByCategory 함수는 확보했으나 form category field와 "
        "신뢰성 있게 연결하지 못했다. 함수 body의 DOM selector와 "
        "submit/AJAX 호출을 site-specific parser로 해석한다."
    )

else:

    resolution = (
        "SEARCH_BY_CATEGORY_IMPLEMENTATION_NOT_FOUND"
    )

    next_action = (
        "inline/external JavaScript에서 searchByCategory 정의를 "
        "찾지 못했다. 이벤트 바인딩 또는 번들 JavaScript에서 "
        "함수 등록 구조를 추가 탐색한다."
    )


runtime_registration_blocked = True

site_false_interpretation_blocked = True


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-O "
        "Development Density Management Area "
        "Gangseo searchByCategory Request Reconstruction"
    ),

    "target": {
        "name":
            TARGET_NAME,

        "standard_code":
            STANDARD_CODE,

        "category":
            TARGET_CATEGORY,
    },

    "input": {
        "n_stage_path":
            str(
                N_STAGE_INPUT_PATH
            ),

        "n_stage_exists":
            n_stage_exists,

        "n_stage_parsed":
            bool(
                n_stage_data
            ),
    },

    "method": {
        "actual_search_form_reused":
            True,

        "hidden_fields_preserved":
            True,

        "arbitrary_category_parameter_injection":
            False,

        "category_field_requires_evidence":
            True,

        "inline_javascript_analysis":
            True,

        "external_official_javascript_analysis":
            True,

        "search_by_category_function_analysis":
            True,

        "bbs_category_reconstruction":
            True,

        "visible_target_required_for_result_item":
            True,

        "search_echo_guard":
            True,

        "detail_seed_is_final_positive":
            False,
    },

    "initial_search": {
        "form_index":
            primary_search_form.get(
                "form_index"
            ),

        "method":
            primary_search_form.get(
                "method"
            ),

        "action_url":
            primary_search_form.get(
                "action_url"
            ),

        "search_field":
            primary_search_field,

        "http_status":
            initial_search_result.http_status,

        "target_response":
            contains_target(
                initial_text
            ),

        "category_counts":
            extract_category_counts(
                initial_text
            ),
    },

    "discovery": {
        "board_form_count":
            len(
                board_forms
            ),

        "search_page_form_count":
            len(
                search_page_forms
            ),

        "search_field_records":
            search_field_records,

        "category_field_records":
            category_field_records,

        "inline_script_count":
            len(
                script_data[
                    "inline_scripts"
                ]
            ),

        "external_script_count":
            len(
                script_data[
                    "external_scripts"
                ]
            ),

        "external_js_records":
            external_js_records,

        "search_by_category_function_evidence":
            function_evidence_records,

        "javascript_field_names":
            js_field_names,
    },

    "submission_plans":
        submission_plans,

    "submission_records":
        submission_records,

    "detail_seed_candidates":
        deduped_detail_seeds,

    "summary": {
        "request_count":
            request_count,

        "http_success_count":
            http_success_count,

        "transport_error_count":
            transport_error_count,

        "external_js_request_count":
            external_js_request_count,

        "function_evidence_count":
            len(
                function_evidence_records
            ),

        "category_field_candidate_count":
            len(
                category_field_records
            ),

        "submission_plan_count":
            len(
                submission_plans
            ),

        "successful_category_submission_count":
            successful_category_submission_count,

        "bbs_count_confirmed_submission_count":
            bbs_count_confirmed_submission_count,

        "target_result_submission_count":
            target_result_submission_count,

        "detail_seed_candidate_count":
            len(
                deduped_detail_seeds
            ),
    },

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
# CONSOLE
# ============================================================

print(
    "Initial search HTTP:",
    initial_search_result.http_status,
)

print(
    "Initial category counts:",
    extract_category_counts(
        initial_text
    ),
)

print(
    "Search page forms:",
    len(
        search_page_forms
    ),
)

print(
    "Inline scripts:",
    len(
        script_data[
            "inline_scripts"
        ]
    ),
)

print(
    "External scripts:",
    len(
        script_data[
            "external_scripts"
        ]
    ),
)

print(
    "searchByCategory function evidence:",
    len(
        function_evidence_records
    ),
)

print(
    "Category field candidates:",
    len(
        category_field_records
    ),
)

print()


if function_evidence_records:

    print(
        "SEARCH BY CATEGORY FUNCTION EVIDENCE"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, record in enumerate(
        function_evidence_records,
        start=1,
    ):

        print(
            f"[{index}]"
        )

        print(
            "Source:",
            record.get(
                "source"
            ),
        )

        print(
            "Args:",
            record.get(
                "args"
            ),
        )

        print(
            "Assignment candidates:",
            record.get(
                "assignment_candidates"
            ),
        )

        print(
            "Generic assignments:",
            record.get(
                "generic_assignments"
            ),
        )

        print(
            "Form submit:",
            record.get(
                "form_submit_detected"
            ),
        )

        print(
            "AJAX URLs:",
            record.get(
                "ajax_urls"
            ),
        )

        print(
            "Body preview:",
            normalize_space(
                record.get(
                    "body"
                )
                or ""
            )[
                :1800
            ],
        )

        print()


if category_field_records:

    print(
        "CATEGORY FIELD CANDIDATES"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, record in enumerate(
        category_field_records,
        start=1,
    ):

        print(
            f"[{index}]"
        )

        print(
            "Form:",
            record.get(
                "form_index"
            ),
        )

        print(
            "Method:",
            record.get(
                "method"
            ),
        )

        print(
            "Action:",
            record.get(
                "action_url"
            ),
        )

        print(
            "Field:",
            record.get(
                "field_name"
            ),
        )

        print(
            "Current value:",
            record.get(
                "current_value"
            ),
        )

        print(
            "Evidence:",
            record.get(
                "evidence"
            ),
        )

        print()


print(
    "============================================================"
)

print(
    "CATEGORY REQUEST EXECUTION"
)

print(
    "============================================================"
)

print(
    "Submission plans:",
    len(
        submission_plans
    ),
)

print()


for record in submission_records:

    print(
        "------------------------------------------------------------"
    )

    print(
        "SUBMISSION:",
        record.get(
            "submission_index"
        ),
    )

    print(
        "Method:",
        record.get(
            "method"
        ),
    )

    print(
        "Action:",
        record.get(
            "action_url"
        ),
    )

    print(
        "Search field:",
        record.get(
            "search_field"
        ),
    )

    print(
        "Category field:",
        record.get(
            "category_field"
        ),
    )

    print(
        "Evidence:",
        record.get(
            "category_field_evidence"
        ),
    )

    print(
        "HTTP:",
        record.get(
            "http_status"
        ),
    )

    print(
        "Target response:",
        record.get(
            "target_response"
        ),
    )

    print(
        "Category counts:",
        record.get(
            "category_counts"
        ),
    )

    print(
        "Target result items:",
        record.get(
            "target_result_item_count"
        ),
    )

    print(
        "Detail seeds:",
        record.get(
            "detail_seed_count"
        ),
    )

    for item in record.get(
        "target_items",
        []
    )[
        :10
    ]:

        print(
            "  TARGET ITEM:",
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
    "RECONSTRUCTION RESULT"
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
    "External JS request count:",
    external_js_request_count,
)

print(
    "Function evidence count:",
    len(
        function_evidence_records
    ),
)

print(
    "Category field candidate count:",
    len(
        category_field_records
    ),
)

print(
    "Submission plan count:",
    len(
        submission_plans
    ),
)

print(
    "Successful category submissions:",
    successful_category_submission_count,
)

print(
    "BBS-count-confirmed submissions:",
    bbs_count_confirmed_submission_count,
)

print(
    "Target-result submissions:",
    target_result_submission_count,
)

print(
    "Detail seed candidate count:",
    len(
        deduped_detail_seeds
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

submission_plan_keys = {
    (
        item.get(
            "method"
        ),
        item.get(
            "action_url"
        ),
        item.get(
            "search_field"
        ),
        item.get(
            "category_field"
        ),
    )
    for item in submission_plans
}


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
        item.get(
            "label"
        ),
    )
    for item in deduped_detail_seeds
}


all_submission_plans_have_evidence = all(
    bool(
        item.get(
            "category_field_evidence"
        )
    )
    for item in submission_plans
)


all_submission_plans_use_bbs = all(
    (
        item.get(
            "payload",
            {}
        ).get(
            item.get(
                "category_field"
            )
        )
        == TARGET_CATEGORY
    )
    for item in submission_plans
)


all_detail_seeds_have_visible_target = all(
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

    "target category bbs": (
        TARGET_CATEGORY
        == "bbs"
    ),

    "N-stage input exists": (
        n_stage_exists
    ),

    "N-stage input parsed": (
        bool(
            n_stage_data
        )
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

    "actual search form discovered": (
        primary_search_form
        is not None
    ),

    "search field discovered": (
        bool(
            primary_search_field
        )
    ),

    "initial search executed": (
        initial_search_result.http_status
        is not None
    ),

    "initial response contains target": (
        contains_target(
            initial_text
        )
    ),

    "N-stage board count preserved": (
        (
            extract_category_counts(
                initial_text
            ).get(
                "게시판"
            )
            or 0
        )
        >= 1
    ),

    "arbitrary category injection disabled": (
        output_data[
            "method"
        ][
            "arbitrary_category_parameter_injection"
        ]
        is False
    ),

    "category field requires evidence": (
        output_data[
            "method"
        ][
            "category_field_requires_evidence"
        ]
        is True
    ),

    "inline JS analysis enabled": (
        output_data[
            "method"
        ][
            "inline_javascript_analysis"
        ]
        is True
    ),

    "external official JS analysis enabled": (
        output_data[
            "method"
        ][
            "external_official_javascript_analysis"
        ]
        is True
    ),

    "searchByCategory analysis enabled": (
        output_data[
            "method"
        ][
            "search_by_category_function_analysis"
        ]
        is True
    ),

    "submission plans unique": (
        len(
            submission_plan_keys
        )
        == len(
            submission_plans
        )
    ),

    "all submission plans have category evidence": (
        all_submission_plans_have_evidence
    ),

    "all submission plans use bbs category": (
        all_submission_plans_use_bbs
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
        all_detail_seeds_have_visible_target
    ),

    "all detail seeds are not search echo": (
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

    "requests executed": (
        request_count
        > 0
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
        "Gangseo category request reconstruction regression failed"
    )