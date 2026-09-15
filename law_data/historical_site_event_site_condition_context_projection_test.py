from dataclasses import replace

from law_data.historical_site_event_rule_engine_consumption_package import (
    HistoricalSiteEventRuleEngineConsumptionPackage,
)
from law_data.historical_site_event_site_condition_context_projection import (
    project_historical_site_event_site_condition_context,
)


CLASSIFICATION = "STEP39_HISTORICAL_SITE_EVENT_SITE_CONDITION_CONTEXT_PROJECTION_BOUNDARY_RECONCILED"


def _package(state: str) -> HistoricalSiteEventRuleEngineConsumptionPackage:
    view = {
        "name": "테스트 역사조건",
        "type": "SITE_HISTORY",
        "state": state,
        "confidence": "HIGH",
        "source": "STEP39_TEST",
    }
    return HistoricalSiteEventRuleEngineConsumptionPackage(
        boundary="HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_PACKAGE",
        target_consumer="RULE_ENGINE_SITE_CONDITION",
        authorization_present=True,
        authorization_boundary_matched=True,
        authorization_granted=True,
        condition_view_present=True,
        condition_name="테스트 역사조건",
        historical_condition_type_matched=True,
        semantic_state=state,
        semantic_state_consumable=True,
        authorization_contract_aligned=True,
        missing_gates=(),
        consumption_ready=True,
        condition_view=view,
    )


def main() -> None:
    true_package = _package("TRUE")
    true_projection = project_historical_site_event_site_condition_context(true_package)
    assert true_projection.context_projection_ready is True
    assert true_projection.site_condition_context_projection["테스트 역사조건"]["state"] == "TRUE"

    false_package = _package("FALSE")
    false_projection = project_historical_site_event_site_condition_context(false_package)
    assert false_projection.context_projection_ready is True
    assert false_projection.site_condition_context_projection["테스트 역사조건"]["state"] == "FALSE"

    not_ready = replace(true_package, consumption_ready=False)
    not_ready_projection = project_historical_site_event_site_condition_context(not_ready)
    assert not_ready_projection.context_projection_ready is False
    assert not_ready_projection.site_condition_context_projection == {}

    wrong_boundary = replace(true_package, boundary="OTHER_BOUNDARY")
    wrong_boundary_projection = project_historical_site_event_site_condition_context(wrong_boundary)
    assert wrong_boundary_projection.context_projection_ready is False

    wrong_target = replace(true_package, target_consumer="OTHER_CONSUMER")
    wrong_target_projection = project_historical_site_event_site_condition_context(wrong_target)
    assert wrong_target_projection.context_projection_ready is False

    wrong_name = replace(
        true_package,
        condition_view={**true_package.condition_view, "name": "다른조건"},
    )
    wrong_name_projection = project_historical_site_event_site_condition_context(wrong_name)
    assert wrong_name_projection.context_projection_ready is False

    unknown = replace(
        true_package,
        semantic_state="UNKNOWN",
        condition_view={**true_package.condition_view, "state": "UNKNOWN"},
    )
    unknown_projection = project_historical_site_event_site_condition_context(unknown)
    assert unknown_projection.context_projection_ready is False

    wrong_type = replace(
        true_package,
        condition_view={**true_package.condition_view, "type": "SITE"},
    )
    wrong_type_projection = project_historical_site_event_site_condition_context(wrong_type)
    assert wrong_type_projection.context_projection_ready is False

    broken_contract = replace(true_package, authorization_contract_aligned=False)
    broken_contract_projection = project_historical_site_event_site_condition_context(broken_contract)
    assert broken_contract_projection.context_projection_ready is False

    missing_projection = project_historical_site_event_site_condition_context(None)
    assert missing_projection.context_projection_ready is False

    for projection in (
        true_projection,
        false_projection,
        not_ready_projection,
        wrong_boundary_projection,
        wrong_target_projection,
        wrong_name_projection,
        unknown_projection,
        wrong_type_projection,
        broken_contract_projection,
        missing_projection,
    ):
        data = projection.to_dict()
        assert data["site_condition_context_injected"] is False
        assert data["rule_engine_input_consumed"] is False
        assert data["site_registry_overlaid"] is False
        assert data["site_state_mutated"] is False
        assert data["rule_engine_state_mutated"] is False
        assert data["rule_evaluation_executed"] is False
        assert data["builder_wiring_applied"] is False
        assert data["production_wiring_applied"] is False
        assert data["runtime_registered"] is False
        assert data["runtime_registry_mutated"] is False
        assert data["historical_producer_auto_run"] is False
        assert data["public_api_exposed"] is False

    print("=" * 72)
    print("STEP 39 HISTORICAL SITE EVENT SITE CONDITION CONTEXT PROJECTION")
    print("=" * 72)
    print("Consumption-ready semantic TRUE projection: PASS")
    print("Consumption-ready semantic FALSE projection: PASS")
    print("Not-ready / UNKNOWN / malformed fail-closed: PASS")
    print("Package boundary / target / identity / contract guards: PASS")
    print("Projection ready != context injected: PASS")
    print("SITE registry overlay / Rule Engine evaluation: NONE")
    print("Builder / production wiring / runtime registration: NONE")
    print("Historical producer auto-run / public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
