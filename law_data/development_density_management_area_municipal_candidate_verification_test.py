# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-D-2
Development Density Management Area
Municipal Positive Candidate Original Document Verification

목표
======================================================================
STEP 17-21-C-16-8-D에서 발견된 municipal positive candidate가

    실제 개발밀도관리구역 지정 / 변경 / 해제 고시 문서인지

원문 단위로 재검증한다.

현재 discovery candidate:
1. 서울특별시 동대문구 통합검색
2. 경기도 김포시 통합검색


핵심 문제
======================================================================
이전 단계에서는 통합검색 페이지 전체 text를 대상으로

    TARGET_NAME 존재
    +
    strong notice context 존재
    +
    document evidence 존재

를 검사했다.

하지만 통합검색 페이지에는 여러 검색결과가 동시에 존재하므로

    TARGET_NAME은 결과 A
    고시번호는 결과 B
    날짜는 결과 C

에서 나온 뒤 page-level에서 결합될 수 있다.

따라서 search result page 자체는
실제 positive official notice로 확정할 수 없다.


이번 단계의 검증 정책
======================================================================
1. 검색 결과 페이지 자체는 FINAL POSITIVE 금지

2. 검색 페이지에서 same-domain document candidate link 추출

3. 개별 candidate URL을 직접 조회

4. 실제 개별 문서 본문에 TARGET_NAME이 있어야 함

5. TARGET_NAME 주변 local context 안에서 다음을 확인

    지정 / 변경 / 해제
    도시관리계획
    고시 / 공고 / 결정
    지형도면

6. 고시번호 / 공고번호 / 날짜 / 문서 metadata 등의
   document evidence 확인

7. TARGET 주변 문맥과 document evidence가
   같은 개별 문서 안에서 확인될 때만 VERIFIED_POSITIVE

8. 검색결과 페이지, 검색폼, 0건 페이지는 positive 금지

9. 검증 실패를 SITE FALSE로 해석하지 않음

