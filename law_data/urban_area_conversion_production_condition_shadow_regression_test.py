from __future__ import annotations

import copy

from law_data.urban_area_conversion_production_condition_shadow_adapter import (
    adapt_urban_area_conversion_production_condition_shadow,
)


CLASSIFICATION = "STEP18_URBAN_AREA_CONVERSION_PRODUCTION_CONDITION_SHADOW_PASS"


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected={expected!r}, actual={actual!r}")


def assert_true(value, label: str) -> None:
    if value is not True:
        raise AssertionError(f"{label}: expected True, actual={value!r}")


def assert_false(value, label: str) -> None:
    if value is not False:
        raise AssertionError(f"{label}: expected False, actual={value!r}")


def current_semantics_payload() -> dict:
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
            "historic_chain_has_missing_content": True,
            "historic_missing_content_notice_count": 1,
            "national_archive_candidates_confirmed": True,
            "national_archive_candidate_count": 10,
            "national_archive_original_pending": True,
            "national_archive_original_unverified_count": 1,
            "notice_123_identified": True,
            "notice_534_found": True,
            "historic_daechi_notice_chain_confirmed": True,
        }
    }


def main() -> None:
    payload = current_semantics_payload()
    before = copy.deepcopy(payload)

    result = adapt_urban_area_conversion_production_condition_shadow(payload)
    condition = result["production_condition"]

    assert_equal(payload, before, "producer payload unchanged")
    assert_equal(result["condition"], "도시지역편입해제구역", "condition identity")
    assert_equal(
        result["adapter_mode"],
        "READ_ONLY_PRODUCTION_CONDITION_SHADOW",
        "adapter mode",
    )

    assert_equal(condition["name"], "도시지역편입해제구역", "contract name")
    assert_equal(condition["condition_type"], "SITE_HISTORY", "contract type")
    assert_equal(
        condition["resolution_type"],
        "HISTORICAL_SITE_EVENT",
        "contract resolution type",
    )
    assert_equal(condition["state"], "UNKNOWN", "current production state")
    assert_equal(condition["confidence"], "MEDIUM", "current confidence")

    assert_false(condition["production_eligible"], "production eligibility blocked")
    assert_false(condition["runtime_registered"], "runtime registration blocked")
    assert_false(condition["negative_evidence_allowed"], "negative evidence disabled")
    assert_false(
        condition["legal_absence_inference_allowed"],
        "legal absence inference disabled",
    )
    assert_false(condition["site_promotion_allowed"], "SITE promotion disabled")

    provenance = condition["provenance"]
    assert_false(provenance["standard_code_verified"], "standard code remains unverified")
    assert_false(
        provenance["provenance_policy_verified"],
        "provenance policy remains unverified",
    )
    assert_false(
        provenance["runtime_registration_policy_verified"],
        "runtime registration policy remains unverified",
    )
    assert_equal(
        provenance["resolver_resolution"],
        "UNKNOWN",
        "generalized resolver UNKNOWN preserved",
    )

    historical = result["historical_shadow"]
    assert_equal(
        historical["generalized_resolution"]["resolution"],
        "UNKNOWN",
        "historical generalized resolution",
    )
    assert_true(
        historical["shadow_diagnostics"]["official_database_negative"],
        "diagnostic database negative preserved",
    )
    assert_true(
        historical["shadow_diagnostics"]["unresolved_historical_source_present"],
        "unresolved historical source preserved",
    )
    assert_false(
        historical["promotion_guards"][
            "official_database_negative_promoted_to_global_history_completeness"
        ],
        "database negative not promoted to completeness",
    )

    readiness = result["production_readiness"]
    blockers = readiness["condition_specific_blockers"]
    assert_true(blockers["standard_code_unverified"], "standard code blocker")
    assert_true(blockers["provenance_policy_unverified"], "provenance blocker")
    assert_true(
        blockers["runtime_registration_policy_unverified"],
        "runtime registration blocker",
    )

    provenance_policy = result["provenance_policy"]["provenance_policy"]
    assert_false(
        provenance_policy["provenance_policy_verified"],
        "production provenance policy blocked",
    )

    runtime_policy = result["runtime_registration_policy"]
    assert_equal(runtime_policy["current_resolution"], "UNKNOWN", "runtime UNKNOWN")
    assert_false(
        runtime_policy["runtime_registration_policy"]["registration_eligible"],
        "runtime registration policy blocked",
    )
    assert_equal(
        runtime_policy["runtime_registration_policy"]["registration_state"],
        "BLOCKED",
        "runtime registration state blocked",
    )

    guards = result["promotion_guards"]
    assert_false(guards["true_candidate_promoted_to_true"], "TRUE promotion guard")
    assert_false(guards["unknown_promoted_to_false"], "UNKNOWN->FALSE guard")
    assert_false(guards["unknown_promoted_to_true"], "UNKNOWN->TRUE guard")
    assert_false(
        guards["readiness_promoted_to_production_eligibility"],
        "readiness promotion guard",
    )
    assert_false(
        guards["runtime_policy_promoted_to_actual_registration"],
        "runtime policy promotion guard",
    )
    assert_false(
        guards["condition_name_promoted_to_standard_code"],
        "standard-code guessing guard",
    )

    assert_false(result["output_written"], "output mutation blocked")
    assert_false(result["production_wiring_applied"], "production wiring blocked")
    assert_false(result["overlay_mutated"], "overlay mutation blocked")
    assert_false(result["runtime_registry_mutated"], "runtime registry mutation blocked")

    print("=" * 72)
    print("STEP 18 URBAN AREA CONVERSION PRODUCTION CONDITION SHADOW REGRESSION")
    print("=" * 72)
    print("Current historical resolution UNKNOWN: PASS")
    print("SITE_HISTORY/HISTORICAL_SITE_EVENT contract mapping: PASS")
    print("Standard-code/provenance/runtime blockers preserved: PASS")
    print("Production eligibility/runtime registration remain False: PASS")
    print("Negative/legal absence/SITE promotion remain disabled: PASS")
    print("Producer payload mutation: NONE")
    print("Output/production wiring/overlay/runtime mutation: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
