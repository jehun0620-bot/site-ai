# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-5A
Reusable Rule Evaluation Pipeline Skeleton

목표
======================================================================
지금까지 분리되어 있던 다음 로직을 하나의 evaluation pipeline으로 묶는다.

1. SITE baseline
2. SITE_HISTORY external dependency
3. PROJECT input
4. PROCEDURE input
5. branch-local condition overlay
6. SITE resolution registry repair
7. numeric-specific verified guards
8. stacking / ceiling semantic override
9. 최종 applicability summary
10. 최종 BCR / FAR state

중요
======================================================================
이번 단계는 기존 검증 결과를 재사용하는 "통합 파이프라인 골격"이다.

새로운 법적 판정을 만들지 않는다.

기존 검증 완료 결과:
- clause 4
- clause 189
- clause 205
- clause 250

를 verified guard registry로 통합한다.
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-5A "
    "reusable rule evaluation pipeline"
)


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

SITE_COMPLETE_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_site_complete.json"
)

BRANCH_OVERLAY_PATH = (
    OUTPUT_DIR
    / "numeric_branch_local_condition_overlay.json"
)

UPPER_BRANCH_PATH = (
    OUTPUT_DIR
    / "upper_relaxation_branch_resolution.json"
)

DISASTER_PATH = (
    OUTPUT_DIR
    / "disaster_prevention_district_resolution.json"
)

CLAUSE_205_PATH = (
    OUTPUT_DIR
    / "clause_205_tourism_branch_guard.json"
)

CLAUSE_250_PATH = (
    OUTPUT_DIR
    / "clause_250_stacking_ceiling_resolution.json"
)

SEOUL_DOWNTOWN_PATH = (
    OUTPUT_DIR
    / "seoul_downtown_condition_resolution.json"
)

BASE_NUMERIC_PATH = (
    OUTPUT_DIR
    / "base_numeric_regulation_hierarchy.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "rule_evaluation_pipeline.json"
)


# ============================================================
# TEST INPUT
#
# 이후 실제 API / UI input으로 교체 가능
# ============================================================

PROJECT_INPUT = {
    "공동주택": "TRUE",
}

PROCEDURE_INPUT = {
    "도시계획위원회심의": "TRUE",
}


VALID_STATES = {
    "TRUE",
    "FALSE",
    "UNKNOWN",
    "UNSET",
}


# ============================================================
# util
# ============================================================

def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():

        raise FileNotFoundError(
            f"입력 파일 없음: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def save_json(
    data: Dict[str, Any],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def validate_input_states(
    data: Dict[str, str],
) -> None:

    for name, state in data.items():

        if state not in VALID_STATES:

            raise ValueError(
                f"잘못된 input state: "
                f"{name}={state}"
            )


# ============================================================
# condition helpers
# ============================================================

def refresh_condition_groups(
    rule: Dict[str, Any],
) -> None:

    conditions = (
        rule.get(
            "conditions",
            []
        )
    )

    rule["required_inputs"] = [
        item
        for item
        in conditions
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "state"
        )
        == "UNSET"
    ]

    rule["blocked_by"] = [
        item
        for item
        in conditions
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "state"
        )
        == "FALSE"
    ]

    rule["unknown_by"] = [
        item
        for item
        in conditions
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "state"
        )
        == "UNKNOWN"
    ]


