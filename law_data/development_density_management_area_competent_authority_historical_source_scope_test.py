# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-11
Development Density Management Area
Competent Authority Historical Source Scope

목표
======================================================================
T-10 current canonical exact search가 0 candidate였던 이후, 같은 query를
반복하기 전에 법정 지정권자와 source role을 명시적으로 고정한다.

현행 국토의 계획 및 이용에 관한 법률 제66조 기준으로 개발밀도관리구역
지정·변경 주체는 특별시장·광역시장·특별자치시장·특별자치도지사·시장·군수이다.
따라서 성남시는 시장이 법정 지정권자 범주에 포함된다.

이 단계는 runtime legal decision이 아니라 source-scope registry hardening test이다.

원칙
======================================================================
1. 성남시 공식 고시/도시계획 source는 PRIMARY authority source candidate.
2. 소방서/부서성 게시판 등 법적 지정권한과 직접 무관한 source는 incompatible.
3. 일반 시보/재게시 archive는 SECONDARY official republication source로 분리 가능.
4. authority classification 자체는 UQQ700 SITE TRUE/FALSE 증거가 아니다.
5. historical source expansion은 PRIMARY → SECONDARY 순서로 진행한다.
6. target query/document candidate/runtime promotion은 이 단계에서 금지한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
T10_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_current_canonical_bounded_target_query_execution.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_competent_authority_historical_source_scope.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

PRIMARY = "PRIMARY_DESIGNATION_AUTHORITY_SOURCE"
SECONDARY = "SECONDARY_OFFICIAL_REPUBLICATION_SOURCE"
SUPPORTING = "SUPPORTING_OFFICIAL_SOURCE"
INCOMPATIBLE = "AUTHORITY_INCOMPATIBLE_SOURCE"
UNRESOLVED = "AUTHORITY_SCOPE_UNRESOLVED"
VALID_ROLES = {PRIMARY, SECONDARY, SUPPORTING, INCOMPATIBLE, UNRESOLVED}

AUTHORITY_BASIS = {
    "law": "국토의 계획 및 이용에 관한 법률",
    "article": "제66조",
    "designation_authority_classes": [
        "특별시장", "광역시장", "특별자치시장", "특별자치도지사", "시장", "군수"
    ],
    "designation_change_notice_required": True,
    "verified_as_of": "2026-08-27",
}

