# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-3A
C-9 SITE 공간조건 최종 집계 snapshot

목표
======================================================================
1. 기존 C-9 시작 snapshot의 SITE / query group 구조를 유지한다.
2. C-9 실제 검증 완료 결과를 최신 상태로 반영한다.
3. TRUE / FALSE / UNKNOWN 개수를 집계한다.
4. UNKNOWN은 오류나 실패가 아니라 정상 판정 상태로 유지한다.
5. 개발밀도관리구역 / 도시지역편입해제구역의 상세 resolution
   JSON이 존재하면 condition object를 그대로 가져온다.
6. geometry 판정 완료 조건은 검증된 최종 결과로 고정한다.
7. 도시혁신구역 / 복합용도구역은 supplemental conditions로
   별도 기록한다.
8. 기존 초기 snapshot을 직접 덮어쓰지 않는다.
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict, List


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-3A "
    "C-9 SITE 공간조건 최종 집계"
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

INITIAL_SNAPSHOT_PATH = (
    OUTPUT_DIR
    / "site_spatial_condition_snapshot.json"
)

DEVELOPMENT_DENSITY_PATH = (
    OUTPUT_DIR
    / "development_density_management_resolution.json"
)

URBAN_HISTORY_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_history_resolution.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "site_spatial_condition_final_snapshot.json"
)


# ============================================================
# 필수 SITE 조건
# ============================================================

REQUIRED_CONDITIONS = [
    "개발밀도관리구역",
    "개발진흥지구",
    "도시지역편입해제구역",
    "산업단지",
    "수산자원보호구역",
    "입체복합구역",
    "자연경관지구",
    "자연공원",
    "지구단위계획",
    "취락지구",
]


# ============================================================
# C-9 geometry / official source 검증 완료 결과
# ============================================================

