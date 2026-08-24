# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-7-H
Disaster Prevention District Numeric Guard Leakage Regression

목표
======================================================================
clause 189의 runtime SITE / PROJECT 조건이 모두 충족된 경우에도
현재 numeric guard가 대표 SITE(개포동 12번지)의 static
disaster_prevention_district_resolution.json 상태를 재사용하여
잘못 차단하는지 재현한다.

검증 시나리오
======================================================================

A. FALSE + TRUE
   방재지구 FALSE
   재해예방시설 TRUE
   → clause 189 NOT_APPLICABLE
   → numeric INACTIVE

B. TRUE + UNSET
   방재지구 TRUE
   재해예방시설 UNSET
   → clause 189 CONDITIONAL
   → numeric POTENTIAL_CONDITIONAL

C. TRUE + TRUE
   방재지구 TRUE
   재해예방시설 TRUE
   → clause 189 APPLICABLE
   → numeric ACTIVE_CANDIDATE

현재 예상되는 leakage
======================================================================
C 시나리오에서 clause 189가 ACTIVE_CANDIDATE까지 정상 도달해도,
build_numeric_guard_registry()가 static 서울 BASE snapshot의:

    disaster_prevention_district_resolution.json
    current_condition.status = FALSE

를 사용하므로 clause 189가 numeric guard에서 제외될 가능성이 있다.

이 테스트는 그 정적 누수를 의도적으로 재현한다.

중요
======================================================================
이 테스트의 목적은 현재 구현을 PASS시키는 것이 아니라,
C-16-7-H 수정 전 leakage를 정확히 증명하는 것이다.

따라서 C 시나리오에서:

    clause 189 excluded by numeric guard == True

가 나오면 현재 bug/leakage가 재현된 것이다.
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

        "expected_reaches_guard":
            False,
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

        "expected_reaches_guard":
            False,
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

        "expected_reaches_guard":
            True,
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

    indexes = safe_list(
        numeric.get(
            "retained_clause_indexes"
        )
    )

    return (
        clause_index
        in indexes
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

    exclusion = (
        find_numeric_exclusion(
            numeric,
            189,
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
            exclusion,
    }


# ============================================================
# OUTPUT
# ============================================================

for scenario_name, item in (
    results.items()
):

    scenario = (
        item[
            "scenario"
        ]
    )

    clause_189 = (
        item[
            "clause_189"
        ]
    )

    disaster_condition = (
        item[
            "disaster_condition"
        ]
    )

    facility_condition = (
        item[
            "facility_condition"
        ]
    )

    numeric = (
        item[
            "numeric"
        ]
    )

    exclusion = (
        item[
            "numeric_exclusion"
        ]
    )

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
        "Clause 189 reason:",
        clause_189.get(
            "applicability_reason"
        ),
    )

    print(
        "Disaster condition:",
        disaster_condition,
    )

    print(
        "Facility condition:",
        facility_condition,
    )

    print(
        "Current numeric effect:",
        current_numeric_effect,
    )

    print(
        "Numeric exclusion:",
        exclusion,
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


a_numeric_effect = safe_dict(
    a_clause.get(
        "current_numeric_effect"
    )
)

b_numeric_effect = safe_dict(
    b_clause.get(
        "current_numeric_effect"
    )
)

c_numeric_effect = safe_dict(
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


a_exclusion = a[
    "numeric_exclusion"
]

b_exclusion = b[
    "numeric_exclusion"
]

c_exclusion = c[
    "numeric_exclusion"
]


# ============================================================
# VALIDATION
# ============================================================

validations = {

    # --------------------------------------------------------
    # rule count
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
    # A FALSE + TRUE
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
        a_numeric_effect.get(
            "status"
        )
        == "INACTIVE"
    ),

    "A does not reach numeric guard": (
        not bool(
            a_exclusion
        )
    ),

    # --------------------------------------------------------
    # B TRUE + UNSET
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
        b_numeric_effect.get(
            "status"
        )
        == "POTENTIAL_CONDITIONAL"
    ),

    "B does not reach numeric guard": (
        not bool(
            b_exclusion
        )
    ),

    # --------------------------------------------------------
    # C TRUE + TRUE
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
        c_numeric_effect.get(
            "status"
        )
        == "ACTIVE_CANDIDATE"
    ),

    # --------------------------------------------------------
    # current leakage reproduction
    #
    # 이 값이 True이면 static 서울 BASE guard가
    # runtime TRUE SITE에 누수되고 있음을 재현한 것이다.
    # --------------------------------------------------------

    "C reaches numeric guard": (
        bool(
            c_exclusion
        )
    ),

    "C excluded clause is 189": (
        c_exclusion.get(
            "clause_index"
        )
        == 189
    ),

    "C static guard blocks numeric": (
        safe_dict(
            c_exclusion.get(
                "guard"
            )
        ).get(
            "allow_numeric"
        )
        is False
    ),

    # --------------------------------------------------------
    # leakage 때문에 아직 final FAR은 유지되어야 한다.
    # --------------------------------------------------------

    "C direct relaxation remains zero": (
        c_numeric.get(
            "direct_relaxation_count"
        )
        == 0
    ),

    "C BCR retained": (
        c_numeric.get(
            "building_coverage_ratio"
        )
        == 50.0
    ),

    "C FAR retained": (
        c_numeric.get(
            "floor_area_ratio"
        )
        == 250.0
    ),

    "C numeric resolution remains safe": (
        c_numeric.get(
            "resolution"
        )
        == "BASE_VALUES_RETAINED"
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
    "A applicability / numeric:",
    (
        a_clause.get(
            "applicability"
        ),
        a_numeric_effect.get(
            "status"
        ),
    ),
)

print(
    "B applicability / numeric:",
    (
        b_clause.get(
            "applicability"
        ),
        b_numeric_effect.get(
            "status"
        ),
    ),
)

print(
    "C applicability / numeric:",
    (
        c_clause.get(
            "applicability"
        ),
        c_numeric_effect.get(
            "status"
        ),
    ),
)

print()

print(
    "C numeric exclusion:",
    c_exclusion,
)

print()

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
    "STATIC_NUMERIC_GUARD_LEAKAGE_REPRODUCED:",
    bool(
        c_exclusion
    ),
)

print()

print(
    "all_pass:",
    all_pass,
)


if not all_pass:

    raise AssertionError(
        "Disaster prevention district numeric guard leakage regression failed"
    )