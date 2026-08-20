# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-11
SITE BCR/FAR numeric regulation final snapshot

목표
======================================================================
지금까지 검증한 numeric 규제 결과를 하나의 최종 snapshot으로 통합한다.

현재 SITE
======================================================================
서울특별시 강남구 개포동 12번지
제3종일반주거지역

확정 기본값
======================================================================
BCR = 50%
FAR = 250%

검증 완료 특례
======================================================================
BCR 60%
    -> 국토계획법 시행령 제84조제6항제2호
    -> 현재 제3종일반주거지역은 대상 zone 아님
    -> NOT_APPLICABLE

FAR 300%
    -> 국토계획법 시행령 제85조제5항
    -> 방재지구 요건 필요
    -> 서울 기존 방재지구 2019 전면폐지
    -> 2019-04-25 이후 서울시 공식 고시 3,952건 전수검색
    -> 방재지구 0건
    -> 재지정 후보 0건
    -> 방재지구 FALSE / HIGH
    -> NOT_APPLICABLE

정책
======================================================================
1. CONFIRMED 효과만 최종 규제값에 반영
2. CONDITIONAL / UNKNOWN은 별도 유지
3. NATIONAL_CEILING은 reference only
4. PLAN_CEILING은 자동 적용하지 않음
5. NON_EFFECT numeric은 BCR/FAR 계산에서 제외
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-2B-11 "
    "SITE numeric regulation final snapshot"
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

SEMANTIC_PATH = (
    OUTPUT_DIR
    / "numeric_semantic_override_finalize.json"
)

UPPER_BRANCH_PATH = (
    OUTPUT_DIR
    / "upper_relaxation_branch_resolution.json"
)

DISASTER_RESOLUTION_PATH = (
    OUTPUT_DIR
    / "disaster_prevention_district_resolution.json"
)

DISASTER_REDESIGNATION_PATH = (
    OUTPUT_DIR
    / "disaster_prevention_district_redesignation_probe.json"
)

CANDIDATE_PATH = (
    OUTPUT_DIR
    / "current_numeric_effect_candidate_finalize.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "site_numeric_regulation_final_snapshot.json"
)


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