def recalculate_applicability(
    rule: Dict[str, Any],
) -> Dict[str, str]:

    blocked = (
        rule.get(
            "blocked_by",
            []
        )
    )

    unknown = (
        rule.get(
            "unknown_by",
            []
        )
    )

    required = (
        rule.get(
            "required_inputs",
            []
        )
    )

    if blocked:

        return {
            "applicability": (
                "NOT_APPLICABLE"
            ),

            "reason": (
                "필수조건 FALSE: "
                + ", ".join(
                    safe_string(
                        item.get(
                            "name"
                        )
                    )
                    for item
                    in blocked
                )
            ),
        }

    if unknown:

        return {
            "applicability": (
                "UNKNOWN"
            ),

            "reason": (
                "필수조건 미확정: "
                + ", ".join(
                    safe_string(
                        item.get(
                            "name"
                        )
                    )
                    for item
                    in unknown
                )
            ),
        }

    if required:

        return {
            "applicability": (
                "CONDITIONAL"
            ),

            "reason": (
                "추가 입력 필요: "
                + ", ".join(
                    safe_string(
                        item.get(
                            "name"
                        )
                    )
                    for item
                    in required
                )
            ),
        }

    if (
        rule.get(
            "zone_relevance"
        )
        == "OTHER_ZONE"
    ):

        return {
            "applicability": (
                "NOT_APPLICABLE"
            ),

            "reason": (
                "현재 SITE 용도지역 불일치"
            ),
        }

    return {
        "applicability": (
            "APPLICABLE"
        ),

        "reason": (
            "모든 필수조건 충족"
        ),
    }


def refresh_numeric_effect(
    rule: Dict[str, Any],
) -> None:

    numeric_effect = (
        rule.get(
            "numeric_effect"
        )
    )

    if not numeric_effect:
        return

    applicability = (
        rule.get(
            "applicability"
        )
    )

    if applicability == "NOT_APPLICABLE":

        status = (
            "INACTIVE"
        )

    elif applicability == "CONDITIONAL":

        status = (
            "POTENTIAL_CONDITIONAL"
        )

    elif applicability == "UNKNOWN":

        status = (
            "POTENTIAL_UNKNOWN"
        )

    else:

        status = (
            "ACTIVE_CANDIDATE"
        )

    rule[
        "current_numeric_effect"
    ] = {
        "status": (
            status
        ),

        "effect_class": (
            rule.get(
                "numeric_effect_class"
            )
        ),

        "semantic": (
            numeric_effect
        ),
    }


# ============================================================
# PROJECT / PROCEDURE injection
# ============================================================

def inject_dynamic_inputs(
    rules: List[Dict[str, Any]],
    project_input: Dict[str, str],
    procedure_input: Dict[str, str],
) -> List[Dict[str, Any]]:

    changes = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        before_applicability = (
            rule.get(
                "applicability"
            )
        )

        touched = False

        for condition in rule.get(
            "conditions",
            [],
        ):

            if not isinstance(
                condition,
                dict,
            ):
                continue

            name = safe_string(
                condition.get(
                    "name"
                )
            )

            condition_type = safe_string(
                condition.get(
                    "type"
                )
            )

            new_state = None

            if (
                condition_type
                == "PROJECT"
                and name
                in project_input
            ):

                new_state = (
                    project_input[
                        name
                    ]
                )

            elif (
                condition_type
                == "PROCEDURE"
                and name
                in procedure_input
            ):

                new_state = (
                    procedure_input[
                        name
                    ]
                )

            if new_state is None:
                continue

            previous_state = (
                condition.get(
                    "state"
                )
            )

            condition[
                "state"
            ] = (
                new_state
            )

            condition[
                "previous_state"
            ] = (
                previous_state
            )

            condition[
                "source"
            ] = (
                "PIPELINE_DYNAMIC_INPUT"
            )

            condition[
                "confidence"
            ] = (
                "USER_DECLARED"
            )

            touched = True

        if not touched:
            continue

        refresh_condition_groups(
            rule
        )

        result = (
            recalculate_applicability(
                rule
            )
        )

        rule[
            "applicability"
        ] = (
            result[
                "applicability"
            ]
        )

        rule[
            "applicability_reason"
        ] = (
            result[
                "reason"
            ]
        )

        refresh_numeric_effect(
            rule
        )

        if (
            before_applicability
            != rule.get(
                "applicability"
            )
        ):

            changes.append(
                {
                    "clause_index": (
                        rule.get(
                            "clause_index"
                        )
                    ),

                    "before": (
                        before_applicability
                    ),

                    "after": (
                        rule.get(
                            "applicability"
                        )
                    ),
                }
            )

    return changes


# ============================================================
# SITE registry repair
# ============================================================

