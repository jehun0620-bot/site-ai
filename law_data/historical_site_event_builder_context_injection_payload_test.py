from dataclasses import replace

from law_data.historical_site_event_builder_context_injection_authorization import (
    HistoricalSiteEventBuilderContextInjectionAuthorization,
)
from law_data.historical_site_event_builder_context_injection_payload import (
    prepare_historical_site_event_builder_context_injection_payload,
)


CLASSIFICATION = "STEP42_HISTORICAL_SITE_EVENT_BUILDER_CONTEXT_INJECTION_PAYLOAD_BOUNDARY_RECONCILED"


def _authorization(state: str = "TRUE") -> HistoricalSiteEventBuilderContextInjectionAuthorization:
    return HistoricalSiteEventBuilderContextInjectionAuthorization(
        boundary="HISTORICAL_SITE_EVENT_BUILDER_CONTEXT_INJECTION_AUTHORIZATION",
        target_injection_point="SITE_ANALYSIS_BUILDER_SITE_CONDITION_CONTEXT",
        merge_present=True,
        merge_boundary_matched=True,
        merge_ready=True,
        merged_context_present=True,
        historical_condition_name_present=True,
        historical_condition_preserved=True,
        no_condition_name_collision=True,
        merge_contract_aligned=True,
        missing_gates=(),
        builder_injection_authorized=True,
        authorized_merged_context={
            "기존 공간조건": {
                "name": "기존 공간조건",
                "type": "SITE_SPATIAL",
                "state": "TRUE",
            },
            "테스트 역사조건": {
                "name": "테스트 역사조건",
                "type": "SITE_HISTORY",
                "state": state,
                "confidence": "HIGH",
                "source": "STEP42_TEST",
            },
        },
    )


def main() -> None:
    true_auth = _authorization("TRUE")
    true_payload = prepare_historical_site_event_builder_context_injection_payload(true_auth)
    assert true_payload.injection_ready is True
    assert true_payload.site_condition_context_payload["테스트 역사조건"]["state"] == "TRUE"

    false_auth = _authorization("FALSE")
    false_payload = prepare_historical_site_event_builder_context_injection_payload(false_auth)
    assert false_payload.injection_ready is True
    assert false_payload.site_condition_context_payload["테스트 역사조건"]["state"] == "FALSE"

    unauthorized = replace(true_auth, builder_injection_authorized=False)
    assert prepare_historical_site_event_builder_context_injection_payload(unauthorized).injection_ready is False

    wrong_boundary = replace(true_auth, boundary="OTHER_BOUNDARY")
    assert prepare_historical_site_event_builder_context_injection_payload(wrong_boundary).injection_ready is False

    wrong_target = replace(true_auth, target_injection_point="OTHER_TARGET")
    assert prepare_historical_site_event_builder_context_injection_payload(wrong_target).injection_ready is False

    empty_context = replace(true_auth, authorized_merged_context={})
    empty_payload = prepare_historical_site_event_builder_context_injection_payload(empty_context)
    assert empty_payload.injection_ready is False
    assert empty_payload.site_condition_context_payload == {}

    broken_contract = replace(true_auth, historical_condition_preserved=False)
    assert prepare_historical_site_event_builder_context_injection_payload(broken_contract).injection_ready is False

    missing_auth = prepare_historical_site_event_builder_context_injection_payload(None)
    assert missing_auth.injection_ready is False

    for result in (
        true_payload,
        false_payload,
        prepare_historical_site_event_builder_context_injection_payload(unauthorized),
        prepare_historical_site_event_builder_context_injection_payload(wrong_boundary),
        prepare_historical_site_event_builder_context_injection_payload(wrong_target),
        empty_payload,
        prepare_historical_site_event_builder_context_injection_payload(broken_contract),
        missing_auth,
    ):
        data = result.to_dict()
        assert data["builder_argument_supplied"] is False
        assert data["site_analysis_builder_modified"] is False
        assert data["site_condition_context_injected"] is False
        assert data["rule_engine_input_consumed"] is False
        assert data["site_registry_overlaid"] is False
        assert data["site_state_mutated"] is False
        assert data["rule_engine_state_mutated"] is False
        assert data["rule_evaluation_executed"] is False
        assert data["rule_applicability_changed"] is False
        assert data["builder_wiring_applied"] is False
        assert data["production_wiring_applied"] is False
        assert data["runtime_registered"] is False
        assert data["runtime_registry_mutated"] is False
        assert data["historical_producer_auto_run"] is False
        assert data["public_api_exposed"] is False

    print("=" * 72)
    print("STEP 42 HISTORICAL SITE EVENT BUILDER CONTEXT INJECTION PAYLOAD")
    print("=" * 72)
    print("Authorized semantic TRUE payload: PASS")
    print("Authorized semantic FALSE payload: PASS")
    print("Unauthorized / wrong target / malformed fail-closed: PASS")
    print("Authorization boundary / upstream contract guards: PASS")
    print("Injection ready != builder argument supplied: PASS")
    print("SITE context injection / registry overlay / Rule Engine evaluation: NONE")
    print("Builder modification / production wiring / runtime registration: NONE")
    print("Historical producer auto-run / public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
