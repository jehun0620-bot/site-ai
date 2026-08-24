# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-7-F/G
Disaster Prevention District Rule Propagation Regression

목표
======================================================================
runtime 방재지구 condition이 Rule Engine의:

site_condition_context
→ site_registry
→ verified upper-branch condition
→ rule conditions

까지 정상 전파되는지 검증한다.

C-16-7-G 추가 검증
======================================================================
clause 189의 실제 상위법 branch는:

    SITE    방재지구
    PROJECT 재해예방시설

이다.

따라서:

1. runtime 방재지구 TRUE
   + 재해예방시설 UNSET
   → clause 189 CONDITIONAL
   → numeric POTENTIAL_CONDITIONAL

2. runtime 방재지구 FALSE
   → clause 189 NOT_APPLICABLE
   → numeric INACTIVE

이어야 한다.

추가 안전 검증
======================================================================
현재 C-16-7-G 단계에서는 numeric guard가 여전히
기존 disaster_prevention_district_resolution.json의 static guard를
사용한다.

따라서 runtime 방재지구 TRUE여도 아직 FAR 완화가 자동 적용되어서는
안 된다.

즉:

    spatial 방재지구 TRUE
    ≠
    clause 189 FAR 특례 자동 적용

C-16-7-H에서 numeric guard의 Multi-SITE/runtime 일반화를 별도로 수행한다.
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

PROJECT_PROFILE = {}

PROCEDURE_PROFILE = {}

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


RUNTIME_FALSE = {

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
        item
        for item
        in rules
        if isinstance(
            item,
            dict,
        )
    ]


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
                != condition_name
            ):
                continue

            found.append(
                {

                    "clause_index":
                        rule.get(
                            "clause_index"
                        ),

                    "rule_title":
                        rule.get(
                            "rule_title"
                        ),

                    "applicability":
                        rule.get(
                            "applicability"
                        ),

                    "condition_state":
                        condition.get(
                            "state"
                        ),

                    "condition_confidence":
                        condition.get(
                            "confidence"
                        ),

                    "condition_source":
                        condition.get(
                            "source"
                        ),

                    "upper_branch_verified":
                        condition.get(
                            "upper_branch_verified"
                        ),

                    "upper_branch_resolution":
                        condition.get(
                            "upper_branch_resolution"
                        ),

                    "upper_reference":
                        condition.get(
                            "upper_reference"
                        ),
                }
            )

    return found


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


def clause_189_excluded(
    items: List[Any],
) -> bool:

    for item in items:

        if not isinstance(
            item,
            dict,
        ):
            continue

        if (
            item.get(
                "clause_index"
            )
            == 189
        ):

            return True

    return False


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
        "방재지구"
    )
)

