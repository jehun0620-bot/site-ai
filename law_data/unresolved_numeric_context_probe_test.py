# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2A-5
Unresolved numeric clause parent/inherited-context semantic probe

목표
======================================================================
1. hierarchy dedup 후 남은 UNKNOWN_NUMERIC_EFFECT 8건 추출
2. 각 clause의:
   - 자체 text
   - inherited_context
   - 동일 rule_title 상위 clause
   - 바로 위 parent clause
   - effect_targets
   - applicability
   를 함께 확인
3. semantic을 아직 자동 확정하지 않는다.
4. 다음 단계에서 안전한 explicit override를 만들 근거를 확보한다.
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


STEP_NAME = (
    "STEP 17-21-C-10-2A-5 "
    "Unresolved numeric context probe"
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

DEDUP_PATH = (
    OUTPUT_DIR
    / "active_numeric_hierarchy_dedup.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "unresolved_numeric_context_probe.json"
)


def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def compact(
    value: Any,
    limit: int = 700,
) -> str:

    text = " ".join(
        safe_string(
            value
        ).split()
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

    parents = []

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

        parents.append(
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
                "inherited_context": (
                    clause.get(
                        "inherited_context",
                        ""
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

    parents.sort(
        key=lambda item: (
            item[
                "specificity"
            ]
        )
    )

    return parents


def main() -> int:

    clause_data = load_json(
        CLAUSE_PATH
    )

    dedup = load_json(
        DEDUP_PATH
    )

    clauses = clause_data.get(
        "clauses",
        [],
    )

    candidates = dedup.get(
        "candidates",
        [],
    )

    unresolved = [
        item
        for item
        in candidates
        if (
            isinstance(
                item,
                dict,
            )
            and item.get(
                "semantic",
                {},
            ).get(
                "semantic_type"
            )
            == "UNKNOWN_NUMERIC_EFFECT"
        )
    ]

    results = []

    for candidate in unresolved:

        index = int(
            candidate[
                "clause_index"
            ]
        )

        if (
            index < 1
            or index > len(
                clauses
            )
        ):
            continue

        source = clauses[
            index - 1
        ]

        parents = find_parents(
            source,
            clauses,
        )

        nearest_parent = (
            parents[-1]
            if parents
            else None
        )

        results.append(
            {
                "clause_index": index,

                "applicability": (
                    candidate.get(
                        "applicability"
                    )
                ),

                "law_name": (
                    source.get(
                        "law_name"
                    )
                ),

                "rule_title": (
                    source.get(
                        "rule_title"
                    )
                ),

                "path": (
                    clause_path(
                        source
                    )
                ),

                "effect_targets": (
                    source.get(
                        "effect_targets",
                        [],
                    )
                ),

                "numeric_values": (
                    source.get(
                        "numeric_values",
                        [],
                    )
                ),

                "conditions": (
                    source.get(
                        "conditions",
                        [],
                    )
                ),

                "inherited_context": (
                    source.get(
                        "inherited_context",
                        ""
                    )
                ),

                "text": (
                    source.get(
                        "text",
                        ""
                    )
                ),

                "parent_count": (
                    len(
                        parents
                    )
                ),

                "nearest_parent": (
                    nearest_parent
                ),

                "all_parents": (
                    parents
                ),

                "semantic_resolution": (
                    "UNVERIFIED"
                ),
            }
        )

    output = {
        "step": STEP_NAME,

        "summary": {
            "unresolved_count": (
                len(
                    results
                )
            ),
        },

        "clauses": (
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
        "Unresolved:",
        len(
            results
        ),
    )

    print()

    for item in results:

        print(
            f"[clause {item['clause_index']}] "
            f"{item['applicability']} | "
            f"{item['rule_title']}"
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
            "text:",
            compact(
                item[
                    "text"
                ],
                500,
            ),
        )

        print(
            "inherited:",
            compact(
                item[
                    "inherited_context"
                ],
                500,
            ),
        )

        parent = item.get(
            "nearest_parent"
        )

        if parent:

            print(
                "parent:",
                parent[
                    "clause_index"
                ],
                "| numeric=",
                parent[
                    "numeric_values"
                ],
            )

            print(
                "parent text:",
                compact(
                    parent[
                        "text"
                    ],
                    600,
                ),
            )

        else:

            print(
                "parent: NONE"
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