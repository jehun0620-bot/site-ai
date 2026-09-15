from dataclasses import replace

from law_data.historical_site_event_overlay_application_authorization import (
    authorize_historical_site_event_overlay_application,
)
from law_data.historical_site_event_overlay_execution_package import (
    EXECUTION_TARGET,
    package_historical_site_event_overlay_execution,
)
from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    build_historical_site_event_provenance_preserving_overlay_contract,
)


CLASSIFICATION = "STEP46_HISTORICAL_SITE_EVENT_OVERLAY_EXECUTION_PACKAGE_BOUNDARY_RECONCILED"


def _authorization(state: str = "TRUE"):
    contract = build_historical_site_event_provenance_preserving_overlay_contract(
        "테스트 역사조건",
        {
            "type": "SITE_HISTORY",
            "state": state,
            "confidence": "HIGH",
            "source": "STEP46_TEST_HISTORICAL_SOURCE",
            "resolution": "TEST_RESOLUTION",
            "evaluation": {"verified": True},
            "evidence": {"document": "TEST_NOTICE"},
        },
    )
    return authorize_historical_site_event_overlay_application(contract)


def main() -> None:
    true_package = package_historical_site_event_overlay_execution(
        "테스트 역사조건", _authorization("TRUE")
    )
    assert true_package.execution_ready is True
    assert true_package.execution_target == EXECUTION_TARGET
    assert true_package.condition_name == "테스트 역사조건"
    assert true_package.registry_condition["type"] == "SITE_HISTORY"
    assert true_package.registry_condition["state"] == "TRUE"
    assert true_package.registry_condition["source"] == "RUNTIME_HISTORICAL_SITE_EVENT"

    false_package = package_historical_site_event_overlay_execution(
        "테스트 역사조건", _authorization("FALSE")
    )
    assert false_package.execution_ready is True
    assert false_package.registry_condition["state"] == "FALSE"

    unknown_package = package_historical_site_event_overlay_execution(
        "테스트 역사조건", _authorization("UNKNOWN")
    )
    assert unknown_package.execution_ready is True
    assert unknown_package.registry_condition["state"] == "UNKNOWN"

    unauthorized = replace(
        _authorization(),
        overlay_application_authorized=False,
        authorized_registry_condition={},
    )
    assert package_historical_site_event_overlay_execution(
        "테스트 역사조건", unauthorized
    ).execution_ready is False

    wrong_boundary = replace(_authorization(), boundary="OTHER_BOUNDARY")
    assert package_historical_site_event_overlay_execution(
        "테스트 역사조건", wrong_boundary
    ).execution_ready is False

    empty_name = package_historical_site_event_overlay_execution("", _authorization())
    assert empty_name.execution_ready is False
    assert empty_name.condition_name == ""
    assert empty_name.registry_condition == {}

    broken_candidate_auth = _authorization()
    broken_candidate = dict(broken_candidate_auth.authorized_registry_condition)
    broken_candidate["source"] = "RUNTIME_SPATIAL_CONDITION"
    broken_candidate_auth = replace(
        broken_candidate_auth,
        authorized_registry_condition=broken_candidate,
    )
    assert package_historical_site_event_overlay_execution(
        "테스트 역사조건", broken_candidate_auth
    ).execution_ready is False

    broken_contract = replace(_authorization(), contract_diagnostics_aligned=False)
    assert package_historical_site_event_overlay_execution(
        "테스트 역사조건", broken_contract
    ).execution_ready is False

    missing_auth = package_historical_site_event_overlay_execution("테스트 역사조건", None)
    assert missing_auth.execution_ready is False

    results = (
        true_package,
        false_package,
        unknown_package,
        package_historical_site_event_overlay_execution("테스트 역사조건", unauthorized),
        package_historical_site_event_overlay_execution("테스트 역사조건", wrong_boundary),
        empty_name,
        package_historical_site_event_overlay_execution("테스트 역사조건", broken_candidate_auth),
        package_historical_site_event_overlay_execution("테스트 역사조건", broken_contract),
        missing_auth,
    )
    for result in results:
        data = result.to_dict()
        assert data["overlay_application_executed"] is False
        assert data["site_registry_overlaid"] is False
        assert data["apply_site_registry_called"] is False
        assert data["rule_evaluation_pipeline_modified"] is False
        assert data["site_analysis_builder_modified"] is False
        assert data["site_condition_context_injected"] is False
        assert data["rule_engine_input_consumed"] is False
        assert data["site_state_mutated"] is False
        assert data["rule_engine_state_mutated"] is False
        assert data["rule_evaluation_executed"] is False
        assert data["rule_applicability_recalculated"] is False
        assert data["rule_applicability_changed"] is False
        assert data["builder_wiring_applied"] is False
        assert data["production_wiring_applied"] is False
        assert data["runtime_registered"] is False
        assert data["runtime_registry_mutated"] is False
        assert data["historical_producer_auto_run"] is False
        assert data["public_api_exposed"] is False

    print("=" * 72)
    print("STEP 46 HISTORICAL SITE EVENT OVERLAY EXECUTION PACKAGE")
    print("=" * 72)
    print("Historical TRUE execution package: PASS")
    print("Historical FALSE execution package: PASS")
    print("Historical UNKNOWN execution package: PASS")
    print("Authorization / boundary / condition-name guards: PASS")
    print("Historical type / state / provenance guards: PASS")
    print("Execution ready != SITE registry overlay: PASS")
    print("apply_site_registry / Rule Engine evaluation: NONE")
    print("Builder / production wiring / runtime registration / API: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
