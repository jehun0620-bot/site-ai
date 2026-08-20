# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14G
도시지역편입해제구역 history evidence 종합 / UNKNOWN 판정 패키징

목표
======================================================================
1. 지금까지 생성한 핵심 evidence JSON을 읽는다.
2. 개별 probe 결과를 하나의 정식 condition result로 종합한다.
3. 다음 사실을 검증한다.

   - 서울시 결정고시 전체 DB 정상조회
   - SITE 관련 결합 후보 검토 완료
   - target-history 후보 0
   - 개포동 12번지 직접 고시는 지구단위계획 변경으로 비대상
   - 현행 UQ111 도시지역 Parcel 교차 확인
   - 현행 UQ141 개발제한구역 Parcel 교차 없음
   - 1989 최초 택지개발 chain 존재
   - 최초 지정/협의 원문 내용은 아직 미확정
   - 국가기록원 공식 원기록 후보 존재
   - 원문 상태는 UNVERIFIED

4. 과거 편입/해제 부재를 완전히 입증하지 못했으므로 UNKNOWN 유지
5. source 미확정/원문 미확보를 FALSE로 변환하지 않는다.
6. 이후 원문 evidence가 확보되면 이 객체만 TRUE/FALSE로 승격 가능하게 한다.
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-14G "
    "도시지역편입해제구역 history evidence 종합"
)

CONDITION_NAME = (
    "도시지역편입해제구역"
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

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR
    / "site_spatial_query_context.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_history_resolution.json"
)


# ============================================================
# 핵심 evidence
# ============================================================

