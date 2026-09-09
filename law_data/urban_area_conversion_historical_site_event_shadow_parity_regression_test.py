from __future__ import annotations

from law_data.urban_area_conversion_historical_site_event_shadow_adapter import (
    adapt_urban_area_conversion_history_shadow,
)


CLASSIFICATION = "URBAN_AREA_CONVERSION_HISTORICAL_SITE_EVENT_SHADOW_PARITY_PASS"


def _current_unknown_checks() -> dict:
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
        "national_archive_original_unverified_count": 1,
    }


def main() -> int:
    current = adapt_urban_area_conversion_history_shadow(
        {"checks": _current_unknown_checks()}
    )
    current_generalized = current["generalized_resolution"]

    positive_checks = _current_unknown_checks()
    positive_checks["combined_target_candidate_count"] = 1
    positive = adapt_urban_area_conversion_history_shadow({"checks": positive_checks})

    originals_resolved_checks = _current_unknown_checks()
    originals_resolved_checks["historic_chain_has_missing_content"] = False
    originals_resolved_checks["historic_missing_content_notice_count"] = 0
    originals_resolved_checks["national_archive_original_pending"] = False
    originals_resolved_checks["national_archive_original_unverified_count"] = 0
    originals_resolved = adapt_urban_area_conversion_history_shadow(
        {"checks": originals_resolved_checks}
    )

    weak_negative_checks = _current_unknown_checks()
    weak_negative_checks["announcement_total_count"] = 1
    weak_negative = adapt_urban_area_conversion_history_shadow(
        {"checks": weak_negative_checks}
    )

    validations = {
        "current legacy UNKNOWN boundary shadows to UNKNOWN": (
            current_generalized["resolution"] == "UNKNOWN"
        ),
        "current unresolved originals are preserved": (
            current["shadow_diagnostics"]["unresolved_historical_source_present"]
            is True
        ),
        "current official database negative is diagnostic only": (
            current["shadow_diagnostics"]["official_database_negative"] is True
            and current_generalized["evidence_state"][
                "history_scope_complete_verified"
            ]
            is False
        ),
        "legacy positive candidate is not promoted to verified event": (
            positive["shadow_diagnostics"]["positive_candidate_present"] is True
            and positive["generalized_resolution"]["evidence_state"][
                "verified_qualifying_event_present"
            ]
            is False
            and positive["generalized_resolution"]["resolution"] == "UNKNOWN"
        ),
        "resolving originals alone cannot manufacture FALSE": (
            originals_resolved["shadow_diagnostics"][
                "unresolved_historical_source_present"
            ]
            is False
            and originals_resolved["generalized_resolution"]["evidence_state"][
                "history_scope_complete_verified"
            ]
            is False
            and originals_resolved["generalized_resolution"]["resolution"]
            == "UNKNOWN"
        ),
        "weak database negative cannot manufacture completeness": (
            weak_negative["shadow_diagnostics"]["official_database_negative"]
            is False
            and weak_negative["generalized_resolution"]["resolution"] == "UNKNOWN"
        ),
        "shadow adapter never opens generic negative inference": (
            current_generalized["generic_negative_inference_allowed"] is False
            and current_generalized[
                "legal_absence_inference_from_discovery_allowed"
            ]
            is False
        ),
        "shadow adapter never auto-promotes TRUE": (
            current_generalized["automatic_true_promotion_allowed"] is False
        ),
        "promotion guards remain closed": (
            current["promotion_guards"][
                "legacy_positive_candidate_promoted_to_verified_event"
            ]
            is False
            and current["promotion_guards"][
                "official_database_negative_promoted_to_global_history_completeness"
            ]
            is False
        ),
        "shadow path remains production-unwired": (
            current["production_wiring_applied"] is False
            and current["overlay_mutated"] is False
            and current["runtime_registry_mutated"] is False
            and current_generalized["production_wiring_applied"] is False
            and current_generalized["runtime_registry_mutated"] is False
        ),
    }

    print("=" * 72)
    print("URBAN AREA CONVERSION HISTORICAL SITE EVENT SHADOW PARITY")
    print("=" * 72)
    for name, passed in validations.items():
        print(f"{name}: {passed}")

    all_pass = all(validations.values())
    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(f"CLASSIFICATION: {CLASSIFICATION if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
