from __future__ import annotations

from pathlib import Path

from law_data.regulation_resolution_profile import RegulationResolutionProfile
from law_data.regulation_resolution_profile_registry import (
    UQQ700_CONDITION_NAME,
    URBAN_AREA_CONVERSION_CONDITION_NAME,
    get_regulation_resolution_profile,
)
from law_data.regulation_source_policy_requirement import (
    evaluate_regulation_source_policy_requirement,
)
from law_data.urban_area_conversion_provenance_policy_adapter import (
    adapt_urban_area_conversion_provenance_policy,
)


CLASSIFICATION = (
    "STEP23_REGULATION_SOURCE_POLICY_REQUIREMENT_BOUNDARY_TERMINALLY_RECONCILED"
)
BASE_DIR = Path(__file__).resolve().parent.parent


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def _read_source(relative_path: str) -> str:
    return (BASE_DIR / relative_path).read_text(encoding="utf-8")


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
            # Verification-looking diagnostics must remain non-dispositive.
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


def test_boundary_fails_closed_without_profile_or_requirements() -> None:
    missing_profile = evaluate_regulation_source_policy_requirement(
        None,
        {
            "HISTORY COMPLETENESS VERIFIED": True,
            "PROVENANCE VERIFIED": True,
        },
    ).to_dict()

    require(missing_profile["profile_present"] is False, "missing profile inferred")
    require(
        missing_profile["source_policy_requirements_declared"] is False,
        "missing profile unexpectedly declared requirements",
    )
    require(
        missing_profile["source_policy_requirement_satisfied"] is False,
        "missing profile unexpectedly satisfied source-policy requirement",
    )

    empty_profile = RegulationResolutionProfile(
        name="EMPTY SOURCE POLICY",
        condition_type="SITE",
        resolution_type="SNAPSHOT",
        source_policy_requirements=(),
        source_policy_verified=True,
    )
    empty = evaluate_regulation_source_policy_requirement(
        empty_profile,
        {},
    ).to_dict()

    require(
        empty["source_policy_requirements_declared"] is False,
        "empty source-policy declaration unexpectedly treated as declared",
    )
    require(
        empty["source_policy_requirement_satisfied"] is False,
        "empty source-policy declaration was vacuously satisfied",
    )


def test_declaration_and_profile_flag_do_not_manufacture_verification() -> None:
    historical_profile = get_regulation_resolution_profile(
        URBAN_AREA_CONVERSION_CONDITION_NAME
    )
    require(historical_profile is not None, "historical profile missing")

    assessment = evaluate_regulation_source_policy_requirement(
        historical_profile,
        None,
    ).to_dict()

    require(
        assessment["source_policy_requirements_declared"] is True,
        "historical source-policy requirements unexpectedly missing",
    )
    require(
        assessment["verified_requirements"] == [],
        "declaration unexpectedly manufactured verified requirements",
    )
    require(
        assessment["source_policy_requirement_satisfied"] is False,
        "declaration unexpectedly satisfied source-policy requirement",
    )

    synthetic_profile = RegulationResolutionProfile(
        name="SYNTHETIC SOURCE POLICY",
        condition_type="SITE",
        resolution_type="SNAPSHOT",
        source_policy_requirements=("EXPLICIT FACT VERIFIED",),
        source_policy_verified=True,
    )
    synthetic = evaluate_regulation_source_policy_requirement(
        synthetic_profile,
        None,
    ).to_dict()

    require(
        synthetic["source_policy_requirement_satisfied"] is False,
        "profile source_policy_verified flag bypassed explicit requirement facts",
    )


def test_positive_satisfaction_requires_all_declared_explicit_true_facts() -> None:
    historical_profile = get_regulation_resolution_profile(
        URBAN_AREA_CONVERSION_CONDITION_NAME
    )
    require(historical_profile is not None, "historical profile missing")

    partial = evaluate_regulation_source_policy_requirement(
        historical_profile,
        {
            "HISTORY COMPLETENESS VERIFIED": True,
            "PROVENANCE VERIFIED": False,
        },
    ).to_dict()
    require(
        partial["source_policy_requirement_satisfied"] is False,
        "partial source-policy facts unexpectedly satisfied requirements",
    )

    truthy = evaluate_regulation_source_policy_requirement(
        historical_profile,
        {
            "HISTORY COMPLETENESS VERIFIED": 1,
            "PROVENANCE VERIFIED": "true",
        },
    ).to_dict()
    require(
        truthy["source_policy_requirement_satisfied"] is False,
        "truthy non-bool source-policy facts unexpectedly satisfied requirements",
    )

    complete = evaluate_regulation_source_policy_requirement(
        historical_profile,
        {
            "HISTORY COMPLETENESS VERIFIED": True,
            "PROVENANCE VERIFIED": True,
            "UNRELATED VERIFIED FACT": True,
        },
    ).to_dict()
    require(
        complete["source_policy_requirement_satisfied"] is True,
        "all explicit declared True facts did not satisfy requirements",
    )
    require(
        complete["verified_requirements"] == [
            "HISTORY COMPLETENESS VERIFIED",
            "PROVENANCE VERIFIED",
        ],
        "declared verified requirement set changed",
    )
    require(
        complete["unexpected_requirements"] == ["UNRELATED VERIFIED FACT"],
        "unrelated verified fact was not isolated diagnostically",
    )
    require(
        "state" not in complete and "site_state" not in complete,
        "source-policy assessment manufactured SITE state",
    )
    require(
        "production_registration_allowed" not in complete,
        "source-policy assessment manufactured production permission",
    )
    require(
        "runtime_registration_allowed" not in complete,
        "source-policy assessment manufactured runtime permission",
    )