10. VERIFIED_POSITIVE 확보 전까지 runtime registry 등록 금지
"""

from __future__ import annotations

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
        "municipal_candidate_verification.json"
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
# CURRENT DISCOVERY CANDIDATES
# ============================================================
#
# C-16-8-D에서 발견된 2건.
#
# 중요:
# 이 URL 자체는 search result page이므로
# verified positive로 인정하지 않는다.
# ============================================================

SEARCH_CANDIDATES: List[Dict[str, str]] = [

    {
        "region":
            "서울특별시",

        "municipality":
            "동대문구",

        "agency":
            "서울특별시 동대문구",

        "search_url":
            (
                "https://www.ddm.go.kr/"
                "search/search.jsp?"
                "query=%EA%B0%9C%EB%B0%9C%EB%B0%80%EB%8F%84"
                "%EA%B4%80%EB%A6%AC%EA%B5%AC%EC%97%AD"
            ),
    },

    {
        "region":
            "경기도",

        "municipality":
            "김포시",

        "agency":
            "경기도 김포시",

        "search_url":
            (
                "https://www.gimpo.go.kr/"
                "search/search.jsp?"
                "query=%EA%B0%9C%EB%B0%9C%EB%B0%80%EB%8F%84"
                "%EA%B4%80%EB%A6%AC%EA%B5%AC%EC%97%AD"
            ),
    },
]


# ============================================================
# REQUEST CONFIG
# ============================================================

REQUEST_TIMEOUT = 20

REQUEST_SLEEP = 0.25

MAX_CONTENT_LENGTH = (
    2_000_000
)

MAX_LINKS_PER_SEARCH_PAGE = (
    150
)

MAX_DOCUMENT_CANDIDATES_PER_SITE = (
    80
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
        "application/xml;q=0.9,"
        "*/*;q=0.8"
    ),

    "Accept-Language": (
        "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
}


# ============================================================
# CONTEXT POLICY
# ============================================================

STRONG_CONTEXT_TERMS = [

    "개발밀도관리구역 지정",

    "개발밀도관리구역 변경",

    "개발밀도관리구역 해제",

    "개발밀도관리구역 결정",

    "개발밀도관리구역의 지정",

    "개발밀도관리구역의 변경",

    "개발밀도관리구역의 해제",

    "개발밀도 관리구역 지정",

    "개발밀도 관리구역 변경",

    "개발밀도 관리구역 해제",

    "도시관리계획",

    "도시계획",

    "지형도면",

    "결정",
]


NOTICE_TERMS = [

    "고시",

    "공고",

    "지정",

    "변경",

    "해제",

    "결정",

    "도시관리계획",

    "지형도면",
]


DOCUMENT_METADATA_TERMS = [

    "고시번호",

    "공고번호",

    "고시 제",

    "고시제",

    "공고 제",

    "공고제",

    "등록일",

    "작성일",

    "게시일",

    "고시일",

    "담당부서",

    "첨부파일",
]


ZERO_RESULT_TERMS = [

    "검색결과 0건",

    "검색 결과 0건",

    "검색결과가 없습니다",

    "검색 결과가 없습니다",

    "검색된 결과가 없습니다",

    "검색 결과 없음",

    "검색결과 없음",

    "총 0건",

    "총0건",
]


SEARCH_PAGE_TERMS = [

    "통합검색",

    "검색어 입력",

    "결과 내 재검색",

    "검색방법",

    "검색범위",
]


LINK_HINT_TERMS = [

    "고시",

    "공고",

    "도시계획",

    "도시관리",

    "개발밀도",

    "개발",

    "토지",

    "지형도면",

    "게시판",

    "board",

    "bbs",

    "view",

    "detail",

    "article",

    "notice",
]


# ============================================================
# REGEX
# ============================================================

NOTICE_PATTERNS = [

    re.compile(
        r"("
        r"(?:서울특별시|부산광역시|대구광역시|인천광역시|"
        r"광주광역시|대전광역시|울산광역시|세종특별자치시|"
        r"경기도|강원특별자치도|충청북도|충청남도|"
        r"전북특별자치도|전라남도|경상북도|경상남도|"
        r"제주특별자치도|"
        r"[가-힣]+시|[가-힣]+군|[가-힣]+구)"
        r"\s*고시\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호?"
        r")"
    ),

    re.compile(
        r"(고시\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호?)"
    ),

    re.compile(
        r"(공고\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호?)"
    ),
]


DATE_PATTERNS = [

    re.compile(
        r"(20\d{2})[.\-/년]\s*"
        r"(0?[1-9]|1[0-2])[.\-/월]\s*"
        r"(0?[1-9]|[12]\d|3[01])(?:일)?"
    ),

    re.compile(
        r"(20\d{2})(0[1-9]|1[0-2])([0-3]\d)"
    ),
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
    html: str,
) -> str:

    value = re.sub(
        r"(?is)<script[^>]*>.*?</script>",
        " ",
        html,
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

    replacements = {

        "&nbsp;": " ",

        "&amp;": "&",

        "&lt;": "<",

        "&gt;": ">",

        "&#39;": "'",

        "&quot;": '"',
    }

    for old, new in replacements.items():

        value = value.replace(
            old,
            new,
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
        str(
            value
            or ""
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


def contains_any(
    value: str,
    terms: List[str],
) -> bool:

    text = normalize_space(
        value
    )

    return any(
        term in text
        for term in terms
    )


def is_zero_result_page(
    value: str,
) -> bool:

    return contains_any(
        value,
        ZERO_RESULT_TERMS,
    )


# ============================================================
# TARGET LOCAL CONTEXT
# ============================================================

def find_target_local_context(
    text: str,
    *,
    radius: int = 700,
) -> str:

    """
    TARGET_NAME 주변 문맥만 추출한다.

    page 전체의 unrelated 고시/날짜가
    target evidence에 섞이는 것을 방지한다.
    """

    normalized = normalize_space(
        text
    )

    variants = [

        "개발밀도관리구역",

        "개발밀도 관리구역",

        "개발 밀도 관리구역",
    ]

    target_index = -1

    matched = ""

    for variant in variants:

        target_index = normalized.find(
            variant
        )

        if (
            target_index
            >= 0
        ):

            matched = variant

            break

    if (
        target_index
        < 0
    ):

        return ""

    start = max(
        0,
        target_index
        - radius,
    )

    end = min(
        len(
            normalized
        ),
        target_index
        + len(
            matched
        )
        + radius,
    )

    return normalized[
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

    cleaned = parsed._replace(
        query=urlencode(
            query_items,
            doseq=True,
        ),
        fragment="",
    )

    return urlunparse(
        cleaned
    )


def same_or_subdomain(
    url: str,
    base_url: str,
) -> bool:

    try:

        target_host = (
            urlparse(
                url
            )
            .hostname
            or ""
        ).lower()

        base_host = (
            urlparse(
                base_url
            )
            .hostname
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
            "."
            + base_host
        )

        or base_host.endswith(
            "."
            + target_host
        )
    )


def is_search_url(
    url: str,
) -> bool:

    lower = (
        url.lower()
    )

    search_hints = (

        "/search/",

        "/search.",

        "/search?",

        "search.jsp",

        "search.do",

        "query=",

        "searchkeyword=",
    )

    return any(
        item in lower
        for item in search_hints
    )


def is_probably_document_url(
    url: str,
) -> bool:

    lower_path = (
        url.lower()
        .split(
            "?",
            1,
        )[0]
    )

    blocked_extensions = (

        ".jpg",

        ".jpeg",

        ".png",

        ".gif",

        ".svg",

        ".webp",

        ".zip",
    )

    if any(
        lower_path.endswith(
            extension
        )
        for extension
        in blocked_extensions
    ):

        return False

    return True


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

    text = (
        response.text
        or ""
    )

    if (
        len(
            text
        )
        > MAX_CONTENT_LENGTH
    ):

        text = text[
            :MAX_CONTENT_LENGTH
        ]

    return FetchResult(

        url=url,

        http_status=response.status_code,

        content_type=(
            response.headers.get(
                "Content-Type",
                "",
            )
        ),

        text=text,

        error=None,

        final_url=response.url,
    )


# ============================================================
# LINK EXTRACTION
# ============================================================

def extract_links(
    html: str,
    *,
    base_url: str,
) -> List[Dict[str, str]]:

    pattern = re.compile(
        r"""(?is)
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

    results = []

    seen = set()

    for match in pattern.finditer(
        html
    ):

        href = (

            match.group(
                1
            )

            or match.group(
                2
            )

            or match.group(
                3
            )

            or ""
        ).strip()

        label_html = (
            match.group(
                4
            )
            or ""
        )

        label = strip_html(
            label_html
        )

        if not href:

            continue

        lowered = (
            href.lower()
        )

        if lowered.startswith(
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
                "url":
                    absolute,

                "label":
                    label,
            }
        )

        if (
            len(
                results
            )
            >= MAX_LINKS_PER_SEARCH_PAGE
        ):

            break

    return results


