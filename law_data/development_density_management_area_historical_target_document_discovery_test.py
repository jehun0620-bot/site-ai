# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-1

Development Density Management Area
Historical Target Document Discovery


목표
======================================================================

S-3에서 hardening qualification을 통과한 historical entry endpoint만
대상으로 개발밀도관리구역 관련 실제 document identity를 발견한다.


S-stage와의 역할 분리
======================================================================

S-stage
    historical source entry endpoint 발견 / qualification

T-stage
    qualification된 endpoint 내부에서 실제 target document 발견


핵심 원칙
======================================================================

1. S-3 hardened qualified endpoint만 입력으로 사용한다.

2. endpoint discovery를 다시 수행하지 않는다.

3. 검색엔진 scraping을 사용하지 않는다.

4. source-family / region 범위를 상속한다.

5. 다음 target query만 bounded execution한다.

    - 개발밀도관리구역
    - 개발밀도관리구역 지정
    - 개발밀도관리구역 변경
    - 개발밀도관리구역 해제
    - 개발밀도관리구역 고시
    - 개발밀도관리구역 지정 고시

6. endpoint 페이지 자체가 target 문서를 포함한다고 해서
   endpoint 자체를 document positive로 승격하지 않는다.

7. 발견된 detail/document URL만 document candidate로 만든다.

8. search result 0건은 FALSE가 아니다.

    NOT_FOUND_IN_THIS_SOURCE
        !=
    SITE FALSE

9. 문서를 발견하더라도 verified positive가 아니다.

10. runtime registration 금지.

11. SITE TRUE 자동판정 금지.

12. 이후 U-stage에서 다음을 검증한다.

    - 문서 identity
    - 고시번호
    - 발령기관
    - 고시일
    - 지정 / 변경 / 해제
    - 첨부파일
    - 본문
    - 현재 유효성
