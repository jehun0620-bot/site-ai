# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-9
상위 시행령 relaxation branch 정식 resolution

대상
======================================================================
clause 4
    서울특별시 도시계획 조례
    영 제84조제6항제2호
    BCR 120%

clause 189
    서울특별시 도시계획 조례
    영 제85조제5항
    FAR 120%

현행 시행령 원 branch
======================================================================

[제84조제6항제2호]

대상 용도지역:
- 녹지지역
- 관리지역
- 농림지역
- 자연환경보전지역

추가 요건:
- 방재지구
- 재해저감대책에 부합
- 재해예방시설 설치

현재 SITE:
제3종일반주거지역

따라서 clause 4:
NOT_APPLICABLE


[제85조제5항]

대상:
법 제37조제4항 후단에 따른 방재지구

추가 요건:
재해저감대책에 부합하게 재해예방시설 설치

제1항제1호~제13호 용도지역 적용 가능
-> 제3종일반주거지역 포함

현재:
방재지구 SITE condition 미확정
재해예방시설 PROJECT condition 미입력

따라서 clause 189:
UNKNOWN 우선
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-2B-9 "
    "upper relaxation branch resolution"
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

SITE_PATH = (
    OUTPUT_DIR
    / "site_spatial_condition_final_snapshot.json"
)

PROJECT_PATH = (
    OUTPUT_DIR
    / "project_profile_template.json"
)

GUARD_PATH = (
    OUTPUT_DIR
    / "resolved_relaxation_applicability_guard.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "upper_relaxation_branch_resolution.json"
)


# ============================================================
# 현재 SITE zone
# ============================================================

SITE_ZONE = (
    "제3종일반주거지역"
)


# ============================================================
# 제84조제6항제2호 대상 zone groups
# ============================================================

BCR_84_6_2_ZONE_GROUPS = {
    "녹지지역",
    "보전녹지지역",
    "생산녹지지역",
    "자연녹지지역",

    "관리지역",
    "보전관리지역",
    "생산관리지역",
    "계획관리지역",

    "농림지역",

    "자연환경보전지역",
}


# ============================================================
# 제85조제5항 적용 대상
#
# 시행령 제85조제1항 제1호~제13호
# ============================================================

