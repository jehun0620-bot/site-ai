"""Contract test for bridging promotion execution into the existing historical lane."""
from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
from law_data.historical_site_event_rule_engine_registry_adapter import (
    adapt_historical_site_event_rule_engine_registry,
)
from law_data.historical_site_event_site_truth_promotion_executor import (
    BOUNDARY_NAME as EXECUTOR_BOUNDARY,
    EXECUTED,
    HistoricalSiteEventSiteTruthPromotionExecution,
)
from law_data.historical_site_event_site_truth_promotion_rule_input_bridge import (
    READY,
    REJECTED,
    bridge_historical_site_event_site_truth_promotion_rule_input,
)

PNU = "1168010300100120000"
CONDITION = "TEST_HISTORICAL_CONDITION"


def execution():
    promoted = {
        "type": "SITE",
        "state": "FALSE",
        "confidence": "HIGH",
        "source": PROVENANCE,
        "runtime": True,
        "pnu": PNU,
        "historical": True,
    }
    return HistoricalSiteEventSiteTruthPromotionExecution(
        boundary=EXECUTOR_BOUNDARY,
        status=EXECUTED,
        authorization_present=True,
        authorization_boundary_matched=True,
        promotion_authorized=True,
        bound_pnu=PNU,
        bound_condition=CONDITION,
        bound_state="FALSE",
        promoted_condition_present=True,
        promoted_condition=promoted,
        missing_gates=(),
        execution_succeeded=True,
    )


def main():
    executed = execution()
    assert executed.executed

    good = bridge_historical_site_event_site_truth_promotion_rule_input(executed)
    assert good.status == READY
    assert good.ready
    assert good.historical_rule_input["channel"] == CHANNEL
    assert good.historical_rule_input["provenance"] == PROVENANCE
    assert good.historical_rule_input["repairs"] == [
        {
            "condition": CONDITION,
            "after": "FALSE",
            "new_confidence": "HIGH",
            "new_source": PROVENANCE,
            "pnu": PNU,
        }
    ]
    assert not good.site_registry_mutated
    assert not good.registry_adapter_called
    assert not good.collision_policy_called
    assert not good.rule_engine_called
    assert not good.builder_modified
    assert not good.runtime_registered
    assert not good.public_api_exposed

    # The output must already fit the existing historical registry adapter.
    adapted = adapt_historical_site_event_rule_engine_registry(good.historical_rule_input)
    assert adapted.registry_ready
    assert adapted.historical_site_registry[CONDITION] == {
        "state": "FALSE",
        "confidence": "HIGH",
        "source": PROVENANCE,
    }

    wrong_pnu = bridge_historical_site_event_site_truth_promotion_rule_input(
        replace(executed, bound_pnu="11680")
    )
    assert wrong_pnu.status == REJECTED
    assert not wrong_pnu.ready
    assert "pnu_valid" in wrong_pnu.missing_gates

    wrong_state = bridge_historical_site_event_site_truth_promotion_rule_input(
        replace(executed, bound_state="UNKNOWN")
    )
    assert wrong_state.status == REJECTED
    assert not wrong_state.ready
    assert "state_valid" in wrong_state.missing_gates

    wrong_promoted_pnu = bridge_historical_site_event_site_truth_promotion_rule_input(
        replace(executed, promoted_condition={**executed.promoted_condition, "pnu": "1168010300100130000"})
    )
    assert wrong_promoted_pnu.status == REJECTED
    assert not wrong_promoted_pnu.ready
    assert "promoted_condition_aligned" in wrong_promoted_pnu.missing_gates

    wrong_source = bridge_historical_site_event_site_truth_promotion_rule_input(
        replace(executed, promoted_condition={**executed.promoted_condition, "source": "OTHER"})
    )
    assert wrong_source.status == REJECTED
    assert not wrong_source.ready
    assert "provenance_preserved" in wrong_source.missing_gates

    unauthorized = bridge_historical_site_event_site_truth_promotion_rule_input(
        replace(executed, execution_succeeded=False)
    )
    assert unauthorized.status == REJECTED
    assert not unauthorized.ready
    assert "execution_succeeded" in unauthorized.missing_gates

    print("HISTORICAL_SITE_EVENT_SITE_TRUTH_PROMOTION_RULE_INPUT_BRIDGE_CONTRACT_PASS")


if __name__ == "__main__":
    main()
