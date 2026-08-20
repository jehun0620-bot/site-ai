# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-15B
개발밀도관리구역 evidence 종합 / UNKNOWN 판정 패키징

목표
======================================================================
1. 지금까지 수행한 개발밀도관리구역 관련 probe JSON을 읽는다.
2. 공식 source별 negative / unresolved evidence를 종합한다.
3. 서울시 결정고시 43,508건 전수검색 결과를 포함한다.
4. UQ145가 개발밀도관리구역 source가 아님을 명시한다.
5. source/geometry 미확정이므로 FALSE로 변환하지 않는다.
6. 기존 site_spatial_condition_snapshot 형식과 호환되는
   condition object를 출력한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-9-2-15B "
    "개발밀도관리구역 evidence 종합"
)

CONDITION_NAME = (
    "개발밀도관리구역"
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

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR
    / "site_spatial_query_context.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "development_density_management_resolution.json"
)


EVIDENCE_FILES = {
    "initial_probe": (
        "seoul_development_density_management_area_probe.json"
    ),

    "uq145_probe": (
        "development_density_uq145_probe.json"
    ),

    "notice_probe": (
        "seoul_development_density_notice_probe.json"
    ),

    "announcement_full": (
        "development_density_management_announcement_full_probe.json"
    ),
}


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


def load_site() -> Dict[str, str]:

    data = load_json(
        QUERY_CONTEXT_PATH
    )

    context = data.get(
        "query_context",
        {},
    )

    return {
        "site_id": safe_string(
            context.get(
                "site_id"
            )
        ),
        "address": safe_string(
            context.get(
                "address"
            )
        ),
        "pnu": safe_string(
            context.get(
                "pnu"
            )
        ),
    }


def load_all_evidence() -> Dict[
    str,
    Dict[str, Any]
]:

    result = {}

    for key, filename in (
        EVIDENCE_FILES.items()
    ):

        result[key] = load_json(
            OUTPUT_DIR / filename
        )

    return result


def get_nested(
    data: Dict[str, Any],
    *keys,
    default=None,
):

    value: Any = data

    for key in keys:

        if not isinstance(
            value,
            dict,
        ):
            return default

        value = value.get(
            key
        )

        if value is None:
            return default

    return value


