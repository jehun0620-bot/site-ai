# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-7-E
Disaster Prevention District Runtime 3-SITE Regression

목표
======================================================================
방재지구 runtime evaluator가 실제 SITE Parcel Polygon 기준으로
TRUE / FALSE를 정확하게 판정하는지 검증한다.

검증 SITE
======================================================================

1. BASE
   서울특별시 강남구 개포동 12번지
   PNU: 1168010300100120000
   expected: 방재지구 FALSE

2. LIVE
   서울특별시 강남구 개포동 13번지
   PNU: 1168010300100130000
   expected: 방재지구 FALSE

3. POSITIVE
   전남광주통합특별시 목포시 죽교동 580-6
   PNU: 1211015700105800006
   expected: 방재지구 TRUE

   expected feature:
       LT_C_UQ125.22

   expected district name:
       방재지구

핵심 검증
======================================================================
- SITE별 Parcel Polygon 독립 확보
- VWorld LP_PA_CBND_BUBUN
- Feature PNU 직접 일치
- LT_C_UQ125 runtime query
- BASE / LIVE verified empty FALSE
- POSITIVE Parcel Polygon intersection TRUE

중요
======================================================================
방재지구 spatial TRUE는 SITE 공간조건 판정일 뿐이다.

    방재지구 TRUE
    ≠
    clause 189 numeric FAR 특례 자동 적용

