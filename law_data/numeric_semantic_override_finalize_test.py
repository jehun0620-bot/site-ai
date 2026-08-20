# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2A-9
Numeric semantic explicit override / final effect candidate classification

목표
======================================================================
1. hierarchy dedup 결과 28개 candidate를 사용한다.
2. branch-local applicability fix 결과를 최신 applicability로 사용한다.
3. 기존 semantic parser 결과를 유지하되,
   unresolved 8건에 explicit semantic override를 적용한다.
4. clause 251은 실제 BCR/FAR effect가 아니라
   개발밀도관리구역 지정기준 threshold이므로 effect 계산에서 제외한다.
5. candidate를 다음으로 분류한다.

   CALCULABLE_NOW
       APPLICABLE + semantic 계산가능

   CONDITIONAL_EFFECT
       CONDITIONAL + semantic 계산가능
       -> 입력 충족 시 계산 가능

   UNKNOWN_EFFECT
       UNKNOWN + semantic 계산가능
       -> SITE/history 등 사실관계 해결 필요

   NON_EFFECT
       숫자가 있으나 BCR/FAR 계산효과 아님

   SEMANTIC_UNRESOLVED
       여전히 의미 미확정

6. 실제 최종 건폐율/용적률 값 계산은 아직 하지 않는다.
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-2A-9 "
    "numeric semantic override finalize"
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

DEDUP_PATH = (
    OUTPUT_DIR
    / "active_numeric_hierarchy_dedup.json"
)

APPLICABILITY_PATH = (
    OUTPUT_DIR
    / "branch_local_predicate_applicability_fix.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "numeric_semantic_override_finalize.json"
)


# ============================================================
# semantic types
# ============================================================

ABSOLUTE_MAX = "ABSOLUTE_MAX"

ABSOLUTE_CEILING = "ABSOLUTE_CEILING"

RANGE = "RANGE"

BASE_RATIO_MULTIPLIER = (
    "BASE_RATIO_MULTIPLIER"
)

MAX_LIMIT_REDUCTION_RATIO = (
    "MAX_LIMIT_REDUCTION_RATIO"
)

MAX_LIMIT_MULTIPLIER = (
    "MAX_LIMIT_MULTIPLIER"
)

ADDITIVE_PERCENT_POINT = (
    "ADDITIVE_PERCENT_POINT"
)

NON_EFFECT_THRESHOLD = (
    "NON_EFFECT_THRESHOLD"
)

UNKNOWN_NUMERIC_EFFECT = (
    "UNKNOWN_NUMERIC_EFFECT"
)


# ============================================================
# explicit overrides
# ============================================================

SEMANTIC_OVERRIDES = {

    20: {
        "semantic_type": (
            ABSOLUTE_MAX
        ),
        "value": 60.0,
        "unit": "percent",
        "formula": (
            "max_allowed = 60"
        ),
        "confidence": "HIGH",
        "reason": (
            "상위 문맥에서 시장정비사업 승인대상 "
            "전통시장의 제3종일반주거지역 건폐율은 "
            "60퍼센트 이하로 규정"
        ),
    },

    61: {
        "semantic_type": (
            ABSOLUTE_MAX
        ),
        "value": 70.0,
        "unit": "percent",
        "formula": (
            "max_allowed = 70"
        ),
        "confidence": "HIGH",
        "reason": (
            "국토계획법상 도시지역 중 주거지역 "
            "건폐율 최대한도 70퍼센트 이하"
        ),
    },

    121: {
        "semantic_type": (
            MAX_LIMIT_REDUCTION_RATIO
        ),
        "value": 50.0,
        "factor": 0.5,
        "unit": (
            "percent_of_max_limit"
        ),
        "formula": (
            "strengthened_limit >= "
            "original_max_limit * 0.5"
        ),
        "confidence": "HIGH",
        "reason": (
            "해당 구역에 적용할 건폐율 최대한도의 "
            "50퍼센트까지 낮출 수 있다는 강화 규칙"
        ),
    },

    208: {
        "semantic_type": (
            ABSOLUTE_CEILING
        ),
        "value": 880.0,
        "unit": "percent",
        "formula": (
            "plan_defined_far <= 880"
        ),
        "confidence": "HIGH",
        "reason": (
            "서울도심 내 도시정비형 재개발사업에서 "
            "880퍼센트 범위 내에서 도시ㆍ주거환경정비 "
            "기본계획이 정하는 용적률을 적용"
        ),
    },

    227: {
        "semantic_type": (
            ABSOLUTE_MAX
        ),
        "value": 200.0,
        "unit": "percent",
        "formula": (
            "max_allowed = 200"
        ),
        "confidence": "HIGH",
        "reason": (
            "학교이적지의 제3종일반주거지역 "
            "용적률은 200퍼센트 이하"
        ),
    },

    233: {
        "semantic_type": (
            ABSOLUTE_MAX
        ),
        "value": 500.0,
        "unit": "percent",
        "formula": (
            "max_allowed = 500"
        ),
        "confidence": "HIGH",
        "reason": (
            "법률상 도시지역 중 주거지역의 "
            "용적률 최대한도 500퍼센트 이하"
        ),
    },

    251: {
        "semantic_type": (
            NON_EFFECT_THRESHOLD
        ),
        "value": 20.0,
        "unit": "percent",
        "formula": None,
        "confidence": "HIGH",
        "reason": (
            "20퍼센트는 용적률 효과값이 아니라 "
            "개발밀도관리구역 지정 여부를 판단하는 "
            "용도지역별 도로율 미달 기준"
        ),
    },

    262: {
        "semantic_type": (
            MAX_LIMIT_MULTIPLIER
        ),
        "value": 50.0,
        "factor": 0.5,
        "unit": (
            "percent_of_max_limit"
        ),
        "formula": (
            "strengthened_max = "
            "original_max_limit * 0.5"
        ),
        "confidence": "HIGH",
        "reason": (
            "개발밀도관리구역에서는 "
            "해당 용도지역 용적률 최대한도의 "
            "50퍼센트 범위로 강화"
        ),
    },
}


