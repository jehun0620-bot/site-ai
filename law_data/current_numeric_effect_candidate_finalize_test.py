# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-4
현재 SITE numeric effect candidate finalize

목표
======================================================================
1. 2B-2 CALCULABLE_NOW 9개 역할을 최종 정리
2. clause 3 / 220 / 244 역할을 문맥에 따라 explicit override
3. 현재 확정값에 즉시 반영 가능한 효과와
   계획상한 / 조건부 / 참조값을 분리
4. 아직 여러 특례 사이의 최종 우선순위 계산은 하지 않는다.

현재 BASE
======================================================================
BCR = 50%
FAR = 250%
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-2B-4 "
    "current numeric effect candidate finalize"
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

ROLE_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "current_numeric_effect_role_probe.json"
)

BASE_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "base_numeric_regulation_hierarchy.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "current_numeric_effect_candidate_finalize.json"
)


# ============================================================
# final roles
# ============================================================

DIRECT_RELAXATION = (
    "DIRECT_RELAXATION"
)

CONDITIONAL_RELAXATION = (
    "CONDITIONAL_RELAXATION"
)

DISTRICT_PLAN_CEILING = (
    "DISTRICT_PLAN_CEILING"
)

CONDITIONAL_PLAN_RANGE = (
    "CONDITIONAL_PLAN_RANGE"
)

NATIONAL_CEILING = (
    "NATIONAL_CEILING"
)

SPECIAL_AREA_REFERENCE = (
    "SPECIAL_AREA_REFERENCE"
)

CONDITIONAL_STRENGTHENING = (
    "CONDITIONAL_STRENGTHENING"
)

OTHER_REFERENCE = (
    "OTHER_REFERENCE"
)


# ============================================================
# explicit final role overrides
# ============================================================

FINAL_ROLE_OVERRIDES = {

    # --------------------------------------------------------
    # BCR
    # --------------------------------------------------------

    3: {
        "final_role": (
            CONDITIONAL_PLAN_RANGE
        ),

        "apply_now": False,

        "reason": (
            "지구단위계획구역이라는 사실만으로 적용되지 않고 "
            "영 제84조제6항제1호에 따른 특정 건축물이라는 "
            "추가 전제가 필요함. 80~90%는 지구단위계획에서 "
            "별도로 정할 수 있는 범위"
        ),

        "result_type": (
            "POTENTIAL_RANGE"
        ),

        "candidate_min": 80.0,
        "candidate_max": 90.0,
    },

    4: {
        "final_role": (
            DIRECT_RELAXATION
        ),

        "apply_now": True,

        "reason": (
            "현재 applicability와 semantic 결과상 "
            "해당 용도지역별 건폐율의 120% 이하 완화"
        ),
    },

    50: {
        "final_role": (
            DIRECT_RELAXATION
        ),

        "apply_now": True,

        "reason": (
            "현재 applicability와 semantic 결과상 "
            "지구단위계획 관련 건폐율 완화 규칙"
        ),
    },

    61: {
        "final_role": (
            NATIONAL_CEILING
        ),

        "apply_now": False,

        "reason": (
            "주거지역 전체의 상위법 ceiling으로 "
            "서울 제3종일반주거지역 base 50%를 대체하지 않음"
        ),
    },

    # --------------------------------------------------------
    # FAR
    # --------------------------------------------------------

    189: {
        "final_role": (
            DIRECT_RELAXATION
        ),

        "apply_now": True,

        "reason": (
            "현재 applicability와 semantic 결과상 "
            "용도지역별 용적률의 120% 이하 완화"
        ),
    },

    220: {
        "final_role": (
            DISTRICT_PLAN_CEILING
        ),

        "apply_now": False,

        "reason": (
            "지구단위계획구역에서 규칙으로 정할 수 있는 "
            "용적률 상한으로, 110%가 자동 적용되는 "
            "확정 용적률은 아님"
        ),

        "result_type": (
            "PLAN_CEILING"
        ),
    },

    233: {
        "final_role": (
            NATIONAL_CEILING
        ),

        "apply_now": False,

        "reason": (
            "주거지역 전체에 대한 상위법 ceiling 500%로 "
            "서울 제3종일반주거지역 base 250%를 대체하지 않음"
        ),
    },

    244: {
        "final_role": (
            SPECIAL_AREA_REFERENCE
        ),

        "apply_now": False,

        "reason": (
            "법 제77조제3항제2호부터 제5호에 해당하는 "
            "별도 지역에 대한 특칙. 현재 SITE가 해당 "
            "특수지역이라는 evidence가 없으므로 적용하지 않음"
        ),

        "result_type": (
            "SPECIAL_AREA_LIMIT"
        ),
    },

    262: {
        "final_role": (
            CONDITIONAL_STRENGTHENING
        ),

        "apply_now": False,

        "reason": (
            "개발밀도관리구역 TRUE일 때만 적용. "
            "현재 개발밀도관리구역은 UNKNOWN"
        ),
    },
}


