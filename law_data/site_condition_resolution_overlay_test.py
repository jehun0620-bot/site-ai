# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-3B-2
SITE condition resolution overlay

목표
======================================================================
기존 최종 Rule Evaluation Snapshot:

    site_rule_evaluation_final_snapshot.json

에 후속으로 확정된 SITE condition resolution을 overlay한다.

현재 overlay 대상
======================================================================
서울도심:
    UNKNOWN -> FALSE / HIGH

예상 영향
======================================================================
clause 208
    UNKNOWN -> NOT_APPLICABLE

전체 applicability:
    APPLICABLE      58 유지
    NOT_APPLICABLE 192 -> 193
    CONDITIONAL     43 유지
    UNKNOWN         21 -> 20

Unresolved SITE condition:
    4 -> 3

남는 항목:
- 개발밀도관리구역
- 학교이적지
- 도시지역편입해제구역

중요 정책
======================================================================
1. 기존 final snapshot을 직접 수정하지 않는다.
2. overlay 결과를 새 snapshot으로 생성한다.
3. FALSE condition 하나라도 존재하면 NOT_APPLICABLE.
4. UNKNOWN / UNSET 판정 우선순위는 기존 evaluator 정책 유지.
5. numeric confirmed BCR/FAR 50/250은 변경하지 않는다.
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-3B-2 "
    "SITE condition resolution overlay"
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

FINAL_RULE_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_final_snapshot.json"
)

SEOUL_DOWNTOWN_PATH = (
    OUTPUT_DIR
    / "seoul_downtown_condition_resolution.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_condition_overlay.json"
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
# applicability recalc
# ============================================================

def recalculate_applicability(
    rule: Dict[str, Any],
) -> Dict[str, Any]:

    conditions = rule.get(
        "conditions",
        [],
    )

    false_conditions = [
        item
        for item in conditions
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "state"
        )
        == "FALSE"
    ]

    unknown_conditions = [
        item
        for item in conditions
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "state"
        )
        == "UNKNOWN"
    ]

    unset_conditions = [
        item
        for item in conditions
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "state"
        )
        == "UNSET"
    ]

    # --------------------------------------------------------
    # FALSE 최우선
    # --------------------------------------------------------

    if false_conditions:

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
                    in false_conditions
                )
            ),
        }

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    if unknown_conditions:

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
                    in unknown_conditions
                )
            ),
        }

    # --------------------------------------------------------
    # UNSET
    # --------------------------------------------------------

    if unset_conditions:

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
                    in unset_conditions
                )
            ),
        }

    # --------------------------------------------------------
    # 기존 OTHER_ZONE 같은 선행 blocker 보존
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
# helper: rule condition groups
# ============================================================

def refresh_condition_groups(
    rule: Dict[str, Any],
) -> None:

    conditions = rule.get(
        "conditions",
        [],
    )

    rule[
        "required_inputs"
    ] = [
        item
        for item in conditions
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
        for item in conditions
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
        for item in conditions
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
# numeric current effect refresh
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

    effect_class = rule.get(
        "numeric_effect_class"
    )

    if applicability == (
        "NOT_APPLICABLE"
    ):

        status = (
            "INACTIVE"
        )

    elif applicability == (
        "CONDITIONAL"
    ):

        status = (
            "POTENTIAL_CONDITIONAL"
        )

    elif applicability == (
        "UNKNOWN"
    ):

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
            effect_class
        ),

        "semantic": (
            numeric_effect
        ),
    }


# ============================================================
# unresolved SITE aggregation
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

            if (
                condition_type
                not in {
                    "SITE",
                    "SITE_HISTORY",
                }
            ):
                continue

            name = safe_string(
                condition.get(
                    "name"
                )
            )

            if name:

                counter[
                    name
                ] += 1

    return [
        {
            "name": name,

            "affected_clause_count": (
                count
            ),

            "site_state": (
                "UNKNOWN"
            ),
        }

        for name, count
        in counter.most_common()
    ]


# ============================================================
# project/procedure aggregation
# ============================================================

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

                counter[
                    name
                ] += 1

    return [
        {
            "name": name,

            "affected_clause_count": (
                count
            ),

            "profile_state": (
                "UNSET"
            ),
        }

        for name, count
        in counter.most_common()
    ]


# ============================================================
# main
# ============================================================