def apply_site_registry(
    rules: List[Dict[str, Any]],
    registry: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:

    repairs = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        changed = False

        for condition in rule.get(
            "conditions",
            [],
        ):

            if not isinstance(
                condition,
                dict,
            ):
                continue

            name = safe_string(
                condition.get(
                    "name"
                )
            )

            resolved = (
                registry.get(
                    name
                )
            )

            if not resolved:
                continue

            previous_state = (
                condition.get(
                    "state"
                )
            )

            if (
                previous_state
                == resolved[
                    "state"
                ]
            ):
                continue

            condition[
                "state"
            ] = (
                resolved[
                    "state"
                ]
            )

            condition[
                "confidence"
            ] = (
                resolved[
                    "confidence"
                ]
            )

            condition[
                "source"
            ] = (
                resolved[
                    "source"
                ]
            )

            repairs.append(
                {
                    "clause_index": (
                        rule.get(
                            "clause_index"
                        )
                    ),

                    "condition": (
                        name
                    ),

                    "before": (
                        previous_state
                    ),

                    "after": (
                        resolved[
                            "state"
                        ]
                    ),
                }
            )

            changed = True

        if not changed:
            continue

        refresh_condition_groups(
            rule
        )

        result = (
            recalculate_applicability(
                rule
            )
        )

        rule[
            "applicability"
        ] = (
            result[
                "applicability"
            ]
        )

        rule[
            "applicability_reason"
        ] = (
            result[
                "reason"
            ]
        )

        refresh_numeric_effect(
            rule
        )

    return repairs


# ============================================================
# numeric verified guard
# ============================================================

def apply_numeric_guards(
    rules: List[Dict[str, Any]],
    guards: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:

    active_before = []

    excluded = []

    retained = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        if not rule.get(
            "numeric_effect"
        ):
            continue

        if (
            rule.get(
                "current_numeric_effect",
                {},
            ).get(
                "status"
            )
            != "ACTIVE_CANDIDATE"
        ):
            continue

        active_before.append(
            rule
        )

    for rule in active_before:

        clause_index = int(
            rule.get(
                "clause_index"
            )
        )

        guard = (
            guards.get(
                clause_index
            )
        )

        if (
            guard
            and guard.get(
                "allow_numeric"
            )
            is False
        ):

            excluded.append(
                {
                    "clause_index": (
                        clause_index
                    ),

                    "rule_title": (
                        rule.get(
                            "rule_title"
                        )
                    ),

                    "guard": (
                        guard
                    ),
                }
            )

            continue

        retained.append(
            rule
        )

    return {
        "active_before": (
            active_before
        ),

        "excluded": (
            excluded
        ),

        "retained": (
            retained
        ),
    }


# ============================================================
# remaining input aggregation
# ============================================================

def aggregate_required_inputs(
    rules: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:

    project_counter = Counter()
    procedure_counter = Counter()

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        for condition in rule.get(
            "required_inputs",
            [],
        ):

            if not isinstance(
                condition,
                dict,
            ):
                continue

            name = safe_string(
                condition.get(
                    "name"
                )
            )

            condition_type = safe_string(
                condition.get(
                    "type"
                )
            )

            if condition_type == "PROJECT":

                project_counter[
                    name
                ] += 1

            elif condition_type == "PROCEDURE":

                procedure_counter[
                    name
                ] += 1

    return {
        "project": [
            {
                "name": (
                    name
                ),

                "affected_clause_count": (
                    count
                ),

                "state": (
                    "UNSET"
                ),
            }

            for name, count
            in project_counter.most_common()
        ],

        "procedure": [
            {
                "name": (
                    name
                ),

                "affected_clause_count": (
                    count
                ),

                "state": (
                    "UNSET"
                ),
            }

            for name, count
            in procedure_counter.most_common()
        ],
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    validate_input_states(
        PROJECT_INPUT
    )

    validate_input_states(
        PROCEDURE_INPUT
    )

    site_complete = load_json(
        SITE_COMPLETE_PATH
    )

    branch_overlay = load_json(
        BRANCH_OVERLAY_PATH
    )

    upper = load_json(
        UPPER_BRANCH_PATH
    )

    disaster = load_json(
        DISASTER_PATH
    )

    clause_205 = load_json(
        CLAUSE_205_PATH
    )

    clause_250 = load_json(
        CLAUSE_250_PATH
    )

    downtown = load_json(
        SEOUL_DOWNTOWN_PATH
    )

    base_numeric = load_json(
        BASE_NUMERIC_PATH
    )

    # ========================================================
    # 1. source rules
    #
    # branch-local overlay가 이미 반영된 최신 rule set 사용
    # ========================================================

    rules = copy.deepcopy(
        branch_overlay.get(
            "rules",
            []
        )
    )

    if len(rules) != 314:

        raise ValueError(
            f"rule count 오류: {len(rules)}"
        )

    # ========================================================
    # 2. SITE registry
    # ========================================================

    downtown_condition = (
        downtown.get(
            "condition",
            {}
        )
    )

    site_registry = {

        "서울도심": {
            "state": (
                downtown_condition.get(
                    "status"
                )
            ),

            "confidence": (
                downtown_condition.get(
                    "confidence"
                )
            ),

            "source": (
                "SEOUL_DOWNTOWN_CONDITION_RESOLUTION"
            ),
        },
    }

    site_repairs = (
        apply_site_registry(
            rules,
            site_registry,
        )
    )

    # ========================================================
    # 3. dynamic input
    # ========================================================

    dynamic_changes = (
        inject_dynamic_inputs(
            rules,
            PROJECT_INPUT,
            PROCEDURE_INPUT,
        )
    )

    # ========================================================
    # 4. verified numeric guard registry
    # ========================================================

    clause_4_resolution = (
        upper.get(
            "resolutions",
            {},
        ).get(
            "clause_4",
            {},
        ).get(
            "resolution"
        )
    )

    disaster_condition = (
        disaster.get(
            "current_condition",
            {}
        )
    )

    clause_189_resolution = (
        disaster.get(
            "numeric_effect",
            {},
        ).get(
            "resolution"
        )
    )

    clause_205_resolution = (
        clause_205.get(
            "resolution",
            {},
        ).get(
            "applicability"
        )
    )

    clause_250_resolution = (
        clause_250.get(
            "resolution",
            {}
        )
    )

    verified_guards = {

        4: {
            "allow_numeric": (
                clause_4_resolution
                == "CONFIRMED"
            ),

            "resolution": (
                clause_4_resolution
            ),

            "role": (
                "DIRECT_RELAXATION"
            ),
        },

        189: {
            "allow_numeric": (
                clause_189_resolution
                == "CONFIRMED"
                and disaster_condition.get(
                    "status"
                )
                == "TRUE"
            ),

            "resolution": (
                clause_189_resolution
            ),

            "role": (
                "DIRECT_RELAXATION"
            ),
        },

        205: {
            "allow_numeric": (
                clause_205_resolution
                == "APPLICABLE"
            ),

            "resolution": (
                clause_205_resolution
            ),

            "role": (
                "DIRECT_RELAXATION"
            ),
        },

        250: {
            "allow_numeric": (
                clause_250_resolution.get(
                    "allow_numeric_effect"
                )
                is True
            ),

            "resolution": (
                clause_250_resolution.get(
                    "applicability"
                )
            ),

            "role": (
                clause_250_resolution.get(
                    "role"
                )
            ),

            "corrected_numeric_semantic": (
                clause_250_resolution.get(
                    "corrected_numeric_semantic"
                )
            ),
        },
    }

    numeric_guard_result = (
        apply_numeric_guards(
            rules,
            verified_guards,
        )
    )

    # ========================================================
    # 5. final applicability
    # ========================================================

    applicability = Counter(
        rule.get(
            "applicability"
        )
        for rule
        in rules
        if isinstance(
            rule,
            dict,
        )
    )

    # ========================================================
    # 6. base regulation
    # ========================================================

    base_regulation = (
        base_numeric.get(
            "current_base_regulation",
            {}
        )
    )

    base_bcr = float(
        base_regulation.get(
            "building_coverage_ratio",
            {},
        ).get(
            "value",
            50.0,
        )
    )

    base_far = float(
        base_regulation.get(
            "floor_area_ratio",
            {},
        ).get(
            "value",
            250.0,
        )
    )

    # ========================================================
    # 7. immediate numeric effect
    #
    # 현재 verified direct relaxation은
    # 4, 189, 205
    #
    # 모두 guard false일 것으로 예상
    # ========================================================

    DIRECT_RELAXATION_INDEXES = {
        4,
        189,
        205,
    }

    retained_direct_relaxations = [
        rule
        for rule
        in numeric_guard_result[
            "retained"
        ]
        if int(
            rule.get(
                "clause_index"
            )
        )
        in DIRECT_RELAXATION_INDEXES
    ]

    if retained_direct_relaxations:

        numeric_resolution = (
            "RECALC_REQUIRED"
        )

        confirmed_bcr = None
        confirmed_far = None

    else:

        numeric_resolution = (
            "BASE_VALUES_RETAINED"
        )

        confirmed_bcr = (
            base_bcr
        )

        confirmed_far = (
            base_far
        )

    # ========================================================
    # 8. external history dependency
    # ========================================================

    historical_dependency = (
        site_complete.get(
            "historical_dependency",
            {}
        )
    )

    # ========================================================
    # 9. remaining inputs
    # ========================================================

    remaining_inputs = (
        aggregate_required_inputs(
            rules
        )
    )

    # ========================================================
    # 10. pipeline status
    # ========================================================

    pipeline_ready = (
        site_complete.get(
            "site_stage",
            {},
        ).get(
            "rule_engine_ready"
        )
        is True
        and numeric_resolution
        == "BASE_VALUES_RETAINED"
        and confirmed_bcr
        == 50.0
        and confirmed_far
        == 250.0
    )

    # ========================================================
    # 11. validations
    # ========================================================

    excluded_indexes = {
        item[
            "clause_index"
        ]
        for item
        in numeric_guard_result[
            "excluded"
        ]
    }

    validations = {

        "rules 314": (
            len(
                rules
            )
            == 314
        ),

        "SITE engine ready": (
            site_complete.get(
                "site_stage",
                {},
            ).get(
                "rule_engine_ready"
            )
            is True
        ),

        "clause 4 guard applied": (
            4
            in excluded_indexes
        ),

        "clause 189 guard applied": (
            189
            in excluded_indexes
        ),

        "clause 205 inactive": (
            (
                205
                in excluded_indexes
            )
            or not any(
                int(
                    rule.get(
                        "clause_index",
                        -1,
                    )
                )
                == 205

                for rule
                in numeric_guard_result[
                    "active_before"
                ]
            )
        ),

        "clause 250 guard applied": (
            (
                250
                in excluded_indexes
            )
            or not any(
                int(
                    rule.get(
                        "clause_index",
                        -1,
                    )
                )
                == 250

                for rule
                in numeric_guard_result[
                    "active_before"
                ]
            )
        ),

        "direct relaxation 0": (
            len(
                retained_direct_relaxations
            )
            == 0
        ),

        "numeric base retained": (
            numeric_resolution
            == "BASE_VALUES_RETAINED"
        ),

        "BCR 50": (
            confirmed_bcr
            == 50.0
        ),

        "FAR 250": (
            confirmed_far
            == 250.0
        ),

        "historical dependency preserved": (
            historical_dependency.get(
                "automation_state"
            )
            == "HISTORICAL_SOURCE_PENDING"
        ),

        "pipeline ready": (
            pipeline_ready
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # 12. output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "pipeline": {
            "ready": (
                pipeline_ready
            ),

            "site_stage": (
                site_complete.get(
                    "site_stage",
                    {}
                )
            ),
        },

        "input": {
            "project": (
                PROJECT_INPUT
            ),

            "procedure": (
                PROCEDURE_INPUT
            ),
        },

        "site_registry": (
            site_registry
        ),

        "site_repairs": (
            site_repairs
        ),

        "dynamic_changes": (
            dynamic_changes
        ),

        "verified_numeric_guards": (
            verified_guards
        ),

        "numeric_guard_result": {
            "active_before_count": (
                len(
                    numeric_guard_result[
                        "active_before"
                    ]
                )
            ),

            "excluded_count": (
                len(
                    numeric_guard_result[
                        "excluded"
                    ]
                )
            ),

            "excluded": (
                numeric_guard_result[
                    "excluded"
                ]
            ),

            "retained_count": (
                len(
                    numeric_guard_result[
                        "retained"
                    ]
                )
            ),

            "retained_clause_indexes": [
                rule.get(
                    "clause_index"
                )

                for rule
                in numeric_guard_result[
                    "retained"
                ]
            ],
        },

        "rule_summary": {
            "total": (
                len(
                    rules
                )
            ),

            "applicable": (
                applicability[
                    "APPLICABLE"
                ]
            ),

            "not_applicable": (
                applicability[
                    "NOT_APPLICABLE"
                ]
            ),

            "conditional": (
                applicability[
                    "CONDITIONAL"
                ]
            ),

            "unknown": (
                applicability[
                    "UNKNOWN"
                ]
            ),
        },

        "numeric_result": {
            "resolution": (
                numeric_resolution
            ),

            "building_coverage_ratio": (
                confirmed_bcr
            ),

            "floor_area_ratio": (
                confirmed_far
            ),

            "retained_direct_relaxation_count": (
                len(
                    retained_direct_relaxations
                )
            ),
        },

        "remaining_inputs": (
            remaining_inputs
        ),

        "external_dependencies": {
            "historical": (
                historical_dependency
            ),
        },

        "rules": (
            rules
        ),

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "Pipeline ready:",
        pipeline_ready,
    )

    print()

    print(
        "Input PROJECT:",
        PROJECT_INPUT,
    )

    print(
        "Input PROCEDURE:",
        PROCEDURE_INPUT,
    )

    print()

    print(
        "SITE repairs:",
        len(
            site_repairs
        ),
    )

    print(
        "Dynamic changes:",
        len(
            dynamic_changes
        ),
    )

    print()

    print(
        "Rules:",
        len(
            rules
        ),
    )

    print(
        "APPLICABLE:",
        applicability[
            "APPLICABLE"
        ],
    )

    print(
        "NOT_APPLICABLE:",
        applicability[
            "NOT_APPLICABLE"
        ],
    )

    print(
        "CONDITIONAL:",
        applicability[
            "CONDITIONAL"
        ],
    )

    print(
        "UNKNOWN:",
        applicability[
            "UNKNOWN"
        ],
    )

    print()

    print(
        "Numeric active before guard:",
        len(
            numeric_guard_result[
                "active_before"
            ]
        ),
    )

    print(
        "Numeric excluded:",
        len(
            numeric_guard_result[
                "excluded"
            ]
        ),
    )

    print(
        "Numeric retained:",
        len(
            numeric_guard_result[
                "retained"
            ]
        ),
    )

    print()

    print(
        "Immediate direct relaxation:",
        len(
            retained_direct_relaxations
        ),
    )

    print(
        "Numeric resolution:",
        numeric_resolution,
    )

    print()

    print(
        "Confirmed BCR:",
        confirmed_bcr,
    )

    print(
        "Confirmed FAR:",
        confirmed_far,
    )

    print()

    print(
        "Remaining PROJECT inputs:",
        len(
            remaining_inputs[
                "project"
            ]
        ),
    )

    print(
        "Remaining PROCEDURE inputs:",
        len(
            remaining_inputs[
                "procedure"
            ]
        ),
    )

    print()

    print(
        "Historical dependency:",
        historical_dependency.get(
            "automation_state"
        ),
    )

    print()

    print(
        "all_pass:",
        all_pass,
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return (
        0
        if all_pass
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )