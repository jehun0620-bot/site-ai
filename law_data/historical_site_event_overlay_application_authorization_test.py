from dataclasses import replace

from law_data.historical_site_event_overlay_application_authorization import (
    authorize_historical_site_event_overlay_application,
)
from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    build_historical_site_event_provenance_preserving_overlay_contract,
)


CLASSIFICATION = "STEP45_HISTORICAL_SITE_EVENT_PROVENANCE_PRESERVING_OVERLAY_APPLICATION_AUTHORIZATION_BOUNDARY_RECONCILED"


def _contract(state: str = "TRUE"):
    return build_historical_site_event_provenance_preserving_overlay_contract(
        "테스트 역사조건",
        {
            "name": "테스트 역사조건",
            "type": "SITE_HISTORY",
            "state": state,
            "confidence": "HIGH",
            "source": "STEP45_TEST_HISTORICAL_SOURCE",
            "resolution": "TEST_RESOLUTION",
            "evaluation": {"verified": True},
            "evidence": {"document": "TEST_NOTICE"},
        },
    )


def main() -> None:
    for state in ("TRUE", "FALSE", "UNKNOWN"):
        result = authorize_historical_site_event_overlay_application(_contract(state))
        assert result.overlay_application_authorized is True
        assert result.authorized_registry_condition["type"] == "SITE_HISTORY"
        assert result.authorized_registry_condition["state"] == state
        assert result.authorized_registry_condition["source"] == "RUNTIME_HISTORICAL_SITE_EVENT"
        assert result.authorized_registry_condition["historical_source"] == "STEP45_TEST_HISTORICAL_SOURCE"
        assert result.authorized_registry_condition["runtime_source"] == "STEP45_TEST_HISTORICAL_SOURCE"

    valid_contract = _contract("TRUE")

    wrong_boundary = replace(valid_contract, boundary="OTHER_BOUNDARY")
    assert authorize_historical_site_event_overlay_application(wrong_boundary).overlay_application_authorized is False

    not_ready = replace(valid_contract, contract_ready=False)
    assert authorize_historical_site_event_overlay_application(not_ready).overlay_application_authorized is False

    bad_type_candidate = dict(valid_contract.registry_condition_candidate)
    bad_type_candidate["type"] = "SITE_SPATIAL"
    bad_type = replace(valid_contract, registry_condition_candidate=bad_type_candidate)
    assert authorize_historical_site_event_overlay_application(bad_type).overlay_application_authorized is False

    bad_state_candidate = dict(valid_contract.registry_condition_candidate)
    bad_state_candidate["state"] = "TRUE_CANDIDATE"
    bad_state = replace(valid_contract, registry_condition_candidate=bad_state_candidate)
    assert authorize_historical_site_event_overlay_application(bad_state).overlay_application_authorized is False

    bad_source_candidate = dict(valid_contract.registry_condition_candidate)
    bad_source_candidate["source"] = "RUNTIME_SPATIAL_CONDITION"
    bad_source = replace(valid_contract, registry_condition_candidate=bad_source_candidate)
    assert authorize_historical_site_event_overlay_application(bad_source).overlay_application_authorized is False

    lost_original_candidate = dict(valid_contract.registry_condition_candidate)
    lost_original_candidate["historical_source"] = ""
    lost_original = replace(valid_contract, registry_condition_candidate=lost_original_candidate)
    assert authorize_historical_site_event_overlay_application(lost_original).overlay_application_authorized is False

    broken_diagnostic = replace(valid_contract, provenance_family_preserved=False)
    assert authorize_historical_site_event_overlay_application(broken_diagnostic).overlay_application_authorized is False

    missing = authorize_historical_site_event_overlay_application(None)
    assert missing.overlay_application_authorized is False

    results = [
        authorize_historical_site_event_overlay_application(_contract("TRUE")),
        authorize_historical_site_event_overlay_application(_contract("FALSE")),
        authorize_historical_site_event_overlay_application(_contract("UNKNOWN")),
        authorize_historical_site_event_overlay_application(wrong_boundary),
        authorize_historical_site_event_overlay_application(not_ready),
        authorize_historical_site_event_overlay_application(bad_type),
        authorize_historical_site_event_overlay_application(bad_state),
        authorize_historical_site_event_overlay_application(bad_source),
        authorize_historical_site_event_overlay_application(lost_original),
        authorize_historical_site_event_overlay_application(broken_diagnostic),
        missing,
    ]
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
    print("STEP 45 HISTORICAL SITE EVENT OVERLAY APPLICATION AUTHORIZATION")
    print("=" * 72)
    print("Historical TRUE overlay authorization: PASS")
    print("Historical FALSE overlay authorization: PASS")
    print("Historical UNKNOWN overlay authorization: PASS")
    print("Boundary / contract readiness guards: PASS")
    print("Historical type / state / provenance guards: PASS")
    print("Overlay authorized != SITE registry overlay: PASS")
    print("apply_site_registry / Rule Engine evaluation: NONE")
    print("Builder / production wiring / runtime registration / API: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
