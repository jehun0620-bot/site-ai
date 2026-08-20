# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-10B
서울시 방재지구 전면폐지 이력 기반 현재 상태 resolution

근거
======================================================================
서울특별시 고시 제2019-133호
2019-04-25

서울시 기존 방재지구 5개소 전부 폐지

폐지 대상
----------------------------------------------------------------------
1. 노원구 월계동 487-17 일대
2. 성동구 용답동 108-1 일대
3. 구로구 개봉본동 90-22 일대
4. 구로구 개봉본동 138-2 일대
5. 구로구 개봉본동 133-11 일대

총 면적 약 208,701.74㎡

서울시 후속 도시계획조례 개정에서도
"방재지구가 전부 해제됨"을 전제로 관련 조문 삭제.

현재 대상 SITE
======================================================================
서울특별시 강남구 개포동 12번지

판정 정책
======================================================================
- 서울시 기존 방재지구가 2019년에 전부 폐지
- 현재 서울시 공식 공간자료에서 방재지구 현행 layer를 확인하지 못함
- 현재 SITE가 과거 폐지 대상 위치에도 해당하지 않음
- 따라서 현행 방재지구 = FALSE / HIGH

주의
======================================================================
이 판정은 "침수위험 없음"을 의미하지 않는다.

방재지구:
    국토계획법상 용도지구

침수취약지역 / 자연재해위험개선지구:
    별도 제도

서로 동일하지 않음.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-2B-10B "
    "서울 방재지구 current-state resolution"
)


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

UPPER_RESOLUTION_PATH = (
    OUTPUT_DIR
    / "upper_relaxation_branch_resolution.json"
)

SOURCE_PROBE_PATH = (
    OUTPUT_DIR
    / "disaster_prevention_district_source_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "disaster_prevention_district_resolution.json"
)


SITE = {
    "site_id": "11680-10300-0012-0000",
    "address": "서울특별시 강남구 개포동 12번지",
    "sido": "서울특별시",
    "sigungu": "강남구",
    "dong": "개포동",
}


SEOUL_ABOLITION = {
    "notice": "서울특별시 고시 제2019-133호",
    "notice_date": "2019-04-25",

    "action": (
        "서울시 기존 방재지구 전부 폐지"
    ),

    "former_district_count": 5,

    "former_total_area_m2": 208701.74,

    "former_locations": [
        "노원구 월계동 487-17 일대",
        "성동구 용답동 108-1 일대",
        "구로구 개봉본동 90-22 일대",
        "구로구 개봉본동 138-2 일대",
        "구로구 개봉본동 133-11 일대",
    ],

    "reason_summary": (
        "타 법령 및 서울시 안전관리기본계획, "
        "풍수해저감 종합계획 등에 따른 관리와 "
        "방재 개선사업 시행 등으로 지정목적을 달성하고 "
        "제도운영 변화에 따라 지정 실효성이 저하되어 폐지"
    ),
}


def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():
        return {}

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