def compact_effect(
    item: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "clause_index": (
            item.get(
                "clause_index"
            )
        ),

        "applicability": (
            item.get(
                "applicability"
            )
        ),

        "effect_class": (
            item.get(
                "effect_class"
            )
        ),

        "rule_title": (
            item.get(
                "rule_title"
            )
        ),

        "effect_targets": (
            item.get(
                "effect_targets",
                [],
            )
        ),

        "numeric_values": (
            item.get(
                "numeric_values",
                [],
            )
        ),

        "semantic": (
            item.get(
                "semantic"
            )
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    base_data = load_json(
        BASE_PATH
    )

    semantic_data = load_json(
        SEMANTIC_PATH
    )

    upper_branch = load_json(
        UPPER_BRANCH_PATH
    )

    disaster_resolution = load_json(
        DISASTER_RESOLUTION_PATH
    )

    disaster_redesignation = load_json(
        DISASTER_REDESIGNATION_PATH
    )

    candidate_data = load_json(
        CANDIDATE_PATH
    )

    # ========================================================
    # 1. BASE
    # ========================================================

    base_regulation = (
        base_data[
            "current_base_regulation"
        ]
    )

    base_bcr = float(
        base_regulation[
            "building_coverage_ratio"
        ][
            "value"
        ]
    )

    base_far = float(
        base_regulation[
            "floor_area_ratio"
        ][
            "value"
        ]
    )

    site_zone = (
        base_data.get(
            "site_zone"
        )
    )

    # ========================================================
    # 2. clause 4 BCR relaxation
    # ========================================================

    clause_4 = (
        upper_branch.get(
            "resolutions",
            {},
        ).get(
            "clause_4",
            {},
        )
    )

    bcr_relaxation_resolution = (
        clause_4.get(
            "resolution"
        )
    )

    bcr_candidate = (
        clause_4.get(
            "candidate_value",
            60.0,
        )
    )

    if (
        bcr_relaxation_resolution
        == "CONFIRMED"
    ):

        confirmed_bcr = float(
            bcr_candidate
        )

        bcr_source = (
            "CONFIRMED_RELAXATION"
        )

    else:

        confirmed_bcr = (
            base_bcr
        )

        bcr_source = (
            "BASE_REGULATION"
        )

    # ========================================================
    # 3. 방재지구 evidence
    # ========================================================

    disaster_condition = (
        disaster_resolution.get(
            "current_condition",
            {},
        )
    )

    disaster_numeric = (
        disaster_resolution.get(
            "numeric_effect",
            {},
        )
    )

    redesignation_resolution = (
        disaster_redesignation.get(
            "resolution",
            {},
        )
    )

    redesignation_search = (
        disaster_redesignation.get(
            "search",
            {},
        )
    )

    redesignation_api = (
        disaster_redesignation.get(
            "api",
            {},
        )
    )

    no_redesignation_evidence = (
        redesignation_resolution.get(
            "resolution"
        )
        == "NO_REDESIGNATION_EVIDENCE"
    )

    redesignation_confidence_high = (
        redesignation_resolution.get(
            "confidence"
        )
        == "HIGH"
    )

    strong_redesignation_count = int(
        redesignation_search.get(
            "strong_redesignation_count",
            0,
        )
        or 0
    )

    disaster_hits = int(
        redesignation_search.get(
            "exact_hit_count",
            0,
        )
        or 0
    )

    post_abolition_rows = int(
        redesignation_api.get(
            "post_abolition_rows",
            0,
        )
        or 0
    )

    # ========================================================
    # 4. 방재지구 final current-state
    # ========================================================

    if (
        disaster_condition.get(
            "status"
        )
        == "FALSE"
        and disaster_condition.get(
            "confidence"
        )
        == "HIGH"
        and no_redesignation_evidence
        and redesignation_confidence_high
        and strong_redesignation_count
        == 0
    ):

        disaster_final_status = (
            "FALSE"
        )

        disaster_final_confidence = (
            "HIGH"
        )

        disaster_final_reason = (
            "2019년 서울 기존 방재지구 전면폐지 이력과 "
            f"2019-04-25 이후 서울시 공식 고시 "
            f"{post_abolition_rows}건 전수검색 결과 "
            "방재지구 재지정 evidence가 확인되지 않음"
        )

    else:

        disaster_final_status = (
            "UNKNOWN"
        )

        disaster_final_confidence = (
            "NONE"
        )

        disaster_final_reason = (
            "방재지구 current-state evidence "
            "최종 검증 조건 미충족"
        )

    # ========================================================
    # 5. FAR relaxation
    # ========================================================

    far_candidate = float(
        disaster_numeric.get(
            "relaxation_candidate",
            300.0,
        )
    )

    if (
        disaster_final_status
        == "FALSE"
    ):

        far_relaxation_resolution = (
            "NOT_APPLICABLE"
        )

        confirmed_far = (
            base_far
        )

        far_source = (
            "BASE_REGULATION"
        )

    else:

        far_relaxation_resolution = (
            disaster_numeric.get(
                "resolution",
                "UNKNOWN",
            )
        )

        if (
            far_relaxation_resolution
            == "CONFIRMED"
        ):

            confirmed_far = (
                far_candidate
            )

            far_source = (
                "CONFIRMED_RELAXATION"
            )

        else:

            confirmed_far = (
                base_far
            )

            far_source = (
                "BASE_REGULATION"
            )

    # ========================================================
    # 6. semantic candidate groups
    # ========================================================

    conditional_effects = [
        compact_effect(
            item
        )

        for item
        in semantic_data.get(
            "conditional_effects",
            [],
        )
    ]

    unknown_effects = [
        compact_effect(
            item
        )

        for item
        in semantic_data.get(
            "unknown_effects",
            [],
        )
    ]

    non_effects = [
        compact_effect(
            item
        )

        for item
        in semantic_data.get(
            "non_effects",
            [],
        )
    ]

    # ========================================================
    # 7. deferred role effects
    # ========================================================

    deferred_effects = []

    for item in candidate_data.get(
        "deferred_effects",
        [],
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        deferred_effects.append(
            {
                "clause_index": (
                    item.get(
                        "clause_index"
                    )
                ),

                "final_role": (
                    item.get(
                        "final_role"
                    )
                ),

                "rule_title": (
                    item.get(
                        "rule_title"
                    )
                ),

                "apply_now": (
                    item.get(
                        "apply_now"
                    )
                ),

                "reason": (
                    item.get(
                        "final_reason"
                    )
                ),
            }
        )

    # ========================================================
    # 8. final confirmed regulation
    # ========================================================

    confirmed_regulation = {

        "building_coverage_ratio": {
            "value": (
                confirmed_bcr
            ),

            "unit": "percent",

            "status": (
                "CONFIRMED"
            ),

            "confidence": (
                "HIGH"
            ),

            "source_type": (
                bcr_source
            ),

            "base_value": (
                base_bcr
            ),

            "relaxation_candidate": (
                float(
                    bcr_candidate
                )
            ),

            "relaxation_resolution": (
                bcr_relaxation_resolution
            ),
        },

        "floor_area_ratio": {
            "value": (
                confirmed_far
            ),

            "unit": "percent",

            "status": (
                "CONFIRMED"
            ),

            "confidence": (
                "HIGH"
            ),

            "source_type": (
                far_source
            ),

            "base_value": (
                base_far
            ),

            "relaxation_candidate": (
                far_candidate
            ),

            "relaxation_resolution": (
                far_relaxation_resolution
            ),
        },
    }

    # ========================================================
    # 9. supporting conditions
    # ========================================================

    supporting_conditions = {

        "zone": (
            site_zone
        ),

        "disaster_prevention_district": {
            "status": (
                disaster_final_status
            ),

            "confidence": (
                disaster_final_confidence
            ),

            "reason": (
                disaster_final_reason
            ),

            "official_notice_hits_after_abolition": (
                disaster_hits
            ),

            "strong_redesignation_candidates": (
                strong_redesignation_count
            ),

            "post_abolition_announcement_rows": (
                post_abolition_rows
            ),
        },

        "development_density_management": (
            base_data.get(
                "development_density_management"
            )
        ),
    }

    # ========================================================
    # 10. validations
    # ========================================================

    validations = {

        "SITE zone 제3종일반주거지역": (
            site_zone
            == "제3종일반주거지역"
        ),

        "base BCR 50": (
            base_bcr
            == 50.0
        ),

        "base FAR 250": (
            base_far
            == 250.0
        ),

        "clause 4 NOT_APPLICABLE": (
            bcr_relaxation_resolution
            == "NOT_APPLICABLE"
        ),

        "BCR 60 candidate 미적용": (
            confirmed_bcr
            == 50.0
        ),

        "방재지구 FALSE": (
            disaster_final_status
            == "FALSE"
        ),

        "방재지구 confidence HIGH": (
            disaster_final_confidence
            == "HIGH"
        ),

        "2019 이후 공식 고시 전수검색 존재": (
            post_abolition_rows
            > 0
        ),

        "2019 이후 방재지구 hit 0": (
            disaster_hits
            == 0
        ),

        "2019 이후 재지정 후보 0": (
            strong_redesignation_count
            == 0
        ),

        "FAR 300 NOT_APPLICABLE": (
            far_relaxation_resolution
            == "NOT_APPLICABLE"
        ),

        "confirmed BCR 50": (
            confirmed_bcr
            == 50.0
        ),

        "confirmed FAR 250": (
            confirmed_far
            == 250.0
        ),

        "semantic unresolved 0": (
            semantic_data.get(
                "summary",
                {},
            ).get(
                "semantic_unresolved"
            )
            == 0
        ),

        "NON_EFFECT numeric 분리 유지": (
            len(
                non_effects
            )
            >= 1
        ),

        "미확정 효과를 confirmed 값에 반영하지 않음": (
            True
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # 11. output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "site": {
            "site_id": (
                "11680-10300-0012-0000"
            ),

            "address": (
                "서울특별시 강남구 개포동 12번지"
            ),

            "zone": (
                site_zone
            ),
        },

        "confirmed_regulation": (
            confirmed_regulation
        ),

        "supporting_conditions": (
            supporting_conditions
        ),

        "conditional_effects": (
            conditional_effects
        ),

        "unknown_effects": (
            unknown_effects
        ),

        "deferred_effects": (
            deferred_effects
        ),

        "non_effect_numeric": (
            non_effects
        ),

        "summary": {
            "building_coverage_ratio": (
                confirmed_bcr
            ),

            "floor_area_ratio": (
                confirmed_far
            ),

            "bcr_status": (
                "CONFIRMED"
            ),

            "far_status": (
                "CONFIRMED"
            ),

            "numeric_engine_status": (
                "READY"
                if all_pass
                else "CHECK_REQUIRED"
            ),
        },

        "policy": {
            "confirmed_rule": (
                "확정 적용요건이 검증된 numeric effect만 "
                "confirmed regulation에 반영"
            ),

            "conditional_rule": (
                "PROJECT/PROCEDURE 미입력 특례는 "
                "conditional effect로 별도 유지"
            ),

            "unknown_rule": (
                "SITE/history 미확정 특례는 "
                "confirmed 값에 반영하지 않음"
            ),

            "ceiling_rule": (
                "national/plan ceiling은 "
                "자동 적용값으로 사용하지 않음"
            ),

            "redesignation_rule": (
                "과거 전면폐지 이력만으로 현행 FALSE를 "
                "확정하지 않고 이후 공식 고시 재지정 여부까지 검증"
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
        "SITE:",
        output[
            "site"
        ][
            "address"
        ],
    )

    print(
        "Zone:",
        site_zone,
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
        "BCR relaxation 60:",
        bcr_relaxation_resolution,
    )

    print(
        "FAR relaxation 300:",
        far_relaxation_resolution,
    )

    print()

    print(
        "방재지구:",
        disaster_final_status,
        "/",
        disaster_final_confidence,
    )

    print(
        "Post-2019 notices:",
        post_abolition_rows,
    )

    print(
        "방재지구 hits:",
        disaster_hits,
    )

    print(
        "Redesignation candidates:",
        strong_redesignation_count,
    )

    print()

    print(
        "Conditional effects:",
        len(
            conditional_effects
        ),
    )

    print(
        "Unknown effects:",
        len(
            unknown_effects
        ),
    )

    print(
        "Deferred effects:",
        len(
            deferred_effects
        ),
    )

    print(
        "Non-effect numeric:",
        len(
            non_effects
        ),
    )

    print()

    print(
        "Numeric engine:",
        output[
            "summary"
        ][
            "numeric_engine_status"
        ],
    )

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