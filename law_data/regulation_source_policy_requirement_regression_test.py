from __future__ import annotations

from law_data.regulation_resolution_profile import RegulationResolutionProfile
from law_data.regulation_source_policy_requirement import (
    BOUNDARY_NAME,
    evaluate_regulation_source_policy_requirement,
)


CLASSIFICATION = "STEP23_REGULATION_SOURCE_POLICY_REQUIREMENT_BOUNDARY_PASS"


def _profile(
    *,
    requirements: tuple[str, ...] = ("HISTORY COMPLETENESS VERIFIED", "PROVENANCE VERIFIED"),
    source_policy_verified: bool = False,
) -> RegulationResolutionProfile:
    return RegulationResolutionProfile(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        standard_code=None,
        standard_code_verified=False,
        authority_requirements=("VERIFIED QUALIFYING HISTORICAL SITE EVENT",),
        source_policy_requirements=requirements,
        source_policy_verified=source_policy_verified,
        negative_evidence_allowed=False,
        legal_absence_inference_allowed=False,
        site_promotion_allowed=False,
        production_registration_allowed=False,
        runtime_registration_allowed=False,
    )


def main() -> None:
    profile = _profile()

    missing_facts = evaluate_regulation_source_policy_requirement(profile, None)
    assert missing_facts.profile_present is True
    assert missing_facts.source_policy_requirements_declared is True
    assert missing_facts.verified_requirements == ()
    assert missing_facts.missing_requirements == profile.source_policy_requirements
    assert missing_facts.source_policy_requirement_satisfied is False

    partial = evaluate_regulation_source_policy_requirement(
        profile,
        {
            "HISTORY COMPLETENESS VERIFIED": True,
            "PROVENANCE VERIFIED": False,
        },
    )
    assert partial.verified_requirements == ("HISTORY COMPLETENESS VERIFIED",)
    assert partial.missing_requirements == ("PROVENANCE VERIFIED",)
    assert partial.source_policy_requirement_satisfied is False

    truthy_not_true = evaluate_regulation_source_policy_requirement(
        profile,
        {
            "HISTORY COMPLETENESS VERIFIED": 1,
            "PROVENANCE VERIFIED": "true",
        },
    )
    assert truthy_not_true.verified_requirements == ()
    assert truthy_not_true.source_policy_requirement_satisfied is False

    unrelated = evaluate_regulation_source_policy_requirement(
        profile,
        {
            "OTHER VERIFIED REQUIREMENT": True,
        },
    )
    assert unrelated.unexpected_requirements == ("OTHER VERIFIED REQUIREMENT",)
    assert unrelated.source_policy_requirement_satisfied is False

    complete_with_extra = evaluate_regulation_source_policy_requirement(
        profile,
        {
            "HISTORY COMPLETENESS VERIFIED": True,
            "PROVENANCE VERIFIED": True,
            "UNRELATED POSITIVE FACT": True,
        },
    )
    assert complete_with_extra.verified_requirements == profile.source_policy_requirements
    assert complete_with_extra.missing_requirements == ()
    assert complete_with_extra.unexpected_requirements == ("UNRELATED POSITIVE FACT",)
    assert complete_with_extra.source_policy_requirement_satisfied is True

    profile_flag_only = evaluate_regulation_source_policy_requirement(
        _profile(source_policy_verified=True),
        None,
    )
    assert profile_flag_only.source_policy_requirement_satisfied is False

    empty_declaration = evaluate_regulation_source_policy_requirement(
        _profile(requirements=()),
        {},
    )
    assert empty_declaration.source_policy_requirements_declared is False
    assert empty_declaration.source_policy_requirement_satisfied is False

    absent_profile = evaluate_regulation_source_policy_requirement(
        None,
        {
            "HISTORY COMPLETENESS VERIFIED": True,
            "PROVENANCE VERIFIED": True,
        },
    )
    assert absent_profile.profile_present is False
    assert absent_profile.source_policy_requirements == ()
    assert absent_profile.source_policy_requirement_satisfied is False

    payload = complete_with_extra.to_dict()
    assert payload["boundary_name"] == BOUNDARY_NAME
    forbidden_keys = {
        "site_state",
        "site_condition_context",
        "negative_evidence_allowed",
        "legal_absence_inference_allowed",
        "site_promotion_allowed",
        "production_registration_allowed",
        "runtime_registration_allowed",
        "rule_engine_mutated",
        "public_api_exposed",
    }
    assert forbidden_keys.isdisjoint(payload)

    print("=" * 72)
    print("STEP 23 REGULATION SOURCE POLICY REQUIREMENT BOUNDARY REGRESSION")
    print("Requirement declaration -> verification: NONE")
    print("Profile source_policy_verified flag -> requirement satisfaction: NONE")
    print("Partial / truthy / unrelated facts -> requirement satisfaction: NONE")
    print("Empty declaration -> vacuous satisfaction: BLOCKED")
    print("Positive satisfaction: ALL DECLARED REQUIREMENTS EXPLICITLY TRUE ONLY")
    print("SITE/legal absence/production/runtime mutation semantics: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
