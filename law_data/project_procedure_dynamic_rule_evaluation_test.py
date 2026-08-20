# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-4A
PROJECT / PROCEDURE Dynamic Rule Evaluation

목표
======================================================================
SITE 판정이 완료된 상태에서 PROJECT / PROCEDURE 입력을 주입하여
Rule Evaluation을 동적으로 재계산한다.

기준 snapshot
======================================================================
site_rule_evaluation_site_complete.json

SITE condition은 더 이상 재판정하지 않는다.

입력 대상
======================================================================
PROJECT:
- 공개공지
- 공공시설제공
- 공공주택
- 공동주택
- 기부채납
- 대학
- 사회복지시설
- 임대주택
- 종합의료시설
- 주거복합
- 한옥
- 기타 branch-local PROJECT predicate

PROCEDURE:
- 도시계획위원회심의
- 시장정비사업심의

입력 state
======================================================================
TRUE
FALSE
UNKNOWN
UNSET

정책
======================================================================
FALSE   -> 해당 필수조건 조문 NOT_APPLICABLE
UNKNOWN -> UNKNOWN
UNSET   -> CONDITIONAL
TRUE    -> 조건 충족

SITE_HISTORY external dependency는 그대로 유지한다.
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-4A "
    "PROJECT PROCEDURE dynamic rule evaluation"
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

INPUT_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_site_complete.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "project_procedure_dynamic_rule_evaluation.json"
)


# ============================================================
# TEST SCENARIO
#
# 우선 engine 검증을 위한 scenario.
# 이후 실제 사용자 입력 object로 교체한다.
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

def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


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


# ============================================================
# input validation
# ============================================================

def validate_inputs(
    data: Dict[str, str],
    input_type: str,
) -> None:

    for name, state in data.items():

        if state not in VALID_STATES:

            raise ValueError(
                f"{input_type} 입력 오류: "
                f"{name}={state}"
            )


# ============================================================
# condition refresh
# ============================================================

def refresh_condition_groups(
    rule: Dict[str, Any],
) -> None:

    conditions = rule.get(
        "conditions",
        [],
    )

    rule["required_inputs"] = [
        item
        for item in conditions
        if isinstance(item, dict)
        and item.get("state") == "UNSET"
    ]

    rule["blocked_by"] = [
        item
        for item in conditions
        if isinstance(item, dict)
        and item.get("state") == "FALSE"
    ]

    rule["unknown_by"] = [
        item
        for item in conditions
        if isinstance(item, dict)
        and item.get("state") == "UNKNOWN"
    ]


# ============================================================
# applicability
# ============================================================

def recalculate_applicability(
    rule: Dict[str, Any],
) -> Dict[str, str]:

    blocked = rule.get(
        "blocked_by",
        [],
    )

    unknown = rule.get(
        "unknown_by",
        [],
    )

    required = rule.get(
        "required_inputs",
        [],
    )

    # --------------------------------------------------------
    # FALSE
    # --------------------------------------------------------

    if blocked:

        return {
            "applicability": (
                "NOT_APPLICABLE"
            ),

            "reason": (
                "필수조건 FALSE: "
                + ", ".join(
                    safe_string(
                        item.get("name")
                    )
                    for item in blocked
                )
            ),
        }

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    if unknown:

        return {
            "applicability": (
                "UNKNOWN"
            ),

            "reason": (
                "필수조건 미확정: "
                + ", ".join(
                    safe_string(
                        item.get("name")
                    )
                    for item in unknown
                )
            ),
        }

    # --------------------------------------------------------
    # UNSET
    # --------------------------------------------------------

    if required:

        return {
            "applicability": (
                "CONDITIONAL"
            ),

            "reason": (
                "추가 입력 필요: "
                + ", ".join(
                    safe_string(
                        item.get("name")
                    )
                    for item in required
                )
            ),
        }

    # --------------------------------------------------------
    # zone blocker
    # --------------------------------------------------------

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
# numeric state refresh
# ============================================================

def refresh_numeric_effect(
    rule: Dict[str, Any],
) -> None:

    numeric_effect = rule.get(
        "numeric_effect"
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
        "status": status,

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
# inject
# ============================================================

def inject_inputs(
    rules: List[Dict[str, Any]],
    project_input: Dict[str, str],
    procedure_input: Dict[str, str],
) -> Dict[str, Any]:

    touched = []

    changes = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        previous_applicability = (
            rule.get(
                "applicability"
            )
        )

        matched_conditions = []

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
                condition_type == "PROJECT"
                and name in project_input
            ):

                new_state = (
                    project_input[
                        name
                    ]
                )

            elif (
                condition_type == "PROCEDURE"
                and name in procedure_input
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
            ] = new_state

            condition[
                "source"
            ] = (
                "DYNAMIC_USER_INPUT"
            )

            condition[
                "previous_state"
            ] = (
                previous_state
            )

            condition[
                "confidence"
            ] = (
                "USER_DECLARED"
            )

            matched_conditions.append(
                {
                    "name": name,
                    "type": condition_type,
                    "previous_state": (
                        previous_state
                    ),
                    "new_state": (
                        new_state
                    ),
                }
            )

        if not matched_conditions:
            continue

        refresh_condition_groups(
            rule
        )

        result = recalculate_applicability(
            rule
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

        touched.append(
            {
                "clause_index": (
                    rule.get(
                        "clause_index"
                    )
                ),

                "conditions": (
                    matched_conditions
                ),
            }
        )

        if (
            previous_applicability
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
                        previous_applicability
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
# remaining input aggregation
# ============================================================

def aggregate_remaining_inputs(
    rules: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:

    project_counter = Counter()
    procedure_counter = Counter()

    for rule in rules:

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
                "name": name,
                "affected_clause_count": count,
                "state": "UNSET",
            }

            for name, count
            in project_counter.most_common()
        ],

        "procedure": [
            {
                "name": name,
                "affected_clause_count": count,
                "state": "UNSET",
            }

            for name, count
            in procedure_counter.most_common()
        ],
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

    snapshot = load_json(
        INPUT_PATH
    )

    rules = copy.deepcopy(
        snapshot.get(
            "rules",
            [],
        )
    )

    before = Counter(
        rule.get(
            "applicability"
        )
        for rule in rules
        if isinstance(
            rule,
            dict,
        )
    )

    # ========================================================
    # inject
    # ========================================================

    injection = inject_inputs(
        rules,
        PROJECT_INPUT,
        PROCEDURE_INPUT,
    )

    after = Counter(
        rule.get(
            "applicability"
        )
        for rule in rules
        if isinstance(
            rule,
            dict,
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
            "changes"
        ]
    )

    # ========================================================
    # remaining input
    # ========================================================

    remaining_inputs = (
        aggregate_remaining_inputs(
            rules
        )
    )

    # ========================================================
    # numeric active candidates
    # ========================================================

    active_numeric = []

    conditional_numeric = []

    unknown_numeric = []

    for rule in rules:

        current = rule.get(
            "current_numeric_effect",
            {}
        )

        status = current.get(
            "status"
        )

        if status == "ACTIVE_CANDIDATE":

            active_numeric.append(
                rule.get(
                    "clause_index"
                )
            )

        elif status == "POTENTIAL_CONDITIONAL":

            conditional_numeric.append(
                rule.get(
                    "clause_index"
                )
            )

        elif status == "POTENTIAL_UNKNOWN":

            unknown_numeric.append(
                rule.get(
                    "clause_index"
                )
            )

    # ========================================================
    # confirmed regulation
    #
    # 이번 단계는 applicability 주입 검증 단계.
    # numeric 재해석/stacking은 다음 단계에서 수행.
    # ========================================================

    confirmed_regulation = (
        snapshot.get(
            "confirmed_regulation",
            {}
        )
    )

    confirmed_bcr = (
        confirmed_regulation.get(
            "building_coverage_ratio",
            {},
        ).get(
            "value"
        )
    )

    confirmed_far = (
        confirmed_regulation.get(
            "floor_area_ratio",
            {},
        ).get(
            "value"
        )
    )

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "rules 314": (
            len(
                rules
            )
            == 314
        ),

        "SITE stage ready": (
            snapshot.get(
                "site_stage",
                {},
            ).get(
                "rule_engine_ready"
            )
            is True
        ),

        "공동주택 TRUE injected": (
            any(
                condition[
                    "name"
                ]
                == "공동주택"
                and condition[
                    "new_state"
                ]
                == "TRUE"

                for touched
                in injection[
                    "touched"
                ]

                for condition
                in touched[
                    "conditions"
                ]
            )
        ),

        "도시계획위원회심의 TRUE injected": (
            any(
                condition[
                    "name"
                ]
                == "도시계획위원회심의"
                and condition[
                    "new_state"
                ]
                == "TRUE"

                for touched
                in injection[
                    "touched"
                ]

                for condition
                in touched[
                    "conditions"
                ]
            )
        ),

        "CONDITIONAL 감소 또는 유지": (
            after[
                "CONDITIONAL"
            ]
            <= before[
                "CONDITIONAL"
            ]
        ),

        "UNKNOWN 2 유지": (
            after[
                "UNKNOWN"
            ]
            == 2
        ),

        "confirmed BCR 50 유지": (
            confirmed_bcr
            == 50.0
        ),

        "confirmed FAR 250 유지": (
            confirmed_far
            == 250.0
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

        "site": (
            snapshot.get(
                "site",
                {}
            )
        ),

        "input": {
            "project": (
                PROJECT_INPUT
            ),

            "procedure": (
                PROCEDURE_INPUT
            ),
        },

        "before": {
            "applicable": (
                before[
                    "APPLICABLE"
                ]
            ),

            "not_applicable": (
                before[
                    "NOT_APPLICABLE"
                ]
            ),

            "conditional": (
                before[
                    "CONDITIONAL"
                ]
            ),

            "unknown": (
                before[
                    "UNKNOWN"
                ]
            ),
        },

        "after": {
            "applicable": (
                after[
                    "APPLICABLE"
                ]
            ),

            "not_applicable": (
                after[
                    "NOT_APPLICABLE"
                ]
            ),

            "conditional": (
                after[
                    "CONDITIONAL"
                ]
            ),

            "unknown": (
                after[
                    "UNKNOWN"
                ]
            ),
        },

        "injection": {
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
                f"{before_state} -> {after_state}": (
                    count
                )

                for (
                    before_state,
                    after_state
                ), count
                in transitions.items()
            },

            "changed_rules": (
                injection[
                    "changes"
                ]
            ),
        },

        "remaining_inputs": (
            remaining_inputs
        ),

        "numeric_state": {
            "active_candidate_count": (
                len(
                    active_numeric
                )
            ),

            "conditional_candidate_count": (
                len(
                    conditional_numeric
                )
            ),

            "unknown_candidate_count": (
                len(
                    unknown_numeric
                )
            ),

            "active_clause_indexes": (
                active_numeric
            ),

            "conditional_clause_indexes": (
                conditional_numeric
            ),

            "unknown_clause_indexes": (
                unknown_numeric
            ),
        },

        "confirmed_regulation": (
            confirmed_regulation
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
        "Input PROJECT:",
        PROJECT_INPUT,
    )

    print(
        "Input PROCEDURE:",
        PROCEDURE_INPUT,
    )

    print()

    print(
        "Before:",
        {
            "APPLICABLE": (
                before[
                    "APPLICABLE"
                ]
            ),
            "NOT_APPLICABLE": (
                before[
                    "NOT_APPLICABLE"
                ]
            ),
            "CONDITIONAL": (
                before[
                    "CONDITIONAL"
                ]
            ),
            "UNKNOWN": (
                before[
                    "UNKNOWN"
                ]
            ),
        },
    )

    print(
        "After:",
        {
            "APPLICABLE": (
                after[
                    "APPLICABLE"
                ]
            ),
            "NOT_APPLICABLE": (
                after[
                    "NOT_APPLICABLE"
                ]
            ),
            "CONDITIONAL": (
                after[
                    "CONDITIONAL"
                ]
            ),
            "UNKNOWN": (
                after[
                    "UNKNOWN"
                ]
            ),
        },
    )

    print()

    print(
        "Touched rules:",
        len(
            injection[
                "touched"
            ]
        ),
    )

    print(
        "Changed rules:",
        len(
            injection[
                "changes"
            ]
        ),
    )

    print(
        "Transitions:",
        {
            f"{before_state} -> {after_state}": count

            for (
                before_state,
                after_state
            ), count
            in transitions.items()
        },
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
        "Active numeric:",
        len(
            active_numeric
        ),
    )

    print(
        "Conditional numeric:",
        len(
            conditional_numeric
        ),
    )

    print(
        "Unknown numeric:",
        len(
            unknown_numeric
        ),
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