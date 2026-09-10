from __future__ import annotations

from law_data.urban_area_conversion_historical_site_event_shadow_adapter import (
    adapt_urban_area_conversion_history_shadow,
)


def _payload(*, originals_resolved: bool) -> dict:
    return {
        "checks": {
            "announcement_query_success": True,
            "announcement_total_count": 43508,
            "combined_candidate_count": 8,
            "combined_target_candidate_count": 0,
            "combined_unresolved_count": 0,
            "all_combined_candidates_classified_non_target": True,
            "direct_target_event_count": 0,
            "direct_notice_is_not_target_history": True,
            "current_urban_area_confirmed": True,
            "current_greenbelt_absent": True,
            "historic_chain_has_missing_content": not originals_resolved,
            "historic_missing_content_notice_count": 0 if originals_resolved else 1,
            "national_archive_original_pending": not originals_resolved,
            "national_archive_original_unverified_count": 0 if originals_resolved else 1,
        }
    }


def main() -> None:
    current = adapt_urban_area_conversion_history_shadow(
        _payload(originals_resolved=False)
    )
    originals_resolved = adapt_urban_area_conversion_history_shadow(
        _payload(originals_resolved=True)
    )

    current_resolution = current["generalized_resolution"]
    current_evidence = current_resolution["evidence_state"]
    future_resolution = originals_resolved["generalized_resolution"]
    future_evidence = future_resolution["evidence_state"]
    diagnostics = originals_resolved["shadow_diagnostics"]
    guards = originals_resolved["promotion_guards"]

    checks = {
        "current actual-like state remains UNKNOWN": (
            current_resolution["resolution"] == "UNKNOWN"
        ),
        "official DB negative remains available as diagnostic": (
            diagnostics["official_database_negative"] is True
        ),
        "DB negative does not promote global candidate universe": (
            future_evidence["candidate_universe_exhaustively_enumerated"] is False
        ),
        "DB negative does not promote all candidates non-target gate": (
            future_evidence["all_candidates_classified_non_target"] is False
        ),
        "resolving originals maps only originals state": (
            future_evidence["required_originals_resolved"] is True
            and future_evidence["unresolved_historical_source_present"] is False
        ),
        "resolving originals still cannot open FALSE": (
            future_resolution["resolution"] == "UNKNOWN"
            and future_resolution["exhaustive_disproof_verified"] is False
        ),
        "history completeness remains unverified": (
            future_evidence["history_scope_complete_verified"] is False
        ),
        "announcement success is not complete source set promotion": (
            guards[
                "announcement_query_success_promoted_to_complete_source_set"
            ]
            is False
        ),
        "global candidate universe promotion guard is explicit": (
            guards[
                "official_database_negative_promoted_to_global_candidate_universe"
            ]
            is False
        ),
        "all-candidates non-target promotion guard is explicit": (
            guards[
                "official_database_negative_promoted_to_all_candidates_non_target"
            ]
            is False
        ),
        "negative and legal absence inference stay disabled": (
            future_resolution["generic_negative_inference_allowed"] is False
            and future_resolution[
                "legal_absence_inference_from_discovery_allowed"
            ]
            is False
        ),
        "shadow remains production-unwired": (
            originals_resolved["production_wiring_applied"] is False
            and originals_resolved["overlay_mutated"] is False
            and originals_resolved["runtime_registry_mutated"] is False
        ),
    }

    all_pass = all(checks.values())

    print("=" * 72)
    print("URBAN AREA CONVERSION HISTORICAL SHADOW SEMANTIC HARDENING")
    print("=" * 72)
    for label, passed in checks.items():
        print(f"{label}: {passed}")
    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        + (
            "URBAN_AREA_CONVERSION_HISTORICAL_SHADOW_SEMANTIC_HARDENING_PASS"
            if all_pass
            else "URBAN_AREA_CONVERSION_HISTORICAL_SHADOW_SEMANTIC_HARDENING_FAIL"
        )
    )

    if not all_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
