# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-3
Remaining numeric role/context probe

대상
======================================================================
clause 3
clause 220
clause 244

목표
======================================================================
1. 세 clause의 자체 text / inherited_context 확인
2. parent / sibling hierarchy 확인
3. 현재 semantic 및 projected value 확인
4. BASE / RELAXATION / STRENGTHENING / CEILING 중 역할 확정 근거 확보
5. clause 3 RANGE가 실제 어떤 범위인지 확인
6. clause 220 / 244가 현재 SITE 기본 FAR=250에
   실제 적용되는 값인지 또는 다른 조건/용도지역 기준인지 검증
7. 아직 최종 BCR/FAR 계산은 수행하지 않음
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


STEP_NAME = (
    "STEP 17-21-C-10-2B-3 "
    "remaining numeric role context probe"
)

TARGET_INDEXES = {
    3,
    220,
    244,
}


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

CLAUSE_PATH = (
    OUTPUT_DIR
    / "law_special_rule_clauses.json"
)

NUMERIC_PATH = (
    OUTPUT_DIR
    / "numeric_semantic_override_finalize.json"
)

ROLE_PATH = (
    OUTPUT_DIR
    / "current_numeric_effect_role_probe.json"
)

APPLICABILITY_PATH = (
    OUTPUT_DIR
    / "branch_local_predicate_applicability_fix.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "remaining_numeric_role_context_probe.json"
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


def compact(
    value: Any,
    limit: int = 800,
) -> str:

    text = " ".join(
        safe_string(value).split()
    )

    if len(text) > limit:
        return text[:limit] + "..."

    return text


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

    return sum(
        1
        for value
        in clause_path(clause)
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

    p = clause_path(
        parent
    )

    c = clause_path(
        child
    )

    if p == c:
        return False

    if specificity(
        parent
    ) >= specificity(
        child
    ):
        return False

    for pv, cv in zip(
        p,
        c,
    ):

        if pv and pv != cv:
            return False

    return True


def find_parents(
    target: Dict[str, Any],
    clauses: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    results = []

    for index, clause in enumerate(
        clauses,
        start=1,
    ):

        if not isinstance(
            clause,
            dict,
        ):
            continue

        if not is_parent_of(
            clause,
            target,
        ):
            continue

        results.append(
            {
                "clause_index": index,

                "specificity": (
                    specificity(
                        clause
                    )
                ),

                "path": (
                    clause_path(
                        clause
                    )
                ),

                "numeric_values": (
                    clause.get(
                        "numeric_values",
                        [],
                    )
                ),

                "effect_targets": (
                    clause.get(
                        "effect_targets",
                        [],
                    )
                ),

                "conditions": (
                    clause.get(
                        "conditions",
                        [],
                    )
                ),

                "text": (
                    clause.get(
                        "text",
                        ""
                    )
                ),

                "inherited_context": (
                    clause.get(
                        "inherited_context",
                        ""
                    )
                ),
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


def find_siblings(
    target_index: int,
    target: Dict[str, Any],
    clauses: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    results = []

    target_path = clause_path(
        target
    )

    target_specificity = specificity(
        target
    )

    for index, clause in enumerate(
        clauses,
        start=1,
    ):

        if index == target_index:
            continue

        if not isinstance(
            clause,
            dict,
        ):
            continue

        if not same_rule(
            target,
            clause,
        ):
            continue

        if specificity(
            clause
        ) != target_specificity:
            continue

        path = clause_path(
            clause
        )

        # 완전히 다른 branch까지 너무 많이 출력하지 않고
        # paragraph 또는 item의 상위 단계가 같은 sibling 우선
        same_parent_context = False

        if target_specificity == 1:
            same_parent_context = True

        elif target_specificity == 2:
            same_parent_context = (
                target_path[0]
                == path[0]
            )

        elif target_specificity == 3:
            same_parent_context = (
                target_path[0]
                == path[0]
                and target_path[1]
                == path[1]
            )

        if not same_parent_context:
            continue

        results.append(
            {
                "clause_index": index,

                "path": path,

                "numeric_values": (
                    clause.get(
                        "numeric_values",
                        [],
                    )
                ),

                "text": (
                    clause.get(
                        "text",
                        ""
                    )
                ),
            }
        )

    return results


# ============================================================
# indexes
# ============================================================

def build_index(
    data: Dict[str, Any],
    key: str = "clause_index",
) -> Dict[int, Dict[str, Any]]:

    result = {}

    collections = []

    for possible_key in (
        "candidates",
        "all_calculable_now",
        "clauses",
    ):

        values = data.get(
            possible_key
        )

        if isinstance(
            values,
            list,
        ):
            collections.extend(
                values
            )

    for item in collections:

        if not isinstance(
            item,
            dict,
        ):
            continue

        index = item.get(
            key
        )

        if index is None:
            continue

        result[
            int(index)
        ] = item

    return result


# ============================================================
# semantic hint
#
# 자동 최종판정 아님.
# 문구 유형만 보여준다.
# ============================================================

def semantic_language_hints(
    text: str,
    inherited: str,
) -> List[str]:

    context = (
        safe_string(
            inherited
        )
        + " "
        + safe_string(
            text
        )
    )

    hints = []

    for token, label in (
        (
            "이하",
            "UPPER_LIMIT_LANGUAGE",
        ),
        (
            "이상",
            "LOWER_LIMIT_LANGUAGE",
        ),
        (
            "범위",
            "RANGE_OR_CEILING_LANGUAGE",
        ),
        (
            "완화",
            "RELAXATION_LANGUAGE",
        ),
        (
            "강화",
            "STRENGTHENING_LANGUAGE",
        ),
        (
            "최대한도",
            "MAX_LIMIT_REFERENCE",
        ),
        (
            "제48조",
            "LOCAL_FAR_REFERENCE",
        ),
        (
            "제3종일반주거지역",
            "THIRD_GENERAL_RESIDENTIAL",
        ),
        (
            "지구단위계획",
            "DISTRICT_UNIT_PLAN",
        ),
        (
            "학교이적지",
            "SCHOOL_RELOCATION_SITE",
        ),
    ):

        if token in context:
            hints.append(
                label
            )

    return hints


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

    role_data = load_json(
        ROLE_PATH
    )

    applicability_data = load_json(
        APPLICABILITY_PATH
    )

    clauses = clause_data.get(
        "clauses",
        [],
    )

    numeric_index = build_index(
        numeric_data
    )

    role_index = build_index(
        role_data
    )

    applicability_index = build_index(
        applicability_data
    )

    results = []

    for target_index in sorted(
        TARGET_INDEXES
    ):

        if (
            target_index < 1
            or target_index > len(
                clauses
            )
        ):

            continue

        clause = clauses[
            target_index - 1
        ]

        numeric = numeric_index.get(
            target_index,
            {}
        )

        role = role_index.get(
            target_index,
            {}
        )

        applicability = (
            applicability_index.get(
                target_index,
                {}
            )
        )

        parents = find_parents(
            clause,
            clauses,
        )

        siblings = find_siblings(
            target_index,
            clause,
            clauses,
        )

        results.append(
            {
                "clause_index": (
                    target_index
                ),

                "applicability": (
                    applicability.get(
                        "applicability"
                    )
                ),

                "law_name": (
                    clause.get(
                        "law_name"
                    )
                ),

                "rule_title": (
                    clause.get(
                        "rule_title"
                    )
                ),

                "path": (
                    clause_path(
                        clause
                    )
                ),

                "effect_targets": (
                    clause.get(
                        "effect_targets",
                        [],
                    )
                ),

                "numeric_values": (
                    clause.get(
                        "numeric_values",
                        [],
                    )
                ),

                "semantic": (
                    numeric.get(
                        "semantic"
                    )
                ),

                "current_role": (
                    role.get(
                        "role"
                    )
                ),

                "current_base_comparison": (
                    role.get(
                        "base_comparison"
                    )
                ),

                "conditions": (
                    clause.get(
                        "conditions",
                        [],
                    )
                ),

                "effective_conditions": (
                    applicability.get(
                        "effective_conditions",
                        [],
                    )
                ),

                "condition_results": (
                    applicability.get(
                        "condition_results",
                        [],
                    )
                ),

                "text": (
                    clause.get(
                        "text",
                        ""
                    )
                ),

                "inherited_context": (
                    clause.get(
                        "inherited_context",
                        ""
                    )
                ),

                "language_hints": (
                    semantic_language_hints(
                        clause.get(
                            "text",
                            ""
                        ),
                        clause.get(
                            "inherited_context",
                            ""
                        ),
                    )
                ),

                "parents": (
                    parents
                ),

                "siblings": (
                    siblings
                ),

                "resolution": (
                    "UNVERIFIED"
                ),
            }
        )

    output = {
        "step": (
            STEP_NAME
        ),

        "summary": {
            "target_count": (
                len(
                    results
                )
            ),
        },

        "targets": (
            results
        ),

        "resolution": (
            "CONTEXT_READY"
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # concise console
    # ========================================================

    print(
        "Targets:",
        len(
            results
        ),
    )

    print()

    for item in results:

        print(
            f"[clause {item['clause_index']}] "
            f"{item['applicability']} "
            f"| {item['rule_title']}"
        )

        print(
            "path:",
            item[
                "path"
            ],
        )

        print(
            "effect:",
            item[
                "effect_targets"
            ],
        )

        print(
            "numeric:",
            item[
                "numeric_values"
            ],
        )

        print(
            "semantic:",
            item[
                "semantic"
            ],
        )

        print(
            "current role:",
            item[
                "current_role"
            ],
        )

        print(
            "base comparison:",
            item[
                "current_base_comparison"
            ],
        )

        print(
            "language hints:",
            item[
                "language_hints"
            ],
        )

        print(
            "conditions:",
            [
                (
                    condition.get(
                        "name"
                    ),
                    condition.get(
                        "type"
                    ),
                )

                for condition
                in item[
                    "effective_conditions"
                ]

                if isinstance(
                    condition,
                    dict,
                )
            ],
        )

        print(
            "text:",
            compact(
                item[
                    "text"
                ],
                700,
            ),
        )

        print(
            "inherited:",
            compact(
                item[
                    "inherited_context"
                ],
                700,
            ),
        )

        print(
            "parents:",
            len(
                item[
                    "parents"
                ]
            ),
        )

        for parent in (
            item[
                "parents"
            ][-2:]
        ):

            print(
                f"  parent "
                f"{parent['clause_index']} "
                f"| path="
                f"{parent['path']} "
                f"| numeric="
                f"{parent['numeric_values']}"
            )

            print(
                "    ",
                compact(
                    parent[
                        "text"
                    ],
                    500,
                ),
            )

        print(
            "siblings:",
            len(
                item[
                    "siblings"
                ]
            ),
        )

        for sibling in (
            item[
                "siblings"
            ][:6]
        ):

            print(
                f"  sibling "
                f"{sibling['clause_index']} "
                f"| path="
                f"{sibling['path']} "
                f"| numeric="
                f"{sibling['numeric_values']} "
                f"| "
                f"{compact(sibling['text'], 260)}"
            )

        print()

    print(
        "resolution: CONTEXT_READY"
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )