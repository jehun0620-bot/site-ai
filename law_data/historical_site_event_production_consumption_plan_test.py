from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_final_resolution import HistoricalSiteEventFinalResolutionAssessment
from law_data.historical_site_event_production_application_adapter import adapt_historical_site_event_production_application_shadow
from law_data.historical_site_event_production_consumption_authorization import assess_historical_site_event_production_consumption_authorization
from law_data.historical_site_event_production_consumption_eligibility import HistoricalSiteEventProductionConsumptionEligibilityAssessment
from law_data.historical_site_event_production_consumption_plan import plan_historical_site_event_production_consumption
from law_data.production_site_condition import FALSE, TRUE, UNKNOWN
from law_data.regulation_resolution_profile import RegulationResolutionProfile


CLASSIFICATION = "STEP35_HISTORICAL_SITE_EVENT_PRODUCTION_CONSUMPTION_PLAN_BOUNDARY_RECONCILED"
NAME = "synthetic historical condition"


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def profile() -> RegulationResolutionProfile:
    return RegulationResolutionProfile(
        name=NAME,
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        site_promotion_allowed=True,
        production_registration_allowed=True,
        runtime_registration_allowed=True,
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
        final_resolution_candidate="TRUE_CANDIDATE" if resolution == TRUE else "FALSE_CANDIDATE" if resolution == FALSE else UNKNOWN,
        missing_gates=(),
        resolution=resolution,
    )


def eligibility(resolution: str, eligible: bool = True) -> HistoricalSiteEventProductionConsumptionEligibilityAssessment:
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


def shadow(resolution: str, eligible: bool = True):
    return adapt_historical_site_event_production_application_shadow(
        profile(), final(resolution), eligibility(resolution, eligible),
        confidence="HIGH", source="STEP35_TEST",
    )


def make_plan(resolution: str):
    item = shadow(resolution)
    auth = assess_historical_site_event_production_consumption_authorization(item)
    return item, auth, plan_historical_site_event_production_consumption(item, auth).to_dict()


def main() -> None:
    true_shadow, true_auth, true_plan = make_plan(TRUE)
    require(true_plan["consumption_planned"] is True, "authorized TRUE must be planned")
    require(true_plan["semantic_state"] == TRUE, "TRUE state must be preserved")
    require(true_plan["target_consumer"] == "RULE_ENGINE_SITE_CONDITION", "target must be explicit")

    _, _, false_plan = make_plan(FALSE)
    require(false_plan["consumption_planned"] is True, "authorized FALSE must be planned")
    require(false_plan["semantic_state"] == FALSE, "FALSE state must be preserved")

    unknown_shadow = shadow(UNKNOWN, eligible=False)
    unknown_auth = assess_historical_site_event_production_consumption_authorization(unknown_shadow)
    unknown_plan = plan_historical_site_event_production_consumption(unknown_shadow, unknown_auth).to_dict()
    require(unknown_plan["consumption_planned"] is False, "UNKNOWN must fail closed")

    ineligible_shadow = shadow(TRUE, eligible=False)
    ineligible_auth = assess_historical_site_event_production_consumption_authorization(ineligible_shadow)
    ineligible_plan = plan_historical_site_event_production_consumption(ineligible_shadow, ineligible_auth).to_dict()
    require(ineligible_plan["consumption_planned"] is False, "ineligible must fail closed")

    denied_auth = replace(true_auth, production_consumption_authorized=False)
    denied_plan = plan_historical_site_event_production_consumption(true_shadow, denied_auth).to_dict()
    require(denied_plan["consumption_planned"] is False, "denied authorization must fail closed")

    mismatch_auth = replace(true_auth, semantic_state=FALSE)
    mismatch_plan = plan_historical_site_event_production_consumption(true_shadow, mismatch_auth).to_dict()
    require(mismatch_plan["consumption_planned"] is False, "state mismatch must fail closed")

    wrong_boundary_auth = replace(true_auth, boundary="OTHER_BOUNDARY")
    wrong_boundary_plan = plan_historical_site_event_production_consumption(true_shadow, wrong_boundary_auth).to_dict()
    require(wrong_boundary_plan["consumption_planned"] is False, "authorization boundary mismatch must fail closed")

    missing_shadow_plan = plan_historical_site_event_production_consumption(None, true_auth).to_dict()
    missing_auth_plan = plan_historical_site_event_production_consumption(true_shadow, None).to_dict()
    require(missing_shadow_plan["consumption_planned"] is False, "missing shadow must fail closed")
    require(missing_auth_plan["consumption_planned"] is False, "missing authorization must fail closed")

    for item in (
        true_plan, false_plan, unknown_plan, ineligible_plan, denied_plan,
        mismatch_plan, wrong_boundary_plan, missing_shadow_plan, missing_auth_plan,
    ):
        require(item["consumption_executed"] is False, "planned must not become executed")
        require(item["site_state_mutated"] is False, "SITE mutation forbidden")
        require(item["rule_engine_state_mutated"] is False, "Rule Engine mutation forbidden")
        require(item["production_wiring_applied"] is False, "production wiring forbidden")
        require(item["runtime_registered"] is False, "runtime registration forbidden")
        require(item["runtime_registry_mutated"] is False, "runtime registry mutation forbidden")
        require(item["historical_producer_auto_run"] is False, "historical producer auto-run forbidden")
        require(item["public_api_exposed"] is False, "public API exposure forbidden")

    print("=" * 72)
    print("STEP 35 HISTORICAL SITE EVENT PRODUCTION CONSUMPTION PLAN")
    print("=" * 72)
    print("Authorized semantic TRUE plan: PASS")
    print("Authorized semantic FALSE plan: PASS")
    print("UNKNOWN / ineligible / unauthorized fail-closed: PASS")
    print("Authorization boundary / semantic alignment guards: PASS")
    print("Planned != executed: PASS")
    print("SITE / Rule Engine mutation: NONE")
    print("Production wiring / runtime registration: NONE")
    print("Historical producer auto-run / public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
