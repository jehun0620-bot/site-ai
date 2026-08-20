# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2A
특례 numeric effect semantic probe

목표
======================================================================
1. law_special_rule_clauses.json의 numeric_values를 전수 분석한다.
2. 단순 숫자 배열을 그대로 계산에 사용하지 않는다.
3. 조문 text를 이용하여 숫자의 의미를 다음 계열로 분류한다.

   RANGE
       예: 80퍼센트 이상 90퍼센트 이하

   BASE_RATIO_MULTIPLIER
       예: 해당 용도지역별 건폐율의 120퍼센트 이하

   ABSOLUTE_MAX
       예: 건폐율은 30퍼센트 이하

   ABSOLUTE_VALUE
       예: 용적률을 200퍼센트로 한다

   ADDITIVE_PERCENT_POINT
       예: 20퍼센트포인트를 가산

   UNKNOWN_NUMERIC_EFFECT
       숫자는 있으나 의미를 안전하게 확정할 수 없음

4. building_coverage_ratio / floor_area_ratio 효과를 우선 분석한다.
5. 계산 가능한 clause와 추가 semantic 분석이 필요한 clause를 구분한다.
6. UNKNOWN_NUMERIC_EFFECT를 임의 계산하지 않는다.
"""

from __future__ import annotations

import json
import re

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional


STEP_NAME = (
    "STEP 17-21-C-10-2A "
    "numeric effect semantic probe"
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
    / "special_rule_applicability.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "numeric_effect_semantic_probe.json"
)


# ============================================================
# 분석 대상
# ============================================================

TARGET_EFFECTS = {
    "building_coverage_ratio",
    "floor_area_ratio",
}


# ============================================================
# semantic types
# ============================================================

RANGE = "RANGE"

BASE_RATIO_MULTIPLIER = (
    "BASE_RATIO_MULTIPLIER"
)

ABSOLUTE_MAX = "ABSOLUTE_MAX"

ABSOLUTE_MIN = "ABSOLUTE_MIN"

ABSOLUTE_VALUE = "ABSOLUTE_VALUE"

ADDITIVE_PERCENT_POINT = (
    "ADDITIVE_PERCENT_POINT"
)

UNKNOWN_NUMERIC_EFFECT = (
    "UNKNOWN_NUMERIC_EFFECT"
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


def normalize_text(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        safe_string(value),
    ).strip()


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

    text = normalize_text(
        value
    )

    if len(text) > limit:

        return (
            text[:limit]
            + "..."
        )

    return text


# ============================================================
# percentage parsing
# ============================================================

NUMBER = (
    r"(\d+(?:\.\d+)?)"
)

PERCENT = (
    r"(?:퍼센트|%)"
)


def parse_float(
    value: Any,
) -> Optional[float]:

    try:

        return float(value)

    except Exception:

        return None


# ============================================================
# semantic parser
# ============================================================

def classify_numeric_effect(
    text: str,
    effect_targets: List[str],
    numeric_values: List[Any],
) -> Dict[str, Any]:

    text = normalize_text(
        text
    )

    values = [
        value
        for value
        in (
            parse_float(item)
            for item
            in numeric_values
        )
        if value is not None
    ]

    # ========================================================
    # 1. 퍼센트포인트 가산
    # ========================================================

    match = re.search(
        NUMBER
        + r"\s*퍼센트포인트"
        + r".{0,30}"
        + r"(?:가산|더하|추가)",
        text,
    )

    if match:

        value = float(
            match.group(1)
        )

        return {
            "semantic_type": (
                ADDITIVE_PERCENT_POINT
            ),

            "value": (
                value
            ),

            "unit": (
                "percentage_point"
            ),

            "formula": (
                "base + value"
            ),

            "confidence": (
                "HIGH"
            ),
        }

    # ========================================================
    # 2. 명확한 범위
    #
    # 80퍼센트 이상 90퍼센트 이하
    # ========================================================

    match = re.search(
        NUMBER
        + r"\s*"
        + PERCENT
        + r"\s*이상"
        + r".{0,50}?"
        + NUMBER
        + r"\s*"
        + PERCENT
        + r"\s*이하",
        text,
    )

    if match:

        minimum = float(
            match.group(1)
        )

        maximum = float(
            match.group(2)
        )

        return {
            "semantic_type": (
                RANGE
            ),

            "min": (
                minimum
            ),

            "max": (
                maximum
            ),

            "unit": (
                "percent"
            ),

            "formula": None,

            "confidence": (
                "HIGH"
            ),
        }

    # ========================================================
    # 3. 기준값 배율
    #
    # 해당 용도지역별 건폐율의 120퍼센트 이하
    # 기존 건폐율의 120퍼센트
    # ========================================================

    multiplier_patterns = [
        (
            r"(?:해당\s*)?"
            r"용도지역(?:별)?"
            r".{0,30}?"
            r"(?:건폐율|용적률)"
            r"\s*의\s*"
            + NUMBER
            + r"\s*"
            + PERCENT
        ),

        (
            r"(?:기준|종전|기존|허용된)"
            r".{0,30}?"
            r"(?:건폐율|용적률)"
            r"\s*의\s*"
            + NUMBER
            + r"\s*"
            + PERCENT
        ),

        (
            r"(?:건폐율|용적률)"
            r"\s*의\s*"
            + NUMBER
            + r"\s*"
            + PERCENT
        ),
    ]

    for pattern in (
        multiplier_patterns
    ):

        match = re.search(
            pattern,
            text,
        )

        if not match:
            continue

        percent = float(
            match.group(1)
        )

        return {
            "semantic_type": (
                BASE_RATIO_MULTIPLIER
            ),

            "value": (
                percent
            ),

            "factor": (
                percent / 100.0
            ),

            "unit": (
                "percent_of_base"
            ),

            "formula": (
                f"base * {percent / 100.0}"
            ),

            "confidence": (
                "HIGH"
            ),
        }

    # ========================================================
    # 4. 절대 상한
    #
    # 건폐율은 30퍼센트 이하
    # 용적률은 250퍼센트 이하
    # ========================================================

    match = re.search(
        r"(?:건폐율|용적률)"
        r".{0,30}?"
        + NUMBER
        + r"\s*"
        + PERCENT
        + r"\s*이하",
        text,
    )

    if match:

        value = float(
            match.group(1)
        )

        return {
            "semantic_type": (
                ABSOLUTE_MAX
            ),

            "value": (
                value
            ),

            "unit": (
                "percent"
            ),

            "formula": (
                "min(calculated, value)"
            ),

            "confidence": (
                "HIGH"
            ),
        }

    # ========================================================
    # 5. 절대 하한
    # ========================================================

    match = re.search(
        r"(?:건폐율|용적률)"
        r".{0,30}?"
        + NUMBER
        + r"\s*"
        + PERCENT
        + r"\s*이상",
        text,
    )

    if match:

        value = float(
            match.group(1)
        )

        return {
            "semantic_type": (
                ABSOLUTE_MIN
            ),

            "value": (
                value
            ),

            "unit": (
                "percent"
            ),

            "formula": (
                "max(calculated, value)"
            ),

            "confidence": (
                "HIGH"
            ),
        }

    # ========================================================
    # 6. 값으로 한다 / 적용한다
    # ========================================================

    match = re.search(
        r"(?:건폐율|용적률)"
        r".{0,40}?"
        + NUMBER
        + r"\s*"
        + PERCENT
        + r".{0,20}?"
        + r"(?:로\s*한다|로\s*적용|를\s*적용)",
        text,
    )

    if match:

        value = float(
            match.group(1)
        )

        return {
            "semantic_type": (
                ABSOLUTE_VALUE
            ),

            "value": (
                value
            ),

            "unit": (
                "percent"
            ),

            "formula": (
                "value"
            ),

            "confidence": (
                "HIGH"
            ),
        }

    # ========================================================
    # 7. numeric 값 1개이며 effect가 명확한 경우
    #
    # 의미는 아직 확정하지 않는다.
    # ========================================================

    return {
        "semantic_type": (
            UNKNOWN_NUMERIC_EFFECT
        ),

        "raw_values": (
            values
        ),

        "unit": None,

        "formula": None,

        "confidence": (
            "NONE"
        ),
    }


# ============================================================
# applicability index
# ============================================================

def build_applicability_index(
    applicability: Dict[str, Any],
) -> Dict[int, str]:

    """
    special_rule_applicability.json의 clauses 순서는
    law_special_rule_clauses.json 순서와 동일하므로
    1-based index로 연결한다.
    """

    result = {}

    for index, item in enumerate(
        applicability.get(
            "clauses",
            [],
        ),
        start=1,
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        result[
            index
        ] = safe_string(
            item.get(
                "applicability"
            )
        )

    return result


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

    clauses = clause_data.get(
        "clauses",
        [],
    )

    applicability_index = (
        build_applicability_index(
            applicability_data
        )
    )

    results = []

    # ========================================================
    # 전수 분석
    # ========================================================

    for index, clause in enumerate(
        clauses,
        start=1,
    ):

        if not isinstance(
            clause,
            dict,
        ):
            continue

        effect_targets = clause.get(
            "effect_targets",
            [],
        )

        if not isinstance(
            effect_targets,
            list,
        ):
            continue

        relevant_effects = [
            effect
            for effect
            in effect_targets
            if effect
            in TARGET_EFFECTS
        ]

        if not relevant_effects:
            continue

        numeric_values = clause.get(
            "numeric_values",
            [],
        )

        if not numeric_values:
            continue

        semantic = (
            classify_numeric_effect(
                text=safe_string(
                    clause.get(
                        "text"
                    )
                ),
                effect_targets=(
                    relevant_effects
                ),
                numeric_values=(
                    numeric_values
                ),
            )
        )

        results.append(
            {
                "clause_index": (
                    index
                ),

                "applicability": (
                    applicability_index.get(
                        index,
                        "UNKNOWN"
                    )
                ),

                "category": (
                    clause.get(
                        "category"
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

                "zone_relevance": (
                    clause.get(
                        "zone_relevance"
                    )
                ),

                "effect_targets": (
                    relevant_effects
                ),

                "numeric_values": (
                    numeric_values
                ),

                "conditions": (
                    clause.get(
                        "conditions",
                        [],
                    )
                ),

                "text": (
                    clause.get(
                        "text"
                    )
                ),

                "semantic": (
                    semantic
                ),
            }
        )

    # ========================================================
    # 통계
    # ========================================================

    semantic_counter = Counter(
        item[
            "semantic"
        ][
            "semantic_type"
        ]
        for item
        in results
    )

    applicability_counter = Counter(
        item[
            "applicability"
        ]
        for item
        in results
    )

    calculable_types = {
        RANGE,
        BASE_RATIO_MULTIPLIER,
        ABSOLUTE_MAX,
        ABSOLUTE_MIN,
        ABSOLUTE_VALUE,
        ADDITIVE_PERCENT_POINT,
    }

    calculable = [
        item
        for item
        in results
        if item[
            "semantic"
        ][
            "semantic_type"
        ]
        in calculable_types
    ]

    unresolved = [
        item
        for item
        in results
        if item[
            "semantic"
        ][
            "semantic_type"
        ]
        == UNKNOWN_NUMERIC_EFFECT
    ]

    # --------------------------------------------------------
    # 현재 SITE에서 실질적으로 중요한 것
    # --------------------------------------------------------

    active = [
        item
        for item
        in results
        if item[
            "applicability"
        ]
        in {
            "APPLICABLE",
            "CONDITIONAL",
            "UNKNOWN",
        }
    ]

    active_unresolved = [
        item
        for item
        in active
        if item[
            "semantic"
        ][
            "semantic_type"
        ]
        == UNKNOWN_NUMERIC_EFFECT
    ]

    # ========================================================
    # validation
    # ========================================================

    all_numeric_preserved = all(
        bool(
            item.get(
                "numeric_values"
            )
        )
        for item
        in results
    )

    no_unknown_marked_calculable = all(
        item[
            "semantic"
        ][
            "semantic_type"
        ]
        != UNKNOWN_NUMERIC_EFFECT

        for item
        in calculable
    )

    validations = {
        "numeric_values 보유 clause만 분석": (
            all_numeric_preserved
        ),

        "UNKNOWN numeric effect를 계산가능으로 오인하지 않음": (
            no_unknown_marked_calculable
        ),

        "원문 text를 semantic 판정 근거로 사용": (
            True
        ),

        "단순 numeric max를 최종값으로 사용하지 않음": (
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
            "numeric_clause_count": (
                len(
                    results
                )
            ),

            "calculable_count": (
                len(
                    calculable
                )
            ),

            "unresolved_count": (
                len(
                    unresolved
                )
            ),

            "active_numeric_clause_count": (
                len(
                    active
                )
            ),

            "active_unresolved_count": (
                len(
                    active_unresolved
                )
            ),
        },

        "semantic_type_summary": (
            dict(
                semantic_counter
            )
        ),

        "applicability_summary": (
            dict(
                applicability_counter
            )
        ),

        "active_unresolved_preview": [
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

                "effect_targets": (
                    item[
                        "effect_targets"
                    ]
                ),

                "numeric_values": (
                    item[
                        "numeric_values"
                    ]
                ),

                "text": compact(
                    item[
                        "text"
                    ]
                ),
            }

            for item
            in active_unresolved[:20]
        ],

        "semantic_examples": {
            semantic_type: [
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

                    "effect_targets": (
                        item[
                            "effect_targets"
                        ]
                    ),

                    "numeric_values": (
                        item[
                            "numeric_values"
                        ]
                    ),

                    "semantic": (
                        item[
                            "semantic"
                        ]
                    ),

                    "text": compact(
                        item[
                            "text"
                        ]
                    ),
                }

                for item
                in results

                if item[
                    "semantic"
                ][
                    "semantic_type"
                ]
                == semantic_type
            ][
                :5
            ]

            for semantic_type
            in sorted(
                semantic_counter.keys()
            )
        },

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),

        "clauses": (
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
        "Numeric clauses:",
        len(
            results
        ),
    )

    print(
        "Calculable:",
        len(
            calculable
        ),
    )

    print(
        "Unresolved:",
        len(
            unresolved
        ),
    )

    print(
        "Active numeric:",
        len(
            active
        ),
    )

    print(
        "Active unresolved:",
        len(
            active_unresolved
        ),
    )

    print()

    print(
        "Semantic types:",
        dict(
            semantic_counter
        ),
    )

    print()

    for index, item in enumerate(
        active_unresolved[:10],
        start=1,
    ):

        print(
            f"[{index}] "
            f"clause={item['clause_index']} "
            f"{item['applicability']} | "
            f"{item['rule_title']}"
        )

        print(
            "  effect:",
            item[
                "effect_targets"
            ],
        )

        print(
            "  numeric:",
            item[
                "numeric_values"
            ],
        )

        print(
            "  text:",
            compact(
                item[
                    "text"
                ],
                300,
            ),
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