numeric guard는 별도 검증 단계에서 계속 독립적으로 유지한다.
"""

from __future__ import annotations

from typing import Any, Dict, List

from law_data.parcel_geometry_provider import (
    resolve_live_parcel_geometry,
)

from law_data.spatial_condition_evaluator import (
    resolve_site_spatial_condition,
)


# ============================================================
# SITE CONFIG
# ============================================================

SITES = {

    "BASE": {

        "site_id":
            "11680-10300-0012-0000",

        "address":
            "서울특별시 강남구 개포동 12번지",

        "pnu":
            "1168010300100120000",

        "coordinate": {

            "x":
                127.07539280356858,

            "y":
                37.494197498186885,

            "crs":
                "EPSG:4326",
        },

        "expected_state":
            "FALSE",
    },

    "LIVE": {

        "site_id":
            "11680-10300-0013-0000",

        "address":
            "서울특별시 강남구 개포동 13번지",

        "pnu":
            "1168010300100130000",

        "coordinate": {

            "x":
                127.07804416954306,

            "y":
                37.49668484241573,

            "crs":
                "EPSG:4326",
        },

        "expected_state":
            "FALSE",
    },

    "POSITIVE": {

        "site_id":
            "12110-15700-0580-0006",

        "address":
            "전남광주통합특별시 목포시 죽교동 580-6",

        "pnu":
            "1211015700105800006",

        # ----------------------------------------------------
        # C-16-7-C에서 VWorld Search API로 확보한
        # 실제 해당 Parcel의 representative coordinate.
        #
        # 방재지구 feature representative point:
        # 126.37369914302997 / 34.801980483931146
        #
        # 와 구분한다.
        # ----------------------------------------------------

        "coordinate": {

            "x":
                126.37500209660791,

            "y":
                34.80148474343932,

            "crs":
                "EPSG:4326",
        },

        "expected_state":
            "TRUE",
    },
}


# ============================================================
# EXPECTED
# ============================================================

EXPECTED_DATASET = (
    "LT_C_UQ125"
)

EXPECTED_POSITIVE_FEATURE_ID = (
    "LT_C_UQ125.22"
)

EXPECTED_POSITIVE_DISTRICT_NAME = (
    "방재지구"
)


# ============================================================
# HELPERS
# ============================================================

def safe_dict(
    value: Any,
) -> Dict[str, Any]:

    if isinstance(
        value,
        dict,
    ):

        return value

    return {}


def safe_list(
    value: Any,
) -> List[Any]:

    if isinstance(
        value,
        list,
    ):

        return value

    return []


def build_runtime_parcel(
    *,
    pnu: str,
    address: str,
) -> Dict[str, Any]:

    """
    현재 SITE의 PNU를 기준으로 VWorld live Parcel Polygon을 확보한다.

    중요:
    strict_pnu_verified == True인 geometry만 regression에 사용한다.
    """

    live_result = (
        resolve_live_parcel_geometry(
            pnu=pnu,
            address=address,
        )
    )

    source = safe_dict(
        live_result.get(
            "source"
        )
    )

    return {

        "pnu":
            pnu,

        "geometry":
            live_result.get(
                "geometry"
            ),

        "geometry_type":
            live_result.get(
                "geometry_type"
            ),

        "geometry_loaded":
            live_result.get(
                "geometry_loaded"
            ),

        "crs":
            source.get(
                "crs"
            )
            or live_result.get(
                "crs"
            )
            or "EPSG:4326",

        "source": {

            **source,

            "provider":
                source.get(
                    "provider"
                )
                or "VWorld",
        },

        "feature_pnu":
            live_result.get(
                "feature_pnu"
            ),

        "strict_pnu_verified":
            live_result.get(
                "strict_pnu_verified"
            ),

        "resolution":
            live_result.get(
                "resolution"
            ),

        "query":
            live_result.get(
                "query"
            ),
    }


def get_intersections(
    condition: Dict[str, Any],
) -> List[Dict[str, Any]]:

    evidence = safe_dict(
        condition.get(
            "evidence"
        )
    )

    value = (
        evidence.get(
            "intersections"
        )
    )

    if not isinstance(
        value,
        list,
    ):

        return []

    return [
        item
        for item
        in value
        if isinstance(
            item,
            dict,
        )
    ]


# ============================================================
# RUN
# ============================================================

results: Dict[
    str,
    Dict[str, Any],
] = {}


for name, site_config in (
    SITES.items()
):

    site = {

        "site_id":
            site_config[
                "site_id"
            ],

        "address":
            site_config[
                "address"
            ],

        "pnu":
            site_config[
                "pnu"
            ],

        "coordinate":
            site_config[
                "coordinate"
            ],
    }

    # --------------------------------------------------------
    # current PNU Parcel
    # --------------------------------------------------------

    parcel = (
        build_runtime_parcel(
            pnu=(
                site[
                    "pnu"
                ]
            ),

            address=(
                site[
                    "address"
                ]
            ),
        )
    )

    # --------------------------------------------------------
    # runtime spatial condition
    # --------------------------------------------------------

    condition = (
        resolve_site_spatial_condition(
            condition_name=(
                "방재지구"
            ),

            site=site,

            parcel=parcel,
        )
    )

    results[
        name
    ] = {

        "site":
            site,

        "parcel":
            parcel,

        "condition":
            condition,

        "expected_state":
            site_config[
                "expected_state"
            ],
    }


# ============================================================
# OUTPUT
# ============================================================

for name, result in (
    results.items()
):

    site = (
        result[
            "site"
        ]
    )

    parcel = (
        result[
            "parcel"
        ]
    )

    condition = (
        result[
            "condition"
        ]
    )

    print()

    print(
        "============================================================"
    )

    print(
        name
    )

    print(
        "============================================================"
    )

    print(
        "SITE ID:",
        site.get(
            "site_id"
        ),
    )

    print(
        "Address:",
        site.get(
            "address"
        ),
    )

    print(
        "PNU:",
        site.get(
            "pnu"
        ),
    )

    print(
        "Coordinate:",
        site.get(
            "coordinate"
        ),
    )

    print()

    print(
        "--- PARCEL ---"
    )

    print(
        "Loaded:",
        parcel.get(
            "geometry_loaded"
        ),
    )

    print(
        "Geometry:",
        parcel.get(
            "geometry_type"
        ),
    )

    print(
        "CRS:",
        parcel.get(
            "crs"
        ),
    )

    print(
        "Provider:",
        safe_dict(
            parcel.get(
                "source"
            )
        ).get(
            "provider"
        ),
    )

    print(
        "Dataset:",
        safe_dict(
            parcel.get(
                "source"
            )
        ).get(
            "dataset"
        ),
    )

    print(
        "Feature PNU:",
        parcel.get(
            "feature_pnu"
        ),
    )

    print(
        "Strict PNU verified:",
        parcel.get(
            "strict_pnu_verified"
        ),
    )

    print(
        "Resolution:",
        parcel.get(
            "resolution"
        ),
    )

    print()

    print(
        "--- DISASTER PREVENTION DISTRICT ---"
    )

    print(
        "State:",
        condition.get(
            "state"
        ),
    )

    print(
        "Expected:",
        result.get(
            "expected_state"
        ),
    )

    print(
        "Confidence:",
        condition.get(
            "confidence"
        ),
    )

    print(
        "Resolution:",
        condition.get(
            "resolution"
        ),
    )

    print(
        "Source:",
        condition.get(
            "source"
        ),
    )

    print(
        "Geometry verified:",
        condition.get(
            "geometry_verified"
        ),
    )

    print(
        "Evaluation:",
        condition.get(
            "evaluation"
        ),
    )

    print(
        "Intersections:",
        get_intersections(
            condition
        ),
    )


# ============================================================
# EXTRACT
# ============================================================

base = (
    results[
        "BASE"
    ]
)

live = (
    results[
        "LIVE"
    ]
)

positive = (
    results[
        "POSITIVE"
    ]
)


base_site = (
    base[
        "site"
    ]
)

live_site = (
    live[
        "site"
    ]
)

positive_site = (
    positive[
        "site"
    ]
)


base_parcel = (
    base[
        "parcel"
    ]
)

live_parcel = (
    live[
        "parcel"
    ]
)

positive_parcel = (
    positive[
        "parcel"
    ]
)


base_condition = (
    base[
        "condition"
    ]
)

live_condition = (
    live[
        "condition"
    ]
)

positive_condition = (
    positive[
        "condition"
    ]
)


base_source = safe_dict(
    base_condition.get(
        "source"
    )
)

live_source = safe_dict(
    live_condition.get(
        "source"
    )
)

positive_source = safe_dict(
    positive_condition.get(
        "source"
    )
)


base_evaluation = safe_dict(
    base_condition.get(
        "evaluation"
    )
)

live_evaluation = safe_dict(
    live_condition.get(
        "evaluation"
    )
)

positive_evaluation = safe_dict(
    positive_condition.get(
        "evaluation"
    )
)


positive_intersections = (
    get_intersections(
        positive_condition
    )
)


positive_feature_ids = {

    str(
        item.get(
            "feature_id"
        )
        or ""
    ).strip()

    for item
    in positive_intersections

    if (
        item.get(
            "intersects"
        )
        is True
    )
}


positive_names = {

    str(
        item.get(
            "district_name"
        )
        or ""
    ).strip()

    for item
    in positive_intersections

    if (
        item.get(
            "intersects"
        )
        is True
    )
}


# ============================================================
# VALIDATION
# ============================================================

validations = {

    # --------------------------------------------------------
    # identity isolation
    # --------------------------------------------------------

    "three different PNU": (
        len(
            {
                base_site[
                    "pnu"
                ],

                live_site[
                    "pnu"
                ],

                positive_site[
                    "pnu"
                ],
            }
        )
        == 3
    ),

    # --------------------------------------------------------
    # Parcel
    # --------------------------------------------------------

    "BASE parcel loaded": (
        base_parcel.get(
            "geometry_loaded"
        )
        is True
    ),

    "LIVE parcel loaded": (
        live_parcel.get(
            "geometry_loaded"
        )
        is True
    ),

    "POSITIVE parcel loaded": (
        positive_parcel.get(
            "geometry_loaded"
        )
        is True
    ),

    "BASE PNU verified": (
        base_parcel.get(
            "strict_pnu_verified"
        )
        is True
    ),

    "LIVE PNU verified": (
        live_parcel.get(
            "strict_pnu_verified"
        )
        is True
    ),

    "POSITIVE PNU verified": (
        positive_parcel.get(
            "strict_pnu_verified"
        )
        is True
    ),

    "BASE feature PNU matches": (
        base_parcel.get(
            "feature_pnu"
        )
        == base_site[
            "pnu"
        ]
    ),

    "LIVE feature PNU matches": (
        live_parcel.get(
            "feature_pnu"
        )
        == live_site[
            "pnu"
        ]
    ),

    "POSITIVE feature PNU matches": (
        positive_parcel.get(
            "feature_pnu"
        )
        == positive_site[
            "pnu"
        ]
    ),

    "BASE parcel CRS": (
        base_parcel.get(
            "crs"
        )
        == "EPSG:4326"
    ),

    "LIVE parcel CRS": (
        live_parcel.get(
            "crs"
        )
        == "EPSG:4326"
    ),

    "POSITIVE parcel CRS": (
        positive_parcel.get(
            "crs"
        )
        == "EPSG:4326"
    ),

    # --------------------------------------------------------
    # dataset
    # --------------------------------------------------------

    "BASE dataset": (
        base_source.get(
            "dataset"
        )
        == EXPECTED_DATASET
    ),

    "LIVE dataset": (
        live_source.get(
            "dataset"
        )
        == EXPECTED_DATASET
    ),

    "POSITIVE dataset": (
        positive_source.get(
            "dataset"
        )
        == EXPECTED_DATASET
    ),

    # --------------------------------------------------------
    # BASE / LIVE negative
    # --------------------------------------------------------

    "BASE disaster FALSE": (
        base_condition.get(
            "state"
        )
        == "FALSE"
    ),

    "LIVE disaster FALSE": (
        live_condition.get(
            "state"
        )
        == "FALSE"
    ),

    "BASE confidence HIGH": (
        base_condition.get(
            "confidence"
        )
        == "HIGH"
    ),

    "LIVE confidence HIGH": (
        live_condition.get(
            "confidence"
        )
        == "HIGH"
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

    "BASE no intersection": (
        base_evaluation.get(
            "intersects"
        )
        is False
    ),

    "LIVE no intersection": (
        live_evaluation.get(
            "intersects"
        )
        is False
    ),

    "BASE empty resolution": (
        base_condition.get(
            "resolution"
        )
        == "NO_DISASTER_PREVENTION_DISTRICT_FEATURE"
    ),

    "LIVE empty resolution": (
        live_condition.get(
            "resolution"
        )
        == "NO_DISASTER_PREVENTION_DISTRICT_FEATURE"
    ),

    # --------------------------------------------------------
    # positive
    # --------------------------------------------------------

    "POSITIVE disaster TRUE": (
        positive_condition.get(
            "state"
        )
        == "TRUE"
    ),

    "POSITIVE confidence HIGH": (
        positive_condition.get(
            "confidence"
        )
        == "HIGH"
    ),

    "POSITIVE geometry verified": (
        positive_condition.get(
            "geometry_verified"
        )
        is True
    ),

    "POSITIVE query success": (
        positive_evaluation.get(
            "query_success"
        )
        is True
    ),

    "POSITIVE evaluator intersects": (
        positive_evaluation.get(
            "intersects"
        )
        is True
    ),

    "POSITIVE intersection count": (
        (
            positive_evaluation.get(
                "intersection_count"
            )
            or 0
        )
        >= 1
    ),

    "POSITIVE intersection exists": (
        any(
            item.get(
                "intersects"
            )
            is True

            for item
            in positive_intersections
        )
    ),

    "POSITIVE feature ID": (
        EXPECTED_POSITIVE_FEATURE_ID
        in positive_feature_ids
    ),

    "POSITIVE district name": (
        EXPECTED_POSITIVE_DISTRICT_NAME
        in positive_names
    ),

    "POSITIVE resolution": (
        positive_condition.get(
            "resolution"
        )
        == "PARCEL_INTERSECTS_DISASTER_PREVENTION_DISTRICT"
    ),
}


# ============================================================
# RESULT
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
    "POSITIVE state:",
    positive_condition.get(
        "state"
    ),
)

print(
    "POSITIVE district names:",
    sorted(
        positive_names
    ),
)

print(
    "POSITIVE feature IDs:",
    sorted(
        positive_feature_ids
    ),
)

print()

print(
    "all_pass:",
    all_pass,
)


if not all_pass:

    raise AssertionError(
        "Disaster prevention district runtime regression failed"
    )