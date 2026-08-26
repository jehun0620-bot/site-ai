# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-H
Development Density Management Area
Official Board Endpoint Relevance Refinement & Canonicalization

목표
======================================================================
G 단계에서 확보한 공식 지자체 board endpoint 후보를
실제 개발밀도관리구역 탐색에 사용할 수 있도록 의미 기반으로 정제한다.

입력:
    law_data/output/
    development_density_management_area_official_board_endpoint_discovery.json

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 문제
======================================================================
G 단계에서는 공식 사이트의 board 구조를 넓게 수집했기 때문에
다음과 같은 generic / false-positive endpoint가 포함될 수 있다.

예:
    - 칭찬합시다
    - 업무추진비
    - 보도자료
    - 채용공고
    - 입찰공고
    - 분묘개장공고
    - 일반 공지사항
    - 보건소
    - URL에 bbs / board / notice만 포함된 일반 게시판

따라서 H 단계에서는 다음을 수행한다.

1. URL canonicalization
2. token / csrf / jsessionid 등 일회성 값 제거
3. 동일 endpoint 중복 제거
4. 강한 고시/공고 의미 증거 판정
5. 공보/시보 archive 별도 분류
6. 도시계획 관련 board 별도 분류
7. generic board 제거
8. ambiguous endpoint는 SECONDARY_REVIEW로 보존

분류
======================================================================

PRIMARY_GOSI_BOARD
    실제 고시/공고/행정예고 계열 board

GAZETTE_ARCHIVE
    공보 / 시보 / 군보 / 구보 archive

URBAN_PLANNING_BOARD
    도시계획 / 도시관리계획 / 도시정책 계열 자료원

SECONDARY_REVIEW
    구조상 가능성은 있으나 의미 증거가 약한 endpoint

EXCLUDED_GENERIC_BOARD
    일반 게시판, 채용, 입찰, 보도, 민원 등

안전정책
======================================================================
1. endpoint 발견 자체를 SITE TRUE로 해석하지 않는다.
2. endpoint 미발견을 SITE FALSE로 해석하지 않는다.
3. 개발밀도관리구역 실제 게시물/고시가 검증되기 전까지 UNKNOWN 유지.
4. runtime spatial condition 등록은 계속 차단.
5. VWorld LT_C_UQ141을 UQQ700 dataset으로 확정하지 않는다.
6. PRIMARY_GOSI_BOARD 역시 실제 positive notice가 아니다.
"""

from __future__ import annotations

import html
import json
import re

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlparse,
    urlunparse,
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

INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "official_board_endpoint_discovery.json"
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
        "official_board_endpoint_refinement.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"

STANDARD_CODE = "UQQ700"


# ============================================================
# CLASS NAMES
# ============================================================

CLASS_PRIMARY_GOSI = (
    "PRIMARY_GOSI_BOARD"
)

CLASS_GAZETTE = (
    "GAZETTE_ARCHIVE"
)

CLASS_URBAN = (
    "URBAN_PLANNING_BOARD"
)

CLASS_SECONDARY = (
    "SECONDARY_REVIEW"
)

CLASS_EXCLUDED = (
    "EXCLUDED_GENERIC_BOARD"
)

CLASS_NAMES = {
    CLASS_PRIMARY_GOSI,
    CLASS_GAZETTE,
    CLASS_URBAN,
    CLASS_SECONDARY,
    CLASS_EXCLUDED,
}


# ============================================================
# CANONICALIZATION CONFIG
# ============================================================

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "csrftoken",
    "sessionid",
    "jsessionid",
    "timestamp",
    "_",
    "rand",
    "random",
    "cachebuster",
    "cache_buster",
    "cb",
    "ts",
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

VOLATILE_QUERY_KEY_PATTERNS = [
    re.compile(
        r"^token$",
        re.IGNORECASE,
    ),
    re.compile(
        r"csrf",
        re.IGNORECASE,
    ),
    re.compile(
        r"session",
        re.IGNORECASE,
    ),
    re.compile(
        r"timestamp",
        re.IGNORECASE,
    ),
]

JSESSIONID_PATTERN = re.compile(
    r";jsessionid=[^/?]+",
    re.IGNORECASE,
)


# ============================================================
# STRONG SEMANTIC TERMS
# ============================================================

PRIMARY_GOSI_LABEL_TERMS = [
    "고시공고",
    "고시 공고",
    "고시/공고",
    "고시·공고",
    "고시ㆍ공고",
    "고시 및 공고",
    "고시 및공고",
    "고시공고알림",
    "공고알림",
]

PRIMARY_GOSI_URL_TERMS = [
    "/saeol/gosi/",
    "/saeolgosi/",
    "saeolgosi",
    "publicnotice",
    "public_notice",
    "eminwonannounce",
    "/gosi/",
    "gosi/list",
    "gosi.asp",
    "announce.jsp",
]

GAZETTE_LABEL_TERMS = [
    "시보",
    "군보",
    "구보",
    "공보",
]

URBAN_LABEL_TERMS = [
    "도시관리계획",
    "도시계획정보",
    "도시계획",
    "도시정책",
    "도시관리",
    "도시계획정보포털",
]

URBAN_URL_TERMS = [
    "cityplan",
    "urbanplanning",
    "urban-plan",
    "urban_plan",
    "/urban/",
    "/city/",
]


# ============================================================
# EXCLUSION TERMS
# ============================================================

HARD_EXCLUDE_LABEL_TERMS = [
    "입찰공고",
    "입찰 공고",
    "채용공고",
    "채용 공고",
    "분묘개장공고",
    "분묘 개장 공고",
    "무연분묘",
    "장사공고",
    "장사 공고",
    "보도자료",
    "보도해명",
    "언론 보도",
    "칭찬합시다",
    "자유게시판",
    "업무추진비",
    "민원서식",
    "민원 서식",
    "공지사항",
    "새소식",
    "알림광장",
    "재정공시",
    "정보공개",
    "자료실",
    "나눔장터",
    "팝니다",
    "교환",
    "버스시간표",
    "공공체육시설",
    "채용 일자리",
    "일자리",
    "문화행사",
    "포토구정",
]

HEALTH_LABEL_TERMS = [
    "보건소",
    "건강",
    "의료",
    "보건",
]

GENERIC_STRUCTURE_TERMS = [
    "bbs",
    "board",
    "notice",
    "post",
    "list.do",
    "view.do",
]


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


def compact_text(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        "",
        normalize_space(
            value
        ),
    )


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


def contains_any(
    value: str,
    terms: Iterable[str],
) -> bool:

    lowered = normalize_space(
        value
    ).lower()

    return any(
        term.lower()
        in lowered
        for term in terms
    )


def matched_terms(
    value: str,
    terms: Iterable[str],
) -> List[str]:

    lowered = normalize_space(
        value
    ).lower()

    return [
        term
        for term in terms
        if term.lower() in lowered
    ]

def flatten_string_values(
    value: Any,
) -> List[str]:

    results: List[str] = []

    if value is None:
        return results

    if isinstance(
        value,
        str,
    ):
        normalized = normalize_space(
            value
        )

        if normalized:
            results.append(
                normalized
            )

        return results

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        for item in value:
            results.extend(
                flatten_string_values(
                    item
                )
            )

        return results

    return results


def candidate_label_values(
    candidate: Dict[str, Any],
) -> List[str]:
    """
    G 단계 JSON의 label field 명칭 변화에 안전하게 대응한다.
    """

    values: List[str] = []

    candidate_keys = [
        "label",
        "labels",
        "anchor_label",
        "anchor_labels",
        "link_label",
        "link_labels",
        "source_label",
        "source_labels",
        "matched_label",
        "matched_labels",
        "title",
        "titles",
        "text",
    ]

    for key in candidate_keys:
        values.extend(
            flatten_string_values(
                candidate.get(
                    key
                )
            )
        )

    # source / original / raw 등 nested object도 검사
    for nested_key in [
        "source",
        "source_candidate",
        "raw_candidate",
        "original",
        "link",
    ]:

        nested = candidate.get(
            nested_key
        )

        if not isinstance(
            nested,
            dict,
        ):
            continue

        for key in candidate_keys:
            values.extend(
                flatten_string_values(
                    nested.get(
                        key
                    )
                )
            )

    return unique_strings(
        values
    )


def label_semantic_score(
    label: str,
) -> int:

    text = normalize_space(
        label
    )

    if not text:
        return -100

    score = 0

    if contains_any(
        text,
        PRIMARY_GOSI_LABEL_TERMS,
    ):
        score += 30

    if has_gazette_label_evidence(
        text
    ):
        score += 25

    if contains_any(
        text,
        URBAN_LABEL_TERMS,
    ):
        score += 20

    if contains_any(
        text,
        HARD_EXCLUDE_LABEL_TERMS,
    ):
        # exclusion을 인식할 수 있게
        # 빈 label보다 반드시 우선 선택한다.
        score += 15

    score += min(
        len(
            text
        ),
        100,
    ) // 20

    return score


def choose_candidate_label(
    candidate: Dict[str, Any],
) -> str:

    labels = candidate_label_values(
        candidate
    )

    if not labels:
        return ""

    return max(
        labels,
        key=lambda value: (
            label_semantic_score(
                value
            ),
            len(
                value
            ),
        ),
    )

# ============================================================
# CANONICAL URL
# ============================================================
def normalize_query_key(
    key: str,
) -> str:
    """
    G 단계에서 수집된 URL에 다음 형태가 섞일 수 있다.

        &amp;token=...
        amp;token=...
        amp%3Btoken=...
        &amp;mId=...
        amp%3BmId=...

    parse_qsl 이후에는 amp;token / amp;mId 형태가 될 수 있으므로
    query key 자체를 먼저 정규화한다.
    """

    value = html.unescape(
        str(
            key
            or ""
        )
    ).strip()

    # percent decoding은 parse_qsl 단계에서 이미 처리된다.
    # HTML entity 잔여 prefix 제거.
    while value.lower().startswith(
        "amp;"
    ):
        value = value[
            4:
        ].strip()

    return value

def is_volatile_query_key(
    key: str,
) -> bool:

    normalized = normalize_query_key(
        key
    )

    lowered = normalized.lower()

    if lowered in VOLATILE_QUERY_KEYS:
        return True

    if lowered in TRACKING_QUERY_KEYS:
        return True

    if any(
        pattern.search(
            lowered
        )
        is not None
        for pattern in VOLATILE_QUERY_KEY_PATTERNS
    ):
        return True

    # token 계열 변형 방어
    if re.search(
        r"(?:^|[_\-])token$",
        lowered,
        re.IGNORECASE,
    ):
        return True

    if re.search(
        r"(?:^|[_\-])csrf(?:token)?$",
        lowered,
        re.IGNORECASE,
    ):
        return True

    return False


def canonicalize_url(
    url: str,
) -> str:

    value = normalize_space(
        url
    )

    if not value:
        return ""

    # --------------------------------------------------------
    # HTML entity contamination 제거
    #
    # 예:
    #     ?a=1&amp;token=123
    # ->
    #     ?a=1&token=123
    # --------------------------------------------------------

    value = html.unescape(
        value
    )

    try:
        parsed = urlparse(
            value
        )

    except Exception:
        return value

    scheme = (
        parsed.scheme
        or "https"
    ).lower()

    host = (
        parsed.hostname
        or ""
    ).lower()

    if not host:
        return value

    try:
        port = parsed.port
    except ValueError:
        port = None

    if (
        port is not None
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

    path = JSESSIONID_PATTERN.sub(
        "",
        path,
    )

    path = re.sub(
        r"/{2,}",
        "/",
        path,
    )

    query_items = []

    seen_pairs = set()

    for raw_key, query_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        key = normalize_query_key(
            raw_key
        )

        if not key:
            continue

        if is_volatile_query_key(
            key
        ):
            continue

        pair = (
            key,
            query_value,
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


# ============================================================
# LABEL GUARDS
# ============================================================

def is_health_false_gazette_label(
    label: str,
) -> bool:

    """
    '연수구보건소' 안의 '구보'를
    Gazette 증거로 오인하는 문제를 차단한다.
    """

    compact = compact_text(
        label
    )

    if not compact:

        return False

    if (
        "보건소"
        in compact
    ):

        return True

    return False


def has_gazette_label_evidence(
    label: str,
) -> bool:

    text = normalize_space(
        label
    )

    if not text:

        return False

    if is_health_false_gazette_label(
        text
    ):

        return False

    return any(
        term in text
        for term in GAZETTE_LABEL_TERMS
    )


def has_primary_gosi_label_evidence(
    label: str,
) -> bool:

    return contains_any(
        label,
        PRIMARY_GOSI_LABEL_TERMS,
    )


def has_primary_gosi_url_evidence(
    url: str,
) -> bool:

    return contains_any(
        url,
        PRIMARY_GOSI_URL_TERMS,
    )


def has_urban_evidence(
    label: str,
    url: str,
) -> bool:

    return (
        contains_any(
            label,
            URBAN_LABEL_TERMS,
        )
        or contains_any(
            url,
            URBAN_URL_TERMS,
        )
    )


def has_hard_exclusion(
    label: str,
) -> bool:

    return contains_any(
        label,
        HARD_EXCLUDE_LABEL_TERMS,
    )


def looks_generic_only(
    label: str,
    url: str,
    source_terms: List[str],
) -> bool:

    """
    board / bbs / notice 같은 구조 문자열만 존재하고
    고시·공보·도시계획 의미 증거가 없는 경우.
    """

    if has_primary_gosi_label_evidence(
        label
    ):

        return False

    if has_primary_gosi_url_evidence(
        url
    ):

        return False

    if has_gazette_label_evidence(
        label
    ):

        return False

    if has_urban_evidence(
        label,
        url,
    ):

        return False

    semantic_terms = {
        normalize_space(
            term
        ).lower()
        for term in source_terms
        if normalize_space(
            term
        )
    }

    if not semantic_terms:

        return True

    generic = {
        item.lower()
        for item in GENERIC_STRUCTURE_TERMS
    }

    if all(
        any(
            generic_term
            in term
            for generic_term in generic
        )
        for term in semantic_terms
    ):

        return True

    return False


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_endpoint(
    candidate: Dict[str, Any],
) -> Dict[str, Any]:

    region = normalize_space(
        candidate.get(
            "region"
        )
    )

    agency = normalize_space(
        candidate.get(
            "agency"
        )
    )

    raw_url = normalize_space(
        candidate.get(
            "url"
        )
    )

    canonical_url = canonicalize_url(
        raw_url
    )

    all_labels = candidate_label_values(
    candidate
    )

    label = choose_candidate_label(
    candidate
    )

    source_terms = unique_strings(
        candidate.get(
            "matched_terms"
        )
        or candidate.get(
            "terms"
        )
        or []
    )

    target_found = (
        candidate.get(
            "target_found"
        )
        is True
    )

    primary_label_terms = (
        matched_terms(
            label,
            PRIMARY_GOSI_LABEL_TERMS,
        )
    )

    primary_url_terms = (
        matched_terms(
            canonical_url,
            PRIMARY_GOSI_URL_TERMS,
        )
    )

    gazette_terms = []

    if has_gazette_label_evidence(
        label
    ):

        gazette_terms = matched_terms(
            label,
            GAZETTE_LABEL_TERMS,
        )

    urban_label_terms = (
        matched_terms(
            label,
            URBAN_LABEL_TERMS,
        )
    )

    urban_url_terms = (
        matched_terms(
            canonical_url,
            URBAN_URL_TERMS,
        )
    )

    exclusion_terms = matched_terms(
        label,
        HARD_EXCLUDE_LABEL_TERMS,
    )

    generic_only = looks_generic_only(
        label,
        canonical_url,
        source_terms,
    )

    classification_reasons = []

    classification = (
        CLASS_SECONDARY
    )

    score = 0

    # --------------------------------------------------------
    # 1. HARD EXCLUDE
    # --------------------------------------------------------

    if exclusion_terms:

        classification = (
            CLASS_EXCLUDED
        )

        classification_reasons.append(
            "HARD_EXCLUDE_LABEL"
        )

        score = -10

    # --------------------------------------------------------
    # 2. Gazette
    # --------------------------------------------------------

    elif gazette_terms:

        classification = (
            CLASS_GAZETTE
        )

        classification_reasons.append(
            "GAZETTE_LABEL_EVIDENCE"
        )

        score += 8

    # --------------------------------------------------------
    # 3. Primary gosi
    # --------------------------------------------------------

    elif (
        primary_label_terms
        or primary_url_terms
    ):

        classification = (
            CLASS_PRIMARY_GOSI
        )

        if primary_label_terms:

            classification_reasons.append(
                "PRIMARY_GOSI_LABEL_EVIDENCE"
            )

            score += 7

        if primary_url_terms:

            classification_reasons.append(
                "PRIMARY_GOSI_URL_EVIDENCE"
            )

            score += 5

    # --------------------------------------------------------
    # 4. Urban planning
    # --------------------------------------------------------

    elif (
        urban_label_terms
        or urban_url_terms
    ):

        classification = (
            CLASS_URBAN
        )

        classification_reasons.append(
            "URBAN_PLANNING_EVIDENCE"
        )

        score += 6

    # --------------------------------------------------------
    # 5. Generic only
    # --------------------------------------------------------

    elif generic_only:

        classification = (
            CLASS_EXCLUDED
        )

        classification_reasons.append(
            "GENERIC_BOARD_ONLY"
        )

        score = -5

    # --------------------------------------------------------
    # 6. Remaining ambiguous candidate
    # --------------------------------------------------------

    else:

        classification = (
            CLASS_SECONDARY
        )

        classification_reasons.append(
            "AMBIGUOUS_STRUCTURE_EVIDENCE"
        )

        score += 1

    if target_found:

        # 중요:
        # target text 자체는 endpoint를 SITE positive로 만들지 않는다.
        # 단 ranking 보조 신호로만 사용.
        score += 2

        classification_reasons.append(
            "TARGET_TEXT_PRESENT_ON_ENDPOINT_PAGE"
        )

    return {
        "region":
            region,

        "agency":
            agency,

        "raw_url":
            raw_url,

        "canonical_url":
            canonical_url,

        "label":
            label,

        "all_labels":
            all_labels,

        "source_terms":
            source_terms,

        "target_found":
            target_found,

        "classification":
            classification,

        "classification_score":
            score,

        "classification_reasons":
            unique_strings(
                classification_reasons
            ),

        "evidence": {
            "primary_gosi_label_terms":
                primary_label_terms,

            "primary_gosi_url_terms":
                primary_url_terms,

            "gazette_terms":
                gazette_terms,

            "urban_label_terms":
                urban_label_terms,

            "urban_url_terms":
                urban_url_terms,

            "hard_exclusion_terms":
                exclusion_terms,

            "generic_only":
                generic_only,

            "health_false_gazette_guard":
                is_health_false_gazette_label(
                    label
                ),
        },

        "source_candidate":
            candidate,
    }


# ============================================================
# LOAD INPUT
# ============================================================

print(
    "============================================================"
)

print(
    "DEVELOPMENT DENSITY MANAGEMENT AREA"
)

print(
    "OFFICIAL BOARD ENDPOINT RELEVANCE REFINEMENT"
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


if not INPUT_PATH.exists():

    raise FileNotFoundError(
        "G-stage output JSON not found: "
        f"{INPUT_PATH}"
    )


input_data = json.loads(
    INPUT_PATH.read_text(
        encoding="utf-8"
    )
)


# ============================================================
# LOCATE ENDPOINT CANDIDATES
# ============================================================

raw_candidates = (
    input_data.get(
        "accepted_board_endpoints"
    )
)

if raw_candidates is None:

    raw_candidates = (
        input_data.get(
            "board_endpoints"
        )
    )

if raw_candidates is None:

    raw_candidates = (
        input_data.get(
            "official_board_endpoint_candidates"
        )
    )

if raw_candidates is None:

    raw_candidates = []


if not isinstance(
    raw_candidates,
    list,
):

    raise TypeError(
        "Board endpoint collection must be a list."
    )


print(
    "Raw endpoint candidate count:",
    len(
        raw_candidates
    ),
)


# ============================================================
# FALLBACK:
# site_results 내부 accepted endpoints까지 탐색
# ============================================================

if not raw_candidates:

    recovered_candidates = []

    for site in (
        input_data.get(
            "site_results"
        )
        or []
    ):

        region = site.get(
            "region"
        )

        agency = site.get(
            "agency"
        )

        collections = [
            site.get(
                "accepted_board_endpoints"
            ),
            site.get(
                "board_endpoints"
            ),
            site.get(
                "accepted_endpoints"
            ),
        ]

        for collection in collections:

            if not isinstance(
                collection,
                list,
            ):

                continue

            for item in collection:

                if not isinstance(
                    item,
                    dict,
                ):

                    continue

                candidate = dict(
                    item
                )

                candidate.setdefault(
                    "region",
                    region,
                )

                candidate.setdefault(
                    "agency",
                    agency,
                )

                recovered_candidates.append(
                    candidate
                )

    raw_candidates = (
        recovered_candidates
    )

    print(
        "Recovered endpoint candidates from site_results:",
        len(
            raw_candidates
        ),
    )


# ============================================================
# CLASSIFY
# ============================================================

classified_candidates = [
    classify_endpoint(
        item
    )
    for item in raw_candidates
    if isinstance(
        item,
        dict,
    )
]


# ============================================================
# CANONICAL DEDUPE
# ============================================================

grouped: Dict[
    Tuple[
        str,
        str,
    ],
    List[
        Dict[
            str,
            Any
        ]
    ],
] = defaultdict(
    list
)

for item in classified_candidates:

    key = (
        item.get(
            "region"
        )
        or "",
        item.get(
            "canonical_url"
        )
        or "",
    )

    grouped[
        key
    ].append(
        item
    )


CLASS_PRIORITY = {
    CLASS_PRIMARY_GOSI:
        50,

    CLASS_GAZETTE:
        40,

    CLASS_URBAN:
        30,

    CLASS_SECONDARY:
        20,

    CLASS_EXCLUDED:
        10,
}


def choose_group_representative(
    group: List[
        Dict[
            str,
            Any
        ]
    ],
) -> Dict[str, Any]:

    ordered = sorted(
        group,
        key=lambda item: (
            -CLASS_PRIORITY.get(
                item.get(
                    "classification"
                ),
                0,
            ),
            -int(
                item.get(
                    "classification_score"
                )
                or 0
            ),
            -len(
                item.get(
                    "label"
                )
                or ""
            ),
        ),
    )

    representative = dict(
        ordered[
            0
        ]
    )

    representative[
        "raw_variant_count"
    ] = len(
        group
    )

    representative[
        "raw_urls"
    ] = unique_strings(
        item.get(
            "raw_url"
        )
        for item in group
    )

    representative[
        "labels"
    ] = unique_strings(
        item.get(
            "label"
        )
        for item in group
    )

    representative[
        "all_source_terms"
    ] = unique_strings(
        term
        for item in group
        for term in (
            item.get(
                "source_terms"
            )
            or []
        )
    )

    representative[
        "all_classification_reasons"
    ] = unique_strings(
        reason
        for item in group
        for reason in (
            item.get(
                "classification_reasons"
            )
            or []
        )
    )

    representative[
        "source_candidates"
    ] = [
        item.get(
            "source_candidate"
        )
        for item in group
    ]

    representative.pop(
        "source_candidate",
        None,
    )

    return representative


canonical_candidates = [
    choose_group_representative(
        group
    )
    for group in grouped.values()
]


canonical_candidates.sort(
    key=lambda item: (
        -CLASS_PRIORITY.get(
            item.get(
                "classification"
            ),
            0,
        ),
        -int(
            item.get(
                "classification_score"
            )
            or 0
        ),
        str(
            item.get(
                "region"
            )
            or ""
        ),
        str(
            item.get(
                "canonical_url"
            )
            or ""
        ),
    )
)


# ============================================================
# SPLIT BY CLASS
# ============================================================

primary_gosi_boards = [
    item
    for item in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_PRIMARY_GOSI
]

gazette_archives = [
    item
    for item in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_GAZETTE
]

urban_planning_boards = [
    item
    for item in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_URBAN
]

secondary_review = [
    item
    for item in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_SECONDARY
]

excluded_generic_boards = [
    item
    for item in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_EXCLUDED
]


# ============================================================
# NEXT-STAGE SEARCH POOL
# ============================================================

next_stage_search_pool = (
    primary_gosi_boards
    + gazette_archives
    + urban_planning_boards
)

next_stage_search_pool.sort(
    key=lambda item: (
        -CLASS_PRIORITY.get(
            item.get(
                "classification"
            ),
            0,
        ),
        -int(
            item.get(
                "classification_score"
            )
            or 0
        ),
        str(
            item.get(
                "region"
            )
            or ""
        ),
        str(
            item.get(
                "canonical_url"
            )
            or ""
        ),
    )
)


# ============================================================
# SUMMARY
# ============================================================

classification_counts = Counter(
    item.get(
        "classification"
    )
    for item in canonical_candidates
)


raw_url_count = len(
    classified_candidates
)

canonical_url_count = len(
    canonical_candidates
)

duplicate_removed_count = (
    raw_url_count
    - canonical_url_count
)


# ============================================================
# RESOLUTION
# ============================================================

if next_stage_search_pool:

    resolution = (
        "OFFICIAL_BOARD_ENDPOINT_REFINEMENT_COMPLETED_"
        "SEARCHABLE_ENDPOINTS_CONFIRMED"
    )

    next_action = (
        "PRIMARY_GOSI_BOARD / GAZETTE_ARCHIVE / "
        "URBAN_PLANNING_BOARD에 대해 실제 검색 form, "
        "query parameter, pagination 구조를 탐색하고 "
        "개발밀도관리구역 게시물 제목·본문·첨부파일을 직접 조회한다."
    )

else:

    resolution = (
        "OFFICIAL_BOARD_ENDPOINT_REFINEMENT_COMPLETED_"
        "NO_SEARCHABLE_ENDPOINT"
    )

    next_action = (
        "현재 endpoint 후보는 모두 generic 또는 ambiguous 상태다. "
        "공보 전용 시스템, SAEOL endpoint, 지자체 도시계획 포털 및 "
        "공식 고시 DB를 별도 seed로 추가 탐색한다."
    )


runtime_registration_blocked = True

site_false_interpretation_blocked = True


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-H "
        "Development Density Management Area "
        "Official Board Endpoint Relevance Refinement "
        "& Canonicalization"
    ),

    "target": {
        "name":
            TARGET_NAME,

        "standard_code":
            STANDARD_CODE,
    },

    "input": {
        "path":
            str(
                INPUT_PATH
            ),

        "g_stage_resolution":
            input_data.get(
                "resolution"
            ),
    },

    "method": {
        "network_requery":
            False,

        "canonicalization":
            True,

        "volatile_query_parameter_removal":
            True,

        "jsessionid_removal":
            True,

        "semantic_relevance_classification":
            True,

        "generic_board_exclusion":
            True,

        "gazette_false_positive_guard":
            True,

        "runtime_positive_allowed":
            False,
    },

    "summary": {
        "raw_candidate_count":
            len(
                raw_candidates
            ),

        "classified_candidate_count":
            raw_url_count,

        "canonical_endpoint_count":
            canonical_url_count,

        "duplicate_removed_count":
            duplicate_removed_count,

        "primary_gosi_board_count":
            len(
                primary_gosi_boards
            ),

        "gazette_archive_count":
            len(
                gazette_archives
            ),

        "urban_planning_board_count":
            len(
                urban_planning_boards
            ),

        "secondary_review_count":
            len(
                secondary_review
            ),

        "excluded_generic_board_count":
            len(
                excluded_generic_boards
            ),

        "next_stage_search_pool_count":
            len(
                next_stage_search_pool
            ),
    },

    "classification_counts":
        dict(
            classification_counts
        ),

    "primary_gosi_boards":
        primary_gosi_boards,

    "gazette_archives":
        gazette_archives,

    "urban_planning_boards":
        urban_planning_boards,

    "secondary_review":
        secondary_review,

    "excluded_generic_boards":
        excluded_generic_boards,

    "next_stage_search_pool":
        next_stage_search_pool,

    "all_canonical_endpoints":
        canonical_candidates,

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
    "REFINEMENT RESULT"
)

print(
    "============================================================"
)

print(
    "Raw candidate count:",
    len(
        raw_candidates
    ),
)

print(
    "Classified candidate count:",
    raw_url_count,
)

print(
    "Canonical endpoint count:",
    canonical_url_count,
)

print(
    "Duplicate / volatile variants removed:",
    duplicate_removed_count,
)

print()

print(
    "PRIMARY_GOSI_BOARD:",
    len(
        primary_gosi_boards
    ),
)

print(
    "GAZETTE_ARCHIVE:",
    len(
        gazette_archives
    ),
)

print(
    "URBAN_PLANNING_BOARD:",
    len(
        urban_planning_boards
    ),
)

print(
    "SECONDARY_REVIEW:",
    len(
        secondary_review
    ),
)

print(
    "EXCLUDED_GENERIC_BOARD:",
    len(
        excluded_generic_boards
    ),
)

print()

print(
    "Next-stage search pool:",
    len(
        next_stage_search_pool
    ),
)


# ============================================================
# PRINT HIGH-VALUE ENDPOINTS
# ============================================================

def print_candidate_group(
    title: str,
    candidates: List[
        Dict[
            str,
            Any
        ]
    ],
    *,
    limit: int = 50,
) -> None:

    if not candidates:

        return

    print()

    print(
        title
    )

    print(
        "------------------------------------------------------------"
    )

    for index, item in enumerate(
        candidates[
            :limit
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            item.get(
                "region"
            ),
        )

        print(
            "Class:",
            item.get(
                "classification"
            ),
        )

        print(
            "Score:",
            item.get(
                "classification_score"
            ),
        )

        print(
            "Label:",
            item.get(
                "label"
            ),
        )

        print(
            "Reasons:",
            item.get(
                "classification_reasons"
            ),
        )

        print(
            "Canonical URL:",
            item.get(
                "canonical_url"
            ),
        )

        print(
            "Raw variants:",
            item.get(
                "raw_variant_count"
            ),
        )

        print()


print_candidate_group(
    "PRIMARY GOSI BOARD ENDPOINTS",
    primary_gosi_boards,
)

print_candidate_group(
    "GAZETTE ARCHIVE ENDPOINTS",
    gazette_archives,
)

print_candidate_group(
    "URBAN PLANNING BOARD ENDPOINTS",
    urban_planning_boards,
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
# VALIDATION HELPERS
# ============================================================

canonical_keys = {
    (
        item.get(
            "region"
        ),
        item.get(
            "canonical_url"
        ),
    )
    for item in canonical_candidates
}


next_stage_keys = {
    (
        item.get(
            "region"
        ),
        item.get(
            "canonical_url"
        ),
    )
    for item in next_stage_search_pool
}


all_classifications_valid = all(
    item.get(
        "classification"
    )
    in CLASS_NAMES
    for item in canonical_candidates
)


all_canonical_urls_exist = all(
    bool(
        item.get(
            "canonical_url"
        )
    )
    for item in canonical_candidates
)


def canonical_query_keys(
    url: str,
) -> List[str]:

    try:
        parsed = urlparse(
            url
        )
    except Exception:
        return []

    return [
        normalize_query_key(
            key
        )
        for key, _ in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
    ]


def canonical_has_token_key(
    url: str,
) -> bool:

    for key in canonical_query_keys(
        url
    ):

        lowered = key.lower()

        if (
            lowered == "token"
            or re.search(
                r"(?:^|[_\-])token$",
                lowered,
            )
        ):
            return True

    return False


def canonical_has_csrf_key(
    url: str,
) -> bool:

    return any(
        "csrf"
        in key.lower()
        for key in canonical_query_keys(
            url
        )
    )


no_token_in_canonical_urls = all(
    not canonical_has_token_key(
        item.get(
            "canonical_url"
        )
        or ""
    )
    for item in canonical_candidates
)


no_csrf_in_canonical_urls = all(
    not canonical_has_csrf_key(
        item.get(
            "canonical_url"
        )
        or ""
    )
    for item in canonical_candidates
)


no_csrf_in_canonical_urls = all(
    "csrf"
    not in (
        item.get(
            "canonical_url"
        )
        or ""
    ).lower()
    for item in canonical_candidates
)


no_jsessionid_in_canonical_urls = all(
    ";jsessionid="
    not in (
        item.get(
            "canonical_url"
        )
        or ""
    ).lower()
    for item in canonical_candidates
)


next_stage_excludes_generic = all(
    item.get(
        "classification"
    )
    != CLASS_EXCLUDED
    for item in next_stage_search_pool
)


next_stage_excludes_secondary = all(
    item.get(
        "classification"
    )
    != CLASS_SECONDARY
    for item in next_stage_search_pool
)


primary_gosi_have_evidence = all(
    bool(
        item.get(
            "evidence",
        ).get(
            "primary_gosi_label_terms"
        )
        or item.get(
            "evidence",
        ).get(
            "primary_gosi_url_terms"
        )
    )
    for item in primary_gosi_boards
)


gazette_have_evidence = all(
    bool(
        item.get(
            "evidence",
        ).get(
            "gazette_terms"
        )
    )
    for item in gazette_archives
)


urban_have_evidence = all(
    bool(
        item.get(
            "evidence",
        ).get(
            "urban_label_terms"
        )
        or item.get(
            "evidence",
        ).get(
            "urban_url_terms"
        )
    )
    for item in urban_planning_boards
)


health_false_gazette_leakage = sum(
    1
    for item in gazette_archives
    if item.get(
        "evidence",
    ).get(
        "health_false_gazette_guard"
    )
    is True
)


generic_only_promoted = sum(
    1
    for item in next_stage_search_pool
    if item.get(
        "evidence",
    ).get(
        "generic_only"
    )
    is True
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

    "G-stage input parsed": (
        isinstance(
            input_data,
            dict,
        )
    ),

    "raw candidates loaded": (
        len(
            raw_candidates
        )
        > 0
    ),

    "canonicalization enabled": (
        output_data[
            "method"
        ][
            "canonicalization"
        ]
        is True
    ),

    "semantic relevance classification enabled": (
        output_data[
            "method"
        ][
            "semantic_relevance_classification"
        ]
        is True
    ),

    "generic board exclusion enabled": (
        output_data[
            "method"
        ][
            "generic_board_exclusion"
        ]
        is True
    ),

    "canonical endpoints unique": (
        len(
            canonical_keys
        )
        == len(
            canonical_candidates
        )
    ),

    "all classifications valid": (
        all_classifications_valid
    ),

    "all canonical URLs exist": (
        all_canonical_urls_exist
    ),

    "token removed from canonical URLs": (
        no_token_in_canonical_urls
    ),

    "csrf removed from canonical URLs": (
        no_csrf_in_canonical_urls
    ),

    "jsessionid removed from canonical URLs": (
        no_jsessionid_in_canonical_urls
    ),

    "next-stage endpoints unique": (
        len(
            next_stage_keys
        )
        == len(
            next_stage_search_pool
        )
    ),

    "next-stage excludes generic boards": (
        next_stage_excludes_generic
    ),

    "next-stage excludes secondary review": (
        next_stage_excludes_secondary
    ),

    "primary gosi boards have strong evidence": (
        primary_gosi_have_evidence
    ),

    "gazette archives have gazette evidence": (
        gazette_have_evidence
    ),

    "urban planning boards have urban evidence": (
        urban_have_evidence
    ),

    "health-label false gazette leakage zero": (
        health_false_gazette_leakage
        == 0
    ),

    "generic-only promotion zero": (
        generic_only_promoted
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


print()

print(
    "Health false-gazette leakage:",
    health_false_gazette_leakage,
)

print(
    "Generic-only endpoint promotion:",
    generic_only_promoted,
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
        "official board endpoint refinement regression failed"
    )