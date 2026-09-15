from dataclasses import replace

from law_data.historical_site_event_rule_engine_consumption_authorization import (
    authorize_historical_site_event_rule_engine_consumption,
)
from law_data.historical_site_event_rule_engine_input_adapter import (
    HistoricalSiteEventRuleEngineInputPreparation,
)


CLASSIFICATION = "STEP37_HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_AUTHORIZATION_BOUNDARY_RECONCILED"


def _preparation(state: str) -> HistoricalSiteEventRuleEngineInputPreparation:
    return HistoricalSiteEventRuleEngineInputPreparation(
        boundary="HISTORICAL_SITE_EVENT_RULE_ENGINE_INPUT_ADAPTER",
        shadow_present=True,
        plan_present=True,
        plan_boundary_matched=True,
        target_consumer_matched=True,
        consumption_planned=True,
        historical_shape_matched=True,
        semantic_state_consumable=True,
        plan_shadow_aligned=True,
        missing_gates=(),
        input_prepared=True,
        condition_view={
            "name": "테스트 역사조건",
            "type": "SITE_HISTORY",
            "state": state,
            "confidence": "HIGH",
            "source": "STEP37_TEST",
        },
    )


def main() -> None:
    true_preparation = _preparation("TRUE")
    true_result = authorize_historical_site_event_rule_engine_consumption(true_preparation)
    assert true_result.rule_engine_consumption_authorized is True
    assert true_result.authorized_condition_view["state"] == "TRUE"

    false_preparation = _preparation("FALSE")
    false_result = authorize_historical_site_event_rule_engine_consumption(false_preparation)
    assert false_result.rule_engine_consumption_authorized is True
    assert false_result.authorized_condition_view["state"] == "FALSE"

    not_prepared = replace(true_preparation, input_prepared=False)
    not_prepared_result = authorize_historical_site_event_rule_engine_consumption(not_prepared)
    assert not_prepared_result.rule_engine_consumption_authorized is False
    assert not_prepared_result.authorized_condition_view == {}

    wrong_boundary = replace(true_preparation, boundary="OTHER_BOUNDARY")
    wrong_boundary_result = authorize_historical_site_event_rule_engine_consumption(wrong_boundary)
    assert wrong_boundary_result.rule_engine_consumption_authorized is False

    wrong_type = replace(
        true_preparation,
        condition_view={**true_preparation.condition_view, "type": "SITE"},
    )
    wrong_type_result = authorize_historical_site_event_rule_engine_consumption(wrong_type)
    assert wrong_type_result.rule_engine_consumption_authorized is False

    unknown_state = replace(
        true_preparation,
        condition_view={**true_preparation.condition_view, "state": "UNKNOWN"},
    )
    unknown_result = authorize_historical_site_event_rule_engine_consumption(unknown_state)
    assert unknown_result.rule_engine_consumption_authorized is False

    empty_name = replace(
        true_preparation,
        condition_view={**true_preparation.condition_view, "name": ""},
    )
    empty_name_result = authorize_historical_site_event_rule_engine_consumption(empty_name)
    assert empty_name_result.rule_engine_consumption_authorized is False

    broken_alignment = replace(true_preparation, plan_shadow_aligned=False)
    broken_alignment_result = authorize_historical_site_event_rule_engine_consumption(broken_alignment)
    assert broken_alignment_result.rule_engine_consumption_authorized is False

    missing_result = authorize_historical_site_event_rule_engine_consumption(None)
    assert missing_result.rule_engine_consumption_authorized is False

    for result in (
        true_result,
        false_result,
        not_prepared_result,
        wrong_boundary_result,
        wrong_type_result,
        unknown_result,
        empty_name_result,
        broken_alignment_result,
        missing_result,
    ):
        data = result.to_dict()
        assert data["rule_engine_input_consumed"] is False
        assert data["site_registry_overlaid"] is False
        assert data["site_state_mutated"] is False
        assert data["rule_engine_state_mutated"] is False
        assert data["rule_evaluation_executed"] is False
        assert data["production_wiring_applied"] is False
        assert data["runtime_registered"] is False
        assert data["runtime_registry_mutated"] is False
        assert data["historical_producer_auto_run"] is False
        assert data["public_api_exposed"] is False

    print("=" * 72)
    print("STEP 37 HISTORICAL SITE EVENT RULE ENGINE CONSUMPTION AUTHORIZATION")
    print("=" * 72)
    print("Prepared semantic TRUE authorization: PASS")
    print("Prepared semantic FALSE authorization: PASS")
    print("Unprepared / UNKNOWN / malformed fail-closed: PASS")
    print("Boundary / type / identity / alignment guards: PASS")
    print("Authorized != consumed: PASS")
    print("SITE registry / Rule Engine mutation: NONE")
    print("Rule evaluation / production wiring / runtime registration: NONE")
    print("Historical producer auto-run / public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