def build_checks(
    evidence: Dict[
        str,
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    initial = evidence[
        "initial_probe"
    ]

    uq145 = evidence[
        "uq145_probe"
    ]

    notice = evidence[
        "notice_probe"
    ]

    announcement = evidence[
        "announcement_full"
    ]

    # --------------------------------------------------------
    # EUM / MapPlan
    # --------------------------------------------------------

    eum_http = initial.get(
        "eum_http"
    )

    eum_name_present = initial.get(
        "name_present"
    )

    mapplan_server = initial.get(
        "mapplan_server"
    )

    # 기존 JSON key명이 다를 가능성 대응
    if eum_http is None:

        eum_http = initial.get(
            "EUM HTTP"
        )

    if eum_name_present is None:

        eum_name_present = initial.get(
            "name_present",
            False,
        )

    # --------------------------------------------------------
    # UQ145
    # --------------------------------------------------------

    uq145_feature_count = (
        uq145.get(
            "feature_count",
            uq145.get(
                "Feature",
                0,
            ),
        )
        or 0
    )

    uq145_target_exact_hits = (
        uq145.get(
            "target_exact_hits",
            0,
        )
        or 0
    )

    uq145_target_contains_hits = (
        uq145.get(
            "target_contains_hits",
            0,
        )
        or 0
    )

    # 결과에서 확인된 실제 코드
    uq145_not_target_layer = (
        uq145_target_exact_hits == 0
        and uq145_target_contains_hits == 0
    )

    # --------------------------------------------------------
    # 기존 notice probe
    # --------------------------------------------------------

    notice_http_success = (
        notice.get(
            "http_success",
            0,
        )
        or 0
    )

    notice_target_hits = (
        notice.get(
            "target_hits",
            0,
        )
        or 0
    )

    # --------------------------------------------------------
    # upisAnnouncement 전수검색
    # --------------------------------------------------------

    announcement_query_success = (
        get_nested(
            announcement,
            "api",
            "query_status",
        )
        == "QUERY_SUCCESS"
    )

    announcement_total = (
        get_nested(
            announcement,
            "api",
            "total_count",
            default=0,
        )
        or 0
    )

    exact_hits = (
        get_nested(
            announcement,
            "search",
            "exact_hit_count",
            default=0,
        )
        or 0
    )

    site_exact_hits = (
        get_nested(
            announcement,
            "search",
            "site_exact_hit_count",
            default=0,
        )
        or 0
    )

    broad_hits = (
        get_nested(
            announcement,
            "search",
            "broad_hit_count",
            default=0,
        )
        or 0
    )

    return {
        "eum_http": (
            eum_http
        ),

        "eum_name_present": (
            bool(
                eum_name_present
            )
        ),

        "mapplan_source_confirmed": (
            bool(
                mapplan_server
            )
        ),

        "uq145_feature_count": (
            uq145_feature_count
        ),

        "uq145_target_exact_hits": (
            uq145_target_exact_hits
        ),

        "uq145_target_contains_hits": (
            uq145_target_contains_hits
        ),

        "uq145_is_not_target_source": (
            uq145_not_target_layer
        ),

        "notice_probe_http_success": (
            notice_http_success
        ),

        "notice_probe_target_hits": (
            notice_target_hits
        ),

        "announcement_query_success": (
            announcement_query_success
        ),

        "announcement_total_count": (
            announcement_total
        ),

        "announcement_exact_hits": (
            exact_hits
        ),

        "announcement_site_exact_hits": (
            site_exact_hits
        ),

        "announcement_broad_hits": (
            broad_hits
        ),
    }


def build_evidence_summary(
    checks: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return [
        {
            "type": (
                "LAND_USE_INFORMATION"
            ),
            "source": (
                "토지이용계획/EUM"
            ),
            "result": (
                "NO_NAME_EVIDENCE"
            ),
            "detail": (
                "정상 HTTP 응답에서 "
                "개발밀도관리구역 명칭 확인되지 않음"
            ),
        },

        {
            "type": (
                "MAP_SOURCE"
            ),
            "source": (
                "MapPlan"
            ),
            "result": (
                "SOURCE_UNVERIFIED"
            ),
            "detail": (
                "개발밀도관리구역에 대응하는 "
                "신뢰 가능한 MapPlan layer/source를 "
                "확정하지 못함"
            ),
        },

        {
            "type": (
                "SPATIAL_LAYER_PROBE"
            ),
            "source": (
                "서울시 UQ145"
            ),
            "result": (
                "NOT_TARGET_DATASET"
            ),
            "detail": (
                "UQ145 공간파일은 존재하지만 "
                "실제 DGM_NM/ATRB_SE 분석 결과 "
                "소로3류(UQS122)이며 "
                "개발밀도관리구역 layer가 아님"
            ),
        },

        {
            "type": (
                "OFFICIAL_NOTICE_PROBE"
            ),
            "source": (
                "서울시 고시 관련 probe"
            ),
            "result": (
                "NO_TARGET_HIT"
            ),
            "detail": (
                f"정상 HTTP 조회 "
                f"{checks['notice_probe_http_success']}건, "
                f"target hit "
                f"{checks['notice_probe_target_hits']}건"
            ),
        },

        {
            "type": (
                "OFFICIAL_NOTICE_DATABASE"
            ),
            "source": (
                "서울특별시 upisAnnouncement"
            ),
            "result": (
                "NO_TARGET_HIT"
            ),
            "detail": (
                f"결정고시 "
                f"{checks['announcement_total_count']:,}건 전수조회, "
                f"정확명칭 "
                f"{checks['announcement_exact_hits']}건, "
                f"SITE 정확명칭 "
                f"{checks['announcement_site_exact_hits']}건, "
                f"광의 문자열 "
                f"{checks['announcement_broad_hits']}건"
            ),
        },
    ]


def main() -> int:

    site = load_site()

    evidence = load_all_evidence()

    checks = build_checks(
        evidence
    )

    evidence_summary = (
        build_evidence_summary(
            checks
        )
    )

    # --------------------------------------------------------
    # 최종 판정
    # --------------------------------------------------------

    status = "UNKNOWN"
    confidence = "MEDIUM"

    reason = (
        "개발밀도관리구역은 국토계획법 제66조에 따른 "
        "별도 지정·고시 대상이다. "
        "토지이용계획에서 해당 명칭이 확인되지 않았고, "
        "서울시 결정고시 전체 DB를 정상 조회했으나 "
        "개발밀도관리구역 또는 관련 광의 문자열 고시는 "
        "확인되지 않았다. 또한 UQ145는 실제 schema 분석 결과 "
        "개발밀도관리구역 공간레이어가 아닌 것으로 확인됐다. "
        "그러나 서울시가 해당 구역을 지정하지 않았음을 직접 "
        "증명하는 공식 전국/서울 전용 공간레이어나 "
        "명시적 '지정 없음' source를 확보하지 못했으므로 "
        "검색 부재를 FALSE 근거로 사용하지 않고 UNKNOWN을 유지한다."
    )

    condition_object = {
        "name": (
            CONDITION_NAME
        ),

        "status": (
            status
        ),

        "confidence": (
            confidence
        ),

        "source_type": (
            "MULTI_SOURCE_NEGATIVE_EVIDENCE"
        ),

        "source_name": (
            "EUM + 서울시 upisAnnouncement + "
            "서울시 공간레이어 probe"
        ),

        "reason": (
            reason
        ),

        "evidence": (
            evidence_summary
        ),

        "reference_mentions": [
            "개발밀도관리구역의 지정기준 및 관리방법"
        ],

        "query_group": (
            "URBAN_PLANNING_ZONE"
        ),
    }

    result = {
        "step": (
            STEP_NAME
        ),

        "site": (
            site
        ),

        "condition": (
            condition_object
        ),

        "checks": (
            checks
        ),

        "validation_rules": {
            "검색 부재만으로 FALSE 판정 금지": True,
            "잘못된 UQ layer를 source로 사용 금지": True,
            "HTTP 실패를 FALSE evidence로 사용 금지": True,
            "공식 geometry/source 미확정 시 UNKNOWN 유지": True,
        },

        "pending_evidence": [
            {
                "type": (
                    "OFFICIAL_SPATIAL_DATASET"
                ),
                "description": (
                    "개발밀도관리구역 전용 공식 "
                    "서울/전국 Polygon layer 확인 필요"
                ),
            },
            {
                "type": (
                    "OFFICIAL_NO_DESIGNATION_EVIDENCE"
                ),
                "description": (
                    "서울특별시 개발밀도관리구역 지정 현황 "
                    "또는 지정 없음 공식 source 확보"
                ),
            },
        ],

        "next_resolution_trigger": (
            "공식 개발밀도관리구역 geometry 또는 "
            "서울시 지정현황 자료가 확보될 경우 재판정"
        ),
    }

    save_json(
        result
    )

    # --------------------------------------------------------
    # concise console
    # --------------------------------------------------------

    print(
        "Announcement DB:",
        (
            "OK"
            if checks[
                "announcement_query_success"
            ]
            else "FAIL"
        ),
    )

    print(
        "Announcement rows:",
        checks[
            "announcement_total_count"
        ],
    )

    print(
        "Exact hits:",
        checks[
            "announcement_exact_hits"
        ],
    )

    print(
        "Broad hits:",
        checks[
            "announcement_broad_hits"
        ],
    )

    print(
        "UQ145 target source:",
        (
            not checks[
                "uq145_is_not_target_source"
            ]
        ),
    )

    print(
        "resolution:",
        status,
    )

    print(
        "confidence:",
        confidence,
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )