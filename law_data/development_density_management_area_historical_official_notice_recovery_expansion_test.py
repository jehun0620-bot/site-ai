# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-N
Development Density Management Area
Historical Official Notice Recovery Expansion

목표
======================================================================
M-stage에서 현재 공보 attachment 경로가 negative로 종료되었으므로,
개발밀도관리구역의 과거 지정·변경·해제 고시를 공식 archive에서
역탐색하기 위한 recovery seed를 생성한다.

입력 1:
    law_data/output/
    development_density_management_area_
    gazette_recovered_attachment_source_verification.json

입력 2:
    law_data/output/
    development_density_management_area_
    official_notice_source_verification.json

입력 3:
    law_data/output/
    development_density_management_area_
    target_document_candidate_verification.json

출력:
    law_data/output/
    development_density_management_area_
    historical_official_notice_recovery_expansion.json

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 원칙
======================================================================
1. M-stage에서 확인한 negative document는 exclusion memory로 유지한다.

2. 기존 J/Y-stage false positive도 재승격하지 않는다.

3. 검색 결과/list page는 final positive가 아니다.

4. historical recovery는 다음 identity를 우선 수집한다.

    - exact target phrase
    - target + 지정
    - target + 변경
    - target + 해제
    - target + 고시
    - target + 도시관리계획
    - target + 지형도면
    - target + 기반시설부담구역

5. detail URL / attachment URL / archive issue URL만
   다음 단계 verification seed로 넘긴다.

6. 일반 navigation / 홈페이지 / 검색 page / login page 제외.

7. 행정업무표·사무전결표·업무분장표 제외.

8. 법령·조례의 정의/단순 언급 제외.

9. runtime registration 금지.

10. SITE TRUE/FALSE 자동 판정 금지.