# ============================================================
# util
# ============================================================

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

    OUTPUT_PATH.parent.mkdir(
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
# main
# ============================================================

def main() -> int:

    role_data = load_json(
        ROLE_PATH
    )

    base_data = load_json(
        BASE_PATH
    )

    input_items = role_data.get(
        "all_calculable_now",
        [],
    )

    base = {
        "building_coverage_ratio": float(
            base_data[
                "current_base_regulation"
            ][
                "building_coverage_ratio"
            ][
                "value"
            ]
        ),

        "floor_area_ratio": float(
            base_data[
                "current_base_regulation"
            ][
                "floor_area_ratio"
            ][
                "value"
            ]
        ),
    }

    results = []

    role_counter = Counter()

    # ========================================================
    # final role
    # ========================================================

    for original in input_items:

        if not isinstance(
            original,
            dict,
        ):
            continue

        item = copy.deepcopy(
            original
        )

        index = int(
            item[
                "clause_index"
            ]
        )

        override = (
            FINAL_ROLE_OVERRIDES.get(
                index
            )
        )

        if not override:

            item[
                "final_role"
            ] = OTHER_REFERENCE

            item[
                "apply_now"
            ] = False

            item[
                "final_reason"
            ] = (
                "명시적 최종 역할 미확정"
            )

        else:

            item[
                "final_role"
            ] = (
                override[
                    "final_role"
                ]
            )

            item[
                "apply_now"
            ] = (
                override[
                    "apply_now"
                ]
            )

            item[
                "final_reason"
            ] = (
                override[
                    "reason"
                ]
            )

            for key in (
                "result_type",
                "candidate_min",
                "candidate_max",
            ):

                if key in override:

                    item[
                        key
                    ] = (
                        override[
                            key
                        ]
                    )

        role_counter[
            item[
                "final_role"
            ]
        ] += 1

        results.append(
            item
        )

    # ========================================================
    # immediate effects
    # ========================================================

    immediate = [
        item
        for item
        in results
        if item[
            "apply_now"
        ]
    ]

    deferred = [
        item
        for item
        in results
        if not item[
            "apply_now"
        ]
    ]

    # ========================================================
    # BCR/FAR immediate candidate values
    # ========================================================

    bcr_candidates = []

    far_candidates = []

    for item in immediate:

        comparison = item.get(
            "base_comparison",
            {}
        )

        target = comparison.get(
            "target"
        )

        value = comparison.get(
            "projected_value"
        )

        if not isinstance(
            value,
            (int, float),
        ):
            continue

        entry = {
            "clause_index": (
                item[
                    "clause_index"
                ]
            ),

            "value": float(
                value
            ),

            "role": (
                item[
                    "final_role"
                ]
            ),

            "rule_title": (
                item.get(
                    "rule_title"
                )
            ),
        }

        if (
            target
            == "building_coverage_ratio"
        ):

            bcr_candidates.append(
                entry
            )

        elif (
            target
            == "floor_area_ratio"
        ):

            far_candidates.append(
                entry
            )

    # ========================================================
    # known checks
    # ========================================================

    by_index = {
        item[
            "clause_index"
        ]: item
        for item
        in results
    }

    validations = {

        "input 9개 유지": (
            len(
                results
            )
            == 9
        ),

        "clause 3 현재 미적용": (
            by_index[
                3
            ][
                "apply_now"
            ]
            is False
        ),

        "clause 220 plan ceiling": (
            by_index[
                220
            ][
                "final_role"
            ]
            ==
            DISTRICT_PLAN_CEILING
        ),

        "clause 220 현재 미적용": (
            by_index[
                220
            ][
                "apply_now"
            ]
            is False
        ),

        "clause 244 special area reference": (
            by_index[
                244
            ][
                "final_role"
            ]
            ==
            SPECIAL_AREA_REFERENCE
        ),

        "clause 244 현재 미적용": (
            by_index[
                244
            ][
                "apply_now"
            ]
            is False
        ),

        "clause 262 현재 미적용": (
            by_index[
                262
            ][
                "apply_now"
            ]
            is False
        ),

        "즉시 BCR 후보 존재": (
            len(
                bcr_candidates
            )
            > 0
        ),

        "즉시 FAR 후보 존재": (
            len(
                far_candidates
            )
            > 0
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

        "base": (
            base
        ),

        "summary": {
            "input": (
                len(
                    results
                )
            ),

            "apply_now": (
                len(
                    immediate
                )
            ),

            "deferred": (
                len(
                    deferred
                )
            ),

            "bcr_immediate_candidates": (
                len(
                    bcr_candidates
                )
            ),

            "far_immediate_candidates": (
                len(
                    far_candidates
                )
            ),
        },

        "role_summary": (
            dict(
                role_counter
            )
        ),

        "bcr_immediate_candidates": (
            bcr_candidates
        ),

        "far_immediate_candidates": (
            far_candidates
        ),

        "immediate_effects": (
            immediate
        ),

        "deferred_effects": (
            deferred
        ),

        "all_effects": (
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
        "Base BCR:",
        base[
            "building_coverage_ratio"
        ],
    )

    print(
        "Base FAR:",
        base[
            "floor_area_ratio"
        ],
    )

    print()

    print(
        "Input:",
        len(
            results
        ),
    )

    print(
        "Apply now:",
        len(
            immediate
        ),
    )

    print(
        "Deferred:",
        len(
            deferred
        ),
    )

    print(
        "Roles:",
        dict(
            role_counter
        ),
    )

    print()

    print(
        "Immediate BCR candidates:",
        bcr_candidates,
    )

    print(
        "Immediate FAR candidates:",
        far_candidates,
    )

    print()

    for index in (
        3,
        220,
        244,
        262,
    ):

        item = by_index[
            index
        ]

        print(
            f"clause {index}: "
            f"{item['final_role']} "
            f"/ apply_now="
            f"{item['apply_now']}"
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