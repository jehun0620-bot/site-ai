from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_final_resolution import (
    HistoricalSiteEventFinalResolutionAssessment,
)
from law_data.historical_site_event_production_application_adapter import (
    adapt_historical_site_event_production_application_shadow,
)
from law_data.historical_site_event_production_consumption_authorization import (
    assess_historical_site_event_production_consumption_authorization,
)
from law_data.historical_site_event_production_consumption_eligibility import (
    HistoricalSiteEventProductionConsumptionEligibilityAssessment,
)
from law_data.production_site_condition import FALSE, TRUE, UNKNOWN
from law_data.regulation_resolution_profile import RegulationResolutionProfile


CLASSIFICATION = "STEP34_HISTORICAL_SITE_EVENT_PRODUCTION_CONSUMPTION_AUTHORIZATION_BOUNDARY_RECONCILED"
NAME = "synthetic historical condition"


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def profile(*, permissions: bool = True) -> RegulationResolutionProfile:
    return RegulationResolutionProfile(
        name=NAME,
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        site_promotion_allowed=permissions,
        production_registration_allowed=permissions,
        runtime_registration_allowed=permissions,
    )


def final(resolution: str) -> HistoricalSiteEventFinalResolutionAssessment:
    return HistoricalSiteEventFinalResolutionAssessment(
        boundary="HISTORICAL_SITE_EVENT_FINAL_RESOLUTION",
        profile_present=True,
        profile_name=NAME,
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
) -> HistoricalSiteEventProductionConsumptionEligibilityAssessment:
    return HistoricalSiteEventProductionConsumptionEligibilityAssessment(
        boundary="HISTORICAL_SITE_EVENT_PRODUCTION_CONSUMPTION_ELIGIBILITY",
        profile_present=True,
        profile_name=NAME,
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


def shadow(resolution: str, *, eligible: bool = True):
    return adapt_historical_site_event_production_application_shadow(
        profile(permissions=eligible),
        final(resolution),
        eligibility(resolution, eligible=eligible),
        confidence="HIGH",
        source="STEP34_TEST",
    )


def main() -> None:
    true_assessment = assess_historical_site_event_production_consumption_authorization(
        shadow(TRUE)
    ).to_dict()
    require(true_assessment["production_consumption_authorized"] is True, "eligible STEP33 TRUE must authorize")
    require(true_assessment["semantic_state"] == TRUE, "TRUE semantic state must be preserved")

    false_assessment = assess_historical_site_event_production_consumption_authorization(
        shadow(FALSE)
    ).to_dict()
    require(false_assessment["production_consumption_authorized"] is True, "eligible STEP33 FALSE must authorize")
    require(false_assessment["semantic_state"] == FALSE, "FALSE semantic state must be preserved")

    unknown_assessment = assess_historical_site_event_production_consumption_authorization(
        shadow(UNKNOWN, eligible=False)
    ).to_dict()
    require(unknown_assessment["production_consumption_authorized"] is False, "UNKNOWN must not authorize")

    ineligible_assessment = assess_historical_site_event_production_consumption_authorization(
        shadow(TRUE, eligible=False)
    ).to_dict()
    require(ineligible_assessment["production_consumption_authorized"] is False, "ineligible shadow must not authorize")

    eligible_shadow = shadow(TRUE)
    registered_shadow = replace(eligible_shadow, runtime_registered=True)
    registered_assessment = assess_historical_site_event_production_consumption_authorization(
        registered_shadow
    ).to_dict()
    require(registered_assessment["production_consumption_authorized"] is False, "already runtime-registered shadow must fail closed")

    wrong_provenance_shadow = replace(eligible_shadow, provenance={"adapter": "OTHER"})
    wrong_provenance_assessment = assess_historical_site_event_production_consumption_authorization(
        wrong_provenance_shadow
    ).to_dict()
    require(wrong_provenance_assessment["production_consumption_authorized"] is False, "unverified STEP33 provenance must fail closed")

    mutated_diagnostics = dict(eligible_shadow.diagnostics)
    mutated_diagnostics["rule_engine_state_mutated"] = True
    mutated_shadow = replace(eligible_shadow, diagnostics=mutated_diagnostics)
    mutated_assessment = assess_historical_site_event_production_consumption_authorization(
        mutated_shadow
    ).to_dict()
    require(mutated_assessment["production_consumption_authorized"] is False, "pre-mutated shadow must fail closed")

    missing_assessment = assess_historical_site_event_production_consumption_authorization(
        None
    ).to_dict()
    require(missing_assessment["production_consumption_authorized"] is False, "missing shadow must fail closed")

    for assessment in (
        true_assessment,
        false_assessment,
        unknown_assessment,
        ineligible_assessment,
        registered_assessment,
        wrong_provenance_assessment,
        mutated_assessment,
        missing_assessment,
    ):
        require(assessment["production_consumed"] is False, "authorization must not become consumption")
        require(assessment["site_state_mutated"] is False, "SITE mutation forbidden")
        require(assessment["rule_engine_state_mutated"] is False, "Rule Engine mutation forbidden")
        require(assessment["production_wiring_applied"] is False, "production wiring forbidden")
        require(assessment["runtime_registry_mutated"] is False, "runtime registry mutation forbidden")
        require(assessment["historical_producer_auto_run"] is False, "historical producer auto-run forbidden")
        require(assessment["public_api_exposed"] is False, "public API exposure forbidden")

    print("=" * 72)
    print("STEP 34 HISTORICAL SITE EVENT PRODUCTION CONSUMPTION AUTHORIZATION")
    print("=" * 72)
    print("Eligible STEP33 semantic TRUE authorization: PASS")
    print("Eligible STEP33 semantic FALSE authorization: PASS")
    print("UNKNOWN / ineligible fail-closed: PASS")
    print("Runtime registration / provenance / mutation guards: PASS")
    print("Authorization != consumption: PASS")
    print("SITE / Rule Engine mutation: NONE")
    print("Production wiring / runtime registration: NONE")
    print("Historical producer auto-run / public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
