# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-5-B
Development Promotion District Rule Propagation Regression

목표
======================================================================
runtime 개발진흥지구 condition이 Rule Engine의:

site_condition_context
→ site_registry
→ 314개 rule conditions

까지 실제로 전파되는지 검증한다.

검증 시나리오
======================================================================
1. runtime TRUE
2. runtime FALSE

핵심 검증
======================================================================
- 최종 site_registry 개발진흥지구 state
- source = RUNTIME_SPATIAL_CONDITION
- runtime flag = True
- 개발진흥지구 condition을 가진 rule clause에 state 전파
- 총 rule 수 314 유지
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

PROJECT_PROFILE = {
    "공동주택":
        "TRUE",
}

PROCEDURE_PROFILE = {
    "도시계획위원회심의":
        "TRUE",
}

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

SITE_ZONE_CONTEXT = (
    "제3종일반주거지역"
)


# ============================================================
# RUNTIME CONTEXT
# ============================================================

RUNTIME_TRUE = {

    "개발진흥지구": {

        "type":
            "SITE",

        "state":
            "TRUE",

        "confidence":
            "HIGH",

        "pnu":
            "1123010300110820000",

        "resolution":
            "PARCEL_INTERSECTS_DEVELOPMENT_PROMOTION_DISTRICT",

        "geometry_verified":
            True,

        "source": {

            "provider":
                "VWorld",

            "dataset":
                "LT_C_UQ129",
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

    "개발진흥지구": {

        "type":
            "SITE",

        "state":
            "FALSE",

        "confidence":
            "HIGH",

        "pnu":
            "1168010300100120000",

        "resolution":
            "NO_DEVELOPMENT_PROMOTION_DISTRICT_FEATURE",

        "geometry_verified":
            True,

        "source": {

            "provider":
                "VWorld",

            "dataset":
                "LT_C_UQ129",
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
# EVALUATION
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


def find_condition(
    rules: List[
        Dict[str, Any]
    ],
    condition_name: str,
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
                != condition_name
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


# ============================================================
# EXTRACT
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
        "개발진흥지구"
    )
)

false_registry_condition = safe_dict(
    false_registry.get(
        "개발진흥지구"
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
    find_condition(
        true_rules,
        "개발진흥지구",
    )
)

false_conditions = (
    find_condition(
        false_rules,
        "개발진흥지구",
    )
)


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


# ============================================================
# CONSOLE
# ============================================================

print(
    "=== DEVELOPMENT PROMOTION TRUE ==="
)

print(
    "Registry:",
    true_registry_condition,
)

print(
    "Rule conditions:",
    true_conditions,
)


print()

print(
    "=== DEVELOPMENT PROMOTION FALSE ==="
)

print(
    "Registry:",
    false_registry_condition,
)

print(
    "Rule conditions:",
    false_conditions,
)


# ============================================================
# VALIDATION
# ============================================================

validations = {

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

    "development condition found TRUE": (
        len(
            true_conditions
        )
        > 0
    ),

    "development condition found FALSE": (
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

    "registry states differ": (
        true_registry_condition.get(
            "state"
        )
        != false_registry_condition.get(
            "state"
        )
    ),

    "rule states differ": (
        true_condition_states
        != false_condition_states
    ),

    "TRUE rule source propagated": (
    {
        item.get(
            "condition_source"
        )
        for item
        in true_conditions
    }
    == {
        "RUNTIME_SPATIAL_CONDITION"
    }
),

"FALSE rule source propagated": (
    {
        item.get(
            "condition_source"
        )
        for item
        in false_conditions
    }
    == {
        "RUNTIME_SPATIAL_CONDITION"
    }
),
}


# ============================================================
# RESULT
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
    "TRUE states:",
    true_condition_states,
)

print(
    "FALSE states:",
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

    raise AssertionError(
        "Development promotion rule propagation regression failed"
    )