FAR_85_5_ZONE_GROUPS = {
    "제1종전용주거지역",
    "제2종전용주거지역",
    "제1종일반주거지역",
    "제2종일반주거지역",
    "제3종일반주거지역",
    "준주거지역",

    "중심상업지역",
    "일반상업지역",
    "근린상업지역",
    "유통상업지역",

    "전용공업지역",
    "일반공업지역",
    "준공업지역",
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
# SITE condition
# ============================================================

def build_site_index(
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

            result[name] = {
                "state": safe_string(
                    item.get(
                        "status"
                    )
                ),

                "confidence": safe_string(
                    item.get(
                        "confidence"
                    )
                ),

                "source": (
                    "SITE_SPATIAL_CONDITION"
                ),
            }

    return result


# ============================================================
# PROJECT condition
# ============================================================

def build_project_index(
    profile: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:

    result = {}

    for item in profile.get(
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

        if not name:
            continue

        result[name] = {
            "state": safe_string(
                item.get(
                    "state"
                )
            ),

            "value": (
                item.get(
                    "value"
                )
            ),

            "confidence": safe_string(
                item.get(
                    "confidence"
                )
            ),

            "source": (
                "PROJECT_PROFILE"
            ),
        }

    return result


# ============================================================
# 신규 branch condition resolver
# ============================================================

def resolve_site_condition(
    name: str,
    site_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    value = site_index.get(
        name
    )

    if value:

        return {
            "name": name,
            "type": "SITE",
            **value,
        }

    return {
        "name": name,
        "type": "SITE",
        "state": "UNKNOWN",
        "confidence": "NONE",
        "source": (
            "SITE_CONDITION_NOT_CONNECTED"
        ),
    }


def resolve_project_condition(
    name: str,
    project_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    value = project_index.get(
        name
    )

    if value:

        return {
            "name": name,
            "type": "PROJECT",
            **value,
        }

    return {
        "name": name,
        "type": "PROJECT",
        "state": "UNSET",
        "value": None,
        "confidence": "NONE",
        "source": (
            "PROJECT_INPUT_REQUIRED"
        ),
    }


# ============================================================
# clause 4
# ============================================================

def resolve_clause_4() -> Dict[str, Any]:

    zone_match = (
        SITE_ZONE
        in BCR_84_6_2_ZONE_GROUPS
    )

    if not zone_match:

        resolution = (
            "NOT_APPLICABLE"
        )

        reason = (
            "영 제84조제6항제2호는 "
            "녹지지역ㆍ관리지역ㆍ농림지역ㆍ"
            "자연환경보전지역의 건축물을 대상으로 하나 "
            f"현재 SITE는 {SITE_ZONE}이므로 적용대상이 아님"
        )

    else:

        resolution = (
            "UNKNOWN"
        )

        reason = (
            "용도지역은 대상이나 방재지구 및 "
            "재해예방시설 요건 추가 검증 필요"
        )

    return {
        "clause_index": 4,

        "upper_reference": (
            "국토계획법 시행령 "
            "제84조제6항제2호"
        ),

        "effect": (
            "building_coverage_ratio"
        ),

        "base_value": 50.0,

        "candidate_value": 60.0,

        "required_zone_groups": (
            sorted(
                BCR_84_6_2_ZONE_GROUPS
            )
        ),

        "site_zone": (
            SITE_ZONE
        ),

        "zone_match": (
            zone_match
        ),

        "resolution": (
            resolution
        ),

        "reason": (
            reason
        ),

        "apply_candidate_now": (
            resolution
            == "CONFIRMED"
        ),
    }


# ============================================================
# clause 189
# ============================================================

def resolve_clause_189(
    site_index: Dict[str, Dict[str, Any]],
    project_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    zone_match = (
        SITE_ZONE
        in FAR_85_5_ZONE_GROUPS
    )

    disaster_zone = (
        resolve_site_condition(
            "방재지구",
            site_index,
        )
    )

    disaster_prevention = (
        resolve_project_condition(
            "재해예방시설",
            project_index,
        )
    )

    conditions = [
        disaster_zone,
        disaster_prevention,
    ]

    # --------------------------------------------------------
    # zone 자체가 대상 아님
    # --------------------------------------------------------

    if not zone_match:

        resolution = (
            "NOT_APPLICABLE"
        )

        reason = (
            "영 제85조제5항의 대상 용도지역이 아님"
        )

    # --------------------------------------------------------
    # FALSE 우선
    # --------------------------------------------------------

    elif any(
        item[
            "state"
        ]
        == "FALSE"

        for item
        in conditions
    ):

        resolution = (
            "NOT_APPLICABLE"
        )

        reason = (
            "방재지구 또는 재해예방시설 "
            "필수조건이 FALSE"
        )

    # --------------------------------------------------------
    # SITE unknown 우선
    # --------------------------------------------------------

    elif any(
        (
            item[
                "type"
            ]
            == "SITE"
            and item[
                "state"
            ]
            == "UNKNOWN"
        )

        for item
        in conditions
    ):

        resolution = (
            "UNKNOWN"
        )

        reason = (
            "방재지구 SITE 여부가 아직 미확정"
        )

    # --------------------------------------------------------
    # project UNSET
    # --------------------------------------------------------

    elif any(
        item[
            "state"
        ]
        == "UNSET"

        for item
        in conditions
    ):

        resolution = (
            "CONDITIONAL"
        )

        reason = (
            "재해예방시설 설치 여부 PROJECT 입력 필요"
        )

    else:

        resolution = (
            "CONFIRMED"
        )

        reason = (
            "방재지구 및 재해예방시설 조건 충족"
        )

    return {
        "clause_index": 189,

        "upper_reference": (
            "국토계획법 시행령 "
            "제85조제5항"
        ),

        "effect": (
            "floor_area_ratio"
        ),

        "base_value": 250.0,

        "candidate_value": 300.0,

        "national_max_factor": (
            1.40
        ),

        "seoul_ordinance_factor": (
            1.20
        ),

        "required_zone_groups": (
            sorted(
                FAR_85_5_ZONE_GROUPS
            )
        ),

        "site_zone": (
            SITE_ZONE
        ),

        "zone_match": (
            zone_match
        ),

        "conditions": (
            conditions
        ),

        "resolution": (
            resolution
        ),

        "reason": (
            reason
        ),

        "apply_candidate_now": (
            resolution
            == "CONFIRMED"
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    site_data = load_json(
        SITE_PATH
    )

    project_data = load_json(
        PROJECT_PATH
    )

    guard_data = load_json(
        GUARD_PATH
    )

    site_index = build_site_index(
        site_data
    )

    project_index = (
        build_project_index(
            project_data
        )
    )

    clause_4 = (
        resolve_clause_4()
    )

    clause_189 = (
        resolve_clause_189(
            site_index,
            project_index,
        )
    )

    # ========================================================
    # confirmed regulation
    # ========================================================

    if clause_4[
        "apply_candidate_now"
    ]:

        confirmed_bcr = (
            clause_4[
                "candidate_value"
            ]
        )

        bcr_source = (
            "CLAUSE_4_RELAXATION"
        )

    else:

        confirmed_bcr = (
            clause_4[
                "base_value"
            ]
        )

        bcr_source = (
            "BASE_REGULATION"
        )

    if clause_189[
        "apply_candidate_now"
    ]:

        confirmed_far = (
            clause_189[
                "candidate_value"
            ]
        )

        far_source = (
            "CLAUSE_189_RELAXATION"
        )

    else:

        confirmed_far = (
            clause_189[
                "base_value"
            ]
        )

        far_source = (
            "BASE_REGULATION"
        )

    final_status = {
        "building_coverage_ratio": {
            "confirmed_value": (
                confirmed_bcr
            ),

            "base_value": 50.0,

            "relaxation_candidate": (
                60.0
            ),

            "relaxation_resolution": (
                clause_4[
                    "resolution"
                ]
            ),

            "source": (
                bcr_source
            ),
        },

        "floor_area_ratio": {
            "confirmed_value": (
                confirmed_far
            ),

            "base_value": 250.0,

            "relaxation_candidate": (
                300.0
            ),

            "relaxation_resolution": (
                clause_189[
                    "resolution"
                ]
            ),

            "source": (
                far_source
            ),
        },
    }

    # ========================================================
    # previous guard consistency
    # ========================================================

    previous = (
        guard_data.get(
            "current_confirmed_result",
            {}
        )
    )

    previous_bcr = (
        previous.get(
            "building_coverage_ratio",
            {},
        ).get(
            "confirmed_value"
        )
    )

    previous_far = (
        previous.get(
            "floor_area_ratio",
            {},
        ).get(
            "confirmed_value"
        )
    )

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "제3종일반주거지역은 84조6항2호 대상 아님": (
            clause_4[
                "zone_match"
            ]
            is False
        ),

        "clause 4 NOT_APPLICABLE": (
            clause_4[
                "resolution"
            ]
            == "NOT_APPLICABLE"
        ),

        "BCR candidate 60 현재 미적용": (
            clause_4[
                "apply_candidate_now"
            ]
            is False
        ),

        "제3종일반주거지역은 85조5항 용도지역 범위 포함": (
            clause_189[
                "zone_match"
            ]
            is True
        ),

        "clause 189 방재지구 condition 생성": (
            any(
                item[
                    "name"
                ]
                == "방재지구"

                for item
                in clause_189[
                    "conditions"
                ]
            )
        ),

        "clause 189 재해예방시설 condition 생성": (
            any(
                item[
                    "name"
                ]
                == "재해예방시설"

                for item
                in clause_189[
                    "conditions"
                ]
            )
        ),

        "미확정 FAR relaxation을 현재 확정값으로 사용하지 않음": (
            (
                clause_189[
                    "resolution"
                ]
                == "CONFIRMED"
            )
            or confirmed_far
            == 250.0
        ),

        "BCR confirmed 50": (
            confirmed_bcr
            == 50.0
        ),

        "기존 guard와 BCR 일관": (
            previous_bcr
            == 50.0
        ),

        "기존 guard와 FAR 일관": (
            previous_far
            == 250.0
        ),
    }

    all_pass = all(
        validations.values()
    )

    output = {
        "step": (
            STEP_NAME
        ),

        "source_verification": {
            "national_enforcement_decree_effective": (
                "2026-07-01"
            ),

            "clause_4_upper_branch": (
                "제84조제6항제2호"
            ),

            "clause_189_upper_branch": (
                "제85조제5항"
            ),
        },

        "resolutions": {
            "clause_4": (
                clause_4
            ),

            "clause_189": (
                clause_189
            ),
        },

        "current_confirmed_regulation": (
            final_status
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
        "SITE zone:",
        SITE_ZONE,
    )

    print()

    print(
        "clause 4:",
        clause_4[
            "resolution"
        ],
    )

    print(
        "  zone match:",
        clause_4[
            "zone_match"
        ],
    )

    print(
        "  BCR candidate:",
        clause_4[
            "candidate_value"
        ],
    )

    print(
        "  apply now:",
        clause_4[
            "apply_candidate_now"
        ],
    )

    print()

    print(
        "clause 189:",
        clause_189[
            "resolution"
        ],
    )

    print(
        "  zone match:",
        clause_189[
            "zone_match"
        ],
    )

    print(
        "  conditions:",
        [
            (
                item[
                    "name"
                ],
                item[
                    "state"
                ],
            )
            for item
            in clause_189[
                "conditions"
            ]
        ],
    )

    print(
        "  FAR candidate:",
        clause_189[
            "candidate_value"
        ],
    )

    print(
        "  apply now:",
        clause_189[
            "apply_candidate_now"
        ],
    )

    print()

    print(
        "Confirmed BCR:",
        confirmed_bcr,
    )

    print(
        "Confirmed FAR:",
        confirmed_far,
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