# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-7-I
Disaster Prevention District Runtime Numeric Guard Regression

목표
======================================================================
방재지구 clause 189 numeric guard가 더 이상 대표 SITE의 static
방재지구 상태를 재사용하지 않고, 현재 Rule Engine에서 평가된
SITE / PROJECT branch 상태를 기준으로 동작하는지 검증한다.

시나리오
======================================================================

A. 방재지구 FALSE + 재해예방시설 TRUE
   → clause 189 NOT_APPLICABLE
   → numeric INACTIVE
   → numeric guard 도달 안 함
   → BASE_VALUES_RETAINED

B. 방재지구 TRUE + 재해예방시설 UNSET
   → clause 189 CONDITIONAL
   → POTENTIAL_CONDITIONAL
   → numeric guard 도달 안 함
   → BASE_VALUES_RETAINED

C. 방재지구 TRUE + 재해예방시설 TRUE
   → clause 189 APPLICABLE
   → ACTIVE_CANDIDATE
   → numeric guard 통과
   → retained
   → direct_relaxation_count = 1
   → RECALC_REQUIRED

중요
======================================================================
C 시나리오에서 FAR 300을 즉시 확정하지 않는다.

현재 단계에서는:

    valid numeric candidate
    → RECALC_REQUIRED

까지만 허용한다.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from law_data.rule_evaluation_pipeline import (
    evaluate_site_rules,
)


# ============================================================
# COMMON
# ============================================================

SITE_ZONE_CONTEXT = (
    "제3종일반주거지역"
)

BASE_NUMERIC_CONTEXT = {

    "building_coverage_ratio": {
        "value":
            50.0,
    },

    "floor_area_ratio": {
        "value":
            250.0,
    },
}


# ============================================================
# RUNTIME SITE CONTEXT
# ============================================================

DISASTER_TRUE_CONTEXT = {

    "방재지구": {

        "type":
            "SITE",

        "state":
            "TRUE",

        "confidence":
            "HIGH",

        "pnu":
            "1211015700105800006",

        "resolution":
            "PARCEL_INTERSECTS_DISASTER_PREVENTION_DISTRICT",

        "geometry_verified":
            True,

        "source": {

            "provider":
                "VWorld",

            "dataset":
                "LT_C_UQ125",
        },

        "evaluation": {

            "query_success":
                True,

            "intersects":
                True,

            "intersection_count":
                1,
        },
    },
}


DISASTER_FALSE_CONTEXT = {

    "방재지구": {

        "type":
            "SITE",

        "state":
            "FALSE",

        "confidence":
            "HIGH",

        "pnu":
            "1168010300100120000",

        "resolution":
            "NO_DISASTER_PREVENTION_DISTRICT_FEATURE",

        "geometry_verified":
            True,

        "source": {

            "provider":
                "VWorld",

            "dataset":
                "LT_C_UQ125",
        },

        "evaluation": {

            "query_success":
                True,

            "intersects":
                False,

            "intersection_count":
                0,
        },
    },
}


# ============================================================
# SCENARIOS
# ============================================================

