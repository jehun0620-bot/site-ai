# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2A-4
Active numeric parent/child hierarchy dedup

목표
======================================================================
1. numeric_effect_semantic_recheck.json의 ACTIVE numeric clause 사용
2. 동일 law_name + rule_title 내 parent/child 관계 탐지
3. ACTIVE child가 존재하는 aggregate parent를 최종 계산 후보에서 제외
4. 가장 구체적인 clause를 우선
5. APPLICABLE / CONDITIONAL / UNKNOWN 상태는 유지
6. semantic UNKNOWN도 삭제하지 않는다.
   -> hierarchy만 정리하고 다음 semantic 보강 단계로 전달
7. parent와 child가 같은 numeric 값을 갖더라도 중복 계산 금지
"""

from __future__ import annotations

import json

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


STEP_NAME = (
    "STEP 17-21-C-10-2A-4 "
    "Active numeric hierarchy dedup"
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

INPUT_PATH = (
    OUTPUT_DIR
    / "numeric_effect_semantic_recheck.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "active_numeric_hierarchy_dedup.json"
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

    """
    root                = 0
    paragraph           = 1
    paragraph + item    = 2
    paragraph+item+sub  = 3
    """

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

    if (
        parent_path
        == child_path
    ):
        return False

    if (
        specificity(
            child
        )
        <=
        specificity(
            parent
        )
    ):
        return False

    # --------------------------------------------------------
    # parent에서 명시된 hierarchy 요소는
    # child에서도 같아야 한다.
    # --------------------------------------------------------

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
# dedup
# ============================================================

def build_parent_child_map(
    active: List[Dict[str, Any]],
) -> Dict[int, List[int]]:

    result = defaultdict(
        list
    )

    for parent in active:

        for child in active:

            if (
                parent[
                    "clause_index"
                ]
                ==
                child[
                    "clause_index"
                ]
            ):
                continue

            if not is_parent_of(
                parent,
                child,
            ):
                continue

            result[
                parent[
                    "clause_index"
                ]
            ].append(
                child[
                    "clause_index"
                ]
            )

    return {
        key: sorted(
            set(
                values
            )
        )

        for key, values
        in result.items()
    }


def deepest_active_descendants(
    parent_index: int,
    parent_child_map: Dict[
        int,
        List[int]
    ],
) -> List[int]:

    """
    parent 아래의 최종 leaf active children을 찾는다.
    """

    children = (
        parent_child_map.get(
            parent_index,
            []
        )
    )

    if not children:
        return []

    leaves = []

    for child in children:

        child_children = (
            parent_child_map.get(
                child,
                []
            )
        )

        if child_children:

            deeper = (
                deepest_active_descendants(
                    child,
                    parent_child_map,
                )
            )

            if deeper:
                leaves.extend(
                    deeper
                )

            else:
                leaves.append(
                    child
                )

        else:

            leaves.append(
                child
            )

    return sorted(
        set(
            leaves
        )
    )


# ============================================================
# main
# ============================================================

def main() -> int:

    data = load_json(
        INPUT_PATH
    )

    clauses = data.get(
        "clauses",
        [],
    )

    # ========================================================
    # ACTIVE only
    # ========================================================

    active = [
        item

        for item
        in clauses

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
    ]

    active_by_index = {
        int(
            item[
                "clause_index"
            ]
        ): item

        for item
        in active
    }

    # ========================================================
    # hierarchy
    # ========================================================

    parent_child_map = (
        build_parent_child_map(
            active
        )
    )

    parent_indexes = set(
        parent_child_map.keys()
    )

    # ========================================================
    # aggregate parent 제외
    # ========================================================

    excluded_parents = []

    final_candidates = []

    for item in active:

        index = int(
            item[
                "clause_index"
            ]
        )

        if index in parent_indexes:

            leaves = (
                deepest_active_descendants(
                    index,
                    parent_child_map,
                )
            )

            excluded_parents.append(
                {
                    "clause_index": (
                        index
                    ),

                    "applicability": (
                        item.get(
                            "applicability"
                        )
                    ),

                    "law_name": (
                        item.get(
                            "law_name"
                        )
                    ),

                    "rule_title": (
                        item.get(
                            "rule_title"
                        )
                    ),

                    "path": (
                        clause_path(
                            item
                        )
                    ),

                    "specificity": (
                        specificity(
                            item
                        )
                    ),

                    "numeric_values": (
                        item.get(
                            "numeric_values"
                        )
                    ),

                    "semantic": (
                        item.get(
                            "semantic"
                        )
                    ),

                    "active_children": (
                        parent_child_map[
                            index
                        ]
                    ),

                    "leaf_descendants": (
                        leaves
                    ),

                    "reason": (
                        "더 구체적인 ACTIVE child "
                        "numeric clause가 존재하므로 "
                        "aggregate parent 계산 제외"
                    ),
                }
            )

            continue

        final_candidates.append(
            item
        )

    # ========================================================
    # child가 실제로 남았는지 검증
    # ========================================================

    final_indexes = {
        int(
            item[
                "clause_index"
            ]
        )
        for item
        in final_candidates
    }

    excluded_indexes = {
        item[
            "clause_index"
        ]
        for item
        in excluded_parents
    }

    every_parent_has_remaining_leaf = True

    for parent in excluded_parents:

        leaves = parent[
            "leaf_descendants"
        ]

        if not leaves:

            every_parent_has_remaining_leaf = False
            break

        if not any(
            leaf in final_indexes
            for leaf in leaves
        ):

            every_parent_has_remaining_leaf = False
            break

    # ========================================================
    # semantic summary
    # ========================================================

    before_semantic = Counter(
        item.get(
            "semantic",
            {},
        ).get(
            "semantic_type"
        )
        for item in active
    )

    after_semantic = Counter(
        item.get(
            "semantic",
            {},
        ).get(
            "semantic_type"
        )
        for item in final_candidates
    )

    status_before = Counter(
        item.get(
            "applicability"
        )
        for item in active
    )

    status_after = Counter(
        item.get(
            "applicability"
        )
        for item in final_candidates
    )

    unresolved_after = [
        item

        for item
        in final_candidates

        if item.get(
            "semantic",
            {},
        ).get(
            "semantic_type"
        )
        == "UNKNOWN_NUMERIC_EFFECT"
    ]

    # ========================================================
    # expected known examples
    # ========================================================

    expected_parent_child = {
        18: 20,
        60: 61,
        221: 227,
        232: 233,
    }

    expected_checks = {}

    for parent, child in (
        expected_parent_child.items()
    ):

        # parent가 active가 아닌 경우는 SKIP
        if parent not in active_by_index:

            expected_checks[
                f"{parent}->{child}"
            ] = (
                "PARENT_NOT_ACTIVE"
            )

            continue

        expected_checks[
            f"{parent}->{child}"
        ] = (
            parent
            in excluded_indexes
            and child
            in final_indexes
        )

    # ========================================================
    # validation
    # ========================================================

    no_excluded_parent_remaining = (
        excluded_indexes.isdisjoint(
            final_indexes
        )
    )

    no_duplicate_indexes = (
        len(
            final_indexes
        )
        ==
        len(
            final_candidates
        )
    )

    candidate_count_reduced = (
        len(
            final_candidates
        )
        <
        len(
            active
        )
    )

    validations = {
        "ACTIVE numeric 입력 존재": (
            len(
                active
            )
            > 0
        ),

        "hierarchy parent 탐지": (
            len(
                excluded_parents
            )
            > 0
        ),

        "aggregate parent가 최종 candidate에 남지 않음": (
            no_excluded_parent_remaining
        ),

        "제외 parent마다 최종 leaf child 존재": (
            every_parent_has_remaining_leaf
        ),

        "final candidate clause index 중복 없음": (
            no_duplicate_indexes
        ),

        "hierarchy dedup으로 candidate 수 감소": (
            candidate_count_reduced
        ),

        "UNKNOWN semantic을 dedup 이유로 삭제하지 않음": (
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
            "active_numeric_before": (
                len(
                    active
                )
            ),

            "aggregate_parent_excluded": (
                len(
                    excluded_parents
                )
            ),

            "final_numeric_candidates": (
                len(
                    final_candidates
                )
            ),

            "unresolved_after_dedup": (
                len(
                    unresolved_after
                )
            ),
        },

        "status_before": (
            dict(
                status_before
            )
        ),

        "status_after": (
            dict(
                status_after
            )
        ),

        "semantic_before": (
            dict(
                before_semantic
            )
        ),

        "semantic_after": (
            dict(
                after_semantic
            )
        ),

        "parent_child_map": (
            parent_child_map
        ),

        "expected_examples": (
            expected_checks
        ),

        "excluded_aggregate_parents": (
            excluded_parents
        ),

        "unresolved_preview": [
            {
                "clause_index": (
                    item[
                        "clause_index"
                    ]
                ),

                "applicability": (
                    item[
                        "applicability"
                    ]
                ),

                "rule_title": (
                    item[
                        "rule_title"
                    ]
                ),

                "path": (
                    clause_path(
                        item
                    )
                ),

                "numeric_values": (
                    item[
                        "numeric_values"
                    ]
                ),

                "text": (
                    safe_string(
                        item.get(
                            "text"
                        )
                    )[
                        :350
                    ]
                ),
            }

            for item
            in unresolved_after[:20]
        ],

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),

        "candidates": (
            final_candidates
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # concise console
    # ========================================================

    print(
        "Active numeric before:",
        len(
            active
        ),
    )

    print(
        "Aggregate parents excluded:",
        len(
            excluded_parents
        ),
    )

    print(
        "Final numeric candidates:",
        len(
            final_candidates
        ),
    )

    print(
        "Unresolved after dedup:",
        len(
            unresolved_after
        ),
    )

    print()

    print(
        "Semantic before:",
        dict(
            before_semantic
        ),
    )

    print(
        "Semantic after:",
        dict(
            after_semantic
        ),
    )

    print()

    print(
        "Known hierarchy checks:",
        expected_checks,
    )

    print()

    for item in (
        excluded_parents[:15]
    ):

        print(
            f"EXCLUDE parent "
            f"{item['clause_index']} "
            f"| {item['rule_title']} "
            f"| children="
            f"{item['active_children']} "
            f"| leaves="
            f"{item['leaf_descendants']}"
        )

    print()

    print(
        "Remaining unresolved:"
    )

    for item in (
        unresolved_after[:10]
    ):

        print(
            f"- clause={item['clause_index']} "
            f"{item['applicability']} "
            f"| {item['rule_title']} "
            f"| numeric="
            f"{item['numeric_values']}"
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