# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-5B
Clean-baseline reusable rule evaluation pipeline

목표
======================================================================
이미 PROJECT / PROCEDURE 값이 주입된 중간 JSON을 출발점으로 사용하지 않는다.

항상:

site_rule_evaluation_site_complete.json
    ↓
branch-local predicate 확장
    ↓
SITE registry 적용
    ↓
PROJECT / PROCEDURE input 적용
    ↓
applicability 재계산
    ↓
verified numeric guards
    ↓
최종 numeric resolution

순서로 처음부터 평가한다.


중요
======================================================================
이 단계가 통과해야 실제 reusable pipeline으로 승격할 수 있다.

현재 테스트 입력:

PROJECT
    공동주택 = TRUE

PROCEDURE
    도시계획위원회심의 = TRUE
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-5B "
    "clean baseline reusable rule evaluation pipeline"
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

BRANCH_PROBE_PATH = (
    OUTPUT_DIR
    / "numeric_branch_local_condition_generalization_probe.json"
)

SEOUL_DOWNTOWN_PATH = (
    OUTPUT_DIR
    / "seoul_downtown_condition_resolution.json"
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

BASE_NUMERIC_PATH = (
    OUTPUT_DIR
    / "base_numeric_regulation_hierarchy.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "rule_evaluation_clean_pipeline.json"
)


# ============================================================
# TEST INPUT
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


def validate_inputs(
    data: Dict[str, str],
    input_type: str,
) -> None:

    for name, state in data.items():

        if state not in VALID_STATES:

            raise ValueError(
                f"{input_type} state 오류: "
                f"{name}={state}"
            )


# ============================================================
# condition groups
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


# ============================================================
# applicability
# ============================================================

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


# ============================================================
# numeric status
# ============================================================

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
# single rule refresh
# ============================================================

def refresh_rule(
    rule: Dict[str, Any],
) -> None:

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


# ============================================================
# SITE-specific branch resolver
# ============================================================

def resolve_branch_condition(
    name: str,
    condition_type: str,
    site_zone: str,
    site_registry: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    # --------------------------------------------------------
    # existing SITE registry
    # --------------------------------------------------------

    existing = (
        site_registry.get(
            name
        )
    )

    if existing:

        return {
            "name": (
                name
            ),

            "type": (
                condition_type
            ),

            "state": (
                existing[
                    "state"
                ]
            ),

            "confidence": (
                existing[
                    "confidence"
                ]
            ),

            "source": (
                existing[
                    "source"
                ]
            ),

            "branch_local": (
                True
            ),
        }

    # --------------------------------------------------------
    # 서울시 조례 제48조 7~10호
    # --------------------------------------------------------

    if (
        name
        == "서울조례제48조7호부터10호지역"
    ):

        zone_map = {
            "제1종전용주거지역": 1,
            "제2종전용주거지역": 2,
            "제1종일반주거지역": 3,
            "제2종일반주거지역": 4,
            "제3종일반주거지역": 5,
            "준주거지역": 6,
            "중심상업지역": 7,
            "일반상업지역": 8,
            "근린상업지역": 9,
            "유통상업지역": 10,
        }

        number = (
            zone_map.get(
                site_zone
            )
        )

        return {
            "name": (
                name
            ),

            "type": (
                "SITE"
            ),

            "state": (
                "TRUE"
                if number
                in {
                    7,
                    8,
                    9,
                    10,
                }
                else "FALSE"
            ),

            "confidence": (
                "HIGH"
            ),

            "source": (
                "PIPELINE_BRANCH_SITE_RESOLVER"
            ),

            "branch_local": (
                True
            ),

            "resolution_meta": {
                "site_zone": (
                    site_zone
                ),

                "article_48_number": (
                    number
                ),
            },
        }

    # --------------------------------------------------------
    # new PROJECT
    # --------------------------------------------------------

    if condition_type == "PROJECT":

        return {
            "name": (
                name
            ),

            "type": (
                condition_type
            ),

            "state": (
                "UNSET"
            ),

            "confidence": (
                "NONE"
            ),

            "source": (
                "PIPELINE_BRANCH_PREDICATE"
            ),

            "branch_local": (
                True
            ),
        }

    # --------------------------------------------------------
    # new PROCEDURE
    # --------------------------------------------------------

    if condition_type == "PROCEDURE":

        return {
            "name": (
                name
            ),

            "type": (
                condition_type
            ),

            "state": (
                "UNSET"
            ),

            "confidence": (
                "NONE"
            ),

            "source": (
                "PIPELINE_BRANCH_PREDICATE"
            ),

            "branch_local": (
                True
            ),
        }

    # --------------------------------------------------------
    # unresolved SITE
    # --------------------------------------------------------

    return {
        "name": (
            name
        ),

        "type": (
            condition_type
        ),

        "state": (
            "UNKNOWN"
        ),

        "confidence": (
            "NONE"
        ),

        "source": (
            "PIPELINE_BRANCH_PREDICATE"
        ),

        "branch_local": (
            True
        ),
    }


# ============================================================
# apply branch-local predicates
# ============================================================

def apply_branch_predicates(
    rules: List[Dict[str, Any]],
    high_candidates: List[Dict[str, Any]],
    site_zone: str,
    site_registry: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    selected = [
        item
        for item
        in high_candidates
        if item.get(
            "direct_in_clause_text"
        )
        is True
    ]

    by_clause = {}

    for item in selected:

        clause_index = int(
            item.get(
                "clause_index"
            )
        )

        by_clause.setdefault(
            clause_index,
            [],
        ).append(
            item
        )

    added = []

    reused = []

    touched = set()

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        clause_index = int(
            rule.get(
                "clause_index"
            )
        )

        predicates = (
            by_clause.get(
                clause_index,
                []
            )
        )

        if not predicates:
            continue

        existing_names = {
            safe_string(
                condition.get(
                    "name"
                )
            )
            for condition
            in rule.get(
                "conditions",
                []
            )
            if isinstance(
                condition,
                dict,
            )
        }

        for predicate in predicates:

            name = (
                predicate[
                    "name"
                ]
            )

            condition_type = (
                predicate[
                    "type"
                ]
            )

            if name in existing_names:

                reused.append(
                    {
                        "clause_index": (
                            clause_index
                        ),

                        "name": (
                            name
                        ),
                    }
                )

                continue

            condition = (
                resolve_branch_condition(
                    name=name,
                    condition_type=condition_type,
                    site_zone=site_zone,
                    site_registry=site_registry,
                )
            )

            condition[
                "detector_confidence"
            ] = (
                predicate.get(
                    "confidence"
                )
            )

            rule.setdefault(
                "conditions",
                []
            ).append(
                condition
            )

            existing_names.add(
                name
            )

            added.append(
                {
                    "clause_index": (
                        clause_index
                    ),

                    **condition,
                }
            )

            touched.add(
                clause_index
            )

        refresh_rule(
            rule
        )

    return {
        "selected_count": (
            len(
                selected
            )
        ),

        "added": (
            added
        ),

        "reused": (
            reused
        ),

        "touched_clause_indexes": (
            sorted(
                touched
            )
        ),
    }


# ============================================================
# apply SITE registry globally
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

            previous = (
                condition.get(
                    "state"
                )
            )

            if (
                previous
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
                        previous
                    ),

                    "after": (
                        resolved[
                            "state"
                        ]
                    ),
                }
            )

            changed = True

        if changed:

            refresh_rule(
                rule
            )

    return repairs


# ============================================================
# inject PROJECT / PROCEDURE
# ============================================================

def inject_inputs(
    rules: List[Dict[str, Any]],
    project_input: Dict[str, str],
    procedure_input: Dict[str, str],
) -> Dict[str, Any]:

    touched_rules = []

    changed_rules = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        before = (
            rule.get(
                "applicability"
            )
        )

        matched = []

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

            state = None

            if (
                condition_type
                == "PROJECT"
                and name
                in project_input
            ):

                state = (
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

                state = (
                    procedure_input[
                        name
                    ]
                )

            if state is None:
                continue

            previous = (
                condition.get(
                    "state"
                )
            )

            condition[
                "state"
            ] = (
                state
            )

            condition[
                "confidence"
            ] = (
                "USER_DECLARED"
            )

            condition[
                "source"
            ] = (
                "CLEAN_PIPELINE_DYNAMIC_INPUT"
            )

            matched.append(
                {
                    "name": (
                        name
                    ),

                    "type": (
                        condition_type
                    ),

                    "before": (
                        previous
                    ),

                    "after": (
                        state
                    ),
                }
            )

        if not matched:
            continue

        refresh_rule(
            rule
        )

        touched_rules.append(
            {
                "clause_index": (
                    rule.get(
                        "clause_index"
                    )
                ),

                "conditions": (
                    matched
                ),
            }
        )

        if (
            before
            != rule.get(
                "applicability"
            )
        ):

            changed_rules.append(
                {
                    "clause_index": (
                        rule.get(
                            "clause_index"
                        )
                    ),

                    "rule_title": (
                        rule.get(
                            "rule_title"
                        )
                    ),

                    "before": (
                        before
                    ),

                    "after": (
                        rule.get(
                            "applicability"
                        )
                    ),
                }
            )

    return {
        "touched_rules": (
            touched_rules
        ),

        "changed_rules": (
            changed_rules
        ),
    }


# ============================================================
# numeric guard
# ============================================================

def apply_numeric_guards(
    rules: List[Dict[str, Any]],
    guards: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:

    active = []

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

        active.append(
            rule
        )

    for rule in active:

        index = int(
            rule.get(
                "clause_index"
            )
        )

        guard = (
            guards.get(
                index
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
                        index
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
        "active": active,
        "excluded": excluded,
        "retained": retained,
    }


# ============================================================
# remaining input
# ============================================================

def aggregate_inputs(
    rules: List[Dict[str, Any]],
) -> Dict[str, Any]:

    project = Counter()
    procedure = Counter()

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

                project[
                    name
                ] += 1

            elif condition_type == "PROCEDURE":

                procedure[
                    name
                ] += 1

    return {
        "project": (
            dict(
                project
            )
        ),

        "procedure": (
            dict(
                procedure
            )
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    validate_inputs(
        PROJECT_INPUT,
        "PROJECT",
    )

    validate_inputs(
        PROCEDURE_INPUT,
        "PROCEDURE",
    )

    # ========================================================
    # load
    # ========================================================

    site_complete = load_json(
        SITE_COMPLETE_PATH
    )

    branch_probe = load_json(
        BRANCH_PROBE_PATH
    )

    downtown = load_json(
        SEOUL_DOWNTOWN_PATH
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

    base_numeric = load_json(
        BASE_NUMERIC_PATH
    )

    # ========================================================
    # CLEAN SOURCE
    # ========================================================

    rules = copy.deepcopy(
        site_complete.get(
            "rules",
            []
        )
    )

    baseline_counter = Counter(
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
    # site zone
    # ========================================================

    site_zone = (
        base_numeric.get(
            "site_zone"
        )
    )

    # ========================================================
    # SITE registry
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

    # ========================================================
    # branch-local predicate expansion
    # ========================================================

    branch_result = (
        apply_branch_predicates(
            rules=rules,
            high_candidates=branch_probe.get(
                "high_priority_missing",
                [],
            ),
            site_zone=site_zone,
            site_registry=site_registry,
        )
    )

    after_branch_counter = Counter(
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
    # global SITE registry
    # ========================================================

    site_repairs = (
        apply_site_registry(
            rules,
            site_registry,
        )
    )

    # ========================================================
    # dynamic input — FIRST TIME
    # ========================================================

    injection = (
        inject_inputs(
            rules=rules,
            project_input=PROJECT_INPUT,
            procedure_input=PROCEDURE_INPUT,
        )
    )

    final_counter = Counter(
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
    # verified numeric guards
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

    guards = {

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

    numeric_result = (
        apply_numeric_guards(
            rules,
            guards,
        )
    )

    # ========================================================
    # direct relaxation
    # ========================================================

    DIRECT_RELAXATION_INDEXES = {
        4,
        189,
        205,
    }

    retained_direct = [
        rule
        for rule
        in numeric_result[
            "retained"
        ]
        if int(
            rule.get(
                "clause_index"
            )
        )
        in DIRECT_RELAXATION_INDEXES
    ]

    # ========================================================
    # base regulation
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

    if retained_direct:

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
    # remaining inputs
    # ========================================================

    remaining_inputs = (
        aggregate_inputs(
            rules
        )
    )

    # ========================================================
    # external history
    # ========================================================

    historical_dependency = (
        site_complete.get(
            "historical_dependency",
            {}
        )
    )

    # ========================================================
    # transitions
    # ========================================================

    transitions = Counter(
        (
            item[
                "before"
            ],
            item[
                "after"
            ],
        )

        for item
        in injection[
            "changed_rules"
        ]
    )

    # ========================================================
    # validation
    # ========================================================

    excluded_indexes = {
        item[
            "clause_index"
        ]
        for item
        in numeric_result[
            "excluded"
        ]
    }

    validations = {

        "clean baseline rules 314": (
            len(
                rules
            )
            == 314
        ),

        "baseline APPLICABLE 58": (
            baseline_counter[
                "APPLICABLE"
            ]
            == 58
        ),

        "baseline NOT_APPLICABLE 211": (
            baseline_counter[
                "NOT_APPLICABLE"
            ]
            == 211
        ),

        "baseline CONDITIONAL 43": (
            baseline_counter[
                "CONDITIONAL"
            ]
            == 43
        ),

        "baseline UNKNOWN 2": (
            baseline_counter[
                "UNKNOWN"
            ]
            == 2
        ),

        "branch predicates added": (
            len(
                branch_result[
                    "added"
                ]
            )
            > 0
        ),

        "dynamic touched > 0": (
            len(
                injection[
                    "touched_rules"
                ]
            )
            > 0
        ),

        "dynamic changes > 0": (
            len(
                injection[
                    "changed_rules"
                ]
            )
            > 0
        ),

        "CONDITIONAL -> APPLICABLE exists": (
            transitions[
                (
                    "CONDITIONAL",
                    "APPLICABLE",
                )
            ]
            > 0
        ),

        "clause4 excluded": (
            4
            in excluded_indexes
        ),

        "clause189 excluded": (
            189
            in excluded_indexes
        ),

        "no direct relaxation": (
            len(
                retained_direct
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
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "input": {
            "project": (
                PROJECT_INPUT
            ),

            "procedure": (
                PROCEDURE_INPUT
            ),
        },

        "baseline": (
            dict(
                baseline_counter
            )
        ),

        "branch_overlay": {
            "selected_count": (
                branch_result[
                    "selected_count"
                ]
            ),

            "added_condition_count": (
                len(
                    branch_result[
                        "added"
                    ]
                )
            ),

            "added_conditions": (
                branch_result[
                    "added"
                ]
            ),

            "after_branch": (
                dict(
                    after_branch_counter
                )
            ),
        },

        "site_registry": (
            site_registry
        ),

        "site_repairs": (
            site_repairs
        ),

        "dynamic_injection": {
            "touched_rule_count": (
                len(
                    injection[
                        "touched_rules"
                    ]
                )
            ),

            "changed_rule_count": (
                len(
                    injection[
                        "changed_rules"
                    ]
                )
            ),

            "transitions": {
                f"{before} -> {after}": (
                    count
                )

                for (
                    before,
                    after
                ), count
                in transitions.items()
            },

            "changed_rules": (
                injection[
                    "changed_rules"
                ]
            ),
        },

        "final_rule_summary": (
            dict(
                final_counter
            )
        ),

        "numeric": {
            "active_before_guard": (
                len(
                    numeric_result[
                        "active"
                    ]
                )
            ),

            "excluded_count": (
                len(
                    numeric_result[
                        "excluded"
                    ]
                )
            ),

            "excluded": (
                numeric_result[
                    "excluded"
                ]
            ),

            "retained_count": (
                len(
                    numeric_result[
                        "retained"
                    ]
                )
            ),

            "retained_clause_indexes": [
                rule.get(
                    "clause_index"
                )
                for rule
                in numeric_result[
                    "retained"
                ]
            ],

            "direct_relaxation_count": (
                len(
                    retained_direct
                )
            ),

            "resolution": (
                numeric_resolution
            ),

            "building_coverage_ratio": (
                confirmed_bcr
            ),

            "floor_area_ratio": (
                confirmed_far
            ),
        },

        "remaining_inputs": (
            remaining_inputs
        ),

        "external_dependency": (
            historical_dependency
        ),

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
        "Clean baseline:",
        dict(
            baseline_counter
        ),
    )

    print()

    print(
        "Branch conditions added:",
        len(
            branch_result[
                "added"
            ]
        ),
    )

    print(
        "After branch:",
        dict(
            after_branch_counter
        ),
    )

    print()

    print(
        "Dynamic touched:",
        len(
            injection[
                "touched_rules"
            ]
        ),
    )

    print(
        "Dynamic changed:",
        len(
            injection[
                "changed_rules"
            ]
        ),
    )

    print(
        "Transitions:",
        {
            f"{before} -> {after}": count

            for (
                before,
                after
            ), count
            in transitions.items()
        },
    )

    print()

    print(
        "Final:",
        dict(
            final_counter
        ),
    )

    print()

    print(
        "Numeric active:",
        len(
            numeric_result[
                "active"
            ]
        ),
    )

    print(
        "Numeric excluded:",
        len(
            numeric_result[
                "excluded"
            ]
        ),
    )

    print(
        "Numeric retained:",
        len(
            numeric_result[
                "retained"
            ]
        ),
    )

    print()

    print(
        "Direct relaxation:",
        len(
            retained_direct
        ),
    )

    print(
        "Numeric resolution:",
        numeric_resolution,
    )

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