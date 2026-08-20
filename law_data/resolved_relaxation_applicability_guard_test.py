# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-7
Resolved relaxation applicability guard

목표
======================================================================
현재 numeric 경로에서 계산된:

    BCR candidate = 60%
    FAR candidate = 300%

을 곧바로 최종 허용값으로 확정하지 않는다.

검증 대상
======================================================================
clause 4
    서울특별시 도시계획 조례
    건폐율의 완화
    해당 용도지역별 건폐율의 120%

clause 189
    서울특별시 도시계획 조례
    용적률의 완화
    해당 용도지역별 용적률의 120%

문제
======================================================================
두 조문 모두 상위 시행령의 특정 완화 사유를 전제로 한다.

따라서:
- parser conditions가 비어 있다고 해서
  자동 APPLICABLE로 확정하면 안 된다.
- 상위법 reference가 존재하는 경우
  그 reference의 branch 조건이 모델링됐는지 확인해야 한다.

최종 상태
======================================================================
CONFIRMED
    적용요건까지 모두 검증됨

CONDITIONAL
    PROJECT / PROCEDURE 입력 필요

UNKNOWN
    SITE 또는 상위법 branch 적용사유 미확정

BASE_ONLY
    특례 확정 불가 -> 현재 기본값 유지
"""

from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-2B-7 "
    "resolved relaxation applicability guard"
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

RESOLUTION_PATH = (
    OUTPUT_DIR
    / "relaxation_path_ceiling_resolution.json"
)

APPLICABILITY_PATH = (
    OUTPUT_DIR
    / "branch_local_predicate_applicability_fix.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "resolved_relaxation_applicability_guard.json"
)


# ============================================================
# 대상 clause
# ============================================================

TARGETS = {

    4: {
        "effect": (
            "building_coverage_ratio"
        ),

        "candidate_value": 60.0,

        "base_value": 50.0,

        "reference_pattern": (
            r"영\s*제84조제6항제2호"
        ),
    },

    189: {
        "effect": (
            "floor_area_ratio"
        ),

        "candidate_value": 300.0,

        "base_value": 250.0,

        "reference_pattern": (
            r"영\s*제85조제5항"
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

    return str(
        value
    ).strip()


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
    limit: int = 500,
) -> str:

    text = normalize_text(
        value
    )

    if len(
        text
    ) > limit:

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
            int(
                index
            )
        ] = item

    return result


# ============================================================
# reference / condition guard
# ============================================================

def analyze_target(
    clause_index: int,
    clause: Dict[str, Any],
    applicability: Dict[str, Any],
    definition: Dict[str, Any],
) -> Dict[str, Any]:

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

    context = normalize_text(
        inherited
        + " "
        + text
    )

    reference_pattern = (
        definition[
            "reference_pattern"
        ]
    )

    has_upper_reference = bool(
        re.search(
            reference_pattern,
            context,
        )
    )

    condition_results = (
        applicability.get(
            "condition_results",
            []
        )
    )

    modeled_conditions = [
        {
            "name": (
                item.get(
                    "name"
                )
            ),

            "type": (
                item.get(
                    "effective_type"
                )
                or item.get(
                    "declared_type"
                )
            ),

            "state": (
                item.get(
                    "state"
                )
            ),
        }

        for item
        in condition_results

        if isinstance(
            item,
            dict,
        )
    ]

    false_conditions = [
        item
        for item
        in modeled_conditions
        if item[
            "state"
        ]
        == "FALSE"
    ]

    unknown_conditions = [
        item
        for item
        in modeled_conditions
        if item[
            "state"
        ]
        == "UNKNOWN"
    ]

    unset_conditions = [
        item
        for item
        in modeled_conditions
        if item[
            "state"
        ]
        == "UNSET"
    ]

    # --------------------------------------------------------
    # 핵심 safeguard
    #
    # 상위법 특정 호를 참조하는데
    # 현재 branch condition이 하나도 모델링되지 않은 경우
    # APPLICABLE로 확정하지 않는다.
    # --------------------------------------------------------

    reference_branch_unmodeled = (
        has_upper_reference
        and len(
            modeled_conditions
        )
        == 0
    )

    # --------------------------------------------------------
    # resolution
    # --------------------------------------------------------

    if false_conditions:

        resolution = (
            "NOT_APPLICABLE"
        )

        reason = (
            "모델링된 적용조건 중 FALSE 존재"
        )

    elif unknown_conditions:

        resolution = (
            "UNKNOWN"
        )

        reason = (
            "모델링된 적용조건 중 UNKNOWN 존재"
        )

    elif unset_conditions:

        resolution = (
            "CONDITIONAL"
        )

        reason = (
            "추가 PROJECT/PROCEDURE 입력 필요"
        )

    elif reference_branch_unmodeled:

        resolution = (
            "UNKNOWN"
        )

        reason = (
            "상위 시행령의 특정 완화 호를 참조하지만 "
            "해당 branch 적용사유가 condition model에 "
            "아직 명시적으로 연결되지 않음"
        )

    else:

        resolution = (
            "CONFIRMED"
        )

        reason = (
            "현재 모델 기준 적용요건 충족"
        )

    return {
        "clause_index": (
            clause_index
        ),

        "effect": (
            definition[
                "effect"
            ]
        ),

        "base_value": (
            definition[
                "base_value"
            ]
        ),

        "candidate_value": (
            definition[
                "candidate_value"
            ]
        ),

        "current_applicability": (
            applicability.get(
                "applicability"
            )
        ),

        "has_upper_reference": (
            has_upper_reference
        ),

        "upper_reference_pattern": (
            reference_pattern
        ),

        "modeled_conditions": (
            modeled_conditions
        ),

        "reference_branch_unmodeled": (
            reference_branch_unmodeled
        ),

        "resolution": (
            resolution
        ),

        "reason": (
            reason
        ),

        "text": (
            text
        ),

        "inherited_context": (
            inherited
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    clause_data = load_json(
        CLAUSE_PATH
    )

    resolution_data = load_json(
        RESOLUTION_PATH
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

    # ========================================================
    # numeric path 값 검증
    # ========================================================

    resolved_numeric = (
        resolution_data.get(
            "resolved_candidates",
            {}
        )
    )

    numeric_bcr = (
        resolved_numeric.get(
            "building_coverage_ratio",
            {},
        ).get(
            "resolved_candidate_value"
        )
    )

    numeric_far = (
        resolved_numeric.get(
            "floor_area_ratio",
            {},
        ).get(
            "resolved_candidate_value"
        )
    )

    # ========================================================
    # target 분석
    # ========================================================

    results = []

    for clause_index, definition in (
        TARGETS.items()
    ):

        if (
            clause_index < 1
            or clause_index > len(
                clauses
            )
        ):

            continue

        clause = (
            clauses[
                clause_index - 1
            ]
        )

        applicability = (
            applicability_index.get(
                clause_index,
                {}
            )
        )

        results.append(
            analyze_target(
                clause_index,
                clause,
                applicability,
                definition,
            )
        )

    by_index = {
        item[
            "clause_index"
        ]: item
        for item
        in results
    }

    # ========================================================
    # 현재 확정 출력 정책
    # ========================================================

    bcr_guard = (
        by_index.get(
            4,
            {}
        )
    )

    far_guard = (
        by_index.get(
            189,
            {}
        )
    )

    # --------------------------------------------------------
    # 특례가 CONFIRMED일 때만 candidate를 확정값으로 승격
    # --------------------------------------------------------

    if (
        bcr_guard.get(
            "resolution"
        )
        == "CONFIRMED"
    ):

        current_bcr = (
            TARGETS[
                4
            ][
                "candidate_value"
            ]
        )

        bcr_source = (
            "RELAXATION_CONFIRMED"
        )

    else:

        current_bcr = (
            TARGETS[
                4
            ][
                "base_value"
            ]
        )

        bcr_source = (
            "BASE_REGULATION"
        )

    if (
        far_guard.get(
            "resolution"
        )
        == "CONFIRMED"
    ):

        current_far = (
            TARGETS[
                189
            ][
                "candidate_value"
            ]
        )

        far_source = (
            "RELAXATION_CONFIRMED"
        )

    else:

        current_far = (
            TARGETS[
                189
            ][
                "base_value"
            ]
        )

        far_source = (
            "BASE_REGULATION"
        )

    current_result = {
        "building_coverage_ratio": {
            "confirmed_value": (
                current_bcr
            ),

            "source": (
                bcr_source
            ),

            "base_value": 50.0,

            "relaxation_candidate": (
                numeric_bcr
            ),

            "relaxation_resolution": (
                bcr_guard.get(
                    "resolution"
                )
            ),
        },

        "floor_area_ratio": {
            "confirmed_value": (
                current_far
            ),

            "source": (
                far_source
            ),

            "base_value": 250.0,

            "relaxation_candidate": (
                numeric_far
            ),

            "relaxation_resolution": (
                far_guard.get(
                    "resolution"
                )
            ),
        },
    }

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "numeric BCR candidate 60 확인": (
            numeric_bcr
            == 60.0
        ),

        "numeric FAR candidate 300 확인": (
            numeric_far
            == 300.0
        ),

        "clause 4 분석 완료": (
            4 in by_index
        ),

        "clause 189 분석 완료": (
            189 in by_index
        ),

        "상위법 branch 미모델링 시 CONFIRMED 금지": (
            all(
                not (
                    item[
                        "reference_branch_unmodeled"
                    ]
                    and item[
                        "resolution"
                    ]
                    == "CONFIRMED"
                )

                for item
                in results
            )
        ),

        "미확정 특례를 confirmed value로 사용하지 않음": (
            (
                bcr_guard.get(
                    "resolution"
                )
                == "CONFIRMED"
                or current_bcr
                == 50.0
            )
            and
            (
                far_guard.get(
                    "resolution"
                )
                == "CONFIRMED"
                or current_far
                == 250.0
            )
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

        "numeric_candidates": {
            "building_coverage_ratio": (
                numeric_bcr
            ),

            "floor_area_ratio": (
                numeric_far
            ),
        },

        "guards": (
            results
        ),

        "current_confirmed_result": (
            current_result
        ),

        "policy": {
            "rule": (
                "법령상 numeric 완화경로가 계산되더라도 "
                "상위 branch 적용사유가 명시적으로 검증되기 전에는 "
                "해당 candidate를 confirmed regulation 값으로 승격하지 않는다."
            ),

            "unverified_relaxation_fallback": (
                "BASE_REGULATION"
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
        "Numeric BCR candidate:",
        numeric_bcr,
    )

    print(
        "Numeric FAR candidate:",
        numeric_far,
    )

    print()

    for item in results:

        print(
            f"clause {item['clause_index']}: "
            f"{item['resolution']}"
        )

        print(
            "  reference:",
            item[
                "has_upper_reference"
            ],
        )

        print(
            "  modeled conditions:",
            item[
                "modeled_conditions"
            ],
        )

        print(
            "  branch unmodeled:",
            item[
                "reference_branch_unmodeled"
            ],
        )

        print(
            "  reason:",
            item[
                "reason"
            ],
        )

    print()

    print(
        "Confirmed BCR:",
        current_result[
            "building_coverage_ratio"
        ][
            "confirmed_value"
        ],
        "/ candidate:",
        current_result[
            "building_coverage_ratio"
        ][
            "relaxation_candidate"
        ],
    )

    print(
        "Confirmed FAR:",
        current_result[
            "floor_area_ratio"
        ][
            "confirmed_value"
        ],
        "/ candidate:",
        current_result[
            "floor_area_ratio"
        ][
            "relaxation_candidate"
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