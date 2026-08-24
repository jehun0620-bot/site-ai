# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16
Runtime Spatial Condition Generalization Regression

목표
======================================================================
build_site_analysis()가 개별 condition을 하드코딩하지 않고
spatial evaluator registry의 지원 condition 전체를 자동 실행하는지
검증한다.

현재 runtime conditions
======================================================================
- 지구단위계획
- 개발진흥지구
- 취락지구
- 방재지구

C-16-7 반영
======================================================================
방재지구 runtime evaluation이 Rule Engine까지 연결되면서
clause 189의 실제 상위 branch:

    SITE    방재지구
    PROJECT 재해예방시설

가 복원되었다.

BASE / LIVE SITE 모두 runtime 방재지구 FALSE이므로
기존 APPLICABLE이던 clause 189가 NOT_APPLICABLE로 이동한다.

따라서 정상 rule summary는:

BASE
    62 / 214 / 36 / 2

LIVE
    62 / 216 / 34 / 2

이다.

중요
======================================================================
이 변화는 regression 오류가 아니다.

대표 SITE static 방재지구 판단 대신 현재 SITE runtime evidence를
Rule Engine이 사용하게 된 결과다.
"""

from __future__ import annotations

from typing import Any, Dict

from law_data.site_analysis_builder import (
    build_site_analysis,
)

from law_data.spatial_condition_evaluator import (
    get_supported_spatial_conditions,
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


PROJECT_PROFILE = {

    "공동주택":
        "TRUE",
}


PROCEDURE_PROFILE = {

    "도시계획위원회심의":
        "TRUE",
}


# ============================================================
# EXPECTED
# ============================================================

EXPECTED_SUPPORTED_CONDITIONS = {

    "지구단위계획",
    "개발진흥지구",
    "취락지구",
    "방재지구",
}


EXPECTED_BASE_RULE_SUMMARY = {

    "total":
        314,

    "applicable":
        62,

    "not_applicable":
        214,

    "conditional":
        36,

    "unknown":
        2,
}


EXPECTED_LIVE_RULE_SUMMARY = {

    "total":
        314,

    "applicable":
        62,

    "not_applicable":
        216,

    "conditional":
        34,

    "unknown":
        2,
}


# ============================================================
# ANALYSIS
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
        {},
    )
)

live_site = (
    live_analysis.get(
        "site",
        {},
    )
)


base_runtime = (
    base_site.get(
        "runtime_conditions",
        {},
    )
)

live_runtime = (
    live_site.get(
        "runtime_conditions",
        {},
    )
)


supported = (
    get_supported_spatial_conditions()
)


# ============================================================
# CONSOLE
# ============================================================

print(
    "Supported runtime conditions:",
    supported,
)

print()


print(
    "BASE runtime conditions:"
)

for name, result in (
    base_runtime.items()
):

    print(
        name,
        "=>",
        result.get(
            "state"
        ),
        "/",
        result.get(
            "confidence"
        ),
        "/",
        result.get(
            "resolution"
        ),
    )


print()

print(
    "LIVE runtime conditions:"
)

for name, result in (
    live_runtime.items()
):

    print(
        name,
        "=>",
        result.get(
            "state"
        ),
        "/",
        result.get(
            "confidence"
        ),
        "/",
        result.get(
            "resolution"
        ),
    )


# ============================================================
# HELPERS
# ============================================================

def get_rule_summary(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:

    value = analysis.get(
        "rule_evaluation",
        {},
    )

    if isinstance(
        value,
        dict,
    ):

        return value

    return {}


def get_runtime_condition(
    runtime: Dict[str, Any],
    name: str,
) -> Dict[str, Any]:

    value = runtime.get(
        name,
        {},
    )

    if isinstance(
        value,
        dict,
    ):

        return value

    return {}


# ============================================================
# CONDITION EXTRACT
# ============================================================

base_district_unit_plan = (
    get_runtime_condition(
        base_runtime,
        "지구단위계획",
    )
)

live_district_unit_plan = (
    get_runtime_condition(
        live_runtime,
        "지구단위계획",
    )
)


base_development_promotion = (
    get_runtime_condition(
        base_runtime,
        "개발진흥지구",
    )
)

live_development_promotion = (
    get_runtime_condition(
        live_runtime,
        "개발진흥지구",
    )
)


base_settlement = (
    get_runtime_condition(
        base_runtime,
        "취락지구",
    )
)

live_settlement = (
    get_runtime_condition(
        live_runtime,
        "취락지구",
    )
)


base_disaster = (
    get_runtime_condition(
        base_runtime,
        "방재지구",
    )
)

live_disaster = (
    get_runtime_condition(
        live_runtime,
        "방재지구",
    )
)


# ============================================================
# RULE SUMMARY
# ============================================================

base_rule_summary = (
    get_rule_summary(
        base_analysis
    )
)

live_rule_summary = (
    get_rule_summary(
        live_analysis
    )
)


# ============================================================
# VALIDATION
# ============================================================

validations = {

    # --------------------------------------------------------
    # registry
    # --------------------------------------------------------

    "supported district unit plan": (
        "지구단위계획"
        in supported
    ),

    "supported development promotion": (
        "개발진흥지구"
        in supported
    ),

    "supported settlement district": (
        "취락지구"
        in supported
    ),

    "supported disaster prevention district": (
        "방재지구"
        in supported
    ),

    "supported count >= 4": (
        len(
            supported
        )
        >= 4
    ),

    "supported expected conditions": (
        EXPECTED_SUPPORTED_CONDITIONS.issubset(
            set(
                supported
            )
        )
    ),

    # --------------------------------------------------------
    # builder automatic collection
    # --------------------------------------------------------

    "BASE runtime keys match supported": (
        set(
            base_runtime.keys()
        )
        == set(
            supported
        )
    ),

    "LIVE runtime keys match supported": (
        set(
            live_runtime.keys()
        )
        == set(
            supported
        )
    ),

    # --------------------------------------------------------
    # district unit plan
    # --------------------------------------------------------

    "BASE district unit plan TRUE": (
        base_district_unit_plan.get(
            "state"
        )
        == "TRUE"
    ),

    "LIVE district unit plan TRUE": (
        live_district_unit_plan.get(
            "state"
        )
        == "TRUE"
    ),

    "BASE district confidence HIGH": (
        base_district_unit_plan.get(
            "confidence"
        )
        == "HIGH"
    ),

    "LIVE district confidence HIGH": (
        live_district_unit_plan.get(
            "confidence"
        )
        == "HIGH"
    ),

    "BASE district dataset": (
        base_district_unit_plan.get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == "LT_C_UPISUQ161"
    ),

    "LIVE district dataset": (
        live_district_unit_plan.get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == "LT_C_UPISUQ161"
    ),

    # --------------------------------------------------------
    # development promotion district
    # --------------------------------------------------------

    "BASE development promotion FALSE": (
        base_development_promotion.get(
            "state"
        )
        == "FALSE"
    ),

    "LIVE development promotion FALSE": (
        live_development_promotion.get(
            "state"
        )
        == "FALSE"
    ),

    "BASE development confidence HIGH": (
        base_development_promotion.get(
            "confidence"
        )
        == "HIGH"
    ),

    "LIVE development confidence HIGH": (
        live_development_promotion.get(
            "confidence"
        )
        == "HIGH"
    ),

    "BASE development dataset": (
        base_development_promotion.get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == "LT_C_UQ129"
    ),

    "LIVE development dataset": (
        live_development_promotion.get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == "LT_C_UQ129"
    ),

    # --------------------------------------------------------
    # settlement district
    # --------------------------------------------------------

    "BASE settlement FALSE": (
        base_settlement.get(
            "state"
        )
        == "FALSE"
    ),

    "LIVE settlement FALSE": (
        live_settlement.get(
            "state"
        )
        == "FALSE"
    ),

    "BASE settlement confidence HIGH": (
        base_settlement.get(
            "confidence"
        )
        == "HIGH"
    ),

    "LIVE settlement confidence HIGH": (
        live_settlement.get(
            "confidence"
        )
        == "HIGH"
    ),

    "BASE settlement dataset": (
        base_settlement.get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == "LT_C_UQ128"
    ),

    "LIVE settlement dataset": (
        live_settlement.get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == "LT_C_UQ128"
    ),

    # --------------------------------------------------------
    # disaster prevention district
    # --------------------------------------------------------

    "BASE disaster prevention FALSE": (
        base_disaster.get(
            "state"
        )
        == "FALSE"
    ),

    "LIVE disaster prevention FALSE": (
        live_disaster.get(
            "state"
        )
        == "FALSE"
    ),

    "BASE disaster confidence HIGH": (
        base_disaster.get(
            "confidence"
        )
        == "HIGH"
    ),

    "LIVE disaster confidence HIGH": (
        live_disaster.get(
            "confidence"
        )
        == "HIGH"
    ),

    "BASE disaster dataset": (
        base_disaster.get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == "LT_C_UQ125"
    ),

    "LIVE disaster dataset": (
        live_disaster.get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == "LT_C_UQ125"
    ),

    "BASE disaster query success": (
        base_disaster.get(
            "evaluation",
            {},
        ).get(
            "query_success"
        )
        is True
    ),

    "LIVE disaster query success": (
        live_disaster.get(
            "evaluation",
            {},
        ).get(
            "query_success"
        )
        is True
    ),

    "BASE disaster no intersection": (
        base_disaster.get(
            "evaluation",
            {},
        ).get(
            "intersects"
        )
        is False
    ),

    "LIVE disaster no intersection": (
        live_disaster.get(
            "evaluation",
            {},
        ).get(
            "intersects"
        )
        is False
    ),

    # --------------------------------------------------------
    # analysis status
    # --------------------------------------------------------

    "BASE analysis READY": (
        base_analysis.get(
            "analysis",
            {},
        ).get(
            "status"
        )
        == "READY"
    ),

    "LIVE analysis READY": (
        live_analysis.get(
            "analysis",
            {},
        ).get(
            "status"
        )
        == "READY"
    ),

    # --------------------------------------------------------
    # numeric non-regression
    # --------------------------------------------------------

    "BASE BCR": (
        base_analysis.get(
            "regulation",
            {},
        ).get(
            "building_coverage_ratio",
            {},
        ).get(
            "value"
        )
        == 50.0
    ),

    "BASE FAR": (
        base_analysis.get(
            "regulation",
            {},
        ).get(
            "floor_area_ratio",
            {},
        ).get(
            "value"
        )
        == 250.0
    ),

    "LIVE BCR": (
        live_analysis.get(
            "regulation",
            {},
        ).get(
            "building_coverage_ratio",
            {},
        ).get(
            "value"
        )
        == 60.0
    ),

    "LIVE FAR": (
        live_analysis.get(
            "regulation",
            {},
        ).get(
            "floor_area_ratio",
            {},
        ).get(
            "value"
        )
        == 150.0
    ),

    # --------------------------------------------------------
    # rule summary
    # --------------------------------------------------------

    "BASE rules total 314": (
        base_rule_summary.get(
            "total"
        )
        == EXPECTED_BASE_RULE_SUMMARY[
            "total"
        ]
    ),

    "BASE rule summary expected": (
        (
            base_rule_summary.get(
                "applicable"
            ),
            base_rule_summary.get(
                "not_applicable"
            ),
            base_rule_summary.get(
                "conditional"
            ),
            base_rule_summary.get(
                "unknown"
            ),
        )
        == (
            EXPECTED_BASE_RULE_SUMMARY[
                "applicable"
            ],
            EXPECTED_BASE_RULE_SUMMARY[
                "not_applicable"
            ],
            EXPECTED_BASE_RULE_SUMMARY[
                "conditional"
            ],
            EXPECTED_BASE_RULE_SUMMARY[
                "unknown"
            ],
        )
    ),

    "LIVE rules total 314": (
        live_rule_summary.get(
            "total"
        )
        == EXPECTED_LIVE_RULE_SUMMARY[
            "total"
        ]
    ),

    "LIVE rule summary expected": (
        (
            live_rule_summary.get(
                "applicable"
            ),
            live_rule_summary.get(
                "not_applicable"
            ),
            live_rule_summary.get(
                "conditional"
            ),
            live_rule_summary.get(
                "unknown"
            ),
        )
        == (
            EXPECTED_LIVE_RULE_SUMMARY[
                "applicable"
            ],
            EXPECTED_LIVE_RULE_SUMMARY[
                "not_applicable"
            ],
            EXPECTED_LIVE_RULE_SUMMARY[
                "conditional"
            ],
            EXPECTED_LIVE_RULE_SUMMARY[
                "unknown"
            ],
        )
    ),
}


# ============================================================
# OUTPUT
# ============================================================

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
    "BASE rule summary:",
    base_rule_summary,
)

print(
    "LIVE rule summary:",
    live_rule_summary,
)

print()

print(
    "Expected BASE rule summary:",
    EXPECTED_BASE_RULE_SUMMARY,
)

print(
    "Expected LIVE rule summary:",
    EXPECTED_LIVE_RULE_SUMMARY,
)

print()

print(
    "all_pass:",
    all_pass,
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
            "-",
            name,
        )

    raise AssertionError(
        "Runtime spatial condition generalization regression failed"
    )