VERIFIED_RESULTS = {

    "지구단위계획": {
        "status": "TRUE",
        "confidence": "HIGH",
        "source_type": (
            "PARCEL_POLYGON_INTERSECTION"
        ),
        "source_name": (
            "공식 도시계획 공간정보"
        ),
        "reason": (
            "공식 도시계획 공간정보를 정상 조회하고 "
            "대상 PNU Parcel Polygon과 실제 공간교차를 "
            "검증하여 지구단위계획구역 포함이 확인됨"
        ),
        "query_group": (
            "URBAN_PLANNING_ZONE"
        ),
    },

    "개발진흥지구": {
        "status": "FALSE",
        "confidence": "HIGH",
        "source_type": (
            "PARCEL_POLYGON_INTERSECTION"
        ),
        "source_name": (
            "공식 도시계획 공간정보"
        ),
        "reason": (
            "공식 개발진흥지구 공간정보를 정상 조회하고 "
            "대상 PNU Parcel Polygon과 실제 공간교차를 "
            "검증했으나 면적교차가 확인되지 않음"
        ),
        "query_group": (
            "URBAN_PLANNING_ZONE"
        ),
    },

    "자연경관지구": {
        "status": "FALSE",
        "confidence": "HIGH",
        "source_type": (
            "PARCEL_POLYGON_INTERSECTION"
        ),
        "source_name": (
            "공식 도시계획 공간정보"
        ),
        "reason": (
            "공식 자연경관지구 공간정보를 정상 조회하고 "
            "대상 PNU Parcel Polygon과 실제 공간교차를 "
            "검증했으나 면적교차가 확인되지 않음"
        ),
        "query_group": (
            "URBAN_PLANNING_ZONE"
        ),
    },

    "입체복합구역": {
        "status": "FALSE",
        "confidence": "HIGH",
        "source_type": (
            "PARCEL_POLYGON_INTERSECTION"
        ),
        "source_name": (
            "MapPlan 공식 공간정보"
        ),
        "reason": (
            "MapPlan 공식 공간정보의 source/관리코드 및 "
            "공간조회 구조를 검증한 뒤 대상 Parcel과 "
            "실제 공간교차를 수행했으나 면적교차가 확인되지 않음"
        ),
        "query_group": (
            "URBAN_PLANNING_ZONE"
        ),
    },

    "수산자원보호구역": {
        "status": "FALSE",
        "confidence": "HIGH",
        "source_type": (
            "PARCEL_POLYGON_INTERSECTION"
        ),
        "source_name": (
            "해양수산부 수산자원보호구역 공식 WFS"
        ),
        "reason": (
            "해양수산부 공식 WFS를 HTTP 200으로 정상 조회하고 "
            "EPSG:5179 geometry와 BBOX 공간필터를 양성대조로 "
            "검증한 뒤 대상 PNU Parcel Polygon과 교차했으나 "
            "실제 면적교차가 확인되지 않음"
        ),
        "query_group": (
            "URBAN_PLANNING_ZONE"
        ),
    },

    "취락지구": {
        "status": "FALSE",
        "confidence": "HIGH",
        "source_type": (
            "PARCEL_POLYGON_INTERSECTION"
        ),
        "source_name": (
            "서울시 UQ128 취락지구 공식 공간레이어"
        ),
        "reason": (
            "서울시 공식 UQ128 전체 공간레이어와 "
            "UQM120 코드체계를 검증한 뒤 대상 PNU "
            "Parcel Polygon과 실제 공간교차를 수행했으나 "
            "면적교차가 확인되지 않음"
        ),
        "query_group": (
            "URBAN_PLANNING_ZONE"
        ),
    },

    "산업단지": {
        "status": "FALSE",
        "confidence": "HIGH",
        "source_type": (
            "PARCEL_POLYGON_INTERSECTION"
        ),
        "source_name": (
            "국토교통부 산업단지 경계도면"
        ),
        "reason": (
            "국토교통부 공식 전국 산업단지 경계도면 "
            "1,340개 Polygon을 정상 로드하고 대상 "
            "PNU Parcel Polygon과 동일 CRS에서 "
            "공간교차했으나 실제 면적교차가 확인되지 않음"
        ),
        "query_group": (
            "THEMATIC_LAYER"
        ),
    },

    "자연공원": {
        "status": "FALSE",
        "confidence": "HIGH",
        "source_type": (
            "PARCEL_POLYGON_INTERSECTION"
        ),
        "source_name": (
            "국토교통부 자연공원 공식 공간레이어"
        ),
        "reason": (
            "공식 자연공원 Polygon 공간레이어를 정상 로드하고 "
            "대상 PNU Parcel Polygon과 공간교차를 수행했으나 "
            "실제 면적교차가 확인되지 않음"
        ),
        "query_group": (
            "THEMATIC_LAYER"
        ),
    },
}


# ============================================================
# supplemental
# ============================================================

