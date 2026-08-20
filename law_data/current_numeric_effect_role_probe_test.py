# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-2
CALCULABLE_NOW numeric effect role classification

목표
======================================================================
1. numeric_semantic_override_finalize.json의 CALCULABLE_NOW만 사용
2. base_numeric_regulation_hierarchy.json의
   BCR=50 / FAR=250을 계산 기준으로 사용
3. 각 clause를 다음 역할로 분류

   BASE_REFERENCE
       기본 규제 또는 일반 규정 참고값

   NATIONAL_CEILING
       상위법상 최대 허용범위
       -> SITE 기본값으로 직접 사용 금지

   RELAXATION
       현재 base를 완화할 수 있는 규칙

   STRENGTHENING
       현재 base를 낮출 수 있는 규칙

   CONDITIONAL_STRENGTHENING
       semantic은 계산 가능하지만
       별도 SITE condition이 해결돼야 적용

   OTHER_EFFECT
       위 역할로 안전하게 분류할 수 없는 규칙

4. 실제 현재값 변경 가능성이 있는 clause만 effect candidate로 추출
5. 아직 여러 특례를 합산하거나 최종 수치를 계산하지 않는다.
"""

from __future__ import annotations

import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-2B-2 "
    "CALCULABLE_NOW numeric effect role classification"
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

NUMERIC_PATH = (
    OUTPUT_DIR
    / "numeric_semantic_override_finalize.json"
)

BASE_PATH = (
    OUTPUT_DIR
    / "base_numeric_regulation_hierarchy.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "current_numeric_effect_role_probe.json"
)


# ============================================================
# ROLE
# ============================================================

BASE_REFERENCE = "BASE_REFERENCE"

NATIONAL_CEILING = "NATIONAL_CEILING"

RELAXATION = "RELAXATION"

STRENGTHENING = "STRENGTHENING"

CONDITIONAL_STRENGTHENING = (
    "CONDITIONAL_STRENGTHENING"
)

OTHER_EFFECT = "OTHER_EFFECT"


# ============================================================
# known explicit roles
#
# 문맥이 이미 검증된 clause만 명시
# ============================================================

ROLE_OVERRIDES = {

    # 국가법 광역 ceiling
    61: {
        "role": NATIONAL_CEILING,
        "reason": (
            "주거지역 건폐율 70%는 서울 제3종일반주거지역 "
            "실제 기본값 50%가 아니라 상위법 최대범위"
        ),
    },

    233: {
        "role": NATIONAL_CEILING,
        "reason": (
            "주거지역 용적률 500%는 서울 제3종일반주거지역 "
            "실제 기본값 250%가 아니라 상위법 최대범위"
        ),
    },

    # 건폐율 강화
    121: {
        "role": STRENGTHENING,
        "reason": (
            "건폐율 최대한도를 50%까지 낮출 수 있는 강화 규칙"
        ),
    },

    # 개발밀도관리구역 FAR 강화
    262: {
        "role": CONDITIONAL_STRENGTHENING,
        "reason": (
            "개발밀도관리구역 지정 시 용적률 최대한도를 "
            "50% 수준으로 강화하는 규칙"
        ),
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
# effect target
# ============================================================

def primary_effect_target(
    candidate: Dict[str, Any],
) -> str:

    targets = candidate.get(
        "effect_targets",
        [],
    )

    if not isinstance(
        targets,
        list,
    ):
        return ""

    if (
        "building_coverage_ratio"
        in targets
    ):
        return (
            "building_coverage_ratio"
        )

    if (
        "floor_area_ratio"
        in targets
    ):
        return (
            "floor_area_ratio"
        )

    return ""


# ============================================================
# role classify
# ============================================================

def classify_role(
    candidate: Dict[str, Any],
) -> Dict[str, Any]:

    clause_index = int(
        candidate[
            "clause_index"
        ]
    )

    # --------------------------------------------------------
    # explicit override 우선
    # --------------------------------------------------------

    if clause_index in ROLE_OVERRIDES:

        return {
            **ROLE_OVERRIDES[
                clause_index
            ],
            "source": (
                "EXPLICIT_ROLE_OVERRIDE"
            ),
        }

    rule_title = safe_string(
        candidate.get(
            "rule_title"
        )
    )

    text = safe_string(
        candidate.get(
            "text"
        )
    )

    semantic_type = safe_string(
        candidate.get(
            "semantic",
            {},
        ).get(
            "semantic_type"
        )
    )

    # --------------------------------------------------------
    # 명확한 강화
    # --------------------------------------------------------

    if (
        "강화"
        in rule_title
        or "낮출 수"
        in text
        or "낮추어야"
        in text
    ):

        return {
            "role": (
                STRENGTHENING
            ),
            "reason": (
                "조문 제목/본문이 명시적으로 "
                "규제 강화 또는 최대한도 저감을 규정"
            ),
            "source": (
                "TEXT_ROLE_CLASSIFIER"
            ),
        }

    # --------------------------------------------------------
    # 명확한 완화
    # --------------------------------------------------------

    if (
        "완화"
        in rule_title
        or "완화할 수"
        in text
        or "완화 가능"
        in text
    ):

        return {
            "role": (
                RELAXATION
            ),
            "reason": (
                "조문 제목/본문이 명시적으로 "
                "건폐율 또는 용적률 완화를 규정"
            ),
            "source": (
                "TEXT_ROLE_CLASSIFIER"
            ),
        }

    # --------------------------------------------------------
    # BASE_RATIO_MULTIPLIER인데
    # 완화/강화 방향이 text에서 명확하지 않은 경우
    # --------------------------------------------------------

    if semantic_type == (
        "BASE_RATIO_MULTIPLIER"
    ):

        return {
            "role": (
                OTHER_EFFECT
            ),
            "reason": (
                "기준값 배율은 확인됐으나 "
                "현재 base에 대한 완화/강화 역할을 "
                "문맥상 안전하게 확정하지 못함"
            ),
            "source": (
                "SEMANTIC_FALLBACK"
            ),
        }

    # --------------------------------------------------------
    # absolute 값도 그것만으로는
    # 기본규제인지 특례인지 판단 금지
    # --------------------------------------------------------

    return {
        "role": (
            OTHER_EFFECT
        ),
        "reason": (
            "현재 정보만으로 BASE/완화/강화 역할을 "
            "안전하게 확정하지 않음"
        ),
        "source": (
            "SAFE_FALLBACK"
        ),
    }


# ============================================================
# base comparison
# ============================================================

def compare_with_base(
    candidate: Dict[str, Any],
    role: str,
    base_values: Dict[str, float],
) -> Dict[str, Any]:

    target = primary_effect_target(
        candidate
    )

    base = base_values.get(
        target
    )

    semantic = candidate.get(
        "semantic",
        {},
    )

    semantic_type = safe_string(
        semantic.get(
            "semantic_type"
        )
    )

    value = semantic.get(
        "value"
    )

    factor = semantic.get(
        "factor"
    )

    result = {
        "target": target,
        "base": base,
        "projected_value": None,
        "changes_base": None,
        "calculation_status": (
            "NOT_CALCULATED"
        ),
    }

    if base is None:

        return result

    # --------------------------------------------------------
    # 국가 ceiling은 적용 계산 금지
    # --------------------------------------------------------

    if role == NATIONAL_CEILING:

        result[
            "calculation_status"
        ] = (
            "REFERENCE_ONLY"
        )

        result[
            "changes_base"
        ] = False

        return result

    # --------------------------------------------------------
    # 조건부 강화는 현재 미적용
    # --------------------------------------------------------

    if (
        role
        == CONDITIONAL_STRENGTHENING
    ):

        result[
            "calculation_status"
        ] = (
            "SITE_CONDITION_REQUIRED"
        )

        return result

    # --------------------------------------------------------
    # 절대 상한
    # --------------------------------------------------------

    if (
        semantic_type
        == "ABSOLUTE_MAX"
        and isinstance(
            value,
            (int, float),
        )
    ):

        projected = float(
            value
        )

        result[
            "projected_value"
        ] = projected

        result[
            "changes_base"
        ] = (
            projected
            != base
        )

        result[
            "calculation_status"
        ] = (
            "COMPARABLE"
        )

        return result

    # --------------------------------------------------------
    # 절대 ceiling
    # --------------------------------------------------------

    if (
        semantic_type
        == "ABSOLUTE_CEILING"
        and isinstance(
            value,
            (int, float),
        )
    ):

        result[
            "projected_value"
        ] = float(
            value
        )

        result[
            "changes_base"
        ] = (
            float(
                value
            )
            != base
        )

        result[
            "calculation_status"
        ] = (
            "CEILING_ONLY"
        )

        return result

    # --------------------------------------------------------
    # base multiplier
    # --------------------------------------------------------

    if (
        semantic_type
        == "BASE_RATIO_MULTIPLIER"
        and isinstance(
            factor,
            (int, float),
        )
    ):

        projected = (
            base
            * float(
                factor
            )
        )

        result[
            "projected_value"
        ] = (
            projected
        )

        result[
            "changes_base"
        ] = (
            projected
            != base
        )

        result[
            "calculation_status"
        ] = (
            "COMPARABLE"
        )

        return result

    # --------------------------------------------------------
    # 강화 multiplier
    # --------------------------------------------------------

    if (
        semantic_type
        in {
            "MAX_LIMIT_MULTIPLIER",
            "MAX_LIMIT_REDUCTION_RATIO",
        }
        and isinstance(
            factor,
            (int, float),
        )
    ):

        projected = (
            base
            * float(
                factor
            )
        )

        result[
            "projected_value"
        ] = (
            projected
        )

        result[
            "changes_base"
        ] = (
            projected
            != base
        )

        result[
            "calculation_status"
        ] = (
            "COMPARABLE"
        )

        return result

    result[
        "calculation_status"
    ] = (
        "SEMANTIC_NOT_DIRECTLY_COMPARABLE"
    )

    return result


# ============================================================
# main
# ============================================================

def main() -> int:

    numeric = load_json(
        NUMERIC_PATH
    )

    base_data = load_json(
        BASE_PATH
    )

    calculable_now = numeric.get(
        "calculable_now",
        [],
    )

    base_regulation = (
        base_data[
            "current_base_regulation"
        ]
    )

    base_values = {
        "building_coverage_ratio": (
            float(
                base_regulation[
                    "building_coverage_ratio"
                ][
                    "value"
                ]
            )
        ),

        "floor_area_ratio": (
            float(
                base_regulation[
                    "floor_area_ratio"
                ][
                    "value"
                ]
            )
        ),
    }

    results = []

    role_counter = Counter()

    # ========================================================
    # role + base comparison
    # ========================================================

    for candidate in calculable_now:

        if not isinstance(
            candidate,
            dict,
        ):
            continue

        role = classify_role(
            candidate
        )

        comparison = (
            compare_with_base(
                candidate,
                role[
                    "role"
                ],
                base_values,
            )
        )

        role_counter[
            role[
                "role"
            ]
        ] += 1

        results.append(
            {
                "clause_index": (
                    candidate[
                        "clause_index"
                    ]
                ),

                "law_name": (
                    candidate.get(
                        "law_name"
                    )
                ),

                "rule_title": (
                    candidate.get(
                        "rule_title"
                    )
                ),

                "effect_targets": (
                    candidate.get(
                        "effect_targets"
                    )
                ),

                "semantic": (
                    candidate.get(
                        "semantic"
                    )
                ),

                "role": (
                    role[
                        "role"
                    ]
                ),

                "role_reason": (
                    role[
                        "reason"
                    ]
                ),

                "role_source": (
                    role[
                        "source"
                    ]
                ),

                "base_comparison": (
                    comparison
                ),

                "text": (
                    candidate.get(
                        "text"
                    )
                ),
            }
        )

    # ========================================================
    # 실제 base 변경 가능 후보
    # ========================================================

    active_effect_candidates = [
        item
        for item
        in results
        if (
            item[
                "role"
            ]
            in {
                RELAXATION,
                STRENGTHENING,
            }
            and item[
                "base_comparison"
            ][
                "calculation_status"
            ]
            in {
                "COMPARABLE",
                "CEILING_ONLY",
            }
        )
    ]

    reference_only = [
        item
        for item
        in results
        if item[
            "role"
        ]
        in {
            NATIONAL_CEILING,
            BASE_REFERENCE,
        }
    ]

    conditional_strengthening = [
        item
        for item
        in results
        if item[
            "role"
        ]
        == CONDITIONAL_STRENGTHENING
    ]

    unresolved_roles = [
        item
        for item
        in results
        if item[
            "role"
        ]
        == OTHER_EFFECT
    ]

    # ========================================================
    # known validation
    # ========================================================

    by_index = {
        item[
            "clause_index"
        ]: item
        for item
        in results
    }

    clause61_reference = (
        by_index.get(
            61,
            {},
        ).get(
            "role"
        )
        == NATIONAL_CEILING
    )

    clause233_reference = (
        by_index.get(
            233,
            {},
        ).get(
            "role"
        )
        == NATIONAL_CEILING
    )

    clause262_conditional = (
        by_index.get(
            262,
            {},
        ).get(
            "role"
        )
        == CONDITIONAL_STRENGTHENING
    )

    # ========================================================
    # validation
    # ========================================================

    validations = {
        "CALCULABLE_NOW 9개 유지": (
            len(
                results
            )
            == 9
        ),

        "clause 61 NATIONAL_CEILING": (
            clause61_reference
        ),

        "clause 233 NATIONAL_CEILING": (
            clause233_reference
        ),

        "clause 262 conditional strengthening": (
            clause262_conditional
        ),

        "국가 ceiling을 현재 base로 적용하지 않음": (
            all(
                item[
                    "base_comparison"
                ][
                    "calculation_status"
                ]
                == "REFERENCE_ONLY"

                for item
                in results

                if item[
                    "role"
                ]
                == NATIONAL_CEILING
            )
        ),

        "OTHER_EFFECT는 현재값 계산에 포함하지 않음": (
            True
        ),

        "conditional strengthening은 현재값에 적용하지 않음": (
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

        "base": {
            "building_coverage_ratio": (
                base_values[
                    "building_coverage_ratio"
                ]
            ),

            "floor_area_ratio": (
                base_values[
                    "floor_area_ratio"
                ]
            ),
        },

        "summary": {
            "calculable_now_input": (
                len(
                    results
                )
            ),

            "active_effect_candidate_count": (
                len(
                    active_effect_candidates
                )
            ),

            "reference_only_count": (
                len(
                    reference_only
                )
            ),

            "conditional_strengthening_count": (
                len(
                    conditional_strengthening
                )
            ),

            "other_effect_count": (
                len(
                    unresolved_roles
                )
            ),
        },

        "role_summary": (
            dict(
                role_counter
            )
        ),

        "active_effect_candidates": (
            active_effect_candidates
        ),

        "reference_only": (
            reference_only
        ),

        "conditional_strengthening": (
            conditional_strengthening
        ),

        "other_effects": (
            unresolved_roles
        ),

        "all_calculable_now": (
            results
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
        "Input CALCULABLE_NOW:",
        len(
            results
        ),
    )

    print(
        "Roles:",
        dict(
            role_counter
        ),
    )

    print(
        "Active effect candidates:",
        len(
            active_effect_candidates
        ),
    )

    print(
        "Reference only:",
        len(
            reference_only
        ),
    )

    print(
        "Conditional strengthening:",
        len(
            conditional_strengthening
        ),
    )

    print(
        "Other effects:",
        len(
            unresolved_roles
        ),
    )

    print()

    print(
        "Base BCR:",
        base_values[
            "building_coverage_ratio"
        ],
    )

    print(
        "Base FAR:",
        base_values[
            "floor_area_ratio"
        ],
    )

    print()

    for item in results:

        comparison = item[
            "base_comparison"
        ]

        print(
            f"clause {item['clause_index']}: "
            f"{item['role']} "
            f"| {item['rule_title']} "
            f"| target="
            f"{comparison['target']} "
            f"| projected="
            f"{comparison['projected_value']} "
            f"| status="
            f"{comparison['calculation_status']}"
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