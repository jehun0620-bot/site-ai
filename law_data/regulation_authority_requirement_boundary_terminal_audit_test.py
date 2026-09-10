from __future__ import annotations

from pathlib import Path

from law_data.authority_source_scope import AuthoritySourceScope
from law_data.regulation_authority_requirement import (
    evaluate_regulation_authority_requirement,
)
from law_data.regulation_resolution_profile_registry import (
    UQQ700_CONDITION_NAME,
    URBAN_AREA_CONVERSION_CONDITION_NAME,
    get_regulation_resolution_profile,
)
from law_data.urban_area_conversion_provenance_policy_adapter import (
    adapt_urban_area_conversion_provenance_policy,
)


CLASSIFICATION = (
    "STEP22_REGULATION_AUTHORITY_REQUIREMENT_BOUNDARY_TERMINALLY_RECONCILED"
)
BASE_DIR = Path(__file__).resolve().parent.parent


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def _read_source(relative_path: str) -> str:
    return (BASE_DIR / relative_path).read_text(encoding="utf-8")


def _fully_verified_scope(target_regulation: str) -> AuthoritySourceScope:
    return AuthoritySourceScope(
        source_uri="https://city.go.kr/notice/1",
        source_host="city.go.kr",
        official_host_verified=True,
        region_binding="서울특별시",
        region_binding_verified=True,
        source_role="PRIMARY",
        source_role_verified=True,
        legal_authority_scope="도시계획 고시",
        legal_authority_scope_verified=True,
        target_regulation=target_regulation,
        target_regulation_compatible=True,
        target_regulation_compatibility_verified=True,
    )


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
            # These verification-looking diagnostic values must remain non-dispositive.
            "official_host_verified": True,
            "region_binding_verified": True,
            "source_role_verified": True,
            "legal_authority_scope_verified": True,
            "target_regulation_compatible": True,
            "target_regulation_compatibility_verified": True,
        }
    }


def test_boundary_fails_closed_without_profile_or_scope() -> None:
    no_profile = evaluate_regulation_authority_requirement(None, None).to_dict()
    require(no_profile["profile_present"] is False, "missing profile inferred")
    require(
        no_profile["authority_requirement_satisfied"] is False,
        "missing profile/scope unexpectedly satisfied authority requirement",
    )

    historical_profile = get_regulation_resolution_profile(
        URBAN_AREA_CONVERSION_CONDITION_NAME
    )
    require(historical_profile is not None, "historical profile missing")

    no_scope = evaluate_regulation_authority_requirement(
        historical_profile,
        None,
    ).to_dict()
    require(
        no_scope["condition_identity_aligned"] is False,
        "missing scope unexpectedly aligned condition identity",
    )
    require(
        no_scope["authority_requirement_satisfied"] is False,
        "missing scope unexpectedly satisfied authority requirement",
    )


def test_descriptive_identity_and_metadata_do_not_verify_authority() -> None:
    historical_profile = get_regulation_resolution_profile(
        URBAN_AREA_CONVERSION_CONDITION_NAME
    )
    require(historical_profile is not None, "historical profile missing")

    assessment = evaluate_regulation_authority_requirement(
        historical_profile,
        {
            "source_uri": "https://example.go.kr/notice/123",
            "region_binding": "서울특별시",
            "source_role": "PRIMARY",
            "legal_authority_scope": "도시계획 고시",
            "target_regulation": URBAN_AREA_CONVERSION_CONDITION_NAME,
        },
    ).to_dict()

    require(
        assessment["condition_identity_aligned"] is True,
        "exact descriptive identity should align",
    )
    require(
        assessment["authority_chain_verified"] is False,
        "descriptive metadata unexpectedly verified authority chain",
    )
    require(
        assessment["authority_requirement_satisfied"] is False,
        "descriptive profile/scope binding unexpectedly satisfied authority requirement",
    )


def test_cross_regulation_verified_scope_is_blocked() -> None:
    historical_profile = get_regulation_resolution_profile(
        URBAN_AREA_CONVERSION_CONDITION_NAME
    )
    require(historical_profile is not None, "historical profile missing")

    assessment = evaluate_regulation_authority_requirement(
        historical_profile,
        _fully_verified_scope(UQQ700_CONDITION_NAME),
    ).to_dict()

    require(
        assessment["authority_chain_verified"] is True,
        "synthetic verified scope should be internally verified for its own target",
    )
    require(
        assessment["condition_identity_aligned"] is False,
        "cross-regulation target unexpectedly aligned",
    )
    require(
        assessment["authority_requirement_satisfied"] is False,
        "verified authority for another regulation was reused",
    )


def test_positive_satisfaction_requires_exact_verified_matching_chain() -> None:
    uqq700_profile = get_regulation_resolution_profile(UQQ700_CONDITION_NAME)
    require(uqq700_profile is not None, "UQQ700 profile missing")

    assessment = evaluate_regulation_authority_requirement(
        uqq700_profile,
        _fully_verified_scope(UQQ700_CONDITION_NAME),
    ).to_dict()

    require(
        assessment["condition_identity_aligned"] is True,
        "matching verified scope did not align condition identity",
    )
    require(
        assessment["authority_chain_verified"] is True,
        "fully verified scope did not verify authority chain",
    )
    require(
        assessment["authority_requirement_satisfied"] is True,
        "explicit verified matching chain did not satisfy authority requirement",
    )
    require(
        assessment["source_policy_requirements_declared"] is True,
        "source-policy requirements unexpectedly missing",
    )
    require(
        "state" not in assessment and "site_state" not in assessment,
        "authority requirement assessment manufactured SITE state",
    )
    require(
        "production_registration_allowed" not in assessment,
        "authority requirement assessment manufactured production permission",
    )
    require(
        "runtime_registration_allowed" not in assessment,
        "authority requirement assessment manufactured runtime permission",
    )