11. final positive promotion 금지.
"""

from __future__ import annotations

import html
import json
import re

from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
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

M_STAGE_INPUT = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gazette_recovered_attachment_source_verification.json"
    )
)

J_STAGE_INPUT = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "official_notice_source_verification.json"
    )
)

Y_STAGE_INPUT = (
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
        "historical_official_notice_recovery_expansion.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# EXPECTED PREVIOUS RESOLUTION
# ============================================================

M_STAGE_EXPECTED_RESOLUTION = (
    "GAZETTE_RECOVERED_ATTACHMENT_VERIFICATION_COMPLETED_NO_TARGET"
)


# ============================================================
# RECOVERY CLASSES
# ============================================================

CLASS_EXACT_TARGET_QUERY = (
    "HISTORICAL_EXACT_TARGET_QUERY"
)

CLASS_ACTION_QUERY = (
    "HISTORICAL_ACTION_QUERY"
)

CLASS_NOTICE_QUERY = (
    "HISTORICAL_NOTICE_QUERY"
)

CLASS_URBAN_QUERY = (
    "HISTORICAL_URBAN_PLANNING_QUERY"
)

CLASS_ARCHIVE_QUERY = (
    "HISTORICAL_ARCHIVE_QUERY"
)

VALID_QUERY_CLASSES = {
    CLASS_EXACT_TARGET_QUERY,
    CLASS_ACTION_QUERY,
    CLASS_NOTICE_QUERY,
    CLASS_URBAN_QUERY,
    CLASS_ARCHIVE_QUERY,
}


# ============================================================
# SEARCH QUERY DEFINITIONS
# ============================================================

QUERY_DEFINITIONS = [
    {
        "classification": CLASS_EXACT_TARGET_QUERY,
        "query": "개발밀도관리구역",
        "priority": 100,
    },

    {
        "classification": CLASS_ACTION_QUERY,
        "query": "개발밀도관리구역 지정",
        "priority": 95,
    },

    {
        "classification": CLASS_ACTION_QUERY,
        "query": "개발밀도관리구역 변경",
        "priority": 95,
    },

    {
        "classification": CLASS_ACTION_QUERY,
        "query": "개발밀도관리구역 해제",
        "priority": 95,
    },

    {
        "classification": CLASS_NOTICE_QUERY,
        "query": "개발밀도관리구역 고시",
        "priority": 90,
    },

    {
        "classification": CLASS_NOTICE_QUERY,
        "query": "개발밀도관리구역 고시문",
        "priority": 90,
    },

    {
        "classification": CLASS_URBAN_QUERY,
        "query": "개발밀도관리구역 도시관리계획",
        "priority": 85,
    },

    {
        "classification": CLASS_URBAN_QUERY,
        "query": "개발밀도관리구역 지형도면",
        "priority": 85,
    },

    {
        "classification": CLASS_URBAN_QUERY,
        "query": "기반시설부담구역 개발밀도관리구역",
        "priority": 80,
    },

    {
        "classification": CLASS_ARCHIVE_QUERY,
        "query": "개발밀도관리구역 시보",
        "priority": 75,
    },

    {
        "classification": CLASS_ARCHIVE_QUERY,
        "query": "개발밀도관리구역 군보",
        "priority": 75,
    },

    {
        "classification": CLASS_ARCHIVE_QUERY,
        "query": "개발밀도관리구역 구보",
        "priority": 75,
    },

    {
        "classification": CLASS_ARCHIVE_QUERY,
        "query": "개발밀도관리구역 공보",
        "priority": 75,
    },
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


# ============================================================
# URL NORMALIZATION
# ============================================================

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "csrftoken",
    "sessionid",
    "jsessionid",
    "_",
    "timestamp",
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

        return value

    if not parsed.hostname:
        return value

    query_items = []

    for key, query_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        lowered = (
            key.lower()
        )

        if lowered in VOLATILE_QUERY_KEYS:
            continue

        if lowered in TRACKING_QUERY_KEYS:
            continue

        if "csrf" in lowered:
            continue

        if "session" in lowered:
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

    return urlunparse(
        (
            (
                parsed.scheme
                or "https"
            ).lower(),

            (
                parsed.netloc
            ).lower(),

            parsed.path
            or "/",

            "",

            urlencode(
                query_items,
                doseq=True,
            ),

            "",
        )
    )


# ============================================================
# INPUT LOAD
# ============================================================

def load_json(
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
            f"JSON root must be object: {path}"
        )

    return data


# ============================================================
# EXCLUSION MEMORY
# ============================================================

def collect_negative_document_urls(
    m_stage_data: Dict[str, Any],
) -> Set[str]:

    result: Set[str] = set()

    for item in (
        m_stage_data.get(
            "verification_records"
        )
        or []
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        if item.get(
            "verified_positive"
        ) is True:
            continue

        url = canonicalize_url(
            item.get(
                "document_url"
            )
            or ""
        )

        if url:

            result.add(
                url
            )

    return result


def collect_prior_false_positive_urls(
    *datasets: Dict[str, Any],
) -> Set[str]:

    result: Set[str] = set()

    excluded_resolutions = {
        "ADMINISTRATIVE_DUTY_REFERENCE_ONLY",
        "LEGAL_REFERENCE_ONLY",
        "TARGET_MENTION_ONLY",

        "GAZETTE_CHILD_ADMINISTRATIVE_DUTY_REFERENCE",
        "GAZETTE_CHILD_LEGAL_REFERENCE_ONLY",
        "GAZETTE_CHILD_TARGET_MENTION_ONLY",

        "GAZETTE_RECOVERED_ATTACHMENT_ADMINISTRATIVE_DUTY_REFERENCE",
        "GAZETTE_RECOVERED_ATTACHMENT_LEGAL_REFERENCE_ONLY",
        "GAZETTE_RECOVERED_ATTACHMENT_TARGET_MENTION_ONLY",
        "GAZETTE_RECOVERED_ATTACHMENT_UNRELATED_DOCUMENT",
    }

    def walk(
        value: Any,
    ) -> None:

        if isinstance(
            value,
            dict,
        ):

            resolution = normalize_space(
                value.get(
                    "resolution"
                )
            )

            if resolution in excluded_resolutions:

                url = canonicalize_url(
                    value.get(
                        "url"
                    )
                    or value.get(
                        "document_url"
                    )
                    or value.get(
                        "child_url"
                    )
                    or value.get(
                        "source_url"
                    )
                    or ""
                )

                if url:

                    result.add(
                        url
                    )

            for child in value.values():

                if isinstance(
                    child,
                    (
                        dict,
                        list,
                    ),
                ):

                    walk(
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

                    walk(
                        item
                    )

    for dataset in datasets:

        walk(
            dataset
        )

    return result


# ============================================================
# HISTORICAL PERIOD STRATEGY
# ============================================================

def build_period_strategy() -> List[Dict[str, Any]]:

    """
    개발밀도관리구역 제도는 현재 문서만 보는 것이 아니라
    장기간 과거 고시를 탐색해야 하므로 검색 구간을 나눈다.

    이 단계에서는 실제 검색을 실행하지 않고
    다음 discovery 단계의 deterministic search plan을 만든다.
    """

    return [
        {
            "period_class": "EARLY制度_PERIOD",
            "year_from": 2000,
            "year_to": 2009,
            "priority": 100,
        },

        {
            "period_class": "MIDDLE_PERIOD",
            "year_from": 2010,
            "year_to": 2019,
            "priority": 95,
        },

        {
            "period_class": "RECENT_HISTORICAL_PERIOD",
            "year_from": 2020,
            "year_to": 2025,
            "priority": 90,
        },

        {
            "period_class": "CURRENT_PERIOD",
            "year_from": 2026,
            "year_to": 2026,
            "priority": 20,
        },
    ]


# ============================================================
# SEARCH TARGET MATRIX
# ============================================================

def build_recovery_query_matrix(
) -> List[Dict[str, Any]]:

    periods = (
        build_period_strategy()
    )

    matrix: List[
        Dict[str, Any]
    ] = []

    query_index = 0

    for definition in QUERY_DEFINITIONS:

        for period in periods:

            query_index += 1

            matrix.append(
                {
                    "query_index": query_index,

                    "classification": (
                        definition[
                            "classification"
                        ]
                    ),

                    "query": (
                        definition[
                            "query"
                        ]
                    ),

                    "query_priority": (
                        definition[
                            "priority"
                        ]
                    ),

                    "period_class": (
                        period[
                            "period_class"
                        ]
                    ),

                    "year_from": (
                        period[
                            "year_from"
                        ]
                    ),

                    "year_to": (
                        period[
                            "year_to"
                        ]
                    ),

                    "period_priority": (
                        period[
                            "priority"
                        ]
                    ),

                    "combined_priority": (
                        definition[
                            "priority"
                        ]
                        + period[
                            "priority"
                        ]
                    ),

                    "target_exact_phrase_required_for_direct_seed": (
                        True
                    ),

                    "search_result_final_positive": (
                        False
                    ),

                    "runtime_registration_allowed": (
                        False
                    ),

                    "site_positive_allowed": (
                        False
                    ),
                }
            )

    matrix.sort(
        key=lambda item: (
            -int(
                item[
                    "combined_priority"
                ]
            ),
            int(
                item[
                    "year_from"
                ]
            ),
            int(
                item[
                    "query_index"
                ]
            ),
        )
    )

    return matrix


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
        "HISTORICAL OFFICIAL NOTICE RECOVERY EXPANSION"
    )

    print(
        "=" * 60
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

    print()

    m_stage_data = load_json(
        M_STAGE_INPUT
    )

    j_stage_data = load_json(
        J_STAGE_INPUT
    )

    y_stage_data = load_json(
        Y_STAGE_INPUT
    )

    negative_document_urls = (
        collect_negative_document_urls(
            m_stage_data
        )
    )

    prior_false_positive_urls = (
        collect_prior_false_positive_urls(
            m_stage_data,
            j_stage_data,
            y_stage_data,
        )
    )

    exclusion_urls = (
        negative_document_urls
        | prior_false_positive_urls
    )

    query_matrix = (
        build_recovery_query_matrix()
    )

    classification_counts = Counter(
        item[
            "classification"
        ]
        for item in query_matrix
    )

    period_counts = Counter(
        item[
            "period_class"
        ]
        for item in query_matrix
    )

    # ========================================================
    # RESOLUTION
    # ========================================================

    resolution = (
        "HISTORICAL_OFFICIAL_NOTICE_RECOVERY_EXPANSION_READY"
    )

    next_action = (
        "historical recovery query matrix를 이용해 공식 지자체 고시/"
        "공보 archive와 과거 행정자료에서 exact target phrase를 탐색한다. "
        "검색/list page는 positive로 승격하지 않고, detail/attachment/"
        "archive issue identity만 다음 단계 seed로 수집한다."
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-N "
            "Development Density Management Area "
            "Historical Official Notice Recovery Expansion"
        ),

        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },

        "inputs": {
            "m_stage": str(
                M_STAGE_INPUT
            ),

            "j_stage": str(
                J_STAGE_INPUT
            ),

            "y_stage": str(
                Y_STAGE_INPUT
            ),

            "m_stage_resolution": (
                m_stage_data.get(
                    "resolution"
                )
            ),
        },

        "method": {
            "historical_recovery_expansion": True,

            "negative_document_exclusion_memory": True,

            "prior_false_positive_exclusion_memory": True,

            "exact_target_query_enabled": True,

            "action_query_enabled": True,

            "notice_query_enabled": True,

            "urban_planning_query_enabled": True,

            "archive_query_enabled": True,

            "period_partition_enabled": True,

            "search_page_final_positive_allowed": False,

            "detail_seed_final_positive_allowed": False,

            "attachment_seed_final_positive_allowed": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,

            "final_positive_promotion_allowed": False,
        },

        "summary": {
            "negative_document_url_count": len(
                negative_document_urls
            ),

            "prior_false_positive_url_count": len(
                prior_false_positive_urls
            ),

            "total_exclusion_url_count": len(
                exclusion_urls
            ),

            "query_definition_count": len(
                QUERY_DEFINITIONS
            ),

            "query_matrix_count": len(
                query_matrix
            ),
        },

        "query_classification_counts": dict(
            sorted(
                classification_counts.items()
            )
        ),

        "period_counts": dict(
            sorted(
                period_counts.items()
            )
        ),

        "negative_document_urls": sorted(
            negative_document_urls
        ),

        "prior_false_positive_urls": sorted(
            prior_false_positive_urls
        ),

        "exclusion_urls": sorted(
            exclusion_urls
        ),

        "period_strategy": (
            build_period_strategy()
        ),

        "historical_recovery_query_matrix": (
            query_matrix
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

    print(
        "Negative M-stage document URLs:",
        len(
            negative_document_urls
        ),
    )

    print(
        "Prior false-positive URLs:",
        len(
            prior_false_positive_urls
        ),
    )

    print(
        "Total exclusion URLs:",
        len(
            exclusion_urls
        ),
    )

    print(
        "Historical query matrix:",
        len(
            query_matrix
        ),
    )

    print()

    print(
        "Period strategy"
    )

    print(
        "-" * 60
    )

    for item in build_period_strategy():

        print(
            item[
                "period_class"
            ],
            ":",
            item[
                "year_from"
            ],
            "-",
            item[
                "year_to"
            ],
        )

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

    query_ids = {
        item[
            "query_index"
        ]
        for item in query_matrix
    }

    query_keys = {
        (
            item[
                "classification"
            ],
            item[
                "query"
            ],
            item[
                "year_from"
            ],
            item[
                "year_to"
            ],
        )
        for item in query_matrix
    }

    current_negative_preserved = all(
        url in exclusion_urls
        for url in negative_document_urls
    )

    query_classes_valid = all(
        item[
            "classification"
        ]
        in VALID_QUERY_CLASSES
        for item in query_matrix
    )

    no_positive_promotion = all(
        item.get(
            "search_result_final_positive"
        )
        is False
        for item in query_matrix
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

        "M-stage input exists": (
            M_STAGE_INPUT.exists()
        ),

        "J-stage input exists": (
            J_STAGE_INPUT.exists()
        ),

        "Y-stage input exists": (
            Y_STAGE_INPUT.exists()
        ),

        "M-stage input parsed": (
            isinstance(
                m_stage_data,
                dict,
            )
        ),

        "M-stage no-target resolution preserved": (
            normalize_space(
                m_stage_data.get(
                    "resolution"
                )
            )
            == M_STAGE_EXPECTED_RESOLUTION
        ),

        "M-stage negative documents loaded": (
            len(
                negative_document_urls
            )
            > 0
        ),

        "negative document exclusion memory enabled": (
            output_data[
                "method"
            ][
                "negative_document_exclusion_memory"
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

        "current negative documents preserved": (
            current_negative_preserved
        ),

        "historical recovery query matrix generated": (
            len(
                query_matrix
            )
            > 0
        ),

        "query indexes unique": (
            len(
                query_ids
            )
            == len(
                query_matrix
            )
        ),

        "query matrix unique": (
            len(
                query_keys
            )
            == len(
                query_matrix
            )
        ),

        "all query classes valid": (
            query_classes_valid
        ),

        "exact target query enabled": (
            output_data[
                "method"
            ][
                "exact_target_query_enabled"
            ]
            is True
        ),

        "action query enabled": (
            output_data[
                "method"
            ][
                "action_query_enabled"
            ]
            is True
        ),

        "notice query enabled": (
            output_data[
                "method"
            ][
                "notice_query_enabled"
            ]
            is True
        ),

        "urban-planning query enabled": (
            output_data[
                "method"
            ][
                "urban_planning_query_enabled"
            ]
            is True
        ),

        "archive query enabled": (
            output_data[
                "method"
            ][
                "archive_query_enabled"
            ]
            is True
        ),

        "period partition enabled": (
            output_data[
                "method"
            ][
                "period_partition_enabled"
            ]
            is True
        ),

        "search page final positive prohibited": (
            no_positive_promotion
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
            "historical official notice recovery expansion "
            "regression failed"
        )


if __name__ == "__main__":
    main()