SOURCE_SCOPE: List[Dict[str, Any]] = [
    {
        "region": "경기도 성남시",
        "source_family": "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE",
        "url": "https://www.seongnam.go.kr/pm010301/list",
        "authority_role": PRIMARY,
        "authority_entity": "성남시장",
        "reasons": [
            "STATUTORY_AUTHORITY_CLASS:시장",
            "MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE",
            "REGION_BOUND:경기도 성남시",
        ],
    },
    {
        "region": "경기도 성남시",
        "source_family": "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE",
        "url": "https://www.seongnam.go.kr/ct020100",
        "authority_role": PRIMARY,
        "authority_entity": "성남시장",
        "reasons": [
            "STATUTORY_AUTHORITY_CLASS:시장",
            "MUNICIPAL_URBAN_PLANNING_SOURCE",
            "REGION_BOUND:경기도 성남시",
        ],
    },
    {
        "region": "경기도 성남시",
        "source_family": "LEGACY_LOCAL_NOTICE",
        "url": "https://119.gg.go.kr/seongnam",
        "authority_role": INCOMPATIBLE,
        "authority_entity": "경기도 소방 관련 기관",
        "reasons": [
            "OFFICIAL_HOST_ONLY_INSUFFICIENT",
            "SOURCE_FUNCTION_FIRE_SERVICE_NOT_DESIGNATION_AUTHORITY",
        ],
    },
    {
        "region": "경기도 평택시",
        "source_family": "LEGACY_LOCAL_NOTICE",
        "url": "http://119.gg.go.kr/pyeongtaek",
        "authority_role": INCOMPATIBLE,
        "authority_entity": "경기도 소방 관련 기관",
        "reasons": [
            "OFFICIAL_HOST_ONLY_INSUFFICIENT",
            "SOURCE_FUNCTION_FIRE_SERVICE_NOT_DESIGNATION_AUTHORITY",
        ],
    },
    {
        "region": "경기도 평택시",
        "source_family": "SAEOL_OFFICIAL_NOTICE_ARCHIVE",
        "url": "https://eminwon.pyeongtaek.go.kr/emwp/gov/mogaha/ntis/web/ofr/action/OfrAction.do",
        "authority_role": SECONDARY,
        "authority_entity": "평택시 공식 전자민원/고시공고 계열",
        "reasons": [
            "MUNICIPALITY_BOUND_OFFICIAL_NOTICE_REPUBLICATION",
            "SEARCH_CONTRACT_NO_OBSERVABLE_EFFECT_IN_TESTED_SHAPE",
            "PRIMARY_SOURCE_PREFERRED_OVER_SAEOL",
        ],
    },
]


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("COMPETENT AUTHORITY HISTORICAL SOURCE SCOPE")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print()

    previous_data: Dict[str, Any] = {}
    if T10_INPUT_PATH.exists():
        loaded = json.loads(T10_INPUT_PATH.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            previous_data = loaded

    primary = [item for item in SOURCE_SCOPE if item["authority_role"] == PRIMARY]
    secondary = [item for item in SOURCE_SCOPE if item["authority_role"] == SECONDARY]
    incompatible = [item for item in SOURCE_SCOPE if item["authority_role"] == INCOMPATIBLE]

    next_stage_primary_source_pool = [
        {
            **item,
            "historical_reverse_discovery_required": True,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in primary
    ]

    output_data = {
        "step": "STEP 17-21-C-16-8-T-11 Competent Authority Historical Source Scope",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "authority_basis": AUTHORITY_BASIS,
        "input": {
            "t10_path": str(T10_INPUT_PATH),
            "t10_resolution": previous_data.get("resolution"),
        },
        "source_scope_registry": SOURCE_SCOPE,
        "summary": {
            "source_scope_count": len(SOURCE_SCOPE),
            "primary_count": len(primary),
            "secondary_count": len(secondary),
            "incompatible_count": len(incompatible),
            "next_stage_primary_source_pool_count": len(next_stage_primary_source_pool),
        },
        "next_stage_primary_source_pool": next_stage_primary_source_pool,
        "resolution": "COMPETENT_AUTHORITY_SOURCE_SCOPE_ESTABLISHED",
        "next_action": (
            "T-12에서 PRIMARY designation-authority source만 대상으로 historical reverse discovery를 수행한다. "
            "exact target query 반복보다 도시관리계획/지형도면/고시번호/list pagination/archive link identity를 우선 복원한다."
        ),
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    invalid_role_leakage = sum(1 for item in SOURCE_SCOPE if item.get("authority_role") not in VALID_ROLES)
    fire_source_primary_leakage = sum(
        1 for item in SOURCE_SCOPE
        if "119.gg.go.kr" in item.get("url", "") and item.get("authority_role") == PRIMARY
    )
    unsafe_promotion_leakage = sum(
        1 for item in next_stage_primary_source_pool
        if item.get("document_candidate") is True
        or item.get("verified_positive") is True
        or item.get("runtime_registration_allowed") is True
        or item.get("site_positive_allowed") is True
        or item.get("site_negative_allowed") is True
        or item.get("final_positive_promotion_allowed") is True
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "statutory authority includes mayor": "시장" in AUTHORITY_BASIS["designation_authority_classes"],
        "designation/change notice required": AUTHORITY_BASIS["designation_change_notice_required"] is True,
        "source roles valid": invalid_role_leakage == 0,
        "primary sources present": len(primary) > 0,
        "fire-service primary leakage zero": fire_source_primary_leakage == 0,
        "next-stage pool primary only": all(item.get("authority_role") == PRIMARY for item in next_stage_primary_source_pool),
        "unsafe promotion leakage zero": unsafe_promotion_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print("Authority basis:", AUTHORITY_BASIS)
    print("Primary source count:", len(primary))
    print("Secondary source count:", len(secondary))
    print("Authority-incompatible source count:", len(incompatible))
    print("Next-stage primary source pool count:", len(next_stage_primary_source_pool))
    print()
    print("PRIMARY SOURCES")
    print("-" * 60)
    for index, item in enumerate(primary, start=1):
        print(f"[{index}] {item['source_family']}")
        print("Region:", item["region"])
        print("Authority:", item["authority_entity"])
        print("URL:", item["url"])
        print("Reasons:", item["reasons"])
        print()

    print("INCOMPATIBLE SOURCES")
    print("-" * 60)
    for index, item in enumerate(incompatible, start=1):
        print(f"[{index}] {item['url']}")
        print("Reasons:", item["reasons"])
    print()

    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Invalid role leakage:", invalid_role_leakage)
    print("Fire-service primary leakage:", fire_source_primary_leakage)
    print("Unsafe promotion leakage:", unsafe_promotion_leakage)
    print("Output:", OUTPUT_PATH)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")
    if not all_pass:
        raise AssertionError("UQQ700 competent authority historical source scope regression failed")


if __name__ == "__main__":
    main()
