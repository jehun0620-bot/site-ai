from __future__ import annotations

from law_data.urban_area_conversion_history_completeness_adapter import (
    adapt_urban_area_conversion_history_completeness,
)


def _payload(*, originals_resolved: bool = False) -> dict:
    return {
        "checks": {
            "announcement_query_success": True,
            "announcement_total_count": 43508,
            "combined_target_candidate_count": 0,
            "combined_unresolved_count": 0,
            "all_combined_candidates_classified_non_target": True,
            "direct_target_event_count": 0,
            "direct_notice_is_not_target_history": True,
            "historic_chain_has_missing_content": not originals_resolved,
            "historic_missing_content_notice_count": 0 if originals_resolved else 1,
            "national_archive_original_pending": not originals_resolved,
            "national_archive_original_unverified_count": 0 if originals_resolved else 10,
        }
    }


def main() -> int:
    print("=" * 72)
    print("URBAN AREA CONVERSION HISTORY COMPLETENESS ADAPTER")
    print("=" * 72)

    current = adapt_urban_area_conversion_history_completeness(_payload())
    current_v = current["completeness_verification"]
    current_d = current["condition_diagnostics"]
    current_g = current["promotion_guards"]

    resolved = adapt_urban_area_conversion_history_completeness(
        _payload(originals_resolved=True)
    )
    resolved_v = resolved["completeness_verification"]
    resolved_d = resolved["condition_diagnostics"]

    empty = adapt_urban_area_conversion_history_completeness({})
    empty_v = empty["completeness_verification"]

    checks = {
        "current actual-like state remains incomplete": (
            current_v["history_scope_complete_verified"] is False
            and current_v["positive_gate_count"] == 0
        ),
        "official DB success is not complete official source set": (
            current_d["announcement_query_success"] is True
            and current_v["official_historical_source_set_verified"] is False
            and current_g[
                "announcement_query_success_promoted_to_official_source_set"
            ] is False
        ),
        "DB-negative is diagnostic only for global universe": (
            current_d["official_database_negative"] is True
            and current_v["candidate_universe_exhaustively_enumerated"] is False
            and current_g[
                "official_database_negative_promoted_to_global_candidate_universe"
            ] is False
        ),
        "row count does not verify authority time scope": (
            current_d["announcement_total_count"] == 43508
            and current_v["authority_time_scope_completeness_verified"] is False
            and current_g[
                "row_count_promoted_to_authority_time_scope_completeness"
            ] is False
        ),
        "current unresolved originals remain unresolved": (
            current_d["unresolved_historical_source_present"] is True
            and current_d["required_original_documents_resolved"] is False
            and current_v["required_original_documents_resolved"] is False
        ),
        "resolving originals maps only the originals gate": (
            resolved_d["unresolved_historical_source_present"] is False
            and resolved_v["required_original_documents_resolved"] is True
            and resolved_v["positive_gate_count"] == 1
        ),
        "resolving originals alone cannot manufacture completeness": (
            resolved_v["official_historical_source_set_verified"] is False
            and resolved_v["authority_time_scope_completeness_verified"] is False
            and resolved_v["candidate_universe_exhaustively_enumerated"] is False
            and resolved_v["history_scope_complete_verified"] is False
        ),
        "missing payload fails closed": (
            empty_v["positive_gate_count"] == 1
            and empty_v["history_scope_complete_verified"] is False
        ),
        "negative and legal absence inference stay disabled": (
            current_v["generic_negative_inference_allowed"] is False
            and current_v["legal_absence_inference_from_discovery_allowed"] is False
        ),
        "adapter remains read-only and production-unwired": (
            current["output_written"] is False
            and current["production_wiring_applied"] is False
            and current["overlay_mutated"] is False
            and current["runtime_registry_mutated"] is False
        ),
    }

    for label, passed in checks.items():
        print(f"{label}: {passed}")

    all_pass = all(checks.values())
    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        "URBAN_AREA_CONVERSION_HISTORY_COMPLETENESS_ADAPTER_"
        + ("PASS" if all_pass else "FAIL")
    )

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
