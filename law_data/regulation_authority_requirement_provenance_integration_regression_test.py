from __future__ import annotations

from law_data.urban_area_conversion_provenance_policy_adapter import (
    CONDITION_NAME,
    adapt_urban_area_conversion_provenance_policy,
)


CLASSIFICATION = (
    "STEP22_REGULATION_AUTHORITY_REQUIREMENT_PROVENANCE_INTEGRATION_PASS"
)


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


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
            # Verification-looking diagnostics remain diagnostic only. The adapter
            # intentionally does not import these flags into AuthoritySourceScope.
            "official_host_verified": True,
            "region_binding_verified": True,
            "source_role_verified": True,
            "legal_authority_scope_verified": True,
            "target_regulation_compatible": True,
            "target_regulation_compatibility_verified": True,
        }
    }


def main() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    profile = result["resolution_profile"]
    scope = result["authority_source_scope"]
    requirement = result["regulation_authority_requirement"]
    policy = result["provenance_policy"]
    gates = policy["gates"]

    require(result["condition"] == CONDITION_NAME, "condition identity changed")
    require(profile is not None, "exact-name regulation profile must be present")
    require(
        profile["name"] == CONDITION_NAME,
        "profile identity must remain exact condition identity",
    )
    require(
        profile["standard_code"] is None,
        "historical standard code must remain absent",
    )
    require(
        profile["standard_code_verified"] is False,
        "historical standard code must remain unverified",
    )

    require(
        scope["target_regulation"] == CONDITION_NAME,
        "authority scope target must remain condition-specific",
    )
    require(
        scope["source_host"] == "example.go.kr",
        "descriptive source host should remain available diagnostically",
    )
    require(
        scope["source_role"] == "PRIMARY",
        "descriptive source role should remain available diagnostically",
    )
    require(
        scope["official_host_verified"] is False,
        "official-looking host must not self-verify",
    )
    require(
        scope["region_binding_verified"] is False,
        "region metadata must not self-verify",
    )
    require(
        scope["source_role_verified"] is False,
        "PRIMARY metadata must not self-verify source role",
    )
    require(
        scope["legal_authority_scope_verified"] is False,
        "authority-scope text must not self-verify legal authority",
    )
    require(
        scope["target_regulation_compatibility_verified"] is False,
        "target name must not self-verify compatibility",
    )
    require(
        scope["target_regulation_compatible"] is None,
        "unverified compatibility must remain unknown",
    )
    require(
        scope["authority_chain_verified"] is False,
        "diagnostic authority scope must remain unverified",
    )

    require(
        requirement["profile_present"] is True,
        "authority requirement must observe exact-name profile presence",
    )
    require(
        requirement["condition_identity_aligned"] is True,
        "profile and condition-specific scope target must align descriptively",
    )
    require(
        requirement["authority_requirements_declared"] is True,
        "historical profile must retain declared authority requirements",
    )
    require(
        requirement["source_policy_requirements_declared"] is True,
        "historical profile must retain source-policy requirements diagnostically",
    )
    require(
        requirement["authority_chain_verified"] is False,
        "profile binding must not manufacture authority-chain verification",
    )
    require(
        requirement["authority_requirement_satisfied"] is False,
        "profile/scope descriptive binding must remain unsatisfied",
    )

    require(
        gates["source_authority_identity_verified"] is False,
        "unsatisfied regulation authority requirement must block provenance authority gate",
    )
    require(
        gates["source_role_explicit"] is False,
        "unverified source role must block provenance source-role gate",
    )
    require(
        policy["provenance_policy_verified"] is False,
        "historical provenance must remain unverified",
    )
    require(
        policy["provenance_state"] == "BLOCKED",
        "historical provenance must remain BLOCKED",
    )

    blockers = result["condition_specific_blockers"]
    require(
        blockers["profile_missing"] is False,
        "known profile must not be reported missing",
    )
    require(
        blockers["authority_requirement_unsatisfied"] is True,
        "authority requirement blocker must remain active",
    )
    require(
        blockers["source_authority_identity_unverified"] is True,
        "source authority identity blocker must remain active",
    )

    guards = result["promotion_guards"]
    require(
        guards["profile_presence_promoted_to_authority_verification"] is False,
        "profile presence must not promote authority verification",
    )
    require(
        guards["profile_name_match_promoted_to_authority_verification"] is False,
        "profile name match must not promote authority verification",
    )
    require(
        guards["authority_requirement_promoted_to_legal_resolution"] is False,
        "authority requirement assessment must not promote legal resolution",
    )
    require(
        guards["source_policy_requirement_promoted_to_verified_evidence"] is False,
        "source-policy requirements must not auto-satisfy evidence",
    )

    require(
        policy["negative_evidence_inference_allowed"] is False,
        "negative evidence inference must remain disabled",
    )
    require(
        policy["legal_absence_inference_allowed"] is False,
        "legal absence inference must remain disabled",
    )
    require(
        policy["site_promotion_applied"] is False,
        "SITE promotion must remain disabled",
    )
    require(
        result["output_written"] is False,
        "adapter must remain read-only",
    )
    require(
        result["production_wiring_applied"] is False,
        "production wiring must remain absent",
    )
    require(result["overlay_mutated"] is False, "SITE overlay mutation must remain absent")
    require(
        result["runtime_registry_mutated"] is False,
        "runtime registry mutation must remain absent",
    )

    rendered = repr(result)
    require("UQQ700" not in rendered, "UQQ700 must not cross-wire into historical adapter")
    require(
        "개발밀도관리구역" not in rendered,
        "UQQ700 condition name must not cross-wire into historical adapter",
    )

    empty = adapt_urban_area_conversion_provenance_policy({})
    require(
        empty["regulation_authority_requirement"]["authority_requirement_satisfied"]
        is False,
        "empty diagnostics must fail closed at authority requirement boundary",
    )
    require(
        empty["provenance_policy"]["provenance_state"] == "BLOCKED",
        "empty diagnostics must keep provenance BLOCKED",
    )

    print("=" * 82)
    print("STEP 22 REGULATION AUTHORITY REQUIREMENT -> HISTORICAL PROVENANCE INTEGRATION")
    print("=" * 82)
    print("Exact-name profile presence -> authority verification: NONE")
    print("Profile/scope identity alignment -> authority verification: NONE")
    print("Diagnostic verification-looking fields -> AuthoritySourceScope gates: NONE")
    print("Authority requirement satisfied: FALSE")
    print("Historical standard code: ABSENT / UNVERIFIED")
    print("Historical provenance state: BLOCKED")
    print("Source-policy requirement auto-satisfaction: NONE")
    print("Negative/legal absence/SITE promotion: NONE")
    print("Production/runtime mutation: NONE")
    print("UQQ700 cross-condition wiring: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
