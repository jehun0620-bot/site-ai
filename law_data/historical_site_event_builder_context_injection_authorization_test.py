from dataclasses import replace

from law_data.historical_site_event_builder_context_injection_authorization import (
    authorize_historical_site_event_builder_context_injection,
)
from law_data.historical_site_event_site_condition_context_merge import (
    HistoricalSiteEventSiteConditionContextMerge,
)


CLASSIFICATION = "STEP41_HISTORICAL_SITE_EVENT_BUILDER_CONTEXT_INJECTION_AUTHORIZATION_BOUNDARY_RECONCILED"


def _merge(state: str = "TRUE") -> HistoricalSiteEventSiteConditionContextMerge:
    historical_name = "테스트 역사조건"
    return HistoricalSiteEventSiteConditionContextMerge(
        boundary="HISTORICAL_SITE_EVENT_SITE_CONDITION_CONTEXT_MERGE",
        existing_context_valid=True,
        projection_present=True,
        projection_boundary_matched=True,
        context_projection_ready=True,
        historical_projection_valid=True,
        historical_condition_name=historical_name,
        condition_name_collision=False,
        projection_contract_aligned=True,
        missing_gates=(),
        merge_ready=True,
        merged_context_candidate={
            "기존 공간조건": {
                "name": "기존 공간조건",
                "type": "SITE_SPATIAL",
                "state": "TRUE",
            },
            historical_name: {
                "name": historical_name,
                "type": "SITE_HISTORY",
                "state": state,
                "confidence": "HIGH",
                "source": "STEP41_TEST",
            },
        },
    )


def main() -> None:
    true_merge = _merge("TRUE")
    true_auth = authorize_historical_site_event_builder_context_injection(true_merge)
    assert true_auth.builder_injection_authorized is True
    assert true_auth.historical_condition_preserved is True
    assert true_auth.authorized_merged_context["테스트 역사조건"]["state"] == "TRUE"

    false_merge = _merge("FALSE")
    false_auth = authorize_historical_site_event_builder_context_injection(false_merge)
    assert false_auth.builder_injection_authorized is True
    assert false_auth.authorized_merged_context["테스트 역사조건"]["state"] == "FALSE"

    not_ready = replace(true_merge, merge_ready=False)
    assert authorize_historical_site_event_builder_context_injection(not_ready).builder_injection_authorized is False

    wrong_boundary = replace(true_merge, boundary="OTHER_BOUNDARY")
    assert authorize_historical_site_event_builder_context_injection(wrong_boundary).builder_injection_authorized is False

    collision = replace(true_merge, condition_name_collision=True)
    assert authorize_historical_site_event_builder_context_injection(collision).builder_injection_authorized is False

    missing_historical = replace(
        true_merge,
        merged_context_candidate={
            "기존 공간조건": true_merge.merged_context_candidate["기존 공간조건"]
        },
    )
    missing_historical_auth = authorize_historical_site_event_builder_context_injection(missing_historical)
    assert missing_historical_auth.builder_injection_authorized is False
    assert missing_historical_auth.historical_condition_preserved is False

    empty_name = replace(true_merge, historical_condition_name="")
    assert authorize_historical_site_event_builder_context_injection(empty_name).builder_injection_authorized is False

    broken_contract = replace(true_merge, projection_contract_aligned=False)
    assert authorize_historical_site_event_builder_context_injection(broken_contract).builder_injection_authorized is False

    missing_merge = authorize_historical_site_event_builder_context_injection(None)
    assert missing_merge.builder_injection_authorized is False

    for result in (
        true_auth,
        false_auth,
        authorize_historical_site_event_builder_context_injection(not_ready),
        authorize_historical_site_event_builder_context_injection(wrong_boundary),
        authorize_historical_site_event_builder_context_injection(collision),
        missing_historical_auth,
        authorize_historical_site_event_builder_context_injection(empty_name),
        authorize_historical_site_event_builder_context_injection(broken_contract),
        missing_merge,
    ):
        data = result.to_dict()
        assert data["site_analysis_builder_modified"] is False
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
    print("STEP 41 HISTORICAL SITE EVENT BUILDER CONTEXT INJECTION AUTHORIZATION")
    print("=" * 72)
    print("Merge-ready semantic TRUE authorization: PASS")
    print("Merge-ready semantic FALSE authorization: PASS")
    print("Not-ready / collision / malformed fail-closed: PASS")
    print("Merge boundary / historical preservation / contract guards: PASS")
    print("Builder injection authorized != injected: PASS")
    print("SITE registry overlay / Rule Engine evaluation: NONE")
    print("Builder modification / production wiring / runtime registration: NONE")
    print("Historical producer auto-run / public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
