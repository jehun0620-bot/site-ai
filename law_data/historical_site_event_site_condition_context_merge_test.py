from dataclasses import replace

from law_data.historical_site_event_site_condition_context_merge import (
    merge_historical_site_event_site_condition_context,
)
from law_data.historical_site_event_site_condition_context_projection import (
    HistoricalSiteEventSiteConditionContextProjection,
)


CLASSIFICATION = "STEP40_HISTORICAL_SITE_EVENT_SITE_CONDITION_CONTEXT_MERGE_BOUNDARY_RECONCILED"


def _projection(name: str = "테스트 역사조건", state: str = "TRUE") -> HistoricalSiteEventSiteConditionContextProjection:
    return HistoricalSiteEventSiteConditionContextProjection(
        boundary="HISTORICAL_SITE_EVENT_SITE_CONDITION_CONTEXT_PROJECTION",
        package_present=True,
        package_boundary_matched=True,
        target_consumer_matched=True,
        consumption_ready=True,
        condition_name_present=True,
        condition_view_present=True,
        condition_name_aligned=True,
        historical_condition_type_matched=True,
        semantic_state_consumable=True,
        package_contract_aligned=True,
        missing_gates=(),
        context_projection_ready=True,
        site_condition_context_projection={
            name: {
                "name": name,
                "type": "SITE_HISTORY",
                "state": state,
                "confidence": "HIGH",
                "source": "STEP40_TEST",
            }
        },
    )


def main() -> None:
    existing = {
        "기존 공간조건": {
            "name": "기존 공간조건",
            "type": "SITE_SPATIAL",
            "state": "TRUE",
            "confidence": "HIGH",
            "source": "SPATIAL_RUNTIME",
        }
    }

    true_projection = _projection(state="TRUE")
    true_merge = merge_historical_site_event_site_condition_context(existing, true_projection)
    assert true_merge.merge_ready is True
    assert set(true_merge.merged_context_candidate) == {"기존 공간조건", "테스트 역사조건"}
    assert true_merge.merged_context_candidate["테스트 역사조건"]["state"] == "TRUE"
    assert existing.keys() == {"기존 공간조건"}

    false_projection = _projection(state="FALSE")
    false_merge = merge_historical_site_event_site_condition_context({}, false_projection)
    assert false_merge.merge_ready is True
    assert false_merge.merged_context_candidate["테스트 역사조건"]["state"] == "FALSE"

    collision_projection = _projection(name="기존 공간조건")
    collision_merge = merge_historical_site_event_site_condition_context(existing, collision_projection)
    assert collision_merge.merge_ready is False
    assert collision_merge.condition_name_collision is True
    assert collision_merge.merged_context_candidate == {}

    not_ready = replace(true_projection, context_projection_ready=False)
    not_ready_merge = merge_historical_site_event_site_condition_context(existing, not_ready)
    assert not_ready_merge.merge_ready is False

    wrong_boundary = replace(true_projection, boundary="OTHER_BOUNDARY")
    wrong_boundary_merge = merge_historical_site_event_site_condition_context(existing, wrong_boundary)
    assert wrong_boundary_merge.merge_ready is False

    malformed_projection = replace(
        true_projection,
        site_condition_context_projection={
            "조건1": {"name": "조건1"},
            "조건2": {"name": "조건2"},
        },
    )
    malformed_merge = merge_historical_site_event_site_condition_context(existing, malformed_projection)
    assert malformed_merge.merge_ready is False

    broken_contract = replace(true_projection, package_contract_aligned=False)
    broken_contract_merge = merge_historical_site_event_site_condition_context(existing, broken_contract)
    assert broken_contract_merge.merge_ready is False

    invalid_existing = merge_historical_site_event_site_condition_context(
        {"기존 공간조건": "NOT_A_MAPPING"},
        true_projection,
    )
    assert invalid_existing.merge_ready is False

    missing_projection = merge_historical_site_event_site_condition_context(existing, None)
    assert missing_projection.merge_ready is False

    for result in (
        true_merge,
        false_merge,
        collision_merge,
        not_ready_merge,
        wrong_boundary_merge,
        malformed_merge,
        broken_contract_merge,
        invalid_existing,
        missing_projection,
    ):
        data = result.to_dict()
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
    print("STEP 40 HISTORICAL SITE EVENT SITE CONDITION CONTEXT MERGE")
    print("=" * 72)
    print("Existing spatial + historical TRUE merge candidate: PASS")
    print("Empty existing + historical FALSE merge candidate: PASS")
    print("Condition-name collision fail-closed: PASS")
    print("Not-ready / malformed / contract guards: PASS")
    print("Merge ready != context injected: PASS")
    print("SITE registry overlay / Rule Engine evaluation: NONE")
    print("Builder / production wiring / runtime registration: NONE")
    print("Historical producer auto-run / public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
