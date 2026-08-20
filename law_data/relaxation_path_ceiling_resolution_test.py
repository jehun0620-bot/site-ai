# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-6
Relaxation path / ceiling resolution

핵심
======================================================================
clause 4
    실제 BCR relaxation path
    base BCR × 1.20

clause 189
    실제 FAR relaxation path
    base FAR × 1.20

clause 50
    직접 완화값을 만드는 규정이 아니라
    완화된 결과가 넘을 수 없는 ceiling

    BCR ceiling:
        base BCR × 1.50

    FAR ceiling:
        base FAR × 2.00

따라서:
    effective_relaxed_value
        = min(
            relaxation_path_value,
            applicable_ceiling
        )

주의
======================================================================
- clause 50을 direct relaxation으로 계산하지 않는다.
- 60 × 1.5 같은 연쇄 multiplier 계산 금지
- 300 × 2.0 같은 연쇄 multiplier 계산 금지
- 모든 multiplier는 원래 용도지역 base 기준
- 아직 최종 법적 허용값으로 확정하지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-2B-6 "
    "relaxation path / ceiling resolution"
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

BASE_PATH = (
    OUTPUT_DIR
    / "base_numeric_regulation_hierarchy.json"
)

INTERACTION_PATH = (
    OUTPUT_DIR
    / "immediate_numeric_effect_interaction_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "relaxation_path_ceiling_resolution.json"
)


# ============================================================
# clause role
# ============================================================

ROLE_REGISTRY = {

    4: {
        "role": (
            "RELAXATION_PATH"
        ),

        "target": (
            "building_coverage_ratio"
        ),

        "factor": 1.20,

        "reason": (
            "해당 용도지역별 건폐율의 "
            "120퍼센트 이하 완화 규정"
        ),
    },

    189: {
        "role": (
            "RELAXATION_PATH"
        ),

        "target": (
            "floor_area_ratio"
        ),

        "factor": 1.20,

        "reason": (
            "해당 용도지역별 용적률의 "
            "120퍼센트 이하 완화 규정"
        ),
    },

    50: {
        "role": (
            "RELAXATION_CEILING"
        ),

        "targets": {
            "building_coverage_ratio": {
                "factor": 1.50,
            },

            "floor_area_ratio": {
                "factor": 2.00,
            },
        },

        "reason": (
            "완화하여 적용되는 건폐율 및 용적률은 "
            "각각 해당 용도지역 기준의 "
            "150퍼센트 및 200퍼센트를 "
            "초과할 수 없다는 상한 규정"
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


def build_target_index(
    interaction: Dict[str, Any],
) -> Dict[int, Dict[str, Any]]:

    result = {}

    for item in interaction.get(
        "targets",
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

    base_data = load_json(
        BASE_PATH
    )

    interaction = load_json(
        INTERACTION_PATH
    )

    target_index = (
        build_target_index(
            interaction
        )
    )

    # ========================================================
    # BASE
    # ========================================================

    base_bcr = float(
        base_data[
            "current_base_regulation"
        ][
            "building_coverage_ratio"
        ][
            "value"
        ]
    )

    base_far = float(
        base_data[
            "current_base_regulation"
        ][
            "floor_area_ratio"
        ][
            "value"
        ]
    )

    base_values = {
        "building_coverage_ratio": (
            base_bcr
        ),

        "floor_area_ratio": (
            base_far
        ),
    }

    # ========================================================
    # clause availability
    # ========================================================

    required_indexes = {
        4,
        50,
        189,
    }

    all_targets_present = (
        required_indexes
        .issubset(
            set(
                target_index.keys()
            )
        )
    )

    # ========================================================
    # RELAXATION PATH
    # ========================================================

    paths = {}

    for index in (
        4,
        189,
    ):

        role = ROLE_REGISTRY[
            index
        ]

        target = role[
            "target"
        ]

        base = base_values[
            target
        ]

        factor = float(
            role[
                "factor"
            ]
        )

        raw_value = (
            base
            * factor
        )

        paths[
            target
        ] = {
            "clause_index": (
                index
            ),

            "role": (
                role[
                    "role"
                ]
            ),

            "base": (
                base
            ),

            "factor": (
                factor
            ),

            "raw_relaxed_value": (
                raw_value
            ),

            "reason": (
                role[
                    "reason"
                ]
            ),
        }

    # ========================================================
    # CEILING
    # ========================================================

    ceilings = {}

    ceiling_role = (
        ROLE_REGISTRY[
            50
        ]
    )

    for target, definition in (
        ceiling_role[
            "targets"
        ].items()
    ):

        base = base_values[
            target
        ]

        factor = float(
            definition[
                "factor"
            ]
        )

        ceiling_value = (
            base
            * factor
        )

        ceilings[
            target
        ] = {
            "clause_index": 50,

            "role": (
                "RELAXATION_CEILING"
            ),

            "base": (
                base
            ),

            "factor": (
                factor
            ),

            "ceiling_value": (
                ceiling_value
            ),

            "reason": (
                ceiling_role[
                    "reason"
                ]
            ),
        }

    # ========================================================
    # apply ceiling
    # ========================================================

    resolved = {}

    for target in (
        "building_coverage_ratio",
        "floor_area_ratio",
    ):

        path = paths[
            target
        ]

        ceiling = ceilings[
            target
        ]

        raw_value = float(
            path[
                "raw_relaxed_value"
            ]
        )

        ceiling_value = float(
            ceiling[
                "ceiling_value"
            ]
        )

        effective_value = min(
            raw_value,
            ceiling_value,
        )

        ceiling_binding = (
            raw_value
            >
            ceiling_value
        )

        resolved[
            target
        ] = {
            "base": (
                base_values[
                    target
                ]
            ),

            "path_clause": (
                path[
                    "clause_index"
                ]
            ),

            "path_factor": (
                path[
                    "factor"
                ]
            ),

            "raw_relaxed_value": (
                raw_value
            ),

            "ceiling_clause": 50,

            "ceiling_factor": (
                ceiling[
                    "factor"
                ]
            ),

            "ceiling_value": (
                ceiling_value
            ),

            "ceiling_binding": (
                ceiling_binding
            ),

            "resolved_candidate_value": (
                effective_value
            ),

            "calculation": (
                "min("
                f"{raw_value}, "
                f"{ceiling_value}"
                ")"
            ),

            "status": (
                "NUMERIC_PATH_RESOLVED"
            ),
        }

    # ========================================================
    # anti-stacking checks
    # ========================================================

    wrong_bcr_stacked = (
        base_bcr
        * 1.20
        * 1.50
    )

    wrong_far_stacked = (
        base_far
        * 1.20
        * 2.00
    )

    anti_stacking = {

        "bcr_wrong_stacked_value": (
            wrong_bcr_stacked
        ),

        "far_wrong_stacked_value": (
            wrong_far_stacked
        ),

        "bcr_wrong_stacked_used": (
            resolved[
                "building_coverage_ratio"
            ][
                "resolved_candidate_value"
            ]
            ==
            wrong_bcr_stacked
        ),

        "far_wrong_stacked_used": (
            resolved[
                "floor_area_ratio"
            ][
                "resolved_candidate_value"
            ]
            ==
            wrong_far_stacked
        ),
    }

    # ========================================================
    # known expected values
    # ========================================================

    bcr = resolved[
        "building_coverage_ratio"
    ]

    far = resolved[
        "floor_area_ratio"
    ]

    validations = {

        "clause 4/50/189 존재": (
            all_targets_present
        ),

        "BCR base 50": (
            base_bcr
            == 50.0
        ),

        "FAR base 250": (
            base_far
            == 250.0
        ),

        "clause 4 BCR relaxation 60": (
            bcr[
                "raw_relaxed_value"
            ]
            == 60.0
        ),

        "clause 50 BCR ceiling 75": (
            bcr[
                "ceiling_value"
            ]
            == 75.0
        ),

        "BCR ceiling 비구속": (
            bcr[
                "ceiling_binding"
            ]
            is False
        ),

        "BCR resolved candidate 60": (
            bcr[
                "resolved_candidate_value"
            ]
            == 60.0
        ),

        "clause 189 FAR relaxation 300": (
            far[
                "raw_relaxed_value"
            ]
            == 300.0
        ),

        "clause 50 FAR ceiling 500": (
            far[
                "ceiling_value"
            ]
            == 500.0
        ),

        "FAR ceiling 비구속": (
            far[
                "ceiling_binding"
            ]
            is False
        ),

        "FAR resolved candidate 300": (
            far[
                "resolved_candidate_value"
            ]
            == 300.0
        ),

        "BCR multiplier 연쇄적용 금지": (
            anti_stacking[
                "bcr_wrong_stacked_used"
            ]
            is False
        ),

        "FAR multiplier 연쇄적용 금지": (
            anti_stacking[
                "far_wrong_stacked_used"
            ]
            is False
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "base": (
            base_values
        ),

        "role_registry": (
            ROLE_REGISTRY
        ),

        "relaxation_paths": (
            paths
        ),

        "ceilings": (
            ceilings
        ),

        "resolved_candidates": (
            resolved
        ),

        "anti_stacking": (
            anti_stacking
        ),

        "interpretation": {

            "building_coverage_ratio": (
                "clause 4가 base 건폐율의 120% 이하 "
                "완화 경로를 제공하고 clause 50은 "
                "완화 결과의 150% ceiling을 제공한다. "
                "현재 60%는 ceiling 75% 이하이므로 "
                "ceiling은 구속하지 않는다."
            ),

            "floor_area_ratio": (
                "clause 189가 base 용적률의 120% 이하 "
                "완화 경로를 제공하고 clause 50은 "
                "완화 결과의 200% ceiling을 제공한다. "
                "현재 300%는 ceiling 500% 이하이므로 "
                "ceiling은 구속하지 않는다."
            ),

            "warning": (
                "resolved_candidate_value는 현재까지 확인된 "
                "numeric 법령경로상의 후보값이며 최종 허용값 "
                "확정은 추가 적용요건/계획결정 검증 후 수행한다."
            ),
        },

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
        base_bcr,
    )

    print(
        "BCR relaxation path:",
        bcr[
            "raw_relaxed_value"
        ],
    )

    print(
        "BCR ceiling:",
        bcr[
            "ceiling_value"
        ],
    )

    print(
        "BCR ceiling binding:",
        bcr[
            "ceiling_binding"
        ],
    )

    print(
        "BCR resolved candidate:",
        bcr[
            "resolved_candidate_value"
        ],
    )

    print()

    print(
        "Base FAR:",
        base_far,
    )

    print(
        "FAR relaxation path:",
        far[
            "raw_relaxed_value"
        ],
    )

    print(
        "FAR ceiling:",
        far[
            "ceiling_value"
        ],
    )

    print(
        "FAR ceiling binding:",
        far[
            "ceiling_binding"
        ],
    )

    print(
        "FAR resolved candidate:",
        far[
            "resolved_candidate_value"
        ],
    )

    print()

    print(
        "Wrong stacked BCR:",
        wrong_bcr_stacked,
    )

    print(
        "Wrong stacked FAR:",
        wrong_far_stacked,
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