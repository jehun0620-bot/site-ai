"""Terminal audit for STEP32 production-consumption eligibility boundary."""

from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_final_resolution import (
    FALSE,
    TRUE,
    UNKNOWN,
    HistoricalSiteEventFinalResolutionAssessment,
)
from law_data.historical_site_event_production_consumption_eligibility import (
    evaluate_historical_site_event_production_consumption_eligibility,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile
from law_data.regulation_resolution_profile_registry import (
    URBAN_AREA_CONVERSION_CONDITION_NAME,
    get_regulation_resolution_profile,
)


TERMINAL_CLASSIFICATION = (
    "STEP32_HISTORICAL_SITE_EVENT_PRODUCTION_CONSUMPTION_ELIGIBILITY_"
    "BOUNDARY_TERMINALLY_RECONCILED"
)


def _profile(
    name: str,
    *,
    site: object = True,
    production: object = True,
    runtime: object = True,
) -> RegulationResolutionProfile:
    return RegulationResolutionProfile(
        name=name,
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        negative_evidence_allowed=True,
        legal_absence_inference_allowed=False,
        site_promotion_allowed=site,
        production_registration_allowed=production,
        runtime_registration_allowed=runtime,
    )


def _resolution(
    profile: RegulationResolutionProfile,
    resolution: str,
) -> HistoricalSiteEventFinalResolutionAssessment:
    return HistoricalSiteEventFinalResolutionAssessment(
        boundary="STEP32_SYNTHETIC_FINAL_RESOLUTION",
        profile_present=True,
        profile_name=profile.name,
        historical_resolution_type_matched=True,
        historical_condition_type_matched=True,
        candidate_assessment_present=True,
        candidate_profile_aligned=True,
        candidate_conflict_detected=False,
        final_resolution_candidate=(
            "TRUE_CANDIDATE"
            if resolution == TRUE
            else "FALSE_CANDIDATE"
            if resolution == FALSE
            else UNKNOWN
        ),
        missing_gates=(),
        resolution=resolution,
    )


def main() -> None:
    profile = _profile("STEP32_SYNTHETIC_PROFILE")

    true_assessment = evaluate_historical_site_event_production_consumption_eligibility(
        profile, _resolution(profile, TRUE)
    )
    assert true_assessment.production_consumption_eligible is True
    assert true_assessment.semantic_resolution == TRUE

    false_assessment = evaluate_historical_site_event_production_consumption_eligibility(
        profile, _resolution(profile, FALSE)
    )
    assert false_assessment.production_consumption_eligible is True
    assert false_assessment.semantic_resolution == FALSE

    unknown_assessment = evaluate_historical_site_event_production_consumption_eligibility(
        profile, _resolution(profile, UNKNOWN)
    )
    assert unknown_assessment.production_consumption_eligible is False
    assert "semantic_resolution_consumable" in unknown_assessment.missing_gates

    missing = evaluate_historical_site_event_production_consumption_eligibility(
        profile, None
    )
    assert missing.production_consumption_eligible is False
    assert "final_resolution_assessment_present" in missing.missing_gates

    other_profile = _profile("STEP32_OTHER_PROFILE")
    mismatched = evaluate_historical_site_event_production_consumption_eligibility(
        other_profile, _resolution(profile, TRUE)
    )
    assert mismatched.production_consumption_eligible is False
    assert "final_resolution_profile_aligned" in mismatched.missing_gates

    for field_name in (
        "site_promotion_allowed",
        "production_registration_allowed",
        "runtime_registration_allowed",
    ):
        blocked_profile = replace(profile, **{field_name: False})
        blocked = evaluate_historical_site_event_production_consumption_eligibility(
            blocked_profile, _resolution(blocked_profile, TRUE)
        )
        assert blocked.production_consumption_eligible is False
        assert field_name in blocked.missing_gates

    for field_name in (
        "site_promotion_allowed",
        "production_registration_allowed",
        "runtime_registration_allowed",
    ):
        truthy_profile = replace(profile, **{field_name: 1})
        truthy = evaluate_historical_site_event_production_consumption_eligibility(
            truthy_profile, _resolution(truthy_profile, TRUE)
        )
        assert truthy.production_consumption_eligible is False
        assert field_name in truthy.missing_gates

    invalid_resolution = _resolution(profile, UNKNOWN)
    invalid_resolution = replace(invalid_resolution, resolution="TRUE_CANDIDATE")
    invalid = evaluate_historical_site_event_production_consumption_eligibility(
        profile, invalid_resolution
    )
    assert invalid.production_consumption_eligible is False
    assert "semantic_resolution_consumable" in invalid.missing_gates

    payload = true_assessment.to_dict()
    assert payload["site_state_mutated"] is False
    assert payload["rule_engine_state_mutated"] is False
    assert payload["production_wiring_applied"] is False
    assert payload["runtime_registry_mutated"] is False
    assert payload["public_api_exposed"] is False

    actual_profile = get_regulation_resolution_profile(
        URBAN_AREA_CONVERSION_CONDITION_NAME
    )
    assert actual_profile is not None
    actual_resolution = _resolution(actual_profile, UNKNOWN)
    actual = evaluate_historical_site_event_production_consumption_eligibility(
        actual_profile, actual_resolution
    )
    assert actual_profile.site_promotion_allowed is False
    assert actual_profile.production_registration_allowed is False
    assert actual_profile.runtime_registration_allowed is False
    assert actual.semantic_resolution == UNKNOWN
    assert actual.production_consumption_eligible is False

    print("=" * 60)
    print("STEP32 HISTORICAL SITE EVENT PRODUCTION CONSUMPTION ELIGIBILITY")
    print("=" * 60)
    print("Semantic TRUE + all explicit permissions -> eligible: PASS")
    print("Semantic FALSE + all explicit permissions -> eligible: PASS")
    print("Semantic UNKNOWN -> eligibility blocked: PASS")
    print("Missing / mismatched assessment -> eligibility blocked: PASS")
    print("Missing or truthy non-bool permission -> eligibility blocked: PASS")
    print("Actual historical profile remains production-blocked: PASS")
    print("SITE / Rule Engine / production / runtime / API mutation: NONE")
    print(f"Classification: {TERMINAL_CLASSIFICATION}")


if __name__ == "__main__":
    main()
