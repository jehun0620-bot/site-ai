# -*- coding: utf-8 -*-

"""
STEP 17-21-C-15-3
District Unit Plan Dual-SITE Runtime Regression

목표
======================================================================
대표 SITE와 실제 두 번째 SITE에 대해 동일한 runtime spatial
condition evaluator를 실행한다.

BASE
----------------------------------------------------------------------
서울특별시 강남구 개포동 12번지
PNU: 1168010300100120000

Primary Parcel:
MapPlan snapshot

Primary Parcel CRS:
미확정

따라서 지구단위계획 평가 시:
VWorld LP_PA_CBND_BUBUN compatible geometry fallback 사용

LIVE
----------------------------------------------------------------------
서울특별시 강남구 개포동 13번지
PNU: 1168010300100130000

Primary Parcel:
VWorld LP_PA_CBND_BUBUN

Primary Parcel CRS:
EPSG:4326

따라서 지구단위계획 평가 시:
PRIMARY_PARCEL 직접 사용

핵심 검증
======================================================================
1. 두 SITE의 PNU가 다르다.
2. 두 SITE의 primary parcel source가 다르다.
3. BASE는 LIVE_COMPATIBLE_FALLBACK을 사용한다.
4. LIVE는 PRIMARY_PARCEL을 사용한다.
5. 두 SITE 모두 동일 LT_C_UPISUQ161 dataset으로 평가한다.
6. condition 결과는 각각 독립적으로 계산된다.
7. 대표 SITE의 기존 C-9 TRUE 값을 LIVE SITE에 그대로 복사하지 않는다.
"""

from __future__ import annotations

from typing import Any, Dict

from law_data.site_analysis_builder import (
    build_site_analysis,
)

from law_data.spatial_condition_evaluator import (
    resolve_site_spatial_condition,
)


# ============================================================
# SITE
# ============================================================

BASE_SITE_INPUT: Dict[str, Any] = {

    "site_id":
        "11680-10300-0012-0000",

    "address":
        "서울특별시 강남구 개포동 12번지",

    "road_address":
        "서울특별시 강남구 개포로109길 21 (개포동)",

    "sigungu_cd":
        "11680",

    "bjdong_cd":
        "10300",

    "bun":
        "0012",

    "ji":
        "0000",

    "sigungu_code":
        "11680",

    "bjdong_code":
        "10300",

    "main_no":
        "0012",

    "sub_no":
        "0000",

    "pnu":
        "1168010300100120000",

    "zone":
        "제3종일반주거지역",

    "land_use_zone":
        "제3종일반주거지역",

    "land_area":
        121040.4,

    "land_category":
        "대",
}


LIVE_SITE_INPUT: Dict[str, Any] = {

    "site_id":
        "11680-10300-0013-0000",

    "address":
        "서울특별시 강남구 개포동 13번지",

    "road_address":
        "서울특별시 강남구 개포로109길 74 (개포동)",

    "sigungu_cd":
        "11680",

    "bjdong_cd":
        "10300",

    "bun":
        "0013",

    "ji":
        "0000",

    "sigungu_code":
        "11680",

    "bjdong_code":
        "10300",

    "main_no":
        "0013",

    "sub_no":
        "0000",

    "pnu":
        "1168010300100130000",

    "zone":
        "제1종일반주거지역",

    "land_use_zone":
        "제1종일반주거지역",

    "land_area":
        13000.5,

    "land_category":
        "학교용지",
}


# ============================================================
# common profile
# ============================================================

PROJECT_PROFILE = {
    "공동주택":
        "TRUE",
}

PROCEDURE_PROFILE = {
    "도시계획위원회심의":
        "TRUE",
}


# ============================================================
# analysis
# ============================================================

base_analysis = (
    build_site_analysis(
        site_input=(
            BASE_SITE_INPUT
        ),

        project_profile=(
            PROJECT_PROFILE
        ),

        procedure_profile=(
            PROCEDURE_PROFILE
        ),
    )
)


live_analysis = (
    build_site_analysis(
        site_input=(
            LIVE_SITE_INPUT
        ),

        project_profile=(
            PROJECT_PROFILE
        ),

        procedure_profile=(
            PROCEDURE_PROFILE
        ),
    )
)


base_site = (
    base_analysis.get(
        "site",
        {}
    )
)

live_site = (
    live_analysis.get(
        "site",
        {}
    )
)


base_parcel = (
    base_site
    .get(
        "spatial",
        {}
    )
    .get(
        "parcel",
        {}
    )
)

live_parcel = (
    live_site
    .get(
        "spatial",
        {}
    )
    .get(
        "parcel",
        {}
    )
)


# ============================================================
# runtime conditions
# ============================================================

base_condition = (
    resolve_site_spatial_condition(
        condition_name=(
            "지구단위계획"
        ),

        site=(
            base_site
        ),

        parcel=(
            base_parcel
        ),
    )
)


live_condition = (
    resolve_site_spatial_condition(
        condition_name=(
            "지구단위계획"
        ),

        site=(
            live_site
        ),

        parcel=(
            live_parcel
        ),
    )
)


# ============================================================
# helpers
# ============================================================

def get_evaluation_parcel(
    condition: Dict[str, Any],
) -> Dict[str, Any]:

    evidence = (
        condition.get(
            "evidence",
            {}
        )
    )

    direct = (
        evidence.get(
            "evaluation_parcel"
        )
    )

    if isinstance(
        direct,
        dict,
    ):

        return direct

    coordinate = (
        evidence.get(
            "coordinate",
            {}
        )
    )

    nested = (
        coordinate.get(
            "evaluation_parcel"
        )
        if isinstance(
            coordinate,
            dict,
        )
        else None
    )

    if isinstance(
        nested,
        dict,
    ):

        return nested

    return {}


def get_query(
    condition: Dict[str, Any],
) -> Dict[str, Any]:

    evidence = (
        condition.get(
            "evidence",
            {}
        )
    )

    query = (
        evidence.get(
            "query",
            {}
        )
    )

    if isinstance(
        query,
        dict,
    ):

        return query

    return {}


def get_intersections(
    condition: Dict[str, Any],
):

    evidence = (
        condition.get(
            "evidence",
            {}
        )
    )

    value = (
        evidence.get(
            "intersections",
            []
        )
    )

    if isinstance(
        value,
        list,
    ):

        return value

    return []


base_eval_parcel = (
    get_evaluation_parcel(
        base_condition
    )
)

live_eval_parcel = (
    get_evaluation_parcel(
        live_condition
    )
)

base_query = (
    get_query(
        base_condition
    )
)

live_query = (
    get_query(
        live_condition
    )
)

base_intersections = (
    get_intersections(
        base_condition
    )
)

live_intersections = (
    get_intersections(
        live_condition
    )
)


# ============================================================
# console
# ============================================================

print(
    "=== BASE SITE ==="
)

print(
    "SITE ID:",
    base_site.get(
        "site_id"
    ),
)

print(
    "PNU:",
    base_site.get(
        "pnu"
    ),
)

print(
    "Zone:",
    base_site.get(
        "zone"
    ),
)

print(
    "Coordinate:",
    base_site.get(
        "coordinate"
    ),
)

print(
    "Primary provider:",
    base_parcel.get(
        "source",
        {}
    ).get(
        "provider"
    ),
)

print(
    "Primary geometry:",
    base_parcel.get(
        "geometry_type"
    ),
)

print(
    "Primary CRS:",
    base_parcel.get(
        "crs"
    ),
)

print(
    "Evaluation parcel:",
    base_eval_parcel,
)

print(
    "Condition:",
    {
        "state":
            base_condition.get(
                "state"
            ),

        "confidence":
            base_condition.get(
                "confidence"
            ),

        "resolution":
            base_condition.get(
                "resolution"
            ),
    },
)

print(
    "Query:",
    base_query,
)

print(
    "Intersections:",
    base_intersections,
)


print()

print(
    "=== LIVE SITE ==="
)

print(
    "SITE ID:",
    live_site.get(
        "site_id"
    ),
)

print(
    "PNU:",
    live_site.get(
        "pnu"
    ),
)

print(
    "Zone:",
    live_site.get(
        "zone"
    ),
)

print(
    "Coordinate:",
    live_site.get(
        "coordinate"
    ),
)

print(
    "Primary provider:",
    live_parcel.get(
        "source",
        {}
    ).get(
        "provider"
    ),
)

print(
    "Primary geometry:",
    live_parcel.get(
        "geometry_type"
    ),
)

print(
    "Primary CRS:",
    live_parcel.get(
        "crs"
    ),
)

print(
    "Evaluation parcel:",
    live_eval_parcel,
)

print(
    "Condition:",
    {
        "state":
            live_condition.get(
                "state"
            ),

        "confidence":
            live_condition.get(
                "confidence"
            ),

        "resolution":
            live_condition.get(
                "resolution"
            ),
    },
)

print(
    "Query:",
    live_query,
)

print(
    "Intersections:",
    live_intersections,
)


# ============================================================
# validations
# ============================================================

base_evaluation = (
    base_condition.get(
        "evaluation",
        {}
    )
)

live_evaluation = (
    live_condition.get(
        "evaluation",
        {}
    )
)


validations = {

    # --------------------------------------------------------
    # identity isolation
    # --------------------------------------------------------

    "different SITE ID": (
        base_site.get(
            "site_id"
        )
        != live_site.get(
            "site_id"
        )
    ),

    "different PNU": (
        base_site.get(
            "pnu"
        )
        != live_site.get(
            "pnu"
        )
    ),

    # --------------------------------------------------------
    # primary parcel sources
    # --------------------------------------------------------

    "BASE primary MapPlan": (
        base_parcel.get(
            "source",
            {}
        ).get(
            "provider"
        )
        == "MapPlan"
    ),

    "BASE primary loaded": (
        base_parcel.get(
            "geometry_loaded"
        )
        is True
    ),

    "BASE primary CRS unresolved": (
        not bool(
            base_parcel.get(
                "crs"
            )
        )
    ),

    "LIVE primary VWorld": (
        live_parcel.get(
            "source",
            {}
        ).get(
            "provider"
        )
        == "VWorld"
    ),

    "LIVE primary loaded": (
        live_parcel.get(
            "geometry_loaded"
        )
        is True
    ),

    "LIVE primary CRS 4326": (
        live_parcel.get(
            "crs"
        )
        == "EPSG:4326"
    ),

    # --------------------------------------------------------
    # evaluation parcel strategy
    # --------------------------------------------------------

    "BASE compatible fallback": (
        base_eval_parcel.get(
            "fallback_used"
        )
        is True
    ),

    "BASE fallback mode": (
        base_eval_parcel.get(
            "source",
            {}
        ).get(
            "mode"
        )
        == "LIVE_COMPATIBLE_FALLBACK"
    ),

    "BASE evaluation CRS": (
        base_eval_parcel.get(
            "crs"
        )
        == "EPSG:4326"
    ),

    "LIVE primary evaluation": (
        live_eval_parcel.get(
            "fallback_used"
        )
        is False
    ),

    "LIVE evaluation mode": (
        live_eval_parcel.get(
            "source",
            {}
        ).get(
            "mode"
        )
        == "PRIMARY_PARCEL"
    ),

    "LIVE evaluation CRS": (
        live_eval_parcel.get(
            "crs"
        )
        == "EPSG:4326"
    ),

    # --------------------------------------------------------
    # dataset/query
    # --------------------------------------------------------

    "BASE dataset": (
        base_condition.get(
            "source",
            {}
        ).get(
            "dataset"
        )
        == "LT_C_UPISUQ161"
    ),

    "LIVE dataset": (
        live_condition.get(
            "source",
            {}
        ).get(
            "dataset"
        )
        == "LT_C_UPISUQ161"
    ),

    "BASE query success": (
        base_evaluation.get(
            "query_success"
        )
        is True
    ),

    "LIVE query success": (
        live_evaluation.get(
            "query_success"
        )
        is True
    ),

    # --------------------------------------------------------
    # condition resolved
    # --------------------------------------------------------

    "BASE state resolved": (
        base_condition.get(
            "state"
        )
        in {
            "TRUE",
            "FALSE",
        }
    ),

    "LIVE state resolved": (
        live_condition.get(
            "state"
        )
        in {
            "TRUE",
            "FALSE",
        }
    ),

    "BASE geometry verified": (
        base_condition.get(
            "geometry_verified"
        )
        is True
    ),

    "LIVE geometry verified": (
        live_condition.get(
            "geometry_verified"
        )
        is True
    ),

    # --------------------------------------------------------
    # current known LIVE result
    # --------------------------------------------------------

    "LIVE district unit plan TRUE": (
        live_condition.get(
            "state"
        )
        == "TRUE"
    ),

    "LIVE intersection exists": (
        live_evaluation.get(
            "intersection_count",
            0,
        )
        > 0
    ),

    "LIVE district name": (
        any(
            item.get(
                "district_name"
            )
            == "대치택지개발지구"

            for item
            in live_intersections
        )
    ),
}


# ============================================================
# output
# ============================================================

print()

print(
    "=== VALIDATION ==="
)


for name, passed in (
    validations.items()
):

    print(
        f"{name}:",
        passed,
    )


all_pass = all(
    validations.values()
)


print()

print(
    "BASE state:",
    base_condition.get(
        "state"
    ),
)

print(
    "LIVE state:",
    live_condition.get(
        "state"
    ),
)

print(
    "BASE evaluation mode:",
    base_eval_parcel.get(
        "source",
        {}
    ).get(
        "mode"
    ),
)

print(
    "LIVE evaluation mode:",
    live_eval_parcel.get(
        "source",
        {}
    ).get(
        "mode"
    ),
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

    for name, passed in (
        validations.items()
    ):

        if not passed:

            print(
                "-",
                name,
            )


raise SystemExit(
    0
    if all_pass
    else 1
)