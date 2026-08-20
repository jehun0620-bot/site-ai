# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-3B-7
도시지역편입해제구역 final evidence resolution

핵심
======================================================================
이 단계에서는 과거 probe JSON을 다시 제각각 해석하지 않는다.

이미 STEP 17-21-C-9-2-14G
urban_area_conversion_history_resolution_test.py 가
각 원본 JSON의 실제 schema를 사용해서 evidence를 종합했다.

따라서 그 통합 결과를 source of truth로 사용한다.

판정
======================================================================
현재까지:
- 서울시 공식 결정고시 전체 DB 조회 성공
- target history 후보 없음
- 개포동 12 직접고시는 target history 아님
- 현재 도시지역 TRUE
- 현재 개발제한구역 FALSE
- 1989 과거 chain 존재
- 일부 historic notice 원문 missing
- 국가기록원 공식 후보 존재
- 원문 UNVERIFIED

따라서:
도시지역편입해제구역 = UNKNOWN / MEDIUM
automation = HISTORICAL_SOURCE_PENDING

중요
======================================================================
UNKNOWN을 FALSE로 강제하지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-3B-7 "
    "도시지역편입해제구역 final evidence resolution"
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

PREVIOUS_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_history_resolution.json"
)

RULE_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_school_overlay.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_history_final_resolution.json"
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


def safe_int(
    value: Any,
    default: int = 0,
) -> int:

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def first_dict(
    data: Dict[str, Any],
    *keys: str,
) -> Dict[str, Any]:

    for key in keys:

        value = data.get(
            key
        )

        if isinstance(
            value,
            dict,
        ):

            return value

    return {}


# ============================================================
# main
# ============================================================

