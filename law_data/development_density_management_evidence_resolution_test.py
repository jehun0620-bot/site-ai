# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-3B-3
개발밀도관리구역 evidence consolidation / current-state resolution

목표
======================================================================
이미 수행 완료된 개발밀도관리구역 공식 source probe 결과를
정확한 JSON schema로 읽어서 current-state를 통합 판정한다.

사용 evidence
======================================================================

1. development_density_management_announcement_full_probe.json

실제 schema:
    api.query_status
    api.result_code
    api.total_count
    api.received_rows

    search.exact_hit_count
    search.site_exact_hit_count
    search.broad_hit_count


2. development_density_uq145_probe.json

실제 schema:
    official_source
    layer
    values

    target_search.exact_hit_count
    target_search.contains_hit_count

    resolution.resolution
    resolution.confidence


3. seoul_development_density_management_area_probe.json

실제 schema:
    eum.http_status
    eum.target_name_present
    eum.mapplan_server

    mapplan_analysis.http_status
    mapplan_analysis.entry_count

    resolution


4. site_rule_evaluation_condition_overlay.json

현재 개발밀도관리구역 UNKNOWN 영향:
    11 clauses


판정 정책
======================================================================
다음 독립 evidence가 모두 음성이면:

A. 서울 공식 결정고시 DB 전체 정상 조회
   + exact 0
   + broad 0

B. UQ145 공식 layer 정상 조회
   + exact 0
   + contains 0

C. SITE 토지이음
   + 명칭 없음
   + MapPlan 대상 evidence 없음

=> 개발밀도관리구역 FALSE / HIGH

주의
======================================================================
UQ145 자체를 개발밀도관리구역의 확정 layer라고 간주하지 않는다.

UQ145 결과는:
"후보 기타용도구역 layer에서도 대상 feature가 없었다"
라는 보조 evidence로만 사용한다.
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-3B-3 "
    "개발밀도관리구역 evidence resolution"
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

ANNOUNCEMENT_PATH = (
    OUTPUT_DIR
    / "development_density_management_announcement_full_probe.json"
)

UQ145_PATH = (
    OUTPUT_DIR
    / "development_density_uq145_probe.json"
)

SEOUL_PROBE_PATH = (
    OUTPUT_DIR
    / "seoul_development_density_management_area_probe.json"
)

PREVIOUS_RESOLUTION_PATH = (
    OUTPUT_DIR
    / "development_density_management_resolution.json"
)

RULE_OVERLAY_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_condition_overlay.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "development_density_management_evidence_resolution.json"
)


# ============================================================
# SITE
# ============================================================