def test_historical_integration_remains_blocked_and_unpromoted() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    profile = result["resolution_profile"]
    scope = result["authority_source_scope"]
    requirement = result["regulation_authority_requirement"]
    policy = result["provenance_policy"]
    gates = policy["gates"]

    require(result["condition"] == URBAN_AREA_CONVERSION_CONDITION_NAME, "condition changed")
    require(profile is not None, "historical profile missing from adapter")
    require(profile["standard_code"] is None, "historical standard code was guessed")
    require(
        profile["standard_code_verified"] is False,
        "historical standard code unexpectedly verified",
    )

    require(scope["official_host_verified"] is False, "diagnostic host was promoted")
    require(scope["region_binding_verified"] is False, "diagnostic region was promoted")
    require(scope["source_role_verified"] is False, "diagnostic source role was promoted")
    require(
        scope["legal_authority_scope_verified"] is False,
        "diagnostic authority scope was promoted",
    )
    require(
        scope["target_regulation_compatibility_verified"] is False,
        "diagnostic regulation compatibility was promoted",
    )
    require(scope["authority_chain_verified"] is False, "authority chain was promoted")

    require(
        requirement["profile_present"] is True,
        "historical profile presence missing from authority assessment",
    )
    require(
        requirement["condition_identity_aligned"] is True,
        "historical profile/scope descriptive identity should align",
    )
    require(
        requirement["authority_requirement_satisfied"] is False,
        "historical authority requirement unexpectedly satisfied",
    )

    require(
        gates["source_authority_identity_verified"] is False,
        "historical provenance authority gate unexpectedly verified",
    )
    require(
        gates["source_role_explicit"] is False,
        "historical provenance source-role gate unexpectedly verified",
    )
    require(
        policy["provenance_policy_verified"] is False,
        "historical provenance unexpectedly verified",
    )
    require(
        policy["provenance_state"] == "BLOCKED",
        "historical provenance must remain BLOCKED",
    )

    require(
        policy["negative_evidence_inference_allowed"] is False,
        "negative evidence inference enabled",
    )
    require(
        policy["legal_absence_inference_allowed"] is False,
        "legal absence inference enabled",
    )
    require(policy["site_promotion_applied"] is False, "SITE promotion applied")
    require(result["output_written"] is False, "adapter wrote output")
    require(result["production_wiring_applied"] is False, "production wiring applied")
    require(result["overlay_mutated"] is False, "SITE overlay mutated")
    require(result["runtime_registry_mutated"] is False, "runtime registry mutated")

    rendered = repr(result)
    require("UQQ700" not in rendered, "UQQ700 cross-wired into historical adapter")
    require(
        UQQ700_CONDITION_NAME not in rendered,
        "UQQ700 condition name cross-wired into historical adapter",
    )


def test_no_runtime_rule_engine_or_public_api_auto_wiring() -> None:
    isolated_paths = (
        "law_data/spatial_condition_evaluator.py",
        "law_data/site_analysis_builder.py",
        "site_data/site_analysis_service.py",
        "site_data/site_analysis_orchestrator.py",
        "site_data/site_analysis_response.py",
    )

    forbidden_tokens = (
        "regulation_authority_requirement",
        "RegulationAuthorityRequirementAssessment",
        "evaluate_regulation_authority_requirement",
    )

    for relative_path in isolated_paths:
        source = _read_source(relative_path)
        for token in forbidden_tokens:
            require(
                token not in source,
                f"STEP22 boundary unexpectedly auto-wired into {relative_path}: {token}",
            )


def test_boundary_does_not_require_authority_registry() -> None:
    boundary_source = _read_source("law_data/regulation_authority_requirement.py")

    forbidden_registry_surfaces = (
        "SOURCE_AUTHORITY_REGISTRY",
        "AUTHORITY_SCOPE_REGISTRY",
        "def register_",
        "def register_runtime",
        "def resolve_",
        "def promote_",
    )

    for token in forbidden_registry_surfaces:
        require(
            token not in boundary_source,
            f"authority registry/mutation surface unexpectedly required: {token}",
        )


def run_terminal_audit() -> None:
    test_boundary_fails_closed_without_profile_or_scope()
    test_descriptive_identity_and_metadata_do_not_verify_authority()
    test_cross_regulation_verified_scope_is_blocked()
    test_positive_satisfaction_requires_exact_verified_matching_chain()
    test_historical_integration_remains_blocked_and_unpromoted()
    test_no_runtime_rule_engine_or_public_api_auto_wiring()
    test_boundary_does_not_require_authority_registry()

    print("=" * 82)
    print("STEP 22 REGULATION AUTHORITY REQUIREMENT BOUNDARY TERMINAL AUDIT")
    print("=" * 82)
    print("Missing profile/scope fail-closed: PASS")
    print("Profile/scope descriptive identity -> authority verification: NONE")
    print("Official-looking host / PRIMARY / authority text promotion: NONE")
    print("Cross-regulation verified authority reuse: BLOCKED")
    print("Positive authority requirement: EXPLICIT VERIFIED MATCHING CHAIN ONLY")
    print("Source-policy requirement auto-satisfaction: NONE")
    print("Historical standard code: ABSENT / UNVERIFIED")
    print("Historical provenance state: BLOCKED")
    print("Negative/legal absence/SITE promotion: NONE")
    print("Production/runtime mutation: NONE")
    print("UQQ700 cross-condition wiring: NONE")
    print("Builder/service/orchestrator/public API/spatial runtime auto-wiring: NONE")
    print("Authority registry requirement: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    run_terminal_audit()
