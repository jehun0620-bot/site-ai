from __future__ import annotations

from law_data.urban_area_conversion_provenance_policy_adapter import (
    CONDITION_NAME,
    adapt_urban_area_conversion_provenance_policy,
)


CLASSIFICATION = (
    "STEP23_REGULATION_SOURCE_POLICY_REQUIREMENT_PROVENANCE_INTEGRATION_PASS"
)


def _diagnostic_payload() -> dict[str, object]:
    return {
        "checks": {
            "combined_candidate_count": 4,
            "direct_notice_hit_count": 2,
            "notice_123_identified": True,
            "notice_534_found": True,
            "historic_daechi_notice_chain_confirmed": True,
            "announcement_query_success": True,
            "national_archive_candidates_confirmed": True,
            "national_archive_candidate_count": 3,
            "source_uri": "https://example.go.kr/notice/123",
            "region_binding": "서울특별시",
            "source_role": "PRIMARY",
            "legal_authority_scope": "도시계획 고시",
            # Verification-looking diagnostics must not be promoted by the adapter.
            "official_host_verified": True,
            "region_binding_verified": True,
            "source_role_verified": True,
            "legal_authority_scope_verified": True,
            "target_regulation_compatible": True,
            "target_regulation_compatibility_verified": True,
            "history_completeness_verified": True,
            "provenance_verified": True,
            "source_policy_verified": True,
        }
    }


def test_historical_source_policy_binding_remains_fail_closed() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())

    assert result["condition"] == CONDITION_NAME

    profile = result["resolution_profile"]
    assert profile is not None
    assert profile["standard_code"] is None
    assert profile["standard_code_verified"] is False
    assert profile["source_policy_requirements"] == [
        "HISTORY COMPLETENESS VERIFIED",
        "PROVENANCE VERIFIED",
    ]
    assert profile["source_policy_verified"] is False

    policy = result["provenance_policy"]
    assert policy["provenance_policy_verified"] is False
    assert policy["provenance_state"] == "BLOCKED"

    assessment = result["regulation_source_policy_requirement"]
    assert assessment["profile_present"] is True
    assert assessment["source_policy_requirements_declared"] is True
    assert assessment["verified_requirements"] == []
    assert assessment["missing_requirements"] == [
        "HISTORY COMPLETENESS VERIFIED",
        "PROVENANCE VERIFIED",
    ]
    assert assessment["unexpected_requirements"] == []
    assert assessment["source_policy_requirement_satisfied"] is False


def test_diagnostic_verification_looking_fields_are_not_requirement_facts() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())

    scope = result["authority_source_scope"]
    assert scope["official_host_verified"] is False
    assert scope["region_binding_verified"] is False
    assert scope["source_role_verified"] is False
    assert scope["legal_authority_scope_verified"] is False
    assert scope["target_regulation_compatibility_verified"] is False
    assert scope["authority_chain_verified"] is False

    authority = result["regulation_authority_requirement"]
    assert authority["authority_requirement_satisfied"] is False

    source_policy = result["regulation_source_policy_requirement"]
    assert source_policy["source_policy_requirement_satisfied"] is False


def test_adapter_does_not_claim_history_completeness() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())

    semantic = result["semantic_contract"]
    blockers = result["condition_specific_blockers"]

    assert semantic["history_completeness_not_verified_by_this_adapter"] is True
    assert semantic["contract_readiness_does_not_supply_requirement_facts"] is True
    assert semantic["profile_source_policy_verified_does_not_supply_requirement_facts"] is True
    assert blockers["history_completeness_unverified"] is True
    assert blockers["source_policy_requirement_unsatisfied"] is True


def test_source_policy_binding_does_not_promote_legal_or_runtime_state() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())

    guards = result["promotion_guards"]
    policy = result["provenance_policy"]

    assert guards["source_policy_requirement_promoted_to_verified_evidence"] is False
    assert guards["source_policy_requirement_promoted_to_legal_resolution"] is False
    assert guards["contract_readiness_promoted_to_source_policy_verification"] is False
    assert policy["negative_evidence_inference_allowed"] is False
    assert policy["legal_absence_inference_allowed"] is False
    assert policy["site_promotion_applied"] is False
    assert result["output_written"] is False
    assert result["production_wiring_applied"] is False
    assert result["overlay_mutated"] is False
    assert result["runtime_registry_mutated"] is False


def test_uqq700_is_not_cross_wired_into_historical_adapter() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    rendered = repr(result)

    assert "UQQ700" not in rendered
    assert "개발밀도관리구역" not in rendered


def main() -> None:
    test_historical_source_policy_binding_remains_fail_closed()
    test_diagnostic_verification_looking_fields_are_not_requirement_facts()
    test_adapter_does_not_claim_history_completeness()
    test_source_policy_binding_does_not_promote_legal_or_runtime_state()
    test_uqq700_is_not_cross_wired_into_historical_adapter()

    print("=" * 86)
    print("STEP 23 REGULATION SOURCE POLICY REQUIREMENT -> HISTORICAL PROVENANCE INTEGRATION")
    print("=" * 86)
    print("Declared historical source-policy requirements: 2")
    print("Diagnostic verification-looking fields -> requirement facts: NONE")
    print("History completeness verified by provenance adapter: FALSE")
    print("Historical provenance state: BLOCKED")
    print("Source-policy requirement satisfied: FALSE")
    print("Historical standard code: ABSENT / UNVERIFIED")
    print("Negative/legal absence/SITE promotion: NONE")
    print("Production/runtime mutation: NONE")
    print("UQQ700 cross-condition wiring: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
