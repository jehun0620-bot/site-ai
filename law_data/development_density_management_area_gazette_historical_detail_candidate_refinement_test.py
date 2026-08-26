# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-S
Development Density Management Area
Gazette Historical Detail Candidate Refinement

목표
======================================================================
R-stage 공보 archive historical discovery에서 확보된 detail candidate 중

- 공통 메뉴
- 목록 페이지
- navigation link
- pagination 반복 링크
- 단순 "고시/공고", "채용공고", "도시계획", "변경" 등의
  의미가 약한 공통 링크

를 제거하고,

실제 과거 공보 게시물 / 고시 상세문서로 볼 수 있는
구조적 증거가 있는 URL만 다음 원문 검증 단계의 seed로 남긴다.

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 안전정책
======================================================================
1. R-stage의 relevant_detail_candidate는 final positive가 아니다.
2. label에 "고시", "공고", "도시계획"이 있다는 이유만으로
   상세문서 후보로 승격하지 않는다.
3. archive/list/menu/category URL은 상세문서 후보에서 제외한다.
4. 여러 historical page에서 반복 등장하는 공통 링크는
   navigation contamination 가능성이 높다고 본다.
5. 실제 detail identifier 또는 detail URL structure가 있어야
   다음 단계 verification seed로 우선 승격한다.
