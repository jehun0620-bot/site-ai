from __future__ import annotations

import sys
from pathlib import Path


LAW_DATA_DIR = Path(__file__).resolve().parent
if str(LAW_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(LAW_DATA_DIR))

from historical_site_event_resolver import (  # noqa: E402
    FALSE,
    UNKNOWN,
    HistoricalSiteEventEvidenceState,
    resolve_historical_site_event,
)
from urban_area_conversion_historical_site_event_shadow_adapter import (  # noqa: E402
    adapt_urban_area_conversion_history_shadow,
)


def legacy_resolution_from_checks(checks: dict[str, object]) -> str:
    announcement_ok = bool(checks.get("announcement_query_success", False))
    announcement_rows = int(checks.get("announcement_total_count", 0) or 0)
    target_candidates = int(checks.get("combined_target_candidate_count", 0) or 0)
    unresolved_candidates = int(checks.get("combined_unresolved_count", 0) or 0)
    all_candidates_classified = bool(
        checks.get("all_combined_candidates_classified_non_target", False)
    )
    direct_target_events = int(checks.get("direct_target_event_count", 0) or 0)
    direct_not_target = bool(
        checks.get("direct_notice_is_not_target_history", False)
    )

    historic_missing = bool(checks.get("historic_chain_has_missing_content", False))
    missing_content_count = int(
        checks.get("historic_missing_content_notice_count", 0) or 0
    )
    archive_pending = bool(checks.get("national_archive_original_pending", False))
    archive_unverified = int(
        checks.get("national_archive_original_unverified_count", 0) or 0
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

    if positive_history_evidence:
        return "TRUE_CANDIDATE"
    if official_database_negative and unresolved_historic_source:
        return UNKNOWN
    if official_database_negative and not unresolved_historic_source:
        return FALSE
    return UNKNOWN


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
        "current_urban_area_confirmed": True,
        "current_greenbelt_absent": True,
        "historic_chain_has_missing_content": True,
        "historic_missing_content_notice_count": 1,
        "national_archive_original_pending": True,
        "national_archive_original_unverified_count": 2,
    }


def generalized_shadow_resolution(checks: dict[str, object]) -> dict[str, object]:
    return adapt_urban_area_conversion_history_shadow({"checks": checks})


def main() -> int:
    current = current_like_checks()
    current_legacy = legacy_resolution_from_checks(current)
    current_shadow = generalized_shadow_resolution(current)

    originals_resolved = dict(current)
    originals_resolved.update(
        {
            "historic_chain_has_missing_content": False,
            "historic_missing_content_notice_count": 0,
            "national_archive_original_pending": False,
            "national_archive_original_unverified_count": 0,
        }
    )
    originals_legacy = legacy_resolution_from_checks(originals_resolved)
    originals_shadow = generalized_shadow_resolution(originals_resolved)

    db_negative_only = {
        "announcement_query_success": True,
        "announcement_total_count": 43508,
        "combined_candidate_count": 8,
        "combined_target_candidate_count": 0,
        "combined_unresolved_count": 0,
        "all_combined_candidates_classified_non_target": True,
        "direct_target_event_count": 0,
        "direct_notice_is_not_target_history": True,
    }
    db_negative_shadow = generalized_shadow_resolution(db_negative_only)

    generalized_complete_negative = resolve_historical_site_event(
        HistoricalSiteEventEvidenceState(
            verified_qualifying_event_present=False,
            official_history_source_verified=True,
            history_scope_complete_verified=True,
            required_originals_resolved=True,
            candidate_universe_exhaustively_enumerated=True,
            all_candidates_classified_non_target=True,
            unresolved_historical_source_present=False,
        )
    )

    positive_candidate = dict(current)
    positive_candidate["combined_target_candidate_count"] = 1
    positive_shadow = generalized_shadow_resolution(positive_candidate)

    checks = {
        "current unresolved state is UNKNOWN in legacy": current_legacy == UNKNOWN,
        "current unresolved state is UNKNOWN in generalized shadow": (
            current_shadow["generalized_resolution"]["resolution"] == UNKNOWN
        ),
        "resolving originals opens legacy FALSE": originals_legacy == FALSE,
        "resolving originals alone remains UNKNOWN in generalized shadow": (
            originals_shadow["generalized_resolution"]["resolution"] == UNKNOWN
        ),
        "legacy database negative is not global completeness": (
            originals_shadow["generalized_resolution"]["evidence_state"][
                "history_scope_complete_verified"
            ]
            is False
        ),
        "database negative alone remains UNKNOWN in generalized shadow": (
            db_negative_shadow["generalized_resolution"]["resolution"] == UNKNOWN
        ),
        "generalized FALSE requires explicit exhaustive disproof": (
            generalized_complete_negative["resolution"] == FALSE
            and generalized_complete_negative["exhaustive_disproof_verified"] is True
        ),
        "positive legacy candidate is not promoted to verified event": (
            positive_shadow["shadow_diagnostics"]["positive_candidate_present"] is True
            and positive_shadow["generalized_resolution"]["evidence_state"][
                "verified_qualifying_event_present"
            ]
            is False
            and positive_shadow["generalized_resolution"]["resolution"] == UNKNOWN
        ),
        "generalized path keeps generic negative inference disabled": all(
            result["generalized_resolution"]["generic_negative_inference_allowed"]
            is False
            for result in (
                current_shadow,
                originals_shadow,
                db_negative_shadow,
                positive_shadow,
            )
        ),
        "divergence regression remains production-unwired": all(
            result["production_wiring_applied"] is False
            and result["overlay_mutated"] is False
            and result["runtime_registry_mutated"] is False
            for result in (
                current_shadow,
                originals_shadow,
                db_negative_shadow,
                positive_shadow,
            )
        ),
    }

    all_pass = all(checks.values())

    print("=" * 72)
    print("URBAN AREA CONVERSION HISTORICAL FALSE GATE DIVERGENCE")
    print("=" * 72)
    for name, passed in checks.items():
        print(f"{name}: {passed}")
    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        + (
            "URBAN_AREA_CONVERSION_HISTORICAL_FALSE_GATE_DIVERGENCE_PASS"
            if all_pass
            else "URBAN_AREA_CONVERSION_HISTORICAL_FALSE_GATE_DIVERGENCE_FAIL"
        )
    )

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