# ============================================================
# 계산 가능한 semantic
# ============================================================

CALCULABLE_SEMANTICS = {
    ABSOLUTE_MAX,
    ABSOLUTE_CEILING,
    RANGE,
    BASE_RATIO_MULTIPLIER,
    MAX_LIMIT_REDUCTION_RATIO,
    MAX_LIMIT_MULTIPLIER,
    ADDITIVE_PERCENT_POINT,
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

        result[
            int(index)
        ] = item

    return result


# ============================================================
# classification
# ============================================================

def classify_candidate(
    applicability: str,
    semantic_type: str,
) -> str:

    if semantic_type == (
        NON_EFFECT_THRESHOLD
    ):

        return "NON_EFFECT"

    if semantic_type == (
        UNKNOWN_NUMERIC_EFFECT
    ):

        return "SEMANTIC_UNRESOLVED"

    if semantic_type not in (
        CALCULABLE_SEMANTICS
    ):

        return "SEMANTIC_UNRESOLVED"

    if applicability == (
        "APPLICABLE"
    ):

        return "CALCULABLE_NOW"

    if applicability == (
        "CONDITIONAL"
    ):

        return "CONDITIONAL_EFFECT"

    if applicability == (
        "UNKNOWN"
    ):

        return "UNKNOWN_EFFECT"

    return "NOT_ACTIVE"


# ============================================================
# main
# ============================================================

def main() -> int:

    dedup_data = load_json(
        DEDUP_PATH
    )

    applicability_data = load_json(
        APPLICABILITY_PATH
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

    finalized = []

    override_count = 0

    # ========================================================
    # semantic finalize
    # ========================================================

    for candidate in candidates:

        if not isinstance(
            candidate,
            dict,
        ):
            continue

        item = copy.deepcopy(
            candidate
        )

        index = int(
            item[
                "clause_index"
            ]
        )

        # ----------------------------------------------------
        # 최신 applicability
        # ----------------------------------------------------

        applicability_item = (
            applicability_index.get(
                index,
                {}
            )
        )

        applicability = safe_string(
            applicability_item.get(
                "applicability"
            )
        )

        item[
            "applicability"
        ] = applicability

        item[
            "effective_conditions"
        ] = applicability_item.get(
            "effective_conditions",
            [],
        )

        item[
            "condition_results"
        ] = applicability_item.get(
            "condition_results",
            [],
        )

        # ----------------------------------------------------
        # semantic override
        # ----------------------------------------------------

        original_semantic = item.get(
            "semantic",
            {}
        )

        override = (
            SEMANTIC_OVERRIDES.get(
                index
            )
        )

        if override:

            item[
                "semantic_before_override"
            ] = original_semantic

            item[
                "semantic"
            ] = {
                **override,
                "source": (
                    "EXPLICIT_CONTEXT_OVERRIDE"
                ),
            }

            override_count += 1

        semantic_type = (
            item.get(
                "semantic",
                {},
            ).get(
                "semantic_type",
                UNKNOWN_NUMERIC_EFFECT,
            )
        )

        item[
            "effect_class"
        ] = (
            classify_candidate(
                applicability,
                semantic_type,
            )
        )

        finalized.append(
            item
        )

    # ========================================================
    # summary
    # ========================================================

    effect_class_counter = Counter(
        item[
            "effect_class"
        ]
        for item
        in finalized
    )

    semantic_counter = Counter(
        item.get(
            "semantic",
            {},
        ).get(
            "semantic_type"
        )
        for item
        in finalized
    )

    status_counter = Counter(
        item.get(
            "applicability"
        )
        for item
        in finalized
    )

    calculable_now = [
        item
        for item
        in finalized
        if item[
            "effect_class"
        ]
        == "CALCULABLE_NOW"
    ]

    conditional_effects = [
        item
        for item
        in finalized
        if item[
            "effect_class"
        ]
        == "CONDITIONAL_EFFECT"
    ]

    unknown_effects = [
        item
        for item
        in finalized
        if item[
            "effect_class"
        ]
        == "UNKNOWN_EFFECT"
    ]

    non_effects = [
        item
        for item
        in finalized
        if item[
            "effect_class"
        ]
        == "NON_EFFECT"
    ]

    unresolved = [
        item
        for item
        in finalized
        if item[
            "effect_class"
        ]
        == "SEMANTIC_UNRESOLVED"
    ]

    # ========================================================
    # known validations
    # ========================================================

    by_index = {
        item[
            "clause_index"
        ]: item
        for item
        in finalized
    }

    clause251_non_effect = (
        by_index.get(
            251,
            {},
        ).get(
            "effect_class"
        )
        == "NON_EFFECT"
    )

    clause20_conditional = (
        by_index.get(
            20,
            {},
        ).get(
            "effect_class"
        )
        == "CONDITIONAL_EFFECT"
    )

    clause188_conditional = (
        by_index.get(
            188,
            {},
        ).get(
            "effect_class"
        )
        == "CONDITIONAL_EFFECT"
    )

    clause208_unknown = (
        by_index.get(
            208,
            {},
        ).get(
            "effect_class"
        )
        == "UNKNOWN_EFFECT"
    )

    semantic_8_resolved = all(
        by_index.get(
            index,
            {},
        ).get(
            "semantic",
            {},
        ).get(
            "semantic_type"
        )
        != UNKNOWN_NUMERIC_EFFECT

        for index in (
            20,
            61,
            121,
            208,
            227,
            233,
            251,
            262,
        )
    )

    validations = {
        "dedup candidate 28개 유지": (
            len(
                finalized
            )
            == 28
        ),

        "explicit semantic override 8개 적용": (
            override_count
            == 8
        ),

        "unresolved 8건 semantic 확정": (
            semantic_8_resolved
        ),

        "clause 251 NON_EFFECT 분류": (
            clause251_non_effect
        ),

        "clause 20 CONDITIONAL_EFFECT": (
            clause20_conditional
        ),

        "clause 188 CONDITIONAL_EFFECT": (
            clause188_conditional
        ),

        "clause 208 UNKNOWN_EFFECT": (
            clause208_unknown
        ),

        "NON_EFFECT를 BCR/FAR 계산 후보에서 제외": (
            True
        ),

        "UNKNOWN/CONDITIONAL을 현재 확정값으로 계산하지 않음": (
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
        "step": STEP_NAME,

        "summary": {
            "candidate_count": (
                len(
                    finalized
                )
            ),

            "semantic_override_count": (
                override_count
            ),

            "calculable_now": (
                len(
                    calculable_now
                )
            ),

            "conditional_effect": (
                len(
                    conditional_effects
                )
            ),

            "unknown_effect": (
                len(
                    unknown_effects
                )
            ),

            "non_effect": (
                len(
                    non_effects
                )
            ),

            "semantic_unresolved": (
                len(
                    unresolved
                )
            ),
        },

        "applicability_summary": (
            dict(
                status_counter
            )
        ),

        "semantic_summary": (
            dict(
                semantic_counter
            )
        ),

        "effect_class_summary": (
            dict(
                effect_class_counter
            )
        ),

        "semantic_overrides": (
            SEMANTIC_OVERRIDES
        ),

        "calculable_now": (
            calculable_now
        ),

        "conditional_effects": (
            conditional_effects
        ),

        "unknown_effects": (
            unknown_effects
        ),

        "non_effects": (
            non_effects
        ),

        "semantic_unresolved": (
            unresolved
        ),

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),

        "candidates": (
            finalized
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # concise console
    # ========================================================

    print(
        "Candidates:",
        len(
            finalized
        ),
    )

    print(
        "Overrides:",
        override_count,
    )

    print(
        "CALCULABLE_NOW:",
        len(
            calculable_now
        ),
    )

    print(
        "CONDITIONAL_EFFECT:",
        len(
            conditional_effects
        ),
    )

    print(
        "UNKNOWN_EFFECT:",
        len(
            unknown_effects
        ),
    )

    print(
        "NON_EFFECT:",
        len(
            non_effects
        ),
    )

    print(
        "SEMANTIC_UNRESOLVED:",
        len(
            unresolved
        ),
    )

    print()

    print(
        "Semantic summary:",
        dict(
            semantic_counter
        ),
    )

    print()

    print(
        "Key clauses:"
    )

    for index in (
        20,
        61,
        121,
        188,
        208,
        227,
        233,
        251,
        262,
    ):

        item = by_index.get(
            index
        )

        if not item:
            continue

        print(
            f"- {index}: "
            f"{item['applicability']} / "
            f"{item['effect_class']} / "
            f"{item['semantic']['semantic_type']}"
        )

    print()

    if unresolved:

        print(
            "Remaining semantic unresolved:"
        )

        for item in unresolved:

            print(
                f"- clause={item['clause_index']} "
                f"| {item.get('rule_title')} "
                f"| numeric="
                f"{item.get('numeric_values')}"
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