# ============================================================
# LINK SCORE
# ============================================================

def score_candidate_link(
    link: Dict[str, str],
) -> int:

    label = normalize_space(
        link.get(
            "label"
        )
    )

    url = normalize_space(
        link.get(
            "url"
        )
    )

    haystack = (
        label
        + " "
        + url
    ).lower()

    score = 0

    if contains_target(
        label
    ):

        score += 100

    if contains_target(
        url
    ):

        score += 50

    for term in LINK_HINT_TERMS:

        if (
            term.lower()
            in haystack
        ):

            score += 5

    if is_search_url(
        url
    ):

        score -= 100

    return score


# ============================================================
# NOTICE / DATE EXTRACTION
# ============================================================

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

    for pattern in DATE_PATTERNS:

        for match in pattern.finditer(
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

            except Exception:

                continue

            if not (
                1
                <= month
                <= 12

                and 1
                <= day
                <= 31
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
# DOCUMENT CLASSIFICATION
# ============================================================

def classify_document(
    *,
    region: str,
    municipality: str,
    agency: str,
    url: str,
    html: str,
) -> Dict[str, Any]:

    text = strip_html(
        html
    )

    target_found = contains_target(
        text
    )

    zero_result = is_zero_result_page(
        text
    )

    search_url = is_search_url(
        url
    )

    search_page_text = (
        contains_any(
            text[
                :5000
            ],
            SEARCH_PAGE_TERMS,
        )
    )

    local_context = (
        find_target_local_context(
            text
        )
        if target_found
        else ""
    )

    local_notice_context = (
        contains_any(
            local_context,
            NOTICE_TERMS,
        )
    )

    local_strong_context = (
        contains_any(
            local_context,
            STRONG_CONTEXT_TERMS,
        )
    )

    # --------------------------------------------------------
    # document-wide metadata는 허용하지만
    # TARGET 자체와 strong context는 local window에서 요구한다.
    # --------------------------------------------------------

    notice_numbers = (
        extract_notice_numbers(
            text
        )
    )

    local_notice_numbers = (
        extract_notice_numbers(
            local_context
        )
        if local_context
        else []
    )

    dates = (
        extract_dates(
            text
        )
    )

    local_dates = (
        extract_dates(
            local_context
        )
        if local_context
        else []
    )

    document_metadata = (
        contains_any(
            text,
            DOCUMENT_METADATA_TERMS,
        )
    )

    structured_document_evidence = (
        bool(
            notice_numbers
        )
        or document_metadata
    )

    local_document_evidence = (
        bool(
            local_notice_numbers
        )
        or contains_any(
            local_context,
            DOCUMENT_METADATA_TERMS,
        )
    )

    # ========================================================
    # VERIFIED POSITIVE POLICY
    # ========================================================
    #
    # 검색 URL 자체는 절대 positive가 아니다.
    #
    # 실제 document에서:
    #
    # target
    # +
    # target 주변 strong context
    # +
    # document evidence
    #
    # 필요.
    #
    # local document evidence가 있으면 가장 강함.
    # 그렇지 않더라도 실제 개별 문서에서 document-wide
    # structured evidence가 존재하면 candidate verification을
    # 통과할 수 있다.
    # ========================================================

    verified_positive = (

        target_found

        and not zero_result

        and not search_url

        and not search_page_text

        and local_notice_context

        and local_strong_context

        and structured_document_evidence
    )

    confidence = (
        "HIGH"
        if (
            verified_positive
            and local_document_evidence
        )
        else (
            "MEDIUM"
            if verified_positive
            else "NONE"
        )
    )

    if verified_positive:

        resolution = (
            "VERIFIED_OFFICIAL_DOCUMENT_TARGET_NOTICE"
        )

    elif search_url:

        resolution = (
            "SEARCH_PAGE_NOT_DOCUMENT"
        )

    elif zero_result:

        resolution = (
            "ZERO_RESULT_PAGE"
        )

    elif not target_found:

        resolution = (
            "TARGET_NOT_FOUND_IN_DOCUMENT"
        )

    elif not local_strong_context:

        resolution = (
            "TARGET_FOUND_BUT_NO_LOCAL_STRONG_NOTICE_CONTEXT"
        )

    elif not structured_document_evidence:

        resolution = (
            "TARGET_CONTEXT_FOUND_BUT_DOCUMENT_EVIDENCE_MISSING"
        )

    else:

        resolution = (
            "NOT_VERIFIED"
        )

    return {

        "region":
            region,

        "municipality":
            municipality,

        "agency":
            agency,

        "url":
            url,

        "target_found":
            target_found,

        "zero_result":
            zero_result,

        "search_url":
            search_url,

        "search_page_text":
            search_page_text,

        "local_notice_context":
            local_notice_context,

        "local_strong_context":
            local_strong_context,

        "document_metadata":
            document_metadata,

        "structured_document_evidence":
            structured_document_evidence,

        "local_document_evidence":
            local_document_evidence,

        "notice_numbers":
            notice_numbers,

        "local_notice_numbers":
            local_notice_numbers,

        "dates":
            dates,

        "local_dates":
            local_dates,

        "verified_positive":
            verified_positive,

        "confidence":
            confidence,

        "resolution":
            resolution,

        "local_context":
            local_context,
    }


# ============================================================
# STATE
# ============================================================

candidate_results = []

verified_positive_documents = []

request_count = 0

http_success_count = 0

transport_error_count = 0

document_parse_count = 0

search_page_final_positive_leakage = 0


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
    "MUNICIPAL CANDIDATE ORIGINAL DOCUMENT VERIFICATION"
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
    "Search candidate count:",
    len(
        SEARCH_CANDIDATES
    ),
)

print()


# ============================================================
# VERIFY EACH DISCOVERY SEARCH PAGE
# ============================================================

for candidate_index, candidate in enumerate(
    SEARCH_CANDIDATES,
    start=1,
):

    region = candidate[
        "region"
    ]

    municipality = candidate[
        "municipality"
    ]

    agency = candidate[
        "agency"
    ]

    search_url = candidate[
        "search_url"
    ]

    print(
        "------------------------------------------------------------"
    )

    print(
        f"CANDIDATE {candidate_index}:",
        region,
        municipality,
    )

    print(
        "Search URL:",
        search_url,
    )

    search_result = fetch_url(
        search_url
    )

    request_count += 1

    if search_result.error:

        transport_error_count += 1

        print(
            "Search page error:",
            search_result.error,
        )

        candidate_results.append(
            {
                "region":
                    region,

                "municipality":
                    municipality,

                "agency":
                    agency,

                "search_url":
                    search_url,

                "search_http":
                    None,

                "search_error":
                    search_result.error,

                "document_candidates":
                    [],

                "verified_positive_count":
                    0,
            }
        )

        continue

    if (
        search_result.http_status
        == 200
    ):

        http_success_count += 1

    search_final_url = (
        search_result.final_url
        or search_url
    )

    # ========================================================
    # Search page는 명시적으로 final positive 금지
    # ========================================================

    search_classification = classify_document(
        region=region,
        municipality=municipality,
        agency=agency,
        url=search_final_url,
        html=search_result.text,
    )

    if (
        search_classification[
            "verified_positive"
        ]
    ):

        search_page_final_positive_leakage += 1

    print(
        "Search HTTP:",
        search_result.http_status,
    )

    print(
        "Search target found:",
        search_classification[
            "target_found"
        ],
    )

    print(
        "Search page final positive:",
        search_classification[
            "verified_positive"
        ],
    )

    # ========================================================
    # LINKS
    # ========================================================

    links = extract_links(
        search_result.text,
        base_url=search_final_url,
    )

    base_url = (
        f"{urlparse(search_final_url).scheme}://"
        f"{urlparse(search_final_url).netloc}/"
    )

    filtered_links = []

    seen_urls: Set[str] = set()

    for link in links:

        url = normalize_url(
            link[
                "url"
            ]
        )

        if url in seen_urls:

            continue

        if not same_or_subdomain(
            url,
            base_url,
        ):

            continue

        if not is_probably_document_url(
            url
        ):

            continue

        if is_search_url(
            url
        ):

            continue

        score = score_candidate_link(
            link
        )

        # 너무 강하게 filter하지 않는다.
        # 검색결과의 실제 링크 label이 generic일 수도 있기 때문.
        if (
            score
            < 0
        ):

            continue

        seen_urls.add(
            url
        )

        filtered_links.append(
            {
                "url":
                    url,

                "label":
                    link.get(
                        "label"
                    ),

                "score":
                    score,
            }
        )

    # TARGET label / notice hint link를 우선 검사
    filtered_links.sort(
        key=lambda item: (
            item.get(
                "score",
                0,
            )
        ),
        reverse=True,
    )

    filtered_links = filtered_links[
        :MAX_DOCUMENT_CANDIDATES_PER_SITE
    ]

    print(
        "Extracted links:",
        len(
            links
        ),
    )

    print(
        "Document candidates:",
        len(
            filtered_links
        ),
    )

    document_records = []

    local_verified = []

    # ========================================================
    # FETCH ACTUAL DOCUMENTS
    # ========================================================

    for document_index, link in enumerate(
        filtered_links,
        start=1,
    ):

        document_url = link[
            "url"
        ]

        result = fetch_url(
            document_url
        )

        request_count += 1

        if result.error:

            transport_error_count += 1

            document_records.append(
                {
                    "url":
                        document_url,

                    "label":
                        link.get(
                            "label"
                        ),

                    "score":
                        link.get(
                            "score"
                        ),

                    "http_status":
                        None,

                    "error":
                        result.error,

                    "verified_positive":
                        False,

                    "resolution":
                        "TRANSPORT_ERROR",
                }
            )

            continue

        if (
            result.http_status
            == 200
        ):

            http_success_count += 1

        final_url = (
            result.final_url
            or document_url
        )

        classification = classify_document(
            region=region,
            municipality=municipality,
            agency=agency,
            url=final_url,
            html=result.text,
        )

        document_parse_count += 1

        record = {

            "index":
                document_index,

            "url":
                document_url,

            "final_url":
                final_url,

            "label":
                link.get(
                    "label"
                ),

            "score":
                link.get(
                    "score"
                ),

            "http_status":
                result.http_status,

            "content_type":
                result.content_type,

            **classification,
        }

        document_records.append(
            record
        )

        # target가 있는 문서는 console에 표시
        if classification[
            "target_found"
        ]:

            print()

            print(
                "TARGET DOCUMENT:",
                final_url,
            )

            print(
                "  Label:",
                link.get(
                    "label"
                ),
            )

            print(
                "  Resolution:",
                classification[
                    "resolution"
                ],
            )

            print(
                "  Verified:",
                classification[
                    "verified_positive"
                ],
            )

            print(
                "  Confidence:",
                classification[
                    "confidence"
                ],
            )

            print(
                "  Notice:",
                classification[
                    "notice_numbers"
                ],
            )

            print(
                "  Local notice:",
                classification[
                    "local_notice_numbers"
                ],
            )

            print(
                "  Dates:",
                classification[
                    "dates"
                ],
            )

            print(
                "  Local dates:",
                classification[
                    "local_dates"
                ],
            )

            print(
                "  Context:",
                classification[
                    "local_context"
                ][
                    :1000
                ],
            )

        if classification[
            "verified_positive"
        ]:

            local_verified.append(
                record
            )

            verified_positive_documents.append(
                record
            )

        time.sleep(
            REQUEST_SLEEP
        )

    print()

    print(
        "Verified positive documents:",
        len(
            local_verified
        ),
    )

    candidate_results.append(
        {
            "region":
                region,

            "municipality":
                municipality,

            "agency":
                agency,

            "search_url":
                search_url,

            "search_http":
                search_result.http_status,

            "search_final_url":
                search_final_url,

            "search_target_found":
                search_classification[
                    "target_found"
                ],

            "search_final_positive":
                search_classification[
                    "verified_positive"
                ],

            "extracted_link_count":
                len(
                    links
                ),

            "document_candidate_count":
                len(
                    filtered_links
                ),

            "document_candidates":
                document_records,

            "verified_positive_count":
                len(
                    local_verified
                ),
        }
    )


# ============================================================
# DEDUP VERIFIED
# ============================================================

deduped_verified = []

seen_verified = set()

for item in verified_positive_documents:

    key = normalize_url(
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

    if key in seen_verified:

        continue

    seen_verified.add(
        key
    )

    deduped_verified.append(
        item
    )


# ============================================================
# RESOLUTION
# ============================================================

if deduped_verified:

    resolution = (
        "MUNICIPAL_OFFICIAL_NOTICE_DOCUMENT_VERIFIED"
    )

    next_action = (
        "검증된 원문에서 지정일 / 고시번호 / 지정 범위 / "
        "현재 유효 여부를 확정하고 positive parcel/PNU 및 "
        "공식 spatial source를 역탐색한다."
    )

else:

    resolution = (
        "DISCOVERY_SEARCH_PAGES_NOT_VERIFIED_AS_OFFICIAL_NOTICE"
    )

    next_action = (
        "현재 2개 통합검색 후보를 false positive 또는 "
        "unverified candidate로 유지하고 전국 시군구 탐색 또는 "
        "공보/HWP/PDF 원문 탐색으로 확장한다."
    )


runtime_registration_blocked = (
    True
)


# ============================================================
# OUTPUT
# ============================================================

output_data = {

    "step":
        (
            "STEP 17-21-C-16-8-D-2 "
            "Development Density Management Area "
            "Municipal Candidate Original Document Verification"
        ),

    "target": {

        "name":
            TARGET_NAME,

        "standard_code":
            STANDARD_CODE,
    },

    "policy": {

        "search_page_can_be_final_positive":
            False,

        "target_local_context_required":
            True,

        "strong_notice_context_required":
            True,

        "document_evidence_required":
            True,

        "site_false_interpretation_blocked":
            True,

        "runtime_registration_blocked":
            True,
    },

    "summary": {

        "search_candidate_count":
            len(
                SEARCH_CANDIDATES
            ),

        "request_count":
            request_count,

        "http_success_count":
            http_success_count,

        "transport_error_count":
            transport_error_count,

        "document_parse_count":
            document_parse_count,

        "search_page_final_positive_leakage":
            search_page_final_positive_leakage,

        "verified_positive_document_count":
            len(
                deduped_verified
            ),
    },

    "verified_positive_documents":
        deduped_verified,

    "candidate_results":
        candidate_results,

    "resolution":
        resolution,

    "runtime_registration_blocked":
        runtime_registration_blocked,

    "site_false_interpretation_blocked":
        True,

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
    "VERIFICATION RESULT"
)

print(
    "============================================================"
)

print(
    "Search candidate count:",
    len(
        SEARCH_CANDIDATES
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
    "Document parse count:",
    document_parse_count,
)

print(
    "Search-page positive leakage:",
    search_page_final_positive_leakage,
)

print(
    "Verified positive document count:",
    len(
        deduped_verified
    ),
)

print()


if deduped_verified:

    print(
        "VERIFIED OFFICIAL DOCUMENTS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, item in enumerate(
        deduped_verified,
        start=1,
    ):

        print(
            f"[{index}]",
            item.get(
                "region"
            ),
            item.get(
                "municipality"
            ),
        )

        print(
            "URL:",
            item.get(
                "final_url"
            )
            or item.get(
                "url"
            ),
        )

        print(
            "Confidence:",
            item.get(
                "confidence"
            ),
        )

        print(
            "Notice numbers:",
            item.get(
                "notice_numbers"
            ),
        )

        print(
            "Dates:",
            item.get(
                "dates"
            ),
        )

        print(
            "Local context:",
            item.get(
                "local_context"
            ),
        )

        print()

else:

    print(
        "No municipal official notice document verified."
    )


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

validations = {

    "target name": (
        TARGET_NAME
        == "개발밀도관리구역"
    ),

    "standard code": (
        STANDARD_CODE
        == "UQQ700"
    ),

    "two discovery candidates": (
        len(
            SEARCH_CANDIDATES
        )
        == 2
    ),

    "Dongdaemun candidate exists": (
        any(
            item.get(
                "municipality"
            )
            == "동대문구"
            for item
            in SEARCH_CANDIDATES
        )
    ),

    "Gimpo candidate exists": (
        any(
            item.get(
                "municipality"
            )
            == "김포시"
            for item
            in SEARCH_CANDIDATES
        )
    ),

    "search pages prohibited as final positive": (
        output_data[
            "policy"
        ][
            "search_page_can_be_final_positive"
        ]
        is False
    ),

    "search-page positive leakage zero": (
        search_page_final_positive_leakage
        == 0
    ),

    "requests executed": (
        request_count
        > 0
    ),

    "candidate accounting": (
        len(
            candidate_results
        )
        == len(
            SEARCH_CANDIDATES
        )
    ),

    "verified documents unique": (
        len(
            {
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
                for item
                in deduped_verified
            }
        )
        == len(
            deduped_verified
        )
    ),

    "verified documents contain target": (
        all(
            item.get(
                "target_found"
            )
            is True
            for item
            in deduped_verified
        )
    ),

    "verified documents have local strong context": (
        all(
            item.get(
                "local_strong_context"
            )
            is True
            for item
            in deduped_verified
        )
    ),

    "verified documents have evidence": (
        all(
            item.get(
                "structured_document_evidence"
            )
            is True
            for item
            in deduped_verified
        )
    ),

    "verified documents are not search URLs": (
        all(
            item.get(
                "search_url"
            )
            is False
            for item
            in deduped_verified
        )
    ),

    "verified documents are not zero-result pages": (
        all(
            item.get(
                "zero_result"
            )
            is False
            for item
            in deduped_verified
        )
    ),

    "runtime registration remains blocked": (
        runtime_registration_blocked
        is True
    ),

    "SITE FALSE remains blocked": (
        output_data[
            "site_false_interpretation_blocked"
        ]
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

    raise AssertionError(
        "Development density management area "
        "municipal candidate verification regression failed"
    )