def main() -> int:

    source_probe = load_json(
        SOURCE_PROBE_PATH
    )

    upper_resolution = load_json(
        UPPER_RESOLUTION_PATH
    )

    # ========================================================
    # 1. 서울 여부
    # ========================================================

    is_seoul = (
        SITE[
            "sido"
        ]
        == "서울특별시"
    )

    # ========================================================
    # 2. 과거 폐지 대상 위치 여부
    #
    # SITE는 강남구 개포동이므로 과거 5개 지역에도 해당하지 않음
    # ========================================================

    former_location_match = any(
        token in SITE[
            "address"
        ]

        for token in (
            "월계동",
            "용답동",
            "개봉",
        )
    )

    # ========================================================
    # 3. 기존 source probe
    # ========================================================

    source_resolution = (
        source_probe.get(
            "resolution"
        )
    )

    current_layer_verified = (
        source_resolution
        == "SOURCE_FOUND"
    )

    # 현재 UM102는 자연공원이며 방재지구 evidence 없음
    no_current_spatial_evidence = (
        not current_layer_verified
    )

    # ========================================================
    # 4. current resolution
    # ========================================================

    if (
        is_seoul
        and no_current_spatial_evidence
    ):

        resolution = "FALSE"
        confidence = "HIGH"

        reason = (
            "서울특별시 고시 제2019-133호(2019-04-25)로 "
            "서울시 기존 방재지구 5개소가 전부 폐지되었고, "
            "후속 서울시 도시계획조례 개정에서도 "
            "방재지구 전면 해제를 전제로 관련 규정을 삭제함. "
            "현재 서울 공식 공간자료에서도 방재지구 현행 "
            "공간레이어 evidence를 확인하지 못했으므로 "
            "대상 SITE의 현행 방재지구 해당 여부를 FALSE로 판정"
        )

    else:

        resolution = "UNKNOWN"
        confidence = "NONE"

        reason = (
            "방재지구 current-state evidence가 충분하지 않음"
        )

    # ========================================================
    # 5. clause 189 FAR effect
    # ========================================================

    far_relaxation_candidate = 300.0

    if resolution == "FALSE":

        clause_189_resolution = (
            "NOT_APPLICABLE"
        )

        clause_189_apply = False

        confirmed_far = 250.0

        far_reason = (
            "국토계획법 시행령 제85조제5항의 "
            "방재지구 요건이 FALSE이므로 "
            "서울시 조례 clause 189 FAR 300% "
            "완화후보는 적용되지 않음"
        )

    elif resolution == "TRUE":

        clause_189_resolution = (
            "CONDITIONAL"
        )

        clause_189_apply = False

        confirmed_far = 250.0

        far_reason = (
            "방재지구는 TRUE이나 재해예방시설 "
            "PROJECT 조건 확인 필요"
        )

    else:

        clause_189_resolution = (
            "UNKNOWN"
        )

        clause_189_apply = False

        confirmed_far = 250.0

        far_reason = (
            "방재지구 상태 미확정"
        )

    # ========================================================
    # 6. validations
    # ========================================================

    validations = {

        "SITE 서울특별시": (
            is_seoul
        ),

        "2019 서울 방재지구 전면폐지 근거 등록": (
            SEOUL_ABOLITION[
                "former_district_count"
            ]
            == 5
        ),

        "SITE 과거 폐지 5개소 위치와 불일치": (
            former_location_match
            is False
        ),

        "현재 방재지구 공간 evidence 없음": (
            no_current_spatial_evidence
        ),

        "방재지구 FALSE": (
            resolution
            == "FALSE"
        ),

        "confidence HIGH": (
            confidence
            == "HIGH"
        ),

        "clause 189 NOT_APPLICABLE": (
            clause_189_resolution
            == "NOT_APPLICABLE"
        ),

        "FAR 300 candidate 미적용": (
            clause_189_apply
            is False
        ),

        "confirmed FAR 250": (
            confirmed_far
            == 250.0
        ),
    }

    all_pass = all(
        validations.values()
    )

    output = {
        "step": STEP_NAME,

        "site": SITE,

        "official_history": (
            SEOUL_ABOLITION
        ),

        "source_probe": {
            "resolution": (
                source_resolution
            ),

            "current_spatial_layer_verified": (
                current_layer_verified
            ),
        },

        "current_condition": {
            "name": "방재지구",

            "status": (
                resolution
            ),

            "confidence": (
                confidence
            ),

            "reason": (
                reason
            ),
        },

        "numeric_effect": {
            "clause_index": 189,

            "base_far": 250.0,

            "relaxation_candidate": (
                far_relaxation_candidate
            ),

            "resolution": (
                clause_189_resolution
            ),

            "apply_now": (
                clause_189_apply
            ),

            "confirmed_far": (
                confirmed_far
            ),

            "reason": (
                far_reason
            ),
        },

        "important_note": (
            "방재지구 FALSE는 침수취약지역, "
            "자연재해위험개선지구, 재해지도 등의 "
            "별도 재해위험 제도까지 FALSE라는 의미가 아님"
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
        "Official abolition:",
        SEOUL_ABOLITION[
            "notice"
        ],
    )

    print(
        "Former districts:",
        SEOUL_ABOLITION[
            "former_district_count"
        ],
    )

    print(
        "Current spatial evidence:",
        current_layer_verified,
    )

    print()

    print(
        "방재지구:",
        resolution,
    )

    print(
        "confidence:",
        confidence,
    )

    print()

    print(
        "clause 189:",
        clause_189_resolution,
    )

    print(
        "FAR candidate:",
        far_relaxation_candidate,
    )

    print(
        "apply now:",
        clause_189_apply,
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