false_registry_condition = safe_dict(
    false_registry.get(
        "방재지구"
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


# ============================================================
# 방재지구 condition
# ============================================================

true_conditions = (
    find_condition(
        true_rules,
        "방재지구",
    )
)

false_conditions = (
    find_condition(
        false_rules,
        "방재지구",
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


true_condition_sources = {

    item.get(
        "condition_source"
    )

    for item
    in true_conditions
}


false_condition_sources = {

    item.get(
        "condition_source"
    )

    for item
    in false_conditions
}


# ============================================================
# 재해예방시설 condition
# ============================================================

true_facility_conditions = (
    find_condition(
        true_rules,
        "재해예방시설",
    )
)

false_facility_conditions = (
    find_condition(
        false_rules,
        "재해예방시설",
    )
)


true_facility_states = {

    item.get(
        "condition_state"
    )

    for item
    in true_facility_conditions
}


false_facility_states = {

    item.get(
        "condition_state"
    )

    for item
    in false_facility_conditions
}


# ============================================================
# CLAUSE 189
# ============================================================

true_clause_189 = (
    find_clause(
        true_rules,
        189,
    )
)

false_clause_189 = (
    find_clause(
        false_rules,
        189,
    )
)


true_clause_189_numeric = safe_dict(
    true_clause_189.get(
        "current_numeric_effect"
    )
)

false_clause_189_numeric = safe_dict(
    false_clause_189.get(
        "current_numeric_effect"
    )
)


# ============================================================
# NUMERIC
# ============================================================

true_numeric = safe_dict(
    true_result.get(
        "numeric"
    )
)

false_numeric = safe_dict(
    false_result.get(
        "numeric"
    )
)


true_excluded = safe_list(
    true_numeric.get(
        "excluded"
    )
)

false_excluded = safe_list(
    false_numeric.get(
        "excluded"
    )
)


# ============================================================
# OUTPUT
# ============================================================

print(
    "=== DISASTER TRUE ==="
)

print(
    "Registry:",
    true_registry_condition,
)

print(
    "Disaster conditions:",
    true_conditions,
)

print(
    "Facility conditions:",
    true_facility_conditions,
)

print(
    "Clause 189:",
    {
        "applicability":
            true_clause_189.get(
                "applicability"
            ),

        "conditions":
            true_clause_189.get(
                "conditions"
            ),

        "required_inputs":
            true_clause_189.get(
                "required_inputs"
            ),

        "blocked_by":
            true_clause_189.get(
                "blocked_by"
            ),

        "numeric_effect":
            true_clause_189.get(
                "numeric_effect"
            ),

        "current_numeric_effect":
            true_clause_189.get(
                "current_numeric_effect"
            ),
    },
)

print(
    "Numeric:",
    true_numeric,
)


print()

print(
    "=== DISASTER FALSE ==="
)

print(
    "Registry:",
    false_registry_condition,
)

print(
    "Disaster conditions:",
    false_conditions,
)

print(
    "Facility conditions:",
    false_facility_conditions,
)

print(
    "Clause 189:",
    {
        "applicability":
            false_clause_189.get(
                "applicability"
            ),

        "conditions":
            false_clause_189.get(
                "conditions"
            ),

        "required_inputs":
            false_clause_189.get(
                "required_inputs"
            ),

        "blocked_by":
            false_clause_189.get(
                "blocked_by"
            ),

        "numeric_effect":
            false_clause_189.get(
                "numeric_effect"
            ),

        "current_numeric_effect":
            false_clause_189.get(
                "current_numeric_effect"
            ),
    },
)

print(
    "Numeric:",
    false_numeric,
)


# ============================================================
# VALIDATION
# ============================================================

validations = {

    # --------------------------------------------------------
    # Registry
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
    # 방재지구 condition propagation
    # --------------------------------------------------------

    "disaster condition found TRUE": (
        len(
            true_conditions
        )
        > 0
    ),

    "disaster condition found FALSE": (
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

    "TRUE rule source propagated": (
        true_condition_sources
        == {
            "RUNTIME_SPATIAL_CONDITION"
        }
    ),

    "FALSE rule source propagated": (
        false_condition_sources
        == {
            "RUNTIME_SPATIAL_CONDITION"
        }
    ),

    # --------------------------------------------------------
    # verified upper branch
    # --------------------------------------------------------

    "TRUE disaster upper branch verified": (
        all(
            item.get(
                "upper_branch_verified"
            )
            is True

            for item
            in true_conditions
        )
        and bool(
            true_conditions
        )
    ),

    "FALSE disaster upper branch verified": (
        all(
            item.get(
                "upper_branch_verified"
            )
            is True

            for item
            in false_conditions
        )
        and bool(
            false_conditions
        )
    ),

    "TRUE disaster upper reference": (
        all(
            item.get(
                "upper_reference"
            )
            == "국토계획법 시행령 제85조제5항"

            for item
            in true_conditions
        )
        and bool(
            true_conditions
        )
    ),

    "FALSE disaster upper reference": (
        all(
            item.get(
                "upper_reference"
            )
            == "국토계획법 시행령 제85조제5항"

            for item
            in false_conditions
        )
        and bool(
            false_conditions
        )
    ),

    # --------------------------------------------------------
    # 재해예방시설 PROJECT condition
    # --------------------------------------------------------

    "TRUE facility condition found": (
        len(
            true_facility_conditions
        )
        > 0
    ),

    "FALSE facility condition found": (
        len(
            false_facility_conditions
        )
        > 0
    ),

    "TRUE facility remains UNSET": (
        true_facility_states
        == {
            "UNSET"
        }
    ),

    "FALSE facility remains UNSET": (
        false_facility_states
        == {
            "UNSET"
        }
    ),

    "TRUE facility upper branch verified": (
        all(
            item.get(
                "upper_branch_verified"
            )
            is True

            for item
            in true_facility_conditions
        )
        and bool(
            true_facility_conditions
        )
    ),

    "FALSE facility upper branch verified": (
        all(
            item.get(
                "upper_branch_verified"
            )
            is True

            for item
            in false_facility_conditions
        )
        and bool(
            false_facility_conditions
        )
    ),

    # --------------------------------------------------------
    # rules
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
    # clause 189 applicability
    # --------------------------------------------------------

    "TRUE clause 189 exists": (
        bool(
            true_clause_189
        )
    ),

    "FALSE clause 189 exists": (
        bool(
            false_clause_189
        )
    ),

    "TRUE clause 189 conditional": (
        true_clause_189.get(
            "applicability"
        )
        == "CONDITIONAL"
    ),

    "FALSE clause 189 not applicable": (
        false_clause_189.get(
            "applicability"
        )
        == "NOT_APPLICABLE"
    ),

    # --------------------------------------------------------
    # clause 189 numeric status
    # --------------------------------------------------------

    "TRUE clause 189 numeric conditional": (
        true_clause_189_numeric.get(
            "status"
        )
        == "POTENTIAL_CONDITIONAL"
    ),

    "FALSE clause 189 numeric inactive": (
        false_clause_189_numeric.get(
            "status"
        )
        == "INACTIVE"
    ),

    # --------------------------------------------------------
    # C-16-7-G numeric pipeline safety
    #
    # clause 189는 verified upper-branch condition 복원 후:
    #
    # TRUE scenario:
    #   방재지구 TRUE
    #   재해예방시설 UNSET
    #   → CONDITIONAL
    #   → POTENTIAL_CONDITIONAL
    #
    # FALSE scenario:
    #   방재지구 FALSE
    #   → NOT_APPLICABLE
    #   → INACTIVE
    #
    # 따라서 양쪽 모두 ACTIVE_CANDIDATE가 아니며
    # numeric guard 대상에 들어가면 안 된다.
    # --------------------------------------------------------

    "TRUE clause 189 does not reach numeric guard": (
        not clause_189_excluded(
        true_excluded
        )
    ),

    "FALSE clause 189 does not reach numeric guard": (
        not clause_189_excluded(
        false_excluded
        )
    ),

    "TRUE direct relaxation remains zero": (
        true_numeric.get(
            "direct_relaxation_count"
        )
        == 0
    ),

    "FALSE direct relaxation remains zero": (
        false_numeric.get(
            "direct_relaxation_count"
        )
        == 0
    ),

    # --------------------------------------------------------
    # confirmed numeric unchanged
    # --------------------------------------------------------

    "TRUE BCR retained": (
        true_numeric.get(
            "building_coverage_ratio"
        )
        == 50.0
    ),

    "TRUE FAR retained": (
        true_numeric.get(
            "floor_area_ratio"
        )
        == 250.0
    ),

    "FALSE BCR retained": (
        false_numeric.get(
            "building_coverage_ratio"
        )
        == 50.0
    ),

    "FALSE FAR retained": (
        false_numeric.get(
            "floor_area_ratio"
        )
        == 250.0
    ),

    "TRUE numeric resolution safe": (
        true_numeric.get(
            "resolution"
        )
        == "BASE_VALUES_RETAINED"
    ),

    "FALSE numeric resolution safe": (
        false_numeric.get(
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
    "TRUE disaster states:",
    true_condition_states,
)

print(
    "FALSE disaster states:",
    false_condition_states,
)

print(
    "TRUE disaster sources:",
    true_condition_sources,
)

print(
    "FALSE disaster sources:",
    false_condition_sources,
)

print(
    "TRUE facility states:",
    true_facility_states,
)

print(
    "FALSE facility states:",
    false_facility_states,
)

print(
    "TRUE clause 189 reaches numeric guard:",
    clause_189_excluded(
        true_excluded
    ),
)

print(
    "FALSE clause 189 reaches numeric guard:",
    clause_189_excluded(
        false_excluded
    ),
)

print(
    "TRUE clause 189 numeric status:",
    true_clause_189_numeric.get(
        "status"
    ),
)

print(
    "FALSE clause 189 numeric status:",
    false_clause_189_numeric.get(
        "status"
    ),
)

print(
    "TRUE clause 189 excluded:",
    clause_189_excluded(
        true_excluded
    ),
)

print(
    "FALSE clause 189 excluded:",
    clause_189_excluded(
        false_excluded
    ),
)

print(
    "TRUE BCR/FAR:",
    (
        true_numeric.get(
            "building_coverage_ratio"
        ),
        true_numeric.get(
            "floor_area_ratio"
        ),
    ),
)

print(
    "FALSE BCR/FAR:",
    (
        false_numeric.get(
            "building_coverage_ratio"
        ),
        false_numeric.get(
            "floor_area_ratio"
        ),
    ),
)

print()

print(
    "all_pass:",
    all_pass,
)


if not all_pass:

    raise AssertionError(
        "Disaster prevention district rule propagation regression failed"
    )