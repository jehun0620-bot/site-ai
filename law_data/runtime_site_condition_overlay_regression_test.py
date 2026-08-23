# -*- coding: utf-8 -*-

"""
STEP 17-21-C-15-4
Runtime SITE Condition Overlay Regression

목표
======================================================================
runtime SITE condition context가 실제 Rule Engine에 반영되는지 검증한다.

대상 condition:
    지구단위계획

검증 시나리오
======================================================================
1. runtime TRUE
2. runtime FALSE

핵심 검증
======================================================================
- runtime TRUE/FALSE가 최종 site_registry에 반영되는가
- source가 RUNTIME_SPATIAL_CONDITION으로 바뀌는가
- runtime FALSE가 기존 대표 SITE TRUE보다 우선하는가
- 실제 rule condition state가 바뀌는가
- 총 rule 수 314는 유지되는가
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from law_data.rule_evaluation_pipeline import (
    evaluate_site_rules,
)


# ============================================================
# common
# ============================================================

PROJECT_PROFILE = {
    "공동주택": "TRUE",
}

PROCEDURE_PROFILE = {
    "도시계획위원회심의": "TRUE",
}

BASE_NUMERIC_CONTEXT = {

    "building_coverage_ratio": {
        "value": 50.0,
    },

    "floor_area_ratio": {
        "value": 250.0,
    },
}

SITE_ZONE_CONTEXT = (
    "제3종일반주거지역"
)


# ============================================================
# runtime contexts
# ============================================================

RUNTIME_TRUE = {

    "지구단위계획": {

        "type":
            "SITE",

        "state":
            "TRUE",

        "confidence":
            "HIGH",

        "pnu":
            "1168010300100120000",

        "resolution":
            "PARCEL_INTERSECTS_DISTRICT_UNIT_PLAN",

        "geometry_verified":
            True,

        "source": {
            "provider":
                "VWorld",

            "dataset":
                "LT_C_UPISUQ161",
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


RUNTIME_FALSE = {

    "지구단위계획": {

        "type":
            "SITE",

        "state":
            "FALSE",

        "confidence":
            "HIGH",

        "pnu":
            "TEST_FALSE_PNU",

        "resolution":
            "PARCEL_DOES_NOT_INTERSECT_DISTRICT_UNIT_PLAN",

        "geometry_verified":
            True,

        "source": {
            "provider":
                "VWorld",

            "dataset":
                "LT_C_UPISUQ161",
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
# evaluation
# ============================================================

true_result = (
    evaluate_site_rules(
        project_profile=(
            PROJECT_PROFILE
        ),

        procedure_profile=(
            PROCEDURE_PROFILE
        ),

        base_numeric_context=(
            BASE_NUMERIC_CONTEXT
        ),

        site_zone_context=(
            SITE_ZONE_CONTEXT
        ),

        site_condition_context=(
            deepcopy(
                RUNTIME_TRUE
            )
        ),
    )
)


false_result = (
    evaluate_site_rules(
        project_profile=(
            PROJECT_PROFILE
        ),

        procedure_profile=(
            PROCEDURE_PROFILE
        ),

        base_numeric_context=(
            BASE_NUMERIC_CONTEXT
        ),

        site_zone_context=(
            SITE_ZONE_CONTEXT
        ),

        site_condition_context=(
            deepcopy(
                RUNTIME_FALSE
            )
        ),
    )
)


# ============================================================
# helpers
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

    candidates = [

        result.get(
            "rules"
        ),

        safe_dict(
            result.get(
                "rule_evaluation"
            )
        ).get(
            "rules"
        ),

        safe_dict(
            result.get(
                "evaluation"
            )
        ).get(
            "rules"
        ),
    ]

    for candidate in candidates:

        if isinstance(
            candidate,
            list,
        ):

            return [
                item
                for item
                in candidate
                if isinstance(
                    item,
                    dict,
                )
            ]

    return []


def find_district_unit_plan_conditions(
    rules: List[
        Dict[str, Any]
    ],
) -> List[
    Dict[str, Any]
]:

    found = []

    for rule in rules:

        conditions = safe_list(
            rule.get(
                "conditions"
            )
        )

        for condition in conditions:

            if not isinstance(
                condition,
                dict,
            ):
                continue

            if (
                condition.get(
                    "name"
                )
                != "지구단위계획"
            ):
                continue

            found.append(
                {
                    "clause_id": (
                        rule.get(
                            "clause_id"
                        )
                        or rule.get(
                            "id"
                        )
                    ),

                    "applicability": (
                        rule.get(
                            "applicability"
                        )
                    ),

                    "condition_state": (
                        condition.get(
                            "state"
                        )
                    ),

                    "condition_confidence": (
                        condition.get(
                            "confidence"
                        )
                    ),

                    "condition_source": (
                        condition.get(
                            "source"
                        )
                    ),
                }
            )

    return found


def summarize_applicability(
    result: Dict[str, Any],
) -> Dict[str, Any]:

    candidates = [

        result.get(
            "summary"
        ),

        result.get(
            "rule_summary"
        ),

        result.get(
            "final"
        ),

        safe_dict(
            result.get(
                "rule_evaluation"
            )
        ),
    ]

    for candidate in candidates:

        if not isinstance(
            candidate,
            dict,
        ):
            continue

        keys = {
            str(
                key
            ).upper():
                value
            for key, value
            in candidate.items()
        }

        if all(
            key in keys
            for key in {
                "APPLICABLE",
                "NOT_APPLICABLE",
                "CONDITIONAL",
                "UNKNOWN",
            }
        ):

            return {
                "APPLICABLE":
                    keys[
                        "APPLICABLE"
                    ],

                "NOT_APPLICABLE":
                    keys[
                        "NOT_APPLICABLE"
                    ],

                "CONDITIONAL":
                    keys[
                        "CONDITIONAL"
                    ],

                "UNKNOWN":
                    keys[
                        "UNKNOWN"
                    ],
            }

    return {}


# ============================================================
# extracted
# ============================================================

true_registry = safe_dict(
    true_result.get(
        "site_registry"
    )
)

false_registry = safe_dict(
    false_result.get(
        "site_registry"
    )
)


true_registry_condition = safe_dict(
    true_registry.get(
        "지구단위계획"
    )
)

false_registry_condition = safe_dict(
    false_registry.get(
        "지구단위계획"
    )
)


true_rules = (
    extract_rules(
        true_result
    )
)

false_rules = (
    extract_rules(
        false_result
    )
)


true_conditions = (
    find_district_unit_plan_conditions(
        true_rules
    )
)

false_conditions = (
    find_district_unit_plan_conditions(
        false_rules
    )
)


true_summary = (
    summarize_applicability(
        true_result
    )
)

false_summary = (
    summarize_applicability(
        false_result
    )
)


# ============================================================
# console
# ============================================================

print(
    "=== RUNTIME TRUE ==="
)

print(
    "Registry:",
    true_registry_condition,
)

print(
    "District-unit-plan conditions:",
    true_conditions,
)

print(
    "Summary:",
    true_summary,
)


print()

print(
    "=== RUNTIME FALSE ==="
)

print(
    "Registry:",
    false_registry_condition,
)

print(
    "District-unit-plan conditions:",
    false_conditions,
)

print(
    "Summary:",
    false_summary,
)


# ============================================================
# validation
# ============================================================

true_condition_states = {
    item.get(
        "condition_state"
    )
    for item
    in true_conditions
}

false_condition_states = {
    item.get(
        "condition_state"
    )
    for item
    in false_conditions
}


validations = {

    # --------------------------------------------------------
    # registry overlay
    # --------------------------------------------------------

    "TRUE registry exists": (
        bool(
            true_registry_condition
        )
    ),

    "FALSE registry exists": (
        bool(
            false_registry_condition
        )
    ),

    "TRUE registry state": (
        true_registry_condition.get(
            "state"
        )
        == "TRUE"
    ),

    "FALSE registry state": (
        false_registry_condition.get(
            "state"
        )
        == "FALSE"
    ),

    "TRUE runtime source": (
        true_registry_condition.get(
            "source"
        )
        == "RUNTIME_SPATIAL_CONDITION"
    ),

    "FALSE runtime source": (
        false_registry_condition.get(
            "source"
        )
        == "RUNTIME_SPATIAL_CONDITION"
    ),

    "TRUE runtime flag": (
        true_registry_condition.get(
            "runtime"
        )
        is True
    ),

    "FALSE runtime flag": (
        false_registry_condition.get(
            "runtime"
        )
        is True
    ),

    # --------------------------------------------------------
    # actual rule conditions
    # --------------------------------------------------------

    "district condition found TRUE": (
        len(
            true_conditions
        )
        > 0
    ),

    "district condition found FALSE": (
        len(
            false_conditions
        )
        > 0
    ),

    "TRUE conditions propagated": (
        true_condition_states
        == {
            "TRUE"
        }
    ),

    "FALSE conditions propagated": (
        false_condition_states
        == {
            "FALSE"
        }
    ),

    # --------------------------------------------------------
    # total rules
    # --------------------------------------------------------

    "TRUE rules 314": (
        len(
            true_rules
        )
        == 314
    ),

    "FALSE rules 314": (
        len(
            false_rules
        )
        == 314
    ),

    # --------------------------------------------------------
    # runtime scenarios are genuinely distinct
    # --------------------------------------------------------

    "registry states differ": (
        true_registry_condition.get(
            "state"
        )
        != false_registry_condition.get(
            "state"
        )
    ),

    "rule condition states differ": (
        true_condition_states
        != false_condition_states
    ),
}


# ============================================================
# result
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
    "TRUE condition states:",
    true_condition_states,
)

print(
    "FALSE condition states:",
    false_condition_states,
)

print(
    "TRUE rule count:",
    len(
        true_rules
    ),
)

print(
    "FALSE rule count:",
    len(
        false_rules
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