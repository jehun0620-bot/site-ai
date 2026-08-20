# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-1
Base Regulation / Special Effect hierarchy validation

목표
======================================================================
1. 현재 SITE의 실제 기본 건폐율 / 용적률 값을 별도 Base Regulation으로 정의
2. 국가법상 광역 상한과 서울시 조례 실제 적용값을 구분
3. numeric candidate 중 BASE RULE과 SPECIAL EFFECT를 분리
4. clause 61 / 233을 실제 SITE 기본값으로 오인하지 않음
5. 개발밀도관리구역 관련 clause 262를 현재 확정값에 바로 적용하지 않음
6. 아직 최종 완화 계산은 하지 않는다.

현재 SITE
======================================================================
zone = 제3종일반주거지역

서울시 조례 기준
======================================================================
건폐율 = 50%
용적률 = 250%

국가법상 광역 최대범위
======================================================================
주거지역 건폐율 법률 상한 = 70%
주거지역 용적률 법률 상한 = 500%

이 두 계층은 서로 다르다.
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-2B-1 "
    "Base Regulation / Special Effect hierarchy"
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

SITE_PATH = (
    OUTPUT_DIR
    / "site_spatial_condition_final_snapshot.json"
)

NUMERIC_PATH = (
    OUTPUT_DIR
    / "numeric_semantic_override_finalize.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "base_numeric_regulation_hierarchy.json"
)


# ============================================================
# 현재 SITE 기본 규제
#
# 현행 서울특별시 도시계획 조례 기준
# ============================================================

BASE_REGULATION = {

    "zone": (
        "제3종일반주거지역"
    ),

    "building_coverage_ratio": {
        "value": 50.0,
        "unit": "percent",

        "regulation_level": (
            "LOCAL_ORDINANCE"
        ),

        "source": (
            "서울특별시 도시계획 조례"
        ),

        "article": (
            "제44조"
        ),

        "rule": (
            "제3종일반주거지역 건폐율 50퍼센트 이하"
        ),

        "confidence": (
            "HIGH"
        ),
    },

    "floor_area_ratio": {
        "value": 250.0,
        "unit": "percent",

        "regulation_level": (
            "LOCAL_ORDINANCE"
        ),

        "source": (
            "서울특별시 도시계획 조례"
        ),

        "article": (
            "제48조"
        ),

        "rule": (
            "제3종일반주거지역 용적률 250퍼센트 이하"
        ),

        "confidence": (
            "HIGH"
        ),
    },
}


# ============================================================
# 상위법 광역 ceiling
#
# 실제 SITE 기본값이 아니다.
# ============================================================

NATIONAL_CEILINGS = {

    "building_coverage_ratio": {
        "value": 70.0,

        "meaning": (
            "도시지역 주거지역 건폐율에 대한 "
            "상위법상 광역 최대한도"
        ),

        "use_as_site_base": False,
    },

    "floor_area_ratio": {
        "value": 500.0,

        "meaning": (
            "도시지역 주거지역 용적률에 대한 "
            "상위법상 광역 최대한도"
        ),

        "use_as_site_base": False,
    },
}


# ============================================================
# known clause role overrides
# ============================================================

