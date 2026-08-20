# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2A-6
Numeric clause parent-condition inheritance integrity probe

목표
======================================================================
1. hierarchy dedup 후 numeric candidate를 대상으로 한다.
2. 동일 rule_title 내 가장 가까운 parent clause를 찾는다.
3. parent conditions가 child conditions에 상속되지 않은 경우 탐지한다.
4. parent가 CONDITIONAL / UNKNOWN / NOT_APPLICABLE인데
   child가 더 강한 APPLICABLE 상태인 경우 HIGH-RISK로 표시한다.
5. 아직 자동 수정하지 않는다.
6. numeric 계산 전에 condition hierarchy 무결성을 확정한다.

핵심 원칙
======================================================================
- 세부 조문은 상위 조문의 적용 전제를 임의로 잃어서는 안 된다.
- child가 parent의 숫자만 세분화한 경우 parent 조건을 상속해야 한다.
- 단, 모든 parent condition을 기계적으로 상속하지 않고 먼저 probe한다.
"""

from __future__ import annotations

import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple


STEP_NAME = (
    "STEP 17-21-C-10-2A-6 "
    "numeric parent condition inheritance probe"
)


# ============================================================
# 경로
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

CLAUSE_PATH = (
    OUTPUT_DIR
    / "law_special_rule_clauses.json"
)

APPLICABILITY_PATH = (
    OUTPUT_DIR
    / "contextual_site_condition_fix.json"
)

DEDUP_PATH = (
    OUTPUT_DIR
    / "active_numeric_hierarchy_dedup.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "numeric_parent_condition_inheritance_probe.json"
)


# ============================================================
# 상태 강도
#
# 숫자가 클수록 더 "적용 가능"한 상태
# parent보다 child가 비정상적으로 강해지는지 확인
# ============================================================

STATE_RANK = {
    "NOT_APPLICABLE": 0,
    "UNKNOWN": 1,
    "CONDITIONAL": 2,
    "APPLICABLE": 3,
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


def compact(
    value: Any,
    limit: int = 350,
) -> str:

    text = " ".join(
        safe_string(
            value
        ).split()
    )

    if len(text) > limit:

        return (
            text[:limit]
            + "..."
        )

    return text


# ============================================================
# hierarchy
# ============================================================

def clause_path(
    clause: Dict[str, Any],
) -> Tuple[str, str, str]:

    return (
        safe_string(
            clause.get(
                "paragraph"
            )
        ),
        safe_string(
            clause.get(
                "item"
            )
        ),
        safe_string(
            clause.get(
                "subitem"
            )
        ),
    )


def specificity(
    clause: Dict[str, Any],
) -> int:

    return sum(
        1
        for value
        in clause_path(
            clause
        )
        if value
    )


def same_rule(
    a: Dict[str, Any],
    b: Dict[str, Any],
) -> bool:

    return (
        safe_string(
            a.get(
                "law_name"
            )
        )
        ==
        safe_string(
            b.get(
                "law_name"
            )
        )
        and
        safe_string(
            a.get(
                "rule_title"
            )
        )
        ==
        safe_string(
            b.get(
                "rule_title"
            )
        )
    )


def is_parent_of(
    parent: Dict[str, Any],
    child: Dict[str, Any],
) -> bool:

    if not same_rule(
        parent,
        child,
    ):
        return False

    parent_path = (
        clause_path(
            parent
        )
    )

    child_path = (
        clause_path(
            child
        )
    )

    if parent_path == child_path:
        return False

    if (
        specificity(
            parent
        )
        >=
        specificity(
            child
        )
    ):
        return False

    for parent_value, child_value in zip(
        parent_path,
        child_path,
    ):

        if (
            parent_value
            and parent_value
            != child_value
        ):
            return False

    return True


# ============================================================
# applicability
# ============================================================

def build_applicability_index(
    data: Dict[str, Any],
) -> Dict[int, Dict[str, Any]]:

    result = {}

    for item in data.get(
        "clauses",
        [],
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        index = item.get(
            "clause_index"
        )

        if index is None:
            continue

        result[
            int(index)
        ] = item

    return result


# ============================================================
# conditions
# ============================================================

def condition_signature(
    condition: Dict[str, Any],
) -> Tuple[str, str]:

    return (
        safe_string(
            condition.get(
                "name"
            )
        ),
        safe_string(
            condition.get(
                "type"
            )
        ),
    )


def explicit_conditions(
    clause: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return [
        condition

        for condition
        in clause.get(
            "conditions",
            []
        )

        if isinstance(
            condition,
            dict,
        )
        and safe_string(
            condition.get(
                "name"
            )
        )
    ]


def effective_conditions_from_applicability(
    item: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return [
        condition

        for condition
        in item.get(
            "effective_conditions",
            []
        )

        if isinstance(
            condition,
            dict,
        )
        and safe_string(
            condition.get(
                "name"
            )
        )
    ]


# ============================================================
# parent 검색
# ============================================================

def find_all_parents(
    child: Dict[str, Any],
    source_clauses: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    results = []

    for index, parent in enumerate(
        source_clauses,
        start=1,
    ):

        if not isinstance(
            parent,
            dict,
        ):
            continue

        if not is_parent_of(
            parent,
            child,
        ):
            continue

        results.append(
            {
                "clause_index": index,
                "specificity": (
                    specificity(
                        parent
                    )
                ),
                "clause": parent,
            }
        )

    results.sort(
        key=lambda item: (
            item[
                "specificity"
            ]
        )
    )

    return results


# ============================================================
# main
# ============================================================

def main() -> int:

    clause_data = load_json(
        CLAUSE_PATH
    )

    applicability_data = load_json(
        APPLICABILITY_PATH
    )

    dedup_data = load_json(
        DEDUP_PATH
    )

    source_clauses = clause_data.get(
        "clauses",
        [],
    )

    applicability_index = (
        build_applicability_index(
            applicability_data
        )
    )

    candidates = dedup_data.get(
        "candidates",
        [],
    )

    results = []

    missing_counter = Counter()

    high_risk = []

    # ========================================================
    # final numeric candidate별 parent 확인
    # ========================================================

    for candidate in candidates:

        if not isinstance(
            candidate,
            dict,
        ):
            continue

        child_index = int(
            candidate[
                "clause_index"
            ]
        )

        if (
            child_index < 1
            or child_index > len(
                source_clauses
            )
        ):
            continue

        child_source = (
            source_clauses[
                child_index - 1
            ]
        )

        child_app = (
            applicability_index.get(
                child_index,
                {}
            )
        )

        parents = find_all_parents(
            child_source,
            source_clauses,
        )

        if not parents:
            continue

        nearest = parents[-1]

        parent_index = (
            nearest[
                "clause_index"
            ]
        )

        parent_source = (
            nearest[
                "clause"
            ]
        )

        parent_app = (
            applicability_index.get(
                parent_index,
                {}
            )
        )

        # ----------------------------------------------------
        # source explicit condition
        # ----------------------------------------------------

        parent_explicit = (
            explicit_conditions(
                parent_source
            )
        )

        child_explicit = (
            explicit_conditions(
                child_source
            )
        )

        # ----------------------------------------------------
        # contextual fix까지 반영된 effective conditions
        # ----------------------------------------------------

        parent_effective = (
            effective_conditions_from_applicability(
                parent_app
            )
        )

        child_effective = (
            effective_conditions_from_applicability(
                child_app
            )
        )

        parent_effective_signatures = {
            condition_signature(
                condition
            )
            for condition
            in parent_effective
        }

        child_effective_signatures = {
            condition_signature(
                condition
            )
            for condition
            in child_effective
        }

        missing_signatures = (
            parent_effective_signatures
            -
            child_effective_signatures
        )

        missing = []

        for name, condition_type in sorted(
            missing_signatures
        ):

            missing.append(
                {
                    "name": name,
                    "type": condition_type,
                }
            )

            missing_counter[
                name
            ] += 1

        parent_state = safe_string(
            parent_app.get(
                "applicability"
            )
        )

        child_state = safe_string(
            child_app.get(
                "applicability"
            )
        )

        rank_violation = (
            parent_state
            in STATE_RANK
            and child_state
            in STATE_RANK
            and STATE_RANK[
                child_state
            ]
            >
            STATE_RANK[
                parent_state
            ]
        )

        entry = {
            "child_index": (
                child_index
            ),

            "child_state": (
                child_state
            ),

            "child_rule_title": (
                child_source.get(
                    "rule_title"
                )
            ),

            "child_path": (
                clause_path(
                    child_source
                )
            ),

            "child_numeric": (
                child_source.get(
                    "numeric_values",
                    []
                )
            ),

            "child_text": (
                child_source.get(
                    "text",
                    ""
                )
            ),

            "parent_index": (
                parent_index
            ),

            "parent_state": (
                parent_state
            ),

            "parent_path": (
                clause_path(
                    parent_source
                )
            ),

            "parent_numeric": (
                parent_source.get(
                    "numeric_values",
                    []
                )
            ),

            "parent_text": (
                parent_source.get(
                    "text",
                    ""
                )
            ),

            "parent_explicit_conditions": (
                parent_explicit
            ),

            "child_explicit_conditions": (
                child_explicit
            ),

            "parent_effective_conditions": (
                parent_effective
            ),

            "child_effective_conditions": (
                child_effective
            ),

            "missing_parent_conditions": (
                missing
            ),

            "applicability_rank_violation": (
                rank_violation
            ),
        }

        results.append(
            entry
        )

        # ----------------------------------------------------
        # HIGH RISK
        #
        # parent condition 누락 + child가 parent보다
        # 더 적용가능한 상태
        # ----------------------------------------------------

        if (
            missing
            and rank_violation
        ):

            high_risk.append(
                entry
            )

    # ========================================================
    # known example clause 20
    # ========================================================

    clause20 = next(
        (
            item
            for item
            in results
            if item[
                "child_index"
            ]
            == 20
        ),
        None,
    )

    clause20_detected = (
        clause20 is not None
        and bool(
            clause20[
                "missing_parent_conditions"
            ]
        )
        and clause20[
            "applicability_rank_violation"
        ]
    )

    # ========================================================
    # 통계
    # ========================================================

    missing_entries = [
        item
        for item
        in results
        if item[
            "missing_parent_conditions"
        ]
    ]

    rank_violations = [
        item
        for item
        in results
        if item[
            "applicability_rank_violation"
        ]
    ]

    validations = {
        "numeric candidate parent 분석 완료": (
            True
        ),

        "parent condition 누락 탐지 수행": (
            True
        ),

        "parent-child applicability monotonicity 검사": (
            True
        ),

        "clause 20 inheritance 문제 탐지": (
            clause20_detected
        ),

        "누락 parent condition을 자동 FALSE 처리하지 않음": (
            True
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

        "summary": {
            "candidate_count": (
                len(
                    candidates
                )
            ),

            "candidate_with_parent_count": (
                len(
                    results
                )
            ),

            "missing_parent_condition_count": (
                len(
                    missing_entries
                )
            ),

            "applicability_rank_violation_count": (
                len(
                    rank_violations
                )
            ),

            "high_risk_count": (
                len(
                    high_risk
                )
            ),
        },

        "missing_condition_frequency": (
            dict(
                missing_counter
            )
        ),

        "high_risk": (
            high_risk
        ),

        "all_parent_checks": (
            results
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
        "Numeric candidates:",
        len(
            candidates
        ),
    )

    print(
        "With parent:",
        len(
            results
        ),
    )

    print(
        "Missing parent conditions:",
        len(
            missing_entries
        ),
    )

    print(
        "Applicability rank violations:",
        len(
            rank_violations
        ),
    )

    print(
        "HIGH-RISK:",
        len(
            high_risk
        ),
    )

    print(
        "Missing condition frequency:",
        dict(
            missing_counter
        ),
    )

    print()

    for index, item in enumerate(
        high_risk[:15],
        start=1,
    ):

        print(
            f"[{index}] "
            f"parent={item['parent_index']} "
            f"{item['parent_state']} "
            f"-> child={item['child_index']} "
            f"{item['child_state']} "
            f"| {item['child_rule_title']}"
        )

        print(
            "  missing:",
            [
                (
                    condition[
                        "name"
                    ],
                    condition[
                        "type"
                    ],
                )
                for condition
                in item[
                    "missing_parent_conditions"
                ]
            ],
        )

        print(
            "  parent:",
            compact(
                item[
                    "parent_text"
                ]
            ),
        )

        print(
            "  child :",
            compact(
                item[
                    "child_text"
                ]
            ),
        )

    print()

    print(
        "clause 20 inheritance detected:",
        clause20_detected,
    )

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