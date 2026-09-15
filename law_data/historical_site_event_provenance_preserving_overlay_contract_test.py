from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    HISTORICAL_REGISTRY_SOURCE,
    build_historical_site_event_provenance_preserving_overlay_contract,
)


CLASSIFICATION = "STEP44_HISTORICAL_SITE_EVENT_PROVENANCE_PRESERVING_OVERLAY_CONTRACT_BOUNDARY_RECONCILED"


def _condition(state: str = "TRUE") -> dict:
    return {
        "name": "테스트 역사조건",
        "type": "SITE_HISTORY",
        "state": state,
        "confidence": "HIGH",
        "source": "STEP44_TEST_HISTORICAL_SOURCE",
        "resolution": "TEST_RESOLUTION",
        "evaluation": {"verified": True},
        "evidence": {"document": "TEST_NOTICE"},
    }


def main() -> None:
    true_contract = build_historical_site_event_provenance_preserving_overlay_contract(
        "테스트 역사조건", _condition("TRUE")
    )
    assert true_contract.contract_ready is True
    true_candidate = true_contract.registry_condition_candidate
    assert true_candidate["type"] == "SITE_HISTORY"
    assert true_candidate["state"] == "TRUE"
    assert true_candidate["source"] == HISTORICAL_REGISTRY_SOURCE
    assert true_candidate["source"] != "RUNTIME_SPATIAL_CONDITION"
    assert true_candidate["historical_source"] == "STEP44_TEST_HISTORICAL_SOURCE"
    assert true_candidate["runtime_source"] == "STEP44_TEST_HISTORICAL_SOURCE"

    false_contract = build_historical_site_event_provenance_preserving_overlay_contract(
        "테스트 역사조건", _condition("FALSE")
    )
    assert false_contract.contract_ready is True
    assert false_contract.registry_condition_candidate["state"] == "FALSE"

    unknown_contract = build_historical_site_event_provenance_preserving_overlay_contract(
        "테스트 역사조건", _condition("UNKNOWN")
    )
    assert unknown_contract.contract_ready is True
    assert unknown_contract.registry_condition_candidate["state"] == "UNKNOWN"

    wrong_type = _condition()
    wrong_type["type"] = "SITE_SPATIAL"
    assert build_historical_site_event_provenance_preserving_overlay_contract(
        "테스트 역사조건", wrong_type
    ).contract_ready is False

    missing_source = _condition()
    missing_source["source"] = ""
    assert build_historical_site_event_provenance_preserving_overlay_contract(
        "테스트 역사조건", missing_source
    ).contract_ready is False

    invalid_state = _condition("TRUE_CANDIDATE")
    assert build_historical_site_event_provenance_preserving_overlay_contract(
        "테스트 역사조건", invalid_state
    ).contract_ready is False

    empty_name = build_historical_site_event_provenance_preserving_overlay_contract("", _condition())
    assert empty_name.contract_ready is False
    assert empty_name.registry_condition_candidate == {}

    malformed = build_historical_site_event_provenance_preserving_overlay_contract(
        "테스트 역사조건", None
    )
    assert malformed.contract_ready is False
    assert malformed.registry_condition_candidate == {}

    for result in (
        true_contract,
        false_contract,
        unknown_contract,
        build_historical_site_event_provenance_preserving_overlay_contract("테스트 역사조건", wrong_type),
        build_historical_site_event_provenance_preserving_overlay_contract("테스트 역사조건", missing_source),
        build_historical_site_event_provenance_preserving_overlay_contract("테스트 역사조건", invalid_state),
        empty_name,
        malformed,
    ):
        data = result.to_dict()
        assert data["rule_evaluation_pipeline_modified"] is False
        assert data["site_analysis_builder_modified"] is False
        assert data["site_condition_context_injected"] is False
        assert data["site_registry_overlaid"] is False
        assert data["rule_engine_input_consumed"] is False
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
    print("STEP 44 HISTORICAL SITE EVENT PROVENANCE PRESERVING OVERLAY CONTRACT")
    print("=" * 72)
    print("Historical TRUE registry candidate: PASS")
    print("Historical FALSE registry candidate: PASS")
    print("Historical UNKNOWN registry candidate: PASS")
    print("Historical registry source family preserved: PASS")
    print("Original historical source retained: PASS")
    print("Wrong type / invalid state / missing source fail-closed: PASS")
    print("Overlay contract ready != SITE registry overlay: PASS")
    print("Rule Engine / builder modification and evaluation: NONE")
    print("Production wiring / runtime registration / public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
