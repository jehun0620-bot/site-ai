from dataclasses import replace

from law_data.historical_site_event_rule_engine_consumption_authorization import (
    HistoricalSiteEventRuleEngineConsumptionAuthorization,
)
from law_data.historical_site_event_rule_engine_consumption_package import (
    package_historical_site_event_rule_engine_consumption,
)


CLASSIFICATION = "STEP38_HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_PACKAGE_BOUNDARY_RECONCILED"


def _authorization(state: str) -> HistoricalSiteEventRuleEngineConsumptionAuthorization:
    return HistoricalSiteEventRuleEngineConsumptionAuthorization(
        boundary="HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_AUTHORIZATION",
        preparation_present=True,
        preparation_boundary_matched=True,
        input_prepared=True,
        condition_view_present=True,
        condition_identity_present=True,
        historical_condition_type_matched=True,
        semantic_state_consumable=True,
        preparation_non_consuming=True,
        missing_gates=(),
        rule_engine_consumption_authorized=True,
        authorized_condition_view={
            "name": "테스트 역사조건",
            "type": "SITE_HISTORY",
            "state": state,
            "confidence": "HIGH",
            "source": "STEP38_TEST",
        },
    )


def main() -> None:
    true_authorization = _authorization("TRUE")
    true_package = package_historical_site_event_rule_engine_consumption(true_authorization)
    assert true_package.consumption_ready is True
    assert true_package.condition_name == "테스트 역사조건"
    assert true_package.semantic_state == "TRUE"
    assert true_package.condition_view["state"] == "TRUE"

    false_authorization = _authorization("FALSE")
    false_package = package_historical_site_event_rule_engine_consumption(false_authorization)
    assert false_package.consumption_ready is True
    assert false_package.semantic_state == "FALSE"

    unauthorized = replace(
        true_authorization,
        rule_engine_consumption_authorized=False,
    )
    unauthorized_package = package_historical_site_event_rule_engine_consumption(unauthorized)
    assert unauthorized_package.consumption_ready is False
    assert unauthorized_package.condition_view == {}

    wrong_boundary = replace(true_authorization, boundary="OTHER_BOUNDARY")
    wrong_boundary_package = package_historical_site_event_rule_engine_consumption(wrong_boundary)
    assert wrong_boundary_package.consumption_ready is False

    unknown = replace(
        true_authorization,
        authorized_condition_view={**true_authorization.authorized_condition_view, "state": "UNKNOWN"},
    )
    unknown_package = package_historical_site_event_rule_engine_consumption(unknown)
    assert unknown_package.consumption_ready is False

    wrong_type = replace(
        true_authorization,
        authorized_condition_view={**true_authorization.authorized_condition_view, "type": "SITE"},
    )
    wrong_type_package = package_historical_site_event_rule_engine_consumption(wrong_type)
    assert wrong_type_package.consumption_ready is False

    empty_name = replace(
        true_authorization,
        authorized_condition_view={**true_authorization.authorized_condition_view, "name": ""},
    )
    empty_name_package = package_historical_site_event_rule_engine_consumption(empty_name)
    assert empty_name_package.consumption_ready is False

    broken_contract = replace(true_authorization, preparation_non_consuming=False)
    broken_contract_package = package_historical_site_event_rule_engine_consumption(broken_contract)
    assert broken_contract_package.consumption_ready is False

    missing_package = package_historical_site_event_rule_engine_consumption(None)
    assert missing_package.consumption_ready is False

    for package in (
        true_package,
        false_package,
        unauthorized_package,
        wrong_boundary_package,
        unknown_package,
        wrong_type_package,
        empty_name_package,
        broken_contract_package,
        missing_package,
    ):
        data = package.to_dict()
        assert data["rule_engine_input_consumed"] is False
        assert data["site_condition_context_injected"] is False
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
    print("STEP 38 HISTORICAL SITE EVENT RULE ENGINE CONSUMPTION PACKAGE")
    print("=" * 72)
    print("Authorized semantic TRUE package: PASS")
    print("Authorized semantic FALSE package: PASS")
    print("Unauthorized / UNKNOWN / malformed fail-closed: PASS")
    print("Authorization boundary / contract alignment guards: PASS")
    print("Consumption ready != consumed: PASS")
    print("SITE context / registry overlay: NONE")
    print("Rule evaluation / production wiring / runtime registration: NONE")
    print("Historical producer auto-run / public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
