# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-4B-2B
Numeric Branch-local Condition Overlay

목표
======================================================================
4B-2A에서 검출한 HIGH + direct predicate를
dynamic rule condition model에 실제 반영한다.

정책
======================================================================
1. HIGH confidence만 반영
2. direct_in_clause_text=True만 반영
3. 기존 condition name이 있으면 새로 추가하지 않고 기존 condition 재사용
4. 신규 SITE condition은 현재 SITE 정보로 즉시 판정 가능한 경우만 판정
5. 신규 PROJECT condition은 기본 UNSET
6. condition overlay 후 applicability 재평가
7. numeric effect 상태도 함께 갱신

현재 known mapping
======================================================================

서울도심
    기존 condition 존재
    FALSE / HIGH
    → 재사용

서울조례제48조7호부터10호지역
    현재 SITE 제3종일반주거지역
    서울시 조례 제48조 제5호
    → FALSE / HIGH

관광숙박시설
    PROJECT
    → UNSET

감염병대응필요시설
    PROJECT
    → UNSET

예상
======================================================================
clause 205:
    APPLICABLE -> NOT_APPLICABLE

clause 188 등:
    감염병대응필요시설가 누락되어 있었다면
    APPLICABLE -> CONDITIONAL 가능
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-4B-2B "
    "numeric branch-local condition overlay"
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

DYNAMIC_PATH = (
    OUTPUT_DIR
    / "project_procedure_dynamic_rule_evaluation.json"
)

PROBE_PATH = (
    OUTPUT_DIR
    / "numeric_branch_local_condition_generalization_probe.json"
)

BASE_PATH = (
    OUTPUT_DIR
    / "base_numeric_regulation_hierarchy.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "numeric_branch_local_condition_overlay.json"
)


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


# ============================================================
# known SITE condition resolver
# ============================================================

def resolve_new_condition(
    name: str,
    condition_type: str,
    site_zone: str,
) -> Dict[str, Any]:

    # --------------------------------------------------------
    # existing known SITE branch
    # --------------------------------------------------------

    if (
        name
        == "서울조례제48조7호부터10호지역"
        and condition_type
        == "SITE"
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

        article_number = (
            zone_map.get(
                site_zone
            )
        )

        state = (
            "TRUE"
            if article_number
            in {
                7,
                8,
                9,
                10,
            }
            else "FALSE"
        )

        return {
            "name": (
                name
            ),

            "type": (
                condition_type
            ),

            "state": (
                state
            ),

            "confidence": (
                "HIGH"
            ),

            "source": (
                "BRANCH_LOCAL_SITE_RESOLVER"
            ),

            "resolution_meta": {
                "site_zone": (
                    site_zone
                ),

                "article_48_number": (
                    article_number
                ),

                "required_numbers": [
                    7,
                    8,
                    9,
                    10,
                ],
            },
        }

    # --------------------------------------------------------
    # 신규 PROJECT predicate
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
                "BRANCH_LOCAL_PREDICATE_DETECTOR"
            ),
        }

    # --------------------------------------------------------
    # 신규 PROCEDURE predicate
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
                "BRANCH_LOCAL_PREDICATE_DETECTOR"
            ),
        }

    # --------------------------------------------------------
    # unknown SITE
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
            "BRANCH_LOCAL_PREDICATE_DETECTOR"
        ),
    }


# ============================================================
# condition refresh
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
# main
# ============================================================

def main() -> int:

    dynamic = load_json(
        DYNAMIC_PATH
    )

    probe = load_json(
        PROBE_PATH
    )

    base = load_json(
        BASE_PATH
    )

    rules = copy.deepcopy(
        dynamic.get(
            "rules",
            []
        )
    )

    site_zone = (
        base.get(
            "site_zone"
        )
    )

    # ========================================================
    # HIGH + direct predicate only
    # ========================================================

    high_candidates = (
        probe.get(
            "high_priority_missing",
            []
        )
    )

    selected = [
        item
        for item
        in high_candidates
        if item.get(
            "direct_in_clause_text"
        )
        is True
    ]

    # ========================================================
    # group per clause
    # ========================================================

    by_clause = {}

    for item in selected:

        clause_index = int(
            item.get(
                "clause_index"
            )
        )

        by_clause.setdefault(
            clause_index,
            []
        ).append(
            item
        )

    # ========================================================
    # overlay
    # ========================================================

    touched_rules = []

    changed_rules = []

    added_conditions = []

    reused_conditions = []

    before_counter = Counter(
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
                clause_index
            )
        )

        if not predicates:
            continue

        before = (
            rule.get(
                "applicability"
            )
        )

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

        rule_changes = []

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

            # ------------------------------------------------
            # existing condition reused
            # ------------------------------------------------

            if name in existing_names:

                reused_conditions.append(
                    {
                        "clause_index": (
                            clause_index
                        ),

                        "name": (
                            name
                        ),

                        "type": (
                            condition_type
                        ),
                    }
                )

                continue

            # ------------------------------------------------
            # add new condition
            # ------------------------------------------------

            condition = (
                resolve_new_condition(
                    name,
                    condition_type,
                    site_zone,
                )
            )

            condition[
                "branch_local"
            ] = True

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

            added_conditions.append(
                {
                    "clause_index": (
                        clause_index
                    ),

                    **condition,
                }
            )

            rule_changes.append(
                condition
            )

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

        touched_rules.append(
            {
                "clause_index": (
                    clause_index
                ),

                "rule_title": (
                    rule.get(
                        "rule_title"
                    )
                ),

                "added_conditions": (
                    rule_changes
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

        if (
            before
            != rule.get(
                "applicability"
            )
        ):

            changed_rules.append(
                {
                    "clause_index": (
                        clause_index
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

    # ========================================================
    # after state
    # ========================================================

    after_counter = Counter(
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
        in changed_rules
    )

    # ========================================================
    # numeric groups
    # ========================================================

    active_numeric = []

    conditional_numeric = []

    unknown_numeric = []

    inactive_numeric = []

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

        status = (
            rule.get(
                "current_numeric_effect",
                {},
            ).get(
                "status"
            )
        )

        index = (
            rule.get(
                "clause_index"
            )
        )

        if status == "ACTIVE_CANDIDATE":

            active_numeric.append(
                index
            )

        elif status == "POTENTIAL_CONDITIONAL":

            conditional_numeric.append(
                index
            )

        elif status == "POTENTIAL_UNKNOWN":

            unknown_numeric.append(
                index
            )

        elif status == "INACTIVE":

            inactive_numeric.append(
                index
            )

    # ========================================================
    # regression: clause 205
    # ========================================================

    clause_205 = next(
        (
            rule
            for rule
            in rules
            if int(
                rule.get(
                    "clause_index",
                    -1,
                )
            )
            == 205
        ),
        None,
    )

    clause_205_condition_states = {}

    if clause_205:

        clause_205_condition_states = {
            condition.get(
                "name"
            ): condition.get(
                "state"
            )

            for condition
            in clause_205.get(
                "conditions",
                []
            )

            if isinstance(
                condition,
                dict,
            )
        }

    # ========================================================
    # clause 188 regression
    # ========================================================

    clause_188 = next(
        (
            rule
            for rule
            in rules
            if int(
                rule.get(
                    "clause_index",
                    -1,
                )
            )
            == 188
        ),
        None,
    )

    clause_188_condition_states = {}

    if clause_188:

        clause_188_condition_states = {
            condition.get(
                "name"
            ): condition.get(
                "state"
            )

            for condition
            in clause_188.get(
                "conditions",
                []
            )

            if isinstance(
                condition,
                dict,
            )
        }

    # ========================================================
    # validations
    # ========================================================

    validations = {

        "selected HIGH direct predicates exist": (
            len(
                selected
            )
            > 0
        ),

        "new conditions added": (
            len(
                added_conditions
            )
            > 0
        ),

        "clause205 exists": (
            clause_205
            is not None
        ),

        "clause205 zone branch added": (
            "서울조례제48조7호부터10호지역"
            in clause_205_condition_states
        ),

        "clause205 tourism added": (
            "관광숙박시설"
            in clause_205_condition_states
        ),

        "clause205 zone branch FALSE": (
            clause_205_condition_states.get(
                "서울조례제48조7호부터10호지역"
            )
            == "FALSE"
        ),

        "clause205 NOT_APPLICABLE": (
            clause_205.get(
                "applicability"
            )
            == "NOT_APPLICABLE"
        ),

        "clause205 numeric inactive": (
            clause_205.get(
                "current_numeric_effect",
                {},
            ).get(
                "status"
            )
            == "INACTIVE"
        ),

        "clause188 infection predicate added if detected": (
            (
                "감염병대응필요시설"
                in clause_188_condition_states
            )
            if clause_188
            else True
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

        "site_zone": (
            site_zone
        ),

        "selected_predicates": (
            selected
        ),

        "overlay": {
            "touched_rule_count": (
                len(
                    touched_rules
                )
            ),

            "changed_rule_count": (
                len(
                    changed_rules
                )
            ),

            "added_condition_count": (
                len(
                    added_conditions
                )
            ),

            "reused_condition_count": (
                len(
                    reused_conditions
                )
            ),

            "transitions": {
                f"{before} -> {after}": count

                for (
                    before,
                    after
                ), count
                in transitions.items()
            },

            "added_conditions": (
                added_conditions
            ),

            "reused_conditions": (
                reused_conditions
            ),

            "changed_rules": (
                changed_rules
            ),
        },

        "before": {
            "applicable": (
                before_counter[
                    "APPLICABLE"
                ]
            ),

            "not_applicable": (
                before_counter[
                    "NOT_APPLICABLE"
                ]
            ),

            "conditional": (
                before_counter[
                    "CONDITIONAL"
                ]
            ),

            "unknown": (
                before_counter[
                    "UNKNOWN"
                ]
            ),
        },

        "after": {
            "applicable": (
                after_counter[
                    "APPLICABLE"
                ]
            ),

            "not_applicable": (
                after_counter[
                    "NOT_APPLICABLE"
                ]
            ),

            "conditional": (
                after_counter[
                    "CONDITIONAL"
                ]
            ),

            "unknown": (
                after_counter[
                    "UNKNOWN"
                ]
            ),
        },

        "numeric_state": {
            "active": (
                active_numeric
            ),

            "conditional": (
                conditional_numeric
            ),

            "unknown": (
                unknown_numeric
            ),

            "inactive": (
                inactive_numeric
            ),
        },

        "clause_205_regression": {
            "applicability": (
                clause_205.get(
                    "applicability"
                )
                if clause_205
                else None
            ),

            "condition_states": (
                clause_205_condition_states
            ),
        },

        "clause_188_regression": {
            "applicability": (
                clause_188.get(
                    "applicability"
                )
                if clause_188
                else None
            ),

            "condition_states": (
                clause_188_condition_states
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
        "Selected predicates:",
        len(
            selected
        ),
    )

    print(
        "Added conditions:",
        len(
            added_conditions
        ),
    )

    print(
        "Reused conditions:",
        len(
            reused_conditions
        ),
    )

    print()

    print(
        "Touched rules:",
        len(
            touched_rules
        ),
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
        "Before:",
        dict(
            before_counter
        ),
    )

    print(
        "After:",
        dict(
            after_counter
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
        "=== CLAUSE 205 ==="
    )

    print(
        "Applicability:",
        (
            clause_205.get(
                "applicability"
            )
            if clause_205
            else None
        ),
    )

    print(
        "Conditions:",
        clause_205_condition_states,
    )

    print()

    print(
        "=== CLAUSE 188 ==="
    )

    print(
        "Applicability:",
        (
            clause_188.get(
                "applicability"
            )
            if clause_188
            else None
        ),
    )

    print(
        "Conditions:",
        clause_188_condition_states,
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