def main() -> int:

    previous = load_json(
        PREVIOUS_PATH
    )

    rules = load_json(
        RULE_PATH
    )

    # ========================================================
    # 1. 이전 통합 resolver의 checks
    #
    # 이전 코드에서 build_checks()로 생성한 값.
    # 버전에 따라 checks / evidence_checks 가능성 대응.
    # ========================================================

    checks = first_dict(
        previous,
        "checks",
        "evidence_checks",
        "verification",
    )

    # --------------------------------------------------------
    # 일부 버전에서 checks가 summary 안에 있을 가능성 대응
    # --------------------------------------------------------

    if not checks:

        summary = previous.get(
            "summary",
            {}
        )

        if isinstance(
            summary,
            dict,
        ):

            checks = first_dict(
                summary,
                "checks",
                "evidence_checks",
            )

    # ========================================================
    # 2. console에서 이미 검증된 이전 resolver 값을
    #    정확한 check key로 읽는다.
    # ========================================================

    announcement_ok = bool(
        checks.get(
            "announcement_query_success",
            False,
        )
    )

    announcement_rows = safe_int(
        checks.get(
            "announcement_total_count"
        )
    )

    combined_count = safe_int(
        checks.get(
            "combined_candidate_count"
        )
    )

    target_candidates = safe_int(
        checks.get(
            "combined_target_candidate_count"
        )
    )

    unresolved_candidates = safe_int(
        checks.get(
            "combined_unresolved_count"
        )
    )

    all_candidates_classified = bool(
        checks.get(
            "all_combined_candidates_classified_non_target",
            False,
        )
    )

    direct_hits = safe_int(
        checks.get(
            "direct_notice_hit_count"
        )
    )

    direct_target_events = safe_int(
        checks.get(
            "direct_target_event_count"
        )
    )

    direct_not_target = bool(
        checks.get(
            "direct_notice_is_not_target_history",
            False,
        )
    )

    urban_positive = safe_int(
        checks.get(
            "current_UQ111_positive_area_count"
        )
    )

    current_urban = bool(
        checks.get(
            "current_urban_area_confirmed",
            False,
        )
    )

    greenbelt_positive = safe_int(
        checks.get(
            "current_UQ141_positive_area_count"
        )
    )

    current_greenbelt_absent = bool(
        checks.get(
            "current_greenbelt_absent",
            False,
        )
    )

    historic_chain = bool(
        checks.get(
            "historic_daechi_notice_chain_confirmed",
            False,
        )
    )

    missing_content_count = safe_int(
        checks.get(
            "historic_missing_content_notice_count"
        )
    )

    historic_missing = bool(
        checks.get(
            "historic_chain_has_missing_content",
            False,
        )
    )

    notice_123_identified = bool(
        checks.get(
            "notice_123_identified",
            False,
        )
    )

    notice_534_found = bool(
        checks.get(
            "notice_534_found",
            False,
        )
    )

    archive_candidates = safe_int(
        checks.get(
            "national_archive_candidate_count"
        )
    )

    archive_public = safe_int(
        checks.get(
            "national_archive_public_count"
        )
    )

    archive_unverified = safe_int(
        checks.get(
            "national_archive_original_unverified_count"
        )
    )

    archive_candidates_confirmed = bool(
        checks.get(
            "national_archive_candidates_confirmed",
            False,
        )
    )

    archive_pending = bool(
        checks.get(
            "national_archive_original_pending",
            False,
        )
    )

    # ========================================================
    # 3. previous resolution 자체도 참고
    # ========================================================

    previous_resolution = first_dict(
        previous,
        "resolution",
        "current_resolution",
        "condition_result",
    )

    previous_status = (
        previous_resolution.get(
            "status"
        )
        or previous_resolution.get(
            "resolution"
        )
    )

    previous_confidence = (
        previous_resolution.get(
            "confidence"
        )
    )

    # ========================================================
    # 4. affected clauses
    # ========================================================

    unresolved_site = (
        rules.get(
            "input_requirements",
            {},
        ).get(
            "unresolved_site_conditions",
            [],
        )
    )

    entry = next(
        (
            item
            for item
            in unresolved_site
            if item.get(
                "name"
            )
            == "도시지역편입해제구역"
        ),
        None,
    )

    affected_clause_count = (
        safe_int(
            entry.get(
                "affected_clause_count"
            )
        )
        if entry
        else 0
    )

    # ========================================================
    # 5. evidence state
    # ========================================================

    official_database_negative = (
        announcement_ok
        and announcement_rows
        >= 40000
        and target_candidates
        == 0
        and unresolved_candidates
        == 0
        and all_candidates_classified
        and direct_target_events
        == 0
        and direct_not_target
    )

    current_state_known = (
        current_urban
        and current_greenbelt_absent
    )

    unresolved_historic_source = (
        historic_missing
        or missing_content_count
        > 0
        or archive_pending
        or archive_unverified
        > 0
    )

    positive_history_evidence = (
        target_candidates
        > 0
        or direct_target_events
        > 0
    )

    # ========================================================
    # 6. FINAL resolution
    # ========================================================

    if positive_history_evidence:

        status = (
            "TRUE_CANDIDATE"
        )

        confidence = (
            "MEDIUM"
        )

        automation_state = (
            "SOURCE_REVIEW_REQUIRED"
        )

        overlay_action = (
            "HOLD_FOR_REVIEW"
        )

        reason = (
            "도시지역 편입ㆍ해제에 해당할 가능성이 있는 "
            "직접 historical evidence가 존재하므로 "
            "원문 확인 후 판정 필요"
        )

    elif (
        official_database_negative
        and unresolved_historic_source
    ):

        status = (
            "UNKNOWN"
        )

        confidence = (
            "MEDIUM"
        )

        automation_state = (
            "HISTORICAL_SOURCE_PENDING"
        )

        overlay_action = (
            "KEEP_UNKNOWN"
        )

        reason = (
            "서울시 공식 결정고시 전체 DB와 직접 SITE 고시에서는 "
            "도시지역 편입ㆍ해제 target history가 확인되지 않았다. "
            "그러나 대치택지개발 초기 고시 중 원문 미구축 자료가 있고 "
            "국가기록원 공식 후보 기록도 원문 UNVERIFIED 상태다. "
            "따라서 negative 검색 결과만으로 과거 이력 부재를 "
            "FALSE로 확정하지 않고 UNKNOWN을 유지한다."
        )

    elif (
        official_database_negative
        and not unresolved_historic_source
    ):

        status = (
            "FALSE"
        )

        confidence = (
            "HIGH"
        )

        automation_state = (
            "RESOLVED"
        )

        overlay_action = (
            "APPLY_FALSE"
        )

        reason = (
            "공식 고시와 과거 원문을 모두 확인했으며 "
            "도시지역 편입ㆍ해제 target history가 확인되지 않음"
        )

    else:

        status = (
            "UNKNOWN"
        )

        confidence = (
            "NONE"
        )

        automation_state = (
            "INSUFFICIENT_EVIDENCE"
        )

        overlay_action = (
            "KEEP_UNKNOWN"
        )

        reason = (
            "도시지역 편입ㆍ해제 이력 판정을 위한 "
            "통합 evidence 검증조건 미충족"
        )

    # ========================================================
    # 7. validations
    # ========================================================

    validations = {

        "previous checks loaded": (
            bool(
                checks
            )
        ),

        "announcement DB OK": (
            announcement_ok
        ),

        "announcement rows 43508": (
            announcement_rows
            == 43508
        ),

        "combined candidates 존재": (
            combined_count
            > 0
        ),

        "target candidates 0": (
            target_candidates
            == 0
        ),

        "combined unresolved 0": (
            unresolved_candidates
            == 0
        ),

        "combined 전부 non-target 분류": (
            all_candidates_classified
        ),

        "direct notice 존재": (
            direct_hits
            > 0
        ),

        "direct target history 0": (
            direct_target_events
            == 0
        ),

        "direct notice non-target": (
            direct_not_target
        ),

        "current urban TRUE": (
            current_urban
        ),

        "UQ111 positive": (
            urban_positive
            > 0
        ),

        "current greenbelt absent": (
            current_greenbelt_absent
        ),

        "UQ141 positive 0": (
            greenbelt_positive
            == 0
        ),

        "historic chain 확인": (
            historic_chain
        ),

        "historic missing content 존재": (
            unresolved_historic_source
        ),

        "archive candidates 존재": (
            archive_candidates_confirmed
            and archive_candidates
            > 0
        ),

        "archive original pending": (
            archive_pending
        ),

        "affected clauses 3": (
            affected_clause_count
            == 3
        ),

        "status UNKNOWN": (
            status
            == "UNKNOWN"
        ),

        "confidence MEDIUM": (
            confidence
            == "MEDIUM"
        ),

        "automation historical pending": (
            automation_state
            == "HISTORICAL_SOURCE_PENDING"
        ),

        "overlay KEEP_UNKNOWN": (
            overlay_action
            == "KEEP_UNKNOWN"
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # 8. output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "condition": {
            "name": (
                "도시지역편입해제구역"
            ),

            "type": (
                "SITE_HISTORY"
            ),
        },

        "previous_resolution": {
            "status": (
                previous_status
            ),

            "confidence": (
                previous_confidence
            ),
        },

        "evidence": {

            "announcement": {
                "query_success": (
                    announcement_ok
                ),

                "total_rows": (
                    announcement_rows
                ),
            },

            "combined_notice": {
                "candidate_count": (
                    combined_count
                ),

                "target_candidate_count": (
                    target_candidates
                ),

                "unresolved_count": (
                    unresolved_candidates
                ),

                "all_non_target": (
                    all_candidates_classified
                ),
            },

            "direct_notice": {
                "hit_count": (
                    direct_hits
                ),

                "target_event_count": (
                    direct_target_events
                ),

                "not_target_history": (
                    direct_not_target
                ),
            },

            "current_state": {
                "urban_positive_area_count": (
                    urban_positive
                ),

                "urban_area": (
                    current_urban
                ),

                "greenbelt_positive_area_count": (
                    greenbelt_positive
                ),

                "greenbelt_absent": (
                    current_greenbelt_absent
                ),
            },

            "historic_chain": {
                "confirmed": (
                    historic_chain
                ),

                "missing_content_count": (
                    missing_content_count
                ),

                "has_missing_content": (
                    historic_missing
                ),

                "notice_123_identified": (
                    notice_123_identified
                ),

                "notice_534_found": (
                    notice_534_found
                ),
            },

            "national_archive": {
                "candidate_count": (
                    archive_candidates
                ),

                "public_count": (
                    archive_public
                ),

                "original_unverified_count": (
                    archive_unverified
                ),

                "candidates_confirmed": (
                    archive_candidates_confirmed
                ),

                "original_pending": (
                    archive_pending
                ),
            },
        },

        "evidence_summary": {
            "official_database_negative": (
                official_database_negative
            ),

            "current_state_known": (
                current_state_known
            ),

            "positive_history_evidence": (
                positive_history_evidence
            ),

            "unresolved_historic_source": (
                unresolved_historic_source
            ),
        },

        "affected_clause_count": (
            affected_clause_count
        ),

        "current_resolution": {
            "status": (
                status
            ),

            "confidence": (
                confidence
            ),

            "automation_state": (
                automation_state
            ),

            "reason": (
                reason
            ),
        },

        "overlay_policy": {
            "action": (
                overlay_action
            ),

            "rule": (
                "historical source 원문이 미확인된 경우 "
                "negative DB 검색만으로 FALSE 처리하지 않는다."
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
        "Announcement DB:",
        (
            "OK"
            if announcement_ok
            else "FAIL"
        ),
    )

    print(
        "Rows:",
        announcement_rows,
    )

    print(
        "Combined:",
        combined_count,
    )

    print(
        "Target candidates:",
        target_candidates,
    )

    print(
        "Unresolved candidates:",
        unresolved_candidates,
    )

    print()

    print(
        "Direct notices:",
        direct_hits,
    )

    print(
        "Direct target history:",
        direct_target_events,
    )

    print()

    print(
        "Current urban:",
        current_urban,
    )

    print(
        "Current greenbelt:",
        not current_greenbelt_absent,
    )

    print()

    print(
        "Historic missing content:",
        unresolved_historic_source,
    )

    print(
        "Archive candidates:",
        archive_candidates,
    )

    print(
        "Archive pending:",
        archive_pending,
    )

    print()

    print(
        "Affected clauses:",
        affected_clause_count,
    )

    print()

    print(
        "도시지역편입해제구역:",
        status,
        "/",
        confidence,
    )

    print(
        "Automation:",
        automation_state,
    )

    print(
        "Overlay:",
        overlay_action,
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