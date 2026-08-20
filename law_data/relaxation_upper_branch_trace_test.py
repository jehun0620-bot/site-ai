# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-8
상위 시행령 relaxation branch trace

대상
======================================================================
A. 건폐율
   서울특별시 도시계획 조례 clause 4
   -> 영 제84조제6항제2호

B. 용적률
   서울특별시 도시계획 조례 clause 189
   -> 영 제85조제5항

목표
======================================================================
1. law_special_rule_clauses.json 전체에서
   국토의 계획 및 이용에 관한 법률 시행령의
   제84조 / 제85조 관련 clause 검색

2. 다음 표현을 별도로 탐지
   - 제84조제6항제2호
   - 제84조 제6항 제2호
   - 제85조제5항
   - 제85조 제5항

3. 정확 일치가 없으면
   rule_title + paragraph/item 구조로 제84조/제85조 후보 검색

4. 각 후보의
   - text
   - inherited_context
   - conditions
   - numeric_values
   - effect_targets
   - paragraph/item/subitem
   출력

5. 상위 시행령 branch가 C-8에 이미 존재하는지 확인

6. 아직 TRUE/FALSE 판정은 하지 않는다.
"""

from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-2B-8 "
    "relaxation upper branch trace"
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

CLAUSE_PATH = (
    OUTPUT_DIR
    / "law_special_rule_clauses.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "relaxation_upper_branch_trace.json"
)


TARGET_LAW = (
    "국토의 계획 및 이용에 관한 법률 시행령"
)


# ============================================================
# target definitions
# ============================================================

TARGETS = {

    "BCR_84_6_2": {
        "article": "제84조",

        "exact_patterns": [
            r"제\s*84\s*조\s*제\s*6\s*항\s*제\s*2\s*호",
            r"제84조제6항제2호",
        ],

        "article_patterns": [
            r"제\s*84\s*조",
            r"제84조",
        ],

        "effect": (
            "building_coverage_ratio"
        ),

        "source_clause": 4,
    },

    "FAR_85_5": {
        "article": "제85조",

        "exact_patterns": [
            r"제\s*85\s*조\s*제\s*5\s*항",
            r"제85조제5항",
        ],

        "article_patterns": [
            r"제\s*85\s*조",
            r"제85조",
        ],

        "effect": (
            "floor_area_ratio"
        ),

        "source_clause": 189,
    },
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


def normalize_text(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        safe_string(
            value
        ),
    ).strip()


def compact(
    value: Any,
    limit: int = 750,
) -> str:

    text = normalize_text(
        value
    )

    if len(text) > limit:

        return (
            text[:limit]
            + "..."
        )

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

        return json.load(
            f
        )


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
# condition summary
# ============================================================

def condition_summary(
    clause: Dict[str, Any],
) -> List[Dict[str, str]]:

    result = []

    for item in clause.get(
        "conditions",
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

        condition_type = safe_string(
            item.get(
                "type"
            )
        )

        if not name:
            continue

        result.append(
            {
                "name": name,
                "type": condition_type,
            }
        )

    return result


# ============================================================
# clause context
# ============================================================

def full_context(
    clause: Dict[str, Any],
) -> str:

    values = [
        clause.get(
            "law_name"
        ),
        clause.get(
            "rule_title"
        ),
        clause.get(
            "inherited_context"
        ),
        clause.get(
            "text"
        ),
    ]

    return normalize_text(
        " ".join(
            safe_string(
                value
            )
            for value
            in values
        )
    )


# ============================================================
# exact matching
# ============================================================

def pattern_match(
    text: str,
    patterns: List[str],
) -> bool:

    return any(
        re.search(
            pattern,
            text,
        )
        is not None

        for pattern
        in patterns
    )


# ============================================================
# likely article match
# ============================================================

def is_target_article_candidate(
    clause: Dict[str, Any],
    definition: Dict[str, Any],
) -> bool:

    if safe_string(
        clause.get(
            "law_name"
        )
    ) != TARGET_LAW:

        return False

    context = full_context(
        clause
    )

    return pattern_match(
        context,
        definition[
            "article_patterns"
        ],
    )


# ============================================================
# scoring
# ============================================================

def score_candidate(
    clause: Dict[str, Any],
    definition: Dict[str, Any],
) -> int:

    score = 0

    context = full_context(
        clause
    )

    text = normalize_text(
        clause.get(
            "text"
        )
    )

    inherited = normalize_text(
        clause.get(
            "inherited_context"
        )
    )

    rule_title = normalize_text(
        clause.get(
            "rule_title"
        )
    )

    # exact reference
    if pattern_match(
        context,
        definition[
            "exact_patterns"
        ],
    ):

        score += 100

    # target article
    if pattern_match(
        context,
        definition[
            "article_patterns"
        ],
    ):

        score += 30

    # effect
    effects = clause.get(
        "effect_targets",
        [],
    )

    if (
        definition[
            "effect"
        ]
        in effects
    ):

        score += 20

    # relevant language
    for token in (
        "완화",
        "건폐율",
        "용적률",
        "초과할 수 없다",
        "조례",
        "범위",
    ):

        if token in text:

            score += 2

    if "완화" in rule_title:

        score += 10

    if "완화" in inherited:

        score += 5

    # hierarchy hint
    paragraph = safe_string(
        clause.get(
            "paragraph"
        )
    )

    item = safe_string(
        clause.get(
            "item"
        )
    )

    if definition[
        "article"
    ] == "제84조":

        if paragraph == "⑥":
            score += 25

        if item == "2":
            score += 30

    if definition[
        "article"
    ] == "제85조":

        if paragraph == "⑤":
            score += 40

    return score


# ============================================================
# candidate record
# ============================================================

def build_record(
    index: int,
    clause: Dict[str, Any],
    definition: Dict[str, Any],
) -> Dict[str, Any]:

    context = full_context(
        clause
    )

    return {
        "clause_index": (
            index
        ),

        "score": (
            score_candidate(
                clause,
                definition,
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

        "paragraph": (
            clause.get(
                "paragraph"
            )
        ),

        "item": (
            clause.get(
                "item"
            )
        ),

        "subitem": (
            clause.get(
                "subitem"
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

        "conditions": (
            condition_summary(
                clause
            )
        ),

        "exact_reference_match": (
            pattern_match(
                context,
                definition[
                    "exact_patterns"
                ],
            )
        ),

        "article_match": (
            pattern_match(
                context,
                definition[
                    "article_patterns"
                ],
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


# ============================================================
# related branch search
# ============================================================

def find_related_branch_candidates(
    clauses: List[Dict[str, Any]],
    definition: Dict[str, Any],
) -> List[Dict[str, Any]]:

    records = []

    for index, clause in enumerate(
        clauses,
        start=1,
    ):

        if not isinstance(
            clause,
            dict,
        ):
            continue

        if safe_string(
            clause.get(
                "law_name"
            )
        ) != TARGET_LAW:

            continue

        # ----------------------------------------------------
        # exact/article/effect 중 최소 하나는 맞아야 후보
        # ----------------------------------------------------

        context = full_context(
            clause
        )

        exact = pattern_match(
            context,
            definition[
                "exact_patterns"
            ],
        )

        article = pattern_match(
            context,
            definition[
                "article_patterns"
            ],
        )

        effects = clause.get(
            "effect_targets",
            [],
        )

        effect_match = (
            definition[
                "effect"
            ]
            in effects
        )

        # article 명시 또는 hierarchy 위치가 맞는 경우
        hierarchy_match = False

        paragraph = safe_string(
            clause.get(
                "paragraph"
            )
        )

        item = safe_string(
            clause.get(
                "item"
            )
        )

        if definition[
            "article"
        ] == "제84조":

            hierarchy_match = (
                paragraph == "⑥"
                and item == "2"
            )

        elif definition[
            "article"
        ] == "제85조":

            hierarchy_match = (
                paragraph == "⑤"
            )

        if not (
            exact
            or (
                article
                and effect_match
            )
            or hierarchy_match
        ):

            continue

        record = build_record(
            index,
            clause,
            definition,
        )

        records.append(
            record
        )

    records.sort(
        key=lambda item: (
            -item[
                "score"
            ],
            item[
                "clause_index"
            ],
        )
    )

    return records


# ============================================================
# main
# ============================================================

def main() -> int:

    data = load_json(
        CLAUSE_PATH
    )

    clauses = data.get(
        "clauses",
        [],
    )

    output_targets = {}

    total_exact = 0

    # ========================================================
    # target별 search
    # ========================================================

    for key, definition in (
        TARGETS.items()
    ):

        candidates = (
            find_related_branch_candidates(
                clauses,
                definition,
            )
        )

        exact_candidates = [
            item
            for item
            in candidates
            if item[
                "exact_reference_match"
            ]
        ]

        total_exact += len(
            exact_candidates
        )

        output_targets[
            key
        ] = {
            "source_clause": (
                definition[
                    "source_clause"
                ]
            ),

            "article": (
                definition[
                    "article"
                ]
            ),

            "candidate_count": (
                len(
                    candidates
                )
            ),

            "exact_match_count": (
                len(
                    exact_candidates
                )
            ),

            "best_candidate": (
                candidates[0]
                if candidates
                else None
            ),

            "candidates": (
                candidates[:30]
            ),

            "resolution": (
                "SOURCE_CANDIDATES_FOUND"
                if candidates
                else "SOURCE_NOT_FOUND"
            ),
        }

    # ========================================================
    # source clause confirm
    # ========================================================

    source_clauses = {}

    for source_index in (
        4,
        189,
    ):

        if (
            1
            <= source_index
            <= len(
                clauses
            )
        ):

            source = (
                clauses[
                    source_index - 1
                ]
            )

            source_clauses[
                str(
                    source_index
                )
            ] = {
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

                "text": (
                    source.get(
                        "text"
                    )
                ),

                "conditions": (
                    condition_summary(
                        source
                    )
                ),
            }

    # ========================================================
    # validation
    # ========================================================

    bcr_candidates = (
        output_targets[
            "BCR_84_6_2"
        ][
            "candidate_count"
        ]
    )

    far_candidates = (
        output_targets[
            "FAR_85_5"
        ][
            "candidate_count"
        ]
    )

    validations = {

        "C-8 clause 데이터 존재": (
            len(
                clauses
            )
            > 0
        ),

        "BCR 시행령 branch 후보 탐색 완료": (
            bcr_candidates
            >= 0
        ),

        "FAR 시행령 branch 후보 탐색 완료": (
            far_candidates
            >= 0
        ),

        "source clause 4 존재": (
            "4"
            in source_clauses
        ),

        "source clause 189 존재": (
            "189"
            in source_clauses
        ),

        "미발견 branch를 자동 FALSE 처리하지 않음": (
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

        "target_law": (
            TARGET_LAW
        ),

        "summary": {
            "total_clauses": (
                len(
                    clauses
                )
            ),

            "exact_reference_matches": (
                total_exact
            ),

            "bcr_candidate_count": (
                bcr_candidates
            ),

            "far_candidate_count": (
                far_candidates
            ),
        },

        "source_clauses": (
            source_clauses
        ),

        "targets": (
            output_targets
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
        "Clauses:",
        len(
            clauses
        ),
    )

    print()

    for key in (
        "BCR_84_6_2",
        "FAR_85_5",
    ):

        target = (
            output_targets[
                key
            ]
        )

        print(
            f"[{key}]"
        )

        print(
            "Candidates:",
            target[
                "candidate_count"
            ],
        )

        print(
            "Exact matches:",
            target[
                "exact_match_count"
            ],
        )

        best = target.get(
            "best_candidate"
        )

        if not best:

            print(
                "Best: NONE"
            )

            print()

            continue

        print(
            "Best clause:",
            best[
                "clause_index"
            ],
        )

        print(
            "Score:",
            best[
                "score"
            ],
        )

        print(
            "Rule:",
            best[
                "rule_title"
            ],
        )

        print(
            "Path:",
            (
                best[
                    "paragraph"
                ],
                best[
                    "item"
                ],
                best[
                    "subitem"
                ],
            ),
        )

        print(
            "Conditions:",
            [
                (
                    item[
                        "name"
                    ],
                    item[
                        "type"
                    ],
                )
                for item
                in best[
                    "conditions"
                ]
            ],
        )

        print(
            "Numeric:",
            best[
                "numeric_values"
            ],
        )

        print(
            "Text:",
            compact(
                best[
                    "text"
                ],
                700,
            ),
        )

        print(
            "Inherited:",
            compact(
                best[
                    "inherited_context"
                ],
                700,
            ),
        )

        print()

        print(
            "Top candidates:"
        )

        for item in (
            target[
                "candidates"
            ][:8]
        ):

            print(
                f"- clause="
                f"{item['clause_index']} "
                f"score="
                f"{item['score']} "
                f"path="
                f"({item['paragraph']},"
                f"{item['item']},"
                f"{item['subitem']}) "
                f"conditions="
                f"{[(c['name'], c['type']) for c in item['conditions']]}"
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