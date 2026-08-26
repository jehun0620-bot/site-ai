# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-P
Development Density Management Area
Historical Official Source Expansion

목표
======================================================================
O-stage

    HISTORICAL_OFFICIAL_ARCHIVE_DISCOVERY_COMPLETED_NO_SEED

결과를 바탕으로 기존 현대 지자체 고시/공보 endpoint 반복 탐색을 중단하고,
개발밀도관리구역의 과거 공식 고시 원문을 복원할 수 있는
historical / legacy official source 탐색 전략을 구성한다.

입력 1:
    law_data/output/
    development_density_management_area_
    historical_official_archive_discovery.json

입력 2:
    law_data/output/
    development_density_management_area_
    historical_official_notice_recovery_expansion.json

입력 3:
    law_data/output/
    development_density_management_area_
    gazette_recovered_attachment_source_verification.json

입력 4:
    law_data/output/
    development_density_management_area_
    target_document_candidate_verification.json

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700


핵심 목표
======================================================================
1. O-stage에서 이미 탐색한 현대 지자체 endpoint brute-force를 반복하지 않는다.

2. 다음 historical source family를 별도 recovery target으로 만든다.

    NATIONAL_ARCHIVES
        국가기록원 / 공공기록물 계열

    OFFICIAL_GAZETTE
        관보 / 전자관보 / 공보 계열

    LEGACY_LOCAL_GAZETTE
        구형 시보/군보/구보 archive

    LEGACY_LOCAL_NOTICE
        구형 고시·공고 archive

    URBAN_PLANNING_ARCHIVE
        도시관리계획 / 지형도면 / 도시계획 archive

    LAND_USE_ARCHIVE
        토지이용계획 / 토지이음 연계 historical source

    NOTICE_NUMBER_REVERSE_LOOKUP
        고시번호 기반 역탐색

3. exact phrase 기반 search plan을 생성한다.

4. 초기 제도 시기인 2000~2009를 가장 높은 우선순위로 둔다.

5. 2010~2019는 중간 우선순위,
   2020~2025는 낮은 historical fallback으로 둔다.

6. 2026 현재 자료는 historical recovery 주대상이 아니다.

7. 기존 negative URL / false-positive URL / O-stage candidate URL을
   exclusion memory로 유지한다.

8. 검색 결과 page 자체는 final positive가 아니다.

9. 실제 detail identity / attachment / issue / notice number만
   다음 단계에서 검증 대상으로 사용할 수 있다.

10. runtime registration은 계속 차단한다.

11. SITE TRUE / FALSE 자동 판정도 계속 차단한다.

12. 이 단계는 실제 web scraping 실행 단계가 아니라
    "historical source expansion plan + normalized seed matrix"
    생성 단계이다.


출력 핵심 구조
======================================================================
source_families
    historical source family 정의

historical_source_targets
    source family별 recovery target

query_matrix
    exact target/action/notice/urban/archive query matrix

notice_reverse_lookup_matrix
    고시번호 역탐색 query template

exclusion_memory
    기존 negative / false-positive / O-stage candidate URL

next_stage_source_discovery_pool
    Q-stage에서 실제 source discovery를 수행할 입력

resolution
    HISTORICAL_OFFICIAL_SOURCE_EXPANSION_READY