EVIDENCE_FILES = {
    "definition": (
        "urban_area_inclusion_release_definition_probe.json"
    ),

    "announcement": (
        "urban_area_conversion_announcement_probe.json"
    ),

    "combined_notice": (
        "urban_area_conversion_combined_notice_summary.json"
    ),

    "direct_notice": (
        "urban_area_conversion_direct_notice_probe.json"
    ),

    "current_state": (
        "urban_area_conversion_current_state.json"
    ),

    "initial_notice": (
        "daechi_initial_designation_notice_probe.json"
    ),

    "notice_chain": (
        "daechi_1989_notice_chain_probe.json"
    ),

    "notice_123": (
        "daechi_notice_123_exact_probe.json"
    ),

    "notice_534": (
        "daechi_1989_534_content_profile.json"
    ),

    "national_archive": (
        "daechi_national_archive_file_probe.json"
    ),
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


# ============================================================
# SITE
# ============================================================

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


# ============================================================
# evidence load
# ============================================================

def load_all_evidence() -> Dict[
    str,
    Dict[str, Any]
]:

    result = {}

    for (
        key,
        filename,
    ) in EVIDENCE_FILES.items():

        path = (
            OUTPUT_DIR
            / filename
        )

        result[
            key
        ] = load_json(
            path
        )

    return result


# ============================================================
# evidence assertions
# ============================================================

def build_checks(
    evidence: Dict[
        str,
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    announcement = evidence[
        "announcement"
    ]

    combined = evidence[
        "combined_notice"
    ]

    direct = evidence[
        "direct_notice"
    ]

    current = evidence[
        "current_state"
    ]

    initial = evidence[
        "initial_notice"
    ]

    chain = evidence[
        "notice_chain"
    ]

    notice_123 = evidence[
        "notice_123"
    ]

    notice_534 = evidence[
        "notice_534"
    ]

    archive = evidence[
        "national_archive"
    ]

    # --------------------------------------------------------
    # 서울시 결정고시
    # --------------------------------------------------------

    announcement_success = (
        get_nested(
            announcement,
            "api",
            "result_code",
        )
        == "INFO-000"
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

    # --------------------------------------------------------
    # 결합 후보 최종 분류
    # --------------------------------------------------------

    combined_count = (
        combined.get(
            "input_combined_count",
            0,
        )
        or 0
    )

    target_candidate_count = (
        combined.get(
            "target_candidate_count",
            0,
        )
        or 0
    )

    unresolved_count = (
        combined.get(
            "unresolved_count",
            0,
        )
        or 0
    )

    all_combined_classified = (
        combined_count > 0
        and target_candidate_count == 0
        and unresolved_count == 0
    )

    # --------------------------------------------------------
    # 직접 주소 고시
    # --------------------------------------------------------

    direct_hit_count = (
        direct.get(
            "direct_hit_count",
            0,
        )
        or 0
    )

    direct_target_event_count = (
        direct.get(
            "direct_target_event_count",
            0,
        )
        or 0
    )

    direct_not_target = (
        direct_hit_count > 0
        and direct_target_event_count == 0
    )

    # --------------------------------------------------------
    # 현행 UQ111
    # --------------------------------------------------------

    urban_positive = (
        get_nested(
            current,
            "current_state",
            "UQ111_urban_area",
            "positive_area_count",
            default=0,
        )
        or 0
    )

    current_urban_confirmed = (
        urban_positive > 0
    )

    # --------------------------------------------------------
    # 현행 UQ141
    # --------------------------------------------------------

    greenbelt_positive = (
        get_nested(
            current,
            "current_state",
            "UQ141_greenbelt",
            "positive_area_count",
            default=0,
        )
        or 0
    )

    current_greenbelt_absent = (
        greenbelt_positive == 0
    )

    # --------------------------------------------------------
    # 1989 계보
    # --------------------------------------------------------

    old_daechi_hits = (
        get_nested(
            initial,
            "search",
            "pre_1997_project_hit_count",
            default=0,
        )
        or 0
    )

    historic_chain_confirmed = (
        old_daechi_hits > 0
    )

    missing_content_notices = (
        chain.get(
            "missing_content_count",
            0,
        )
        or 0
    )

    chain_has_missing_content = (
        missing_content_notices > 0
    )

    # --------------------------------------------------------
    # 건설부 123호
    # --------------------------------------------------------

    notice_123_hits = (
        notice_123.get(
            "notice_123_hit_count",
            0,
        )
        or 0
    )

    notice_123_identified = (
        notice_123_hits > 0
    )

    # --------------------------------------------------------
    # 실시계획 534
    # --------------------------------------------------------

    notice_534_matches = (
        notice_534.get(
            "match_count",
            0,
        )
        or 0
    )

    notice_534_found = (
        notice_534_matches > 0
    )

    # --------------------------------------------------------
    # 국가기록원
    # --------------------------------------------------------

    archive_candidate_count = (
        archive.get(
            "candidate_count",
            0,
        )
        or 0
    )

    archive_public_count = (
        archive.get(
            "public_count",
            0,
        )
        or 0
    )

    archive_original_unverified = (
        archive.get(
            "original_unverified_count",
            0,
        )
        or 0
    )

    archive_candidates_confirmed = (
        archive_candidate_count > 0
    )

    archive_original_pending = (
        archive_original_unverified > 0
    )

    return {
        "announcement_query_success": (
            announcement_success
        ),

        "announcement_total_count": (
            announcement_total
        ),

        "combined_candidate_count": (
            combined_count
        ),

        "combined_target_candidate_count": (
            target_candidate_count
        ),

        "combined_unresolved_count": (
            unresolved_count
        ),

        "all_combined_candidates_classified_non_target": (
            all_combined_classified
        ),

        "direct_notice_hit_count": (
            direct_hit_count
        ),

        "direct_target_event_count": (
            direct_target_event_count
        ),

        "direct_notice_is_not_target_history": (
            direct_not_target
        ),

        "current_UQ111_positive_area_count": (
            urban_positive
        ),

        "current_urban_area_confirmed": (
            current_urban_confirmed
        ),

        "current_UQ141_positive_area_count": (
            greenbelt_positive
        ),

        "current_greenbelt_absent": (
            current_greenbelt_absent
        ),

        "historic_daechi_notice_chain_confirmed": (
            historic_chain_confirmed
        ),

        "historic_missing_content_notice_count": (
            missing_content_notices
        ),

        "historic_chain_has_missing_content": (
            chain_has_missing_content
        ),

        "notice_123_identified": (
            notice_123_identified
        ),

        "notice_534_found": (
            notice_534_found
        ),

        "national_archive_candidate_count": (
            archive_candidate_count
        ),

        "national_archive_public_count": (
            archive_public_count
        ),

        "national_archive_original_unverified_count": (
            archive_original_unverified
        ),

        "national_archive_candidates_confirmed": (
            archive_candidates_confirmed
        ),

        "national_archive_original_pending": (
            archive_original_pending
        ),
    }


# ============================================================
# 핵심 evidence 목록
# ============================================================

def build_evidence_summary(
    checks: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return [
        {
            "type": (
                "OFFICIAL_NOTICE_DATABASE"
            ),

            "source": (
                "서울특별시 도시계획 결정고시 "
                "upisAnnouncement"
            ),

            "result": (
                "QUERY_SUCCESS"
            ),

            "detail": (
                f"전체 결정고시 "
                f"{checks['announcement_total_count']:,}건 "
                f"조회"
            ),
        },

        {
            "type": (
                "NOTICE_FILTER"
            ),

            "source": (
                "서울특별시 결정고시"
            ),

            "result": (
                "NO_TARGET_HISTORY_CANDIDATE"
            ),

            "detail": (
                f"SITE 관련 편입/해제 결합 후보 "
                f"{checks['combined_candidate_count']}건 중 "
                f"target history "
                f"{checks['combined_target_candidate_count']}건, "
                f"미분류 "
                f"{checks['combined_unresolved_count']}건"
            ),
        },

        {
            "type": (
                "DIRECT_NOTICE"
            ),

            "source": (
                "개포동 12번지 직접 일치 결정고시"
            ),

            "result": (
                "NOT_TARGET_HISTORY"
            ),

            "detail": (
                "2010년 대치택지개발지구 "
                "지구단위계획 변경고시로 확인"
            ),
        },

        {
            "type": (
                "CURRENT_GEOMETRY"
            ),

            "source": (
                "서울시 UQ111 도시지역"
            ),

            "result": (
                "INTERSECTS"
            ),

            "detail": (
                "대상 Parcel과 현재 도시지역 "
                f"positive-area intersection "
                f"{checks['current_UQ111_positive_area_count']}건"
            ),
        },

        {
            "type": (
                "CURRENT_GEOMETRY"
            ),

            "source": (
                "서울시 UQ141 개발제한구역"
            ),

            "result": (
                "NO_INTERSECTION"
            ),

            "detail": (
                "대상 Parcel과 현재 개발제한구역 "
                "면적교차 0건"
            ),
        },

        {
            "type": (
                "HISTORIC_NOTICE_CHAIN"
            ),

            "source": (
                "1989 대치택지개발 고시 chain"
            ),

            "result": (
                "PARTIALLY_VERIFIED"
            ),

            "detail": (
                "건설부 제123호 및 제608호, "
                "서울시 제534호 계보 확인. "
                "일부 최초 고시 본문 누락"
            ),
        },

        {
            "type": (
                "NATIONAL_ARCHIVE"
            ),

            "source": (
                "국가기록원 DA0138776"
            ),

            "result": (
                "SOURCE_CONFIRMED_CONTENT_PENDING"
            ),

            "detail": (
                f"관련 기록 후보 "
                f"{checks['national_archive_candidate_count']}건, "
                f"공개 "
                f"{checks['national_archive_public_count']}건, "
                f"원문 상태 UNVERIFIED "
                f"{checks['national_archive_original_unverified_count']}건"
            ),
        },
    ]


# ============================================================
# 판정
# ============================================================

def build_resolution(
    checks: Dict[str, Any],
) -> Dict[str, Any]:

    # --------------------------------------------------------
    # TRUE 조건
    #
    # 현재까지는 과거 실제 Parcel 적용범위 evidence 없음.
    # 따라서 TRUE로 갈 수 없다.
    # --------------------------------------------------------

    positive_history_geometry = False

    # --------------------------------------------------------
    # FALSE 조건
    #
    # 공식 과거 이력 source가 완전하지 않으므로
    # 전수 negative evidence만으로 FALSE 불가.
    # --------------------------------------------------------

    historic_source_complete = (
        checks[
            "announcement_query_success"
        ]
        and not checks[
            "historic_chain_has_missing_content"
        ]
        and not checks[
            "national_archive_original_pending"
        ]
    )

    if positive_history_geometry:

        return {
            "status": "TRUE",
            "confidence": "HIGH",
        }

    if (
        historic_source_complete
        and checks[
            "all_combined_candidates_classified_non_target"
        ]
    ):

        return {
            "status": "FALSE",
            "confidence": "HIGH",
        }

    # --------------------------------------------------------
    # 현재 실제 상태
    # --------------------------------------------------------

    return {
        "status": "UNKNOWN",
        "confidence": "MEDIUM",
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    site = load_site()

    evidence = (
        load_all_evidence()
    )

    checks = build_checks(
        evidence
    )

    evidence_summary = (
        build_evidence_summary(
            checks
        )
    )

    resolution = (
        build_resolution(
            checks
        )
    )

    # --------------------------------------------------------
    # 최종 reason
    # --------------------------------------------------------

    reason = (
        "서울시 공식 도시계획 결정고시 전체 DB를 정상 조회하고 "
        "SITE 관련 편입/해제 후보를 검토했으나 "
        "개발제한구역·시가화조정구역·녹지지역·공원 해제 또는 "
        "도시지역 신규 편입에 해당하는 직접 고시는 확인되지 않았다. "
        "현재 대상 Parcel은 서울시 UQ111 도시지역과 실제 교차하고 "
        "UQ141 개발제한구역과는 교차하지 않는다. "
        "그러나 1989년 대치택지개발 최초 지정 단계의 일부 공식 고시 "
        "본문이 누락되어 있고 국가기록원 원기록의 실제 내용도 "
        "아직 확인되지 않아 과거 편입/해제 부재를 완전히 입증할 수 없다. "
        "따라서 FALSE로 자동 변환하지 않고 UNKNOWN을 유지한다."
    )

    # ========================================================
    # GitHub snapshot 형식과 호환되는 condition object
    # ========================================================

    condition_object = {
        "name": (
            CONDITION_NAME
        ),

        "status": (
            resolution[
                "status"
            ]
        ),

        "confidence": (
            resolution[
                "confidence"
            ]
        ),

        "source_type": (
            "MULTI_SOURCE_HISTORY_EVIDENCE"
        ),

        "source_name": (
            "서울시 도시계획 결정고시 + "
            "서울시 UQ111/UQ141 + "
            "국가기록원 DA0138776"
        ),

        "reason": (
            reason
        ),

        "evidence": (
            evidence_summary
        ),

        "reference_mentions": [],

        "query_group": (
            "HISTORY"
        ),
    }

    # ========================================================
    # 별도 상세 package
    # ========================================================

    result = {
        "step": STEP_NAME,

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
            "문자열 출현만으로 TRUE 금지": True,

            "현재 상태만으로 과거 이력 FALSE 금지": True,

            "결정고시 검색 부재만으로 FALSE 금지": True,

            "누락된 원문 존재 시 FALSE 금지": True,

            "국가기록원 후보 원문 미확정 시 UNKNOWN 유지": True,

            "TRUE는 Parcel/history 적용범위 evidence 필요": True,
        },

        "pending_evidence": [
            {
                "source": (
                    "국가기록원 DA0138776"
                ),

                "ritem_no": (
                    "000000000005"
                ),

                "title": (
                    "개포택지개발 예정지구 "
                    "지정신청에 따른 보완사항 보고"
                ),
            },

            {
                "source": (
                    "국가기록원 DA0138776"
                ),

                "ritem_no": (
                    "000000000007"
                ),

                "title": (
                    "개포 택지개발예정지구 "
                    "지정신청에 따른 보완"
                ),
            },
        ],

        "next_resolution_trigger": (
            "과거 공식 원문 또는 당시 공간도면에서 "
            "대상 Parcel이 개발제한구역·시가화조정구역·"
            "녹지지역·공원 해제 또는 도시지역 신규 편입 "
            "범위에 포함됐는지 확인될 경우 재판정"
        ),
    }

    save_json(
        result
    )

    # ========================================================
    # 초간략 콘솔
    # ========================================================

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
        "Target notice candidates:",
        checks[
            "combined_target_candidate_count"
        ],
    )

    print(
        "Current urban area:",
        checks[
            "current_urban_area_confirmed"
        ],
    )

    print(
        "Current greenbelt:",
        (
            not checks[
                "current_greenbelt_absent"
            ]
        ),
    )

    print(
        "Historic missing content:",
        checks[
            "historic_chain_has_missing_content"
        ],
    )

    print(
        "Archive candidates:",
        checks[
            "national_archive_candidate_count"
        ],
    )

    print(
        "Archive original pending:",
        checks[
            "national_archive_original_pending"
        ],
    )

    print(
        "resolution:",
        condition_object[
            "status"
        ],
    )

    print(
        "confidence:",
        condition_object[
            "confidence"
        ],
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