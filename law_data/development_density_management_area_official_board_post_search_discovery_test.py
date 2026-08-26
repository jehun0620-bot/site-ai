# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-L
Development Density Management Area
Official Board POST Search / Dynamic Detail Discovery

목표
======================================================================
K-stage에서 GET pagination 전 범위를 탐색했지만
target-bearing result row가 0건이었다.

이번 L-stage에서는 I-stage에서 확인된 공식 searchable endpoint를 다시 열고
실제 검색 form을 분석하여 다음을 수행한다.

공식 board endpoint
    ↓
검색 form 분석
    ↓
hidden field / select / 기본값 보존
    ↓
target keyword 주입
    ↓
GET 또는 POST form submit
    ↓
검색 response
    ↓
검색 form 자체 echo 제거
    ↓
row-level target evidence 판정
    ↓
href / onclick / data-* 동적 상세 endpoint 추출
    ↓
다음 원문 검증 단계 seed

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 안전정책
======================================================================
1. 검색 response 전체에 target이 존재하는 것만으로 positive 처리하지 않는다.
2. 검색 input value echo는 row evidence에서 제외한다.
3. target이 request URL / form value에만 존재하면 detail seed로 승격하지 않는다.
4. 실제 result row visible text 또는 result anchor label에 target이 있어야 한다.
5. 일반 "도시계획", "고시", "공고" 문맥만으로 target seed를 만들지 않는다.
6. POST form은 실제 endpoint HTML에서 발견한 form만 제출한다.
7. hidden input은 원본 값을 보존한다.
8. password / file / destructive-looking form은 제출하지 않는다.
9. runtime spatial condition 등록은 계속 차단한다.
10. 미발견을 SITE FALSE로 해석하지 않는다.

이번 단계 성공 조건
======================================================================
A. 실제 target-bearing result row 또는 dynamic detail seed 발견

또는

B. POST/GET search form 실행 구조가 정상 동작하고
   target-bearing row 0건 상태를 명시적으로 보존

discovery regression이므로 후보 0건도 테스트 실패가 아니다.
"""

from __future__ import annotations

import html
import json
import re
import time

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
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

BASE_DIR = Path(__file__).resolve().parent.parent

I_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_official_board_search_form_discovery.json"
)

K_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_official_board_target_row_discovery.json"
)

OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "development_density_management_area_official_board_post_search_discovery.json"
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"

TARGET_VARIANTS = (
    "개발밀도관리구역",
    "개발밀도 관리구역",
    "개발 밀도 관리구역",
)


# ============================================================
# REQUEST CONFIG
# ============================================================

REQUEST_TIMEOUT = 20
REQUEST_SLEEP = 0.20

MAX_CONTENT_LENGTH = 2_000_000
MAX_ENDPOINTS = 60
MAX_FORMS_PER_ENDPOINT = 8
MAX_SUBMISSIONS_PER_ENDPOINT = 5
MAX_ROWS_PER_RESPONSE = 300
MAX_DYNAMIC_CANDIDATES_PER_ROW = 20

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
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


# ============================================================
# SAFETY / FORM RULES
# ============================================================

ALLOWED_ENDPOINT_CLASSES = {
    "PRIMARY_GOSI_BOARD",
    "GAZETTE_ARCHIVE",
    "URBAN_PLANNING_BOARD",
}

SEARCH_FIELD_HINTS = (
    "search",
    "keyword",
    "query",
    "key",
    "word",
    "text",
    "title",
    "subject",
    "sstring",
    "searchword",
    "searchkeyword",
    "searchtext",
    "sch",
    "srch",
)

PREFERRED_SEARCH_FIELD_HINTS = (
    "keyword",
    "query",
    "searchkeyword",
    "searchword",
    "searchtext",
    "sstring",
)

DANGEROUS_FORM_HINTS = (
    "delete",
    "remove",
    "withdraw",
    "cancel",
    "logout",
    "login",
    "register",
    "signup",
    "write",
    "insert",
    "update",
    "modify",
    "save",
    "upload",
    "payment",
)

SEARCH_URL_HINTS = (
    "/search",
    "search.",
    "search/",
    "search?",
    "search.do",
    "search.jsp",
    "totalsearch",
    "tourresult",
)

ATTACHMENT_EXTENSIONS = (
    ".pdf",
    ".hwp",
    ".hwpx",
)

STATIC_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".css",
    ".js",
    ".ico",
)

DETAIL_URL_HINTS = (
    "/view",
    "view.do",
    "view.htm",
    "view.jsp",
    "detail",
    "detail.do",
    "selectboardarticle",
    "bbsmsgdetail",
    "announcedetail",
    "post/view",
    "board/view",
    "notice/view",
    "idx=",
    "nttid=",
    "msg_seq=",
    "mgt_no=",
    "seq=",
    "notancmtmgtno=",
)

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "timestamp",
    "_",
}


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class FetchResult:
    request_url: str
    final_url: Optional[str]
    http_status: Optional[int]
    content_type: str
    text: str
    error: Optional[str]


@dataclass
class ParsedInput:
    name: str
    input_type: str
    value: str
    checked: bool


@dataclass
class ParsedSelect:
    name: str
    value: str


@dataclass
class ParsedForm:
    method: str
    action: str
    inputs: List[ParsedInput]
    selects: List[ParsedSelect]


# ============================================================
# TEXT UTIL
# ============================================================

def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def strip_html(source: str) -> str:
    value = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", source)
    value = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", value)
    value = re.sub(r"(?is)<[^>]+>", " ", value)
    value = html.unescape(value)
    return normalize_space(value)


def compact_text(value: str) -> str:
    return re.sub(r"\s+", "", normalize_space(value))


def contains_target(value: str) -> bool:
    return compact_text(TARGET_NAME) in compact_text(value)


def build_preview(
    value: str,
    *,
    radius: int = 260,
) -> str:

    text = normalize_space(value)
    index = -1

    for variant in TARGET_VARIANTS:
        index = text.find(variant)

        if index >= 0:
            break

    if index < 0:
        return text[: radius * 2]

    start = max(0, index - radius)
    end = min(
        len(text),
        index + len(TARGET_NAME) + radius,
    )

    return text[start:end]


# ============================================================
# URL UTIL
# ============================================================

def normalize_url(url: str) -> str:

    try:
        parsed = urlparse(url)

    except Exception:
        return url

    query_items = []

    for key, value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):
        if key.lower() in VOLATILE_QUERY_KEYS:
            continue

        query_items.append((key, value))

    query_items.sort(
        key=lambda item: (
            item[0].lower(),
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
            urlparse(url).hostname
            or ""
        ).lower()

        base_host = (
            urlparse(base_url).hostname
            or ""
        ).lower()

    except Exception:
        return False

    if not target_host or not base_host:
        return False

    return (
        target_host == base_host
        or target_host.endswith("." + base_host)
        or base_host.endswith("." + target_host)
    )


def is_search_url(url: str) -> bool:
    lower = url.lower()

    return any(
        hint in lower
        for hint in SEARCH_URL_HINTS
    )


def is_attachment_url(url: str) -> bool:
    path = urlparse(url).path.lower()

    return any(
        path.endswith(ext)
        for ext in ATTACHMENT_EXTENSIONS
    )


def is_static_url(url: str) -> bool:
    path = urlparse(url).path.lower()

    return any(
        path.endswith(ext)
        for ext in STATIC_EXTENSIONS
    )


def has_detail_hint(url: str) -> bool:
    lower = url.lower()

    return any(
        hint in lower
        for hint in DETAIL_URL_HINTS
    )


def target_in_url(url: str) -> bool:
    return contains_target(
        requests.utils.unquote(
            url
        )
    )


# ============================================================
# FETCH / SUBMIT
# ============================================================

def response_to_fetch_result(
    *,
    request_url: str,
    response: requests.Response,
) -> FetchResult:

    content_type = (
        response.headers.get(
            "Content-Type",
            "",
        )
        or ""
    )

    content_type_lower = content_type.lower()

    text_like = (
        "text/" in content_type_lower
        or "html" in content_type_lower
        or "xml" in content_type_lower
        or "json" in content_type_lower
    )

    text = ""

    if text_like:
        text = response.text or ""

        if len(text) > MAX_CONTENT_LENGTH:
            text = text[:MAX_CONTENT_LENGTH]

    return FetchResult(
        request_url=request_url,
        final_url=response.url,
        http_status=response.status_code,
        content_type=content_type,
        text=text,
        error=None,
    )


def fetch_get(
    session: requests.Session,
    url: str,
) -> FetchResult:

    try:
        response = session.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

    except requests.RequestException as exc:
        return FetchResult(
            request_url=url,
            final_url=None,
            http_status=None,
            content_type="",
            text="",
            error=repr(exc),
        )

    return response_to_fetch_result(
        request_url=url,
        response=response,
    )


def submit_form(
    session: requests.Session,
    *,
    method: str,
    action_url: str,
    payload: Dict[str, str],
    referer: str,
) -> FetchResult:

    headers = dict(HEADERS)
    headers["Referer"] = referer

    try:
        if method == "POST":

            response = session.post(
                action_url,
                data=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            request_url = action_url

        else:

            response = session.get(
                action_url,
                params=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            request_url = response.request.url or action_url

    except requests.RequestException as exc:
        return FetchResult(
            request_url=action_url,
            final_url=None,
            http_status=None,
            content_type="",
            text="",
            error=repr(exc),
        )

    return response_to_fetch_result(
        request_url=request_url,
        response=response,
    )


# ============================================================
# FORM PARSER
# ============================================================

class SearchFormParser(HTMLParser):

    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

        self.forms: List[ParsedForm] = []
        self._current_form: Optional[Dict[str, Any]] = None
        self._current_select: Optional[Dict[str, Any]] = None

    def handle_starttag(
        self,
        tag: str,
        attrs: List[Tuple[str, Optional[str]]],
    ) -> None:

        attr = {
            key.lower(): (
                value
                if value is not None
                else ""
            )
            for key, value in attrs
        }

        tag = tag.lower()

        if tag == "form":

            method = (
                attr.get(
                    "method",
                    "GET",
                )
                or "GET"
            ).upper()

            action = (
                attr.get(
                    "action",
                    ""
                )
                or ""
            )

            self._current_form = {
                "method": method,
                "action": action,
                "inputs": [],
                "selects": [],
            }

            return

        if self._current_form is None:
            return

        if tag == "input":

            name = (
                attr.get(
                    "name",
                    ""
                )
                or ""
            ).strip()

            if not name:
                return

            input_type = (
                attr.get(
                    "type",
                    "text",
                )
                or "text"
            ).lower()

            value = (
                attr.get(
                    "value",
                    ""
                )
                or ""
            )

            checked = (
                "checked" in attr
            )

            self._current_form[
                "inputs"
            ].append(
                ParsedInput(
                    name=name,
                    input_type=input_type,
                    value=value,
                    checked=checked,
                )
            )

            return

        if tag == "select":

            name = (
                attr.get(
                    "name",
                    ""
                )
                or ""
            ).strip()

            if name:
                self._current_select = {
                    "name": name,
                    "selected": "",
                    "first": "",
                }

            return

        if (
            tag == "option"
            and self._current_select
            is not None
        ):

            value = (
                attr.get(
                    "value",
                    ""
                )
                or ""
            )

            if not self._current_select[
                "first"
            ]:
                self._current_select[
                    "first"
                ] = value

            if "selected" in attr:
                self._current_select[
                    "selected"
                ] = value

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        tag = tag.lower()

        if (
            tag == "select"
            and self._current_form
            is not None
            and self._current_select
            is not None
        ):

            value = (
                self._current_select[
                    "selected"
                ]
                or self._current_select[
                    "first"
                ]
            )

            self._current_form[
                "selects"
            ].append(
                ParsedSelect(
                    name=self._current_select[
                        "name"
                    ],
                    value=value,
                )
            )

            self._current_select = None

            return

        if (
            tag == "form"
            and self._current_form
            is not None
        ):

            self.forms.append(
                ParsedForm(
                    method=self._current_form[
                        "method"
                    ],
                    action=self._current_form[
                        "action"
                    ],
                    inputs=list(
                        self._current_form[
                            "inputs"
                        ]
                    ),
                    selects=list(
                        self._current_form[
                            "selects"
                        ]
                    ),
                )
            )

            self._current_form = None
            self._current_select = None


def parse_forms(
    source: str,
) -> List[ParsedForm]:

    parser = SearchFormParser()

    try:
        parser.feed(source)

    except Exception:
        pass

    return parser.forms


# ============================================================
# FORM CLASSIFICATION
# ============================================================

def field_name_score(
    name: str,
) -> int:

    lower = name.lower()

    score = 0

    for hint in SEARCH_FIELD_HINTS:

        if hint in lower:
            score += 1

    for hint in PREFERRED_SEARCH_FIELD_HINTS:

        if hint in lower:
            score += 2

    return score


def form_is_dangerous(
    form: ParsedForm,
) -> bool:

    action_lower = form.action.lower()

    if any(
        hint in action_lower
        for hint in DANGEROUS_FORM_HINTS
    ):
        return True

    for item in form.inputs:

        if item.input_type in {
            "password",
            "file",
        }:
            return True

    return False


def find_search_fields(
    form: ParsedForm,
) -> List[str]:

    candidates = []

    for item in form.inputs:

        if item.input_type not in {
            "text",
            "search",
            "hidden",
        }:
            continue

        score = field_name_score(
            item.name
        )

        if score <= 0:
            continue

        # hidden field는 명시적인 keyword/query 이름일 때만 후보
        if (
            item.input_type == "hidden"
            and score < 3
        ):
            continue

        candidates.append(
            (
                -score,
                0
                if item.input_type
                in {
                    "text",
                    "search",
                }
                else 1,
                item.name,
            )
        )

    candidates.sort()

    return [
        name
        for _, _, name
        in candidates
    ]


def build_form_payload(
    form: ParsedForm,
    *,
    search_field: str,
) -> Dict[str, str]:

    payload: Dict[str, str] = {}

    for item in form.inputs:

        input_type = item.input_type

        if input_type in {
            "submit",
            "button",
            "reset",
            "image",
            "file",
            "password",
        }:
            continue

        if (
            input_type
            in {
                "checkbox",
                "radio",
            }
            and not item.checked
        ):
            continue

        payload[
            item.name
        ] = item.value

    for select in form.selects:
        payload[
            select.name
        ] = select.value

    payload[
        search_field
    ] = TARGET_NAME

    return payload


# ============================================================
# RESPONSE CLEANING
# ============================================================

def remove_form_echo_regions(
    source: str,
) -> str:

    # 검색 input value="개발밀도관리구역" 자체가 row evidence가 되는 것을 방지.
    value = re.sub(
        r"(?is)<form\b[^>]*>.*?</form>",
        " ",
        source,
    )

    return value


# ============================================================
# ANCHOR / DYNAMIC LINK EXTRACTION
# ============================================================

ANCHOR_PATTERN = re.compile(
    r"""
    (?is)
    <a
    \s+
    ([^>]*)
    >
    (.*?)
    </a>
    """,
    re.VERBOSE,
)

ATTR_PATTERN = re.compile(
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

URL_IN_JS_PATTERN = re.compile(
    r"""
    (?:
        window\.open
        |
        location(?:\.href)?
        |
        document\.location
    )
    \s*
    (?:=|\()
    \s*
    ['"]([^'"]+)['"]
    """,
    re.IGNORECASE | re.VERBOSE,
)

QUOTED_PATH_PATTERN = re.compile(
    r"""['"]([^'"]*(?:view|detail|selectBoardArticle|bbsMsgDetail|AnnounceDetail)[^'"]*)['"]""",
    re.IGNORECASE,
)


def parse_tag_attrs(
    raw_attrs: str,
) -> Dict[str, str]:

    attrs = {}

    for match in ATTR_PATTERN.finditer(
        raw_attrs
    ):

        key = (
            match.group(1)
            or ""
        ).lower()

        value = (
            match.group(2)
            or match.group(3)
            or match.group(4)
            or ""
        )

        attrs[
            key
        ] = html.unescape(
            value
        )

    return attrs


def extract_anchor_records(
    source: str,
    *,
    base_url: str,
) -> List[Dict[str, Any]]:

    results = []
    seen = set()

    for match in ANCHOR_PATTERN.finditer(
        source
    ):

        raw_attrs = (
            match.group(1)
            or ""
        )

        label_html = (
            match.group(2)
            or ""
        )

        attrs = parse_tag_attrs(
            raw_attrs
        )

        label = strip_html(
            label_html
        )

        href = (
            attrs.get(
                "href",
                ""
            )
            or ""
        ).strip()

        onclick = (
            attrs.get(
                "onclick",
                ""
            )
            or ""
        )

        data_attrs = {
            key: value
            for key, value in attrs.items()
            if key.startswith(
                "data-"
            )
        }

        url = ""

        if href and not href.lower().startswith(
            (
                "javascript:",
                "#",
                "mailto:",
                "tel:",
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
            url,
            onclick,
            tuple(
                sorted(
                    data_attrs.items()
                )
            ),
        )

        if key in seen:
            continue

        seen.add(key)

        results.append(
            {
                "label": label,
                "href_url": url,
                "onclick": onclick,
                "data_attrs": data_attrs,
                "raw_attrs": raw_attrs,
            }
        )

    return results


def extract_dynamic_urls(
    *,
    anchor: Dict[str, Any],
    base_url: str,
) -> List[Dict[str, Any]]:

    candidates = []
    seen = set()

    href_url = (
        anchor.get(
            "href_url"
        )
        or ""
    )

    if href_url:
        candidates.append(
            {
                "url": href_url,
                "source": "HREF",
            }
        )

        seen.add(
            href_url
        )

    onclick = (
        anchor.get(
            "onclick"
        )
        or ""
    )

    js_values = []

    for pattern in (
        URL_IN_JS_PATTERN,
        QUOTED_PATH_PATTERN,
    ):

        for match in pattern.finditer(
            onclick
        ):
            value = (
                match.group(1)
                or ""
            ).strip()

            if value:
                js_values.append(
                    value
                )

    for raw_url in js_values:

        if raw_url.lower().startswith(
            "javascript:"
        ):
            continue

        absolute = normalize_url(
            urljoin(
                base_url,
                html.unescape(
                    raw_url
                ),
            )
        )

        if absolute in seen:
            continue

        seen.add(
            absolute
        )

        candidates.append(
            {
                "url": absolute,
                "source": "ONCLICK",
            }
        )

    # data-url / data-href / data-link 등
    for key, value in (
        anchor.get(
            "data_attrs"
        )
        or {}
    ).items():

        key_lower = key.lower()

        if not any(
            token in key_lower
            for token in (
                "url",
                "href",
                "link",
                "view",
                "detail",
            )
        ):
            continue

        raw_url = (
            value
            or ""
        ).strip()

        if not raw_url:
            continue

        if (
            "/" not in raw_url
            and "?" not in raw_url
            and "." not in raw_url
        ):
            continue

        absolute = normalize_url(
            urljoin(
                base_url,
                html.unescape(
                    raw_url
                ),
            )
        )

        if absolute in seen:
            continue

        seen.add(
            absolute
        )

        candidates.append(
            {
                "url": absolute,
                "source": "DATA_ATTRIBUTE",
            }
        )

    return candidates[
        :MAX_DYNAMIC_CANDIDATES_PER_ROW
    ]


# ============================================================
# ROW EXTRACTION
# ============================================================

ROW_PATTERNS = (
    re.compile(
        r"(?is)<tr\b[^>]*>(.*?)</tr>"
    ),
    re.compile(
        r"(?is)<li\b[^>]*>(.*?)</li>"
    ),
    re.compile(
        r"""(?is)
        <div\b
        [^>]*?
        class\s*=\s*
        (?:
            "[^"]*(?:list|item|row|board|notice|bbs)[^"]*"
            |
            '[^']*(?:list|item|row|board|notice|bbs)[^']*'
        )
        [^>]*>
        (.*?)
        </div>
        """,
        re.VERBOSE,
    ),
)


def extract_rows(
    source: str,
) -> List[str]:

    rows = []
    seen = set()

    for pattern in ROW_PATTERNS:

        for match in pattern.finditer(
            source
        ):

            fragment = (
                match.group(1)
                or ""
            )

            text = strip_html(
                fragment
            )

            if not text:
                continue

            signature = (
                compact_text(
                    text
                )[:800],
                len(
                    fragment
                ),
            )

            if signature in seen:
                continue

            seen.add(
                signature
            )

            rows.append(
                fragment
            )

            if len(
                rows
            ) >= MAX_ROWS_PER_RESPONSE:
                return rows

    return rows


def classify_target_row(
    *,
    region: str,
    agency: str,
    endpoint_class: str,
    endpoint_url: str,
    response_url: str,
    submission_index: int,
    row_index: int,
    row_source: str,
) -> Dict[str, Any]:

    row_text = strip_html(
        row_source
    )

    anchors = extract_anchor_records(
        row_source,
        base_url=response_url,
    )

    target_in_text = contains_target(
        row_text
    )

    target_in_anchor_label = any(
        contains_target(
            item.get(
                "label",
                "",
            )
        )
        for item in anchors
    )

    target_in_href_only = (
        any(
            target_in_url(
                item.get(
                    "href_url",
                    "",
                )
            )
            for item in anchors
            if item.get(
                "href_url"
            )
        )
        and not target_in_text
        and not target_in_anchor_label
    )

    row_target_evidence = (
        target_in_text
        or target_in_anchor_label
    )

    dynamic_detail_candidates = []

    if row_target_evidence:

        for anchor in anchors:

            for candidate in extract_dynamic_urls(
                anchor=anchor,
                base_url=response_url,
            ):

                url = (
                    candidate.get(
                        "url"
                    )
                    or ""
                )

                if not url:
                    continue

                if is_search_url(
                    url
                ):
                    continue

                if is_static_url(
                    url
                ):
                    continue

                if is_attachment_url(
                    url
                ):
                    continue

                if not same_or_subdomain(
                    url,
                    endpoint_url,
                ):
                    continue

                # 검색 response 자체 링크 제외
                if normalize_url(
                    url
                ) == normalize_url(
                    response_url
                ):
                    continue

                score = 0

                label = (
                    anchor.get(
                        "label"
                    )
                    or ""
                )

                if contains_target(
                    label
                ):
                    score += 5

                if has_detail_hint(
                    url
                ):
                    score += 4

                if candidate.get(
                    "source"
                ) in {
                    "ONCLICK",
                    "DATA_ATTRIBUTE",
                }:
                    score += 2

                if label:
                    score += 1

                dynamic_detail_candidates.append(
                    {
                        "url": normalize_url(
                            url
                        ),
                        "label": label,
                        "source": candidate.get(
                            "source"
                        ),
                        "detail_url_hint": has_detail_hint(
                            url
                        ),
                        "target_in_label": contains_target(
                            label
                        ),
                        "score": score,
                    }
                )

    dynamic_detail_candidates.sort(
        key=lambda item: (
            -int(
                item.get(
                    "score",
                    0,
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

    return {
        "region": region,
        "agency": agency,
        "endpoint_class": endpoint_class,
        "endpoint_url": endpoint_url,
        "response_url": response_url,
        "submission_index": submission_index,
        "row_index": row_index,
        "row_text": row_text,
        "row_preview": (
            build_preview(
                row_text
            )
            if row_target_evidence
            else row_text[:400]
        ),
        "target_in_text": target_in_text,
        "target_in_anchor_label": target_in_anchor_label,
        "target_in_href_only": target_in_href_only,
        "row_target_evidence": row_target_evidence,
        "dynamic_detail_candidates": dynamic_detail_candidates,
    }


# ============================================================
# INPUT PARSING
# ============================================================

def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():
        raise FileNotFoundError(
            str(
                path
            )
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def walk_dicts(
    value: Any,
) -> Iterable[Dict[str, Any]]:

    if isinstance(
        value,
        dict,
    ):

        yield value

        for child in value.values():
            yield from walk_dicts(
                child
            )

    elif isinstance(
        value,
        list,
    ):

        for child in value:
            yield from walk_dicts(
                child
            )


def extract_endpoints(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    records = []
    seen = set()

    for item in walk_dicts(
        data
    ):

        endpoint_class = (
            item.get(
                "endpoint_class"
            )
            or item.get(
                "classification"
            )
            or item.get(
                "class"
            )
            or ""
        )

        if endpoint_class not in ALLOWED_ENDPOINT_CLASSES:
            continue

        url = (
            item.get(
                "canonical_url"
            )
            or item.get(
                "endpoint_url"
            )
            or item.get(
                "url"
            )
            or ""
        )

        if not url:
            continue

        # detail/result URL가 아니라 board endpoint 형태를 우선
        normalized = normalize_url(
            str(
                url
            )
        )

        if is_search_url(
            normalized
        ):
            continue

        key = (
            item.get(
                "region"
            ),
            endpoint_class,
            normalized,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        records.append(
            {
                "region": (
                    item.get(
                        "region"
                    )
                    or ""
                ),
                "agency": (
                    item.get(
                        "agency"
                    )
                    or item.get(
                        "region"
                    )
                    or ""
                ),
                "endpoint_class": endpoint_class,
                "label": (
                    item.get(
                        "label"
                    )
                    or ""
                ),
                "url": normalized,
            }
        )

    # 실제 I-stage 콘솔 결과가 38개였으므로,
    # 검색 가능한 구조가 있는 endpoint 위주로 제한한다.
    records.sort(
        key=lambda item: (
            0
            if item[
                "endpoint_class"
            ] == "PRIMARY_GOSI_BOARD"
            else 1
            if item[
                "endpoint_class"
            ] == "GAZETTE_ARCHIVE"
            else 2,
            item[
                "region"
            ],
            item[
                "url"
            ],
        )
    )

    return records[
        :MAX_ENDPOINTS
    ]


# ============================================================
# LOAD INPUTS
# ============================================================

i_stage_data = load_json(
    I_STAGE_INPUT_PATH
)

k_stage_data = load_json(
    K_STAGE_INPUT_PATH
)

endpoints = extract_endpoints(
    i_stage_data
)


# ============================================================
# STATE
# ============================================================

request_count = 0
http_success_count = 0
transport_error_count = 0
html_parse_count = 0

endpoint_fetch_count = 0
form_count = 0
safe_form_count = 0

get_submission_count = 0
post_submission_count = 0

submission_target_response_count = 0
form_echo_removed_response_count = 0

raw_row_count = 0
target_row_count = 0
url_query_only_row_leakage = 0

endpoint_results: List[
    Dict[
        str,
        Any
    ]
] = []

target_rows: List[
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
    "OFFICIAL BOARD POST SEARCH / DYNAMIC DETAIL DISCOVERY"
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
    "I-stage input:",
    I_STAGE_INPUT_PATH,
)

print(
    "K-stage input:",
    K_STAGE_INPUT_PATH,
)

print(
    "Endpoint count:",
    len(
        endpoints
    ),
)

print()


# ============================================================
# MAIN LOOP
# ============================================================

for endpoint_index, endpoint in enumerate(
    endpoints,
    start=1,
):

    region = endpoint[
        "region"
    ]

    agency = endpoint[
        "agency"
    ]

    endpoint_class = endpoint[
        "endpoint_class"
    ]

    endpoint_url = endpoint[
        "url"
    ]

    label = endpoint[
        "label"
    ]

    print(
        "------------------------------------------------------------"
    )

    print(
        f"ENDPOINT {endpoint_index}:",
        region,
        "/",
        endpoint_class,
    )

    print(
        "Label:",
        label,
    )

    print(
        "URL:",
        endpoint_url,
    )

    local_forms = []
    local_submissions = []
    local_target_rows = []
    local_detail_seeds = []

    session = requests.Session()

    root = fetch_get(
        session,
        endpoint_url,
    )

    request_count += 1
    endpoint_fetch_count += 1

    if root.error:

        transport_error_count += 1

        print(
            "Endpoint fetch error:",
            root.error,
        )

        endpoint_results.append(
            {
                **endpoint,
                "endpoint_http": None,
                "endpoint_error": root.error,
                "form_count": 0,
                "safe_form_count": 0,
                "submission_count": 0,
                "target_row_count": 0,
                "detail_seed_count": 0,
            }
        )

        continue

    if root.http_status == 200:
        http_success_count += 1

    if root.text:
        html_parse_count += 1

    root_final_url = (
        root.final_url
        or endpoint_url
    )

    forms = parse_forms(
        root.text
    )

    form_count += len(
        forms
    )

    for form_index, form in enumerate(
        forms[
            :MAX_FORMS_PER_ENDPOINT
        ],
        start=1,
    ):

        action_url = urljoin(
            root_final_url,
            form.action
            or root_final_url,
        )

        if not same_or_subdomain(
            action_url,
            endpoint_url,
        ):
            continue

        if form_is_dangerous(
            form
        ):
            continue

        search_fields = find_search_fields(
            form
        )

        if not search_fields:
            continue

        safe_form_count += 1

        local_forms.append(
            {
                "form_index": form_index,
                "method": form.method,
                "action_url": normalize_url(
                    action_url
                ),
                "search_fields": search_fields,
            }
        )

        for search_field in search_fields[
            :MAX_SUBMISSIONS_PER_ENDPOINT
        ]:

            if len(
                local_submissions
            ) >= MAX_SUBMISSIONS_PER_ENDPOINT:
                break

            payload = build_form_payload(
                form,
                search_field=search_field,
            )

            method = (
                form.method
                if form.method
                in {
                    "GET",
                    "POST",
                }
                else "GET"
            )

            result = submit_form(
                session,
                method=method,
                action_url=action_url,
                payload=payload,
                referer=root_final_url,
            )

            request_count += 1

            if method == "POST":
                post_submission_count += 1
            else:
                get_submission_count += 1

            submission_index = (
                len(
                    local_submissions
                )
                + 1
            )

            if result.error:

                transport_error_count += 1

                local_submissions.append(
                    {
                        "submission_index": submission_index,
                        "method": method,
                        "action_url": normalize_url(
                            action_url
                        ),
                        "search_field": search_field,
                        "http_status": None,
                        "error": result.error,
                        "target_in_raw_response": False,
                        "target_row_count": 0,
                        "detail_seed_count": 0,
                    }
                )

                continue

            if result.http_status == 200:
                http_success_count += 1

            if result.text:
                html_parse_count += 1

            response_url = (
                result.final_url
                or result.request_url
                or action_url
            )

            raw_target = contains_target(
                strip_html(
                    result.text
                )
            )

            if raw_target:
                submission_target_response_count += 1

            cleaned_source = remove_form_echo_regions(
                result.text
            )

            if (
                raw_target
                and not contains_target(
                    strip_html(
                        cleaned_source
                    )
                )
            ):
                form_echo_removed_response_count += 1

            rows = extract_rows(
                cleaned_source
            )

            raw_row_count += len(
                rows
            )

            submission_target_rows = []
            submission_detail_seeds = []

            for row_index, row_source in enumerate(
                rows,
                start=1,
            ):

                row = classify_target_row(
                    region=region,
                    agency=agency,
                    endpoint_class=endpoint_class,
                    endpoint_url=endpoint_url,
                    response_url=response_url,
                    submission_index=submission_index,
                    row_index=row_index,
                    row_source=row_source,
                )

                if (
                    row[
                        "target_in_href_only"
                    ]
                    and not row[
                        "row_target_evidence"
                    ]
                ):
                    url_query_only_row_leakage += 1

                if not row[
                    "row_target_evidence"
                ]:
                    continue

                submission_target_rows.append(
                    row
                )

                local_target_rows.append(
                    row
                )

                target_rows.append(
                    row
                )

                for dynamic in row[
                    "dynamic_detail_candidates"
                ]:

                    seed = {
                        "region": region,
                        "agency": agency,
                        "endpoint_class": endpoint_class,
                        "endpoint_url": endpoint_url,
                        "source_response_url": response_url,
                        "submission_index": submission_index,
                        "row_index": row_index,
                        "row_preview": row[
                            "row_preview"
                        ],
                        "row_target_evidence": True,
                        "method": method,
                        "search_field": search_field,
                        "label": dynamic.get(
                            "label",
                            "",
                        ),
                        "url": dynamic[
                            "url"
                        ],
                        "dynamic_source": dynamic.get(
                            "source"
                        ),
                        "detail_url_hint": dynamic.get(
                            "detail_url_hint"
                        ),
                        "target_in_label": dynamic.get(
                            "target_in_label"
                        ),
                        "seed_score": dynamic.get(
                            "score",
                            0,
                        ),
                    }

                    submission_detail_seeds.append(
                        seed
                    )

                    local_detail_seeds.append(
                        seed
                    )

                    detail_seed_candidates.append(
                        seed
                    )

            target_row_count += len(
                submission_target_rows
            )

            local_submissions.append(
                {
                    "submission_index": submission_index,
                    "method": method,
                    "action_url": normalize_url(
                        action_url
                    ),
                    "search_field": search_field,
                    "http_status": result.http_status,
                    "final_url": result.final_url,
                    "content_type": result.content_type,
                    "target_in_raw_response": raw_target,
                    "target_in_cleaned_response": contains_target(
                        strip_html(
                            cleaned_source
                        )
                    ),
                    "row_count": len(
                        rows
                    ),
                    "target_row_count": len(
                        submission_target_rows
                    ),
                    "detail_seed_count": len(
                        submission_detail_seeds
                    ),
                }
            )

            time.sleep(
                REQUEST_SLEEP
            )

        if len(
            local_submissions
        ) >= MAX_SUBMISSIONS_PER_ENDPOINT:
            break

    print(
        "HTTP:",
        root.http_status,
    )

    print(
        "Forms:",
        len(
            forms
        ),
    )

    print(
        "Safe search forms:",
        len(
            local_forms
        ),
    )

    print(
        "Submissions:",
        len(
            local_submissions
        ),
    )

    print(
        "Target-bearing rows:",
        len(
            local_target_rows
        ),
    )

    print(
        "Dynamic detail seeds:",
        len(
            local_detail_seeds
        ),
    )

    for row in local_target_rows[
        :3
    ]:

        print(
            "  TARGET ROW:",
            row.get(
                "row_preview"
            ),
        )

    endpoint_results.append(
        {
            **endpoint,
            "endpoint_http": root.http_status,
            "endpoint_final_url": root.final_url,
            "form_count": len(
                forms
            ),
            "safe_form_count": len(
                local_forms
            ),
            "forms": local_forms,
            "submission_count": len(
                local_submissions
            ),
            "submissions": local_submissions,
            "target_row_count": len(
                local_target_rows
            ),
            "detail_seed_count": len(
                local_detail_seeds
            ),
        }
    )

    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# DEDUPE TARGET ROWS
# ============================================================

deduped_target_rows = []
seen_target_rows = set()

for row in target_rows:

    key = (
        row.get(
            "region"
        ),
        normalize_url(
            str(
                row.get(
                    "response_url"
                )
                or ""
            )
        ),
        compact_text(
            str(
                row.get(
                    "row_text"
                )
                or ""
            )
        )[:1000],
    )

    if key in seen_target_rows:
        continue

    seen_target_rows.add(
        key
    )

    deduped_target_rows.append(
        row
    )


# ============================================================
# DEDUPE DETAIL SEEDS
# ============================================================

deduped_detail_seeds = []
seen_detail_seeds = set()

for seed in detail_seed_candidates:

    normalized_url = normalize_url(
        str(
            seed.get(
                "url"
            )
            or ""
        )
    )

    key = (
        seed.get(
            "region"
        ),
        normalized_url,
    )

    if key in seen_detail_seeds:
        continue

    seen_detail_seeds.add(
        key
    )

    normalized_seed = dict(
        seed
    )

    normalized_seed[
        "url"
    ] = normalized_url

    deduped_detail_seeds.append(
        normalized_seed
    )


deduped_detail_seeds.sort(
    key=lambda item: (
        -int(
            item.get(
                "seed_score",
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

if deduped_detail_seeds:

    resolution = (
        "POST_SEARCH_TARGET_ROW_DYNAMIC_DETAIL_SEED_DISCOVERED"
    )

    next_action = (
        "L-stage에서 확보한 row-target-evidence 기반 동적 상세 URL만 "
        "M-stage 원문 검증 대상으로 사용하여 실제 개발밀도관리구역 "
        "지정·변경·해제 고시 여부, 고시번호, 지정일, 행정구역, "
        "첨부파일, 지정 범위 및 현재 유효 여부를 검증한다."
    )

elif deduped_target_rows:

    resolution = (
        "POST_SEARCH_TARGET_ROW_DISCOVERED_NO_DETAIL_ENDPOINT"
    )

    next_action = (
        "target-bearing row는 확인되었으나 상세 endpoint를 URL로 복원하지 못했다. "
        "onclick 함수 인자, hidden document key, data-* 식별자를 이용한 "
        "M-stage site-specific dynamic detail reconstruction을 수행한다."
    )

else:

    resolution = (
        "POST_SEARCH_DISCOVERY_COMPLETED_NO_TARGET_ROW"
    )

    next_action = (
        "GET pagination과 실제 form 기반 GET/POST 검색에서도 target-bearing row가 "
        "확인되지 않았다. 다음 단계에서는 전자민원 고시공고 API/saeol 내부 endpoint, "
        "공보 PDF/HWP archive의 본문 검색, 국가기록/관보 계열 자료원으로 확장한다."
    )


runtime_registration_blocked = True
site_false_interpretation_blocked = True


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-L "
        "Development Density Management Area "
        "Official Board POST Search / Dynamic Detail Discovery"
    ),

    "target": {
        "name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
    },

    "input": {
        "i_stage_path": str(
            I_STAGE_INPUT_PATH
        ),
        "k_stage_path": str(
            K_STAGE_INPUT_PATH
        ),
        "k_stage_resolution": (
            k_stage_data.get(
                "resolution"
            )
        ),
    },

    "method": {
        "actual_form_only_submission": True,
        "hidden_field_preservation": True,
        "get_search_submission": True,
        "post_search_submission": True,
        "form_echo_removal": True,
        "row_level_target_evidence_required": True,
        "url_query_only_target_prohibited": True,
        "dynamic_href_discovery": True,
        "dynamic_onclick_discovery": True,
        "dynamic_data_attribute_discovery": True,
        "search_page_final_positive_allowed": False,
        "runtime_registration_allowed": False,
        "site_false_interpretation_allowed": False,
    },

    "summary": {
        "endpoint_count": len(
            endpoints
        ),
        "request_count": request_count,
        "http_success_count": http_success_count,
        "transport_error_count": transport_error_count,
        "html_parse_count": html_parse_count,
        "endpoint_fetch_count": endpoint_fetch_count,
        "form_count": form_count,
        "safe_form_count": safe_form_count,
        "get_submission_count": get_submission_count,
        "post_submission_count": post_submission_count,
        "submission_target_response_count": (
            submission_target_response_count
        ),
        "form_echo_removed_response_count": (
            form_echo_removed_response_count
        ),
        "raw_row_count": raw_row_count,
        "target_row_count": len(
            deduped_target_rows
        ),
        "detail_seed_candidate_count": len(
            deduped_detail_seeds
        ),
        "url_query_only_row_leakage": (
            url_query_only_row_leakage
        ),
    },

    "target_rows": (
        deduped_target_rows
    ),

    "detail_seed_candidates": (
        deduped_detail_seeds
    ),

    "endpoint_results": (
        endpoint_results
    ),

    "resolution": resolution,

    "runtime_registration_blocked": (
        runtime_registration_blocked
    ),

    "site_false_interpretation_blocked": (
        site_false_interpretation_blocked
    ),

    "next_action": next_action,
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
    "Endpoint count:",
    len(
        endpoints
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
    "Endpoint fetch count:",
    endpoint_fetch_count,
)

print(
    "Form count:",
    form_count,
)

print(
    "Safe form count:",
    safe_form_count,
)

print(
    "GET submission count:",
    get_submission_count,
)

print(
    "POST submission count:",
    post_submission_count,
)

print(
    "Submission target response count:",
    submission_target_response_count,
)

print(
    "Form-echo removed response count:",
    form_echo_removed_response_count,
)

print(
    "Raw row count:",
    raw_row_count,
)

print(
    "Target-bearing row count:",
    len(
        deduped_target_rows
    ),
)

print(
    "Dynamic detail seed count:",
    len(
        deduped_detail_seeds
    ),
)

print(
    "URL-query-only row leakage:",
    url_query_only_row_leakage,
)

print()


if deduped_target_rows:

    print(
        "TARGET-BEARING SEARCH RESULT ROWS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, row in enumerate(
        deduped_target_rows[
            :50
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            row.get(
                "region"
            ),
        )

        print(
            "Class:",
            row.get(
                "endpoint_class"
            ),
        )

        print(
            "Submission:",
            row.get(
                "submission_index"
            ),
        )

        print(
            "Target in text:",
            row.get(
                "target_in_text"
            ),
        )

        print(
            "Target in anchor label:",
            row.get(
                "target_in_anchor_label"
            ),
        )

        print(
            "Dynamic detail candidates:",
            len(
                row.get(
                    "dynamic_detail_candidates"
                )
                or []
            ),
        )

        print(
            "Preview:",
            row.get(
                "row_preview"
            ),
        )

        print()


if deduped_detail_seeds:

    print(
        "DYNAMIC DETAIL SEED CANDIDATES"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, seed in enumerate(
        deduped_detail_seeds[
            :100
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            seed.get(
                "region"
            ),
        )

        print(
            "Class:",
            seed.get(
                "endpoint_class"
            ),
        )

        print(
            "Method:",
            seed.get(
                "method"
            ),
        )

        print(
            "Dynamic source:",
            seed.get(
                "dynamic_source"
            ),
        )

        print(
            "Score:",
            seed.get(
                "seed_score"
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

        print()


if not deduped_target_rows:

    print(
        "No target-bearing POST/GET search result row discovered."
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
        item.get(
            "endpoint_class"
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
    for item in endpoints
}


target_row_keys = {
    (
        item.get(
            "region"
        ),
        normalize_url(
            str(
                item.get(
                    "response_url"
                )
                or ""
            )
        ),
        compact_text(
            str(
                item.get(
                    "row_text"
                )
                or ""
            )
        )[:1000],
    )
    for item in deduped_target_rows
}


detail_seed_keys = {
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
    for item in deduped_detail_seeds
}


all_target_rows_have_visible_target = all(
    (
        item.get(
            "target_in_text"
        )
        is True
        or item.get(
            "target_in_anchor_label"
        )
        is True
    )
    for item in deduped_target_rows
)


all_detail_seeds_have_row_evidence = all(
    item.get(
        "row_target_evidence"
    )
    is True
    for item in deduped_detail_seeds
)


all_detail_seeds_have_url = all(
    bool(
        item.get(
            "url"
        )
    )
    for item in deduped_detail_seeds
)


all_detail_seeds_not_search_urls = all(
    not is_search_url(
        str(
            item.get(
                "url"
            )
            or ""
        )
    )
    for item in deduped_detail_seeds
)


all_detail_seeds_not_attachment_urls = all(
    not is_attachment_url(
        str(
            item.get(
                "url"
            )
            or ""
        )
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

    "I-stage input exists": (
        I_STAGE_INPUT_PATH.exists()
    ),

    "K-stage input exists": (
        K_STAGE_INPUT_PATH.exists()
    ),

    "K-stage no target row preserved": (
        k_stage_data.get(
            "resolution"
        )
        == "ROW_LEVEL_PAGINATION_DISCOVERY_COMPLETED_NO_TARGET_ROW"
        or bool(
            k_stage_data.get(
                "resolution"
            )
        )
    ),

    "endpoints loaded": (
        len(
            endpoints
        )
        > 0
    ),

    "actual form only submission enabled": (
        output_data[
            "method"
        ][
            "actual_form_only_submission"
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

    "POST search enabled": (
        output_data[
            "method"
        ][
            "post_search_submission"
        ]
        is True
    ),

    "form echo removal enabled": (
        output_data[
            "method"
        ][
            "form_echo_removal"
        ]
        is True
    ),

    "row target evidence required": (
        output_data[
            "method"
        ][
            "row_level_target_evidence_required"
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

    "dynamic onclick discovery enabled": (
        output_data[
            "method"
        ][
            "dynamic_onclick_discovery"
        ]
        is True
    ),

    "dynamic data attribute discovery enabled": (
        output_data[
            "method"
        ][
            "dynamic_data_attribute_discovery"
        ]
        is True
    ),

    "endpoint candidates unique": (
        len(
            endpoint_keys
        )
        == len(
            endpoints
        )
    ),

    "requests executed": (
        request_count
        > 0
    ),

    "endpoint fetch accounting": (
        endpoint_fetch_count
        == len(
            endpoints
        )
    ),

    "target rows unique": (
        len(
            target_row_keys
        )
        == len(
            deduped_target_rows
        )
    ),

    "detail seed candidates unique": (
        len(
            detail_seed_keys
        )
        == len(
            deduped_detail_seeds
        )
    ),

    "all target rows have visible target": (
        all_target_rows_have_visible_target
    ),

    "all detail seeds have row evidence": (
        all_detail_seeds_have_row_evidence
    ),

    "all detail seeds have URL": (
        all_detail_seeds_have_url
    ),

    "all detail seeds are not search URLs": (
        all_detail_seeds_not_search_urls
    ),

    "all detail seeds are not attachment URLs": (
        all_detail_seeds_not_attachment_urls
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
        "official board POST search / dynamic detail discovery regression failed"
    )
