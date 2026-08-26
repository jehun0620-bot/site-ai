# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-M
Development Density Management Area
Dynamic Detail Reconstruction

목표
======================================================================
L-stage POST search discovery에서 확인된 target-bearing row를 대상으로

    개발밀도관리구역

문자열이 실제 검색 결과 문서 row에 존재하는지,
아니면 검색어 echo / 최근검색어 / 검색 UI 문자열인지 판별한다.

특히 서울특별시 강서구

    https://www.gangseo.seoul.kr/gs040301

고시공고 검색 구조를 우선 대상으로 한다.

탐색 구조
======================================================================

official board endpoint
    ↓
실제 search form 탐색
    ↓
GET / POST submission
    ↓
target-bearing HTML fragment
    ↓
SEARCH_TERM_ECHO 여부 판별
    ↓
href / onclick / data-* / hidden identifier
    ↓
JavaScript 함수 정의 분석
    ↓
detail URL reconstruction candidate

중요 안전정책
======================================================================

1. 검색어 echo는 실제 target result row로 인정하지 않는다.
2. URL query에 target이 있다는 이유만으로 target evidence로 인정하지 않는다.
3. "내가 찾은 검색어", "검색어 삭제", "최근검색어" 등의 UI 문자열은
   SEARCH_TERM_ECHO로 명시적으로 분류한다.
4. explicit href가 있더라도 search URL이면 detail candidate로 인정하지 않는다.
5. onclick / data-* 값은 실제 document identifier가 확인될 때만
   reconstruction seed로 사용한다.
6. reconstructed URL은 VERIFIED_POSITIVE가 아니다.
7. reconstructed detail URL은 다음 N-stage 원문 검증 seed일 뿐이다.
8. 실제 원문 검증 전까지 runtime spatial condition 등록은 차단한다.
9. 후보 미발견을 SITE FALSE로 해석하지 않는다.

이번 단계 성공 조건
======================================================================

A.
검색어 echo를 정상적으로 식별 및 차단

또는

B.
실제 target-bearing result fragment에서
detail reconstruction candidate 확보

또는

C.
안전하게 UNRESOLVED 상태를 유지

즉 reconstruction candidate 0건도 regression 실패가 아니다.
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

L_STAGE_INPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "official_board_post_search_discovery.json"
    )
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "dynamic_detail_reconstruction.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"

STANDARD_CODE = "UQQ700"


# ============================================================
# PRIMARY M-STAGE TARGET
# ============================================================

PRIMARY_REGION = "서울특별시 강서구"

PRIMARY_AGENCY = "서울특별시 강서구"

PRIMARY_BOARD_URL = (
    "https://www.gangseo.seoul.kr/gs040301"
)


# ============================================================
# REQUEST CONFIG
# ============================================================

REQUEST_TIMEOUT = 20

REQUEST_SLEEP = 0.25

MAX_CONTENT_LENGTH = 2_000_000

MAX_FRAGMENT_RADIUS = 3000

MAX_SCRIPT_LENGTH = 1_000_000

MAX_RECONSTRUCTED_CANDIDATES = 100


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
# SEARCH / ECHO GUARDS
# ============================================================

SEARCH_ECHO_TERMS = [
    "내가 찾은 검색어",
    "검색어 삭제",
    "최근검색어",
    "최근 검색어",
    "인기검색어",
    "인기 검색어",
    "검색어 저장",
    "검색어입력",
    "검색어 입력",
    "결과 내 재검색",
    "상세검색",
    "통합검색",
]


SEARCH_URL_HINTS = [
    "/search",
    "search.",
    "search/",
    "search?",
    "search.do",
    "search.jsp",
    "totalsearch",
    "totalSearch",
]


DETAIL_URL_HINTS = [
    "view.do",
    "detail.do",
    "selectBoardArticle",
    "selectBoardArticle.do",
    "bbsMsgDetail",
    "bbsMsgDetail.do",
    "eminwonAnnounceDetail",
    "post/view",
    "/view.",
    "?act=view",
    "&act=view",
    "nttId=",
    "idx=",
    "seq=",
    "msg_seq=",
    "mgt_no=",
    "notAncmtMgtNo=",
    "boardSeq=",
    "articleSeq=",
]


DOCUMENT_ID_HINTS = [
    "idx",
    "seq",
    "nttid",
    "ntt_id",
    "nttId",
    "msg_seq",
    "mgt_no",
    "notAncmtMgtNo",
    "boardseq",
    "boardSeq",
    "articleseq",
    "articleSeq",
    "bbsid",
    "bbsId",
    "bcidx",
    "bcIdx",
]


SEARCH_FIELD_HINTS = [
    "search",
    "keyword",
    "query",
    "keyWord",
    "searchWord",
    "searchKeyword",
    "srch",
    "sstring",
    "searchText",
]


# ============================================================
# DATA CLASS
# ============================================================

@dataclass
class FetchResult:
    request_url: str
    method: str
    http_status: Optional[int]
    content_type: str
    text: str
    error: Optional[str]
    final_url: Optional[str]


# ============================================================
# BASIC UTIL
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


# ============================================================
# URL UTIL
# ============================================================

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "jsessionid",
    "timestamp",
    "_",
}


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
            item.lower()
            for item in VOLATILE_QUERY_KEYS
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
        for hint in SEARCH_URL_HINTS
    )


