# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-5
Runtime Spatial Condition Generalization Regression

목표
======================================================================
build_site_analysis()가 개별 condition을 하드코딩하지 않고
spatial evaluator registry의 지원 condition 전체를 자동 실행하는지
검증한다.

현재 runtime conditions:
- 지구단위계획
- 개발진흥지구
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


# ============================================================
# VALIDATION
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

    "supported count >= 2": (
        len(
            supported
        )
        >= 2
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
        base_runtime.get(
            "지구단위계획",
            {},
        ).get(
            "state"
        )
        == "TRUE"
    ),

    "LIVE district unit plan TRUE": (
        live_runtime.get(
            "지구단위계획",
            {},
        ).get(
            "state"
        )
        == "TRUE"
    ),

    # --------------------------------------------------------
    # development promotion district
    # --------------------------------------------------------

    "BASE development promotion FALSE": (
        base_runtime.get(
            "개발진흥지구",
            {},
        ).get(
            "state"
        )
        == "FALSE"
    ),

    "LIVE development promotion FALSE": (
        live_runtime.get(
            "개발진흥지구",
            {},
        ).get(
            "state"
        )
        == "FALSE"
    ),

    "BASE development confidence HIGH": (
        base_runtime.get(
            "개발진흥지구",
            {},
        ).get(
            "confidence"
        )
        == "HIGH"
    ),

    "LIVE development confidence HIGH": (
        live_runtime.get(
            "개발진흥지구",
            {},
        ).get(
            "confidence"
        )
        == "HIGH"
    ),

    "BASE development dataset": (
        base_runtime.get(
            "개발진흥지구",
            {},
        ).get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == "LT_C_UQ129"
    ),

    "LIVE development dataset": (
        live_runtime.get(
            "개발진흥지구",
            {},
        ).get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == "LT_C_UQ129"
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
    # rule summary non-regression
    # --------------------------------------------------------

    "BASE rules total 314": (
        base_rule_summary.get(
            "total"
        )
        == 314
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
            63,
            213,
            36,
            2,
        )
    ),

    "LIVE rules total 314": (
        live_rule_summary.get(
            "total"
        )
        == 314
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
            63,
            215,
            34,
            2,
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
    "all_pass:",
    all_pass,
)


if not all_pass:

    raise AssertionError(
        "Runtime spatial condition generalization regression failed"
    )