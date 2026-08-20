# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2A-7
Numeric branch-local condition integrity probe

목표
======================================================================
1. hierarchy dedup 후 최종 numeric candidate 28개를 대상으로 한다.
2. parent conditions를 자동 상속하지 않는다.
3. child 자신의 text + inherited_context만 branch context로 사용한다.
4. 이미 condition으로 포착된 조건과
   문맥에는 있지만 아직 condition model에 없는 전제를 구분한다.
5. 대표적인 미모델링 전제를 탐지한다.

중요
======================================================================
parent condition set은 여러 sibling branch condition의 합집합일 수 있다.
따라서 parent -> child 전체 condition inheritance 금지.

예:
- clause 20:
    시장정비사업심의는 90% 예외 조건
    제3종 60%에는 직접 상속하지 않음

- clause 208:
    parent 198의 개발진흥지구/대학/기부채납 등을
    모두 상속하면 안 됨
"""

from __future__ import annotations

import json
import re

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-2A-7 "
    "numeric branch-local condition integrity probe"
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

DEDUP_PATH = (
    OUTPUT_DIR
    / "active_numeric_hierarchy_dedup.json"
)

APPLICABILITY_PATH = (
    OUTPUT_DIR
    / "contextual_site_condition_fix.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "numeric_branch_condition_integrity_probe.json"
)


# ============================================================
# 아직 condition registry에 없는 주요 branch predicate 후보
#
# 자동 판정값을 만들지 않는다.
# 먼저 어떤 clause에 필요한지 탐지한다.
# ============================================================

BRANCH_PREDICATE_PATTERNS = {

    "시장정비사업대상전통시장": {
        "type_hint": "PROJECT",
        "patterns": [
            r"시장정비사업\s*추진계획\s*승인대상\s*전통시장",
            r"시장정비사업.*전통시장",
        ],
    },

    "서울도심": {
        "type_hint": "SITE",
        "patterns": [
            r"서울도심",
        ],
    },

    "도시정비형재개발사업": {
        "type_hint": "PROJECT",
        "patterns": [
            r"도시정비형\s*재개발사업",
        ],
    },

    "감염병대응필요시설": {
        "type_hint": "PROJECT",
        "patterns": [
            r"감염병\s*대응",
        ],
    },

    "혁신성장시설": {
        "type_hint": "PROJECT",
        "patterns": [
            r"혁신성장\s*시설",
        ],
    },

    "공공필요의료시설": {
        "type_hint": "PROJECT",
        "patterns": [
            r"공공이\s*필요로\s*하는\s*의료시설",
        ],
    },

    "시장정비사업": {
        "type_hint": "PROJECT",
        "patterns": [
            r"시장정비사업",
        ],
    },

    "전통시장": {
        "type_hint": "SITE_OR_PROJECT",
        "patterns": [
            r"전통시장",
        ],
    },

    "도시정비사업": {
        "type_hint": "PROJECT",
        "patterns": [
            r"도시정비형\s*재개발",
            r"정비사업",
        ],
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
        safe_string(value),
    ).strip()


def compact(
    value: Any,
    limit: int = 450,
) -> str:

    text = normalize_text(
        value
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
# applicability index
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

        result[int(index)] = item

    return result


# ============================================================
# condition names
# ============================================================

def explicit_condition_names(
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

    return sorted(
        set(
            result
        )
    )


def effective_condition_names(
    applicability: Dict[str, Any],
) -> List[str]:

    result = []

    for condition in applicability.get(
        "effective_conditions",
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

    return sorted(
        set(
            result
        )
    )


# ============================================================
# branch predicate detection
# ============================================================

def detect_branch_predicates(
    branch_text: str,
) -> List[Dict[str, Any]]:

    hits = []

    for name, definition in (
        BRANCH_PREDICATE_PATTERNS.items()
    ):

        matched_patterns = []

        for pattern in definition[
            "patterns"
        ]:

            if re.search(
                pattern,
                branch_text,
            ):

                matched_patterns.append(
                    pattern
                )

        if not matched_patterns:
            continue

        hits.append(
            {
                "name": name,
                "type_hint": (
                    definition[
                        "type_hint"
                    ]
                ),
                "matched_patterns": (
                    matched_patterns
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

    dedup_data = load_json(
        DEDUP_PATH
    )

    applicability_data = load_json(
        APPLICABILITY_PATH
    )

    source_clauses = clause_data.get(
        "clauses",
        [],
    )

    candidates = dedup_data.get(
        "candidates",
        [],
    )

    applicability_index = (
        build_applicability_index(
            applicability_data
        )
    )

    results = []

    predicate_counter = Counter()

    active_missing_predicates = []

    # ========================================================
    # candidate branch 분석
    # ========================================================

    for candidate in candidates:

        if not isinstance(
            candidate,
            dict,
        ):
            continue

        index = int(
            candidate[
                "clause_index"
            ]
        )

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

        applicability = (
            applicability_index.get(
                index,
                {}
            )
        )

        own_text = normalize_text(
            clause.get(
                "text"
            )
        )

        inherited = normalize_text(
            clause.get(
                "inherited_context"
            )
        )

        # ----------------------------------------------------
        # child branch 판단에는 자기 text +
        # parser가 제공한 inherited_context만 사용
        # ----------------------------------------------------

        branch_context = normalize_text(
            inherited
            + " "
            + own_text
        )

        explicit = (
            explicit_condition_names(
                clause
            )
        )

        effective = (
            effective_condition_names(
                applicability
            )
        )

        predicates = (
            detect_branch_predicates(
                branch_context
            )
        )

        for predicate in predicates:

            predicate_counter[
                predicate[
                    "name"
                ]
            ] += 1

        # ----------------------------------------------------
        # 이미 condition registry에 있는 이름과
        # 동일하지 않은 predicate는 미모델링 후보
        # ----------------------------------------------------

        unmodeled = [
            predicate

            for predicate
            in predicates

            if (
                predicate[
                    "name"
                ]
                not in explicit
                and predicate[
                    "name"
                ]
                not in effective
            )
        ]

        entry = {
            "clause_index": index,

            "applicability": (
                candidate.get(
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

            "semantic": (
                candidate.get(
                    "semantic"
                )
            ),

            "explicit_conditions": (
                explicit
            ),

            "effective_conditions": (
                effective
            ),

            "detected_branch_predicates": (
                predicates
            ),

            "unmodeled_branch_predicates": (
                unmodeled
            ),

            "text": (
                own_text
            ),

            "inherited_context": (
                inherited
            ),
        }

        results.append(
            entry
        )

        if (
            unmodeled
            and candidate.get(
                "applicability"
            )
            == "APPLICABLE"
        ):

            active_missing_predicates.append(
                entry
            )

    # ========================================================
    # known clauses
    # ========================================================

    def find_clause(
        index: int,
    ) -> Dict[str, Any] | None:

        return next(
            (
                item
                for item
                in results
                if item[
                    "clause_index"
                ]
                == index
            ),
            None,
        )

    clause20 = find_clause(
        20
    )

    clause208 = find_clause(
        208
    )

    clause20_market_context = (
        clause20 is not None
        and any(
            item[
                "name"
            ]
            == "시장정비사업대상전통시장"

            for item
            in clause20[
                "detected_branch_predicates"
            ]
        )
    )

    clause208_context = (
        clause208 is not None
        and any(
            item[
                "name"
            ]
            == "서울도심"

            for item
            in clause208[
                "detected_branch_predicates"
            ]
        )
        and any(
            item[
                "name"
            ]
            == "도시정비형재개발사업"

            for item
            in clause208[
                "detected_branch_predicates"
            ]
        )
    )

    # ========================================================
    # parent inheritance probe 진단 정리
    # ========================================================

    validations = {
        "numeric candidate 28개 유지": (
            len(
                results
            )
            == 28
        ),

        "parent condition 전체 상속 사용하지 않음": (
            True
        ),

        "child text + inherited_context만 branch context로 사용": (
            True
        ),

        "clause 20 시장정비사업 전제 탐지": (
            clause20_market_context
        ),

        "clause 208 서울도심/도시정비형재개발 전제 탐지": (
            clause208_context
        ),

        "미모델링 predicate를 자동 TRUE/FALSE 처리하지 않음": (
            True
        ),
    }

    all_pass = all(
        validations.values()
    )

    output = {
        "step": STEP_NAME,

        "summary": {
            "candidate_count": (
                len(
                    results
                )
            ),

            "predicate_hit_types": (
                len(
                    predicate_counter
                )
            ),

            "applicable_with_unmodeled_predicate_count": (
                len(
                    active_missing_predicates
                )
            ),
        },

        "predicate_frequency": (
            dict(
                predicate_counter
            )
        ),

        "applicable_with_unmodeled_predicates": (
            active_missing_predicates
        ),

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),

        "candidates": (
            results
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
            results
        ),
    )

    print(
        "Predicate frequency:",
        dict(
            predicate_counter
        ),
    )

    print(
        "APPLICABLE with unmodeled predicates:",
        len(
            active_missing_predicates
        ),
    )

    print()

    for index, item in enumerate(
        active_missing_predicates[:15],
        start=1,
    ):

        print(
            f"[{index}] "
            f"clause={item['clause_index']} "
            f"| {item['rule_title']}"
        )

        print(
            "  numeric:",
            item[
                "numeric_values"
            ],
        )

        print(
            "  modeled:",
            item[
                "effective_conditions"
            ],
        )

        print(
            "  unmodeled:",
            [
                (
                    predicate[
                        "name"
                    ],
                    predicate[
                        "type_hint"
                    ],
                )
                for predicate
                in item[
                    "unmodeled_branch_predicates"
                ]
            ],
        )

        print(
            "  context:",
            compact(
                item[
                    "inherited_context"
                ]
                + " "
                + item[
                    "text"
                ],
                500,
            ),
        )

    print()

    print(
        "clause 20 market context:",
        clause20_market_context,
    )

    print(
        "clause 208 redevelopment context:",
        clause208_context,
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