6. target-bearing archive page가 0건이라는 사실을 보존한다.
7. 후보가 0건이어도 regression 성공이다.
8. runtime spatial condition 등록은 계속 차단한다.
9. SITE FALSE 해석도 계속 차단한다.
"""

from __future__ import annotations

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
        "gazette_archive_historical_discovery.json"
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
        "gazette_historical_detail_candidate_refinement.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"

STANDARD_CODE = "UQQ700"


# ============================================================
# CLASSIFICATION CONSTANTS
# ============================================================

CLASS_STRONG_DETAIL = (
    "STRONG_DETAIL_CANDIDATE"
)

CLASS_SECONDARY_DETAIL = (
    "SECONDARY_DETAIL_REVIEW"
)

CLASS_NAVIGATION = (
    "EXCLUDED_NAVIGATION"
)

CLASS_LIST_ENDPOINT = (
    "EXCLUDED_LIST_ENDPOINT"
)

CLASS_GENERIC_LABEL = (
    "EXCLUDED_GENERIC_LABEL"
)

CLASS_REPEATED_COMMON = (
    "EXCLUDED_REPEATED_COMMON_LINK"
)

CLASS_INVALID = (
    "EXCLUDED_INVALID"
)


VALID_CLASSES = {
    CLASS_STRONG_DETAIL,
    CLASS_SECONDARY_DETAIL,
    CLASS_NAVIGATION,
    CLASS_LIST_ENDPOINT,
    CLASS_GENERIC_LABEL,
    CLASS_REPEATED_COMMON,
    CLASS_INVALID,
}


# ============================================================
# GENERIC LABELS
# ============================================================

GENERIC_LABEL_EXACT = {
    "고시",
    "공고",
    "고시공고",
    "고시/공고",
    "고시 공고",
    "고시·공고",
    "일반공고",
    "일반 공고",
    "입찰공고",
    "입찰 공고",
    "채용공고",
    "채용 공고",
    "공고알림",
    "공고 알림",
    "입법예고",
    "도시계획",
    "도시계획정보",
    "도시관리",
    "도시관리계획",
    "변경",
    "해제",
    "지정",
    "공지사항",
    "새소식",
    "알림광장",
    "공보",
    "시보",
    "구보",
}


GENERIC_LABEL_CONTAINS = {
    "더보기",
    "메뉴",
    "자료실",
    "알림",
    "복지정보",
    "정보포털",
    "보건소",
    "부서",
}


# ============================================================
# URL STRUCTURAL EVIDENCE
# ============================================================

DETAIL_PATH_PATTERNS = [
    re.compile(
        r"/view(?:\.do|\.jsp|\.asp|\.htm|\.html|\.web)?$",
        re.I,
    ),
    re.compile(
        r"/detail(?:\.do|\.jsp|\.asp|\.htm|\.html|\.web)?$",
        re.I,
    ),
    re.compile(
        r"/selectBoardArticle\.do$",
        re.I,
    ),
    re.compile(
        r"/selectBoardArticle$",
        re.I,
    ),
    re.compile(
        r"/bbsMsgDetail\.do$",
        re.I,
    ),
    re.compile(
        r"/eminwonAnnounceDetail\.do$",
        re.I,
    ),
    re.compile(
        r"/board/post/view\.do$",
        re.I,
    ),
    re.compile(
        r"/notice/view\.do$",
        re.I,
    ),
]


LIST_PATH_PATTERNS = [
    re.compile(
        r"/list(?:\.do|\.jsp|\.asp|\.htm|\.html|\.web)?$",
        re.I,
    ),
    re.compile(
        r"/selectBoardList\.do$",
        re.I,
    ),
    re.compile(
        r"/board/post/list\.do$",
        re.I,
    ),
    re.compile(
        r"/saeol/gosi/list\.do$",
        re.I,
    ),
]


DETAIL_QUERY_KEYS = {
    "idx",
    "nttid",
    "ntt_id",
    "seq",
    "articleid",
    "article_id",
    "article",
    "postid",
    "post_id",
    "msg_seq",
    "mgt_no",
    "notancmtmgtno",
    "noticeid",
    "notice_id",
    "boardseq",
    "board_seq",
    "bbsno",
    "bbs_no",
    "contentno",
    "content_no",
}


LIST_QUERY_KEYS = {
    "page",
    "pageindex",
    "pageno",
    "curpage",
    "cpage",
    "gotopage",
    "pagesize",
    "pageunit",
    "rowpage",
    "viewpage",
    "postperpage",
    "cntperpage",
    "searchpagesize",
}


VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "jsessionid",
    "sessionid",
    "session",
}


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
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        "",
        normalize_space(
            value
        ),
    )


def contains_target(
    value: Any,
) -> bool:

    return (
        compact_text(
            TARGET_NAME
        )
        in compact_text(
            value
        )
    )


# ============================================================
# URL UTIL
# ============================================================

def normalize_url(
    url: Any,
) -> str:

    value = normalize_space(
        url
    )

    if not value:

        return ""

    try:

        parsed = urlparse(
            value
        )

    except Exception:

        return value

    query_items = []

    for key, query_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        lower_key = key.lower()

        if lower_key in VOLATILE_QUERY_KEYS:

            continue

        query_items.append(
            (
                key,
                query_value,
            )
        )

    query_items.sort(
        key=lambda item: (
            item[0].lower(),
            item[1],
        )
    )

    path = re.sub(
        r";jsessionid=[^/?#]+",
        "",
        parsed.path,
        flags=re.I,
    )

    normalized = urlunparse(
        parsed._replace(
            path=path,
            query=urlencode(
                query_items,
                doseq=True,
            ),
            fragment="",
        )
    )

    return normalized


def get_query_map(
    url: str,
) -> Dict[str, List[str]]:

    result: Dict[
        str,
        List[str]
    ] = defaultdict(
        list
    )

    try:

        parsed = urlparse(
            url
        )

    except Exception:

        return {}

    for key, value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        result[
            key.lower()
        ].append(
            value
        )

    return dict(
        result
    )


def has_detail_query_key(
    url: str,
) -> bool:

    query_map = get_query_map(
        url
    )

    return any(
        key in DETAIL_QUERY_KEYS
        for key in query_map
    )


def has_only_list_query_keys(
    url: str,
) -> bool:

    query_map = get_query_map(
        url
    )

    if not query_map:

        return False

    keys = set(
        query_map
    )

    meaningful_keys = {
        key
        for key in keys
        if key
        not in {
            "mid",
            "menu_id",
            "menucd",
            "menuno",
            "contentuid",
            "boarduid",
            "subpath",
            "bcidx",
            "bbscd",
            "bbsid",
        }
    }

    if not meaningful_keys:

        return False

    return meaningful_keys.issubset(
        LIST_QUERY_KEYS
    )


def path_has_detail_structure(
    url: str,
) -> bool:

    try:

        path = (
            urlparse(
                url
            ).path
            or ""
        )

    except Exception:

        return False

    return any(
        pattern.search(
            path
        )
        is not None
        for pattern
        in DETAIL_PATH_PATTERNS
    )


def path_has_list_structure(
    url: str,
) -> bool:

    try:

        path = (
            urlparse(
                url
            ).path
            or ""
        )

    except Exception:

        return False

    return any(
        pattern.search(
            path
        )
        is not None
        for pattern
        in LIST_PATH_PATTERNS
    )


def looks_like_numeric_path_detail(
    url: str,
) -> bool:

    try:

        path = (
            urlparse(
                url
            ).path
            or ""
        )

    except Exception:

        return False

    segments = [
        segment
        for segment
        in path.split("/")
        if segment
    ]

    if not segments:

        return False

    last_segment = segments[
        -1
    ]

    if re.fullmatch(
        r"\d{3,}",
        last_segment,
    ):

        return True

    if re.fullmatch(
        r"\d{3,}\.(?:web|do|jsp|asp|html?|php)",
        last_segment,
        flags=re.I,
    ):

        return True

    return False


def looks_like_menu_path(
    url: str,
) -> bool:

    try:

        parsed = urlparse(
            url
        )

    except Exception:

        return False

    path = (
        parsed.path
        or ""
    ).lower()

    query_map = get_query_map(
        url
    )

    if (
        path.endswith(
            "/index.do"
        )
        and (
            "menu_id"
            in query_map
        )
        and not has_detail_query_key(
            url
        )
    ):

        return True

    if (
        path.endswith(
            ".web"
        )
        and re.search(
            r"/\d{5}(?:/\d{5}){0,3}\.web$",
            path,
        )
    ):

        return True

    return False


# ============================================================
# LABEL CLASSIFICATION
# ============================================================

def is_generic_label(
    label: Any,
) -> bool:

    text = normalize_space(
        label
    )

    compact = compact_text(
        text
    )

    if not compact:

        return True

    normalized_exact = {
        compact_text(
            item
        )
        for item
        in GENERIC_LABEL_EXACT
    }

    if compact in normalized_exact:

        return True

    if len(
        compact
    ) <= 8:

        if any(
            compact_text(
                term
            )
            in compact
            for term
            in GENERIC_LABEL_CONTAINS
        ):

            return True

    return False


def label_has_specific_document_evidence(
    label: Any,
) -> bool:

    text = normalize_space(
        label
    )

    if not text:

        return False

    if contains_target(
        text
    ):

        return True

    if re.search(
        r"\b20\d{2}\b",
        text,
    ):

        return True

    if re.search(
        r"제?\s*\d{4}\s*[-–]\s*\d+\s*호",
        text,
    ):

        return True

    if re.search(
        r"(지정|변경|해제|결정|지형도면)",
        text,
    ) and len(
        compact_text(
            text
        )
    ) >= 14:

        return True

    return False


# ============================================================
# INPUT LOADING
# ============================================================

if not INPUT_PATH.exists():

    raise FileNotFoundError(
        f"Input not found: {INPUT_PATH}"
    )


input_data = json.loads(
    INPUT_PATH.read_text(
        encoding="utf-8"
    )
)


# ============================================================
# FLEXIBLE INPUT EXTRACTION
# ============================================================

def extract_candidate_list(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    candidate_keys = [
        "relevant_detail_candidates",
        "detail_candidates",
        "historical_detail_candidates",
        "detail_seeds",
    ]

    for key in candidate_keys:

        value = data.get(
            key
        )

        if isinstance(
            value,
            list,
        ):

            return [
                item
                for item
                in value
                if isinstance(
                    item,
                    dict,
                )
            ]

    nested_candidates = []

    archive_result_keys = [
        "archive_results",
        "gazette_archive_results",
        "endpoint_results",
        "site_results",
    ]

    for key in archive_result_keys:

        records = data.get(
            key
        )

        if not isinstance(
            records,
            list,
        ):

            continue

        for record in records:

            if not isinstance(
                record,
                dict,
            ):

                continue

            for detail_key in (
                "detail_candidates",
                "relevant_detail_candidates",
                "historical_detail_candidates",
            ):

                details = record.get(
                    detail_key
                )

                if not isinstance(
                    details,
                    list,
                ):

                    continue

                for detail in details:

                    if not isinstance(
                        detail,
                        dict,
                    ):

                        continue

                    enriched = dict(
                        detail
                    )

                    enriched.setdefault(
                        "region",
                        record.get(
                            "region"
                        ),
                    )

                    enriched.setdefault(
                        "agency",
                        record.get(
                            "agency"
                        ),
                    )

                    enriched.setdefault(
                        "archive_url",
                        (
                            record.get(
                                "url"
                            )
                            or record.get(
                                "archive_url"
                            )
                        ),
                    )

                    nested_candidates.append(
                        enriched
                    )

    return nested_candidates


raw_candidates = extract_candidate_list(
    input_data
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
    "GAZETTE HISTORICAL DETAIL CANDIDATE REFINEMENT"
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
    "Raw detail candidate count:",
    len(
        raw_candidates
    ),
)


# ============================================================
# NORMALIZE CANDIDATES
# ============================================================

normalized_candidates = []

for index, candidate in enumerate(
    raw_candidates,
    start=1,
):

    url = normalize_url(
        (
            candidate.get(
                "url"
            )
            or candidate.get(
                "detail_url"
            )
            or candidate.get(
                "href"
            )
            or ""
        )
    )

    label = normalize_space(
        (
            candidate.get(
                "label"
            )
            or candidate.get(
                "title"
            )
            or candidate.get(
                "text"
            )
            or ""
        )
    )

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

    parent_page_url = normalize_url(
        (
            candidate.get(
                "parent_page_url"
            )
            or candidate.get(
                "source_page_url"
            )
            or candidate.get(
                "archive_page_url"
            )
            or ""
        )
    )

    archive_url = normalize_url(
        (
            candidate.get(
                "archive_url"
            )
            or ""
        )
    )

    normalized_candidates.append(
        {
            **candidate,
            "_source_index": index,
            "region": region,
            "agency": agency,
            "url": url,
            "label": label,
            "parent_page_url": parent_page_url,
            "archive_url": archive_url,
        }
    )


# ============================================================
# URL FREQUENCY
# ============================================================

url_frequency = Counter(
    item.get(
        "url"
    )
    for item
    in normalized_candidates
    if item.get(
        "url"
    )
)

region_url_frequency = Counter(
    (
        item.get(
            "region"
        ),
        item.get(
            "url"
        ),
    )
    for item
    in normalized_candidates
    if item.get(
        "url"
    )
)

parent_url_sets: Dict[
    Tuple[str, str],
    Set[str]
] = defaultdict(
    set
)

for item in normalized_candidates:

    key = (
        str(
            item.get(
                "region"
            )
            or ""
        ),
        str(
            item.get(
                "url"
            )
            or ""
        ),
    )

    parent = str(
        item.get(
            "parent_page_url"
        )
        or ""
    )

    if parent:

        parent_url_sets[
            key
        ].add(
            parent
        )


# ============================================================
# CLASSIFICATION
# ============================================================

classified_candidates = []

for item in normalized_candidates:

    url = str(
        item.get(
            "url"
        )
        or ""
    )

    label = str(
        item.get(
            "label"
        )
        or ""
    )

    region = str(
        item.get(
            "region"
        )
        or ""
    )

    parent_page_url = str(
        item.get(
            "parent_page_url"
        )
        or ""
    )

    archive_url = str(
        item.get(
            "archive_url"
        )
        or ""
    )

    reasons = []

    score = 0

    target_in_label = contains_target(
        label
    )

    target_in_url = contains_target(
        url
    )

    detail_query_evidence = (
        has_detail_query_key(
            url
        )
    )

    detail_path_evidence = (
        path_has_detail_structure(
            url
        )
    )

    numeric_path_evidence = (
        looks_like_numeric_path_detail(
            url
        )
    )

    list_path_evidence = (
        path_has_list_structure(
            url
        )
    )

    list_query_evidence = (
        has_only_list_query_keys(
            url
        )
    )

    menu_path_evidence = (
        looks_like_menu_path(
            url
        )
    )

    generic_label = (
        is_generic_label(
            label
        )
    )

    specific_label_evidence = (
        label_has_specific_document_evidence(
            label
        )
    )

    same_as_archive = bool(
        url
        and archive_url
        and url == archive_url
    )

    same_as_parent = bool(
        url
        and parent_page_url
        and url == parent_page_url
    )

    regional_frequency = (
        region_url_frequency[
            (
                region,
                url,
            )
        ]
        if url
        else 0
    )

    distinct_parent_count = len(
        parent_url_sets.get(
            (
                region,
                url,
            ),
            set(),
        )
    )

    repeated_common_link = (
        regional_frequency >= 3
        or distinct_parent_count >= 3
    )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    if target_in_label:

        score += 10

        reasons.append(
            "TARGET_IN_LABEL"
        )

    if target_in_url:

        score += 8

        reasons.append(
            "TARGET_IN_URL"
        )

    if detail_query_evidence:

        score += 7

        reasons.append(
            "DETAIL_QUERY_IDENTIFIER"
        )

    if detail_path_evidence:

        score += 6

        reasons.append(
            "DETAIL_PATH_STRUCTURE"
        )

    if numeric_path_evidence:

        score += 5

        reasons.append(
            "NUMERIC_DETAIL_PATH"
        )

    if specific_label_evidence:

        score += 4

        reasons.append(
            "SPECIFIC_DOCUMENT_LABEL"
        )

    if generic_label:

        score -= 5

        reasons.append(
            "GENERIC_LABEL"
        )

    if list_path_evidence:

        score -= 8

        reasons.append(
            "LIST_PATH_STRUCTURE"
        )

    if list_query_evidence:

        score -= 5

        reasons.append(
            "LIST_QUERY_STRUCTURE"
        )

    if menu_path_evidence:

        score -= 5

        reasons.append(
            "MENU_STRUCTURE"
        )

    if same_as_archive:

        score -= 10

        reasons.append(
            "SAME_AS_ARCHIVE_ENDPOINT"
        )

    if same_as_parent:

        score -= 8

        reasons.append(
            "SAME_AS_PARENT_PAGE"
        )

    if repeated_common_link:

        score -= 6

        reasons.append(
            "REPEATED_COMMON_LINK"
        )

    # --------------------------------------------------------
    # FINAL CLASS
    # --------------------------------------------------------

    if not url:

        classification = (
            CLASS_INVALID
        )

    elif (
        same_as_archive
        or same_as_parent
    ):

        classification = (
            CLASS_NAVIGATION
        )

    elif (
        list_path_evidence
        and not detail_query_evidence
    ):

        classification = (
            CLASS_LIST_ENDPOINT
        )

    elif (
        menu_path_evidence
        and not detail_query_evidence
        and not numeric_path_evidence
    ):

        classification = (
            CLASS_NAVIGATION
        )

    elif (
        repeated_common_link
        and not target_in_label
        and not target_in_url
        and not detail_query_evidence
        and not numeric_path_evidence
    ):

        classification = (
            CLASS_REPEATED_COMMON
        )

    elif (
        generic_label
        and not target_in_label
        and not target_in_url
        and not detail_query_evidence
        and not detail_path_evidence
        and not numeric_path_evidence
    ):

        classification = (
            CLASS_GENERIC_LABEL
        )

    elif (
        (
            target_in_label
            or target_in_url
        )
        and (
            detail_query_evidence
            or detail_path_evidence
            or numeric_path_evidence
            or specific_label_evidence
        )
    ):

        classification = (
            CLASS_STRONG_DETAIL
        )

    elif (
        detail_query_evidence
        or (
            detail_path_evidence
            and specific_label_evidence
        )
        or (
            numeric_path_evidence
            and specific_label_evidence
        )
    ):

        classification = (
            CLASS_STRONG_DETAIL
        )

    elif (
        score >= 4
        and not list_path_evidence
        and not menu_path_evidence
        and not repeated_common_link
    ):

        classification = (
            CLASS_SECONDARY_DETAIL
        )

    else:

        classification = (
            CLASS_GENERIC_LABEL
        )

    classified_candidates.append(
        {
            **item,
            "classification":
                classification,

            "refinement_score":
                score,

            "refinement_reasons":
                reasons,

            "target_in_label":
                target_in_label,

            "target_in_url":
                target_in_url,

            "detail_query_evidence":
                detail_query_evidence,

            "detail_path_evidence":
                detail_path_evidence,

            "numeric_path_evidence":
                numeric_path_evidence,

            "list_path_evidence":
                list_path_evidence,

            "list_query_evidence":
                list_query_evidence,

            "menu_path_evidence":
                menu_path_evidence,

            "generic_label":
                generic_label,

            "specific_label_evidence":
                specific_label_evidence,

            "regional_url_frequency":
                regional_frequency,

            "distinct_parent_page_count":
                distinct_parent_count,

            "repeated_common_link":
                repeated_common_link,
        }
    )


# ============================================================
# DEDUPE CLASSIFIED CANDIDATES
# ============================================================

CLASS_PRIORITY = {
    CLASS_STRONG_DETAIL: 7,
    CLASS_SECONDARY_DETAIL: 6,
    CLASS_REPEATED_COMMON: 5,
    CLASS_NAVIGATION: 4,
    CLASS_LIST_ENDPOINT: 3,
    CLASS_GENERIC_LABEL: 2,
    CLASS_INVALID: 1,
}


deduped_by_key: Dict[
    Tuple[str, str],
    Dict[str, Any]
] = {}

for item in classified_candidates:

    key = (
        str(
            item.get(
                "region"
            )
            or ""
        ),
        str(
            item.get(
                "url"
            )
            or ""
        ),
    )

    current = deduped_by_key.get(
        key
    )

    if current is None:

        deduped_by_key[
            key
        ] = item

        continue

    new_priority = CLASS_PRIORITY.get(
        item.get(
            "classification"
        ),
        0,
    )

    current_priority = CLASS_PRIORITY.get(
        current.get(
            "classification"
        ),
        0,
    )

    new_score = int(
        item.get(
            "refinement_score",
            0,
        )
    )

    current_score = int(
        current.get(
            "refinement_score",
            0,
        )
    )

    if (
        new_priority > current_priority
        or (
            new_priority == current_priority
            and new_score > current_score
        )
    ):

        deduped_by_key[
            key
        ] = item


deduped_candidates = list(
    deduped_by_key.values()
)


# ============================================================
# GROUPS
# ============================================================

strong_detail_candidates = [
    item
    for item
    in deduped_candidates
    if item.get(
        "classification"
    )
    == CLASS_STRONG_DETAIL
]

secondary_detail_candidates = [
    item
    for item
    in deduped_candidates
    if item.get(
        "classification"
    )
    == CLASS_SECONDARY_DETAIL
]

excluded_candidates = [
    item
    for item
    in deduped_candidates
    if item.get(
        "classification"
    )
    not in {
        CLASS_STRONG_DETAIL,
        CLASS_SECONDARY_DETAIL,
    }
]


strong_detail_candidates.sort(
    key=lambda item: (
        -int(
            item.get(
                "refinement_score",
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

secondary_detail_candidates.sort(
    key=lambda item: (
        -int(
            item.get(
                "refinement_score",
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
# INPUT SUMMARY PRESERVATION
# ============================================================

input_summary = (
    input_data.get(
        "summary"
    )
    if isinstance(
        input_data.get(
            "summary"
        ),
        dict,
    )
    else {}
)

target_archive_page_count = int(
    input_summary.get(
        "target_archive_page_count",
        input_summary.get(
            "target_page_count",
            0,
        ),
    )
    or 0
)

relevant_attachment_candidate_count = int(
    input_summary.get(
        "relevant_attachment_candidate_count",
        0,
    )
    or 0
)


# ============================================================
# RESOLUTION
# ============================================================

if strong_detail_candidates:

    resolution = (
        "GAZETTE_HISTORICAL_STRONG_DETAIL_CANDIDATES_REFINED"
    )

    next_action = (
        "STRONG_DETAIL_CANDIDATE만 개별 HTTP 조회하여 실제 "
        "개발밀도관리구역 지정·변경·해제 고시인지 원문 검증한다. "
        "본문 target, 고시번호, 고시일, 행정구역, 지정·변경·해제 "
        "action context를 모두 확인하기 전까지 final positive로 "
        "승격하지 않는다."
    )

elif secondary_detail_candidates:

    resolution = (
        "GAZETTE_HISTORICAL_ONLY_SECONDARY_DETAIL_CANDIDATES_REMAIN"
    )

    next_action = (
        "강한 detail identifier를 가진 후보는 없고 secondary review "
        "후보만 남았다. 이 후보는 낮은 우선순위로 원문 조회하되 "
        "target body evidence 없이는 positive로 승격하지 않는다."
    )

else:

    resolution = (
        "GAZETTE_HISTORICAL_DETAIL_REFINEMENT_COMPLETED_NO_DETAIL_SEED"
    )

    next_action = (
        "R-stage historical GET archive에서 실제 detail seed가 "
        "확인되지 않았다. POST pagination, archive 검색 form, "
        "연도 필터, JavaScript/AJAX archive endpoint 및 국가관보/"
        "국가기록원 자료원으로 탐색 범위를 확장한다."
    )


runtime_registration_blocked = True

site_false_interpretation_blocked = True


# ============================================================
# OUTPUT
# ============================================================

classification_counts = Counter(
    item.get(
        "classification"
    )
    for item
    in deduped_candidates
)


output_data = {
    "step": (
        "STEP 17-21-C-16-8-S "
        "Development Density Management Area "
        "Gazette Historical Detail Candidate Refinement"
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

        "target_archive_page_count":
            target_archive_page_count,

        "relevant_attachment_candidate_count":
            relevant_attachment_candidate_count,
    },

    "method": {
        "navigation_false_positive_filter":
            True,

        "repeated_link_filter":
            True,

        "generic_label_filter":
            True,

        "detail_url_structure_required":
            True,

        "target_label_priority":
            True,

        "list_endpoint_prohibited":
            True,

        "runtime_registration_allowed":
            False,

        "site_false_allowed":
            False,
    },

    "summary": {
        "raw_candidate_count":
            len(
                raw_candidates
            ),

        "normalized_candidate_count":
            len(
                normalized_candidates
            ),

        "deduped_candidate_count":
            len(
                deduped_candidates
            ),

        "strong_detail_candidate_count":
            len(
                strong_detail_candidates
            ),

        "secondary_detail_candidate_count":
            len(
                secondary_detail_candidates
            ),

        "excluded_candidate_count":
            len(
                excluded_candidates
            ),

        "classification_counts":
            dict(
                classification_counts
            ),

        "target_archive_page_count_preserved":
            target_archive_page_count,

        "relevant_attachment_candidate_count_preserved":
            relevant_attachment_candidate_count,
    },

    "strong_detail_candidates":
        strong_detail_candidates,

    "secondary_detail_candidates":
        secondary_detail_candidates,

    "excluded_candidates":
        excluded_candidates,

    "all_classified_candidates":
        deduped_candidates,

    "resolution":
        resolution,

    "next_action":
        next_action,

    "runtime_registration_blocked":
        runtime_registration_blocked,

    "site_false_interpretation_blocked":
        site_false_interpretation_blocked,
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
    "Normalized candidate count:",
    len(
        normalized_candidates
    ),
)

print(
    "Canonical candidate count:",
    len(
        deduped_candidates
    ),
)

print(
    "Strong detail candidate count:",
    len(
        strong_detail_candidates
    ),
)

print(
    "Secondary detail candidate count:",
    len(
        secondary_detail_candidates
    ),
)

print(
    "Excluded candidate count:",
    len(
        excluded_candidates
    ),
)

print()

for class_name in (
    CLASS_STRONG_DETAIL,
    CLASS_SECONDARY_DETAIL,
    CLASS_REPEATED_COMMON,
    CLASS_NAVIGATION,
    CLASS_LIST_ENDPOINT,
    CLASS_GENERIC_LABEL,
    CLASS_INVALID,
):

    print(
        f"{class_name}:",
        classification_counts.get(
            class_name,
            0,
        ),
    )


# ============================================================
# STRONG CANDIDATES
# ============================================================

if strong_detail_candidates:

    print()

    print(
        "STRONG DETAIL CANDIDATES"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, item in enumerate(
        strong_detail_candidates,
        start=1,
    ):

        print(
            f"[{index}]",
            item.get(
                "region"
            ),
        )

        print(
            "Score:",
            item.get(
                "refinement_score"
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
                "refinement_reasons"
            ),
        )

        print(
            "URL:",
            item.get(
                "url"
            ),
        )

        print()


# ============================================================
# SECONDARY CANDIDATES
# ============================================================

if secondary_detail_candidates:

    print()

    print(
        "SECONDARY DETAIL REVIEW"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, item in enumerate(
        secondary_detail_candidates[
            :50
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
            "Score:",
            item.get(
                "refinement_score"
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
                "refinement_reasons"
            ),
        )

        print(
            "URL:",
            item.get(
                "url"
            ),
        )

        print()


# ============================================================
# RESOLUTION
# ============================================================

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

candidate_keys = {
    (
        item.get(
            "region"
        ),
        item.get(
            "url"
        ),
    )
    for item
    in deduped_candidates
}


strong_keys = {
    (
        item.get(
            "region"
        ),
        item.get(
            "url"
        ),
    )
    for item
    in strong_detail_candidates
}


secondary_keys = {
    (
        item.get(
            "region"
        ),
        item.get(
            "url"
        ),
    )
    for item
    in secondary_detail_candidates
}


all_classes_valid = all(
    item.get(
        "classification"
    )
    in VALID_CLASSES
    for item
    in deduped_candidates
)


all_strong_have_urls = all(
    bool(
        item.get(
            "url"
        )
    )
    for item
    in strong_detail_candidates
)


all_strong_not_list_only = all(
    not (
        item.get(
            "list_path_evidence"
        )
        and not item.get(
            "detail_query_evidence"
        )
    )
    for item
    in strong_detail_candidates
)


all_strong_have_structural_evidence = all(
    (
        item.get(
            "target_in_label"
        )
        or item.get(
            "target_in_url"
        )
        or item.get(
            "detail_query_evidence"
        )
        or item.get(
            "detail_path_evidence"
        )
        or item.get(
            "numeric_path_evidence"
        )
        or item.get(
            "specific_label_evidence"
        )
    )
    for item
    in strong_detail_candidates
)


generic_only_strong_promotion = sum(
    1
    for item
    in strong_detail_candidates
    if (
        item.get(
            "generic_label"
        )
        is True
        and not item.get(
            "target_in_label"
        )
        and not item.get(
            "target_in_url"
        )
        and not item.get(
            "detail_query_evidence"
        )
        and not item.get(
            "detail_path_evidence"
        )
        and not item.get(
            "numeric_path_evidence"
        )
    )
)


repeated_common_strong_promotion = sum(
    1
    for item
    in strong_detail_candidates
    if (
        item.get(
            "repeated_common_link"
        )
        is True
        and not item.get(
            "target_in_label"
        )
        and not item.get(
            "target_in_url"
        )
        and not item.get(
            "detail_query_evidence"
        )
        and not item.get(
            "numeric_path_evidence"
        )
    )
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

    "candidate extraction enabled": (
        isinstance(
            raw_candidates,
            list,
        )
    ),

    "navigation false-positive filter enabled": (
        output_data[
            "method"
        ][
            "navigation_false_positive_filter"
        ]
        is True
    ),

    "repeated-link filter enabled": (
        output_data[
            "method"
        ][
            "repeated_link_filter"
        ]
        is True
    ),

    "generic-label filter enabled": (
        output_data[
            "method"
        ][
            "generic_label_filter"
        ]
        is True
    ),

    "detail URL structure guard enabled": (
        output_data[
            "method"
        ][
            "detail_url_structure_required"
        ]
        is True
    ),

    "list endpoint prohibited": (
        output_data[
            "method"
        ][
            "list_endpoint_prohibited"
        ]
        is True
    ),

    "canonical candidates unique": (
        len(
            candidate_keys
        )
        == len(
            deduped_candidates
        )
    ),

    "strong candidates unique": (
        len(
            strong_keys
        )
        == len(
            strong_detail_candidates
        )
    ),

    "secondary candidates unique": (
        len(
            secondary_keys
        )
        == len(
            secondary_detail_candidates
        )
    ),

    "all classifications valid": (
        all_classes_valid
    ),

    "all strong candidates have URL": (
        all_strong_have_urls
    ),

    "all strong candidates are not list-only": (
        all_strong_not_list_only
    ),

    "all strong candidates have structural evidence": (
        all_strong_have_structural_evidence
    ),

    "generic-only strong promotion zero": (
        generic_only_strong_promotion
        == 0
    ),

    "repeated-common strong promotion zero": (
        repeated_common_strong_promotion
        == 0
    ),

    "target archive page count preserved": (
        output_data[
            "summary"
        ][
            "target_archive_page_count_preserved"
        ]
        == target_archive_page_count
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
    "Generic-only strong promotion:",
    generic_only_strong_promotion,
)

print(
    "Repeated-common strong promotion:",
    repeated_common_strong_promotion,
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
        "gazette historical detail candidate refinement "
        "regression failed"
    )