from __future__ import annotations

from law_data.urban_area_conversion_provenance_policy_adapter import (
    CONDITION_NAME,
    adapt_urban_area_conversion_provenance_policy,
)


CLASSIFICATION = "STEP20_AUTHORITY_SOURCE_SCOPE_PROVENANCE_INTEGRATION_PASS"


def _diagnostic_payload() -> dict[str, object]:
    return {
        "checks": {
            "combined_candidate_count": 2,
            "direct_notice_hit_count": 1,
            "notice_123_identified": True,
            "announcement_query_success": True,
            "national_archive_candidates_confirmed": True,
            "national_archive_candidate_count": 3,
            "source_url": "https://example.go.kr/notice/123",
            "region_binding": "서울특별시",
            "source_role": "PRIMARY",
            "legal_authority_scope": "도시계획 고시",
            # Even if diagnostic payloads carry verification-looking values, the
            # adapter must not import them into AuthoritySourceScope verification.
            "official_host_verified": True,
            "region_binding_verified": True,
            "source_role_verified": True,
            "legal_authority_scope_verified": True,
            "target_regulation_compatible": True,
            "target_regulation_compatibility_verified": True,
        }
    }


def test_descriptive_diagnostics_remain_unverified() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    scope = result["authority_source_scope"]

    assert result["condition"] == CONDITION_NAME
    assert scope["source_host"] == "example.go.kr"
    assert scope["region_binding"] == "서울특별시"
    assert scope["source_role"] == "PRIMARY"
    assert scope["legal_authority_scope"] == "도시계획 고시"
    assert scope["target_regulation"] == CONDITION_NAME

    assert scope["official_host_verified"] is False
    assert scope["region_binding_verified"] is False
    assert scope["source_role_verified"] is False
    assert scope["legal_authority_scope_verified"] is False
    assert scope["target_regulation_compatible"] is None
    assert scope["target_regulation_compatibility_verified"] is False
    assert scope["authority_chain_verified"] is False


def test_provenance_policy_remains_blocked() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    policy = result["provenance_policy"]
    gates = policy["gates"]

    assert gates["source_authority_identity_verified"] is False
    assert gates["source_role_explicit"] is False
    assert gates["document_identity_traceable"] is False
    assert gates["original_document_traceable"] is False
    assert gates["site_applicability_traceable"] is False
    assert gates["temporal_relation_traceable"] is False
    assert policy["provenance_policy_verified"] is False
    assert policy["provenance_state"] == "BLOCKED"


def test_diagnostic_hits_do_not_promote_authority_or_provenance() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    guards = result["promotion_guards"]
    policy_guards = result["provenance_policy"]["promotion_guards"]

    assert guards["candidate_promoted_to_provenance"] is False
    assert guards["notice_identity_promoted_to_provenance"] is False
    assert guards["official_host_promoted_to_competent_authority"] is False
    assert guards["source_role_metadata_promoted_to_verified_role"] is False
    assert guards["authority_metadata_promoted_to_legal_evidence"] is False
    assert guards["archive_candidate_promoted_to_original_traceability"] is False
    assert guards["provenance_promoted_to_legal_resolution"] is False

    assert policy_guards["candidate_promoted_to_authority_identity"] is False
    assert policy_guards["http_200_promoted_to_authority_identity"] is False
    assert policy_guards["source_url_promoted_to_source_role"] is False
    assert policy_guards["archive_candidate_promoted_to_original_traceability"] is False


def test_negative_and_runtime_mutation_guards_remain_closed() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    policy = result["provenance_policy"]

    assert policy["negative_evidence_inference_allowed"] is False
    assert policy["legal_absence_inference_allowed"] is False
    assert policy["site_promotion_applied"] is False
    assert policy["production_wiring_applied"] is False
    assert policy["overlay_mutated"] is False
    assert policy["runtime_registry_mutated"] is False

    assert result["output_written"] is False
    assert result["production_wiring_applied"] is False
    assert result["overlay_mutated"] is False
    assert result["runtime_registry_mutated"] is False


def test_empty_payload_fails_closed() -> None:
    result = adapt_urban_area_conversion_provenance_policy({})
    scope = result["authority_source_scope"]
    policy = result["provenance_policy"]

    assert scope["source_uri"] is None
    assert scope["source_host"] is None
    assert scope["authority_chain_verified"] is False
    assert policy["provenance_policy_verified"] is False
    assert policy["provenance_state"] == "BLOCKED"


def test_no_uqq700_cross_condition_wiring() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    rendered = repr(result)

    assert result["condition"] == "도시지역편입해제구역"
    assert result["authority_source_scope"]["target_regulation"] == "도시지역편입해제구역"
    assert "UQQ700" not in rendered
    assert "개발밀도관리구역" not in rendered


def run_regression() -> None:
    test_descriptive_diagnostics_remain_unverified()
    test_provenance_policy_remains_blocked()
    test_diagnostic_hits_do_not_promote_authority_or_provenance()
    test_negative_and_runtime_mutation_guards_remain_closed()
    test_empty_payload_fails_closed()
    test_no_uqq700_cross_condition_wiring()

    print("=" * 76)
    print("STEP 20 AUTHORITY SOURCE SCOPE -> HISTORICAL PROVENANCE INTEGRATION")
    print("=" * 76)
    print("Diagnostic URL/candidate/title/archive -> authority verification: NONE")
    print("Official-looking host -> competent authority promotion: NONE")
    print("Source-role metadata -> verified role promotion: NONE")
    print("Authority chain verified: FALSE")
    print("Historical provenance state: BLOCKED")
    print("Negative/legal absence/SITE promotion: NONE")
    print("Production/runtime mutation: NONE")
    print("UQQ700 cross-condition wiring: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    run_regression()
