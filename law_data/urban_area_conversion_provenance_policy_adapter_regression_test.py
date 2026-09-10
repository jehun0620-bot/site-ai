from __future__ import annotations

from law_data.urban_area_conversion_provenance_policy_adapter import (
    ADAPTER_MODE,
    CONDITION_NAME,
    adapt_urban_area_conversion_provenance_policy,
)


def main() -> None:
    print("=" * 72)
    print("URBAN AREA CONVERSION PROVENANCE POLICY ADAPTER")
    print("=" * 72)

    diagnostic_payload = {
        "checks": {
            "announcement_query_success": True,
            "combined_candidate_count": 8,
            "combined_target_candidate_count": 0,
            "direct_notice_hit_count": 1,
            "direct_target_event_count": 0,
            "historic_daechi_notice_chain_confirmed": True,
            "notice_123_identified": True,
            "notice_534_found": True,
            "current_urban_area_confirmed": True,
            "current_greenbelt_absent": True,
            "national_archive_candidate_count": 10,
            "national_archive_candidates_confirmed": True,
            "national_archive_original_pending": True,
        }
    }

    result = adapt_urban_area_conversion_provenance_policy(diagnostic_payload)
    policy = result["provenance_policy"]
    gates = policy["gates"]

    checks = {
        "condition identity is preserved": result["condition"] == CONDITION_NAME,
        "adapter remains read-only and production-unwired": result["adapter_mode"] == ADAPTER_MODE,
        "diagnostic provenance does not verify authority identity": gates["source_authority_identity_verified"] is False,
        "diagnostic provenance does not verify source role": gates["source_role_explicit"] is False,
        "notice diagnostics do not verify document traceability": gates["document_identity_traceable"] is False,
        "archive diagnostics do not verify original traceability": gates["original_document_traceable"] is False,
        "current geometry diagnostics do not verify historical SITE traceability": gates["site_applicability_traceable"] is False,
        "document diagnostics do not verify temporal traceability": gates["temporal_relation_traceable"] is False,
        "all six provenance gates remain unverified": policy["verified_gate_count"] == 0,
        "six provenance gates remain required": policy["required_gate_count"] == 6,
        "condition provenance policy remains blocked": policy["provenance_policy_verified"] is False and policy["provenance_state"] == "BLOCKED",
        "all six gates are reported missing": len(policy["missing_gates"]) == 6,
        "diagnostic provenance distinction is explicit": result["semantic_contract"]["diagnostic_provenance_present_does_not_mean_gate_verified"] is True,
        "original diagnostics distinction is explicit": result["semantic_contract"]["original_diagnostics_do_not_mean_complete_production_provenance"] is True,
        "binding distinction is explicit": result["semantic_contract"]["policy_binding_does_not_mean_provenance_policy_verified"] is True,
        "provenance is not legal evidence": result["semantic_contract"]["provenance_policy_verified_does_not_mean_legal_evidence_verified"] is True,
        "candidate cannot manufacture provenance": result["promotion_guards"]["candidate_promoted_to_provenance"] is False,
        "notice identity cannot manufacture provenance": result["promotion_guards"]["notice_identity_promoted_to_provenance"] is False,
        "current geometry cannot manufacture historical SITE provenance": result["promotion_guards"]["current_geometry_promoted_to_historical_site_provenance"] is False,
        "archive candidate cannot manufacture original traceability": result["promotion_guards"]["archive_candidate_promoted_to_original_traceability"] is False,
        "provenance cannot manufacture legal resolution": result["promotion_guards"]["provenance_promoted_to_legal_resolution"] is False,
        "negative and legal absence inference remain disabled": policy["negative_evidence_inference_allowed"] is False and policy["legal_absence_inference_allowed"] is False,
        "adapter writes no output": result["output_written"] is False,
        "adapter performs no production wiring": result["production_wiring_applied"] is False,
        "adapter performs no overlay mutation": result["overlay_mutated"] is False,
        "adapter performs no runtime registry mutation": result["runtime_registry_mutated"] is False,
    }

    for label, passed in checks.items():
        print(f"{label}: {passed}")

    all_pass = all(checks.values())
    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        + (
            "URBAN_AREA_CONVERSION_PROVENANCE_POLICY_ADAPTER_PASS"
            if all_pass
            else "URBAN_AREA_CONVERSION_PROVENANCE_POLICY_ADAPTER_FAIL"
        )
    )

    if not all_pass:
        raise AssertionError("urban area conversion provenance policy adapter regression failed")


if __name__ == "__main__":
    main()