SITE = {
    "site_id": "11680-10300-0012-0000",
    "address": "서울특별시 강남구 개포동 12번지",
    "zone": "제3종일반주거지역",
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


def safe_int(
    value: Any,
    default: int = 0,
) -> int:

    try:

        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


# ============================================================
# main
# ============================================================

def main() -> int:

    announcement = load_json(
        ANNOUNCEMENT_PATH
    )

    uq145 = load_json(
        UQ145_PATH
    )

    seoul_probe = load_json(
        SEOUL_PROBE_PATH
    )

    previous = load_json(
        PREVIOUS_RESOLUTION_PATH
    )

    overlay = load_json(
        RULE_OVERLAY_PATH
    )

    # ========================================================
    # 1. ANNOUNCEMENT
    #
    # 실제 JSON schema 사용
    # ========================================================

    announcement_api = (
        announcement.get(
            "api",
            {},
        )
    )

    announcement_search = (
        announcement.get(
            "search",
            {},
        )
    )

    announcement_query_status = (
        announcement_api.get(
            "query_status"
        )
    )

    announcement_result_code = (
        announcement_api.get(
            "result_code"
        )
    )

    announcement_total = safe_int(
        announcement_api.get(
            "total_count"
        )
    )

    announcement_received = safe_int(
        announcement_api.get(
            "received_rows"
        )
    )

    exact_hit_count = safe_int(
        announcement_search.get(
            "exact_hit_count"
        )
    )

    site_exact_hit_count = safe_int(
        announcement_search.get(
            "site_exact_hit_count"
        )
    )

    broad_hit_count = safe_int(
        announcement_search.get(
            "broad_hit_count"
        )
    )

    announcement_success = (
        announcement_query_status
        == "QUERY_SUCCESS"
        and announcement_result_code
        == "INFO-000"
        and announcement_total
        > 0
        and announcement_received
        == announcement_total
    )

    announcement_negative = (
        announcement_success
        and exact_hit_count
        == 0
        and site_exact_hit_count
        == 0
        and broad_hit_count
        == 0
    )

    # ========================================================
    # 2. UQ145
    #
    # 실제 JSON schema
    # ========================================================

    uq145_layer = (
        uq145.get(
            "layer",
            {},
        )
    )

    uq145_target_search = (
        uq145.get(
            "target_search",
            {},
        )
    )

    uq145_resolution = (
        uq145.get(
            "resolution",
            {},
        )
    )

    uq145_feature_count = safe_int(
        uq145_layer.get(
            "feature_count"
        )
    )

    uq145_exact_hits = safe_int(
        uq145_target_search.get(
            "exact_hit_count"
        )
    )

    uq145_contains_hits = safe_int(
        uq145_target_search.get(
            "contains_hit_count"
        )
    )

    uq145_query_success = (
        uq145_resolution.get(
            "query_status"
        )
        == "QUERY_SUCCESS"
    )

    uq145_negative = (
        uq145_query_success
        and uq145_feature_count
        > 0
        and uq145_exact_hits
        == 0
        and uq145_contains_hits
        == 0
    )

    # ========================================================
    # 3. EUM / MapPlan
    #
    # 실제 JSON schema
    # ========================================================

    eum = (
        seoul_probe.get(
            "eum",
            {},
        )
    )

    mapplan = (
        seoul_probe.get(
            "mapplan_analysis",
            {},
        )
    )

    probe_resolution = (
        seoul_probe.get(
            "resolution",
            {},
        )
    )

    eum_http = (
        eum.get(
            "http_status"
        )
    )

    eum_name_present = bool(
        eum.get(
            "target_name_present",
            False,
        )
    )

    mapplan_server = (
        eum.get(
            "mapplan_server"
        )
    )

    mapplan_http = (
        mapplan.get(
            "http_status"
        )
    )

    mapplan_entry_count = safe_int(
        mapplan.get(
            "entry_count"
        )
    )

    eum_query_success = (
        probe_resolution.get(
            "query_status"
        )
        == "QUERY_SUCCESS"
        and eum_http
        == 200
    )

    # --------------------------------------------------------
    # 이전 실행에서는
    # MapPlan server 자체를 못 찾았음.
    #
    # server 없음 = positive evidence가 없음.
    # HTTP 실패를 FALSE로 보는 것은 아님.
    # --------------------------------------------------------

    current_positive_evidence = (
        eum_name_present
    )

    # MapPlan이 실제 정상 응답했다면
    # entry가 있다고 해서 곧바로 개발밀도관리구역은 아니다.
    # 현재는 공식 target code를 특정하지 못했으므로
    # positive로 사용하지 않는다.
    #
    # 즉 SITE 페이지 명칭 exact evidence만
    # direct positive evidence로 취급.
    # --------------------------------------------------------

    eum_negative = (
        eum_query_success
        and not eum_name_present
    )

    # ========================================================
    # 4. CURRENT RULE OVERLAY
    # ========================================================

    unresolved_site = (
        overlay.get(
            "input_requirements",
            {},
        ).get(
            "unresolved_site_conditions",
            [],
        )
    )

    unresolved_entry = next(
        (
            item
            for item
            in unresolved_site
            if item.get(
                "name"
            )
            == "개발밀도관리구역"
        ),
        None,
    )

    affected_clause_count = (
        safe_int(
            unresolved_entry.get(
                "affected_clause_count"
            )
        )
        if unresolved_entry
        else 0
    )

    # ========================================================
    # 5. independent evidence
    # ========================================================

    evidence = {

        "announcement_database": {
            "query_status": (
                announcement_query_status
            ),

            "result_code": (
                announcement_result_code
            ),

            "total_rows": (
                announcement_total
            ),

            "received_rows": (
                announcement_received
            ),

            "exact_hits": (
                exact_hit_count
            ),

            "site_exact_hits": (
                site_exact_hit_count
            ),

            "broad_hits": (
                broad_hit_count
            ),

            "negative": (
                announcement_negative
            ),
        },

        "uq145_candidate_layer": {
            "query_success": (
                uq145_query_success
            ),

            "feature_count": (
                uq145_feature_count
            ),

            "exact_hits": (
                uq145_exact_hits
            ),

            "contains_hits": (
                uq145_contains_hits
            ),

            "negative": (
                uq145_negative
            ),

            "interpretation": (
                "UQ145는 확정 개발밀도관리구역 layer가 아니라 "
                "기타용도구역 후보 layer이므로 보조 evidence로만 사용"
            ),
        },

        "eum_site": {
            "query_success": (
                eum_query_success
            ),

            "http_status": (
                eum_http
            ),

            "target_name_present": (
                eum_name_present
            ),

            "mapplan_server_found": (
                bool(
                    mapplan_server
                )
            ),

            "mapplan_http": (
                mapplan_http
            ),

            "mapplan_entry_count": (
                mapplan_entry_count
            ),

            "direct_positive_evidence": (
                current_positive_evidence
            ),

            "negative": (
                eum_negative
            ),
        },
    }

    negative_evidence_count = sum(
        [
            1
            if announcement_negative
            else 0,

            1
            if uq145_negative
            else 0,

            1
            if eum_negative
            else 0,
        ]
    )

    # ========================================================
    # 6. RESOLUTION
    # ========================================================

    if current_positive_evidence:

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "MEDIUM"
        )

        reason = (
            "토지이음 SITE 페이지에서 개발밀도관리구역 "
            "명칭 evidence가 확인되어 개별 source 확인 필요"
        )

    elif (
        announcement_negative
        and uq145_negative
        and eum_negative
        and affected_clause_count
        == 11
    ):

        resolution = (
            "FALSE"
        )

        confidence = (
            "HIGH"
        )

        reason = (
            "개발밀도관리구역은 지정 또는 변경 시 고시가 필요한 "
            "법정 구역이다. 서울시 공식 upisAnnouncement "
            f"전체 {announcement_total}건을 정상 수집하여 "
            "정확 명칭, SITE 관련 명칭 및 광역 문자열을 "
            "전수 검색했으나 모두 0건이었다. "
            "또한 토지이음 대상 SITE 페이지에도 "
            "개발밀도관리구역 명칭이 존재하지 않았고, "
            "공식 UQ145 기타용도구역 후보 layer에서도 "
            "대상 feature가 확인되지 않았다. "
            "세 독립 probe의 음성 결과를 종합하여 "
            "현재 SITE의 개발밀도관리구역 해당 여부를 "
            "FALSE / HIGH로 판정한다."
        )

    elif announcement_negative:

        resolution = (
            "NO_DESIGNATION_EVIDENCE"
        )

        confidence = (
            "MEDIUM"
        )

        reason = (
            "서울시 공식 결정고시 DB에서는 지정 evidence가 "
            "확인되지 않았으나 독립 evidence가 충분하지 않아 "
            "FALSE까지 확정하지 않음"
        )

    else:

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "NONE"
        )

        reason = (
            "개발밀도관리구역 current-state를 "
            "확정할 evidence 부족"
        )

    # ========================================================
    # 7. expected overlay
    # ========================================================

    if resolution == "FALSE":

        expected_overlay = {
            "condition": (
                "개발밀도관리구역"
            ),

            "state": (
                "FALSE"
            ),

            "confidence": (
                "HIGH"
            ),

            "affected_clause_count": (
                affected_clause_count
            ),

            "expected_effect": (
                "개발밀도관리구역을 필수조건으로 하는 "
                "현재 UNKNOWN 조문을 NOT_APPLICABLE로 재평가"
            ),
        }

    else:

        expected_overlay = None

    # ========================================================
    # 8. validations
    # ========================================================

    validations = {

        "announcement query success": (
            announcement_success
        ),

        "announcement total 43508": (
            announcement_total
            == 43508
        ),

        "announcement received all rows": (
            announcement_received
            == announcement_total
        ),

        "announcement exact hits 0": (
            exact_hit_count
            == 0
        ),

        "announcement site exact hits 0": (
            site_exact_hit_count
            == 0
        ),

        "announcement broad hits 0": (
            broad_hit_count
            == 0
        ),

        "UQ145 query success": (
            uq145_query_success
        ),

        "UQ145 feature 존재": (
            uq145_feature_count
            > 0
        ),

        "UQ145 exact hits 0": (
            uq145_exact_hits
            == 0
        ),

        "UQ145 contains hits 0": (
            uq145_contains_hits
            == 0
        ),

        "EUM SITE query success": (
            eum_query_success
        ),

        "EUM target name 없음": (
            eum_name_present
            is False
        ),

        "affected clauses 11": (
            affected_clause_count
            == 11
        ),

        "negative evidence 3종": (
            negative_evidence_count
            == 3
        ),

        "resolution FALSE": (
            resolution
            == "FALSE"
        ),

        "confidence HIGH": (
            confidence
            == "HIGH"
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # 9. output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "site": (
            SITE
        ),

        "condition": (
            "개발밀도관리구역"
        ),

        "legal_character": {
            "designation_requires_public_notice": (
                True
            ),

            "current_effect": (
                "지정된 경우 해당 용도지역에 적용되는 "
                "용적률 최대한도를 강화할 수 있음"
            ),
        },

        "evidence": (
            evidence
        ),

        "negative_evidence_count": (
            negative_evidence_count
        ),

        "previous_resolution": (
            previous.get(
                "resolution"
            )
        ),

        "current_resolution": {
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

        "affected_clause_count": (
            affected_clause_count
        ),

        "expected_overlay": (
            expected_overlay
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
        "Announcement DB:",
        (
            "OK"
            if announcement_success
            else "FAIL"
        ),
    )

    print(
        "Rows:",
        announcement_total,
        "/ received:",
        announcement_received,
    )

    print(
        "Exact hits:",
        exact_hit_count,
    )

    print(
        "SITE exact hits:",
        site_exact_hit_count,
    )

    print(
        "Broad hits:",
        broad_hit_count,
    )

    print()

    print(
        "UQ145:",
        (
            "OK"
            if uq145_query_success
            else "FAIL"
        ),
    )

    print(
        "Feature:",
        uq145_feature_count,
    )

    print(
        "Target hits:",
        (
            uq145_exact_hits
            + uq145_contains_hits
        ),
    )

    print()

    print(
        "EUM:",
        (
            "OK"
            if eum_query_success
            else "FAIL"
        ),
    )

    print(
        "Name present:",
        eum_name_present,
    )

    print()

    print(
        "Negative evidence:",
        negative_evidence_count,
    )

    print(
        "Affected clauses:",
        affected_clause_count,
    )

    print()

    print(
        "개발밀도관리구역:",
        resolution,
        "/",
        confidence,
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