def main() -> int:

    final_snapshot = load_json(
        FINAL_RULE_PATH
    )

    downtown_resolution = load_json(
        SEOUL_DOWNTOWN_PATH
    )

    rules = copy.deepcopy(
        final_snapshot.get(
            "rules",
            [],
        )
    )

    # ========================================================
    # 1. overlay definition
    # ========================================================

    condition_data = (
        downtown_resolution.get(
            "condition",
            {}
        )
    )

    overlay_name = safe_string(
        condition_data.get(
            "name"
        )
    )

    overlay_state = safe_string(
        condition_data.get(
            "status"
        )
    )

    overlay_confidence = safe_string(
        condition_data.get(
            "confidence"
        )
    )

    overlay_reason = safe_string(
        condition_data.get(
            "reason"
        )
    )

    if (
        overlay_name
        != "서울도심"
        or overlay_state
        != "FALSE"
    ):

        raise ValueError(
            "서울도심 FALSE resolution 입력이 아님"
        )

    # ========================================================
    # 2. overlay
    # ========================================================

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

        changed_condition = False

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
            ) != overlay_name:

                continue

            previous_state = (
                condition.get(
                    "state"
                )
            )

            condition[
                "state"
            ] = (
                overlay_state
            )

            condition[
                "confidence"
            ] = (
                overlay_confidence
            )

            condition[
                "source"
            ] = (
                "SEOUL_DOWNTOWN_CONDITION_RESOLUTION"
            )

            condition[
                "resolution_reason"
            ] = (
                overlay_reason
            )

            changed_condition = True

        if not changed_condition:
            continue

        # ----------------------------------------------------
        # condition group 재작성
        # ----------------------------------------------------

        refresh_condition_groups(
            rule
        )

        # ----------------------------------------------------
        # applicability 재평가
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # numeric effect 상태 재평가
        # ----------------------------------------------------

        refresh_numeric_effect(
            rule
        )

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
    # 3. summary 재계산
    # ========================================================

    applicability_counter = Counter(
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

    # ========================================================
    # 4. rule groups 재작성
    # ========================================================

    rule_groups = {

        "applicable_clause_indexes": [
            rule[
                "clause_index"
            ]
            for rule in rules
            if rule.get(
                "applicability"
            )
            == "APPLICABLE"
        ],

        "conditional_clause_indexes": [
            rule[
                "clause_index"
            ]
            for rule in rules
            if rule.get(
                "applicability"
            )
            == "CONDITIONAL"
        ],

        "unknown_clause_indexes": [
            rule[
                "clause_index"
            ]
            for rule in rules
            if rule.get(
                "applicability"
            )
            == "UNKNOWN"
        ],

        "not_applicable_clause_indexes": [
            rule[
                "clause_index"
            ]
            for rule in rules
            if rule.get(
                "applicability"
            )
            == "NOT_APPLICABLE"
        ],
    }

    # ========================================================
    # 5. numeric confirmed 값
    #
    # overlay는 서울도심 clause 208만 제거하므로
    # BCR/FAR confirmed 값은 그대로 유지
    # ========================================================

    confirmed_regulation = (
        final_snapshot.get(
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
    # 6. validation
    # ========================================================

    changed_clause_indexes = {
        item[
            "clause_index"
        ]
        for item
        in changed_rules
    }

    remaining_names = {
        item[
            "name"
        ]
        for item
        in unresolved_site
    }

    validations = {

        "rules 314 유지": (
            len(
                rules
            )
            == 314
        ),

        "서울도심 overlay 1 clause": (
            len(
                changed_rules
            )
            == 1
        ),

        "clause 208 변경": (
            208
            in changed_clause_indexes
        ),

        "clause 208 NOT_APPLICABLE": (
            any(
                item[
                    "clause_index"
                ]
                == 208
                and item[
                    "new_applicability"
                ]
                == "NOT_APPLICABLE"

                for item
                in changed_rules
            )
        ),

        "APPLICABLE 58 유지": (
            applicability_counter[
                "APPLICABLE"
            ]
            == 58
        ),

        "NOT_APPLICABLE 193": (
            applicability_counter[
                "NOT_APPLICABLE"
            ]
            == 193
        ),

        "CONDITIONAL 43 유지": (
            applicability_counter[
                "CONDITIONAL"
            ]
            == 43
        ),

        "UNKNOWN 20": (
            applicability_counter[
                "UNKNOWN"
            ]
            == 20
        ),

        "서울도심 unresolved 제거": (
            "서울도심"
            not in remaining_names
        ),

        "unresolved SITE 3종": (
            len(
                unresolved_site
            )
            == 3
        ),

        "개발밀도관리구역 유지": (
            "개발밀도관리구역"
            in remaining_names
        ),

        "학교이적지 유지": (
            "학교이적지"
            in remaining_names
        ),

        "도시지역편입해제구역 유지": (
            "도시지역편입해제구역"
            in remaining_names
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
    # 7. output
    # ========================================================

    previous_summary = (
        final_snapshot.get(
            "rule_evaluation_summary",
            {}
        )
    )

    new_summary = {
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

        "numeric_clause_candidates": (
            previous_summary.get(
                "numeric_clause_candidates"
            )
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
    }

    output = {

        "step": (
            STEP_NAME
        ),

        "site": (
            final_snapshot.get(
                "site",
                {}
            )
        ),

        "confirmed_regulation": (
            confirmed_regulation
        ),

        "overlay": {
            "condition": (
                overlay_name
            ),

            "state": (
                overlay_state
            ),

            "confidence": (
                overlay_confidence
            ),

            "changed_rules": (
                changed_rules
            ),
        },

        "previous_summary": (
            previous_summary
        ),

        "rule_evaluation_summary": (
            new_summary
        ),

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
        overlay_name,
        "->",
        overlay_state,
    )

    print()

    print(
        "Changed rules:",
        len(
            changed_rules
        ),
    )

    for item in changed_rules:

        print(
            f"- clause "
            f"{item['clause_index']} "
            f"| "
            f"{item['previous_applicability']} "
            f"-> "
            f"{item['new_applicability']} "
            f"| "
            f"{item['rule_title']}"
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
                item[
                    "name"
                ],
                item[
                    "affected_clause_count"
                ],
            )
            for item
            in unresolved_site
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