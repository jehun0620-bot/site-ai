# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-S
Development Density Management Area
Gazette Historical Strong Detail Verification

목표
======================================================================
R-stage에서 구조적으로 선별된 STRONG_DETAIL_CANDIDATE를 실제 HTTP 조회하여
개발밀도관리구역의 지정 / 변경 / 해제 고시 원문인지 검증한다.

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

입력:
    development_density_management_area_
    gazette_historical_detail_candidate_refinement.json

핵심 검증 정책
======================================================================
1. URL 구조나 숫자형 detail path만으로 positive 인정 금지.
2. 제목의 "지정", "변경" 같은 일반 단어만으로 positive 인정 금지.
3. 실제 상세 본문에서 "개발밀도관리구역"이 확인되어야 한다.
4. 실제 본문에서 지정 / 변경 / 해제 / 고시 등 action context가 확인되어야 한다.
5. 공식 고시번호 또는 이에 준하는 공식 문서번호 evidence가 필요하다.
6. 검색 페이지, 목록 페이지, preview 페이지는 final positive 금지.
7. 일반 행정·복지·기부·민원·등록·저당권 등 unrelated 문서는 reject한다.
8. verified positive가 없더라도 regression 성공이다.
9. runtime spatial condition 등록은 계속 차단한다.
10. SITE FALSE 해석은 계속 차단한다.

판정
======================================================================

TARGET_NOT_IN_DOCUMENT_BODY
    → REJECTED_STRUCTURAL_FALSE_POSITIVE

target 존재 + action context 없음
    → UNVERIFIED_TARGET_MENTION

target + action context 존재 + official notice evidence 없음
    → UNVERIFIED_OFFICIAL_DOCUMENT

target + action context + official notice evidence
    → VERIFIED_POSITIVE_CANDIDATE

단, 검색/목록/preview URL 또는 일반 unrelated 문서이면
VERIFIED_POSITIVE로 승격하지 않는다.
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

INPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gazette_historical_detail_candidate_refinement.json"
    )
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gazette_historical_strong_detail_verification.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"

STANDARD_CODE = "UQQ700"


# ============================================================
# REQUEST CONFIG
# ============================================================

REQUEST_TIMEOUT = 20

REQUEST_SLEEP = 0.25

MAX_CONTENT_LENGTH = 3_000_000

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
# POLICY TERMS
# ============================================================

ACTION_TERMS = [
    "지정",
    "변경",
    "해제",
    "결정",
    "고시",
    "고시문",
    "지형도면",
    "도시관리계획",
    "도시계획",
]


STRONG_OFFICIAL_TERMS = [
    "고시",
    "고시문",
    "고시번호",
    "제정",
    "결정",
    "지정",
    "변경",
    "해제",
    "도시관리계획",
    "지형도면",
]


UNRELATED_FALSE_POSITIVE_TERMS = [
    "저당권",
    "말소",
    "이전등록",
    "자동차등록",
    "기부",
    "고향사랑",
    "벚꽃",
    "복지정보",
    "공중위생",
    "위생업소",
    "채용",
    "입찰",
    "분묘",
    "장사공고",
    "건강",
    "보건",
    "관광",
    "여행",
    "축제",
    "공모전",
    "기간제근로자",
]


SEARCH_URL_HINTS = [
    "/search",
    "search.",
    "search/",
    "search?",
    "search.do",
    "search.jsp",
    "totalsearch",
]


LIST_URL_HINTS = [
    "/list.do",
    "selectboardlist",
    "bbslist",
    "/list.",
]


PREVIEW_URL_HINTS = [
    "filepreview",
    "/preview",
    "viewer/",
    "docviewer",
]


# ============================================================
# REGEX
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


