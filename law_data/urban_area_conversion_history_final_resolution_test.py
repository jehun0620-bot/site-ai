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
공식 DB negative와 원문 해소만으로 global history completeness를 추정하지 않는다.
FALSE는 별도 history-scope completeness verifier가 도입되기 전까지 열지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-3B-7 "
    "도시지역편입해제구역 final evidence resolution"
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
PREVIOUS_PATH = OUTPUT_DIR / "urban_area_conversion_history_resolution.json"
RULE_PATH = OUTPUT_DIR / "site_rule_evaluation_school_overlay.json"
OUTPUT_PATH = OUTPUT_DIR / "urban_area_conversion_history_final_resolution.json"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"입력 파일 없음: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def first_dict(data: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, dict):
            return value
    return {}


def resolve_final_state(checks: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve the condition without inferring global historical completeness.

    Existing discovery/database negatives and resolved originals are not enough to
    establish that the complete historical universe has been searched. Until a
    dedicated completeness verifier supplies positive proof, FALSE remains closed.
    """

    announcement_ok = bool(checks.get("announcement_query_success", False))
    announcement_rows = safe_int(checks.get("announcement_total_count"))
    target_candidates = safe_int(checks.get("combined_target_candidate_count"))
    unresolved_candidates = safe_int(checks.get("combined_unresolved_count"))
    all_candidates_classified = bool(
        checks.get("all_combined_candidates_classified_non_target", False)
    )
    direct_target_events = safe_int(checks.get("direct_target_event_count"))
    direct_not_target = bool(
        checks.get("direct_notice_is_not_target_history", False)
    )

    historic_missing = bool(checks.get("historic_chain_has_missing_content", False))
    missing_content_count = safe_int(
        checks.get("historic_missing_content_notice_count")
    )
    archive_pending = bool(checks.get("national_archive_original_pending", False))
    archive_unverified = safe_int(
        checks.get("national_archive_original_unverified_count")
    )

    official_database_negative = (
        announcement_ok
        and announcement_rows >= 40000
        and target_candidates == 0
        and unresolved_candidates == 0
        and all_candidates_classified
        and direct_target_events == 0
        and direct_not_target
    )

    unresolved_historic_source = (
        historic_missing
        or missing_content_count > 0
        or archive_pending
        or archive_unverified > 0
    )

    positive_history_evidence = target_candidates > 0 or direct_target_events > 0

    # No current producer field proves global historical scope completeness.
    # Do not derive this from DB success, row count, no-hit, candidate exhaustion,
    # or the mere resolution of previously missing originals.
    history_scope_complete_verified = False

    exhaustive_disproof_verified = (
        official_database_negative
        and not unresolved_historic_source
        and history_scope_complete_verified
    )

    if positive_history_evidence:
        status = "TRUE_CANDIDATE"
        confidence = "MEDIUM"
        automation_state = "SOURCE_REVIEW_REQUIRED"
        overlay_action = "HOLD_FOR_REVIEW"
        reason = (
            "도시지역 편입ㆍ해제에 해당할 가능성이 있는 직접 historical evidence가 "
            "존재하므로 원문 확인 후 판정 필요"
        )
    elif official_database_negative and unresolved_historic_source:
        status = "UNKNOWN"
        confidence = "MEDIUM"
        automation_state = "HISTORICAL_SOURCE_PENDING"
        overlay_action = "KEEP_UNKNOWN"
        reason = (
            "서울시 공식 결정고시 전체 DB와 직접 SITE 고시에서는 도시지역 편입ㆍ해제 "
            "target history가 확인되지 않았다. 그러나 과거 원문 미구축 또는 원문 "
            "UNVERIFIED 상태가 남아 있어 negative 검색 결과만으로 FALSE를 확정하지 않고 "
            "UNKNOWN을 유지한다."
        )
    elif exhaustive_disproof_verified:
        status = "FALSE"
        confidence = "HIGH"
        automation_state = "RESOLVED"
        overlay_action = "APPLY_FALSE"
        reason = (
            "공식 historical source, global history scope completeness, required originals, "
            "candidate universe exhaustive classification이 모두 검증되어 target history가 "
            "없음이 입증됨"
        )
    elif official_database_negative and not unresolved_historic_source:
        status = "UNKNOWN"
        confidence = "MEDIUM"
        automation_state = "HISTORY_COMPLETENESS_PENDING"
        overlay_action = "KEEP_UNKNOWN"
        reason = (
            "확인되지 않았던 historical 원문은 해소되었지만 공식 DB negative와 원문 해소만으로 "
            "전체 historical universe의 completeness를 입증할 수 없다. 별도 history-scope "
            "completeness verifier가 없으므로 FALSE로 승격하지 않고 UNKNOWN을 유지한다."
        )
    else:
        status = "UNKNOWN"
        confidence = "NONE"
        automation_state = "INSUFFICIENT_EVIDENCE"
        overlay_action = "KEEP_UNKNOWN"
        reason = "도시지역 편입ㆍ해제 이력 판정을 위한 통합 evidence 검증조건 미충족"

    return {
        "official_database_negative": official_database_negative,
        "unresolved_historic_source": unresolved_historic_source,
        "positive_history_evidence": positive_history_evidence,
        "history_scope_complete_verified": history_scope_complete_verified,
        "exhaustive_disproof_verified": exhaustive_disproof_verified,
        "status": status,
        "confidence": confidence,
        "automation_state": automation_state,
        "overlay_action": overlay_action,
        "reason": reason,
    }


def main() -> int:
    previous = load_json(PREVIOUS_PATH)
    rules = load_json(RULE_PATH)

    checks = first_dict(previous, "checks", "evidence_checks", "verification")
    if not checks:
        summary = previous.get("summary", {})
        if isinstance(summary, dict):
            checks = first_dict(summary, "checks", "evidence_checks")

    announcement_ok = bool(checks.get("announcement_query_success", False))
    announcement_rows = safe_int(checks.get("announcement_total_count"))
    combined_count = safe_int(checks.get("combined_candidate_count"))
    target_candidates = safe_int(checks.get("combined_target_candidate_count"))
    unresolved_candidates = safe_int(checks.get("combined_unresolved_count"))
    all_candidates_classified = bool(
        checks.get("all_combined_candidates_classified_non_target", False)
    )
    direct_hits = safe_int(checks.get("direct_notice_hit_count"))
    direct_target_events = safe_int(checks.get("direct_target_event_count"))
    direct_not_target = bool(
        checks.get("direct_notice_is_not_target_history", False)
    )
    urban_positive = safe_int(checks.get("current_UQ111_positive_area_count"))
    current_urban = bool(checks.get("current_urban_area_confirmed", False))
    greenbelt_positive = safe_int(checks.get("current_UQ141_positive_area_count"))
    current_greenbelt_absent = bool(checks.get("current_greenbelt_absent", False))
    historic_chain = bool(checks.get("historic_daechi_notice_chain_confirmed", False))
    missing_content_count = safe_int(
        checks.get("historic_missing_content_notice_count")
    )
    historic_missing = bool(checks.get("historic_chain_has_missing_content", False))
    notice_123_identified = bool(checks.get("notice_123_identified", False))
    notice_534_found = bool(checks.get("notice_534_found", False))
    archive_candidates = safe_int(checks.get("national_archive_candidate_count"))
    archive_public = safe_int(checks.get("national_archive_public_count"))
    archive_unverified = safe_int(
        checks.get("national_archive_original_unverified_count")
    )
    archive_candidates_confirmed = bool(
        checks.get("national_archive_candidates_confirmed", False)
    )
    archive_pending = bool(checks.get("national_archive_original_pending", False))

    previous_resolution = first_dict(
        previous,
        "resolution",
        "current_resolution",
        "condition_result",
    )
    previous_status = (
        previous_resolution.get("status") or previous_resolution.get("resolution")
    )
    previous_confidence = previous_resolution.get("confidence")

    unresolved_site = (
        rules.get("input_requirements", {}).get("unresolved_site_conditions", [])
    )
    entry = next(
        (
            item
            for item in unresolved_site
            if item.get("name") == "도시지역편입해제구역"
        ),
        None,
    )
    affected_clause_count = safe_int(entry.get("affected_clause_count")) if entry else 0

    final_state = resolve_final_state(checks)
    official_database_negative = final_state["official_database_negative"]
    unresolved_historic_source = final_state["unresolved_historic_source"]
    positive_history_evidence = final_state["positive_history_evidence"]
    history_scope_complete_verified = final_state[
        "history_scope_complete_verified"
    ]
    exhaustive_disproof_verified = final_state["exhaustive_disproof_verified"]
    status = final_state["status"]
    confidence = final_state["confidence"]
    automation_state = final_state["automation_state"]
    overlay_action = final_state["overlay_action"]
    reason = final_state["reason"]

    current_state_known = current_urban and current_greenbelt_absent

    validations = {
        "previous checks loaded": bool(checks),
        "announcement DB OK": announcement_ok,
        "announcement rows 43508": announcement_rows == 43508,
        "combined candidates 존재": combined_count > 0,
        "target candidates 0": target_candidates == 0,
        "combined unresolved 0": unresolved_candidates == 0,
        "combined 전부 non-target 분류": all_candidates_classified,
        "direct notice 존재": direct_hits > 0,
        "direct target history 0": direct_target_events == 0,
        "direct notice non-target": direct_not_target,
        "current urban TRUE": current_urban,
        "UQ111 positive": urban_positive > 0,
        "current greenbelt absent": current_greenbelt_absent,
        "UQ141 positive 0": greenbelt_positive == 0,
        "historic chain 확인": historic_chain,
        "historic missing content 존재": unresolved_historic_source,
        "archive candidates 존재": archive_candidates_confirmed and archive_candidates > 0,
        "archive original pending": archive_pending,
        "history scope completeness not inferred": history_scope_complete_verified is False,
        "exhaustive disproof not inferred": exhaustive_disproof_verified is False,
        "affected clauses 3": affected_clause_count == 3,
        "status UNKNOWN": status == "UNKNOWN",
        "confidence MEDIUM": confidence == "MEDIUM",
        "automation historical pending": automation_state == "HISTORICAL_SOURCE_PENDING",
        "overlay KEEP_UNKNOWN": overlay_action == "KEEP_UNKNOWN",
    }
    all_pass = all(validations.values())

    output = {
        "step": STEP_NAME,
        "condition": {
            "name": "도시지역편입해제구역",
            "type": "SITE_HISTORY",
        },
        "previous_resolution": {
            "status": previous_status,
            "confidence": previous_confidence,
        },
        "evidence": {
            "announcement": {
                "query_success": announcement_ok,
                "total_rows": announcement_rows,
            },
            "combined_notice": {
                "candidate_count": combined_count,
                "target_candidate_count": target_candidates,
                "unresolved_count": unresolved_candidates,
                "all_non_target": all_candidates_classified,
            },
            "direct_notice": {
                "hit_count": direct_hits,
                "target_event_count": direct_target_events,
                "not_target_history": direct_not_target,
            },
            "current_state": {
                "urban_positive_area_count": urban_positive,
                "urban_area": current_urban,
                "greenbelt_positive_area_count": greenbelt_positive,
                "greenbelt_absent": current_greenbelt_absent,
            },
            "historic_chain": {
                "confirmed": historic_chain,
                "missing_content_count": missing_content_count,
                "has_missing_content": historic_missing,
                "notice_123_identified": notice_123_identified,
                "notice_534_found": notice_534_found,
            },
            "national_archive": {
                "candidate_count": archive_candidates,
                "public_count": archive_public,
                "original_unverified_count": archive_unverified,
                "candidates_confirmed": archive_candidates_confirmed,
                "original_pending": archive_pending,
            },
        },
        "evidence_summary": {
            "official_database_negative": official_database_negative,
            "current_state_known": current_state_known,
            "positive_history_evidence": positive_history_evidence,
            "unresolved_historic_source": unresolved_historic_source,
            "history_scope_complete_verified": history_scope_complete_verified,
            "exhaustive_disproof_verified": exhaustive_disproof_verified,
        },
        "affected_clause_count": affected_clause_count,
        "current_resolution": {
            "status": status,
            "confidence": confidence,
            "automation_state": automation_state,
            "reason": reason,
        },
        "overlay_policy": {
            "action": overlay_action,
            "rule": (
                "historical source 원문과 global history scope completeness가 모두 "
                "positive verification 되기 전에는 negative DB 검색만으로 FALSE 처리하지 않는다."
            ),
        },
        "validations": validations,
        "all_pass": all_pass,
    }

    save_json(output)

    print("Announcement DB:", "OK" if announcement_ok else "FAIL")
    print("Rows:", announcement_rows)
    print("Combined:", combined_count)
    print("Target candidates:", target_candidates)
    print("Unresolved candidates:", unresolved_candidates)
    print()
    print("Direct notices:", direct_hits)
    print("Direct target history:", direct_target_events)
    print()
    print("Current urban:", current_urban)
    print("Current greenbelt:", not current_greenbelt_absent)
    print()
    print("Historic missing content:", unresolved_historic_source)
    print("Archive candidates:", archive_candidates)
    print("Archive pending:", archive_pending)
    print("History scope complete verified:", history_scope_complete_verified)
    print("Exhaustive disproof verified:", exhaustive_disproof_verified)
    print()
    print("Affected clauses:", affected_clause_count)
    print()
    print("도시지역편입해제구역:", status, "/", confidence)
    print("Automation:", automation_state)
    print("Overlay:", overlay_action)
    print()
    print("all_pass:", all_pass)
    print("OUTPUT:", OUTPUT_PATH)

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
