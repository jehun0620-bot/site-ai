from dataclasses import replace

from law_data.historical_site_event_builder_context_injection_payload import (
    HistoricalSiteEventBuilderContextInjectionPayload,
)
from law_data.historical_site_event_rule_engine_context_compatibility import (
    assess_historical_site_event_rule_engine_context_compatibility,
)


CLASSIFICATION = "STEP43_HISTORICAL_SITE_EVENT_RULE_ENGINE_CONTEXT_COMPATIBILITY_BOUNDARY_RECONCILED"


def _payload(state: str = "TRUE") -> HistoricalSiteEventBuilderContextInjectionPayload:
    return HistoricalSiteEventBuilderContextInjectionPayload(
        boundary="HISTORICAL_SITE_EVENT_BUILDER_CONTEXT_INJECTION_PAYLOAD",
        target_injection_point="SITE_ANALYSIS_BUILDER_SITE_CONDITION_CONTEXT",
        authorization_present=True,
        authorization_boundary_matched=True,
        target_injection_point_matched=True,
        builder_injection_authorized=True,
        authorized_context_present=True,
        authorization_contract_aligned=True,
        missing_gates=(),
        injection_ready=True,
        site_condition_context_payload={
            "기존 공간조건": {
                "name": "기존 공간조건",
                "type": "SITE_SPATIAL",
                "state": "TRUE",
                "source": "SPATIAL_TEST",
            },
            "테스트 역사조건": {
                "name": "테스트 역사조건",
                "type": "SITE_HISTORY",
                "state": state,
                "confidence": "HIGH",
                "source": "STEP43_TEST_HISTORICAL_SOURCE",
            },
        },
    )


def main() -> None:
    true_result = assess_historical_site_event_rule_engine_context_compatibility(_payload("TRUE"))
    assert true_result.historical_condition_present is True
    assert true_result.historical_condition_type_preserved is True
    assert true_result.historical_source_present is True
    assert true_result.current_overlay_spatial_source_marker is True
    assert true_result.historical_provenance_preservable_by_current_overlay is False
    assert true_result.historical_context_compatible is False
    assert true_result.compatibility_resolution == "BLOCKED_CURRENT_OVERLAY_SPATIAL_PROVENANCE_SEMANTICS"

    false_result = assess_historical_site_event_rule_engine_context_compatibility(_payload("FALSE"))
    assert false_result.historical_context_compatible is False
    assert false_result.compatibility_resolution == "BLOCKED_CURRENT_OVERLAY_SPATIAL_PROVENANCE_SEMANTICS"

    not_ready = replace(_payload(), injection_ready=False)
    assert assess_historical_site_event_rule_engine_context_compatibility(not_ready).historical_context_compatible is False

    wrong_boundary = replace(_payload(), boundary="OTHER_BOUNDARY")
    assert assess_historical_site_event_rule_engine_context_compatibility(wrong_boundary).historical_context_compatible is False

    no_history = replace(
        _payload(),
        site_condition_context_payload={
            "기존 공간조건": {
                "name": "기존 공간조건",
                "type": "SITE_SPATIAL",
                "state": "TRUE",
                "source": "SPATIAL_TEST",
            }
        },
    )
    assert assess_historical_site_event_rule_engine_context_compatibility(no_history).historical_context_compatible is False

    missing_source = _payload()
    bad_context = dict(missing_source.site_condition_context_payload)
    bad_history = dict(bad_context["테스트 역사조건"])
    bad_history["source"] = ""
    bad_context["테스트 역사조건"] = bad_history
    missing_source = replace(missing_source, site_condition_context_payload=bad_context)
    missing_source_result = assess_historical_site_event_rule_engine_context_compatibility(missing_source)
    assert missing_source_result.historical_source_present is False
    assert missing_source_result.historical_context_compatible is False

    missing_payload = assess_historical_site_event_rule_engine_context_compatibility(None)
    assert missing_payload.historical_context_compatible is False

    for result in (
        true_result,
        false_result,
        assess_historical_site_event_rule_engine_context_compatibility(not_ready),
        assess_historical_site_event_rule_engine_context_compatibility(wrong_boundary),
        assess_historical_site_event_rule_engine_context_compatibility(no_history),
        missing_source_result,
        missing_payload,
    ):
        data = result.to_dict()
        assert data["builder_argument_supplied"] is False
        assert data["site_analysis_builder_modified"] is False
        assert data["rule_evaluation_pipeline_modified"] is False
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
    print("STEP 43 HISTORICAL SITE EVENT RULE ENGINE CONTEXT COMPATIBILITY")
    print("=" * 72)
    print("Historical TRUE context identified: PASS")
    print("Historical FALSE context identified: PASS")
    print("Current spatial overlay provenance mismatch fail-closed: PASS")
    print("Not-ready / wrong boundary / malformed guards: PASS")
    print("Historical type / source preservation guards: PASS")
    print("Compatibility assessment != context injection: PASS")
    print("Rule Engine / builder modification and evaluation: NONE")
    print("Production wiring / runtime registration / public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
