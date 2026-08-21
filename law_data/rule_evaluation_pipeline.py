# -*- coding: utf-8 -*-

"""
Reusable Rule Evaluation Pipeline

목표
======================================================================
깨끗한 SITE baseline에서 시작하여 다음 순서로 rule evaluation을 수행한다.

1. SITE baseline load
2. branch-local predicate detection
3. branch-local condition 추가
4. SITE resolution registry 적용
5. PROJECT / PROCEDURE 입력 적용
6. applicability 재평가
7. numeric-specific verified guard 적용
8. numeric result 확정
9. remaining input / external dependency 반환

중요
======================================================================
이 모듈은 테스트 output JSON의 "판정결과" 자체를 source rule set으로
사용하지 않는다.

항상:
    site_rule_evaluation_site_complete.json

을 clean baseline으로 사용한다.

branch-local predicate는:
    rule_condition_registry.py

에서 직접 탐지한다.
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional


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


# ============================================================
# local module
# ============================================================

try:
    from .rule_condition_registry import (
        build_branch_condition,
        find_missing_branch_predicates,
    )

except ImportError:
    from rule_condition_registry import (
        build_branch_condition,
        find_missing_branch_predicates,
    )


# ============================================================
# VALID STATES
# ============================================================

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


def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip()


def validate_profile(
    profile: Dict[str, str],
    profile_type: str,
) -> None:

    for name, state in profile.items():

        if state not in VALID_STATES:

            raise ValueError(
                f"{profile_type} 입력 오류: "
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
            [],
        )
    )

    rule[
        "required_inputs"
    ] = [
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

    rule[
        "blocked_by"
    ] = [
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

    rule[
        "unknown_by"
    ] = [
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
            [],
        )
    )

    unknown = (
        rule.get(
            "unknown_by",
            [],
        )
    )

    required = (
        rule.get(
            "required_inputs",
            [],
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

        status = "INACTIVE"

    elif applicability == "CONDITIONAL":

        status = "POTENTIAL_CONDITIONAL"

    elif applicability == "UNKNOWN":

        status = "POTENTIAL_UNKNOWN"

    else:

        status = "ACTIVE_CANDIDATE"

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
# SITE registry
# ============================================================

def build_site_registry(
    downtown_data: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:

    downtown_condition = (
        downtown_data.get(
            "condition",
            {},
        )
    )

    return {

        "서울도심": {
            "type": (
                "SITE"
            ),

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


# ============================================================
# branch-local predicates
# ============================================================

def apply_branch_local_conditions(
    rules: List[Dict[str, Any]],
    site_zone: str,
    site_registry: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    added = []

    reused = []

    touched = set()

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

        missing = (
            find_missing_branch_predicates(
                rule
            )
        )

        selected = [
            item
            for item
            in missing
            if (
                item.get(
                    "branch_priority"
                )
                == "HIGH"
                and item.get(
                    "direct_in_clause_text"
                )
                is True
            )
        ]

        if not selected:
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
                [],
            )

            if isinstance(
                condition,
                dict,
            )
        }

        for predicate in selected:

            name = (
                predicate[
                    "name"
                ]
            )

            if name in existing_names:

                reused.append(
                    {
                        "clause_index": (
                            rule.get(
                                "clause_index"
                            )
                        ),

                        "name": (
                            name
                        ),
                    }
                )

                continue

            condition = (
                build_branch_condition(
                    predicate=predicate,
                    site_zone=site_zone,
                    site_registry=site_registry,
                )
            )

            rule.setdefault(
                "conditions",
                []
            ).append(
                condition
            )

            added.append(
                {
                    "clause_index": (
                        rule.get(
                            "clause_index"
                        )
                    ),

                    **condition,
                }
            )

            existing_names.add(
                name
            )

            touched.add(
                int(
                    rule.get(
                        "clause_index"
                    )
                )
            )

        refresh_rule(
            rule
        )

    return {
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
# global SITE registry
# ============================================================

def apply_site_registry(
    rules: List[Dict[str, Any]],
    site_registry: Dict[str, Dict[str, Any]],
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
                site_registry.get(
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

        if changed:

            refresh_rule(
                rule
            )

    return repairs


# ============================================================
# PROJECT / PROCEDURE
# ============================================================

def inject_profiles(
    rules: List[Dict[str, Any]],
    project_profile: Dict[str, str],
    procedure_profile: Dict[str, str],
) -> Dict[str, Any]:

    touched = []

    changes = []

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

            new_state = None

            if (
                condition_type
                == "PROJECT"
                and name
                in project_profile
            ):

                new_state = (
                    project_profile[
                        name
                    ]
                )

            elif (
                condition_type
                == "PROCEDURE"
                and name
                in procedure_profile
            ):

                new_state = (
                    procedure_profile[
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
                "confidence"
            ] = (
                "USER_DECLARED"
            )

            condition[
                "source"
            ] = (
                "RULE_EVALUATION_PIPELINE_INPUT"
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
                        previous_state
                    ),

                    "after": (
                        new_state
                    ),
                }
            )

        if not matched:
            continue

        refresh_rule(
            rule
        )

        touched.append(
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

            changes.append(
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
        "touched": touched,
        "changes": changes,
    }


# ============================================================
# numeric guard registry
# ============================================================

def build_numeric_guard_registry(
    upper_data: Dict[str, Any],
    disaster_data: Dict[str, Any],
    clause_205_data: Dict[str, Any],
    clause_250_data: Dict[str, Any],
) -> Dict[int, Dict[str, Any]]:

    clause_4_resolution = (
        upper_data.get(
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
        disaster_data.get(
            "current_condition",
            {},
        )
    )

    clause_189_resolution = (
        disaster_data.get(
            "numeric_effect",
            {},
        ).get(
            "resolution"
        )
    )

    clause_205_resolution = (
        clause_205_data.get(
            "resolution",
            {},
        ).get(
            "applicability"
        )
    )

    clause_250_resolution = (
        clause_250_data.get(
            "resolution",
            {},
        )
    )

    return {

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


# ============================================================
# numeric guard
# ============================================================

def apply_numeric_guards(
    rules: List[Dict[str, Any]],
    guards: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:

    active = []

    retained = []

    excluded = []

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
        "active": active,
        "excluded": excluded,
        "retained": retained,
    }


# ============================================================
# remaining inputs
# ============================================================

def aggregate_remaining_inputs(
    rules: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:

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
            in project.most_common()
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
            in procedure.most_common()
        ],
    }


# ============================================================
# main API
# ============================================================

def evaluate_site_rules(
    project_profile: Optional[
        Dict[str, str]
    ] = None,
    procedure_profile: Optional[
        Dict[str, str]
    ] = None,
) -> Dict[str, Any]:

    project_profile = (
        project_profile
        or {}
    )

    procedure_profile = (
        procedure_profile
        or {}
    )

    validate_profile(
        project_profile,
        "PROJECT",
    )

    validate_profile(
        procedure_profile,
        "PROCEDURE",
    )

    # ========================================================
    # load source
    # ========================================================

    site_complete = load_json(
        SITE_COMPLETE_PATH
    )

    downtown_data = load_json(
        SEOUL_DOWNTOWN_PATH
    )

    upper_data = load_json(
        UPPER_BRANCH_PATH
    )

    disaster_data = load_json(
        DISASTER_PATH
    )

    clause_205_data = load_json(
        CLAUSE_205_PATH
    )

    clause_250_data = load_json(
        CLAUSE_250_PATH
    )

    base_numeric = load_json(
        BASE_NUMERIC_PATH
    )

    # ========================================================
    # CLEAN baseline
    # ========================================================

    rules = copy.deepcopy(
        site_complete.get(
            "rules",
            [],
        )
    )

    if len(rules) != 314:

        raise ValueError(
            f"rule count 오류: "
            f"{len(rules)}"
        )

    baseline = Counter(
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
    # registry
    # ========================================================

    site_registry = (
        build_site_registry(
            downtown_data
        )
    )

    # ========================================================
    # branch conditions
    # ========================================================

    branch_result = (
        apply_branch_local_conditions(
            rules=rules,
            site_zone=site_zone,
            site_registry=site_registry,
        )
    )

    after_branch = Counter(
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
    # site registry repair
    # ========================================================

    site_repairs = (
        apply_site_registry(
            rules,
            site_registry,
        )
    )

    # ========================================================
    # project / procedure
    # ========================================================

    injection = (
        inject_profiles(
            rules=rules,
            project_profile=project_profile,
            procedure_profile=procedure_profile,
        )
    )

    final_summary = Counter(
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
    # numeric guards
    # ========================================================

    numeric_guards = (
        build_numeric_guard_registry(
            upper_data=upper_data,
            disaster_data=disaster_data,
            clause_205_data=clause_205_data,
            clause_250_data=clause_250_data,
        )
    )

    numeric_guard_result = (
        apply_numeric_guards(
            rules,
            numeric_guards,
        )
    )

    # ========================================================
    # direct relaxation
    # ========================================================

    direct_relaxation_indexes = {
        4,
        189,
        205,
    }

    retained_direct = [
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
        in direct_relaxation_indexes
    ]

    # ========================================================
    # base numeric
    # ========================================================

    base_regulation = (
        base_numeric.get(
            "current_base_regulation",
            {},
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
            "changes"
        ]
    )

    # ========================================================
    # remaining
    # ========================================================

    remaining_inputs = (
        aggregate_remaining_inputs(
            rules
        )
    )

    # ========================================================
    # external dependency
    # ========================================================

    historical_dependency = (
        site_complete.get(
            "historical_dependency",
            {},
        )
    )

    # ========================================================
    # ready
    # ========================================================

    ready = (
        site_complete.get(
            "site_stage",
            {},
        ).get(
            "rule_engine_ready"
        )
        is True
        and numeric_resolution
        in {
            "BASE_VALUES_RETAINED",
            "RECALC_REQUIRED",
        }
    )

    # ========================================================
    # output
    # ========================================================

    return {

        "pipeline": {
            "ready": (
                ready
            ),

            "version": (
                "C-10-5C-2"
            ),
        },

        "input": {
            "project": (
                project_profile
            ),

            "procedure": (
                procedure_profile
            ),
        },

        "site": (
            site_complete.get(
                "site",
                {}
            )
        ),

        "site_zone": (
            site_zone
        ),

        "baseline": (
            dict(
                baseline
            )
        ),

        "branch_overlay": {
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
                    after_branch
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
                        "touched"
                    ]
                )
            ),

            "changed_rule_count": (
                len(
                    injection[
                        "changes"
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

            "changes": (
                injection[
                    "changes"
                ]
            ),
        },

        "rule_summary": (
            dict(
                final_summary
            )
        ),

        "numeric": {
            "active_before_guard": (
                len(
                    numeric_guard_result[
                        "active"
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

        "external_dependencies": {
            "historical": (
                historical_dependency
            ),
        },

        "rules": (
            rules
        ),
    }