# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-5
Immediate numeric effect interaction / stacking probe

목표
======================================================================
현재 즉시 적용 후보 3개:
- clause 4   BCR 60
- clause 50  BCR 75
- clause 189 FAR 300

검증
======================================================================
1. 각 조문의 text / inherited_context / 법령 / hierarchy 확인
2. 같은 기준값을 서로 독립적으로 완화하는 alternative rule인지 확인
3. 한 완화값에 또 다른 완화율을 중첩하는 구조인지 확인
4. 지구단위계획 자체에 의해 실제 적용값이 결정되는지 확인
5. 단순 max() / 합산 적용을 금지
6. 다음 단계에서 최종 확정값과 potential ceiling을 분리할 근거 생성
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


STEP_NAME = (
    "STEP 17-21-C-10-2B-5 "
    "Immediate numeric effect interaction probe"
)


TARGET_INDEXES = {
    4,
    50,
    189,
}


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

FINAL_PATH = (
    OUTPUT_DIR
    / "current_numeric_effect_candidate_finalize.json"
)

APPLICABILITY_PATH = (
    OUTPUT_DIR
    / "branch_local_predicate_applicability_fix.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "immediate_numeric_effect_interaction_probe.json"
)


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
        for value in clause_path(
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

    p = clause_path(
        parent
    )

    c = clause_path(
        child
    )

    if p == c:
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

    for pv, cv in zip(
        p,
        c,
    ):

        if (
            pv
            and pv != cv
        ):
            return False

    return True


def find_parents(
    target: Dict[str, Any],
    clauses: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    result = []

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

        result.append(
            {
                "clause_index": index,
                "path": (
                    clause_path(
                        clause
                    )
                ),
                "text": (
                    clause.get(
                        "text",
                        ""
                    )
                ),
                "numeric_values": (
                    clause.get(
                        "numeric_values",
                        [],
                    )
                ),
            }
        )

    result.sort(
        key=lambda item: (
            len(
                [
                    value
                    for value
                    in item[
                        "path"
                    ]
                    if value
                ]
            )
        )
    )

    return result


def build_index(
    data: Dict[str, Any],
) -> Dict[int, Dict[str, Any]]:

    result = {}

    for key in (
        "all_effects",
        "clauses",
    ):

        items = data.get(
            key,
            [],
        )

        if not isinstance(
            items,
            list,
        ):
            continue

        for item in items:

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


def detect_interaction_hints(
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

    result = []

    tokens = {
        "지구단위계획으로": (
            "PLAN_DEFINED_VALUE"
        ),

        "지구단위계획구역": (
            "DISTRICT_PLAN_CONTEXT"
        ),

        "완화": (
            "RELAXATION"
        ),

        "120퍼센트": (
            "BASE_MULTIPLIER_120"
        ),

        "150퍼센트": (
            "BASE_MULTIPLIER_150"
        ),

        "이하": (
            "UPPER_LIMIT"
        ),

        "중첩": (
            "EXPLICIT_STACKING_LANGUAGE"
        ),

        "각각": (
            "SEPARATE_RULE_LANGUAGE"
        ),

        "범위": (
            "CEILING_OR_RANGE"
        ),

        "제48조에 따른": (
            "LOCAL_BASE_REFERENCE"
        ),

        "제44조에 따른": (
            "LOCAL_BCR_BASE_REFERENCE"
        ),
    }

    for token, label in (
        tokens.items()
    ):

        if token in context:

            result.append(
                label
            )

    return result


def main() -> int:

    clause_data = load_json(
        CLAUSE_PATH
    )

    final_data = load_json(
        FINAL_PATH
    )

    applicability_data = load_json(
        APPLICABILITY_PATH
    )

    clauses = clause_data.get(
        "clauses",
        [],
    )

    final_index = build_index(
        final_data
    )

    applicability_index = (
        build_index(
            applicability_data
        )
    )

    results = []

    for index in sorted(
        TARGET_INDEXES
    ):

        if (
            index < 1
            or index > len(
                clauses
            )
        ):
            continue

        clause = clauses[
            index - 1
        ]

        final = final_index.get(
            index,
            {}
        )

        applicability = (
            applicability_index.get(
                index,
                {}
            )
        )

        parents = find_parents(
            clause,
            clauses,
        )

        results.append(
            {
                "clause_index": index,

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

                "applicability": (
                    applicability.get(
                        "applicability"
                    )
                ),

                "final_role": (
                    final.get(
                        "final_role"
                    )
                ),

                "base_comparison": (
                    final.get(
                        "base_comparison"
                    )
                ),

                "semantic": (
                    final.get(
                        "semantic"
                    )
                ),

                "conditions": (
                    applicability.get(
                        "condition_results",
                        []
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

                "interaction_hints": (
                    detect_interaction_hints(
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

                "stacking_resolution": (
                    "UNVERIFIED"
                ),
            }
        )

    # ========================================================
    # pair comparison
    # ========================================================

    pairs = []

    for i in range(
        len(results)
    ):

        for j in range(
            i + 1,
            len(results),
        ):

            a = results[i]
            b = results[j]

            a_targets = set(
                a.get(
                    "effect_targets",
                    []
                )
            )

            b_targets = set(
                b.get(
                    "effect_targets",
                    []
                )
            )

            common_targets = sorted(
                a_targets
                & b_targets
            )

            if not common_targets:
                continue

            pairs.append(
                {
                    "a": (
                        a[
                            "clause_index"
                        ]
                    ),

                    "b": (
                        b[
                            "clause_index"
                        ]
                    ),

                    "common_targets": (
                        common_targets
                    ),

                    "same_law": (
                        safe_string(
                            a[
                                "law_name"
                            ]
                        )
                        ==
                        safe_string(
                            b[
                                "law_name"
                            ]
                        )
                    ),

                    "same_rule_title": (
                        safe_string(
                            a[
                                "rule_title"
                            ]
                        )
                        ==
                        safe_string(
                            b[
                                "rule_title"
                            ]
                        )
                    ),

                    "explicit_stacking_language": (
                        (
                            "EXPLICIT_STACKING_LANGUAGE"
                            in a[
                                "interaction_hints"
                            ]
                        )
                        or
                        (
                            "EXPLICIT_STACKING_LANGUAGE"
                            in b[
                                "interaction_hints"
                            ]
                        )
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

            "same_effect_pair_count": (
                len(
                    pairs
                )
            ),
        },

        "targets": (
            results
        ),

        "pairs": (
            pairs
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

    print(
        "Same-effect pairs:",
        len(
            pairs
        ),
    )

    print()

    for item in results:

        print(
            f"[clause {item['clause_index']}] "
            f"{item['rule_title']}"
        )

        print(
            "law:",
            item[
                "law_name"
            ],
        )

        print(
            "target:",
            item[
                "effect_targets"
            ],
        )

        print(
            "semantic:",
            item[
                "semantic"
            ],
        )

        print(
            "base:",
            item[
                "base_comparison"
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
                        "state"
                    ),
                )
                for condition
                in item[
                    "conditions"
                ]
                if isinstance(
                    condition,
                    dict,
                )
            ],
        )

        print(
            "hints:",
            item[
                "interaction_hints"
            ],
        )

        print(
            "text:",
            compact(
                item[
                    "text"
                ],
                650,
            ),
        )

        print(
            "inherited:",
            compact(
                item[
                    "inherited_context"
                ],
                650,
            ),
        )

        print()

    print(
        "Pairs:"
    )

    for pair in pairs:

        print(
            f"- {pair['a']} <-> "
            f"{pair['b']} "
            f"| target="
            f"{pair['common_targets']} "
            f"| same_law="
            f"{pair['same_law']} "
            f"| same_rule="
            f"{pair['same_rule_title']} "
            f"| stacking_text="
            f"{pair['explicit_stacking_language']}"
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