SCENARIOS = {

    "A_FALSE_TRUE": {

        "description":
            "방재지구 FALSE + 재해예방시설 TRUE",

        "site_condition_context":
            DISASTER_FALSE_CONTEXT,

        "project_profile": {
            "재해예방시설":
                "TRUE",
        },

        "expected_applicability":
            "NOT_APPLICABLE",

        "expected_numeric_status":
            "INACTIVE",
    },

    "B_TRUE_UNSET": {

        "description":
            "방재지구 TRUE + 재해예방시설 UNSET",

        "site_condition_context":
            DISASTER_TRUE_CONTEXT,

        "project_profile":
            {},

        "expected_applicability":
            "CONDITIONAL",

        "expected_numeric_status":
            "POTENTIAL_CONDITIONAL",
    },

    "C_TRUE_TRUE": {

        "description":
            "방재지구 TRUE + 재해예방시설 TRUE",

        "site_condition_context":
            DISASTER_TRUE_CONTEXT,

        "project_profile": {
            "재해예방시설":
                "TRUE",
        },

        "expected_applicability":
            "APPLICABLE",

        "expected_numeric_status":
            "ACTIVE_CANDIDATE",
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


def safe_list(
    value: Any,
) -> List[Any]:

    if isinstance(
        value,
        list,
    ):
        return value

    return []


def extract_rules(
    result: Dict[str, Any],
) -> List[Dict[str, Any]]:

    rules = (
        result.get(
            "rules"
        )
    )

    if not isinstance(
        rules,
        list,
    ):
        return []

    return [
        rule
        for rule
        in rules
        if isinstance(
            rule,
            dict,
        )
    ]


def find_clause(
    rules: List[
        Dict[str, Any]
    ],
    clause_index: int,
) -> Dict[str, Any]:

    for rule in rules:

        if (
            rule.get(
                "clause_index"
            )
            == clause_index
        ):

            return rule

    return {}


def find_condition(
    rule: Dict[str, Any],
    condition_name: str,
) -> Dict[str, Any]:

    for condition in safe_list(
        rule.get(
            "conditions"
        )
    ):

        if not isinstance(
            condition,
            dict,
        ):
            continue

        if (
            condition.get(
                "name"
            )
            == condition_name
        ):

            return condition

    return {}


def find_numeric_exclusion(
    numeric: Dict[str, Any],
    clause_index: int,
) -> Dict[str, Any]:

    for item in safe_list(
        numeric.get(
            "excluded"
        )
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        if (
            item.get(
                "clause_index"
            )
            == clause_index
        ):

            return item

    return {}


def clause_in_retained(
    numeric: Dict[str, Any],
    clause_index: int,
) -> bool:

    return (
        clause_index
        in safe_list(
            numeric.get(
                "retained_clause_indexes"
            )
        )
    )


# ============================================================
# RUN
# ============================================================

results: Dict[
    str,
    Dict[str, Any],
] = {}


for scenario_name, scenario in (
    SCENARIOS.items()
):

    result = (
        evaluate_site_rules(
            project_profile=(
                deepcopy(
                    scenario[
                        "project_profile"
                    ]
                )
            ),

            procedure_profile={},

            base_numeric_context=(
                deepcopy(
                    BASE_NUMERIC_CONTEXT
                )
            ),

            site_zone_context=(
                SITE_ZONE_CONTEXT
            ),

            site_condition_context=(
                deepcopy(
                    scenario[
                        "site_condition_context"
                    ]
                )
            ),
        )
    )

    rules = (
        extract_rules(
            result
        )
    )

    clause_189 = (
        find_clause(
            rules,
            189,
        )
    )

    numeric = safe_dict(
        result.get(
            "numeric"
        )
    )

    results[
        scenario_name
    ] = {

        "scenario":
            scenario,

        "result":
            result,

        "rules":
            rules,

        "clause_189":
            clause_189,

        "disaster_condition":
            find_condition(
                clause_189,
                "방재지구",
            ),

        "facility_condition":
            find_condition(
                clause_189,
                "재해예방시설",
            ),

        "numeric":
            numeric,

        "numeric_exclusion":
            find_numeric_exclusion(
                numeric,
                189,
            ),
    }


# ============================================================
# OUTPUT
# ============================================================

for scenario_name, item in (
    results.items()
):

    scenario = item[
        "scenario"
    ]

    clause_189 = item[
        "clause_189"
    ]

    numeric = item[
        "numeric"
    ]

    current_numeric_effect = safe_dict(
        clause_189.get(
            "current_numeric_effect"
        )
    )

    print()

    print(
        "============================================================"
    )

    print(
        scenario_name
    )

    print(
        scenario[
            "description"
        ]
    )

    print(
        "============================================================"
    )

    print(
        "Clause 189 applicability:",
        clause_189.get(
            "applicability"
        ),
    )

    print(
        "Disaster condition:",
        item[
            "disaster_condition"
        ],
    )

    print(
        "Facility condition:",
        item[
            "facility_condition"
        ],
    )

    print(
        "Current numeric effect:",
        current_numeric_effect,
    )

    print(
        "Numeric exclusion:",
        item[
            "numeric_exclusion"
        ],
    )

    print(
        "Clause 189 retained:",
        clause_in_retained(
            numeric,
            189,
        ),
    )

    print(
        "Direct relaxation count:",
        numeric.get(
            "direct_relaxation_count"
        ),
    )

    print(
        "Numeric resolution:",
        numeric.get(
            "resolution"
        ),
    )

    print(
        "BCR:",
        numeric.get(
            "building_coverage_ratio"
        ),
    )

    print(
        "FAR:",
        numeric.get(
            "floor_area_ratio"
        ),
    )


# ============================================================
# EXTRACT
# ============================================================

a = results[
    "A_FALSE_TRUE"
]

b = results[
    "B_TRUE_UNSET"
]

c = results[
    "C_TRUE_TRUE"
]


a_clause = a[
    "clause_189"
]

b_clause = b[
    "clause_189"
]

c_clause = c[
    "clause_189"
]


a_effect = safe_dict(
    a_clause.get(
        "current_numeric_effect"
    )
)

b_effect = safe_dict(
    b_clause.get(
        "current_numeric_effect"
    )
)

c_effect = safe_dict(
    c_clause.get(
        "current_numeric_effect"
    )
)


a_numeric = a[
    "numeric"
]

b_numeric = b[
    "numeric"
]

c_numeric = c[
    "numeric"
]


# ============================================================
# VALIDATION
# ============================================================

validations = {

    # --------------------------------------------------------
    # rule counts
    # --------------------------------------------------------

    "A rules 314": (
        len(
            a[
                "rules"
            ]
        )
        == 314
    ),

    "B rules 314": (
        len(
            b[
                "rules"
            ]
        )
        == 314
    ),

    "C rules 314": (
        len(
            c[
                "rules"
            ]
        )
        == 314
    ),

    # --------------------------------------------------------
    # A
    # --------------------------------------------------------

    "A disaster FALSE": (
        a[
            "disaster_condition"
        ].get(
            "state"
        )
        == "FALSE"
    ),

    "A facility TRUE": (
        a[
            "facility_condition"
        ].get(
            "state"
        )
        == "TRUE"
    ),

    "A clause 189 NOT_APPLICABLE": (
        a_clause.get(
            "applicability"
        )
        == "NOT_APPLICABLE"
    ),

    "A numeric INACTIVE": (
        a_effect.get(
            "status"
        )
        == "INACTIVE"
    ),

    "A not retained": (
        not clause_in_retained(
            a_numeric,
            189,
        )
    ),

    "A no numeric exclusion": (
        not bool(
            a[
                "numeric_exclusion"
            ]
        )
    ),

    "A direct relaxation zero": (
        a_numeric.get(
            "direct_relaxation_count"
        )
        == 0
    ),

    "A base resolution": (
        a_numeric.get(
            "resolution"
        )
        == "BASE_VALUES_RETAINED"
    ),

    "A BCR 50": (
        a_numeric.get(
            "building_coverage_ratio"
        )
        == 50.0
    ),

    "A FAR 250": (
        a_numeric.get(
            "floor_area_ratio"
        )
        == 250.0
    ),

    # --------------------------------------------------------
    # B
    # --------------------------------------------------------

    "B disaster TRUE": (
        b[
            "disaster_condition"
        ].get(
            "state"
        )
        == "TRUE"
    ),

    "B facility UNSET": (
        b[
            "facility_condition"
        ].get(
            "state"
        )
        == "UNSET"
    ),

    "B clause 189 CONDITIONAL": (
        b_clause.get(
            "applicability"
        )
        == "CONDITIONAL"
    ),

    "B numeric POTENTIAL_CONDITIONAL": (
        b_effect.get(
            "status"
        )
        == "POTENTIAL_CONDITIONAL"
    ),

    "B not retained": (
        not clause_in_retained(
            b_numeric,
            189,
        )
    ),

    "B no numeric exclusion": (
        not bool(
            b[
                "numeric_exclusion"
            ]
        )
    ),

    "B direct relaxation zero": (
        b_numeric.get(
            "direct_relaxation_count"
        )
        == 0
    ),

    "B base resolution": (
        b_numeric.get(
            "resolution"
        )
        == "BASE_VALUES_RETAINED"
    ),

    "B BCR 50": (
        b_numeric.get(
            "building_coverage_ratio"
        )
        == 50.0
    ),

    "B FAR 250": (
        b_numeric.get(
            "floor_area_ratio"
        )
        == 250.0
    ),

    # --------------------------------------------------------
    # C
    # --------------------------------------------------------

    "C disaster TRUE": (
        c[
            "disaster_condition"
        ].get(
            "state"
        )
        == "TRUE"
    ),

    "C facility TRUE": (
        c[
            "facility_condition"
        ].get(
            "state"
        )
        == "TRUE"
    ),

    "C clause 189 APPLICABLE": (
        c_clause.get(
            "applicability"
        )
        == "APPLICABLE"
    ),

    "C numeric ACTIVE_CANDIDATE": (
        c_effect.get(
            "status"
        )
        == "ACTIVE_CANDIDATE"
    ),

    "C no numeric exclusion": (
        not bool(
            c[
                "numeric_exclusion"
            ]
        )
    ),

    "C clause 189 retained": (
        clause_in_retained(
            c_numeric,
            189,
        )
    ),

    "C direct relaxation one": (
        c_numeric.get(
            "direct_relaxation_count"
        )
        == 1
    ),

    "C resolution RECALC_REQUIRED": (
        c_numeric.get(
            "resolution"
        )
        == "RECALC_REQUIRED"
    ),

    "C BCR pending": (
        c_numeric.get(
            "building_coverage_ratio"
        )
        is None
    ),

    "C FAR pending": (
        c_numeric.get(
            "floor_area_ratio"
        )
        is None
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
    "A:",
    (
        a_clause.get(
            "applicability"
        ),
        a_effect.get(
            "status"
        ),
        a_numeric.get(
            "resolution"
        ),
    ),
)

print(
    "B:",
    (
        b_clause.get(
            "applicability"
        ),
        b_effect.get(
            "status"
        ),
        b_numeric.get(
            "resolution"
        ),
    ),
)

print(
    "C:",
    (
        c_clause.get(
            "applicability"
        ),
        c_effect.get(
            "status"
        ),
        c_numeric.get(
            "resolution"
        ),
    ),
)

print()

print(
    "C clause 189 retained:",
    clause_in_retained(
        c_numeric,
        189,
    ),
)

print(
    "C direct relaxation count:",
    c_numeric.get(
        "direct_relaxation_count"
    ),
)

print(
    "C BCR/FAR:",
    (
        c_numeric.get(
            "building_coverage_ratio"
        ),
        c_numeric.get(
            "floor_area_ratio"
        ),
    ),
)

print()

print(
    "STATIC_NUMERIC_GUARD_LEAKAGE_REMOVED:",
    (
        not bool(
            c[
                "numeric_exclusion"
            ]
        )
        and clause_in_retained(
            c_numeric,
            189,
        )
    ),
)

print()

print(
    "all_pass:",
    all_pass,
)


if not all_pass:

    raise AssertionError(
        "Disaster prevention district runtime numeric guard regression failed"
    )