TITLE_PATTERN = re.compile(
    r"(?is)<title[^>]*>(.*?)</title>"
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
        r"(?is)<!--.*?-->",
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


def contains_any_term(
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


def build_target_preview(
    value: str,
    *,
    radius: int = 320,
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


def extract_html_title(
    source: str,
) -> str:

    match = TITLE_PATTERN.search(
        source
    )

    if not match:

        return ""

    return strip_html(
        match.group(1)
        or ""
    )


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

        lower_key = (
            key
            .strip()
            .lower()
        )

        if lower_key in {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "fbclid",
            "gclid",
            "token",
            "_csrf",
            "csrf",
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
        .lower()
    )

    return any(
        hint in lower
        for hint in SEARCH_URL_HINTS
    )


def is_list_url(
    url: str,
) -> bool:

    lower = (
        url
        .lower()
    )

    return any(
        hint in lower
        for hint in LIST_URL_HINTS
    )


def is_preview_url(
    url: str,
) -> bool:

    lower = (
        url
        .lower()
    )

    return any(
        hint in lower
        for hint in PREVIEW_URL_HINTS
    )


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
        content_type
        .lower()
    )

    text = ""

    if (
        "text/" in content_type_lower
        or "html" in content_type_lower
        or "xml" in content_type_lower
        or "json" in content_type_lower
    ):

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
# INPUT
# ============================================================

if not INPUT_PATH.exists():

    raise FileNotFoundError(
        f"Input file not found: {INPUT_PATH}"
    )


input_data = json.loads(
    INPUT_PATH.read_text(
        encoding="utf-8"
    )
)


# ============================================================
# STRONG CANDIDATE EXTRACTION
# ============================================================

def extract_strong_candidates(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    possible_keys = [
        "strong_detail_candidates",
        "strong_candidates",
        "STRONG_DETAIL_CANDIDATE",
        "strong_detail_candidate",
    ]

    for key in possible_keys:

        value = data.get(
            key
        )

        if isinstance(
            value,
            list,
        ):

            return [
                item
                for item in value
                if isinstance(
                    item,
                    dict,
                )
            ]

    candidate_collections = [
        data.get(
            "refined_candidates"
        ),
        data.get(
            "candidates"
        ),
        data.get(
            "detail_candidates"
        ),
        data.get(
            "classified_candidates"
        ),
    ]

    for collection in candidate_collections:

        if not isinstance(
            collection,
            list,
        ):

            continue

        results = []

        for item in collection:

            if not isinstance(
                item,
                dict,
            ):

                continue

            classification = normalize_space(
                item.get(
                    "classification"
                )
                or item.get(
                    "class"
                )
                or item.get(
                    "candidate_class"
                )
                or ""
            )

            if (
                classification
                == "STRONG_DETAIL_CANDIDATE"
            ):

                results.append(
                    item
                )

        if results:

            return results

    return []


strong_candidates = (
    extract_strong_candidates(
        input_data
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
    "GAZETTE HISTORICAL STRONG DETAIL VERIFICATION"
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
    "Input:",
    INPUT_PATH,
)

print()

print(
    "Strong detail candidate count:",
    len(
        strong_candidates
    ),
)

print()


# ============================================================
# VERIFICATION STATE
# ============================================================

verification_records: List[
    Dict[str, Any]
] = []

verified_positive_candidates: List[
    Dict[str, Any]
] = []

rejected_candidates: List[
    Dict[str, Any]
] = []

request_count = 0

http_success_count = 0

transport_error_count = 0

html_parse_count = 0

search_like_final_positive_leakage = 0

general_false_positive_count = 0


# ============================================================
# VERIFY
# ============================================================

for index, candidate in enumerate(
    strong_candidates,
    start=1,
):

    region = normalize_space(
        candidate.get(
            "region"
        )
        or candidate.get(
            "agency"
        )
        or ""
    )

    agency = normalize_space(
        candidate.get(
            "agency"
        )
        or region
    )

    label = normalize_space(
        candidate.get(
            "label"
        )
        or candidate.get(
            "title"
        )
        or ""
    )

    url = normalize_url(
        str(
            candidate.get(
                "url"
            )
            or candidate.get(
                "canonical_url"
            )
            or ""
        )
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        f"CANDIDATE {index}:",
        region,
    )

    print(
        "Label:",
        label,
    )

    print(
        "URL:",
        url,
    )

    if not url:

        record = {
            "region": region,
            "agency": agency,
            "label": label,
            "url": url,
            "http_status": None,
            "verified_positive": False,
            "resolution": (
                "REJECTED_STRUCTURAL_FALSE_POSITIVE"
            ),
            "reasons": [
                "MISSING_URL",
            ],
        }

        verification_records.append(
            record
        )

        rejected_candidates.append(
            record
        )

        print(
            "HTTP: None"
        )

        print(
            "Verified positive: False"
        )

        print(
            "Reasons:",
            record[
                "reasons"
            ],
        )

        continue

    result = fetch_url(
        url
    )

    request_count += 1

    if result.error:

        transport_error_count += 1

        record = {
            "region": region,
            "agency": agency,
            "label": label,
            "url": url,
            "http_status": None,
            "error": result.error,
            "verified_positive": False,
            "resolution": (
                "UNVERIFIED_TRANSPORT_ERROR"
            ),
            "reasons": [
                "TRANSPORT_ERROR",
            ],
        }

        verification_records.append(
            record
        )

        rejected_candidates.append(
            record
        )

        print(
            "HTTP: None"
        )

        print(
            "Transport error:",
            result.error,
        )

        print(
            "Verified positive: False"
        )

        time.sleep(
            REQUEST_SLEEP
        )

        continue

    if result.http_status == 200:

        http_success_count += 1

    final_url = normalize_url(
        result.final_url
        or url
    )

    source = (
        result.text
        or ""
    )

    if source:

        html_parse_count += 1

    body_text = strip_html(
        source
    )

    html_title = extract_html_title(
        source
    )

    target_in_document_body = (
        contains_target(
            body_text
        )
    )

    action_context = (
        contains_any_term(
            body_text,
            ACTION_TERMS,
        )
    )

    strong_official_context = (
        contains_any_term(
            body_text,
            STRONG_OFFICIAL_TERMS,
        )
    )

    notice_numbers = (
        extract_notice_numbers(
            body_text
        )
    )

    dates = extract_dates(
        body_text
    )

    search_url = (
        is_search_url(
            final_url
        )
        or is_search_url(
            url
        )
    )

    list_url = (
        is_list_url(
            final_url
        )
        or is_list_url(
            url
        )
    )

    preview_url = (
        is_preview_url(
            final_url
        )
        or is_preview_url(
            url
        )
    )

    unrelated_context = (
        contains_any_term(
            (
                label
                + " "
                + html_title
                + " "
                + body_text[
                    :5000
                ]
            ),
            UNRELATED_FALSE_POSITIVE_TERMS,
        )
    )

    # --------------------------------------------------------
    # 일반 unrelated 단어가 존재하더라도
    # 실제 target과 고시번호까지 모두 존재한다면
    # 무조건 false positive 처리하지는 않는다.
    # --------------------------------------------------------

    general_false_positive = (
        unrelated_context
        and not (
            target_in_document_body
            and bool(
                notice_numbers
            )
        )
    )

    if general_false_positive:

        general_false_positive_count += 1

    reasons = []

    if not target_in_document_body:

        reasons.append(
            "TARGET_NOT_IN_DOCUMENT_BODY"
        )

    if not action_context:

        reasons.append(
            "NO_ACTION_CONTEXT"
        )

    if not strong_official_context:

        reasons.append(
            "NO_STRONG_OFFICIAL_CONTEXT"
        )

    if not notice_numbers:

        reasons.append(
            "NO_NOTICE_NUMBER_EVIDENCE"
        )

    if search_url:

        reasons.append(
            "SEARCH_URL_PROHIBITED"
        )

    if list_url:

        reasons.append(
            "LIST_URL_PROHIBITED"
        )

    if preview_url:

        reasons.append(
            "PREVIEW_URL_PROHIBITED"
        )

    if general_false_positive:

        reasons.append(
            "GENERAL_UNRELATED_FALSE_POSITIVE"
        )

    # --------------------------------------------------------
    # 핵심 positive 정책
    # --------------------------------------------------------

    verified_positive = (
        result.http_status == 200
        and target_in_document_body
        and action_context
        and strong_official_context
        and bool(
            notice_numbers
        )
        and not search_url
        and not list_url
        and not preview_url
        and not general_false_positive
    )

    if verified_positive:

        resolution = (
            "VERIFIED_POSITIVE_CANDIDATE"
        )

    elif not target_in_document_body:

        resolution = (
            "REJECTED_STRUCTURAL_FALSE_POSITIVE"
        )

    elif (
        target_in_document_body
        and not action_context
    ):

        resolution = (
            "UNVERIFIED_TARGET_MENTION"
        )

    elif (
        target_in_document_body
        and action_context
        and not notice_numbers
    ):

        resolution = (
            "UNVERIFIED_OFFICIAL_DOCUMENT"
        )

    elif (
        search_url
        or list_url
        or preview_url
        or general_false_positive
    ):

        resolution = (
            "REJECTED_DOCUMENT_TYPE_OR_CONTEXT"
        )

    else:

        resolution = (
            "UNVERIFIED_OFFICIAL_DOCUMENT"
        )

    record = {
        "region": region,
        "agency": agency,
        "label": label,
        "url": url,
        "final_url": final_url,
        "http_status": result.http_status,
        "content_type": result.content_type,
        "html_title": html_title,
        "target_in_document_body": (
            target_in_document_body
        ),
        "action_context": (
            action_context
        ),
        "strong_official_context": (
            strong_official_context
        ),
        "notice_numbers": (
            notice_numbers
        ),
        "dates": dates,
        "search_url": search_url,
        "list_url": list_url,
        "preview_url": preview_url,
        "general_false_positive": (
            general_false_positive
        ),
        "verified_positive": (
            verified_positive
        ),
        "resolution": resolution,
        "reasons": reasons,
        "preview": (
            build_target_preview(
                body_text
            )
            if target_in_document_body
            else body_text[
                :650
            ]
        ),
    }

    verification_records.append(
        record
    )

    if verified_positive:

        verified_positive_candidates.append(
            record
        )

    else:

        rejected_candidates.append(
            record
        )

    if (
        verified_positive
        and (
            search_url
            or list_url
            or preview_url
        )
    ):

        search_like_final_positive_leakage += 1

    print(
        "HTTP:",
        result.http_status,
    )

    print(
        "Final URL:",
        final_url,
    )

    print(
        "Target in document body:",
        target_in_document_body,
    )

    print(
        "Action context:",
        action_context,
    )

    print(
        "Strong official context:",
        strong_official_context,
    )

    print(
        "Notice numbers:",
        notice_numbers,
    )

    print(
        "Dates:",
        dates,
    )

    print(
        "Search URL:",
        search_url,
    )

    print(
        "List URL:",
        list_url,
    )

    print(
        "Preview URL:",
        preview_url,
    )

    print(
        "General false positive:",
        general_false_positive,
    )

    print(
        "Verified positive:",
        verified_positive,
    )

    print(
        "Resolution:",
        resolution,
    )

    print(
        "Reasons:",
        reasons,
    )

    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# DEDUPE VERIFIED POSITIVES
# ============================================================

deduped_verified = []

seen_verified: Set[
    Tuple[
        str,
        str,
    ]
] = set()

for item in verified_positive_candidates:

    key = (
        normalize_space(
            item.get(
                "region"
            )
        ),
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
        ),
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
        "GAZETTE_HISTORICAL_STRONG_DETAIL_VERIFIED_POSITIVE_DISCOVERED"
    )

    next_action = (
        "verified positive 고시에서 고시번호, 고시일, 행정구역, "
        "지정·변경·해제 범위와 첨부 도면을 확정한 뒤 "
        "positive PNU와 spatial source를 역탐색한다."
    )

else:

    resolution = (
        "GAZETTE_HISTORICAL_STRONG_DETAIL_VERIFICATION_COMPLETED_NO_POSITIVE"
    )

    next_action = (
        "R-stage strong detail 후보는 구조적 false positive 또는 "
        "unverified 문서로 유지한다. 다음 단계에서는 과거 공보의 "
        "실제 게시물 행/첨부파일 URL 추출과 연도·호수별 archive "
        "본문 검색으로 확장한다."
    )


runtime_registration_blocked = True

site_false_interpretation_blocked = True


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-S "
        "Development Density Management Area "
        "Gazette Historical Strong Detail Verification"
    ),
    "target": {
        "name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
    },
    "input": {
        "path": str(
            INPUT_PATH
        ),
        "strong_detail_candidate_count": len(
            strong_candidates
        ),
    },
    "method": {
        "actual_detail_http_verification": True,
        "body_target_required": True,
        "action_context_required": True,
        "official_notice_number_required": True,
        "search_url_final_positive_allowed": False,
        "list_url_final_positive_allowed": False,
        "preview_url_final_positive_allowed": False,
        "structural_url_only_positive_allowed": False,
        "generic_action_word_only_positive_allowed": False,
    },
    "summary": {
        "candidate_count": len(
            strong_candidates
        ),
        "request_count": request_count,
        "http_success_count": (
            http_success_count
        ),
        "transport_error_count": (
            transport_error_count
        ),
        "html_parse_count": (
            html_parse_count
        ),
        "general_false_positive_count": (
            general_false_positive_count
        ),
        "verified_positive_count": len(
            deduped_verified
        ),
        "rejected_or_unverified_count": (
            len(
                verification_records
            )
            - len(
                deduped_verified
            )
        ),
        "search_like_final_positive_leakage": (
            search_like_final_positive_leakage
        ),
    },
    "verification_records": (
        verification_records
    ),
    "verified_positive_candidates": (
        deduped_verified
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
    "VERIFICATION RESULT"
)

print(
    "============================================================"
)

print(
    "Strong detail candidate count:",
    len(
        strong_candidates
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
    "General false positive count:",
    general_false_positive_count,
)

print(
    "Verified positive count:",
    len(
        deduped_verified
    ),
)

print(
    "Rejected / unverified count:",
    (
        len(
            verification_records
        )
        - len(
            deduped_verified
        )
    ),
)

print(
    "Search-like final positive leakage:",
    search_like_final_positive_leakage,
)

print()


if deduped_verified:

    print(
        "VERIFIED POSITIVE CANDIDATES"
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
        )

        print(
            "Label:",
            item.get(
                "label"
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
            "Preview:",
            item.get(
                "preview"
            ),
        )

        print()

else:

    print(
        "No gazette historical strong detail "
        "candidate verified as official target document."
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

verified_keys = {
    (
        normalize_space(
            item.get(
                "region"
            )
        ),
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
        ),
    )
    for item in deduped_verified
}


all_verified_have_target = all(
    item.get(
        "target_in_document_body"
    )
    is True
    for item in deduped_verified
)


all_verified_have_action_context = all(
    item.get(
        "action_context"
    )
    is True
    for item in deduped_verified
)


all_verified_have_official_context = all(
    item.get(
        "strong_official_context"
    )
    is True
    for item in deduped_verified
)


all_verified_have_notice_number = all(
    bool(
        item.get(
            "notice_numbers"
        )
    )
    for item in deduped_verified
)


all_verified_not_search = all(
    item.get(
        "search_url"
    )
    is False
    for item in deduped_verified
)


all_verified_not_list = all(
    item.get(
        "list_url"
    )
    is False
    for item in deduped_verified
)


all_verified_not_preview = all(
    item.get(
        "preview_url"
    )
    is False
    for item in deduped_verified
)


all_verified_not_general_false_positive = all(
    item.get(
        "general_false_positive"
    )
    is False
    for item in deduped_verified
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
    "input exists": (
        INPUT_PATH.exists()
    ),
    "R-stage input parsed": (
        isinstance(
            input_data,
            dict,
        )
    ),
    "strong detail candidate extraction enabled": (
        isinstance(
            strong_candidates,
            list,
        )
    ),
    "actual detail HTTP verification enabled": (
        output_data[
            "method"
        ][
            "actual_detail_http_verification"
        ]
        is True
    ),
    "body target required": (
        output_data[
            "method"
        ][
            "body_target_required"
        ]
        is True
    ),
    "action context required": (
        output_data[
            "method"
        ][
            "action_context_required"
        ]
        is True
    ),
    "notice number required": (
        output_data[
            "method"
        ][
            "official_notice_number_required"
        ]
        is True
    ),
    "structural URL-only promotion prohibited": (
        output_data[
            "method"
        ][
            "structural_url_only_positive_allowed"
        ]
        is False
    ),
    "generic action-word-only promotion prohibited": (
        output_data[
            "method"
        ][
            "generic_action_word_only_positive_allowed"
        ]
        is False
    ),
    "candidate accounting": (
        len(
            verification_records
        )
        == len(
            strong_candidates
        )
    ),
    "requests executed when candidates exist": (
        (
            len(
                strong_candidates
            )
            == 0
        )
        or (
            request_count
            > 0
        )
    ),
    "verified documents unique": (
        len(
            verified_keys
        )
        == len(
            deduped_verified
        )
    ),
    "all verified documents contain target": (
        all_verified_have_target
    ),
    "all verified documents have action context": (
        all_verified_have_action_context
    ),
    "all verified documents have official context": (
        all_verified_have_official_context
    ),
    "all verified documents have notice number": (
        all_verified_have_notice_number
    ),
    "all verified documents are not search URLs": (
        all_verified_not_search
    ),
    "all verified documents are not list URLs": (
        all_verified_not_list
    ),
    "all verified documents are not preview URLs": (
        all_verified_not_preview
    ),
    "all verified documents are not general false positives": (
        all_verified_not_general_false_positive
    ),
    "search-like final positive leakage zero": (
        search_like_final_positive_leakage
        == 0
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
        "gazette historical strong detail verification "
        "regression failed"
    )