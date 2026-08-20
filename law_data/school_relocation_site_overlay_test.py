# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-3B-6
학교이적지 FALSE overlay

입력
======================================================================
site_rule_evaluation_density_overlay.json
    - 서울도심 FALSE
    - 개발밀도관리구역 FALSE
      까지 반영된 최신 Rule Evaluation

school_relocation_site_candidate_resolution.json
    - 학교이적지 FALSE / HIGH

목표
======================================================================
1. 학교이적지 condition을 UNKNOWN -> FALSE로 overlay
2. 해당 7개 조문의 applicability 재평가
3. numeric effect 상태 갱신
4. unresolved SITE condition 재집계
5. 마지막 미해결 조건이
   도시지역편입해제구역 하나만 남는지 확인
6. BCR/FAR 50/250 유지 검증
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-3B-6 "
    "학교이적지 FALSE overlay"
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

INPUT_RULE_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_density_overlay.json"
)

RESOLUTION_PATH = (
    OUTPUT_DIR
    / "school_relocation_site_candidate_resolution.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_school_overlay.json"
)


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

    if (
        rule.get("zone_relevance")
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
# numeric state
# ============================================================

def refresh_numeric_effect(
    rule: Dict[str, Any],
) -> None:

    numeric_effect = rule.get(
        "numeric_effect"
    )

    if not numeric_effect:
        return

    applicability = rule.get(
        "applicability"
    )

    if applicability == (
        "NOT_APPLICABLE"
    ):
        status = "INACTIVE"

    elif applicability == (
        "CONDITIONAL"
    ):
        status = "POTENTIAL_CONDITIONAL"

    elif applicability == (
        "UNKNOWN"
    ):
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
# aggregators
# ============================================================

def build_unresolved_site_conditions(
    rules: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    counter = Counter()

    for rule in rules:

        for condition in rule.get(
            "unknown_by",
            [],
        ):

            if not isinstance(
                condition,
                dict,
            ):
                continue

            condition_type = safe_string(
                condition.get(
                    "type"
                )
            )

            if condition_type not in {
                "SITE",
                "SITE_HISTORY",
            }:
                continue

            name = safe_string(
                condition.get(
                    "name"
                )
            )

            if name:
                counter[name] += 1

    return [
        {
            "name": name,
            "affected_clause_count": count,
            "site_state": "UNKNOWN",
        }
        for name, count
        in counter.most_common()
    ]


def build_required_inputs(
    rules: List[Dict[str, Any]],
    condition_type: str,
) -> List[Dict[str, Any]]:

    counter = Counter()

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

            if safe_string(
                condition.get(
                    "type"
                )
            ) != condition_type:
                continue

            name = safe_string(
                condition.get(
                    "name"
                )
            )

            if name:
                counter[name] += 1

    return [
        {
            "name": name,
            "affected_clause_count": count,
            "profile_state": "UNSET",
        }
        for name, count
        in counter.most_common()
    ]


# ============================================================
# main
# ============================================================

def main() -> int:

    snapshot = load_json(
        INPUT_RULE_PATH
    )

    resolution = load_json(
        RESOLUTION_PATH
    )

    current_resolution = (
        resolution.get(
            "current_resolution",
            {},
        )
    )

    status = safe_string(
        current_resolution.get(
            "status"
        )
    )

    confidence = safe_string(
        current_resolution.get(
            "confidence"
        )
    )

    reason = safe_string(
        current_resolution.get(
            "reason"
        )
    )

    if (
        status != "FALSE"
        or confidence != "HIGH"
    ):

        raise ValueError(
            "학교이적지 FALSE/HIGH resolution이 아님"
        )

    rules = copy.deepcopy(
        snapshot.get(
            "rules",
            [],
        )
    )

    # ========================================================
    # overlay
    # ========================================================

    touched_rules = 0
    changed_rules = []

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

        matched = False

        for condition in rule.get(
            "conditions",
            [],
        ):

            if not isinstance(
                condition,
                dict,
            ):
                continue

            if safe_string(
                condition.get(
                    "name"
                )
            ) != "학교이적지":
                continue

            previous_state = (
                condition.get(
                    "state"
                )
            )

            condition[
                "state"
            ] = "FALSE"

            condition[
                "confidence"
            ] = "HIGH"

            condition[
                "source"
            ] = (
                "SCHOOL_RELOCATION_SITE_CANDIDATE_RESOLUTION"
            )

            condition[
                "resolution_reason"
            ] = reason

            condition[
                "previous_state"
            ] = previous_state

            matched = True

        if not matched:
            continue

        touched_rules += 1

        refresh_condition_groups(
            rule
        )

        recalculated = (
            recalculate_applicability(
                rule
            )
        )

        rule[
            "applicability"
        ] = (
            recalculated[
                "applicability"
            ]
        )

        rule[
            "applicability_reason"
        ] = (
            recalculated[
                "reason"
            ]
        )

        refresh_numeric_effect(
            rule
        )

        if (
            previous_applicability
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

                    "previous_applicability": (
                        previous_applicability
                    ),

                    "new_applicability": (
                        rule.get(
                            "applicability"
                        )
                    ),
                }
            )

    # ========================================================
    # summary
    # ========================================================

    applicability_counter = Counter(
        rule.get(
            "applicability"
        )
        for rule in rules
        if isinstance(rule, dict)
    )

    unresolved_site = (
        build_unresolved_site_conditions(
            rules
        )
    )

    project_inputs = (
        build_required_inputs(
            rules,
            "PROJECT",
        )
    )

    procedure_inputs = (
        build_required_inputs(
            rules,
            "PROCEDURE",
        )
    )

    rules_requiring_input = sum(
        1
        for rule in rules
        if rule.get(
            "required_inputs"
        )
    )

    rules_with_unknown = sum(
        1
        for rule in rules
        if rule.get(
            "unknown_by"
        )
    )

    rules_with_blocker = sum(
        1
        for rule in rules
        if rule.get(
            "blocked_by"
        )
    )

    # ========================================================
    # regulation
    # ========================================================

    confirmed_regulation = (
        snapshot.get(
            "confirmed_regulation",
            {},
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
    # transitions
    # ========================================================

    transitions = Counter(
        (
            item[
                "previous_applicability"
            ],
            item[
                "new_applicability"
            ],
        )
        for item in changed_rules
    )

    # ========================================================
    # remaining condition
    # ========================================================

    remaining_names = {
        item["name"]
        for item in unresolved_site
    }

    # ========================================================
    # rule groups
    # ========================================================

    rule_groups = {

        "applicable_clause_indexes": [
            rule["clause_index"]
            for rule in rules
            if rule.get(
                "applicability"
            )
            == "APPLICABLE"
        ],

        "conditional_clause_indexes": [
            rule["clause_index"]
            for rule in rules
            if rule.get(
                "applicability"
            )
            == "CONDITIONAL"
        ],

        "unknown_clause_indexes": [
            rule["clause_index"]
            for rule in rules
            if rule.get(
                "applicability"
            )
            == "UNKNOWN"
        ],

        "not_applicable_clause_indexes": [
            rule["clause_index"]
            for rule in rules
            if rule.get(
                "applicability"
            )
            == "NOT_APPLICABLE"
        ],
    }

    # ========================================================
    # validations
    # ========================================================

    validations = {

        "rules 314": (
            len(rules)
            == 314
        ),

        "학교이적지 touched 7": (
            touched_rules
            == 7
        ),

        "학교이적지 unresolved 제거": (
            "학교이적지"
            not in remaining_names
        ),

        "도시지역편입해제구역 유지": (
            "도시지역편입해제구역"
            in remaining_names
        ),

        "unresolved SITE 1종": (
            len(
                unresolved_site
            )
            == 1
        ),

        "UNKNOWN 감소": (
            applicability_counter[
                "UNKNOWN"
            ]
            < 9
        ),

        "NOT_APPLICABLE 증가": (
            applicability_counter[
                "NOT_APPLICABLE"
            ]
            > 204
        ),

        "confirmed BCR 50": (
            confirmed_bcr
            == 50.0
        ),

        "confirmed FAR 250": (
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

        "confirmed_regulation": (
            confirmed_regulation
        ),

        "overlay": {
            "condition": (
                "학교이적지"
            ),

            "state": (
                "FALSE"
            ),

            "confidence": (
                "HIGH"
            ),

            "touched_rules": (
                touched_rules
            ),

            "changed_rules": (
                changed_rules
            ),

            "transitions": {
                f"{before} -> {after}": count
                for (
                    before,
                    after
                ), count
                in transitions.items()
            },
        },

        "rule_evaluation_summary": {
            "confirmed_building_coverage_ratio": (
                confirmed_bcr
            ),

            "confirmed_floor_area_ratio": (
                confirmed_far
            ),

            "total_clauses": (
                len(
                    rules
                )
            ),

            "applicable": (
                applicability_counter[
                    "APPLICABLE"
                ]
            ),

            "not_applicable": (
                applicability_counter[
                    "NOT_APPLICABLE"
                ]
            ),

            "conditional": (
                applicability_counter[
                    "CONDITIONAL"
                ]
            ),

            "unknown": (
                applicability_counter[
                    "UNKNOWN"
                ]
            ),

            "rules_requiring_input": (
                rules_requiring_input
            ),

            "rules_with_unknown_condition": (
                rules_with_unknown
            ),

            "rules_with_false_blocker": (
                rules_with_blocker
            ),
        },

        "input_requirements": {
            "project": (
                project_inputs
            ),

            "procedure": (
                procedure_inputs
            ),

            "unresolved_site_conditions": (
                unresolved_site
            ),
        },

        "rule_groups": (
            rule_groups
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
    # concise console
    # ========================================================

    print(
        "Overlay:",
        "학교이적지 -> FALSE",
    )

    print(
        "Touched rules:",
        touched_rules,
    )

    print(
        "Changed rules:",
        len(
            changed_rules
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
        "APPLICABLE:",
        applicability_counter[
            "APPLICABLE"
        ],
    )

    print(
        "NOT_APPLICABLE:",
        applicability_counter[
            "NOT_APPLICABLE"
        ],
    )

    print(
        "CONDITIONAL:",
        applicability_counter[
            "CONDITIONAL"
        ],
    )

    print(
        "UNKNOWN:",
        applicability_counter[
            "UNKNOWN"
        ],
    )

    print()

    print(
        "Unresolved SITE:",
        [
            (
                item["name"],
                item[
                    "affected_clause_count"
                ],
            )
            for item in unresolved_site
        ],
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