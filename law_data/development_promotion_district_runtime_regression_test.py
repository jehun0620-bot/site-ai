# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-4
Development Promotion District Runtime 3-SITE Regression

검증 SITE
======================================================================

1. BASE
   서울특별시 강남구 개포동 12번지
   PNU 1168010300100120000
   expected: 개발진흥지구 FALSE

2. LIVE
   서울특별시 강남구 개포동 13번지
   PNU 1168010300100130000
   expected: 개발진흥지구 FALSE

3. POSITIVE
   서울특별시 동대문구 제기동 1082
   PNU 1123010300110820000
   expected: 개발진흥지구 TRUE
   expected feature: 특정개발진흥지구

핵심 검증
======================================================================
- 각 SITE별 PNU Parcel Polygon을 독립 확보한다.
- Parcel Feature PNU 직접 일치를 요구한다.
- LT_C_UQ129 dataset을 runtime query한다.
- FALSE는 verified empty evidence로 판정한다.
- TRUE는 Parcel Polygon intersection까지 확인한다.
- 대표 SITE geometry를 다른 PNU에 재사용하지 않는다.
"""

from __future__ import annotations

from typing import Any, Dict

from law_data.parcel_geometry_provider import (
    resolve_live_parcel_geometry,
)

from law_data.spatial_condition_evaluator import (
    resolve_site_spatial_condition,
)


# ============================================================
# SITE
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
            "11230-10300-1082-0000",

        "address":
            "서울특별시 동대문구 제기동 1082",

        "pnu":
            "1123010300110820000",

        "coordinate": {

            "x":
                127.03762819634002,

            "y":
                37.58067534326105,

            "crs":
                "EPSG:4326",
        },

        "expected_state":
            "TRUE",
    },
}


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


def build_runtime_parcel(
    *,
    pnu: str,
    address: str,
) -> Dict[str, Any]:

    """
    C-14 live parcel provider 결과를
    spatial condition evaluator가 사용하는 parcel 형태로 정규화한다.
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
):

    evidence = safe_dict(
        condition.get(
            "evidence"
        )
    )

    value = evidence.get(
        "intersections"
    )

    if isinstance(
        value,
        list,
    ):
        return value

    return []


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

    parcel = (
        build_runtime_parcel(
            pnu=site[
                "pnu"
            ],
            address=site[
                "address"
            ],
        )
    )

    condition = (
        resolve_site_spatial_condition(
            condition_name=(
                "개발진흥지구"
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
# CONSOLE
# ============================================================

for name, result in (
    results.items()
):

    site = result[
        "site"
    ]

    parcel = result[
        "parcel"
    ]

    condition = result[
        "condition"
    ]

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
        "--- DEVELOPMENT PROMOTION DISTRICT ---"
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
# VALIDATIONS
# ============================================================

base = results[
    "BASE"
]

live = results[
    "LIVE"
]

positive = results[
    "POSITIVE"
]


base_parcel = base[
    "parcel"
]

live_parcel = live[
    "parcel"
]

positive_parcel = positive[
    "parcel"
]


base_condition = base[
    "condition"
]

live_condition = live[
    "condition"
]

positive_condition = positive[
    "condition"
]


positive_intersections = (
    get_intersections(
        positive_condition
    )
)


positive_names = {

    str(
        item.get(
            "district_name"
        )
        or ""
    ).strip()

    for item
    in positive_intersections

    if item.get(
        "intersects"
    )
    is True
}


validations = {

    # --------------------------------------------------------
    # PNU isolation
    # --------------------------------------------------------

    "three different PNU": (
        len(
            {
                base[
                    "site"
                ][
                    "pnu"
                ],

                live[
                    "site"
                ][
                    "pnu"
                ],

                positive[
                    "site"
                ][
                    "pnu"
                ],
            }
        )
        == 3
    ),

    # --------------------------------------------------------
    # parcel
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
        == base[
            "site"
        ][
            "pnu"
        ]
    ),

    "LIVE feature PNU matches": (
        live_parcel.get(
            "feature_pnu"
        )
        == live[
            "site"
        ][
            "pnu"
        ]
    ),

    "POSITIVE feature PNU matches": (
        positive_parcel.get(
            "feature_pnu"
        )
        == positive[
            "site"
        ][
            "pnu"
        ]
    ),

    # --------------------------------------------------------
    # dataset
    # --------------------------------------------------------

    "BASE dataset": (
        safe_dict(
            base_condition.get(
                "source"
            )
        ).get(
            "dataset"
        )
        == "LT_C_UQ129"
    ),

    "LIVE dataset": (
        safe_dict(
            live_condition.get(
                "source"
            )
        ).get(
            "dataset"
        )
        == "LT_C_UQ129"
    ),

    "POSITIVE dataset": (
        safe_dict(
            positive_condition.get(
                "source"
            )
        ).get(
            "dataset"
        )
        == "LT_C_UQ129"
    ),

    # --------------------------------------------------------
    # negative cases
    # --------------------------------------------------------

    "BASE development promotion FALSE": (
        base_condition.get(
            "state"
        )
        == "FALSE"
    ),

    "LIVE development promotion FALSE": (
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

    # --------------------------------------------------------
    # positive case
    # --------------------------------------------------------

    "POSITIVE development promotion TRUE": (
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

    "POSITIVE district name": (
        "특정개발진흥지구"
        in positive_names
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

print()

print(
    "all_pass:",
    all_pass,
)


if not all_pass:

    raise AssertionError(
        "Development promotion district runtime regression failed"
    )