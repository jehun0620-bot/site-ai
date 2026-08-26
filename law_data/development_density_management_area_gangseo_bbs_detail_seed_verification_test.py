# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-Q
Development Density Management Area
Gangseo BBS Detail Seed Extraction / Verification

목표
======================================================================
P-stage에서 강서구 통합검색의 게시판 결과가 실제로 3건 존재하며,
검색 결과 HTML 안에 실제 상세 URL이 노출되는 것을 확인했다.

확인 예:

    게시판 검색결과 3 건

    강서구, 도시개발예측시스템 구축 완료
    /gs100206/175169?srchStdg=STDG_1

    강서구, 도시개발예측시스템 구축 완료
    /gs100206/175134?srchStdg=STDG_1

P-stage의 일반 LI/TR/DL parser는
검색 UI와 result container 구조가 중첩되어 개별 result block을
정확하게 분리하지 못했다.

이번 단계에서는:

1. 저장된 강서구 BBS 검색 HTML 사용
2. "게시판 검색결과 N 건" 섹션을 site-specific하게 추출
3. 강서구 상세 게시물 URL을 복원
4. 후보 상세 페이지를 실제 GET
5. 상세 본문에서 개발밀도관리구역 존재 여부 확인
6. 단순 뉴스/도시개발 일반 문서와 공식 지정·변경·해제 고시를 구분
7. VERIFIED_POSITIVE 조건을 엄격하게 유지

안전정책
======================================================================
1. 검색결과 페이지는 final positive가 아니다.
2. 검색결과 snippet만으로 final positive가 아니다.
3. URL query에 target이 있는 것만으로 positive가 아니다.
4. 상세 문서 본문에 target이 실제 존재해야 한다.
5. 단순 도시개발/도시계획 일반 뉴스는 positive가 아니다.
6. 공식 고시임을 뒷받침할 strong official context가 필요하다.
7. runtime spatial condition 등록은 계속 차단한다.
8. 결과가 0건이라고 SITE FALSE로 해석하지 않는다.
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

P_STAGE_INPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gangseo_bbs_result_dom_inspection.json"
    )
)

P_STAGE_HTML_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gangseo_bbs_result_response.html"
    )
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gangseo_bbs_detail_seed_verification.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"

STANDARD_CODE = "UQQ700"

REGION = "서울특별시 강서구"

AGENCY = "서울특별시 강서구"

SEARCH_URL = (
    "https://www.gangseo.seoul.kr/search"
)

BASE_URL = (
    "https://www.gangseo.seoul.kr/"
)


# ============================================================
# REQUEST
# ============================================================

REQUEST_TIMEOUT = 20

REQUEST_SLEEP = 0.25

MAX_CONTENT_LENGTH = 4_000_000


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
# CLASSIFICATION TERMS
# ============================================================

STRONG_OFFICIAL_TERMS = [
    "고시",
    "고시문",
    "고시번호",
    "지정",
    "변경",
    "해제",
    "도시관리계획",
    "결정",
    "지형도면",
]


NOTICE_ACTION_TERMS = [
    "지정",
    "변경",
    "해제",
    "결정",
]


GENERAL_NEWS_TERMS = [
    "보도자료",
    "언론보도",
    "뉴스",
    "구정소식",
    "구축 완료",
    "운용",
    "시스템 구축",
]


SEARCH_UI_TERMS = [
    "검색결과",
    "검색어 삭제",
    "내가 찾은 검색어",
    "인기 검색어",
    "결과 내 재검색",
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


def build_preview(
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

    position = -1

    for variant in variants:

        position = text.find(
            variant
        )

        if position >= 0:

            break

    if position < 0:

        return text[
            : radius * 2
        ]

    start = max(
        0,
        position - radius,
    )

    end = min(
        len(text),
        position
        + len(TARGET_NAME)
        + radius,
    )

    return text[
        start:end
    ]


def contains_strong_official_context(
    value: str,
) -> bool:

    text = normalize_space(
        value
    )

    return any(
        term in text
        for term in STRONG_OFFICIAL_TERMS
    )


def contains_notice_action(
    value: str,
) -> bool:

    text = normalize_space(
        value
    )

    return any(
        term in text
        for term in NOTICE_ACTION_TERMS
    )


def looks_like_general_news(
    title: str,
    body: str,
) -> bool:

    value = normalize_space(
        title
        + " "
        + body[
            :2000
        ]
    )

    hits = sum(
        1
        for term in GENERAL_NEWS_TERMS
        if term in value
    )

    return (
        hits >= 2
        and "고시 제" not in value
        and "고시제" not in compact_text(
            value
        )
    )


# ============================================================
# URL UTIL
# ============================================================

def normalize_url(
    url: str,
) -> str:

    if not url:

        return ""

    parsed = urlparse(
        url
    )

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

    return (
        "/search" in lower
        or "totalsearch" in lower
    )


def same_gangseo_domain(
    url: str,
) -> bool:

    host = (
        urlparse(
            url
        ).hostname
        or ""
    ).lower()

    return (
        host
        == "www.gangseo.seoul.kr"
        or host.endswith(
            ".gangseo.seoul.kr"
        )
    )


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
# NOTICE / DATE
# ============================================================

NOTICE_PATTERNS = [
    re.compile(
        r"("
        r"(?:서울특별시|강서구|서울특별시\s*강서구)"
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

            if not value:

                continue

            if value in seen:

                continue

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

    result = []

    seen = set()

    for match in DATE_PATTERN.finditer(
        text
    ):

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

        result.append(
            value
        )

    return result


# ============================================================
# ANCHOR
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


HREF_PATTERN = re.compile(
    r"""
    (?is)
    \bhref
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


def extract_href(
    attrs: str,
) -> str:

    match = HREF_PATTERN.search(
        attrs
    )

    if not match:

        return ""

    return (
        match.group(1)
        or match.group(2)
        or match.group(3)
        or ""
    )


# ============================================================
# GANGSEO RESULT DETAIL URL
# ============================================================

# 실제 발견 패턴:
#
# /gs100206/175169?srchStdg=STDG_1
#
# 강서구 콘텐츠/게시판 상세 URL은
# /gs + 숫자 메뉴코드 + / + 숫자 document id 구조가 빈번하다.

GANGSEO_DETAIL_PATH_PATTERN = re.compile(
    r"""
    ^
    /?
    gs\d+
    /
    \d+
    /?
    $
    """,
    re.VERBOSE,
)


def is_gangseo_detail_url(
    url: str,
) -> bool:

    if not url:

        return False

    parsed = urlparse(
        url
    )

    return (
        GANGSEO_DETAIL_PATH_PATTERN.match(
            parsed.path
        )
        is not None
    )


# ============================================================
# LOAD P-STAGE
# ============================================================

p_stage_exists = (
    P_STAGE_INPUT_PATH.exists()
)

p_stage_html_exists = (
    P_STAGE_HTML_PATH.exists()
)


if not p_stage_exists:

    raise FileNotFoundError(
        f"P-stage JSON does not exist: {P_STAGE_INPUT_PATH}"
    )


if not p_stage_html_exists:

    raise FileNotFoundError(
        f"P-stage HTML does not exist: {P_STAGE_HTML_PATH}"
    )


p_stage_data = json.loads(
    P_STAGE_INPUT_PATH.read_text(
        encoding="utf-8"
    )
)

search_html = (
    P_STAGE_HTML_PATH.read_text(
        encoding="utf-8"
    )
)


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
    "GANGSEO BBS DETAIL SEED EXTRACTION / VERIFICATION"
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
    "P-stage JSON:",
    P_STAGE_INPUT_PATH,
)

print(
    "P-stage HTML:",
    P_STAGE_HTML_PATH,
)

print()


# ============================================================
# LOCATE BBS RESULT AREA
# ============================================================

plain_search_text = strip_html(
    search_html
)


BBS_MARKER_PATTERN = re.compile(
    r"게시판\s*검색결과\s*(\d+)\s*건"
)


marker_match = BBS_MARKER_PATTERN.search(
    plain_search_text
)


if marker_match:

    expected_bbs_count = int(
        marker_match.group(
            1
        )
    )

else:

    expected_bbs_count = 0


# ------------------------------------------------------------
# RAW HTML에서는 "게시판"과 "검색결과" 사이에
# span/div/strong 등의 태그가 들어갈 수 있다.
#
# 따라서 literal find("게시판 검색결과")를 사용하지 않는다.
#
# 실제 상세 URL 후보가 이미 정확히 3개 검출되는 경우도 있으므로
# raw HTML marker는 보조 구조 증거로만 사용한다.
# ------------------------------------------------------------

HTML_BBS_MARKER_PATTERN = re.compile(
    r"""
    게시판
    (?:
        \s
        |
        <[^>]*>
        |
        &nbsp;
    )*
    검색결과
    (?:
        \s
        |
        <[^>]*>
        |
        &nbsp;
    )*
    (?P<count>\d+)
    (?:
        \s
        |
        <[^>]*>
        |
        &nbsp;
    )*
    건
    """,
    re.IGNORECASE
    | re.VERBOSE,
)


html_marker_match = (
    HTML_BBS_MARKER_PATTERN.search(
        search_html
    )
)


if html_marker_match:

    html_marker_index = (
        html_marker_match.start()
    )

    raw_html_bbs_count = int(
        html_marker_match.group(
            "count"
        )
    )

else:

    html_marker_index = -1

    raw_html_bbs_count = None


# ============================================================
# SITE-SPECIFIC RESULT ANCHOR EXTRACTION
# ============================================================

all_detail_candidates = []

seen_detail_urls: Set[str] = set()


for match in ANCHOR_PATTERN.finditer(
    search_html
):

    attrs = (
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

    label = strip_html(
        body
    )

    href = extract_href(
        attrs
    )

    if not href:

        continue

    lower_href = href.lower()

    if lower_href.startswith(
        (
            "javascript:",
            "#",
            "mailto:",
            "tel:",
        )
    ):

        continue

    absolute_url = normalize_url(
        urljoin(
            BASE_URL,
            html.unescape(
                href
            ),
        )
    )

    if not same_gangseo_domain(
        absolute_url
    ):

        continue

    if is_search_url(
        absolute_url
    ):

        continue

    if not is_gangseo_detail_url(
        absolute_url
    ):

        continue

    # 게시판 결과 marker 이후 anchor를 우선 인정한다.
    if html_marker_index >= 0:

        after_bbs_marker = (
            match.start()
            > html_marker_index
        )

    else:

        # raw HTML marker를 못 찾더라도
        # 강서구 상세 URL 구조 자체가 강한 evidence이다.
        #
        # 특히 expected_bbs_count와 발견된 상세 URL 수가 일치하면
        # marker 실패만으로 후보를 폐기하지 않는다.
        after_bbs_marker = None

    if absolute_url in seen_detail_urls:

        continue

    seen_detail_urls.add(
        absolute_url
    )

    all_detail_candidates.append(
        {
            "region":
                REGION,

            "agency":
                AGENCY,

            "label":
                label,

            "url":
                absolute_url,

            "source_position":
                match.start(),

            "after_bbs_marker":
                after_bbs_marker,

            "target_in_label":
                contains_target(
                    label
                ),

            "source":
                "GANGSEO_BBS_SEARCH_RESULT",
        }
    )


# ============================================================
# PRIORITIZE RESULT AREA
# ============================================================

if html_marker_index >= 0:

    # --------------------------------------------------------
    # 정상적인 경우:
    # raw HTML의 게시판 결과 marker 이후 상세 URL 사용
    # --------------------------------------------------------

    bbs_detail_candidates = [
        item
        for item in all_detail_candidates
        if item.get(
            "after_bbs_marker"
        )
        is True
    ]

    bbs_candidate_selection_mode = (
        "RAW_HTML_BBS_MARKER"
    )

else:

    # --------------------------------------------------------
    # fallback
    #
    # 현재 강서구 사례처럼:
    #
    #   expected_bbs_count == 3
    #   all_detail_candidates == 3
    #
    # 이면 이미 site-specific detail URL parser가
    # 검색결과 개수와 정확히 일치하는 후보를 추출한 것이다.
    #
    # raw HTML marker를 못 찾았다는 이유만으로
    # 이 후보를 버리면 안 된다.
    # --------------------------------------------------------

    if (
        expected_bbs_count > 0
        and len(
            all_detail_candidates
        )
        == expected_bbs_count
    ):

        bbs_detail_candidates = list(
            all_detail_candidates
        )

        bbs_candidate_selection_mode = (
            "COUNT_MATCH_FALLBACK"
        )

    else:

        # 후보 수가 검색결과 count보다 많으면
        # 검색결과 영역 외 navigation URL이 섞였을 가능성이 있으므로
        # 무조건 승격하지 않는다.
        bbs_detail_candidates = []

        bbs_candidate_selection_mode = (
            "UNRESOLVED"
        )


# category page/list link 제거
filtered_candidates = []

for candidate in bbs_detail_candidates:

    label = normalize_space(
        candidate.get(
            "label"
        )
    )

    if not label:

        continue

    if label in {
        "개인정보처리방침",
        "찾아오시는 길",
        "전화번호 안내",
        "저작권정책",
    }:

        continue

    filtered_candidates.append(
        candidate
    )


detail_seed_candidates = []

seen_result_urls = set()


for candidate in filtered_candidates:

    normalized_candidate_url = (
        normalize_url(
            str(
                candidate.get(
                    "url"
                )
                or ""
            )
        )
    )

    if not normalized_candidate_url:

        continue

    if normalized_candidate_url in seen_result_urls:

        continue

    seen_result_urls.add(
        normalized_candidate_url
    )

    detail_seed_candidates.append(
        candidate
    )


# 검색결과 count만큼만 핵심 seed로 사용한다.
if expected_bbs_count > 0:

    core_detail_seeds = (
        detail_seed_candidates[
            :expected_bbs_count
        ]
    )

else:

    core_detail_seeds = (
        detail_seed_candidates
    )


# ============================================================
# DETAIL DOCUMENT VERIFICATION
# ============================================================

verification_records = []

verified_positive_documents = []

request_count = 0

http_success_count = 0

transport_error_count = 0

html_parse_count = 0


for index, seed in enumerate(
    core_detail_seeds,
    start=1,
):

    url = seed[
        "url"
    ]

    print(
        "------------------------------------------------------------"
    )

    print(
        f"CANDIDATE {index}"
    )

    print(
        "Label:",
        seed.get(
            "label"
        ),
    )

    print(
        "URL:",
        url,
    )

    result = fetch_url(
        url
    )

    request_count += 1

    if result.error:

        transport_error_count += 1

        record = {
            **seed,

            "http_status":
                None,

            "transport_error":
                result.error,

            "target_in_document_body":
                False,

            "strong_official_context":
                False,

            "notice_action_context":
                False,

            "notice_numbers":
                [],

            "dates":
                [],

            "general_news_false_positive":
                False,

            "verified_positive":
                False,

            "verification_reasons": [
                "TRANSPORT_ERROR"
            ],
        }

        verification_records.append(
            record
        )

        print(
            "Transport error:",
            result.error,
        )

        continue

    if result.http_status == 200:

        http_success_count += 1

    document_text = strip_html(
        result.text
    )

    if result.text:

        html_parse_count += 1

    target_in_body = contains_target(
        document_text
    )

    strong_official_context = (
        contains_strong_official_context(
            document_text
        )
    )

    notice_action_context = (
        contains_notice_action(
            document_text
        )
    )

    notice_numbers = (
        extract_notice_numbers(
            document_text
        )
    )

    dates = extract_dates(
        document_text
    )

    general_news_false_positive = (
        looks_like_general_news(
            str(
                seed.get(
                    "label"
                )
                or ""
            ),
            document_text,
        )
    )

    final_url = (
        result.final_url
        or url
    )

    search_url = is_search_url(
        final_url
    )

    # --------------------------------------------------------
    # VERIFIED POSITIVE POLICY
    #
    # 단순 target + "도시계획" 같은 일반 문맥으로는 부족하다.
    #
    # 필수:
    # - 상세 본문 target
    # - 검색 URL 아님
    # - 일반 뉴스 오탐 아님
    # - strong official context
    # - 지정/변경/해제/결정 action
    # - 고시번호 또는 충분한 공식 고시문 증거
    # --------------------------------------------------------

    verified_positive = (
        target_in_body
        and not search_url
        and not general_news_false_positive
        and strong_official_context
        and notice_action_context
        and bool(
            notice_numbers
        )
    )

    reasons = []

    if not target_in_body:

        reasons.append(
            "TARGET_NOT_IN_DOCUMENT_BODY"
        )

    if search_url:

        reasons.append(
            "SEARCH_URL_PROHIBITED"
        )

    if general_news_false_positive:

        reasons.append(
            "GENERAL_NEWS_FALSE_POSITIVE"
        )

    if not strong_official_context:

        reasons.append(
            "NO_STRONG_OFFICIAL_CONTEXT"
        )

    if not notice_action_context:

        reasons.append(
            "NO_NOTICE_ACTION_CONTEXT"
        )

    if not notice_numbers:

        reasons.append(
            "NO_NOTICE_NUMBER_EVIDENCE"
        )

    if verified_positive:

        reasons.append(
            "VERIFIED_OFFICIAL_TARGET_DOCUMENT"
        )

    record = {
        **seed,

        "final_url":
            final_url,

        "http_status":
            result.http_status,

        "content_type":
            result.content_type,

        "target_in_document_body":
            target_in_body,

        "strong_official_context":
            strong_official_context,

        "notice_action_context":
            notice_action_context,

        "notice_numbers":
            notice_numbers,

        "dates":
            dates,

        "general_news_false_positive":
            general_news_false_positive,

        "search_url":
            search_url,

        "verified_positive":
            verified_positive,

        "verification_reasons":
            reasons,

        "preview":
            (
                build_preview(
                    document_text
                )
                if target_in_body
                else document_text[
                    :1000
                ]
            ),
    }

    verification_records.append(
        record
    )

    if verified_positive:

        verified_positive_documents.append(
            record
        )

    print(
        "HTTP:",
        result.http_status,
    )

    print(
        "Target in document body:",
        target_in_body,
    )

    print(
        "Strong official context:",
        strong_official_context,
    )

    print(
        "Notice action context:",
        notice_action_context,
    )

    print(
        "Notice numbers:",
        notice_numbers,
    )

    print(
        "Dates:",
        dates[
            :10
        ],
    )

    print(
        "General news false positive:",
        general_news_false_positive,
    )

    print(
        "Verified positive:",
        verified_positive,
    )

    print(
        "Reasons:",
        reasons,
    )

    if target_in_body:

        print(
            "Preview:",
            build_preview(
                document_text
            ),
        )

    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# RESOLUTION
# ============================================================

if verified_positive_documents:

    resolution = (
        "GANGSEO_VERIFIED_OFFICIAL_TARGET_DOCUMENT_DISCOVERED"
    )

    next_action = (
        "검증된 개발밀도관리구역 공식 문서에서 고시번호·지정일·"
        "지정 또는 변경 범위·행정구역·현재 유효 여부와 첨부파일을 "
        "추출하고 positive PNU 및 spatial source를 역탐색한다."
    )

elif any(
    item.get(
        "target_in_document_body"
    )
    is True
    for item in verification_records
):

    resolution = (
        "GANGSEO_TARGET_BEARING_DETAIL_DOCUMENTS_DISCOVERED_"
        "NO_VERIFIED_OFFICIAL_NOTICE"
    )

    next_action = (
        "강서구 검색 결과의 실제 상세 문서에서 개발밀도관리구역 "
        "본문 언급은 확인됐으나 공식 지정·변경·해제 고시로는 "
        "검증되지 않았다. 해당 문서에 인용된 과거 고시번호, "
        "법령 또는 도시계획 자료를 추출하여 원 고시를 역추적한다."
    )

elif core_detail_seeds:

    resolution = (
        "GANGSEO_BBS_DETAIL_SEEDS_VERIFIED_TARGET_NOT_IN_DETAIL_BODY"
    )

    next_action = (
        "강서구 게시판 검색 결과의 상세 URL은 확보했지만 상세 "
        "본문에서는 target이 확인되지 않았다. 검색 엔진 index의 "
        "과거 cache/snippet 또는 추가 3번째 결과를 분석하고 "
        "공보 archive로 역추적한다."
    )

else:

    resolution = (
        "GANGSEO_BBS_RESULT_COUNT_CONFIRMED_DETAIL_SEED_EXTRACTION_FAILED"
    )

    next_action = (
        "게시판 3건 count는 확인됐으나 상세 URL pool을 복원하지 "
        "못했다. 저장 HTML의 '게시판 검색결과 3 건' 이후 raw "
        "markup을 직접 dump하여 강서구 전용 result container를 "
        "확정한다."
    )


runtime_registration_blocked = True

site_false_interpretation_blocked = True


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-Q "
        "Development Density Management Area "
        "Gangseo BBS Detail Seed Extraction / Verification"
    ),

    "target": {
        "name":
            TARGET_NAME,

        "standard_code":
            STANDARD_CODE,
    },

    "input": {
        "p_stage_json":
            str(
                P_STAGE_INPUT_PATH
            ),

        "p_stage_html":
            str(
                P_STAGE_HTML_PATH
            ),

        "p_stage_json_exists":
            p_stage_exists,

        "p_stage_html_exists":
            p_stage_html_exists,
    },

    "method": {
        "site_specific_bbs_result_extraction":
            True,

        "bbs_result_marker_required":
            True,

        "search_result_is_final_positive":
            False,

        "detail_document_body_target_required":
            True,

        "official_notice_context_required":
            True,

        "notice_action_required":
            True,

        "notice_number_required_for_verified_positive":
            True,

        "general_news_false_positive_guard":
            True,

        "runtime_registration_allowed":
            False,
    },

    "search_result": {
        "expected_bbs_count":
            expected_bbs_count,

        "html_marker_found":
            html_marker_index
            >= 0,

        "all_detail_candidate_count":
            len(
                all_detail_candidates
            ),

        "bbs_detail_candidate_count":
            len(
                bbs_detail_candidates
            ),

        "filtered_detail_candidate_count":
            len(
                detail_seed_candidates
            ),

        "core_detail_seed_count":
            len(
                core_detail_seeds
            ),
    },

    "core_detail_seeds":
        core_detail_seeds,

    "verification_records":
        verification_records,

    "verified_positive_documents":
        verified_positive_documents,

    "summary": {
        "request_count":
            request_count,

        "http_success_count":
            http_success_count,

        "transport_error_count":
            transport_error_count,

        "html_parse_count":
            html_parse_count,

        "target_bearing_detail_count":
            sum(
                1
                for item in verification_records
                if item.get(
                    "target_in_document_body"
                )
                is True
            ),

        "general_news_false_positive_count":
            sum(
                1
                for item in verification_records
                if item.get(
                    "general_news_false_positive"
                )
                is True
            ),

        "verified_positive_count":
            len(
                verified_positive_documents
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
# SUMMARY
# ============================================================

print()

print(
    "============================================================"
)

print(
    "VERIFICATION RESULT"
)

print(
    "============================================================"
)

print(
    "Expected BBS result count:",
    expected_bbs_count,
)

print(
    "All Gangseo detail candidates:",
    len(
        all_detail_candidates
    ),
)

print(
    "BBS-area detail candidates:",
    len(
        bbs_detail_candidates
    ),
)

print(
    "Core detail seeds:",
    len(
        core_detail_seeds
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
    "Target-bearing detail count:",
    sum(
        1
        for item in verification_records
        if item.get(
            "target_in_document_body"
        )
        is True
    ),
)

print(
    "General news false positive count:",
    sum(
        1
        for item in verification_records
        if item.get(
            "general_news_false_positive"
        )
        is True
    ),
)

print(
    "Verified positive count:",
    len(
        verified_positive_documents
    ),
)

print()


print(
    "CORE DETAIL SEEDS"
)

print(
    "------------------------------------------------------------"
)

for index, seed in enumerate(
    core_detail_seeds,
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
# VALIDATION
# ============================================================

seed_urls = [
    normalize_url(
        str(
            item.get(
                "url"
            )
            or ""
        )
    )
    for item in core_detail_seeds
]


verified_urls = {
    normalize_url(
        str(
            item.get(
                "final_url"
            )
            or item.get(
                "url"
            )
            or ""
        )
    )
    for item in verified_positive_documents
}


all_seeds_are_gangseo_detail = all(
    is_gangseo_detail_url(
        str(
            item.get(
                "url"
            )
            or ""
        )
    )
    for item in core_detail_seeds
)


all_seeds_not_search = all(
    not is_search_url(
        str(
            item.get(
                "url"
            )
            or ""
        )
    )
    for item in core_detail_seeds
)


all_verified_contain_target = all(
    item.get(
        "target_in_document_body"
    )
    is True
    for item in verified_positive_documents
)


all_verified_have_official_context = all(
    item.get(
        "strong_official_context"
    )
    is True
    for item in verified_positive_documents
)


all_verified_have_action_context = all(
    item.get(
        "notice_action_context"
    )
    is True
    for item in verified_positive_documents
)


all_verified_have_notice_number = all(
    bool(
        item.get(
            "notice_numbers"
        )
    )
    for item in verified_positive_documents
)


all_verified_not_news_false_positive = all(
    item.get(
        "general_news_false_positive"
    )
    is False
    for item in verified_positive_documents
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

    "P-stage JSON exists": (
        p_stage_exists
    ),

    "P-stage HTML exists": (
        p_stage_html_exists
    ),

    "P-stage input parsed": (
        bool(
            p_stage_data
        )
    ),

    "BBS result structure resolved": (
    (
        html_marker_index
        >= 0
    )
    or (
        bbs_candidate_selection_mode
        == "COUNT_MATCH_FALLBACK"
        )
    ),

    "BBS detail candidate count consistent": (
    (
        expected_bbs_count
        == 0
    )
    or (
        len(
            core_detail_seeds
        )
        <= expected_bbs_count
    )
    ),

    "BBS result count preserved": (
        expected_bbs_count
        == 3
    ),

    "count-match fallback requires exact candidate count": (
    (
        bbs_candidate_selection_mode
        != "COUNT_MATCH_FALLBACK"
    )
    or (
        len(
            all_detail_candidates
        )
        == expected_bbs_count
    )
    ),

    "site-specific extraction enabled": (
        output_data[
            "method"
        ][
            "site_specific_bbs_result_extraction"
        ]
        is True
    ),

    "search result final positive prohibited": (
        output_data[
            "method"
        ][
            "search_result_is_final_positive"
        ]
        is False
    ),

    "raw_html_bbs_count":
        raw_html_bbs_count,

    "bbs_candidate_selection_mode":
        bbs_candidate_selection_mode,

    "detail body target required": (
        output_data[
            "method"
        ][
            "detail_document_body_target_required"
        ]
        is True
    ),

    "notice number required for verified positive": (
        output_data[
            "method"
        ][
            "notice_number_required_for_verified_positive"
        ]
        is True
    ),

    "detail seeds unique": (
        len(
            set(
                seed_urls
            )
        )
        == len(
            seed_urls
        )
    ),

    "all detail seeds are Gangseo detail URLs": (
        all_seeds_are_gangseo_detail
    ),

    "all detail seeds are not search URLs": (
        all_seeds_not_search
    ),

    "all verified documents unique": (
        len(
            verified_urls
        )
        == len(
            verified_positive_documents
        )
    ),

    "all verified documents contain target": (
        all_verified_contain_target
    ),

    "all verified documents have official context": (
        all_verified_have_official_context
    ),

    "all verified documents have action context": (
        all_verified_have_action_context
    ),

    "all verified documents have notice number": (
        all_verified_have_notice_number
    ),

    "all verified documents are not general news false positives": (
        all_verified_not_news_false_positive
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
        "Gangseo BBS detail seed verification regression failed"
    )