from dataclasses import replace

from law_data.historical_site_event_production_application_adapter import (
    adapt_historical_site_event_production_application_shadow,
)
from law_data.historical_site_event_production_consumption_authorization import (
    assess_historical_site_event_production_consumption_authorization,
)
from law_data.historical_site_event_production_consumption_plan import (
    plan_historical_site_event_production_consumption,
)
from law_data.historical_site_event_rule_engine_input_adapter import (
    prepare_historical_site_event_rule_engine_input,
)
from law_data.historical_site_event_final_resolution import (
    HistoricalSiteEventFinalResolutionAssessment,
)
from law_data.historical_site_event_production_consumption_eligibility import (
    HistoricalSiteEventProductionConsumptionEligibilityAssessment,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile


CLASSIFICATION = "STEP36_HISTORICAL_SITE_EVENT_RULE_ENGINE_INPUT_ADAPTER_BOUNDARY_RECONCILED"


def _upstream(state: str):
    profile = RegulationResolutionProfile(
        name="테스트 역사조건",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        standard_code=None,
        site_promotion_allowed=True,
        production_registration_allowed=True,
        runtime_registration_allowed=True,
    )
    final = HistoricalSiteEventFinalResolutionAssessment(
        boundary="HISTORICAL_SITE_EVENT_FINAL_RESOLUTION",
        profile_present=True,
        profile_name=profile.name,
        historical_resolution_type_matched=True,
        historical_condition_type_matched=True,
        candidate_assessment_present=True,
        candidate_profile_aligned=True,
        candidate_conflict_detected=False,
        final_resolution_candidate=f"{state}_CANDIDATE",
        missing_gates=(),
        resolution=state,
    )
    eligibility = HistoricalSiteEventProductionConsumptionEligibilityAssessment(
        boundary="HISTORICAL_SITE_EVENT_PRODUCTION_CONSUMPTION_ELIGIBILITY",
        profile_present=True,
        profile_name=profile.name,
        historical_resolution_type_matched=True,
        historical_condition_type_matched=True,
        final_resolution_assessment_present=True,
        final_resolution_profile_aligned=True,
        semantic_resolution=state,
        semantic_resolution_consumable=True,
        site_promotion_allowed=True,
        production_registration_allowed=True,
        runtime_registration_allowed=True,
        missing_gates=(),
        production_consumption_eligible=True,
    )
    shadow = adapt_historical_site_event_production_application_shadow(
        profile,
        final,
        eligibility,
        confidence="HIGH",
        source="STEP36_TEST",
    )
    authorization = assess_historical_site_event_production_consumption_authorization(shadow)
    plan = plan_historical_site_event_production_consumption(shadow, authorization)
    return shadow, plan


def main() -> None:
    true_shadow, true_plan = _upstream("TRUE")
    true_result = prepare_historical_site_event_rule_engine_input(true_shadow, true_plan)
    assert true_result.input_prepared is True
    assert true_result.condition_view["name"] == true_shadow.name
    assert true_result.condition_view["state"] == "TRUE"
    assert true_result.condition_view["type"] == "SITE_HISTORY"

    false_shadow, false_plan = _upstream("FALSE")
    false_result = prepare_historical_site_event_rule_engine_input(false_shadow, false_plan)
    assert false_result.input_prepared is True
    assert false_result.condition_view["state"] == "FALSE"

    unplanned = replace(true_plan, consumption_planned=False)
    unplanned_result = prepare_historical_site_event_rule_engine_input(true_shadow, unplanned)
    assert unplanned_result.input_prepared is False
    assert unplanned_result.condition_view == {}

    wrong_target = replace(true_plan, target_consumer="OTHER_CONSUMER")
    wrong_target_result = prepare_historical_site_event_rule_engine_input(true_shadow, wrong_target)
    assert wrong_target_result.input_prepared is False

    wrong_state = replace(true_plan, semantic_state="FALSE")
    wrong_state_result = prepare_historical_site_event_rule_engine_input(true_shadow, wrong_state)
    assert wrong_state_result.input_prepared is False

    wrong_name = replace(true_plan, condition_name="다른조건")
    wrong_name_result = prepare_historical_site_event_rule_engine_input(true_shadow, wrong_name)
    assert wrong_name_result.input_prepared is False

    missing_result = prepare_historical_site_event_rule_engine_input(None, None)
    assert missing_result.input_prepared is False
    assert missing_result.condition_view == {}

    for result in (
        true_result,
        false_result,
        unplanned_result,
        wrong_target_result,
        wrong_state_result,
        wrong_name_result,
        missing_result,
    ):
        data = result.to_dict()
        assert data["input_consumed"] is False
        assert data["site_state_mutated"] is False
        assert data["rule_engine_state_mutated"] is False
        assert data["production_wiring_applied"] is False
        assert data["runtime_registered"] is False
        assert data["runtime_registry_mutated"] is False
        assert data["historical_producer_auto_run"] is False
        assert data["public_api_exposed"] is False

    print("=" * 72)
    print("STEP 36 HISTORICAL SITE EVENT RULE ENGINE INPUT ADAPTER")
    print("=" * 72)
    print("Planned semantic TRUE input preparation: PASS")
    print("Planned semantic FALSE input preparation: PASS")
    print("Unplanned / missing fail-closed: PASS")
    print("Target / condition / semantic alignment guards: PASS")
    print("Prepared != consumed: PASS")
    print("SITE / Rule Engine mutation: NONE")
    print("Production wiring / runtime registration: NONE")
    print("Historical producer auto-run / public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