def test_historical_integration_remains_blocked_and_unpromoted() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    profile = result["resolution_profile"]
    policy = result["provenance_policy"]
    source_policy = result["regulation_source_policy_requirement"]
    blockers = result["condition_specific_blockers"]
    guards = result["promotion_guards"]

    require(result["condition"] == URBAN_AREA_CONVERSION_CONDITION_NAME, "condition changed")
    require(profile is not None, "historical profile missing from adapter")
    require(profile["standard_code"] is None, "historical standard code was guessed")
    require(
        profile["standard_code_verified"] is False,
        "historical standard code unexpectedly verified",
    )
    require(
        profile["source_policy_requirements"] == [
            "HISTORY COMPLETENESS VERIFIED",
            "PROVENANCE VERIFIED",
        ],
        "historical source-policy requirements changed",
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
        source_policy["verified_requirements"] == [],
        "diagnostic fields unexpectedly became verified source-policy facts",
    )
    require(
        source_policy["missing_requirements"] == [
            "HISTORY COMPLETENESS VERIFIED",
            "PROVENANCE VERIFIED",
        ],
        "historical missing source-policy requirements changed",
    )
    require(
        source_policy["source_policy_requirement_satisfied"] is False,
        "historical source-policy requirement unexpectedly satisfied",
    )
    require(
        blockers["history_completeness_unverified"] is True,
        "provenance adapter unexpectedly verified history completeness",
    )
    require(
        blockers["source_policy_requirement_unsatisfied"] is True,
        "historical source-policy blocker unexpectedly cleared",
    )

    require(
        guards["source_policy_requirement_promoted_to_verified_evidence"] is False,
        "source-policy assessment promoted to verified evidence",
    )
    require(
        guards["source_policy_requirement_promoted_to_legal_resolution"] is False,
        "source-policy assessment promoted to legal resolution",
    )
    require(
        guards["contract_readiness_promoted_to_source_policy_verification"] is False,
        "contract readiness promoted to source-policy verification",
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
        "regulation_source_policy_requirement",
        "RegulationSourcePolicyRequirementAssessment",
        "evaluate_regulation_source_policy_requirement",
    )

    for relative_path in isolated_paths:
        source = _read_source(relative_path)
        for token in forbidden_tokens:
            require(
                token not in source,
                f"STEP23 boundary unexpectedly auto-wired into {relative_path}: {token}",
            )


def test_boundary_has_no_registry_or_mutation_surface() -> None:
    boundary_source = _read_source("law_data/regulation_source_policy_requirement.py")

    forbidden_surfaces = (
        "SOURCE_POLICY_REGISTRY",
        "SOURCE_REQUIREMENT_REGISTRY",
        "def register_",
        "def register_runtime",
        "def resolve_",
        "def promote_",
    )

    for token in forbidden_surfaces:
        require(
            token not in boundary_source,
            f"source-policy registry/mutation surface unexpectedly present: {token}",
        )


def run_terminal_audit() -> None:
    test_boundary_fails_closed_without_profile_or_requirements()
    test_declaration_and_profile_flag_do_not_manufacture_verification()
    test_positive_satisfaction_requires_all_declared_explicit_true_facts()
    test_historical_integration_remains_blocked_and_unpromoted()
    test_no_runtime_rule_engine_or_public_api_auto_wiring()
    test_boundary_has_no_registry_or_mutation_surface()

    print("=" * 86)
    print("STEP 23 REGULATION SOURCE POLICY REQUIREMENT BOUNDARY TERMINAL AUDIT")
    print("=" * 86)
    print("Missing profile / empty requirement declaration fail-closed: PASS")
    print("Requirement declaration -> verification: NONE")
    print("Profile source_policy_verified flag -> requirement satisfaction: NONE")
    print("Partial / truthy / unrelated facts -> requirement satisfaction: NONE")
    print("Positive source-policy requirement: ALL DECLARED EXPLICIT TRUE FACTS ONLY")
    print("Historical standard code: ABSENT / UNVERIFIED")
    print("Historical provenance state: BLOCKED")
    print("History completeness verified by provenance adapter: FALSE")
    print("Historical source-policy requirement satisfied: FALSE")
    print("Negative/legal absence/SITE promotion: NONE")
    print("Production/runtime mutation: NONE")
    print("UQQ700 cross-condition wiring: NONE")
    print("Builder/service/orchestrator/public API/spatial runtime auto-wiring: NONE")
    print("Source-policy registry/mutation requirement: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    run_terminal_audit()