"""

from __future__ import annotations

import html
import json
import re

from collections import Counter
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

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


O_STAGE_INPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "historical_official_archive_discovery.json"
    )
)

N_STAGE_INPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "historical_official_notice_recovery_expansion.json"
    )
)

M_STAGE_INPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gazette_recovered_attachment_source_verification.json"
    )
)

Y_STAGE_INPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "target_document_candidate_verification.json"
    )
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "historical_official_source_expansion.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# EXPECTED PRIOR RESOLUTIONS
# ============================================================

EXPECTED_O_STAGE_RESOLUTION = (
    "HISTORICAL_OFFICIAL_ARCHIVE_DISCOVERY_COMPLETED_NO_SEED"
)

EXPECTED_M_STAGE_RESOLUTION = (
    "GAZETTE_RECOVERED_ATTACHMENT_VERIFICATION_COMPLETED_NO_TARGET"
)


# ============================================================
# SOURCE FAMILY
# ============================================================

SOURCE_FAMILY_NATIONAL_ARCHIVES = (
    "NATIONAL_ARCHIVES"
)

SOURCE_FAMILY_OFFICIAL_GAZETTE = (
    "OFFICIAL_GAZETTE"
)

SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE = (
    "LEGACY_LOCAL_GAZETTE"
)

SOURCE_FAMILY_LEGACY_LOCAL_NOTICE = (
    "LEGACY_LOCAL_NOTICE"
)

SOURCE_FAMILY_URBAN_PLANNING_ARCHIVE = (
    "URBAN_PLANNING_ARCHIVE"
)

SOURCE_FAMILY_LAND_USE_ARCHIVE = (
    "LAND_USE_ARCHIVE"
)

SOURCE_FAMILY_NOTICE_REVERSE = (
    "NOTICE_NUMBER_REVERSE_LOOKUP"
)


VALID_SOURCE_FAMILIES = {
    SOURCE_FAMILY_NATIONAL_ARCHIVES,
    SOURCE_FAMILY_OFFICIAL_GAZETTE,
    SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE,
    SOURCE_FAMILY_LEGACY_LOCAL_NOTICE,
    SOURCE_FAMILY_URBAN_PLANNING_ARCHIVE,
    SOURCE_FAMILY_LAND_USE_ARCHIVE,
    SOURCE_FAMILY_NOTICE_REVERSE,
}


# ============================================================
# SOURCE TARGET CLASS
# ============================================================

TARGET_CLASS_PRIMARY = (
    "PRIMARY_HISTORICAL_SOURCE"
)

TARGET_CLASS_SECONDARY = (
    "SECONDARY_HISTORICAL_SOURCE"
)

TARGET_CLASS_REVERSE_LOOKUP = (
    "NOTICE_NUMBER_REVERSE_LOOKUP_SOURCE"
)


VALID_TARGET_CLASSES = {
    TARGET_CLASS_PRIMARY,
    TARGET_CLASS_SECONDARY,
    TARGET_CLASS_REVERSE_LOOKUP,
}


# ============================================================
# QUERY CLASS
# ============================================================

QUERY_CLASS_EXACT = (
    "EXACT_TARGET_QUERY"
)

QUERY_CLASS_ACTION = (
    "TARGET_ACTION_QUERY"
)

QUERY_CLASS_NOTICE = (
    "TARGET_NOTICE_QUERY"
)

QUERY_CLASS_URBAN = (
    "TARGET_URBAN_PLANNING_QUERY"
)

QUERY_CLASS_ARCHIVE = (
    "TARGET_ARCHIVE_QUERY"
)

QUERY_CLASS_REGION = (
    "TARGET_REGION_QUERY"
)

QUERY_CLASS_NOTICE_REVERSE = (
    "NOTICE_NUMBER_REVERSE_QUERY"
)


VALID_QUERY_CLASSES = {
    QUERY_CLASS_EXACT,
    QUERY_CLASS_ACTION,
    QUERY_CLASS_NOTICE,
    QUERY_CLASS_URBAN,
    QUERY_CLASS_ARCHIVE,
    QUERY_CLASS_REGION,
    QUERY_CLASS_NOTICE_REVERSE,
}


# ============================================================
# PERIOD STRATEGY
# ============================================================

PERIODS = [
    {
        "period_class": "EARLY制度_PERIOD",
        "start_year": 2000,
        "end_year": 2009,
        "priority": 100,
        "historical_priority": "HIGHEST",
    },
    {
        "period_class": "MIDDLE_PERIOD",
        "start_year": 2010,
        "end_year": 2019,
        "priority": 80,
        "historical_priority": "HIGH",
    },
    {
        "period_class": "RECENT_HISTORICAL_PERIOD",
        "start_year": 2020,
        "end_year": 2025,
        "priority": 50,
        "historical_priority": "MEDIUM",
    },
]


# ============================================================
# QUERY TERMS
# ============================================================

BASE_EXACT_TERMS = [
    "개발밀도관리구역",
    "\"개발밀도관리구역\"",
]

ACTION_TERMS = [
    "개발밀도관리구역 지정",
    "개발밀도관리구역 변경",
    "개발밀도관리구역 해제",
    "개발밀도관리구역 결정",
    "개발밀도관리구역 변경결정",
]

NOTICE_TERMS = [
    "개발밀도관리구역 고시",
    "개발밀도관리구역 고시문",
    "개발밀도관리구역 공고",
    "개발밀도관리구역 고시번호",
]

URBAN_TERMS = [
    "개발밀도관리구역 도시관리계획",
    "개발밀도관리구역 도시계획",
    "개발밀도관리구역 지형도면",
    "개발밀도관리구역 기반시설",
    "기반시설부담구역 개발밀도관리구역",
]

ARCHIVE_TERMS = [
    "개발밀도관리구역 시보",
    "개발밀도관리구역 군보",
    "개발밀도관리구역 구보",
    "개발밀도관리구역 공보",
    "개발밀도관리구역 관보",
    "개발밀도관리구역 기록물",
]


# ============================================================
# REGION HINTS
# ============================================================

REGION_NAMES = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "강원도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라북도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]


# ============================================================
# URL CANONICALIZATION
# ============================================================

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "csrftoken",
    "sessionid",
    "jsessionid",
    "timestamp",
    "rand",
    "random",
    "cachebuster",
    "cache_buster",
    "cb",
    "ts",
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

DISCOVERY_QUERY_KEYS = {
    "keyword",
    "searchkeyword",
    "searchword",
    "searchwrd",
    "searchtext",
    "searchterm",
    "query",
    "q",
    "srchtext",
    "srchword",
    "srchkeyword",
    "search",
}

JSESSIONID_PATTERN = re.compile(
    r";jsessionid=[^/?]+",
    re.IGNORECASE,
)


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


def normalize_query_key(
    key: str,
) -> str:

    value = html.unescape(
        str(
            key
            or ""
        )
    ).strip()

    while value.lower().startswith(
        "amp;"
    ):
        value = value[
            4:
        ].strip()

    return value


def canonicalize_url(
    url: str,
    *,
    remove_discovery_query: bool = True,
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

        return value

    if not parsed.hostname:

        return value

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

    path = JSESSIONID_PATTERN.sub(
        "",
        path,
    )

    path = re.sub(
        r"/{2,}",
        "/",
        path,
    )

    query_items: List[
        Tuple[str, str]
    ] = []

    seen_pairs: Set[
        Tuple[str, str]
    ] = set()

    for raw_key, query_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        key = normalize_query_key(
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

        if (
            remove_discovery_query
            and lowered in DISCOVERY_QUERY_KEYS
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


def safe_load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():

        raise FileNotFoundError(
            f"Input not found: {path}"
        )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        data,
        dict,
    ):

        raise TypeError(
            f"JSON input must be an object: {path}"
        )

    return data


# ============================================================
# RECURSIVE RECORD WALKER
# ============================================================

def walk_dicts(
    value: Any,
) -> Iterable[Dict[str, Any]]:

    if isinstance(
        value,
        dict,
    ):

        yield value

        for child in value.values():

            if isinstance(
                child,
                (
                    dict,
                    list,
                ),
            ):

                yield from walk_dicts(
                    child
                )

    elif isinstance(
        value,
        list,
    ):

        for item in value:

            if isinstance(
                item,
                (
                    dict,
                    list,
                ),
            ):

                yield from walk_dicts(
                    item
                )


# ============================================================
# EXCLUSION MEMORY
# ============================================================

def collect_urls_from_data(
    data: Dict[str, Any],
    *,
    allow_keys: Optional[Set[str]] = None,
) -> Set[str]:

    result: Set[str] = set()

    for record in walk_dicts(
        data
    ):

        for key, value in record.items():

            lowered_key = normalize_space(
                key
            ).lower()

            if allow_keys is not None:

                if lowered_key not in allow_keys:
                    continue

            else:

                if not (
                    lowered_key.endswith(
                        "url"
                    )
                    or lowered_key.endswith(
                        "_url"
                    )
                ):
                    continue

            if not isinstance(
                value,
                str,
            ):
                continue

            url = canonicalize_url(
                value
            )

            if not url:
                continue

            if not urlparse(
                url
            ).hostname:
                continue

            result.add(
                url
            )

    return result


def collect_negative_urls(
    m_stage_data: Dict[str, Any],
) -> Set[str]:

    negative: Set[str] = set()

    for record in walk_dicts(
        m_stage_data
    ):

        resolution = normalize_space(
            record.get(
                "resolution"
            )
        )

        if resolution not in {
            "GAZETTE_RECOVERED_ATTACHMENT_UNRELATED_DOCUMENT",
            "GAZETTE_RECOVERED_ATTACHMENT_TARGET_MENTION_ONLY",
        }:
            continue

        raw_url = (
            record.get(
                "url"
            )
            or record.get(
                "child_url"
            )
            or record.get(
                "document_url"
            )
            or record.get(
                "source_url"
            )
            or ""
        )

        url = canonicalize_url(
            raw_url
        )

        if url:
            negative.add(
                url
            )

    return negative


def collect_prior_false_positive_urls(
    y_stage_data: Dict[str, Any],
) -> Set[str]:

    result: Set[str] = set()

    excluded_resolutions = {
        "ADMINISTRATIVE_DUTY_REFERENCE_ONLY",
        "LEGAL_REFERENCE_ONLY",
        "TARGET_MENTION_ONLY",
        "UNRELATED_DOCUMENT",
    }

    for record in walk_dicts(
        y_stage_data
    ):

        resolution = normalize_space(
            record.get(
                "resolution"
            )
        )

        if resolution not in excluded_resolutions:
            continue

        raw_url = (
            record.get(
                "url"
            )
            or record.get(
                "document_url"
            )
            or record.get(
                "source_url"
            )
            or ""
        )

        url = canonicalize_url(
            raw_url
        )

        if url:
            result.add(
                url
            )

    return result


def collect_o_stage_candidate_urls(
    o_stage_data: Dict[str, Any],
) -> Set[str]:

    result: Set[str] = set()

    for record in walk_dicts(
        o_stage_data
    ):

        classification = normalize_space(
            record.get(
                "classification"
            )
        )

        if not classification:
            continue

        if not (
            classification.startswith(
                "HISTORICAL_"
            )
            or classification.startswith(
                "EXCLUDED_"
            )
        ):
            continue

        raw_url = (
            record.get(
                "url"
            )
            or record.get(
                "document_url"
            )
            or ""
        )

        url = canonicalize_url(
            raw_url
        )

        if url:
            result.add(
                url
            )

    return result


# ============================================================
# SOURCE FAMILIES
# ============================================================

def build_source_families() -> List[Dict[str, Any]]:

    return [
        {
            "source_family": (
                SOURCE_FAMILY_NATIONAL_ARCHIVES
            ),
            "priority": 100,
            "target_class": (
                TARGET_CLASS_PRIMARY
            ),
            "purpose": (
                "국가기록원 및 공공기록물 계열에서 "
                "개발밀도관리구역 초기 지정 고시와 "
                "과거 행정문서를 역탐색한다."
            ),
            "expected_document_types": [
                "RECORD_DETAIL",
                "PDF",
                "HWP",
                "HWPX",
                "IMAGE_SCAN",
            ],
            "search_page_final_positive_allowed": False,
        },

        {
            "source_family": (
                SOURCE_FAMILY_OFFICIAL_GAZETTE
            ),
            "priority": 95,
            "target_class": (
                TARGET_CLASS_PRIMARY
            ),
            "purpose": (
                "관보/전자관보/공식 공보에서 "
                "개발밀도관리구역 지정·변경·해제 고시를 찾는다."
            ),
            "expected_document_types": [
                "GAZETTE_ISSUE",
                "PDF",
                "HWP",
                "NOTICE_DETAIL",
            ],
            "search_page_final_positive_allowed": False,
        },

        {
            "source_family": (
                SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE
            ),
            "priority": 90,
            "target_class": (
                TARGET_CLASS_PRIMARY
            ),
            "purpose": (
                "현행 지자체 홈페이지 이전에 운영된 "
                "구형 시보·군보·구보·공보 archive를 찾는다."
            ),
            "expected_document_types": [
                "GAZETTE_ISSUE",
                "PDF",
                "HWP",
                "HWPX",
            ],
            "search_page_final_positive_allowed": False,
        },

        {
            "source_family": (
                SOURCE_FAMILY_LEGACY_LOCAL_NOTICE
            ),
            "priority": 90,
            "target_class": (
                TARGET_CLASS_PRIMARY
            ),
            "purpose": (
                "구형 전자민원/고시공고 시스템과 "
                "이전 홈페이지의 도시계획 고시 원문을 찾는다."
            ),
            "expected_document_types": [
                "NOTICE_DETAIL",
                "PDF",
                "HWP",
                "HWPX",
            ],
            "search_page_final_positive_allowed": False,
        },

        {
            "source_family": (
                SOURCE_FAMILY_URBAN_PLANNING_ARCHIVE
            ),
            "priority": 85,
            "target_class": (
                TARGET_CLASS_PRIMARY
            ),
            "purpose": (
                "도시관리계획, 도시계획, 지형도면 및 "
                "용도구역 historical archive에서 "
                "개발밀도관리구역 관련 고시를 찾는다."
            ),
            "expected_document_types": [
                "URBAN_NOTICE",
                "PDF",
                "HWP",
                "PLAN_DOCUMENT",
            ],
            "search_page_final_positive_allowed": False,
        },

        {
            "source_family": (
                SOURCE_FAMILY_LAND_USE_ARCHIVE
            ),
            "priority": 70,
            "target_class": (
                TARGET_CLASS_SECONDARY
            ),
            "purpose": (
                "토지이용계획/토지이음 historical source에서 "
                "개발밀도관리구역의 지정 identity 또는 "
                "연계 고시번호를 찾는다."
            ),
            "expected_document_types": [
                "LAND_USE_RECORD",
                "NOTICE_REFERENCE",
                "PLAN_RECORD",
            ],
            "search_page_final_positive_allowed": False,
        },

        {
            "source_family": (
                SOURCE_FAMILY_NOTICE_REVERSE
            ),
            "priority": 80,
            "target_class": (
                TARGET_CLASS_REVERSE_LOOKUP
            ),
            "purpose": (
                "부분적으로 확보된 고시번호 또는 "
                "고시번호 형식을 이용해 원문을 역탐색한다."
            ),
            "expected_document_types": [
                "NOTICE_DETAIL",
                "PDF",
                "HWP",
                "GAZETTE_ISSUE",
            ],
            "search_page_final_positive_allowed": False,
        },
    ]


# ============================================================
# HISTORICAL SOURCE TARGETS
# ============================================================

def build_historical_source_targets(
    source_families: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    family_map = {
        item[
            "source_family"
        ]: item
        for item in source_families
    }

    raw_targets = [
        {
            "name": "국가기록원 기록물 검색",
            "source_family": (
                SOURCE_FAMILY_NATIONAL_ARCHIVES
            ),
            "source_scope": "NATIONAL",
            "requires_endpoint_discovery": True,
            "priority_boost": 20,
            "search_strategy": (
                "TARGET_EXACT_AND_NOTICE_REVERSE"
            ),
        },

        {
            "name": "국가 관보/전자관보",
            "source_family": (
                SOURCE_FAMILY_OFFICIAL_GAZETTE
            ),
            "source_scope": "NATIONAL",
            "requires_endpoint_discovery": True,
            "priority_boost": 15,
            "search_strategy": (
                "TARGET_EXACT_AND_YEAR"
            ),
        },

        {
            "name": "구형 지자체 공보 archive",
            "source_family": (
                SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE
            ),
            "source_scope": "LOCAL",
            "requires_endpoint_discovery": True,
            "priority_boost": 15,
            "search_strategy": (
                "TARGET_EXACT_AND_GAZETTE"
            ),
        },

        {
            "name": "구형 지자체 고시공고 archive",
            "source_family": (
                SOURCE_FAMILY_LEGACY_LOCAL_NOTICE
            ),
            "source_scope": "LOCAL",
            "requires_endpoint_discovery": True,
            "priority_boost": 15,
            "search_strategy": (
                "TARGET_EXACT_AND_ACTION"
            ),
        },

        {
            "name": "도시관리계획 historical archive",
            "source_family": (
                SOURCE_FAMILY_URBAN_PLANNING_ARCHIVE
            ),
            "source_scope": "LOCAL_AND_REGIONAL",
            "requires_endpoint_discovery": True,
            "priority_boost": 10,
            "search_strategy": (
                "TARGET_URBAN_PLANNING"
            ),
        },

        {
            "name": "지형도면 historical archive",
            "source_family": (
                SOURCE_FAMILY_URBAN_PLANNING_ARCHIVE
            ),
            "source_scope": "LOCAL_AND_REGIONAL",
            "requires_endpoint_discovery": True,
            "priority_boost": 10,
            "search_strategy": (
                "TARGET_TOPOGRAPHIC_NOTICE"
            ),
        },

        {
            "name": "토지이음/토지이용계획 historical source",
            "source_family": (
                SOURCE_FAMILY_LAND_USE_ARCHIVE
            ),
            "source_scope": "NATIONAL",
            "requires_endpoint_discovery": True,
            "priority_boost": 0,
            "search_strategy": (
                "TARGET_OR_NOTICE_IDENTITY"
            ),
        },

        {
            "name": "고시번호 역탐색",
            "source_family": (
                SOURCE_FAMILY_NOTICE_REVERSE
            ),
            "source_scope": "NATIONAL_AND_LOCAL",
            "requires_endpoint_discovery": True,
            "priority_boost": 5,
            "search_strategy": (
                "NOTICE_NUMBER_REVERSE_LOOKUP"
            ),
        },
    ]

    result: List[
        Dict[str, Any]
    ] = []

    for index, item in enumerate(
        raw_targets,
        start=1,
    ):

        family = family_map[
            item[
                "source_family"
            ]
        ]

        priority = (
            int(
                family[
                    "priority"
                ]
            )
            + int(
                item.get(
                    "priority_boost"
                )
                or 0
            )
        )

        result.append(
            {
                "target_index": index,
                "name": item[
                    "name"
                ],
                "source_family": item[
                    "source_family"
                ],
                "target_class": family[
                    "target_class"
                ],
                "source_scope": item[
                    "source_scope"
                ],
                "priority": priority,
                "search_strategy": item[
                    "search_strategy"
                ],
                "requires_endpoint_discovery": (
                    item[
                        "requires_endpoint_discovery"
                    ]
                ),
                "search_page_final_positive_allowed": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
            }
        )

    result.sort(
        key=lambda item: (
            -int(
                item[
                    "priority"
                ]
            ),
            int(
                item[
                    "target_index"
                ]
            ),
        )
    )

    return result


# ============================================================
# QUERY MATRIX
# ============================================================

def make_query_record(
    *,
    query_index: int,
    query_class: str,
    query_text: str,
    period: Dict[str, Any],
    source_family: str,
    priority_boost: int = 0,
) -> Dict[str, Any]:

    priority = (
        int(
            period[
                "priority"
            ]
        )
        + priority_boost
    )

    return {
        "query_index": query_index,
        "query_class": query_class,
        "query_text": normalize_space(
            query_text
        ),
        "source_family": source_family,
        "period_class": period[
            "period_class"
        ],
        "start_year": period[
            "start_year"
        ],
        "end_year": period[
            "end_year"
        ],
        "priority": priority,
        "search_page_final_positive_allowed": False,
        "detail_seed_final_positive_allowed": False,
        "attachment_seed_final_positive_allowed": False,
    }


def build_query_matrix() -> List[Dict[str, Any]]:

    result: List[
        Dict[str, Any]
    ] = []

    query_index = 0

    for period in PERIODS:

        # ----------------------------------------------------
        # Exact
        # ----------------------------------------------------

        for term in BASE_EXACT_TERMS:

            query_index += 1

            result.append(
                make_query_record(
                    query_index=query_index,
                    query_class=QUERY_CLASS_EXACT,
                    query_text=term,
                    period=period,
                    source_family=(
                        SOURCE_FAMILY_NATIONAL_ARCHIVES
                    ),
                    priority_boost=25,
                )
            )

        # ----------------------------------------------------
        # Action
        # ----------------------------------------------------

        for term in ACTION_TERMS:

            query_index += 1

            result.append(
                make_query_record(
                    query_index=query_index,
                    query_class=QUERY_CLASS_ACTION,
                    query_text=term,
                    period=period,
                    source_family=(
                        SOURCE_FAMILY_LEGACY_LOCAL_NOTICE
                    ),
                    priority_boost=20,
                )
            )

        # ----------------------------------------------------
        # Notice
        # ----------------------------------------------------

        for term in NOTICE_TERMS:

            query_index += 1

            result.append(
                make_query_record(
                    query_index=query_index,
                    query_class=QUERY_CLASS_NOTICE,
                    query_text=term,
                    period=period,
                    source_family=(
                        SOURCE_FAMILY_OFFICIAL_GAZETTE
                    ),
                    priority_boost=20,
                )
            )

        # ----------------------------------------------------
        # Urban
        # ----------------------------------------------------

        for term in URBAN_TERMS:

            query_index += 1

            result.append(
                make_query_record(
                    query_index=query_index,
                    query_class=QUERY_CLASS_URBAN,
                    query_text=term,
                    period=period,
                    source_family=(
                        SOURCE_FAMILY_URBAN_PLANNING_ARCHIVE
                    ),
                    priority_boost=15,
                )
            )

        # ----------------------------------------------------
        # Archive
        # ----------------------------------------------------

        for term in ARCHIVE_TERMS:

            query_index += 1

            result.append(
                make_query_record(
                    query_index=query_index,
                    query_class=QUERY_CLASS_ARCHIVE,
                    query_text=term,
                    period=period,
                    source_family=(
                        SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE
                    ),
                    priority_boost=10,
                )
            )

    # --------------------------------------------------------
    # dedupe
    # --------------------------------------------------------

    unique: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[
            str,
            str,
            int,
            int,
            str,
        ]
    ] = set()

    for item in result:

        key = (
            item[
                "query_class"
            ],
            item[
                "query_text"
            ],
            int(
                item[
                    "start_year"
                ]
            ),
            int(
                item[
                    "end_year"
                ]
            ),
            item[
                "source_family"
            ],
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique.append(
            item
        )

    # query index 재부여
    for index, item in enumerate(
        unique,
        start=1,
    ):

        item[
            "query_index"
        ] = index

    unique.sort(
        key=lambda item: (
            -int(
                item[
                    "priority"
                ]
            ),
            int(
                item[
                    "query_index"
                ]
            ),
        )
    )

    return unique


# ============================================================
# REGION QUERY MATRIX
# ============================================================

def build_region_query_matrix() -> List[Dict[str, Any]]:

    result: List[
        Dict[str, Any]
    ] = []

    index = 0

    for period in PERIODS:

        for region in REGION_NAMES:

            index += 1

            result.append(
                {
                    "query_index": index,
                    "query_class": (
                        QUERY_CLASS_REGION
                    ),
                    "query_text": (
                        f"{region} {TARGET_NAME}"
                    ),
                    "region": region,
                    "source_family": (
                        SOURCE_FAMILY_LEGACY_LOCAL_NOTICE
                    ),
                    "period_class": (
                        period[
                            "period_class"
                        ]
                    ),
                    "start_year": (
                        period[
                            "start_year"
                        ]
                    ),
                    "end_year": (
                        period[
                            "end_year"
                        ]
                    ),
                    "priority": (
                        period[
                            "priority"
                        ]
                    ),
                    "search_page_final_positive_allowed": False,
                }
            )

    return result


# ============================================================
# NOTICE NUMBER EXTRACTION FROM PRIOR DATA
# ============================================================

NOTICE_NUMBER_PATTERNS = [
    re.compile(
        r"(?P<notice>"
        r"(?:서울특별시|부산광역시|대구광역시|인천광역시|"
        r"광주광역시|대전광역시|울산광역시|세종특별자치시|"
        r"경기도|강원특별자치도|강원도|충청북도|충청남도|"
        r"전북특별자치도|전라북도|전라남도|경상북도|경상남도|"
        r"제주특별자치도|"
        r"[가-힣]{2,12}시|[가-힣]{2,12}군|[가-힣]{2,12}구)"
        r"\s*(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
    ),

    re.compile(
        r"(?P<notice>"
        r"(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
    ),
]


def extract_notice_numbers_from_data(
    *datasets: Dict[str, Any],
) -> List[str]:

    result: List[str] = []

    for data in datasets:

        serialized = json.dumps(
            data,
            ensure_ascii=False,
        )

        for pattern in NOTICE_NUMBER_PATTERNS:

            for match in pattern.finditer(
                serialized
            ):

                notice = normalize_space(
                    match.groupdict().get(
                        "notice"
                    )
                    or match.group(0)
                )

                if notice:

                    result.append(
                        notice
                    )

    return unique_strings(
        result
    )


# ============================================================
# NOTICE REVERSE LOOKUP MATRIX
# ============================================================

def build_notice_reverse_lookup_matrix(
    notice_numbers: List[str],
) -> List[Dict[str, Any]]:

    result: List[
        Dict[str, Any]
    ] = []

    index = 0

    # --------------------------------------------------------
    # Known notice identities
    # --------------------------------------------------------

    for notice in notice_numbers:

        for suffix in [
            "",
            " 개발밀도관리구역",
            " 도시관리계획",
            " 지형도면",
        ]:

            index += 1

            result.append(
                {
                    "query_index": index,
                    "query_class": (
                        QUERY_CLASS_NOTICE_REVERSE
                    ),
                    "source_family": (
                        SOURCE_FAMILY_NOTICE_REVERSE
                    ),
                    "notice_number": notice,
                    "query_text": normalize_space(
                        f"{notice}{suffix}"
                    ),
                    "identity_known": True,
                    "priority": 100,
                    "search_page_final_positive_allowed": False,
                }
            )

    # --------------------------------------------------------
    # Generic reverse templates
    # --------------------------------------------------------

    generic_templates = [
        "{region} 고시 제{year}-*호 개발밀도관리구역",
        "{region} 고시 {year} 개발밀도관리구역",
        "{region} 도시관리계획 개발밀도관리구역 고시",
        "{region} 개발밀도관리구역 지정 고시",
    ]

    for period in PERIODS:

        for region in REGION_NAMES:

            for template in generic_templates:

                index += 1

                query_text = template.format(
                    region=region,
                    year=(
                        f"{period['start_year']}"
                        if period[
                            "start_year"
                        ]
                        == period[
                            "end_year"
                        ]
                        else (
                            f"{period['start_year']}"
                            f"-{period['end_year']}"
                        )
                    ),
                )

                result.append(
                    {
                        "query_index": index,
                        "query_class": (
                            QUERY_CLASS_NOTICE_REVERSE
                        ),
                        "source_family": (
                            SOURCE_FAMILY_NOTICE_REVERSE
                        ),
                        "notice_number": "",
                        "query_text": normalize_space(
                            query_text
                        ),
                        "identity_known": False,
                        "region": region,
                        "period_class": (
                            period[
                                "period_class"
                            ]
                        ),
                        "start_year": (
                            period[
                                "start_year"
                            ]
                        ),
                        "end_year": (
                            period[
                                "end_year"
                            ]
                        ),
                        "priority": (
                            period[
                                "priority"
                            ]
                            + 10
                        ),
                        "search_page_final_positive_allowed": False,
                    }
                )

    # --------------------------------------------------------
    # dedupe
    # --------------------------------------------------------

    deduped: List[
        Dict[str, Any]
    ] = []

    seen: Set[str] = set()

    for item in result:

        key = normalize_space(
            item[
                "query_text"
            ]
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        deduped.append(
            item
        )

    for index, item in enumerate(
        deduped,
        start=1,
    ):

        item[
            "query_index"
        ] = index

    return deduped


# ============================================================
# NEXT STAGE POOL
# ============================================================

def build_next_stage_source_discovery_pool(
    source_targets: List[Dict[str, Any]],
    query_matrix: List[Dict[str, Any]],
    region_query_matrix: List[Dict[str, Any]],
    notice_reverse_matrix: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    family_queries: Dict[
        str,
        List[Dict[str, Any]],
    ] = {}

    for family in VALID_SOURCE_FAMILIES:

        family_queries[
            family
        ] = []

    for item in (
        query_matrix
        + region_query_matrix
        + notice_reverse_matrix
    ):

        family = normalize_space(
            item.get(
                "source_family"
            )
        )

        if family not in family_queries:
            continue

        family_queries[
            family
        ].append(
            item
        )

    result: List[
        Dict[str, Any]
    ] = []

    for target in source_targets:

        family = target[
            "source_family"
        ]

        queries = family_queries.get(
            family,
            [],
        )

        queries = sorted(
            queries,
            key=lambda item: (
                -int(
                    item.get(
                        "priority"
                    )
                    or 0
                ),
                int(
                    item.get(
                        "query_index"
                    )
                    or 0
                ),
            ),
        )

        result.append(
            {
                "target_index": target[
                    "target_index"
                ],
                "name": target[
                    "name"
                ],
                "source_family": family,
                "target_class": target[
                    "target_class"
                ],
                "priority": target[
                    "priority"
                ],
                "search_strategy": target[
                    "search_strategy"
                ],
                "requires_endpoint_discovery": target[
                    "requires_endpoint_discovery"
                ],
                "query_count": len(
                    queries
                ),
                "queries": queries,
                "search_page_final_positive_allowed": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "final_positive_promotion_allowed": False,
            }
        )

    result.sort(
        key=lambda item: (
            -int(
                item[
                    "priority"
                ]
            ),
            int(
                item[
                    "target_index"
                ]
            ),
        )
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
        "HISTORICAL OFFICIAL SOURCE EXPANSION"
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

    print()

    # ========================================================
    # INPUT
    # ========================================================

    o_stage_data = safe_load_json(
        O_STAGE_INPUT_PATH
    )

    n_stage_data = safe_load_json(
        N_STAGE_INPUT_PATH
    )

    m_stage_data = safe_load_json(
        M_STAGE_INPUT_PATH
    )

    y_stage_data = safe_load_json(
        Y_STAGE_INPUT_PATH
    )

    print(
        "O-stage input:",
        O_STAGE_INPUT_PATH,
    )

    print(
        "N-stage input:",
        N_STAGE_INPUT_PATH,
    )

    print(
        "M-stage input:",
        M_STAGE_INPUT_PATH,
    )

    print(
        "Y-stage input:",
        Y_STAGE_INPUT_PATH,
    )

    print()

    # ========================================================
    # EXCLUSION MEMORY
    # ========================================================

    negative_urls = (
        collect_negative_urls(
            m_stage_data
        )
    )

    false_positive_urls = (
        collect_prior_false_positive_urls(
            y_stage_data
        )
    )

    o_stage_urls = (
        collect_o_stage_candidate_urls(
            o_stage_data
        )
    )

    exclusion_urls = (
        negative_urls
        | false_positive_urls
        | o_stage_urls
    )

    print(
        "M-stage negative URLs:",
        len(
            negative_urls
        ),
    )

    print(
        "Prior false-positive URLs:",
        len(
            false_positive_urls
        ),
    )

    print(
        "O-stage candidate URLs:",
        len(
            o_stage_urls
        ),
    )

    print(
        "Total exclusion URLs:",
        len(
            exclusion_urls
        ),
    )

    print()

    # ========================================================
    # SOURCE FAMILY
    # ========================================================

    source_families = (
        build_source_families()
    )

    historical_source_targets = (
        build_historical_source_targets(
            source_families
        )
    )

    # ========================================================
    # QUERY MATRIX
    # ========================================================

    query_matrix = (
        build_query_matrix()
    )

    region_query_matrix = (
        build_region_query_matrix()
    )

    notice_numbers = (
        extract_notice_numbers_from_data(
            o_stage_data,
            n_stage_data,
            m_stage_data,
            y_stage_data,
        )
    )

    notice_reverse_lookup_matrix = (
        build_notice_reverse_lookup_matrix(
            notice_numbers
        )
    )

    next_stage_source_discovery_pool = (
        build_next_stage_source_discovery_pool(
            historical_source_targets,
            query_matrix,
            region_query_matrix,
            notice_reverse_lookup_matrix,
        )
    )

    # ========================================================
    # PERIOD PRINT
    # ========================================================

    print(
        "Historical source family count:",
        len(
            source_families
        ),
    )

    print(
        "Historical source target count:",
        len(
            historical_source_targets
        ),
    )

    print(
        "Base query matrix:",
        len(
            query_matrix
        ),
    )

    print(
        "Region query matrix:",
        len(
            region_query_matrix
        ),
    )

    print(
        "Known notice number count:",
        len(
            notice_numbers
        ),
    )

    print(
        "Notice reverse lookup matrix:",
        len(
            notice_reverse_lookup_matrix
        ),
    )

    print()

    print(
        "Period strategy"
    )

    print(
        "-" * 60
    )

    for period in PERIODS:

        print(
            f"{period['period_class']} : "
            f"{period['start_year']} - "
            f"{period['end_year']} "
            f"| priority={period['priority']}"
        )

    # ========================================================
    # COUNTS
    # ========================================================

    source_family_counts = Counter(
        item[
            "source_family"
        ]
        for item in historical_source_targets
    )

    query_class_counts = Counter(
        item[
            "query_class"
        ]
        for item in (
            query_matrix
            + region_query_matrix
            + notice_reverse_lookup_matrix
        )
    )

    # ========================================================
    # RESOLUTION
    # ========================================================

    resolution = (
        "HISTORICAL_OFFICIAL_SOURCE_EXPANSION_READY"
    )

    next_action = (
        "기존 현대 지자체 endpoint brute-force를 반복하지 않고 "
        "NATIONAL_ARCHIVES, OFFICIAL_GAZETTE, "
        "LEGACY_LOCAL_GAZETTE, LEGACY_LOCAL_NOTICE, "
        "URBAN_PLANNING_ARCHIVE, LAND_USE_ARCHIVE 및 "
        "NOTICE_NUMBER_REVERSE_LOOKUP source family별로 "
        "실제 공식 historical endpoint를 발견한다. "
        "Q-stage에서는 동일 response hash suppression, "
        "endpoint circuit breaker, negative URL exclusion을 적용하고, "
        "검색 결과 page가 아닌 detail/attachment/issue identity만 "
        "verification seed로 승격한다."
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-P "
            "Development Density Management Area "
            "Historical Official Source Expansion"
        ),

        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },

        "inputs": {
            "o_stage_historical_archive_discovery": str(
                O_STAGE_INPUT_PATH
            ),
            "n_stage_historical_recovery_expansion": str(
                N_STAGE_INPUT_PATH
            ),
            "m_stage_gazette_attachment_verification": str(
                M_STAGE_INPUT_PATH
            ),
            "y_stage_target_document_verification": str(
                Y_STAGE_INPUT_PATH
            ),
            "o_stage_resolution": (
                o_stage_data.get(
                    "resolution"
                )
            ),
            "m_stage_resolution": (
                m_stage_data.get(
                    "resolution"
                )
            ),
        },

        "method": {
            "modern_local_endpoint_bruteforce_repeat": False,

            "historical_source_family_expansion": True,

            "national_archives_enabled": True,

            "official_gazette_enabled": True,

            "legacy_local_gazette_enabled": True,

            "legacy_local_notice_enabled": True,

            "urban_planning_archive_enabled": True,

            "land_use_archive_enabled": True,

            "notice_number_reverse_lookup_enabled": True,

            "exact_target_priority_enabled": True,

            "early_period_priority_enabled": True,

            "negative_url_exclusion_memory": True,

            "prior_false_positive_exclusion_memory": True,

            "o_stage_candidate_exclusion_memory": True,

            "response_hash_suppression_required_next_stage": True,

            "endpoint_circuit_breaker_required_next_stage": True,

            "identical_html_analysis_suppression_required_next_stage": True,

            "search_page_final_positive_allowed": False,

            "detail_seed_final_positive_allowed": False,

            "attachment_seed_final_positive_allowed": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,

            "final_positive_promotion_allowed": False,
        },

        "period_strategy": PERIODS,

        "source_families": source_families,

        "historical_source_targets": (
            historical_source_targets
        ),

        "query_matrix": query_matrix,

        "region_query_matrix": (
            region_query_matrix
        ),

        "known_notice_numbers": (
            notice_numbers
        ),

        "notice_reverse_lookup_matrix": (
            notice_reverse_lookup_matrix
        ),

        "exclusion_memory": {
            "m_stage_negative_urls": sorted(
                negative_urls
            ),
            "prior_false_positive_urls": sorted(
                false_positive_urls
            ),
            "o_stage_candidate_urls": sorted(
                o_stage_urls
            ),
            "all_exclusion_urls": sorted(
                exclusion_urls
            ),
        },

        "next_stage_source_discovery_pool": (
            next_stage_source_discovery_pool
        ),

        "summary": {
            "source_family_count": len(
                source_families
            ),
            "historical_source_target_count": len(
                historical_source_targets
            ),
            "base_query_count": len(
                query_matrix
            ),
            "region_query_count": len(
                region_query_matrix
            ),
            "known_notice_number_count": len(
                notice_numbers
            ),
            "notice_reverse_lookup_query_count": len(
                notice_reverse_lookup_matrix
            ),
            "next_stage_source_pool_count": len(
                next_stage_source_discovery_pool
            ),
            "m_stage_negative_url_count": len(
                negative_urls
            ),
            "prior_false_positive_url_count": len(
                false_positive_urls
            ),
            "o_stage_candidate_url_count": len(
                o_stage_urls
            ),
            "total_exclusion_url_count": len(
                exclusion_urls
            ),
        },

        "source_family_counts": dict(
            sorted(
                source_family_counts.items()
            )
        ),

        "query_class_counts": dict(
            sorted(
                query_class_counts.items()
            )
        ),

        "resolution": resolution,

        "next_action": next_action,

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
    # RESULT PRINT
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "HISTORICAL SOURCE EXPANSION RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "Source family count:",
        len(
            source_families
        ),
    )

    print(
        "Historical source target count:",
        len(
            historical_source_targets
        ),
    )

    print(
        "Base query count:",
        len(
            query_matrix
        ),
    )

    print(
        "Region query count:",
        len(
            region_query_matrix
        ),
    )

    print(
        "Known notice number count:",
        len(
            notice_numbers
        ),
    )

    print(
        "Notice reverse lookup query count:",
        len(
            notice_reverse_lookup_matrix
        ),
    )

    print(
        "Next-stage source pool count:",
        len(
            next_stage_source_discovery_pool
        ),
    )

    print()

    print(
        "SOURCE FAMILY TARGETS"
    )

    print(
        "-" * 60
    )

    for item in historical_source_targets:

        print(
            f"[{item['target_index']}] "
            f"{item['source_family']}"
        )

        print(
            "Name:",
            item[
                "name"
            ],
        )

        print(
            "Class:",
            item[
                "target_class"
            ],
        )

        print(
            "Priority:",
            item[
                "priority"
            ],
        )

        print(
            "Strategy:",
            item[
                "search_strategy"
            ],
        )

        print()

    # ========================================================
    # RESOLUTION PRINT
    # ========================================================

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

    query_keys = {
        (
            item[
                "query_class"
            ],
            item[
                "query_text"
            ],
            item.get(
                "period_class"
            ),
            item[
                "source_family"
            ],
        )
        for item in query_matrix
    }

    region_query_keys = {
        (
            item[
                "query_text"
            ],
            item[
                "period_class"
            ],
            item[
                "source_family"
            ],
        )
        for item in region_query_matrix
    }

    reverse_query_texts = {
        item[
            "query_text"
        ]
        for item in notice_reverse_lookup_matrix
    }

    all_source_families_valid = all(
        item[
            "source_family"
        ]
        in VALID_SOURCE_FAMILIES
        for item in historical_source_targets
    )

    all_target_classes_valid = all(
        item[
            "target_class"
        ]
        in VALID_TARGET_CLASSES
        for item in historical_source_targets
    )

    all_query_classes_valid = all(
        item[
            "query_class"
        ]
        in VALID_QUERY_CLASSES
        for item in (
            query_matrix
            + region_query_matrix
            + notice_reverse_lookup_matrix
        )
    )

    all_base_queries_have_period = all(
        isinstance(
            item.get(
                "start_year"
            ),
            int,
        )
        and isinstance(
            item.get(
                "end_year"
            ),
            int,
        )
        and item[
            "start_year"
        ]
        <= item[
            "end_year"
        ]
        for item in query_matrix
    )

    early_period_present = any(
        item[
            "period_class"
        ]
        == "EARLY制度_PERIOD"
        for item in query_matrix
    )

    early_priority_is_highest = (
        max(
            period[
                "priority"
            ]
            for period in PERIODS
        )
        == next(
            period[
                "priority"
            ]
            for period in PERIODS
            if period[
                "period_class"
            ]
            == "EARLY制度_PERIOD"
        )
    )

    positive_allowed_leakage = sum(
        1
        for item in next_stage_source_discovery_pool
        if (
            item.get(
                "search_page_final_positive_allowed"
            )
            is not False
            or item.get(
                "runtime_registration_allowed"
            )
            is not False
            or item.get(
                "site_positive_allowed"
            )
            is not False
            or item.get(
                "final_positive_promotion_allowed"
            )
            is not False
        )
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

        "O-stage input exists": (
            O_STAGE_INPUT_PATH.exists()
        ),

        "N-stage input exists": (
            N_STAGE_INPUT_PATH.exists()
        ),

        "M-stage input exists": (
            M_STAGE_INPUT_PATH.exists()
        ),

        "Y-stage input exists": (
            Y_STAGE_INPUT_PATH.exists()
        ),

        "O-stage input parsed": (
            isinstance(
                o_stage_data,
                dict,
            )
        ),

        "N-stage input parsed": (
            isinstance(
                n_stage_data,
                dict,
            )
        ),

        "M-stage input parsed": (
            isinstance(
                m_stage_data,
                dict,
            )
        ),

        "Y-stage input parsed": (
            isinstance(
                y_stage_data,
                dict,
            )
        ),

        "O-stage no-seed resolution preserved": (
            normalize_space(
                o_stage_data.get(
                    "resolution"
                )
            )
            == EXPECTED_O_STAGE_RESOLUTION
        ),

        "M-stage no-target resolution preserved": (
            normalize_space(
                m_stage_data.get(
                    "resolution"
                )
            )
            == EXPECTED_M_STAGE_RESOLUTION
        ),

        "modern local endpoint brute-force repeat disabled": (
            output_data[
                "method"
            ][
                "modern_local_endpoint_bruteforce_repeat"
            ]
            is False
        ),

        "historical source family expansion enabled": (
            output_data[
                "method"
            ][
                "historical_source_family_expansion"
            ]
            is True
        ),

        "source families loaded": (
            len(
                source_families
            )
            > 0
        ),

        "all source families valid": (
            all_source_families_valid
        ),

        "all target classes valid": (
            all_target_classes_valid
        ),

        "national archives enabled": (
            output_data[
                "method"
            ][
                "national_archives_enabled"
            ]
            is True
        ),

        "official gazette enabled": (
            output_data[
                "method"
            ][
                "official_gazette_enabled"
            ]
            is True
        ),

        "legacy local gazette enabled": (
            output_data[
                "method"
            ][
                "legacy_local_gazette_enabled"
            ]
            is True
        ),

        "legacy local notice enabled": (
            output_data[
                "method"
            ][
                "legacy_local_notice_enabled"
            ]
            is True
        ),

        "urban planning archive enabled": (
            output_data[
                "method"
            ][
                "urban_planning_archive_enabled"
            ]
            is True
        ),

        "land use archive enabled": (
            output_data[
                "method"
            ][
                "land_use_archive_enabled"
            ]
            is True
        ),

        "notice number reverse lookup enabled": (
            output_data[
                "method"
            ][
                "notice_number_reverse_lookup_enabled"
            ]
            is True
        ),

        "query matrix loaded": (
            len(
                query_matrix
            )
            > 0
        ),

        "query matrix unique": (
            len(
                query_keys
            )
            == len(
                query_matrix
            )
        ),

        "region query matrix unique": (
            len(
                region_query_keys
            )
            == len(
                region_query_matrix
            )
        ),

        "notice reverse query matrix unique": (
            len(
                reverse_query_texts
            )
            == len(
                notice_reverse_lookup_matrix
            )
        ),

        "all query classes valid": (
            all_query_classes_valid
        ),

        "all base queries have period bounds": (
            all_base_queries_have_period
        ),

        "exact target query enabled": any(
            item[
                "query_class"
            ]
            == QUERY_CLASS_EXACT
            for item in query_matrix
        ),

        "action query enabled": any(
            item[
                "query_class"
            ]
            == QUERY_CLASS_ACTION
            for item in query_matrix
        ),

        "notice query enabled": any(
            item[
                "query_class"
            ]
            == QUERY_CLASS_NOTICE
            for item in query_matrix
        ),

        "urban-planning query enabled": any(
            item[
                "query_class"
            ]
            == QUERY_CLASS_URBAN
            for item in query_matrix
        ),

        "archive query enabled": any(
            item[
                "query_class"
            ]
            == QUERY_CLASS_ARCHIVE
            for item in query_matrix
        ),

        "regional target query enabled": (
            len(
                region_query_matrix
            )
            > 0
        ),

        "early period enabled": (
            early_period_present
        ),

        "early period highest priority": (
            early_priority_is_highest
        ),

        "negative URL exclusion memory enabled": (
            output_data[
                "method"
            ][
                "negative_url_exclusion_memory"
            ]
            is True
        ),

        "prior false-positive exclusion memory enabled": (
            output_data[
                "method"
            ][
                "prior_false_positive_exclusion_memory"
            ]
            is True
        ),

        "O-stage candidate exclusion memory enabled": (
            output_data[
                "method"
            ][
                "o_stage_candidate_exclusion_memory"
            ]
            is True
        ),

        "response hash suppression required next stage": (
            output_data[
                "method"
            ][
                "response_hash_suppression_required_next_stage"
            ]
            is True
        ),

        "endpoint circuit breaker required next stage": (
            output_data[
                "method"
            ][
                "endpoint_circuit_breaker_required_next_stage"
            ]
            is True
        ),

        "identical HTML analysis suppression required next stage": (
            output_data[
                "method"
            ][
                "identical_html_analysis_suppression_required_next_stage"
            ]
            is True
        ),

        "next-stage source discovery pool loaded": (
            len(
                next_stage_source_discovery_pool
            )
            > 0
        ),

        "search page final positive prohibited": all(
            item.get(
                "search_page_final_positive_allowed"
            )
            is False
            for item in historical_source_targets
        ),

        "next-stage positive permission leakage zero": (
            positive_allowed_leakage
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
        "Negative URL exclusion count:",
        len(
            negative_urls
        ),
    )

    print(
        "Prior false-positive exclusion count:",
        len(
            false_positive_urls
        ),
    )

    print(
        "O-stage exclusion count:",
        len(
            o_stage_urls
        ),
    )

    print(
        "Positive permission leakage:",
        positive_allowed_leakage,
    )

    all_pass = all(
        validations.values()
    )

    print()

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
            "historical official source expansion "
            "regression failed"
        )


if __name__ == "__main__":
    main()