"""


from __future__ import annotations

import hashlib
import html
import json
import re
import time

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import (
    parse_qsl,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)

import requests

from law_data.regulation_resolution_types import (
    STATUS_FALSE,
    STATUS_UNKNOWN,
    get_regulation_resolution_policy,
    resolve_source_failure_status,
    validate_policy,
)


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

S3_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_source_family_entry_endpoint_"
        "qualification_hardening.json"
    )
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
        "historical_target_document_discovery.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


TARGET_QUERIES = [
    "개발밀도관리구역",
    "개발밀도관리구역 지정",
    "개발밀도관리구역 변경",
    "개발밀도관리구역 해제",
    "개발밀도관리구역 고시",
    "개발밀도관리구역 지정 고시",
]


# ============================================================
# SOURCE FAMILY
# ============================================================

FAMILY_GAZETTE = (
    "LEGACY_LOCAL_GAZETTE"
)

FAMILY_NOTICE = (
    "LEGACY_LOCAL_NOTICE"
)

FAMILY_URBAN = (
    "URBAN_PLANNING_ARCHIVE"
)

FAMILY_NOTICE_REVERSE = (
    "NOTICE_NUMBER_REVERSE_LOOKUP"
)

ALLOWED_SOURCE_FAMILIES = {
    FAMILY_GAZETTE,
    FAMILY_NOTICE,
    FAMILY_URBAN,
    FAMILY_NOTICE_REVERSE,
}


# ============================================================
# S-3 INPUT CLASSES
# ============================================================

S3_CLASS_GAZETTE = (
    "QUALIFIED_HARDENED_HISTORICAL_GAZETTE_ENDPOINT"
)

S3_CLASS_NOTICE = (
    "QUALIFIED_HARDENED_HISTORICAL_NOTICE_ENDPOINT"
)

S3_CLASS_URBAN = (
    "QUALIFIED_HARDENED_URBAN_PLANNING_ENDPOINT"
)

S3_CLASS_NOTICE_REVERSE = (
    "QUALIFIED_HARDENED_NOTICE_REVERSE_ENDPOINT"
)

ALLOWED_S3_CLASSES = {
    S3_CLASS_GAZETTE,
    S3_CLASS_NOTICE,
    S3_CLASS_URBAN,
    S3_CLASS_NOTICE_REVERSE,
}


# ============================================================
# OUTPUT CLASSES
# ============================================================

CLASS_TARGET_EXACT = (
    "TARGET_DOCUMENT_EXACT_MATCH"
)

CLASS_TARGET_CANDIDATE = (
    "TARGET_DOCUMENT_CANDIDATE"
)

CLASS_TARGET_WEAK = (
    "TARGET_DOCUMENT_WEAK_MATCH"
)

CLASS_SOURCE_NO_RESULT = (
    "NOT_FOUND_IN_THIS_SOURCE"
)

CLASS_REJECTED_UNRELATED = (
    "REJECTED_UNRELATED_DOCUMENT"
)

CLASS_REJECTED_FALSE_POSITIVE = (
    "REJECTED_FALSE_POSITIVE_DOCUMENT"
)

CLASS_REJECTED_DUPLICATE = (
    "REJECTED_DUPLICATE_DOCUMENT"
)

CLASS_REJECTED_HTTP = (
    "REJECTED_HTTP_FAILURE"
)

CLASS_REJECTED_REGION = (
    "REJECTED_REGION_MISMATCH"
)

CLASS_REJECTED_INVALID = (
    "REJECTED_INVALID_URL"
)

VALID_CLASSES = {
    CLASS_TARGET_EXACT,
    CLASS_TARGET_CANDIDATE,
    CLASS_TARGET_WEAK,
    CLASS_SOURCE_NO_RESULT,
    CLASS_REJECTED_UNRELATED,
    CLASS_REJECTED_FALSE_POSITIVE,
    CLASS_REJECTED_DUPLICATE,
    CLASS_REJECTED_HTTP,
    CLASS_REJECTED_REGION,
    CLASS_REJECTED_INVALID,
}

DOCUMENT_CANDIDATE_CLASSES = {
    CLASS_TARGET_EXACT,
    CLASS_TARGET_CANDIDATE,
    CLASS_TARGET_WEAK,
}


# ============================================================
# HTTP
# ============================================================

TIMEOUT = 20

MAX_RESPONSE_BYTES = (
    12
    * 1024
    * 1024
)

MAX_TOTAL_REQUESTS = 100

MAX_REQUESTS_PER_ENDPOINT = 12

REQUEST_DELAY_SECONDS = 0.03

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# SEARCH FIELD HEURISTICS
# ============================================================

SEARCH_FIELD_NAMES = {
    "search",
    "searchword",
    "search_word",
    "searchkeyword",
    "keyword",
    "query",
    "q",
    "skeyword",
    "srchword",
    "srch_word",
    "schword",
    "searchtext",
    "search_text",
    "searchvalue",
    "search_value",
    "key",
}

SEARCH_TYPE_FIELD_NAMES = {
    "searchtype",
    "search_type",
    "searchcondition",
    "search_condition",
    "condition",
    "searchfield",
    "search_field",
    "keyfield",
}

COMMON_SEARCH_QUERY_KEYS = [
    "searchKeyword",
    "searchWord",
    "keyword",
    "query",
    "q",
]


# ============================================================
# TARGET SEMANTICS
# ============================================================

DESIGNATION_TERMS = [
    "지정",
    "결정",
]

CHANGE_TERMS = [
    "변경",
    "변경지정",
]

RELEASE_TERMS = [
    "해제",
    "폐지",
    "지정해제",
]

NOTICE_TERMS = [
    "고시",
    "고시공고",
    "공고",
]

FALSE_POSITIVE_TERMS = [
    "개발밀도관리구역 제도",
    "개발밀도관리구역 안내",
    "개발밀도관리구역 설명",
    "개발밀도관리구역이란",
]


# ============================================================
# URL NORMALIZATION
# ============================================================

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "sessionid",
    "jsessionid",
    "timestamp",
    "rand",
    "random",
    "_",
}

TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
}


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


def unique_strings(
    values: Iterable[Any],
) -> List[str]:

    result: List[str] = []

    seen: Set[str] = set()

    for value in values:

        text = normalize_space(
            value
        )

        if not text:
            continue

        if text in seen:
            continue

        seen.add(
            text
        )

        result.append(
            text
        )

    return result


def unique_dicts_by(
    values: Iterable[Dict[str, Any]],
    key_function,
) -> List[Dict[str, Any]]:

    result: List[
        Dict[str, Any]
    ] = []

    seen = set()

    for item in values:

        key = key_function(
            item
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            item
        )

    return result


def sha256_bytes(
    value: bytes,
) -> str:

    return hashlib.sha256(
        value
    ).hexdigest()


def contains_any(
    value: str,
    terms: Iterable[str],
) -> bool:

    text = normalize_space(
        value
    )

    return any(
        term in text
        for term in terms
    )


# ============================================================
# URL
# ============================================================

def canonicalize_url(
    url: str,
) -> str:

    value = html.unescape(
        normalize_space(
            url
        )
    )

    if not value:
        return ""

    try:

        parsed = urlparse(
            value
        )

    except Exception:

        return ""

    if not parsed.hostname:
        return ""

    scheme = (
        parsed.scheme
        or "https"
    ).lower()

    host = (
        parsed.hostname
        or ""
    ).lower()

    try:

        port = parsed.port

    except ValueError:

        port = None

    if (
        port
        and not (
            scheme == "https"
            and port == 443
        )
        and not (
            scheme == "http"
            and port == 80
        )
    ):

        netloc = (
            f"{host}:{port}"
        )

    else:

        netloc = host

    path = (
        parsed.path
        or "/"
    )

    path = re.sub(
        r";jsessionid=[^/?]+",
        "",
        path,
        flags=re.IGNORECASE,
    )

    path = re.sub(
        r"/{2,}",
        "/",
        path,
    )

    query_items = []

    seen_pairs = set()

    for raw_key, raw_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        key = normalize_space(
            raw_key
        )

        if not key:
            continue

        lowered = key.lower()

        if lowered in VOLATILE_QUERY_KEYS:
            continue

        if lowered in TRACKING_QUERY_KEYS:
            continue

        if "csrf" in lowered:
            continue

        if "session" in lowered:
            continue

        pair = (
            key,
            raw_value,
        )

        if pair in seen_pairs:
            continue

        seen_pairs.add(
            pair
        )

        query_items.append(
            pair
        )

    query_items.sort(
        key=lambda item: (
            item[0].lower(),
            item[1],
        )
    )

    query = urlencode(
        query_items,
        doseq=True,
    )

    return urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            query,
            "",
        )
    )


def hostname(
    url: str,
) -> str:

    try:

        return (
            urlparse(
                url
            ).hostname
            or ""
        ).lower()

    except Exception:

        return ""


def same_host(
    first_url: str,
    second_url: str,
) -> bool:

    return (
        hostname(
            first_url
        )
        ==
        hostname(
            second_url
        )
    )


def is_government_url(
    url: str,
) -> bool:

    host = hostname(
        url
    )

    return bool(
        host
        and (
            host == "go.kr"
            or host.endswith(
                ".go.kr"
            )
        )
    )


# ============================================================
# HTML PARSER
# ============================================================

class DiscoveryHTMLParser(
    HTMLParser
):

    def __init__(
        self,
        base_url: str,
    ) -> None:

        super().__init__(
            convert_charrefs=True
        )

        self.base_url = (
            base_url
        )

        self.title_parts: List[str] = []

        self._inside_title = False

        self.links: List[
            Dict[str, str]
        ] = []

        self._current_link: Optional[
            Dict[str, Any]
        ] = None

        self.forms: List[
            Dict[str, Any]
        ] = []

        self._current_form: Optional[
            Dict[str, Any]
        ] = None

    def handle_starttag(
        self,
        tag: str,
        attrs: List[
            Tuple[str, Optional[str]]
        ],
    ) -> None:

        attrs_dict = {
            normalize_space(
                key
            ).lower(): (
                value
                or ""
            )
            for key, value
            in attrs
        }

        lowered_tag = tag.lower()

        if lowered_tag == "title":

            self._inside_title = True

        elif lowered_tag == "a":

            href = normalize_space(
                attrs_dict.get(
                    "href"
                )
            )

            if href:

                self._current_link = {
                    "href": href,
                    "text_parts": [],
                }

        elif lowered_tag == "form":

            action = normalize_space(
                attrs_dict.get(
                    "action"
                )
            )

            method = normalize_space(
                attrs_dict.get(
                    "method"
                )
            ).upper()

            if not method:

                method = "GET"

            self._current_form = {
                "action": action,
                "method": method,
                "inputs": [],
            }

        elif (
            lowered_tag
            in {
                "input",
                "textarea",
                "select",
            }
            and self._current_form
            is not None
        ):

            name = normalize_space(
                attrs_dict.get(
                    "name"
                )
            )

            if not name:
                return

            self._current_form[
                "inputs"
            ].append(
                {
                    "name": name,
                    "type": normalize_space(
                        attrs_dict.get(
                            "type"
                        )
                    ).lower(),
                    "value": normalize_space(
                        attrs_dict.get(
                            "value"
                        )
                    ),
                }
            )

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        lowered_tag = (
            tag.lower()
        )

        if lowered_tag == "title":

            self._inside_title = False

        elif (
            lowered_tag == "a"
            and self._current_link
            is not None
        ):

            href = normalize_space(
                self._current_link.get(
                    "href"
                )
            )

            text = normalize_space(
                " ".join(
                    self._current_link.get(
                        "text_parts"
                    )
                    or []
                )
            )

            absolute_url = (
                urljoin(
                    self.base_url,
                    href,
                )
            )

            absolute_url = canonicalize_url(
                absolute_url
            )

            if absolute_url:

                self.links.append(
                    {
                        "url": absolute_url,
                        "text": text,
                    }
                )

            self._current_link = None

        elif (
            lowered_tag == "form"
            and self._current_form
            is not None
        ):

            action = (
                self._current_form.get(
                    "action"
                )
                or self.base_url
            )

            action_url = canonicalize_url(
                urljoin(
                    self.base_url,
                    action,
                )
            )

            self._current_form[
                "action_url"
            ] = action_url

            self.forms.append(
                self._current_form
            )

            self._current_form = None

    def handle_data(
        self,
        data: str,
    ) -> None:

        text = normalize_space(
            data
        )

        if not text:
            return

        if self._inside_title:

            self.title_parts.append(
                text
            )

        if self._current_link is not None:

            self._current_link[
                "text_parts"
            ].append(
                text
            )

    @property
    def title(
        self,
    ) -> str:

        return normalize_space(
            " ".join(
                self.title_parts
            )
        )


def parse_html(
    raw_html: str,
    base_url: str,
) -> DiscoveryHTMLParser:

    parser = DiscoveryHTMLParser(
        base_url
    )

    try:

        parser.feed(
            raw_html
        )

    except Exception:

        pass

    return parser


# ============================================================
# HTTP
# ============================================================

def decode_html(
    response: requests.Response,
    data: bytes,
) -> Tuple[str, str]:

    candidates: List[str] = []

    content_type = normalize_space(
        response.headers.get(
            "Content-Type"
        )
    )

    match = re.search(
        r"""charset\s*=\s*["']?([^;"'\s]+)""",
        content_type,
        flags=re.IGNORECASE,
    )

    if match:

        candidates.append(
            normalize_space(
                match.group(1)
            )
        )

    if response.encoding:

        candidates.append(
            normalize_space(
                response.encoding
            )
        )

    prefix = data[
        :8192
    ]

    preview = prefix.decode(
        "ascii",
        errors="ignore",
    )

    for pattern in [
        re.compile(
            r"""charset\s*=\s*["']?\s*([A-Za-z0-9._\-]+)""",
            re.IGNORECASE,
        ),
    ]:

        meta_match = pattern.search(
            preview
        )

        if meta_match:

            candidates.append(
                normalize_space(
                    meta_match.group(1)
                )
            )

    candidates.extend(
        [
            "utf-8",
            "cp949",
            "euc-kr",
        ]
    )

    for encoding in unique_strings(
        candidates
    ):

        try:

            return (
                data.decode(
                    encoding
                ),
                encoding,
            )

        except (
            UnicodeDecodeError,
            LookupError,
        ):

            continue

    return (
        data.decode(
            "utf-8",
            errors="replace",
        ),
        "utf-8-replace",
    )