CLAUSE_ROLE_OVERRIDES = {

    # --------------------------------------------------------
    # 국가법 광역 ceiling
    # --------------------------------------------------------

    61: {
        "role": (
            "NATIONAL_CEILING"
        ),

        "effect_target": (
            "building_coverage_ratio"
        ),

        "reason": (
            "주거지역 전체에 대한 법률상 건폐율 "
            "최대범위이며 서울 제3종일반주거지역 "
            "실제 조례 기본값 50%와 다름"
        ),
    },

    233: {
        "role": (
            "NATIONAL_CEILING"
        ),

        "effect_target": (
            "floor_area_ratio"
        ),

        "reason": (
            "주거지역 전체에 대한 법률상 용적률 "
            "최대범위이며 서울 제3종일반주거지역 "
            "실제 조례 기본값 250%와 다름"
        ),
    },

    # --------------------------------------------------------
    # 개발밀도관리구역 강화
    # --------------------------------------------------------

    262: {
        "role": (
            "CONDITIONAL_STRENGTHENING"
        ),

        "effect_target": (
            "floor_area_ratio"
        ),

        "required_site_condition": (
            "개발밀도관리구역"
        ),

        "reason": (
            "개발밀도관리구역 지정 시 적용되는 "
            "용적률 강화범위이므로 해당 SITE condition "
            "확정 전에는 현재 FAR에 적용 불가"
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
# SITE condition index
# ============================================================

def build_site_condition_index(
    snapshot: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:

    result = {}

    for group in (
        "conditions",
        "supplemental_conditions",
    ):

        for item in snapshot.get(
            group,
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

            if not name:
                continue

            result[
                name
            ] = {
                "status": safe_string(
                    item.get(
                        "status"
                    )
                ),

                "confidence": safe_string(
                    item.get(
                        "confidence"
                    )
                ),
            }

    return result


# ============================================================
# candidate index
# ============================================================

def build_candidate_index(
    numeric: Dict[str, Any],
) -> Dict[int, Dict[str, Any]]:

    result = {}

    for item in numeric.get(
        "candidates",
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
# main
# ============================================================

def main() -> int:

    site_snapshot = load_json(
        SITE_PATH
    )

    numeric_data = load_json(
        NUMERIC_PATH
    )

    site_index = (
        build_site_condition_index(
            site_snapshot
        )
    )

    candidate_index = (
        build_candidate_index(
            numeric_data
        )
    )

    # ========================================================
    # role classification
    # ========================================================

    role_results = {}

    for clause_index, definition in (
        CLAUSE_ROLE_OVERRIDES.items()
    ):

        candidate = (
            candidate_index.get(
                clause_index,
                {}
            )
        )

        role_results[
            str(
                clause_index
            )
        ] = {
            "candidate_exists": (
                bool(
                    candidate
                )
            ),

            "applicability": (
                candidate.get(
                    "applicability"
                )
            ),

            "semantic": (
                candidate.get(
                    "semantic"
                )
            ),

            **definition,
        }

    # ========================================================
    # 개발밀도관리구역
    # ========================================================

    density_condition = (
        site_index.get(
            "개발밀도관리구역",
            {}
        )
    )

    density_status = (
        density_condition.get(
            "status"
        )
    )

    clause262_can_apply_now = (
        density_status
        == "TRUE"
    )

    role_results[
        "262"
    ][
        "can_apply_to_current_base"
    ] = (
        clause262_can_apply_now
    )

    role_results[
        "262"
    ][
        "site_condition"
    ] = (
        density_condition
    )

    # ========================================================
    # current base
    # ========================================================

    current_base = {
        "building_coverage_ratio": (
            BASE_REGULATION[
                "building_coverage_ratio"
            ]
        ),

        "floor_area_ratio": (
            BASE_REGULATION[
                "floor_area_ratio"
            ]
        ),
    }

    # ========================================================
    # validation
    # ========================================================

    clause61_exists = (
        61
        in candidate_index
    )

    clause233_exists = (
        233
        in candidate_index
    )

    clause262_exists = (
        262
        in candidate_index
    )

    validations = {

        "현재 SITE zone 제3종일반주거지역": (
            BASE_REGULATION[
                "zone"
            ]
            ==
            "제3종일반주거지역"
        ),

        "서울시 기본 건폐율 50": (
            current_base[
                "building_coverage_ratio"
            ][
                "value"
            ]
            == 50.0
        ),

        "서울시 기본 용적률 250": (
            current_base[
                "floor_area_ratio"
            ][
                "value"
            ]
            == 250.0
        ),

        "clause 61 candidate 존재": (
            clause61_exists
        ),

        "clause 61을 SITE base로 사용하지 않음": (
            role_results[
                "61"
            ][
                "role"
            ]
            ==
            "NATIONAL_CEILING"
        ),

        "clause 233 candidate 존재": (
            clause233_exists
        ),

        "clause 233을 SITE base로 사용하지 않음": (
            role_results[
                "233"
            ][
                "role"
            ]
            ==
            "NATIONAL_CEILING"
        ),

        "clause 262 candidate 존재": (
            clause262_exists
        ),

        "개발밀도관리구역 UNKNOWN이면 262 현재 미적용": (
            (
                density_status
                != "TRUE"
            )
            and
            not clause262_can_apply_now
        ),

        "국가 ceiling과 서울 조례 base 분리": (
            NATIONAL_CEILINGS[
                "building_coverage_ratio"
            ][
                "value"
            ]
            !=
            current_base[
                "building_coverage_ratio"
            ][
                "value"
            ]
            and
            NATIONAL_CEILINGS[
                "floor_area_ratio"
            ][
                "value"
            ]
            !=
            current_base[
                "floor_area_ratio"
            ][
                "value"
            ]
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

        "site_zone": (
            BASE_REGULATION[
                "zone"
            ]
        ),

        "current_base_regulation": (
            current_base
        ),

        "national_ceiling_reference": (
            NATIONAL_CEILINGS
        ),

        "candidate_roles": (
            role_results
        ),

        "development_density_management": {
            "status": (
                density_status
            ),

            "confidence": (
                density_condition.get(
                    "confidence"
                )
            ),

            "clause_262_apply_now": (
                clause262_can_apply_now
            ),
        },

        "calculation_policy": {

            "base_source": (
                "LOCAL_ORDINANCE"
            ),

            "national_ceiling_is_base": (
                False
            ),

            "unknown_site_condition_effect_applied": (
                False
            ),

            "rule": (
                "서울시 조례의 용도지역별 기본값을 "
                "base로 사용하고, 특례 및 강화 규칙은 "
                "별도 effect layer로 적용한다."
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
        "SITE zone:",
        BASE_REGULATION[
            "zone"
        ],
    )

    print(
        "Base BCR:",
        current_base[
            "building_coverage_ratio"
        ][
            "value"
        ],
    )

    print(
        "Base FAR:",
        current_base[
            "floor_area_ratio"
        ][
            "value"
        ],
    )

    print()

    print(
        "National BCR ceiling:",
        NATIONAL_CEILINGS[
            "building_coverage_ratio"
        ][
            "value"
        ],
    )

    print(
        "National FAR ceiling:",
        NATIONAL_CEILINGS[
            "floor_area_ratio"
        ][
            "value"
        ],
    )

    print()

    print(
        "Clause 61 role:",
        role_results[
            "61"
        ][
            "role"
        ],
    )

    print(
        "Clause 233 role:",
        role_results[
            "233"
        ][
            "role"
        ],
    )

    print()

    print(
        "개발밀도관리구역:",
        density_status,
    )

    print(
        "Clause 262 apply now:",
        clause262_can_apply_now,
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