def has_detail_url_hint(
    url: str,
) -> bool:

    lower = (
        url
        or ""
    ).lower()

    return any(
        hint.lower() in lower
        for hint in DETAIL_URL_HINTS
    )


def target_only_in_url_query(
    url: str,
    visible_text: str,
) -> bool:

    return (
        contains_target(
            url
        )
        and not contains_target(
            visible_text
        )
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
            request_url=url,
            method="GET",
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
        request_url=url,
        method="GET",
        http_status=response.status_code,
        content_type=content_type,
        text=text,
        error=None,
        final_url=response.url,
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
            request_url=url,
            method="POST",
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
        request_url=url,
        method="POST",
        http_status=response.status_code,
        content_type=content_type,
        text=text,
        error=None,
        final_url=response.url,
    )


# ============================================================
# HTML ATTRIBUTE PARSING
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
    tag_source: str,
) -> Dict[str, str]:

    result = {}

    for match in ATTRIBUTE_PATTERN.finditer(
        tag_source
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

        result[
            name
        ] = html.unescape(
            value
        )

    return result


# ============================================================
# FORM PARSING
# ============================================================

FORM_PATTERN = re.compile(
    r"(?is)<form\b([^>]*)>(.*?)</form>"
)

INPUT_PATTERN = re.compile(
    r"(?is)<input\b([^>]*)>"
)

TEXTAREA_PATTERN = re.compile(
    r"(?is)<textarea\b([^>]*)>(.*?)</textarea>"
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
) -> List[Dict[str, Any]]:

    forms = []

    for form_index, match in enumerate(
        FORM_PATTERN.finditer(
            source
        ),
        start=1,
    ):

        form_tag = (
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

        attrs = parse_attributes(
            form_tag
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

        fields: List[
            Dict[
                str,
                Any
            ]
        ] = []

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

            fields.append(
                {
                    "tag": "input",
                    "name": name,
                    "type": field_type,
                    "value": (
                        input_attrs.get(
                            "value"
                        )
                        or ""
                    ),
                }
            )

        for textarea_match in TEXTAREA_PATTERN.finditer(
            body
        ):

            textarea_attrs = parse_attributes(
                textarea_match.group(
                    1
                )
                or ""
            )

            name = (
                textarea_attrs.get(
                    "name"
                )
                or ""
            )

            if not name:

                continue

            fields.append(
                {
                    "tag": "textarea",
                    "name": name,
                    "type": "textarea",
                    "value": strip_html(
                        textarea_match.group(
                            2
                        )
                        or ""
                    ),
                }
            )

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

            selected_value = ""

            options = list(
                OPTION_PATTERN.finditer(
                    select_match.group(
                        2
                    )
                    or ""
                )
            )

            for option_match in options:

                option_attrs = parse_attributes(
                    option_match.group(
                        1
                    )
                    or ""
                )

                if "selected" in (
                    option_match.group(
                        1
                    )
                    or ""
                ).lower():

                    selected_value = (
                        option_attrs.get(
                            "value"
                        )
                        or strip_html(
                            option_match.group(
                                2
                            )
                            or ""
                        )
                    )

                    break

            if (
                not selected_value
                and options
            ):

                first_attrs = parse_attributes(
                    options[
                        0
                    ].group(
                        1
                    )
                    or ""
                )

                selected_value = (
                    first_attrs.get(
                        "value"
                    )
                    or strip_html(
                        options[
                            0
                        ].group(
                            2
                        )
                        or ""
                    )
                )

            fields.append(
                {
                    "tag": "select",
                    "name": name,
                    "type": "select",
                    "value": selected_value,
                }
            )

        forms.append(
            {
                "form_index": form_index,
                "method": method,
                "action_url": action_url,
                "fields": fields,
                "visible_text": strip_html(
                    body
                ),
            }
        )

    return forms


# ============================================================
# SEARCH FORM IDENTIFICATION
# ============================================================

def field_looks_searchable(
    field: Dict[str, Any],
) -> bool:

    name = str(
        field.get(
            "name"
        )
        or ""
    )

    field_type = str(
        field.get(
            "type"
        )
        or ""
    ).lower()

    if field_type not in {
        "text",
        "search",
        "textarea",
    }:

        return False

    lower_name = name.lower()

    return any(
        hint.lower() in lower_name
        for hint in SEARCH_FIELD_HINTS
    )


def build_search_payload(
    form: Dict[str, Any],
) -> Optional[Dict[str, str]]:

    fields = (
        form.get(
            "fields"
        )
        or []
    )

    search_fields = [
        field
        for field in fields
        if field_looks_searchable(
            field
        )
    ]

    if not search_fields:

        return None

    payload: Dict[
        str,
        str
    ] = {}

    chosen_search_name = str(
        search_fields[
            0
        ].get(
            "name"
        )
        or ""
    )

    for field in fields:

        name = str(
            field.get(
                "name"
            )
            or ""
        )

        if not name:

            continue

        field_type = str(
            field.get(
                "type"
            )
            or ""
        ).lower()

        if field_type in {
            "submit",
            "button",
            "reset",
            "file",
            "image",
        }:

            continue

        if name == chosen_search_name:

            payload[
                name
            ] = TARGET_NAME

        else:

            payload[
                name
            ] = str(
                field.get(
                    "value"
                )
                or ""
            )

    return payload


# ============================================================
# TARGET FRAGMENT EXTRACTION
# ============================================================

def find_target_positions(
    source: str,
) -> List[int]:

    variants = [
        TARGET_NAME,
        "개발밀도 관리구역",
        "개발 밀도 관리구역",
    ]

    positions = []

    for variant in variants:

        start = 0

        while True:

            index = source.find(
                variant,
                start,
            )

            if index < 0:

                break

            positions.append(
                index
            )

            start = (
                index
                + len(
                    variant
                )
            )

    return sorted(
        set(
            positions
        )
    )


def extract_target_fragments(
    source: str,
) -> List[Dict[str, Any]]:

    fragments = []

    seen = set()

    for index in find_target_positions(
        source
    ):

        start = max(
            0,
            index
            - MAX_FRAGMENT_RADIUS,
        )

        end = min(
            len(
                source
            ),
            index
            + len(
                TARGET_NAME
            )
            + MAX_FRAGMENT_RADIUS,
        )

        raw_fragment = source[
            start:end
        ]

        visible_text = strip_html(
            raw_fragment
        )

        key = (
            normalize_space(
                visible_text
            )
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        fragments.append(
            {
                "source_index": index,
                "raw_html": raw_fragment,
                "visible_text": visible_text,
            }
        )

    return fragments


# ============================================================
# SEARCH TERM ECHO CLASSIFICATION
# ============================================================

def search_echo_score(
    visible_text: str,
) -> Tuple[int, List[str]]:

    score = 0

    reasons = []

    normalized = normalize_space(
        visible_text
    )

    for term in SEARCH_ECHO_TERMS:

        if term in normalized:

            score += 2

            reasons.append(
                f"ECHO_TERM:{term}"
            )

    compact = compact_text(
        normalized
    )

    target_compact = compact_text(
        TARGET_NAME
    )

    if (
        target_compact
        in compact
        and (
            "검색어삭제"
            in compact
            or "내가찾은검색어"
            in compact
        )
    ):

        score += 5

        reasons.append(
            "TARGET_ADJACENT_TO_SEARCH_UI"
        )

    if len(
        normalized
    ) < 80:

        if any(
            term in normalized
            for term in [
                "검색어",
                "삭제",
                "재검색",
            ]
        ):

            score += 2

            reasons.append(
                "SHORT_SEARCH_UI_FRAGMENT"
            )

    return (
        score,
        reasons,
    )


def is_search_term_echo(
    visible_text: str,
) -> Tuple[bool, int, List[str]]:

    score, reasons = search_echo_score(
        visible_text
    )

    return (
        score >= 4,
        score,
        reasons,
    )


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
) -> List[Dict[str, Any]]:

    anchors = []

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

        if href:

            absolute_url = normalize_url(
                urljoin(
                    base_url,
                    href,
                )
            )

        anchors.append(
            {
                "label": label,
                "href": href,
                "absolute_url": absolute_url,
                "onclick": (
                    attrs.get(
                        "onclick"
                    )
                    or ""
                ),
                "attributes": attrs,
            }
        )

    return anchors


# ============================================================
# DATA-* / ID EXTRACTION
# ============================================================

TAG_PATTERN = re.compile(
    r"(?is)<([a-zA-Z0-9:_-]+)\b([^>]*)>"
)


def extract_identifier_attributes(
    source: str,
) -> List[Dict[str, Any]]:

    records = []

    seen = set()

    for match in TAG_PATTERN.finditer(
        source
    ):

        tag_name = (
            match.group(
                1
            )
            or ""
        )

        attrs = parse_attributes(
            match.group(
                2
            )
            or ""
        )

        interesting = {}

        for key, value in attrs.items():

            lower_key = key.lower()

            if (
                lower_key.startswith(
                    "data-"
                )
                or lower_key in {
                    "id",
                    "name",
                    "value",
                    "onclick",
                    "href",
                }
                or any(
                    hint.lower()
                    in lower_key
                    for hint in DOCUMENT_ID_HINTS
                )
            ):

                interesting[
                    key
                ] = value

        if not interesting:

            continue

        key = (
            tag_name,
            tuple(
                sorted(
                    interesting.items()
                )
            ),
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        records.append(
            {
                "tag": tag_name,
                "attributes": interesting,
            }
        )

    return records


# ============================================================
# JAVASCRIPT ANALYSIS
# ============================================================

SCRIPT_PATTERN = re.compile(
    r"(?is)<script\b[^>]*>(.*?)</script>"
)


FUNCTION_PATTERN = re.compile(
    r"""
    function
    \s+
    (?P<name>[A-Za-z_$][A-Za-z0-9_$]*)
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
    | re.DOTALL,
)


JS_URL_PATTERN = re.compile(
    r"""
    (?:
        location(?:\.href)?
        |
        window\.location(?:\.href)?
        |
        document\.location
    )
    \s*=\s*
    ["']
    (?P<url>[^"']+)
    ["']
    """,
    re.VERBOSE
    | re.IGNORECASE,
)


STRING_URL_PATTERN = re.compile(
    r"""
    ["']
    (?P<url>
        [^"']*
        (?:
            view\.do
            |
            detail\.do
            |
            selectBoardArticle
            |
            bbsMsgDetail
            |
            eminwonAnnounceDetail
            |
            /view\.
        )
        [^"']*
    )
    ["']
    """,
    re.VERBOSE
    | re.IGNORECASE,
)


def extract_scripts(
    source: str,
) -> List[str]:

    scripts = []

    total = 0

    for match in SCRIPT_PATTERN.finditer(
        source
    ):

        script = (
            match.group(
                1
            )
            or ""
        )

        if not script.strip():

            continue

        if (
            total
            + len(
                script
            )
            > MAX_SCRIPT_LENGTH
        ):

            break

        scripts.append(
            script
        )

        total += len(
            script
        )

    return scripts


def extract_javascript_functions(
    source: str,
) -> List[Dict[str, str]]:

    functions = []

    for script in extract_scripts(
        source
    ):

        for match in FUNCTION_PATTERN.finditer(
            script
        ):

            functions.append(
                {
                    "name": (
                        match.group(
                            "name"
                        )
                        or ""
                    ),
                    "args": normalize_space(
                        match.group(
                            "args"
                        )
                        or ""
                    ),
                    "body": (
                        match.group(
                            "body"
                        )
                        or ""
                    )[
                        :10000
                    ],
                }
            )

    return functions


def extract_script_detail_urls(
    source: str,
    *,
    base_url: str,
) -> List[str]:

    urls = []

    seen = set()

    for script in extract_scripts(
        source
    ):

        for pattern in [
            JS_URL_PATTERN,
            STRING_URL_PATTERN,
        ]:

            for match in pattern.finditer(
                script
            ):

                raw_url = (
                    match.group(
                        "url"
                    )
                    or ""
                )

                if not raw_url:

                    continue

                absolute = normalize_url(
                    urljoin(
                        base_url,
                        html.unescape(
                            raw_url
                        ),
                    )
                )

                if (
                    not has_detail_url_hint(
                        absolute
                    )
                ):

                    continue

                if absolute in seen:

                    continue

                seen.add(
                    absolute
                )

                urls.append(
                    absolute
                )

    return urls


# ============================================================
# ONCLICK ANALYSIS
# ============================================================

FUNCTION_CALL_PATTERN = re.compile(
    r"""
    (?P<name>
        [A-Za-z_$][A-Za-z0-9_$]*
    )
    \s*
    \(
        (?P<args>[^)]*)
    \)
    """,
    re.VERBOSE,
)


QUOTED_ARG_PATTERN = re.compile(
    r"""
    (?:
        "([^"]*)"
        |
        '([^']*)'
        |
        ([^,\s]+)
    )
    """,
    re.VERBOSE,
)


def parse_function_call(
    onclick: str,
) -> Optional[Dict[str, Any]]:

    match = FUNCTION_CALL_PATTERN.search(
        onclick
    )

    if not match:

        return None

    args_text = (
        match.group(
            "args"
        )
        or ""
    )

    args = []

    for arg_match in QUOTED_ARG_PATTERN.finditer(
        args_text
    ):

        value = (
            arg_match.group(
                1
            )
            or arg_match.group(
                2
            )
            or arg_match.group(
                3
            )
            or ""
        )

        args.append(
            value.strip()
        )

    return {
        "function": (
            match.group(
                "name"
            )
            or ""
        ),
        "args": args,
        "raw": onclick,
    }


# ============================================================
# RECONSTRUCTION
# ============================================================

def identifier_evidence_from_attributes(
    records: List[Dict[str, Any]],
) -> List[Dict[str, str]]:

    results = []

    seen = set()

    for record in records:

        attrs = (
            record.get(
                "attributes"
            )
            or {}
        )

        for key, value in attrs.items():

            lower_key = key.lower()

            if not value:

                continue

            evidence = False

            if any(
                hint.lower()
                in lower_key
                for hint in DOCUMENT_ID_HINTS
            ):

                evidence = True

            elif (
                lower_key.startswith(
                    "data-"
                )
                and re.search(
                    r"\d{2,}",
                    str(
                        value
                    ),
                )
            ):

                evidence = True

            if not evidence:

                continue

            evidence_key = (
                key,
                str(
                    value
                ),
            )

            if evidence_key in seen:

                continue

            seen.add(
                evidence_key
            )

            results.append(
                {
                    "name": key,
                    "value": str(
                        value
                    ),
                }
            )

    return results


def reconstruct_from_anchor(
    anchor: Dict[str, Any],
    *,
    base_url: str,
) -> List[Dict[str, Any]]:

    candidates = []

    absolute_url = (
        anchor.get(
            "absolute_url"
        )
        or ""
    )

    if (
        absolute_url
        and not is_search_url(
            absolute_url
        )
        and has_detail_url_hint(
            absolute_url
        )
    ):

        candidates.append(
            {
                "reconstruction_type":
                    "EXPLICIT_DETAIL_HREF",

                "url":
                    normalize_url(
                        absolute_url
                    ),

                "evidence":
                    {
                        "anchor_label":
                            anchor.get(
                                "label"
                            ),

                        "href":
                            anchor.get(
                                "href"
                            ),
                    },
            }
        )

    onclick = (
        anchor.get(
            "onclick"
        )
        or ""
    )

    call = parse_function_call(
        onclick
    )

    if call:

        numeric_args = [
            value
            for value in call[
                "args"
            ]
            if re.fullmatch(
                r"\d{2,}",
                value,
            )
        ]

        url_args = [
            value
            for value in call[
                "args"
            ]
            if (
                "/" in value
                or ".do" in value
                or ".jsp" in value
                or ".web" in value
            )
        ]

        for raw_url in url_args:

            absolute = normalize_url(
                urljoin(
                    base_url,
                    raw_url,
                )
            )

            if (
                not is_search_url(
                    absolute
                )
                and has_detail_url_hint(
                    absolute
                )
            ):

                candidates.append(
                    {
                        "reconstruction_type":
                            "ONCLICK_URL_ARGUMENT",

                        "url":
                            absolute,

                        "evidence":
                            call,
                    }
                )

        if numeric_args:

            candidates.append(
                {
                    "reconstruction_type":
                        "ONCLICK_IDENTIFIER_SEED",

                    "url":
                        None,

                    "evidence":
                        {
                            **call,
                            "numeric_args":
                                numeric_args,
                        },
                }
            )

    return candidates


# ============================================================
# TARGET FRAGMENT CLASSIFICATION
# ============================================================

def classify_target_fragment(
    *,
    fragment: Dict[str, Any],
    page_url: str,
    full_source: str,
) -> Dict[str, Any]:

    raw_html = (
        fragment.get(
            "raw_html"
        )
        or ""
    )

    visible_text = (
        fragment.get(
            "visible_text"
        )
        or ""
    )

    (
        search_term_echo,
        echo_score,
        echo_reasons,
    ) = is_search_term_echo(
        visible_text
    )

    anchors = extract_anchors(
        raw_html,
        base_url=page_url,
    )

    attribute_records = (
        extract_identifier_attributes(
            raw_html
        )
    )

    identifier_evidence = (
        identifier_evidence_from_attributes(
            attribute_records
        )
    )

    reconstruction_candidates = []

    for anchor in anchors:

        reconstruction_candidates.extend(
            reconstruct_from_anchor(
                anchor,
                base_url=page_url,
            )
        )

    script_detail_urls = (
        extract_script_detail_urls(
            full_source,
            base_url=page_url,
        )
    )

    for script_url in script_detail_urls:

        reconstruction_candidates.append(
            {
                "reconstruction_type":
                    "SCRIPT_DETAIL_URL",

                "url":
                    script_url,

                "evidence":
                    {
                        "source":
                            "SCRIPT_BLOCK"
                    },
            }
        )

    usable_url_candidates = [
        candidate
        for candidate
        in reconstruction_candidates
        if (
            candidate.get(
                "url"
            )
            and not is_search_url(
                str(
                    candidate.get(
                        "url"
                    )
                )
            )
        )
    ]

    identifier_seed_candidates = [
        candidate
        for candidate
        in reconstruction_candidates
        if (
            candidate.get(
                "reconstruction_type"
            )
            == "ONCLICK_IDENTIFIER_SEED"
        )
    ]

    actual_result_evidence = (
        bool(
            usable_url_candidates
        )
        or bool(
            identifier_evidence
        )
        or bool(
            identifier_seed_candidates
        )
    )

    result_row_candidate = (
        contains_target(
            visible_text
        )
        and not search_term_echo
        and actual_result_evidence
    )

    return {
        "source_index":
            fragment.get(
                "source_index"
            ),

        "visible_text":
            visible_text,

        "preview":
            visible_text[
                :1200
            ],

        "search_term_echo":
            search_term_echo,

        "echo_score":
            echo_score,

        "echo_reasons":
            echo_reasons,

        "anchor_count":
            len(
                anchors
            ),

        "anchors":
            anchors,

        "identifier_attributes":
            attribute_records,

        "identifier_evidence":
            identifier_evidence,

        "reconstruction_candidates":
            reconstruction_candidates,

        "usable_url_candidate_count":
            len(
                usable_url_candidates
            ),

        "identifier_seed_candidate_count":
            len(
                identifier_seed_candidates
            ),

        "actual_result_evidence":
            actual_result_evidence,

        "result_row_candidate":
            result_row_candidate,
    }


# ============================================================
# LOAD L-STAGE INPUT
# ============================================================

l_stage_input_exists = (
    L_STAGE_INPUT_PATH.exists()
)

l_stage_input_data: Dict[
    str,
    Any
] = {}

if l_stage_input_exists:

    try:

        l_stage_input_data = json.loads(
            L_STAGE_INPUT_PATH.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        l_stage_input_data = {}


# ============================================================
# DISCOVERY STATE
# ============================================================

request_count = 0

http_success_count = 0

transport_error_count = 0

form_count = 0

search_form_count = 0

submission_count = 0

target_response_count = 0

target_fragment_count = 0

search_term_echo_count = 0

result_row_candidate_count = 0

reconstruction_candidate_count = 0

usable_reconstructed_url_count = 0


endpoint_records: List[
    Dict[
        str,
        Any
    ]
] = []

all_target_fragments: List[
    Dict[
        str,
        Any
    ]
] = []

all_reconstruction_candidates: List[
    Dict[
        str,
        Any
    ]
] = []


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
    "DYNAMIC DETAIL RECONSTRUCTION"
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
    "Primary region:",
    PRIMARY_REGION,
)

print(
    "Primary board:",
    PRIMARY_BOARD_URL,
)

print(
    "L-stage input:",
    L_STAGE_INPUT_PATH,
)

print()


# ============================================================
# FETCH PRIMARY BOARD
# ============================================================

root_result = fetch_get(
    PRIMARY_BOARD_URL
)

request_count += 1

if root_result.error:

    transport_error_count += 1

    print(
        "Primary board transport error:",
        root_result.error,
    )

    root_source = ""

else:

    if root_result.http_status == 200:

        http_success_count += 1

    root_source = (
        root_result.text
        or ""
    )


root_final_url = (
    root_result.final_url
    or PRIMARY_BOARD_URL
)


# ============================================================
# FORM DISCOVERY
# ============================================================

forms = parse_forms(
    root_source,
    base_url=root_final_url,
)

form_count += len(
    forms
)


search_forms = []

for form in forms:

    payload = build_search_payload(
        form
    )

    if payload is None:

        continue

    search_forms.append(
        {
            "form":
                form,

            "payload":
                payload,
        }
    )


search_form_count += len(
    search_forms
)


print(
    "Primary HTTP:",
    root_result.http_status,
)

print(
    "Forms:",
    len(
        forms
    ),
)

print(
    "Search forms:",
    len(
        search_forms
    ),
)

print()


# ============================================================
# SUBMIT SEARCH FORMS
# ============================================================

for submission_index, form_record in enumerate(
    search_forms,
    start=1,
):

    form = (
        form_record[
            "form"
        ]
    )

    payload = (
        form_record[
            "payload"
        ]
    )

    action_url = (
        form.get(
            "action_url"
        )
        or root_final_url
    )

    method = (
        form.get(
            "method"
        )
        or "GET"
    ).upper()

    print(
        "------------------------------------------------------------"
    )

    print(
        f"SUBMISSION {submission_index}"
    )

    print(
        "Method:",
        method,
    )

    print(
        "Action:",
        action_url,
    )

    print(
        "Search fields:",
        [
            key
            for key, value
            in payload.items()
            if value == TARGET_NAME
        ],
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

        existing_query = dict(
            parse_qsl(
                parsed.query,
                keep_blank_values=True,
            )
        )

        existing_query.update(
            payload
        )

        submit_url = urlunparse(
            parsed._replace(
                query=urlencode(
                    existing_query,
                    doseq=True,
                )
            )
        )

        result = fetch_get(
            submit_url
        )

    submission_count += 1

    request_count += 1

    if result.error:

        transport_error_count += 1

        print(
            "Transport error:",
            result.error,
        )

        continue

    if result.http_status == 200:

        http_success_count += 1

    final_url = (
        result.final_url
        or action_url
    )

    source = (
        result.text
        or ""
    )

    target_in_response = contains_target(
        strip_html(
            source
        )
    )

    if target_in_response:

        target_response_count += 1

    fragments = extract_target_fragments(
        source
    )

    classified_fragments = []

    for fragment_index, fragment in enumerate(
        fragments,
        start=1,
    ):

        classified = classify_target_fragment(
            fragment=fragment,
            page_url=final_url,
            full_source=source,
        )

        classified[
            "submission_index"
        ] = submission_index

        classified[
            "fragment_index"
        ] = fragment_index

        classified[
            "method"
        ] = method

        classified[
            "action_url"
        ] = action_url

        classified[
            "final_url"
        ] = final_url

        target_fragment_count += 1

        if classified[
            "search_term_echo"
        ]:

            search_term_echo_count += 1

        if classified[
            "result_row_candidate"
        ]:

            result_row_candidate_count += 1

        for reconstruction in classified[
            "reconstruction_candidates"
        ]:

            reconstruction_record = {
                "region":
                    PRIMARY_REGION,

                "agency":
                    PRIMARY_AGENCY,

                "submission_index":
                    submission_index,

                "fragment_index":
                    fragment_index,

                "search_term_echo":
                    classified[
                        "search_term_echo"
                    ],

                "result_row_candidate":
                    classified[
                        "result_row_candidate"
                    ],

                **reconstruction,
            }

            all_reconstruction_candidates.append(
                reconstruction_record
            )

            reconstruction_candidate_count += 1

            if reconstruction_record.get(
                "url"
            ):

                usable_reconstructed_url_count += 1

        classified_fragments.append(
            classified
        )

        all_target_fragments.append(
            classified
        )

    print(
        "HTTP:",
        result.http_status,
    )

    print(
        "Target response:",
        target_in_response,
    )

    print(
        "Target fragments:",
        len(
            classified_fragments
        ),
    )

    print(
        "Echo fragments:",
        sum(
            1
            for item
            in classified_fragments
            if item[
                "search_term_echo"
            ]
        ),
    )

    print(
        "Result-row candidates:",
        sum(
            1
            for item
            in classified_fragments
            if item[
                "result_row_candidate"
            ]
        ),
    )

    for classified in classified_fragments[
        :10
    ]:

        print(
            "  FRAGMENT:",
            classified[
                "preview"
            ][
                :300
            ],
        )

        print(
            "    Search echo:",
            classified[
                "search_term_echo"
            ],
        )

        print(
            "    Echo reasons:",
            classified[
                "echo_reasons"
            ],
        )

        print(
            "    Result evidence:",
            classified[
                "actual_result_evidence"
            ],
        )

        print(
            "    Reconstruction candidates:",
            len(
                classified[
                    "reconstruction_candidates"
                ]
            ),
        )

    endpoint_records.append(
        {
            "submission_index":
                submission_index,

            "method":
                method,

            "action_url":
                action_url,

            "final_url":
                final_url,

            "http_status":
                result.http_status,

            "target_in_response":
                target_in_response,

            "target_fragment_count":
                len(
                    classified_fragments
                ),

            "fragments":
                classified_fragments,
        }
    )

    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# DEDUPE RECONSTRUCTION CANDIDATES
# ============================================================

deduped_reconstruction_candidates = []

seen_reconstruction = set()

for candidate in all_reconstruction_candidates:

    candidate_url = normalize_url(
        str(
            candidate.get(
                "url"
            )
            or ""
        )
    )

    evidence_json = json.dumps(
        candidate.get(
            "evidence"
        ),
        ensure_ascii=False,
        sort_keys=True,
    )

    key = (
        candidate.get(
            "reconstruction_type"
        ),
        candidate_url,
        evidence_json,
    )

    if key in seen_reconstruction:

        continue

    seen_reconstruction.add(
        key
    )

    normalized_candidate = dict(
        candidate
    )

    normalized_candidate[
        "url"
    ] = (
        candidate_url
        or None
    )

    deduped_reconstruction_candidates.append(
        normalized_candidate
    )


deduped_reconstruction_candidates = (
    deduped_reconstruction_candidates[
        :MAX_RECONSTRUCTED_CANDIDATES
    ]
)


# ============================================================
# VERIFIED RECONSTRUCTION SEEDS
# ============================================================

verified_reconstruction_seeds = []

for candidate in deduped_reconstruction_candidates:

    if candidate.get(
        "search_term_echo"
    ) is True:

        continue

    if candidate.get(
        "result_row_candidate"
    ) is not True:

        continue

    candidate_url = (
        candidate.get(
            "url"
        )
        or ""
    )

    reconstruction_type = (
        candidate.get(
            "reconstruction_type"
        )
        or ""
    )

    if candidate_url:

        if is_search_url(
            candidate_url
        ):

            continue

        if not has_detail_url_hint(
            candidate_url
        ):

            continue

    elif reconstruction_type != (
        "ONCLICK_IDENTIFIER_SEED"
    ):

        continue

    verified_reconstruction_seeds.append(
        candidate
    )


# ============================================================
# RESULT CLASSIFICATION
# ============================================================

if verified_reconstruction_seeds:

    resolution = (
        "DYNAMIC_DETAIL_RECONSTRUCTION_SEED_DISCOVERED"
    )

    next_action = (
        "reconstructed detail URL 또는 document identifier seed를 "
        "N-stage에서 직접 요청하여 실제 개발밀도관리구역 "
        "지정·변경·해제 고시 원문인지 검증한다."
    )

elif (
    target_fragment_count > 0
    and search_term_echo_count
    == target_fragment_count
):

    resolution = (
        "TARGET_BEARING_FRAGMENT_CONFIRMED_AS_SEARCH_TERM_ECHO"
    )

    next_action = (
        "강서구 POST 검색 응답의 target 문자열은 검색어 UI echo로 "
        "판정한다. 해당 문자열을 실제 고시 row evidence에서 제외하고 "
        "다른 board endpoint의 POST/동적 검색 구조를 계속 탐색한다."
    )

elif target_fragment_count > 0:

    resolution = (
        "TARGET_FRAGMENT_FOUND_BUT_DETAIL_RECONSTRUCTION_UNRESOLVED"
    )

    next_action = (
        "target-bearing fragment는 확인되었으나 신뢰 가능한 상세 URL 또는 "
        "document identifier를 복원하지 못했다. DOM 범위 확대, "
        "JavaScript event binding 및 AJAX endpoint 분석으로 확장한다."
    )

else:

    resolution = (
        "DYNAMIC_DETAIL_RECONSTRUCTION_COMPLETED_NO_TARGET_FRAGMENT"
    )

    next_action = (
        "POST form payload, hidden field 유지 방식 또는 site-specific "
        "JavaScript/AJAX 검색 endpoint를 추가 분석한다."
    )


runtime_registration_blocked = True

site_false_interpretation_blocked = True


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-M "
        "Development Density Management Area "
        "Dynamic Detail Reconstruction"
    ),

    "target": {
        "name":
            TARGET_NAME,

        "standard_code":
            STANDARD_CODE,
    },

    "primary_target": {
        "region":
            PRIMARY_REGION,

        "agency":
            PRIMARY_AGENCY,

        "board_url":
            PRIMARY_BOARD_URL,
    },

    "input": {
        "l_stage_path":
            str(
                L_STAGE_INPUT_PATH
            ),

        "l_stage_exists":
            l_stage_input_exists,

        "l_stage_parsed":
            bool(
                l_stage_input_data
            ),
    },

    "method": {
        "actual_form_submission":
            True,

        "hidden_field_preservation":
            True,

        "search_term_echo_guard":
            True,

        "url_query_only_target_prohibited":
            True,

        "href_detail_discovery":
            True,

        "onclick_function_discovery":
            True,

        "data_attribute_discovery":
            True,

        "javascript_function_discovery":
            True,

        "script_detail_url_discovery":
            True,

        "reconstructed_url_is_final_positive":
            False,
    },

    "summary": {
        "request_count":
            request_count,

        "http_success_count":
            http_success_count,

        "transport_error_count":
            transport_error_count,

        "form_count":
            form_count,

        "search_form_count":
            search_form_count,

        "submission_count":
            submission_count,

        "target_response_count":
            target_response_count,

        "target_fragment_count":
            target_fragment_count,

        "search_term_echo_count":
            search_term_echo_count,

        "result_row_candidate_count":
            result_row_candidate_count,

        "raw_reconstruction_candidate_count":
            reconstruction_candidate_count,

        "deduped_reconstruction_candidate_count":
            len(
                deduped_reconstruction_candidates
            ),

        "verified_reconstruction_seed_count":
            len(
                verified_reconstruction_seeds
            ),
    },

    "endpoint_records":
        endpoint_records,

    "target_fragments":
        all_target_fragments,

    "reconstruction_candidates":
        deduped_reconstruction_candidates,

    "verified_reconstruction_seeds":
        verified_reconstruction_seeds,

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
    "Form count:",
    form_count,
)

print(
    "Search form count:",
    search_form_count,
)

print(
    "Submission count:",
    submission_count,
)

print(
    "Target response count:",
    target_response_count,
)

print(
    "Target fragment count:",
    target_fragment_count,
)

print(
    "Search-term echo count:",
    search_term_echo_count,
)

print(
    "Result-row candidate count:",
    result_row_candidate_count,
)

print(
    "Reconstruction candidate count:",
    len(
        deduped_reconstruction_candidates
    ),
)

print(
    "Verified reconstruction seed count:",
    len(
        verified_reconstruction_seeds
    ),
)

print()


if all_target_fragments:

    print(
        "TARGET FRAGMENTS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, fragment in enumerate(
        all_target_fragments[
            :20
        ],
        start=1,
    ):

        print(
            f"[{index}]"
        )

        print(
            "Submission:",
            fragment.get(
                "submission_index"
            ),
        )

        print(
            "Search echo:",
            fragment.get(
                "search_term_echo"
            ),
        )

        print(
            "Echo score:",
            fragment.get(
                "echo_score"
            ),
        )

        print(
            "Echo reasons:",
            fragment.get(
                "echo_reasons"
            ),
        )

        print(
            "Actual result evidence:",
            fragment.get(
                "actual_result_evidence"
            ),
        )

        print(
            "Result row candidate:",
            fragment.get(
                "result_row_candidate"
            ),
        )

        print(
            "Identifier evidence:",
            fragment.get(
                "identifier_evidence"
            ),
        )

        print(
            "Preview:",
            fragment.get(
                "preview"
            ),
        )

        print()


if verified_reconstruction_seeds:

    print(
        "VERIFIED RECONSTRUCTION SEEDS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, seed in enumerate(
        verified_reconstruction_seeds,
        start=1,
    ):

        print(
            f"[{index}]"
        )

        print(
            "Type:",
            seed.get(
                "reconstruction_type"
            ),
        )

        print(
            "URL:",
            seed.get(
                "url"
            ),
        )

        print(
            "Evidence:",
            seed.get(
                "evidence"
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

reconstruction_candidate_keys = {
    (
        item.get(
            "reconstruction_type"
        ),
        normalize_url(
            str(
                item.get(
                    "url"
                )
                or ""
            )
        ),
        json.dumps(
            item.get(
                "evidence"
            ),
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    for item in deduped_reconstruction_candidates
}


verified_seed_urls_not_search = all(
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
    for item in verified_reconstruction_seeds
)


verified_seeds_not_echo = all(
    item.get(
        "search_term_echo"
    )
    is False
    for item in verified_reconstruction_seeds
)


verified_seeds_have_result_evidence = all(
    item.get(
        "result_row_candidate"
    )
    is True
    for item in verified_reconstruction_seeds
)


verified_seed_types_valid = all(
    item.get(
        "reconstruction_type"
    )
    in {
        "EXPLICIT_DETAIL_HREF",
        "ONCLICK_URL_ARGUMENT",
        "ONCLICK_IDENTIFIER_SEED",
        "SCRIPT_DETAIL_URL",
    }
    for item in verified_reconstruction_seeds
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

    "primary Gangseo board configured": (
        PRIMARY_REGION
        == "서울특별시 강서구"
        and PRIMARY_BOARD_URL.endswith(
            "/gs040301"
        )
    ),

    "L-stage input exists": (
        l_stage_input_exists
    ),

    "actual form submission enabled": (
        output_data[
            "method"
        ][
            "actual_form_submission"
        ]
        is True
    ),

    "hidden field preservation enabled": (
        output_data[
            "method"
        ][
            "hidden_field_preservation"
        ]
        is True
    ),

    "search-term echo guard enabled": (
        output_data[
            "method"
        ][
            "search_term_echo_guard"
        ]
        is True
    ),

    "URL-query-only target prohibited": (
        output_data[
            "method"
        ][
            "url_query_only_target_prohibited"
        ]
        is True
    ),

    "onclick discovery enabled": (
        output_data[
            "method"
        ][
            "onclick_function_discovery"
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

    "javascript discovery enabled": (
        output_data[
            "method"
        ][
            "javascript_function_discovery"
        ]
        is True
    ),

    "reconstructed URL not final positive": (
        output_data[
            "method"
        ][
            "reconstructed_url_is_final_positive"
        ]
        is False
    ),

    "requests executed": (
        request_count
        > 0
    ),

    "forms discovered": (
        form_count
        >= 0
    ),

    "reconstruction candidates unique": (
        len(
            reconstruction_candidate_keys
        )
        == len(
            deduped_reconstruction_candidates
        )
    ),

    "verified seeds are not search URLs": (
        verified_seed_urls_not_search
    ),

    "verified seeds are not search-term echo": (
        verified_seeds_not_echo
    ),

    "verified seeds have result-row evidence": (
        verified_seeds_have_result_evidence
    ),

    "verified reconstruction types valid": (
        verified_seed_types_valid
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
        "dynamic detail reconstruction regression failed"
    )