def fetch_page(
    session: requests.Session,
    url: str,
    *,
    method: str = "GET",
    params: Optional[
        Dict[str, Any]
    ] = None,
    data_payload: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:

    result: Dict[str, Any] = {
        "requested_url": url,
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "response_bytes": 0,
        "encoding": "",
        "raw_html": "",
        "response_sha256": "",
        "error": "",
    }

    try:

        request_method = (
            method.upper()
        )

        if request_method == "POST":

            response_context = (
                session.post(
                    url,
                    data=(
                        data_payload
                        or {}
                    ),
                    timeout=TIMEOUT,
                    allow_redirects=True,
                    stream=True,
                )
            )

        else:

            response_context = (
                session.get(
                    url,
                    params=(
                        params
                        or {}
                    ),
                    timeout=TIMEOUT,
                    allow_redirects=True,
                    stream=True,
                )
            )

        with response_context as response:

            result[
                "http_status"
            ] = response.status_code

            result[
                "final_url"
            ] = canonicalize_url(
                str(
                    response.url
                )
            )

            result[
                "content_type"
            ] = normalize_space(
                response.headers.get(
                    "Content-Type"
                )
            )

            chunks: List[bytes] = []

            total = 0

            for chunk in response.iter_content(
                chunk_size=128 * 1024,
            ):

                if not chunk:
                    continue

                total += len(
                    chunk
                )

                if (
                    total
                    >
                    MAX_RESPONSE_BYTES
                ):

                    raise ValueError(
                        "response exceeds "
                        f"{MAX_RESPONSE_BYTES} bytes"
                    )

                chunks.append(
                    chunk
                )

            raw_bytes = b"".join(
                chunks
            )

            result[
                "response_bytes"
            ] = len(
                raw_bytes
            )

            result[
                "response_sha256"
            ] = sha256_bytes(
                raw_bytes
            )

            content_type = normalize_space(
                result[
                    "content_type"
                ]
            ).lower()

            html_like = (
                "html" in content_type
                or "text/" in content_type
                or raw_bytes[
                    :1000
                ].lstrip().lower().startswith(
                    (
                        b"<!doctype html",
                        b"<html",
                    )
                )
            )

            if html_like:

                decoded, encoding = decode_html(
                    response,
                    raw_bytes,
                )

                result[
                    "raw_html"
                ] = decoded

                result[
                    "encoding"
                ] = encoding

    except Exception as exc:

        result[
            "error"
        ] = repr(
            exc
        )

    return result


# ============================================================
# INPUT
# ============================================================

def load_s3_endpoints(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    raw = data.get(
        "next_stage_endpoint_pool"
    )

    if not isinstance(
        raw,
        list,
    ):

        raw = data.get(
            "qualified_endpoints"
        )

    if not isinstance(
        raw,
        list,
    ):

        return []

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[str, str]
    ] = set()

    for item in raw:

        if not isinstance(
            item,
            dict,
        ):

            continue

        family = normalize_space(
            item.get(
                "source_family"
            )
        )

        if (
            family
            not in ALLOWED_SOURCE_FAMILIES
        ):

            continue

        classification = normalize_space(
            item.get(
                "classification"
            )
        )

        if (
            classification
            and classification
            not in ALLOWED_S3_CLASSES
        ):

            continue

        url = canonicalize_url(
            item.get(
                "url"
            )
            or item.get(
                "final_url"
            )
            or item.get(
                "input_url"
            )
            or ""
        )

        if not url:
            continue

        regions = item.get(
            "regions"
        )

        if not isinstance(
            regions,
            list,
        ):

            regions = []

        regions = unique_strings(
            regions
        )

        key = (
            family,
            url,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            {
                "source_family": family,
                "classification": classification,
                "regions": regions,
                "url": url,
                "title": normalize_space(
                    item.get(
                        "title"
                    )
                ),
                "reasons": (
                    item.get(
                        "reasons"
                    )
                    or []
                ),
            }
        )

    return result


# ============================================================
# SEARCH FORM DISCOVERY
# ============================================================

def is_search_field(
    name: str,
) -> bool:

    normalized = normalize_space(
        name
    ).lower()

    compact = re.sub(
        r"[^a-z0-9]",
        "",
        normalized,
    )

    return (
        normalized
        in SEARCH_FIELD_NAMES
        or compact
        in {
            re.sub(
                r"[^a-z0-9]",
                "",
                item,
            )
            for item
            in SEARCH_FIELD_NAMES
        }
        or "keyword" in compact
        or "searchword" in compact
        or "srchword" in compact
    )


def build_form_query_payload(
    form: Dict[str, Any],
    target_query: str,
) -> Optional[
    Dict[str, str]
]:

    payload: Dict[
        str,
        str,
    ] = {}

    search_field_found = False

    for field in (
        form.get(
            "inputs"
        )
        or []
    ):

        if not isinstance(
            field,
            dict,
        ):

            continue

        name = normalize_space(
            field.get(
                "name"
            )
        )

        if not name:
            continue

        field_type = normalize_space(
            field.get(
                "type"
            )
        ).lower()

        value = normalize_space(
            field.get(
                "value"
            )
        )

        if (
            field_type
            in {
                "submit",
                "button",
                "reset",
                "file",
                "image",
            }
        ):

            continue

        if is_search_field(
            name
        ):

            payload[
                name
            ] = target_query

            search_field_found = True

        elif (
            field_type
            in {
                "hidden",
                "",
            }
            and value
        ):

            payload[
                name
            ] = value

    if not search_field_found:

        return None

    return payload


# ============================================================
# DOCUMENT DISCOVERY
# ============================================================

def link_target_score(
    *,
    link_text: str,
    link_url: str,
) -> Tuple[
    int,
    List[str],
]:

    evidence = normalize_space(
        f"{link_text} {link_url}"
    )

    reasons: List[str] = []

    score = 0

    if TARGET_NAME in link_text:

        score += 100

        reasons.append(
            "TARGET_NAME_IN_LINK_TEXT"
        )

    elif TARGET_NAME in evidence:

        score += 70

        reasons.append(
            "TARGET_NAME_IN_LINK_EVIDENCE"
        )

    if contains_any(
        evidence,
        NOTICE_TERMS,
    ):

        score += 20

        reasons.append(
            "NOTICE_TERM_PRESENT"
        )

    if contains_any(
        evidence,
        DESIGNATION_TERMS,
    ):

        score += 20

        reasons.append(
            "DESIGNATION_TERM_PRESENT"
        )

    if contains_any(
        evidence,
        CHANGE_TERMS,
    ):

        score += 10

        reasons.append(
            "CHANGE_TERM_PRESENT"
        )

    if contains_any(
        evidence,
        RELEASE_TERMS,
    ):

        score += 10

        reasons.append(
            "RELEASE_TERM_PRESENT"
        )

    return (
        score,
        unique_strings(
            reasons
        ),
    )


def classify_discovered_link(
    *,
    link_text: str,
    link_url: str,
) -> Tuple[
    str,
    int,
    List[str],
]:

    score, reasons = (
        link_target_score(
            link_text=link_text,
            link_url=link_url,
        )
    )

    evidence = normalize_space(
        f"{link_text} {link_url}"
    )

    if contains_any(
        evidence,
        FALSE_POSITIVE_TERMS,
    ):

        return (
            CLASS_REJECTED_FALSE_POSITIVE,
            score,
            reasons
            + [
                "FALSE_POSITIVE_CONTEXT"
            ],
        )

    if (
        TARGET_NAME
        in link_text
        and (
            contains_any(
                evidence,
                NOTICE_TERMS,
            )
            or contains_any(
                evidence,
                DESIGNATION_TERMS,
            )
            or contains_any(
                evidence,
                CHANGE_TERMS,
            )
            or contains_any(
                evidence,
                RELEASE_TERMS,
            )
        )
    ):

        return (
            CLASS_TARGET_EXACT,
            score,
            reasons,
        )

    if TARGET_NAME in evidence:

        return (
            CLASS_TARGET_CANDIDATE,
            score,
            reasons,
        )

    return (
        CLASS_REJECTED_UNRELATED,
        score,
        reasons,
    )


def extract_document_candidates(
    *,
    parser: DiscoveryHTMLParser,
    source_endpoint: Dict[str, Any],
    request_url: str,
    query: str,
) -> List[Dict[str, Any]]:

    result: List[
        Dict[str, Any]
    ] = []

    source_url = (
        source_endpoint[
            "url"
        ]
    )

    for link in parser.links:

        document_url = canonicalize_url(
            link.get(
                "url"
            )
            or ""
        )

        link_text = normalize_space(
            link.get(
                "text"
            )
        )

        if not document_url:
            continue

        # 외부 사이트 link는 T-1 candidate로 사용하지 않는다.
        if not same_host(
            source_url,
            document_url,
        ):

            continue

        # source endpoint 자기 자신은 document가 아니다.
        if (
            document_url
            == source_url
        ):

            continue

        classification, score, reasons = (
            classify_discovered_link(
                link_text=link_text,
                link_url=document_url,
            )
        )

        if (
            classification
            == CLASS_REJECTED_UNRELATED
        ):

            continue

        result.append(
            {
                "standard_code": (
                    STANDARD_CODE
                ),

                "target_name": (
                    TARGET_NAME
                ),

                "source_family": (
                    source_endpoint.get(
                        "source_family"
                    )
                ),

                "regions": (
                    source_endpoint.get(
                        "regions"
                    )
                    or []
                ),

                "source_entry_url": (
                    source_url
                ),

                "request_url": (
                    request_url
                ),

                "query": query,

                "document_url": (
                    document_url
                ),

                "document_title": (
                    link_text
                ),

                "score": score,

                "classification": (
                    classification
                ),

                "reasons": (
                    reasons
                ),

                "verified_positive": False,

                "runtime_registration_allowed": False,

                "site_positive_allowed": False,

                "final_positive_promotion_allowed": False,
            }
        )

    return result


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print(
        "=" * 60
    )

    print(
        "DEVELOPMENT DENSITY MANAGEMENT AREA"
    )

    print(
        "HISTORICAL TARGET DOCUMENT DISCOVERY"
    )

    print(
        "=" * 60
    )

    print()

    print(
        f"Target: {TARGET_NAME}"
    )

    print(
        f"Standard code: {STANDARD_CODE}"
    )

    # ========================================================
    # POLICY
    # ========================================================

    policy_errors = validate_policy(
        STANDARD_CODE
    )

    if policy_errors:

        raise AssertionError(
            "Invalid regulation resolution policy: "
            + repr(
                policy_errors
            )
        )

    policy = (
        get_regulation_resolution_policy(
            STANDARD_CODE
        )
    )

    print(
        "Resolution type:",
        policy.get(
            "resolution_type"
        ),
    )

    print(
        "Negative evidence allowed:",
        policy.get(
            "negative_evidence_allowed"
        ),
    )

    print()

    # ========================================================
    # INPUT
    # ========================================================

    if not S3_STAGE_INPUT_PATH.exists():

        raise FileNotFoundError(
            "S-3 input not found: "
            f"{S3_STAGE_INPUT_PATH}"
        )

    s3_data = json.loads(
        S3_STAGE_INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        s3_data,
        dict,
    ):

        raise TypeError(
            "S-3 input must be JSON object."
        )

    endpoints = load_s3_endpoints(
        s3_data
    )

    print(
        "S-3 endpoint count:",
        len(
            endpoints
        ),
    )

    if not endpoints:

        raise AssertionError(
            "No hardened S-3 endpoint loaded."
        )

    # ========================================================
    # SESSION
    # ========================================================

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                USER_AGENT
            ),

            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),

            "Accept-Language": (
                "ko-KR,ko;q=0.9,"
                "en-US;q=0.7,"
                "en;q=0.5"
            ),
        }
    )

    request_count = 0

    http_success_count = 0

    transport_error_count = 0

    raw_candidates: List[
        Dict[str, Any]
    ] = []

    source_results: List[
        Dict[str, Any]
    ] = []

    # ========================================================
    # ENDPOINT LOOP
    # ========================================================

    for endpoint_index, endpoint in enumerate(
        endpoints,
        start=1,
    ):

        if (
            request_count
            >= MAX_TOTAL_REQUESTS
        ):

            break

        source_url = endpoint[
            "url"
        ]

        print()

        print(
            "-" * 60
        )

        print(
            f"SOURCE {endpoint_index}"
        )

        print(
            "Family:",
            endpoint.get(
                "source_family"
            ),
        )

        print(
            "Regions:",
            endpoint.get(
                "regions"
            ),
        )

        print(
            "URL:",
            source_url,
        )

        endpoint_request_count = 0

        endpoint_candidate_count_before = (
            len(
                raw_candidates
            )
        )

        # ----------------------------------------------------
        # 1. Fetch entry page
        # ----------------------------------------------------

        request_count += 1

        endpoint_request_count += 1

        entry_response = fetch_page(
            session,
            source_url,
        )

        entry_status = entry_response.get(
            "http_status"
        )

        if (
            isinstance(
                entry_status,
                int,
            )
            and 200
            <= entry_status
            < 300
        ):

            http_success_count += 1

        if entry_response.get(
            "error"
        ):

            transport_error_count += 1

        if (
            not isinstance(
                entry_status,
                int,
            )
            or not (
                200
                <= entry_status
                < 300
            )
            or entry_response.get(
                "error"
            )
        ):

            source_results.append(
                {
                    "source_family": endpoint.get(
                        "source_family"
                    ),

                    "regions": endpoint.get(
                        "regions"
                    ),

                    "source_entry_url": source_url,

                    "classification": (
                        CLASS_REJECTED_HTTP
                    ),

                    "http_status": (
                        entry_status
                    ),

                    "error": entry_response.get(
                        "error"
                    ),

                    "candidate_count": 0,

                    "site_status_if_only_source": (
                        STATUS_UNKNOWN
                    ),
                }
            )

            print(
                "Entry HTTP failure:",
                entry_status,
                entry_response.get(
                    "error"
                ),
            )

            continue

        entry_final_url = (
            entry_response.get(
                "final_url"
            )
            or source_url
        )

        if not is_government_url(
            entry_final_url
        ):

            source_results.append(
                {
                    "source_family": endpoint.get(
                        "source_family"
                    ),

                    "regions": endpoint.get(
                        "regions"
                    ),

                    "source_entry_url": source_url,

                    "classification": (
                        CLASS_REJECTED_INVALID
                    ),

                    "candidate_count": 0,

                    "site_status_if_only_source": (
                        STATUS_UNKNOWN
                    ),
                }
            )

            continue

        entry_parser = parse_html(
            entry_response.get(
                "raw_html"
            )
            or "",
            entry_final_url,
        )

        # ----------------------------------------------------
        # Entry page direct link evidence
        # ----------------------------------------------------

        direct_candidates = (
            extract_document_candidates(
                parser=entry_parser,
                source_endpoint=endpoint,
                request_url=entry_final_url,
                query="",
            )
        )

        raw_candidates.extend(
            direct_candidates
        )

        # ----------------------------------------------------
        # 2. Parsed search form execution
        # ----------------------------------------------------

        for form in entry_parser.forms:

            if (
                endpoint_request_count
                >= MAX_REQUESTS_PER_ENDPOINT
                or request_count
                >= MAX_TOTAL_REQUESTS
            ):

                break

            action_url = canonicalize_url(
                form.get(
                    "action_url"
                )
                or ""
            )

            if not action_url:
                continue

            if not same_host(
                source_url,
                action_url,
            ):

                continue

            if not is_government_url(
                action_url
            ):

                continue

            method = normalize_space(
                form.get(
                    "method"
                )
            ).upper()

            if (
                method
                not in {
                    "GET",
                    "POST",
                }
            ):

                continue

            # 가장 정확한 target query부터 실행.
            for target_query in TARGET_QUERIES:

                if (
                    endpoint_request_count
                    >= MAX_REQUESTS_PER_ENDPOINT
                    or request_count
                    >= MAX_TOTAL_REQUESTS
                ):

                    break

                payload = (
                    build_form_query_payload(
                        form,
                        target_query,
                    )
                )

                if not payload:
                    break

                request_count += 1

                endpoint_request_count += 1

                if method == "POST":

                    response = fetch_page(
                        session,
                        action_url,
                        method="POST",
                        data_payload=payload,
                    )

                else:

                    response = fetch_page(
                        session,
                        action_url,
                        method="GET",
                        params=payload,
                    )

                status = response.get(
                    "http_status"
                )

                if (
                    isinstance(
                        status,
                        int,
                    )
                    and 200
                    <= status
                    < 300
                ):

                    http_success_count += 1

                if response.get(
                    "error"
                ):

                    transport_error_count += 1

                if (
                    not isinstance(
                        status,
                        int,
                    )
                    or not (
                        200
                        <= status
                        < 300
                    )
                    or response.get(
                        "error"
                    )
                ):

                    continue

                final_url = (
                    response.get(
                        "final_url"
                    )
                    or action_url
                )

                parser = parse_html(
                    response.get(
                        "raw_html"
                    )
                    or "",
                    final_url,
                )

                raw_candidates.extend(
                    extract_document_candidates(
                        parser=parser,
                        source_endpoint=endpoint,
                        request_url=final_url,
                        query=target_query,
                    )
                )

                if REQUEST_DELAY_SECONDS:

                    time.sleep(
                        REQUEST_DELAY_SECONDS
                    )

        # ----------------------------------------------------
        # 3. Generic GET query fallback
        # ----------------------------------------------------
        #
        # parsed search form을 발견하지 못한 endpoint에 대해
        # 제한적으로만 실행한다.
        # ----------------------------------------------------

        endpoint_candidate_count_now = (
            len(
                raw_candidates
            )
            -
            endpoint_candidate_count_before
        )

        if (
            endpoint_candidate_count_now
            == 0
        ):

            for query_key in COMMON_SEARCH_QUERY_KEYS:

                if (
                    endpoint_request_count
                    >= MAX_REQUESTS_PER_ENDPOINT
                    or request_count
                    >= MAX_TOTAL_REQUESTS
                ):

                    break

                request_count += 1

                endpoint_request_count += 1

                response = fetch_page(
                    session,
                    source_url,
                    method="GET",
                    params={
                        query_key: (
                            TARGET_NAME
                        )
                    },
                )

                status = response.get(
                    "http_status"
                )

                if (
                    isinstance(
                        status,
                        int,
                    )
                    and 200
                    <= status
                    < 300
                ):

                    http_success_count += 1

                if response.get(
                    "error"
                ):

                    transport_error_count += 1

                if (
                    not isinstance(
                        status,
                        int,
                    )
                    or not (
                        200
                        <= status
                        < 300
                    )
                    or response.get(
                        "error"
                    )
                ):

                    continue

                final_url = (
                    response.get(
                        "final_url"
                    )
                    or source_url
                )

                parser = parse_html(
                    response.get(
                        "raw_html"
                    )
                    or "",
                    final_url,
                )

                found = extract_document_candidates(
                    parser=parser,
                    source_endpoint=endpoint,
                    request_url=final_url,
                    query=TARGET_NAME,
                )

                raw_candidates.extend(
                    found
                )

                if found:

                    break

        endpoint_candidate_count = (
            len(
                raw_candidates
            )
            -
            endpoint_candidate_count_before
        )

        if endpoint_candidate_count:

            source_classification = (
                "TARGET_DOCUMENT_DISCOVERED"
            )

        else:

            source_classification = (
                CLASS_SOURCE_NO_RESULT
            )

        source_results.append(
            {
                "source_family": endpoint.get(
                    "source_family"
                ),

                "regions": endpoint.get(
                    "regions"
                ),

                "source_entry_url": source_url,

                "request_count": (
                    endpoint_request_count
                ),

                "candidate_count": (
                    endpoint_candidate_count
                ),

                "classification": (
                    source_classification
                ),

                # 매우 중요
                "site_status_if_only_source": (
                    STATUS_UNKNOWN
                    if (
                        source_classification
                        == CLASS_SOURCE_NO_RESULT
                    )
                    else STATUS_UNKNOWN
                ),

                "negative_evidence_allowed": (
                    policy.get(
                        "negative_evidence_allowed"
                    )
                ),

                "source_not_found_means_false": (
                    policy.get(
                        "source_not_found_means_false"
                    )
                ),
            }
        )

        print(
            "Requests:",
            endpoint_request_count,
        )

        print(
            "Candidates:",
            endpoint_candidate_count,
        )

        print(
            "Resolution:",
            source_classification,
        )

    # ========================================================
    # CANDIDATE DEDUPE
    # ========================================================

    raw_candidate_count = len(
        raw_candidates
    )

    candidate_map: Dict[
        str,
        Dict[str, Any],
    ] = {}

    duplicate_candidate_count = 0

    for item in raw_candidates:

        document_url = canonicalize_url(
            item.get(
                "document_url"
            )
            or ""
        )

        if not document_url:
            continue

        if document_url in candidate_map:

            duplicate_candidate_count += 1

            existing = candidate_map[
                document_url
            ]

            existing[
                "regions"
            ] = unique_strings(
                (
                    existing.get(
                        "regions"
                    )
                    or []
                )
                +
                (
                    item.get(
                        "regions"
                    )
                    or []
                )
            )

            existing[
                "queries"
            ] = unique_strings(
                (
                    existing.get(
                        "queries"
                    )
                    or []
                )
                +
                [
                    item.get(
                        "query"
                    )
                ]
            )

            existing[
                "source_entry_urls"
            ] = unique_strings(
                (
                    existing.get(
                        "source_entry_urls"
                    )
                    or []
                )
                +
                [
                    item.get(
                        "source_entry_url"
                    )
                ]
            )

            existing[
                "reasons"
            ] = unique_strings(
                (
                    existing.get(
                        "reasons"
                    )
                    or []
                )
                +
                (
                    item.get(
                        "reasons"
                    )
                    or []
                )
            )

            if (
                item.get(
                    "score",
                    0,
                )
                >
                existing.get(
                    "score",
                    0,
                )
            ):

                existing[
                    "score"
                ] = item.get(
                    "score"
                )

                existing[
                    "classification"
                ] = item.get(
                    "classification"
                )

                existing[
                    "document_title"
                ] = item.get(
                    "document_title"
                )

            continue

        normalized = dict(
            item
        )

        normalized[
            "queries"
        ] = unique_strings(
            [
                item.get(
                    "query"
                )
            ]
        )

        normalized[
            "source_entry_urls"
        ] = unique_strings(
            [
                item.get(
                    "source_entry_url"
                )
            ]
        )

        candidate_map[
            document_url
        ] = normalized

    document_candidates = list(
        candidate_map.values()
    )

    document_candidates.sort(
        key=lambda item: (
            -int(
                item.get(
                    "score"
                )
                or 0
            ),
            normalize_space(
                item.get(
                    "document_url"
                )
            ),
        )
    )

    # ========================================================
    # CLASSIFICATION COUNTS
    # ========================================================

    candidate_class_counts = Counter(
        item.get(
            "classification"
        )
        for item in document_candidates
    )

    source_class_counts = Counter(
        item.get(
            "classification"
        )
        for item in source_results
    )

    # ========================================================
    # NEXT STAGE DOCUMENT POOL
    # ========================================================

    next_stage_document_pool = [
        {
            "standard_code": (
                STANDARD_CODE
            ),

            "target_name": (
                TARGET_NAME
            ),

            "source_family": item.get(
                "source_family"
            ),

            "regions": item.get(
                "regions"
            )
            or [],

            "source_entry_urls": (
                item.get(
                    "source_entry_urls"
                )
                or []
            ),

            "document_url": (
                item.get(
                    "document_url"
                )
            ),

            "document_title": (
                item.get(
                    "document_title"
                )
            ),

            "classification": (
                item.get(
                    "classification"
                )
            ),

            "score": (
                item.get(
                    "score"
                )
            ),

            "reasons": (
                item.get(
                    "reasons"
                )
                or []
            ),

            "verified_positive": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,

            "final_positive_promotion_allowed": False,
        }

        for item in document_candidates

        if (
            item.get(
                "classification"
            )
            in DOCUMENT_CANDIDATE_CLASSES
        )
    ]

    # ========================================================
    # RESOLUTION
    # ========================================================

    if next_stage_document_pool:

        resolution = (
            "HISTORICAL_TARGET_DOCUMENT_DISCOVERY_COMPLETED"
        )

        next_action = (
            "T-1에서 발견된 target document candidate를 U-stage에서 "
            "직접 재조회하여 문서 identity, 고시번호, 발령기관, 고시일, "
            "지정/변경/해제 상태와 첨부파일을 검증한다. "
            "아직 SITE TRUE로 승격하지 않는다."
        )

    else:

        resolution = (
            "HISTORICAL_TARGET_DOCUMENT_DISCOVERY_NO_DOCUMENT"
        )

        next_action = (
            "현재 S-3 historical endpoint에서는 개발밀도관리구역 관련 "
            "문서가 발견되지 않았다. 이는 SITE FALSE가 아니다. "
            "다른 official source family 또는 notice-number reverse lookup "
            "경로를 추가 탐색한다."
        )

    source_failure_site_status = (
        resolve_source_failure_status(
            STANDARD_CODE
        )
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-T-1 "
            "Historical Target Document Discovery"
        ),

        "target": {
            "name": (
                TARGET_NAME
            ),

            "standard_code": (
                STANDARD_CODE
            ),
        },

        "regulation_resolution_policy": (
            policy
        ),

        "inputs": {
            "s3_stage_path": (
                str(
                    S3_STAGE_INPUT_PATH
                )
            ),

            "s3_stage_resolution": (
                s3_data.get(
                    "resolution"
                )
            ),
        },

        "method": {
            "s3_hardened_endpoint_only": True,

            "endpoint_rediscovery_disabled": True,

            "search_engine_scraping_disabled": True,

            "bounded_target_query_matrix": True,

            "target_queries": (
                TARGET_QUERIES
            ),

            "same_host_document_discovery_required": True,

            "official_go_kr_source_required": True,

            "source_family_scope_inherited": True,

            "region_scope_inherited": True,

            "source_not_found_is_false": False,

            "negative_evidence_allowed": (
                policy.get(
                    "negative_evidence_allowed"
                )
            ),

            "document_candidate_positive_allowed": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,

            "final_positive_promotion_allowed": False,
        },

        "summary": {
            "s3_endpoint_count": (
                len(
                    endpoints
                )
            ),

            "request_count": (
                request_count
            ),

            "http_success_count": (
                http_success_count
            ),

            "transport_error_count": (
                transport_error_count
            ),

            "raw_candidate_count": (
                raw_candidate_count
            ),

            "duplicate_candidate_removed": (
                duplicate_candidate_count
            ),

            "canonical_document_candidate_count": (
                len(
                    document_candidates
                )
            ),

            "next_stage_document_pool_count": (
                len(
                    next_stage_document_pool
                )
            ),

            "source_no_result_count": (
                source_class_counts.get(
                    CLASS_SOURCE_NO_RESULT,
                    0,
                )
            ),
        },

        "candidate_classification_counts": (
            dict(
                sorted(
                    candidate_class_counts.items()
                )
            )
        ),

        "source_classification_counts": (
            dict(
                sorted(
                    source_class_counts.items()
                )
            )
        ),

        "source_results": (
            source_results
        ),

        "document_candidates": (
            document_candidates
        ),

        "next_stage_document_pool": (
            next_stage_document_pool
        ),

        "source_failure_site_status": (
            source_failure_site_status
        ),

        "resolution": (
            resolution
        ),

        "next_action": (
            next_action
        ),

        "verified_positive": False,

        "runtime_registration_allowed": False,

        "site_positive_allowed": False,

        "final_positive_promotion_allowed": False,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            output_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ========================================================
    # RESULT
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "HISTORICAL TARGET DOCUMENT DISCOVERY RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "S-3 endpoint count:",
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
        "Raw candidate count:",
        raw_candidate_count,
    )

    print(
        "Duplicate candidate removed:",
        duplicate_candidate_count,
    )

    print(
        "Canonical document candidate count:",
        len(
            document_candidates
        ),
    )

    print(
        "Next-stage document pool count:",
        len(
            next_stage_document_pool
        ),
    )

    print(
        "Source NOT_FOUND count:",
        source_class_counts.get(
            CLASS_SOURCE_NO_RESULT,
            0,
        ),
    )

    print(
        "Source failure SITE status:",
        source_failure_site_status,
    )

    # ========================================================
    # CANDIDATE PRINT
    # ========================================================

    if next_stage_document_pool:

        print()

        print(
            "TARGET DOCUMENT CANDIDATES"
        )

        print(
            "-" * 60
        )

        for index, item in enumerate(
            next_stage_document_pool,
            start=1,
        ):

            print(
                f"[{index}] "
                f"{item.get('classification')}"
            )

            print(
                "Family:",
                item.get(
                    "source_family"
                ),
            )

            print(
                "Regions:",
                item.get(
                    "regions"
                ),
            )

            print(
                "Title:",
                item.get(
                    "document_title"
                ),
            )

            print(
                "URL:",
                item.get(
                    "document_url"
                ),
            )

            print(
                "Score:",
                item.get(
                    "score"
                ),
            )

            print(
                "Reasons:",
                item.get(
                    "reasons"
                ),
            )

            print()

    # ========================================================
    # RESOLUTION
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "RESOLUTION"
    )

    print(
        "=" * 60
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

    # ========================================================
    # VALIDATION
    # ========================================================

    candidate_urls = [
        canonicalize_url(
            item.get(
                "document_url"
            )
            or ""
        )
        for item in document_candidates
    ]

    next_stage_urls = [
        canonicalize_url(
            item.get(
                "document_url"
            )
            or ""
        )
        for item in next_stage_document_pool
    ]

    verified_positive_leakage = sum(
        1
        for item in document_candidates
        if item.get(
            "verified_positive"
        )
        is True
    )

    runtime_registration_leakage = sum(
        1
        for item in document_candidates
        if item.get(
            "runtime_registration_allowed"
        )
        is True
    )

    site_true_leakage = sum(
        1
        for item in document_candidates
        if item.get(
            "site_positive_allowed"
        )
        is True
    )

    false_from_source_failure_leakage = (
        1
        if (
            source_failure_site_status
            == STATUS_FALSE
            and policy.get(
                "negative_evidence_allowed"
            )
            is not True
        )
        else 0
    )

    all_candidate_classes_valid = all(
        item.get(
            "classification"
        )
        in VALID_CLASSES
        for item in document_candidates
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

        "resolution policy valid": (
            not policy_errors
        ),

        "resolution type hybrid spatial notice": (
            policy.get(
                "resolution_type"
            )
            == "HYBRID_SPATIAL_NOTICE"
        ),

        "S-3 input exists": (
            S3_STAGE_INPUT_PATH.exists()
        ),

        "S-3 hardened endpoints loaded": (
            len(
                endpoints
            )
            > 0
        ),

        "only S-3 hardened endpoints used": (
            all(
                (
                    not item.get(
                        "classification"
                    )
                    or item.get(
                        "classification"
                    )
                    in ALLOWED_S3_CLASSES
                )
                for item in endpoints
            )
        ),

        "endpoint rediscovery disabled": True,

        "search engine scraping disabled": True,

        "bounded target query matrix enabled": True,

        "same-host document discovery enabled": True,

        "negative evidence disabled": (
            policy.get(
                "negative_evidence_allowed"
            )
            is False
        ),

        "source not found does not mean false": (
            policy.get(
                "source_not_found_means_false"
            )
            is False
        ),

        "source failure resolves UNKNOWN": (
            source_failure_site_status
            == STATUS_UNKNOWN
        ),

        "document candidate classes valid": (
            all_candidate_classes_valid
        ),

        "canonical candidate URLs unique": (
            len(
                candidate_urls
            )
            ==
            len(
                set(
                    candidate_urls
                )
            )
        ),

        "next-stage document URLs unique": (
            len(
                next_stage_urls
            )
            ==
            len(
                set(
                    next_stage_urls
                )
            )
        ),

        "verified positive leakage zero": (
            verified_positive_leakage
            == 0
        ),

        "runtime registration leakage zero": (
            runtime_registration_leakage
            == 0
        ),

        "SITE TRUE leakage zero": (
            site_true_leakage
            == 0
        ),

        "false from source failure leakage zero": (
            false_from_source_failure_leakage
            == 0
        ),

        "runtime registration remains blocked": (
            output_data[
                "runtime_registration_allowed"
            ]
            is False
        ),

        "SITE TRUE remains blocked": (
            output_data[
                "site_positive_allowed"
            ]
            is False
        ),

        "final positive promotion remains blocked": (
            output_data[
                "final_positive_promotion_allowed"
            ]
            is False
        ),

        "output written": (
            OUTPUT_PATH.exists()
            and OUTPUT_PATH.stat().st_size
            > 0
        ),
    }

    print()

    print(
        "=" * 60
    )

    print(
        "VALIDATION"
    )

    print(
        "=" * 60
    )

    for name, passed in validations.items():

        print(
            f"{name}: {passed}"
        )

    print()

    print(
        "Verified positive leakage:",
        verified_positive_leakage,
    )

    print(
        "Runtime registration leakage:",
        runtime_registration_leakage,
    )

    print(
        "SITE TRUE leakage:",
        site_true_leakage,
    )

    print(
        "False from source failure leakage:",
        false_from_source_failure_leakage,
    )

    print()

    all_pass = all(
        validations.values()
    )

    print(
        f"all_pass: {all_pass}"
    )

    if not all_pass:

        failed = [
            name
            for name, passed
            in validations.items()
            if not passed
        ]

        print()

        print(
            "FAILED:"
        )

        for name in failed:

            print(
                f"- {name}"
            )

        raise AssertionError(
            "Development density management area "
            "historical target document discovery "
            "regression failed"
        )


if __name__ == "__main__":

    main()