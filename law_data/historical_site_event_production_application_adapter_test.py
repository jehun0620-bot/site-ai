from __future__ import annotations

from law_data.historical_site_event_final_resolution import (
    HistoricalSiteEventFinalResolutionAssessment,
)
from law_data.historical_site_event_production_application_adapter import (
    adapt_historical_site_event_production_application_shadow,
)
from law_data.historical_site_event_production_consumption_eligibility import (
    HistoricalSiteEventProductionConsumptionEligibilityAssessment,
)
from law_data.production_site_condition import FALSE, TRUE, UNKNOWN
from law_data.regulation_resolution_profile import RegulationResolutionProfile


CLASSIFICATION = "STEP33_HISTORICAL_SITE_EVENT_PRODUCTION_APPLICATION_BOUNDARY_RECONCILED"
NAME = "synthetic historical condition"


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def profile(*, permissions: bool) -> RegulationResolutionProfile:
    return RegulationResolutionProfile(
        name=NAME,
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        site_promotion_allowed=permissions,
        production_registration_allowed=permissions,
        runtime_registration_allowed=permissions,
    )


def final(resolution: str, *, name: str = NAME) -> HistoricalSiteEventFinalResolutionAssessment:
    return HistoricalSiteEventFinalResolutionAssessment(
        boundary="HISTORICAL_SITE_EVENT_FINAL_RESOLUTION",
        profile_present=True,
        profile_name=name,
        historical_resolution_type_matched=True,
        historical_condition_type_matched=True,
        candidate_assessment_present=True,
        candidate_profile_aligned=True,
        candidate_conflict_detected=False,
        final_resolution_candidate=(
            "TRUE_CANDIDATE" if resolution == TRUE else
            "FALSE_CANDIDATE" if resolution == FALSE else UNKNOWN
        ),
        missing_gates=(),
        resolution=resolution,
    )


def eligibility(
    resolution: str,
    *,
    eligible: bool,
    name: str = NAME,
) -> HistoricalSiteEventProductionConsumptionEligibilityAssessment:
    return HistoricalSiteEventProductionConsumptionEligibilityAssessment(
        boundary="HISTORICAL_SITE_EVENT_PRODUCTION_CONSUMPTION_ELIGIBILITY",
        profile_present=True,
        profile_name=name,
        historical_resolution_type_matched=True,
        historical_condition_type_matched=True,
        final_resolution_assessment_present=True,
        final_resolution_profile_aligned=True,
        semantic_resolution=resolution,
        semantic_resolution_consumable=resolution in {TRUE, FALSE},
        site_promotion_allowed=eligible,
        production_registration_allowed=eligible,
        runtime_registration_allowed=eligible,
        missing_gates=() if eligible else ("production_consumption_eligible",),
        production_consumption_eligible=eligible,
    )


def main() -> None:
    allowed_profile = profile(permissions=True)

    true_shadow = adapt_historical_site_event_production_application_shadow(
        allowed_profile,
        final(TRUE),
        eligibility(TRUE, eligible=True),
        confidence="HIGH",
        source="STEP33_TEST",
    ).to_dict()
    require(true_shadow["state"] == TRUE, "eligible semantic TRUE must be preserved")
    require(true_shadow["production_eligible"] is True, "TRUE application shadow must be eligible")
    require(true_shadow["runtime_registered"] is False, "permission must not become runtime registration")
    require(true_shadow["site_promotion_allowed"] is False, "adapter must not apply SITE promotion")

    false_shadow = adapt_historical_site_event_production_application_shadow(
        allowed_profile,
        final(FALSE),
        eligibility(FALSE, eligible=True),
    ).to_dict()
    require(false_shadow["state"] == FALSE, "eligible semantic FALSE must be preserved")
    require(false_shadow["production_eligible"] is True, "FALSE application shadow must be eligible")

    unknown_shadow = adapt_historical_site_event_production_application_shadow(
        allowed_profile,
        final(UNKNOWN),
        eligibility(UNKNOWN, eligible=False),
    ).to_dict()
    require(unknown_shadow["state"] == UNKNOWN, "UNKNOWN must remain UNKNOWN")
    require(unknown_shadow["production_eligible"] is False, "UNKNOWN must not become eligible")

    blocked_shadow = adapt_historical_site_event_production_application_shadow(
        profile(permissions=False),
        final(TRUE),
        eligibility(TRUE, eligible=False),
    ).to_dict()
    require(blocked_shadow["state"] == UNKNOWN, "ineligible TRUE must fail closed")
    require(blocked_shadow["production_eligible"] is False, "ineligible TRUE must remain blocked")

    mismatch_shadow = adapt_historical_site_event_production_application_shadow(
        allowed_profile,
        final(TRUE),
        eligibility(FALSE, eligible=True),
    ).to_dict()
    require(mismatch_shadow["state"] == UNKNOWN, "STEP31/32 semantic mismatch must fail closed")
    require(mismatch_shadow["production_eligible"] is False, "mismatch must not be eligible")

    profile_mismatch_shadow = adapt_historical_site_event_production_application_shadow(
        allowed_profile,
        final(TRUE, name="other condition"),
        eligibility(TRUE, eligible=True),
    ).to_dict()
    require(profile_mismatch_shadow["state"] == UNKNOWN, "profile mismatch must fail closed")

    missing_shadow = adapt_historical_site_event_production_application_shadow(
        allowed_profile,
        None,
        None,
    ).to_dict()
    require(missing_shadow["state"] == UNKNOWN, "missing assessments must fail closed")
    require(missing_shadow["production_eligible"] is False, "missing assessments must remain blocked")

    for shadow in (
        true_shadow,
        false_shadow,
        unknown_shadow,
        blocked_shadow,
        mismatch_shadow,
        profile_mismatch_shadow,
        missing_shadow,
    ):
        diagnostics = shadow["diagnostics"]
        require(shadow["runtime_registered"] is False, "runtime registration mutation forbidden")
        require(shadow["negative_evidence_allowed"] is False, "negative evidence inference forbidden")
        require(shadow["legal_absence_inference_allowed"] is False, "legal absence inference forbidden")
        require(shadow["site_promotion_allowed"] is False, "SITE promotion application forbidden")
        require(diagnostics["site_state_mutated"] is False, "SITE mutation forbidden")
        require(diagnostics["rule_engine_state_mutated"] is False, "Rule Engine mutation forbidden")
        require(diagnostics["production_wiring_applied"] is False, "production wiring forbidden")
        require(diagnostics["runtime_registry_mutated"] is False, "runtime registry mutation forbidden")
        require(diagnostics["historical_producer_auto_run"] is False, "historical producer auto-run forbidden")
        require(diagnostics["public_api_exposed"] is False, "public API exposure forbidden")

    print("=" * 72)
    print("STEP 33 HISTORICAL SITE EVENT PRODUCTION APPLICATION BOUNDARY")
    print("=" * 72)
    print("Eligible semantic TRUE shadow: PASS")
    print("Eligible semantic FALSE shadow: PASS")
    print("UNKNOWN preservation: PASS")
    print("Ineligible semantic state fail-closed: PASS")
    print("STEP31/STEP32 alignment guards: PASS")
    print("SITE / Rule Engine mutation: NONE")
    print("Production wiring / runtime registration: NONE")
    print("Historical producer auto-run / public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
