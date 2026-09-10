from __future__ import annotations

import sys
from pathlib import Path


LAW_DATA_DIR = Path(__file__).resolve().parent
if str(LAW_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(LAW_DATA_DIR))

from urban_area_conversion_history_final_resolution_test import (  # noqa: E402
    resolve_final_state,
)


def current_like_checks() -> dict[str, object]:
    return {
        "announcement_query_success": True,
        "announcement_total_count": 43508,
        "combined_candidate_count": 8,
        "combined_target_candidate_count": 0,
        "combined_unresolved_count": 0,
        "all_combined_candidates_classified_non_target": True,
        "direct_notice_hit_count": 1,
        "direct_target_event_count": 0,
        "direct_notice_is_not_target_history": True,
        "current_UQ111_positive_area_count": 1,
        "current_urban_area_confirmed": True,
        "current_UQ141_positive_area_count": 0,
        "current_greenbelt_absent": True,
        "historic_daechi_notice_chain_confirmed": True,
        "historic_chain_has_missing_content": True,
        "historic_missing_content_notice_count": 1,
        "national_archive_candidate_count": 2,
        "national_archive_candidates_confirmed": True,
        "national_archive_original_pending": True,
        "national_archive_original_unverified_count": 2,
    }


def main() -> int:
    current = resolve_final_state(current_like_checks())

    originals_resolved_checks = current_like_checks()
    originals_resolved_checks.update(
        {
            "historic_chain_has_missing_content": False,
            "historic_missing_content_notice_count": 0,
            "national_archive_original_pending": False,
            "national_archive_original_unverified_count": 0,
        }
    )
    originals_resolved = resolve_final_state(originals_resolved_checks)

    candidate_checks = current_like_checks()
    candidate_checks["combined_target_candidate_count"] = 1
    candidate = resolve_final_state(candidate_checks)

    direct_candidate_checks = current_like_checks()
    direct_candidate_checks["direct_target_event_count"] = 1
    direct_candidate = resolve_final_state(direct_candidate_checks)

    no_database_negative_checks = current_like_checks()
    no_database_negative_checks["announcement_query_success"] = False
    insufficient = resolve_final_state(no_database_negative_checks)

    checks = {
        "current actual-like state remains UNKNOWN": (
            current["status"] == "UNKNOWN"
            and current["confidence"] == "MEDIUM"
            and current["automation_state"] == "HISTORICAL_SOURCE_PENDING"
            and current["overlay_action"] == "KEEP_UNKNOWN"
        ),
        "current unresolved source remains explicit": (
            current["unresolved_historic_source"] is True
        ),
        "current history completeness is not inferred": (
            current["history_scope_complete_verified"] is False
            and current["exhaustive_disproof_verified"] is False
        ),
        "resolving originals alone remains UNKNOWN": (
            originals_resolved["status"] == "UNKNOWN"
            and originals_resolved["confidence"] == "MEDIUM"
            and originals_resolved["automation_state"]
            == "HISTORY_COMPLETENESS_PENDING"
            and originals_resolved["overlay_action"] == "KEEP_UNKNOWN"
        ),
        "resolved originals do not manufacture global completeness": (
            originals_resolved["unresolved_historic_source"] is False
            and originals_resolved["official_database_negative"] is True
            and originals_resolved["history_scope_complete_verified"] is False
            and originals_resolved["exhaustive_disproof_verified"] is False
        ),
        "target candidate remains diagnostic UNKNOWN": (
            candidate["positive_history_candidate_present"] is True
            and candidate["verified_qualifying_event_present"] is False
            and candidate["positive_history_evidence"] is False
            and candidate["status"] == "UNKNOWN"
            and candidate["automation_state"]
            == "POSITIVE_EVIDENCE_VERIFICATION_PENDING"
            and candidate["overlay_action"] == "KEEP_UNKNOWN"
        ),
        "direct target candidate remains diagnostic UNKNOWN": (
            direct_candidate["positive_history_candidate_present"] is True
            and direct_candidate["verified_qualifying_event_present"] is False
            and direct_candidate["status"] == "UNKNOWN"
            and direct_candidate["overlay_action"] == "KEEP_UNKNOWN"
        ),
        "candidate signals cannot manufacture TRUE_CANDIDATE": all(
            result["status"] != "TRUE_CANDIDATE"
            for result in (candidate, direct_candidate)
        ),
        "insufficient evidence remains fail-closed UNKNOWN": (
            insufficient["status"] == "UNKNOWN"
            and insufficient["overlay_action"] == "KEEP_UNKNOWN"
        ),
        "FALSE path remains closed without explicit completeness verifier": all(
            result["status"] != "FALSE"
            and result["overlay_action"] != "APPLY_FALSE"
            for result in (
                current,
                originals_resolved,
                candidate,
                direct_candidate,
                insufficient,
            )
        ),
    }

    all_pass = all(checks.values())

    print("=" * 72)
    print("URBAN AREA CONVERSION HISTORY FINAL RESOLUTION HARDENING")
    print("=" * 72)
    for name, passed in checks.items():
        print(f"{name}: {passed}")
    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        + (
            "URBAN_AREA_CONVERSION_HISTORY_FINAL_RESOLUTION_HARDENING_PASS"
            if all_pass
            else "URBAN_AREA_CONVERSION_HISTORY_FINAL_RESOLUTION_HARDENING_FAIL"
        )
    )

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
