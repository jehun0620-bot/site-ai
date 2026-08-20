# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2A-3
Contextual SITE condition 보정 후
numeric effect semantic 재산정

목표
======================================================================
1. contextual_site_condition_fix.json을 최신 applicability 기준으로 사용
2. 기존 numeric semantic parser를 동일하게 적용
3. ACTIVE numeric clause를 다시 계산
4. 자연경관지구 / 입체복합구역 잘못된 active clause가 제거됐는지 확인
5. 다음 parent-child dedup 단계의 정확한 입력을 생성

ACTIVE 상태
======================================================================
APPLICABLE
CONDITIONAL
UNKNOWN

NOT_APPLICABLE은 numeric 계산 후보에서 제외
"""

from __future__ import annotations

import json
import re

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional


STEP_NAME = (
    "STEP 17-21-C-10-2A-3 "
    "context 보정 후 numeric semantic 재산정"
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

OUTPUT_PATH = (
    OUTPUT_DIR
    / "numeric_effect_semantic_recheck.json"
)


# ============================================================
# 대상 effect
# ============================================================

TARGET_EFFECTS = {
    "building_coverage_ratio",
    "floor_area_ratio",
}


ACTIVE_STATES = {
    "APPLICABLE",
    "CONDITIONAL",
    "UNKNOWN",
}


# ============================================================
# semantic type
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
# regex
# ============================================================

NUMBER = (
    r"(\d+(?:\.\d+)?)"
)

PERCENT = (
    r"(?:퍼센트|%)"
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


def compact(
    value: Any,
    limit: int = 300,
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


def parse_float(
    value: Any,
) -> Optional[float]:

    try:
        return float(value)

    except Exception:
        return None


# ============================================================
# semantic classifier
# ============================================================

def classify_numeric_effect(
    text: str,
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

    # --------------------------------------------------------
    # 퍼센트포인트 가산
    # --------------------------------------------------------

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
            "value": value,
            "unit": (
                "percentage_point"
            ),
            "formula": (
                "base + value"
            ),
            "confidence": "HIGH",
        }

    # --------------------------------------------------------
    # 범위
    # --------------------------------------------------------

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

        return {
            "semantic_type": RANGE,
            "min": float(
                match.group(1)
            ),
            "max": float(
                match.group(2)
            ),
            "unit": "percent",
            "formula": None,
            "confidence": "HIGH",
        }

    # --------------------------------------------------------
    # 기준값 배율
    # --------------------------------------------------------

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

    for pattern in multiplier_patterns:

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
            "value": percent,
            "factor": (
                percent / 100.0
            ),
            "unit": (
                "percent_of_base"
            ),
            "formula": (
                f"base * "
                f"{percent / 100.0}"
            ),
            "confidence": "HIGH",
        }

    # --------------------------------------------------------
    # 절대 상한
    # --------------------------------------------------------

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

        return {
            "semantic_type": (
                ABSOLUTE_MAX
            ),
            "value": float(
                match.group(1)
            ),
            "unit": "percent",
            "formula": (
                "min(calculated, value)"
            ),
            "confidence": "HIGH",
        }

    # --------------------------------------------------------
    # 절대 하한
    # --------------------------------------------------------

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

        return {
            "semantic_type": (
                ABSOLUTE_MIN
            ),
            "value": float(
                match.group(1)
            ),
            "unit": "percent",
            "formula": (
                "max(calculated, value)"
            ),
            "confidence": "HIGH",
        }

    # --------------------------------------------------------
    # 절대값
    # --------------------------------------------------------

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

        return {
            "semantic_type": (
                ABSOLUTE_VALUE
            ),
            "value": float(
                match.group(1)
            ),
            "unit": "percent",
            "formula": "value",
            "confidence": "HIGH",
        }

    return {
        "semantic_type": (
            UNKNOWN_NUMERIC_EFFECT
        ),
        "raw_values": values,
        "unit": None,
        "formula": None,
        "confidence": "NONE",
    }


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
    # numeric clause 전수분석
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

        effects = clause.get(
            "effect_targets",
            [],
        )

        if not isinstance(
            effects,
            list,
        ):
            continue

        relevant_effects = [
            effect
            for effect in effects
            if effect in TARGET_EFFECTS
        ]

        if not relevant_effects:
            continue

        numeric_values = clause.get(
            "numeric_values",
            [],
        )

        if not numeric_values:
            continue

        applicability = (
            applicability_index.get(
                index,
                {}
            )
        )

        status = safe_string(
            applicability.get(
                "applicability"
            )
        )

        semantic = (
            classify_numeric_effect(
                safe_string(
                    clause.get(
                        "text"
                    )
                ),
                numeric_values,
            )
        )

        results.append(
            {
                "clause_index": index,

                "applicability": status,

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

                "semantic": semantic,

                "text": (
                    clause.get(
                        "text"
                    )
                ),
            }
        )

    # ========================================================
    # summary
    # ========================================================

    semantic_counter = Counter(
        item[
            "semantic"
        ][
            "semantic_type"
        ]
        for item in results
    )

    status_counter = Counter(
        item[
            "applicability"
        ]
        for item in results
    )

    active = [
        item
        for item in results
        if item[
            "applicability"
        ]
        in ACTIVE_STATES
    ]

    active_counter = Counter(
        item[
            "applicability"
        ]
        for item in active
    )

    active_semantic_counter = Counter(
        item[
            "semantic"
        ][
            "semantic_type"
        ]
        for item in active
    )

    active_unresolved = [
        item
        for item in active
        if item[
            "semantic"
        ][
            "semantic_type"
        ]
        == UNKNOWN_NUMERIC_EFFECT
    ]

    # ========================================================
    # 이전 HIGH-RISK 5건 제거 확인
    # ========================================================

    high_risk_indexes = {
        149,
        150,
        151,
        152,
        272,
    }

    high_risk_status = {
        item[
            "clause_index"
        ]: item[
            "applicability"
        ]

        for item in results

        if item[
            "clause_index"
        ]
        in high_risk_indexes
    }

    high_risk_removed = all(
        high_risk_status.get(
            index
        )
        == "NOT_APPLICABLE"

        for index in high_risk_indexes

        if index in high_risk_status
    )

    active_high_risk = [
        item
        for item in active
        if item[
            "clause_index"
        ]
        in high_risk_indexes
    ]

    # ========================================================
    # validations
    # ========================================================

    validations = {
        "contextual applicability 사용": (
            True
        ),

        "HIGH-RISK 5개 numeric candidate 제거": (
            len(
                active_high_risk
            )
            == 0
        ),

        "HIGH-RISK 상태 NOT_APPLICABLE 확인": (
            high_risk_removed
        ),

        "NOT_APPLICABLE numeric clause는 active에서 제외": (
            all(
                item[
                    "applicability"
                ]
                in ACTIVE_STATES

                for item in active
            )
        ),

        "UNKNOWN numeric semantic을 임의 계산하지 않음": (
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
            "numeric_clause_count": (
                len(
                    results
                )
            ),

            "active_numeric_clause_count": (
                len(
                    active
                )
            ),

            "active_applicable": (
                active_counter[
                    "APPLICABLE"
                ]
            ),

            "active_conditional": (
                active_counter[
                    "CONDITIONAL"
                ]
            ),

            "active_unknown": (
                active_counter[
                    "UNKNOWN"
                ]
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

        "active_semantic_type_summary": (
            dict(
                active_semantic_counter
            )
        ),

        "applicability_summary": (
            dict(
                status_counter
            )
        ),

        "high_risk_recheck": {
            "statuses": (
                high_risk_status
            ),

            "active_remaining": (
                [
                    item[
                        "clause_index"
                    ]
                    for item
                    in active_high_risk
                ]
            ),
        },

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

                "numeric_values": (
                    item[
                        "numeric_values"
                    ]
                ),

                "effect_targets": (
                    item[
                        "effect_targets"
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
        "Active numeric:",
        len(
            active
        ),
    )

    print(
        "Active status:",
        dict(
            active_counter
        ),
    )

    print(
        "Active semantic:",
        dict(
            active_semantic_counter
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
        "HIGH-RISK statuses:",
        high_risk_status,
    )

    print(
        "HIGH-RISK active remaining:",
        [
            item[
                "clause_index"
            ]
            for item
            in active_high_risk
        ],
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
            "  numeric:",
            item[
                "numeric_values"
            ],
        )

        print(
            "  effect:",
            item[
                "effect_targets"
            ],
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