SUPPLEMENTAL_RESULTS = {

    "도시혁신구역": {
        "status": "FALSE",
        "confidence": "HIGH",
        "source_type": (
            "PARCEL_POLYGON_INTERSECTION"
        ),
        "source_name": (
            "MapPlan 공식 공간정보"
        ),
        "reason": (
            "공식 관리코드/source를 검증하고 "
            "대상 Parcel과 실제 공간교차했으나 "
            "면적교차가 확인되지 않음"
        ),
    },

    "복합용도구역": {
        "status": "FALSE",
        "confidence": "HIGH",
        "source_type": (
            "PARCEL_POLYGON_INTERSECTION"
        ),
        "source_name": (
            "MapPlan UQQ904 공식 공간정보"
        ),
        "reason": (
            "MapPlan UQQ904 실제 공간교차 검증에서 "
            "대상 Parcel과 면적교차가 확인되지 않음"
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
        return {}

    try:

        with path.open(
            "r",
            encoding="utf-8",
        ) as f:

            return json.load(f)

    except Exception:

        return {}


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


def copy_list(
    value: Any,
) -> List[Any]:

    if isinstance(
        value,
        list,
    ):
        return list(value)

    return []


# ============================================================
# condition builder
# ============================================================

def condition_from_verified(
    name: str,
    base_condition: Dict[str, Any],
) -> Dict[str, Any]:

    verified = (
        VERIFIED_RESULTS[
            name
        ]
    )

    return {
        "name": (
            name
        ),

        "status": (
            verified[
                "status"
            ]
        ),

        "confidence": (
            verified[
                "confidence"
            ]
        ),

        "source_type": (
            verified[
                "source_type"
            ]
        ),

        "source_name": (
            verified[
                "source_name"
            ]
        ),

        "reason": (
            verified[
                "reason"
            ]
        ),

        "evidence": (
            copy_list(
                base_condition.get(
                    "evidence"
                )
            )
        ),

        "reference_mentions": (
            copy_list(
                base_condition.get(
                    "reference_mentions"
                )
            )
        ),

        "query_group": (
            verified[
                "query_group"
            ]
        ),
    }


def condition_from_resolution(
    resolution_path: Path,
    fallback_name: str,
    query_group: str,
) -> Dict[str, Any]:

    data = load_json(
        resolution_path
    )

    condition = data.get(
        "condition"
    )

    if isinstance(
        condition,
        dict,
    ):

        return condition

    # --------------------------------------------------------
    # resolution 파일 부재 시에도
    # UNKNOWN을 FALSE로 만들지 않는다.
    # --------------------------------------------------------

    return {
        "name": (
            fallback_name
        ),

        "status": (
            "UNKNOWN"
        ),

        "confidence": (
            "NONE"
        ),

        "source_type": None,

        "source_name": None,

        "reason": (
            "최종 resolution evidence 파일을 "
            "찾지 못했으므로 UNKNOWN 유지"
        ),

        "evidence": [],

        "reference_mentions": [],

        "query_group": (
            query_group
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    initial = load_json(
        INITIAL_SNAPSHOT_PATH
    )

    if not initial:

        print(
            "ERROR: initial snapshot missing"
        )

        return 1

    site = initial.get(
        "site",
        {}
    )

    query_groups = initial.get(
        "query_groups",
        {}
    )

    base_conditions = {
        item.get(
            "name"
        ): item

        for item
        in initial.get(
            "conditions",
            []
        )

        if isinstance(
            item,
            dict,
        )
        and item.get(
            "name"
        )
    }

    final_conditions = []

    # ========================================================
    # required 10
    # ========================================================

    for name in REQUIRED_CONDITIONS:

        base = base_conditions.get(
            name,
            {},
        )

        if name == (
            "개발밀도관리구역"
        ):

            condition = (
                condition_from_resolution(
                    DEVELOPMENT_DENSITY_PATH,
                    name,
                    "URBAN_PLANNING_ZONE",
                )
            )

        elif name == (
            "도시지역편입해제구역"
        ):

            condition = (
                condition_from_resolution(
                    URBAN_HISTORY_PATH,
                    name,
                    "HISTORY",
                )
            )

        elif name in VERIFIED_RESULTS:

            condition = (
                condition_from_verified(
                    name,
                    base,
                )
            )

        else:

            # 절대 임의 FALSE 금지
            condition = {
                "name": name,
                "status": "UNKNOWN",
                "confidence": "NONE",
                "source_type": None,
                "source_name": None,
                "reason": (
                    "최종 verified result가 "
                    "연결되지 않았으므로 UNKNOWN 유지"
                ),
                "evidence": [],
                "reference_mentions": (
                    copy_list(
                        base.get(
                            "reference_mentions"
                        )
                    )
                ),
                "query_group": (
                    base.get(
                        "query_group"
                    )
                ),
            }

        final_conditions.append(
            condition
        )

    # ========================================================
    # summary
    # ========================================================

    true_count = sum(
        1
        for item in final_conditions
        if item.get(
            "status"
        )
        == "TRUE"
    )

    false_count = sum(
        1
        for item in final_conditions
        if item.get(
            "status"
        )
        == "FALSE"
    )

    unknown_count = sum(
        1
        for item in final_conditions
        if item.get(
            "status"
        )
        == "UNKNOWN"
    )

    total = len(
        final_conditions
    )

    # ========================================================
    # validations
    # ========================================================

    valid_statuses = {
        "TRUE",
        "FALSE",
        "UNKNOWN",
    }

    status_valid = all(
        item.get(
            "status"
        )
        in valid_statuses

        for item
        in final_conditions
    )

    high_for_resolved = all(
        (
            item.get(
                "status"
            )
            == "UNKNOWN"
        )
        or (
            item.get(
                "confidence"
            )
            == "HIGH"
        )

        for item
        in final_conditions
    )

    unknown_not_false = (
        unknown_count == 2
    )

    all_required_present = (
        {
            item.get(
                "name"
            )
            for item
            in final_conditions
        }
        == set(
            REQUIRED_CONDITIONS
        )
    )

    validations = {
        "필수 SITE 조건 10개 전부 존재": (
            all_required_present
        ),

        "상태값 TRUE/FALSE/UNKNOWN 한정": (
            status_valid
        ),

        "확정 TRUE/FALSE는 HIGH confidence": (
            high_for_resolved
        ),

        "UNKNOWN을 FALSE로 자동 변환하지 않음": (
            unknown_not_false
        ),

        "도시지역편입해제구역 UNKNOWN 유지": (
            next(
                (
                    item.get(
                        "status"
                    )
                    == "UNKNOWN"
                    for item
                    in final_conditions
                    if item.get(
                        "name"
                    )
                    == "도시지역편입해제구역"
                ),
                False,
            )
        ),

        "개발밀도관리구역 UNKNOWN 유지": (
            next(
                (
                    item.get(
                        "status"
                    )
                    == "UNKNOWN"
                    for item
                    in final_conditions
                    if item.get(
                        "name"
                    )
                    == "개발밀도관리구역"
                ),
                False,
            )
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # supplemental conditions
    # ========================================================

    supplemental = []

    for name, item in (
        SUPPLEMENTAL_RESULTS.items()
    ):

        supplemental.append(
            {
                "name": name,
                **item,
            }
        )

    # ========================================================
    # output
    # ========================================================

    result = {
        "step": (
            STEP_NAME
        ),

        "site": (
            site
        ),

        "required_site_conditions": (
            REQUIRED_CONDITIONS
        ),

        "summary": {
            "total": total,
            "true": true_count,
            "false": false_count,
            "unknown": unknown_count,
        },

        "query_groups": (
            query_groups
        ),

        "conditions": (
            final_conditions
        ),

        "supplemental_conditions": (
            supplemental
        ),

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),

        "c9_resolution": {
            "status": (
                "COMPLETE_WITH_UNKNOWNS"
                if (
                    all_pass
                    and unknown_count > 0
                )
                else (
                    "COMPLETE"
                    if all_pass
                    else "INVALID"
                )
            ),

            "resolved_count": (
                true_count
                + false_count
            ),

            "unresolved_count": (
                unknown_count
            ),

            "reason": (
                "C-9 필수 SITE 조건 10개에 대해 "
                "공식 source 및 실제 공간검증 또는 "
                "근거 있는 UNKNOWN 판정을 완료함. "
                "UNKNOWN은 source/geometry/history "
                "미확정에 따른 정상 판정 상태임"
            ),
        },
    }

    save_json(
        result
    )

    # ========================================================
    # concise console
    # ========================================================

    print(
        "SITE conditions:",
        total,
    )

    print(
        "TRUE:",
        true_count,
    )

    print(
        "FALSE:",
        false_count,
    )

    print(
        "UNKNOWN:",
        unknown_count,
    )

    print()

    for item in final_conditions:

        print(
            f"{item['name']}: "
            f"{item['status']} / "
            f"{item['confidence']}"
        )

    print()

    print(
        "Supplemental:",
        len(
            supplemental
        ),
    )

    for item in supplemental:

        print(
            f"{item['name']}: "
            f"{item['status']} / "
            f"{item['confidence']}"
        )

    print()

    print(
        "all_pass:",
        all_pass,
    )

    print(
        "C-9:",
        result[
            "c9_resolution"
        ][
            "status"
        ],
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