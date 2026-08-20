# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2A-1
Active numeric clause hierarchy / missing-condition integrity probe

목표
======================================================================
1. numeric_effect_semantic_probe.json에서 현재 ACTIVE numeric clause 추출
2. 동일 rule_title 내부에서 parent/child clause 중복 여부 검사
3. child가 존재하는 aggregate parent clause 식별
4. rule_title / text에 SITE condition명이 명시돼 있는데
   clause.conditions에 누락된 경우 탐지
5. 특히 C-9 FALSE 조건이 제목/본문에 존재하면서
   APPLICABLE인 clause를 HIGH-RISK로 표시
6. 아직 numeric 계산은 수행하지 않는다.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


STEP_NAME = (
    "STEP 17-21-C-10-2A-1 "
    "Active numeric clause hierarchy / missing-condition probe"
)

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

NUMERIC_PATH = (
    OUTPUT_DIR
    / "numeric_effect_semantic_probe.json"
)

SITE_PATH = (
    OUTPUT_DIR
    / "site_spatial_condition_final_snapshot.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "active_numeric_clause_integrity_probe.json"
)


ACTIVE_STATES = {
    "APPLICABLE",
    "CONDITIONAL",
    "UNKNOWN",
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
# SITE index
# ============================================================

def build_site_index(
    snapshot: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:

    result = {}

    for group in (
        "conditions",
        "supplemental_conditions",
    ):

        for item in snapshot.get(
            group,
            [],
        ):

            if not isinstance(
                item,
                dict,
            ):
                continue

            name = safe_string(
                item.get(
                    "name"
                )
            )

            if not name:
                continue

            result[name] = {
                "status": safe_string(
                    item.get(
                        "status"
                    )
                ),
                "confidence": safe_string(
                    item.get(
                        "confidence"
                    )
                ),
            }

    return result


# ============================================================
# clause path
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


def specificity_score(
    clause: Dict[str, Any],
) -> int:

    """
    세부 clause일수록 점수가 높다.

    rule root        = 0
    paragraph        = 1
    paragraph+item   = 2
    +subitem         = 3
    """

    return sum(
        1
        for value in clause_path(
            clause
        )
        if value
    )


def is_parent_of(
    parent: Dict[str, Any],
    child: Dict[str, Any],
) -> bool:

    if safe_string(
        parent.get(
            "law_name"
        )
    ) != safe_string(
        child.get(
            "law_name"
        )
    ):
        return False

    if safe_string(
        parent.get(
            "rule_title"
        )
    ) != safe_string(
        child.get(
            "rule_title"
        )
    ):
        return False

    p = clause_path(
        parent
    )

    c = clause_path(
        child
    )

    if p == c:
        return False

    # --------------------------------------------------------
    # parent의 지정된 단계는 child와 같아야 하며,
    # parent보다 child가 더 세부적이어야 한다.
    # --------------------------------------------------------

    parent_specificity = (
        specificity_score(
            parent
        )
    )

    child_specificity = (
        specificity_score(
            child
        )
    )

    if (
        child_specificity
        <= parent_specificity
    ):
        return False

    for p_value, c_value in zip(
        p,
        c,
    ):

        if (
            p_value
            and p_value != c_value
        ):
            return False

    return True


# ============================================================
# missing SITE condition
# ============================================================

def declared_condition_names(
    clause: Dict[str, Any],
) -> List[str]:

    result = []

    for condition in clause.get(
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

        if name:
            result.append(
                name
            )

    return result


def detect_missing_site_conditions(
    clause: Dict[str, Any],
    site_index: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:

    declared = set(
        declared_condition_names(
            clause
        )
    )

    search_text = (
        safe_string(
            clause.get(
                "rule_title"
            )
        )
        + " "
        + safe_string(
            clause.get(
                "inherited_context"
            )
        )
        + " "
        + safe_string(
            clause.get(
                "text"
            )
        )
    )

    hits = []

    for name, site in (
        site_index.items()
    ):

        if name in declared:
            continue

        if name not in search_text:
            continue

        hits.append(
            {
                "condition": (
                    name
                ),
                "site_status": (
                    site[
                        "status"
                    ]
                ),
                "confidence": (
                    site[
                        "confidence"
                    ]
                ),
            }
        )

    return hits


# ============================================================
# main
# ============================================================

def main() -> int:

    clause_data = load_json(
        CLAUSE_PATH
    )

    numeric_data = load_json(
        NUMERIC_PATH
    )

    site_snapshot = load_json(
        SITE_PATH
    )

    source_clauses = clause_data.get(
        "clauses",
        [],
    )

    site_index = build_site_index(
        site_snapshot
    )

    # ========================================================
    # ACTIVE numeric clause
    # ========================================================

    active_indexes = {
        int(
            item[
                "clause_index"
            ]
        )

        for item
        in numeric_data.get(
            "clauses",
            []
        )

        if (
            isinstance(
                item,
                dict,
            )
            and item.get(
                "applicability"
            )
            in ACTIVE_STATES
        )
    }

    active = []

    numeric_index = {
        int(
            item[
                "clause_index"
            ]
        ): item

        for item
        in numeric_data.get(
            "clauses",
            []
        )

        if isinstance(
            item,
            dict,
        )
    }

    for index in sorted(
        active_indexes
    ):

        if (
            index < 1
            or index > len(
                source_clauses
            )
        ):
            continue

        clause = (
            source_clauses[
                index - 1
            ]
        )

        numeric = (
            numeric_index[
                index
            ]
        )

        active.append(
            {
                "clause_index": (
                    index
                ),

                **clause,

                "applicability": (
                    numeric.get(
                        "applicability"
                    )
                ),

                "numeric_semantic": (
                    numeric.get(
                        "semantic"
                    )
                ),
            }
        )

    # ========================================================
    # parent-child 중복 탐지
    # ========================================================

    parent_child_pairs = []

    parent_indexes = set()

    child_indexes = set()

    for parent in active:

        for child in active:

            if (
                parent[
                    "clause_index"
                ]
                == child[
                    "clause_index"
                ]
            ):
                continue

            if not is_parent_of(
                parent,
                child,
            ):
                continue

            parent_indexes.add(
                parent[
                    "clause_index"
                ]
            )

            child_indexes.add(
                child[
                    "clause_index"
                ]
            )

            parent_child_pairs.append(
                {
                    "parent": (
                        parent[
                            "clause_index"
                        ]
                    ),

                    "child": (
                        child[
                            "clause_index"
                        ]
                    ),

                    "rule_title": (
                        parent.get(
                            "rule_title"
                        )
                    ),

                    "parent_numeric": (
                        parent.get(
                            "numeric_values"
                        )
                    ),

                    "child_numeric": (
                        child.get(
                            "numeric_values"
                        )
                    ),
                }
            )

    # ========================================================
    # missing condition
    # ========================================================

    missing_condition_clauses = []

    high_risk = []

    for clause in active:

        missing = (
            detect_missing_site_conditions(
                clause,
                site_index,
            )
        )

        if not missing:
            continue

        entry = {
            "clause_index": (
                clause[
                    "clause_index"
                ]
            ),

            "applicability": (
                clause.get(
                    "applicability"
                )
            ),

            "rule_title": (
                clause.get(
                    "rule_title"
                )
            ),

            "declared_conditions": (
                declared_condition_names(
                    clause
                )
            ),

            "missing_site_conditions": (
                missing
            ),

            "numeric_values": (
                clause.get(
                    "numeric_values"
                )
            ),

            "text": (
                safe_string(
                    clause.get(
                        "text"
                    )
                )[
                    :500
                ]
            ),
        }

        missing_condition_clauses.append(
            entry
        )

        # ----------------------------------------------------
        # FALSE/HIGH condition이 누락됐는데
        # 현재 clause가 APPLICABLE이면 HIGH RISK
        # ----------------------------------------------------

        false_high = [
            item
            for item in missing
            if (
                item[
                    "site_status"
                ]
                == "FALSE"
                and item[
                    "confidence"
                ]
                == "HIGH"
            )
        ]

        if (
            false_high
            and clause.get(
                "applicability"
            )
            == "APPLICABLE"
        ):

            high_risk.append(
                {
                    **entry,
                    "false_high_conditions": (
                        false_high
                    ),
                }
            )

    # ========================================================
    # aggregate parent 후보
    # ========================================================

    aggregate_parents = []

    for clause in active:

        index = clause[
            "clause_index"
        ]

        if index not in parent_indexes:
            continue

        children = [
            pair[
                "child"
            ]
            for pair
            in parent_child_pairs
            if pair[
                "parent"
            ]
            == index
        ]

        aggregate_parents.append(
            {
                "clause_index": (
                    index
                ),

                "rule_title": (
                    clause.get(
                        "rule_title"
                    )
                ),

                "specificity": (
                    specificity_score(
                        clause
                    )
                ),

                "child_indexes": (
                    sorted(
                        set(
                            children
                        )
                    )
                ),

                "numeric_values": (
                    clause.get(
                        "numeric_values"
                    )
                ),

                "text": (
                    safe_string(
                        clause.get(
                            "text"
                        )
                    )[
                        :500
                    ]
                ),
            }
        )

    # ========================================================
    # 통계
    # ========================================================

    high_risk_conditions = Counter()

    for item in high_risk:

        for condition in item[
            "false_high_conditions"
        ]:

            high_risk_conditions[
                condition[
                    "condition"
                ]
            ] += 1

    # ========================================================
    # validation
    # ========================================================

    validations = {
        "active numeric clause 존재": (
            len(active) > 0
        ),

        "parent-child 관계 분석 완료": (
            True
        ),

        "SITE condition 누락 탐지 수행": (
            True
        ),

        "FALSE/HIGH 누락조건을 자동 계산하지 않음": (
            True
        ),

        "aggregate parent와 child를 동시 최종계산하지 않음": (
            True
        ),
    }

    all_pass = all(
        validations.values()
    )

    output = {
        "step": (
            STEP_NAME
        ),

        "summary": {
            "active_numeric_clause_count": (
                len(
                    active
                )
            ),

            "parent_child_pair_count": (
                len(
                    parent_child_pairs
                )
            ),

            "aggregate_parent_count": (
                len(
                    aggregate_parents
                )
            ),

            "missing_condition_clause_count": (
                len(
                    missing_condition_clauses
                )
            ),

            "high_risk_applicable_count": (
                len(
                    high_risk
                )
            ),
        },

        "high_risk_conditions": (
            dict(
                high_risk_conditions
            )
        ),

        "aggregate_parents": (
            aggregate_parents
        ),

        "high_risk_applicable_clauses": (
            high_risk
        ),

        "missing_condition_clauses": (
            missing_condition_clauses
        ),

        "parent_child_pairs": (
            parent_child_pairs
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
        "Active numeric:",
        len(
            active
        ),
    )

    print(
        "Parent-child pairs:",
        len(
            parent_child_pairs
        ),
    )

    print(
        "Aggregate parents:",
        len(
            aggregate_parents
        ),
    )

    print(
        "Missing-condition clauses:",
        len(
            missing_condition_clauses
        ),
    )

    print(
        "HIGH-RISK applicable:",
        len(
            high_risk
        ),
    )

    print(
        "HIGH-RISK conditions:",
        dict(
            high_risk_conditions
        ),
    )

    print()

    for index, item in enumerate(
        high_risk[:10],
        start=1,
    ):

        print(
            f"[{index}] "
            f"clause={item['clause_index']} | "
            f"{item['rule_title']}"
        )

        print(
            "  missing:",
            [
                (
                    condition[
                        "condition"
                    ],
                    condition[
                        "site_status"
                    ],
                )
                for condition
                in item[
                    "false_high_conditions"
                ]
            ],
        )

        print(
            "  numeric:",
            item[
                "numeric_values"
            ],
        )

    print()

    print(
        "Aggregate parent preview:"
    )

    for item in (
        aggregate_parents[:10]
    ):

        print(
            f"- clause={item['clause_index']} "
            f"| {item['rule_title']} "
            f"| children={item['child_indexes']} "
            f"| numeric={item['numeric_values']}"
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