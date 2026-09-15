"""Read-only STEP36 Rule Engine input preparation for HISTORICAL_SITE_EVENT.

This boundary prepares a minimal Rule Engine-facing condition view only after an
aligned STEP35 consumption plan. Preparation is not consumption, application,
SITE/Rule Engine mutation, production wiring, runtime registration, producer
execution, or public API exposure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_production_consumption_plan import (
    BOUNDARY_NAME as PLAN_BOUNDARY_NAME,
    TARGET_CONSUMER,
    HistoricalSiteEventProductionConsumptionPlan,
)
from law_data.production_site_condition import (
    FALSE,
    TRUE,
    ProductionSiteCondition,
    rule_engine_condition_view,
)


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_RULE_ENGINE_INPUT_ADAPTER"
HISTORICAL_RESOLUTION_TYPE = "HISTORICAL_SITE_EVENT"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"


@dataclass(frozen=True)
class HistoricalSiteEventRuleEngineInputPreparation:
    boundary: str
    shadow_present: bool
    plan_present: bool
    plan_boundary_matched: bool
    target_consumer_matched: bool
    consumption_planned: bool
    historical_shape_matched: bool
    semantic_state_consumable: bool
    plan_shadow_aligned: bool
    missing_gates: tuple[str, ...]
    input_prepared: bool
    condition_view: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "shadow_present": self.shadow_present,
            "plan_present": self.plan_present,
            "plan_boundary_matched": self.plan_boundary_matched,
            "target_consumer_matched": self.target_consumer_matched,
            "consumption_planned": self.consumption_planned,
            "historical_shape_matched": self.historical_shape_matched,
            "semantic_state_consumable": self.semantic_state_consumable,
            "plan_shadow_aligned": self.plan_shadow_aligned,
            "missing_gates": list(self.missing_gates),
            "input_prepared": self.input_prepared,
            "condition_view": dict(self.condition_view),
            "input_consumed": False,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "runtime_registry_mutated": False,
            "historical_producer_auto_run": False,
            "public_api_exposed": False,
        }


def prepare_historical_site_event_rule_engine_input(
    shadow: ProductionSiteCondition | None,
    plan: HistoricalSiteEventProductionConsumptionPlan | None,
) -> HistoricalSiteEventRuleEngineInputPreparation:
    """Prepare, but never consume, an aligned historical Rule Engine input view."""

    shadow_present = isinstance(shadow, ProductionSiteCondition)
    plan_present = isinstance(plan, HistoricalSiteEventProductionConsumptionPlan)
    plan_boundary_matched = bool(plan_present and plan.boundary == PLAN_BOUNDARY_NAME)
    target_consumer_matched = bool(
        plan_present and plan.target_consumer == TARGET_CONSUMER
    )
    consumption_planned = bool(plan_present and plan.consumption_planned is True)
    historical_shape_matched = bool(
        shadow_present
        and shadow.condition_type == HISTORICAL_CONDITION_TYPE
        and shadow.resolution_type == HISTORICAL_RESOLUTION_TYPE
    )
    semantic_state_consumable = bool(
        shadow_present and shadow.state in {TRUE, FALSE}
    )
    plan_shadow_aligned = bool(
        shadow_present
        and plan_present
        and plan.condition_name == shadow.name
        and plan.semantic_state == shadow.state
        and plan.shadow_present is True
        and plan.authorization_present is True
        and plan.authorization_granted is True
        and plan.historical_shape_matched is True
        and plan.semantic_state_consumable is True
        and plan.authorization_state_aligned is True
        and plan.authorization_shadow_aligned is True
    )

    gates = (
        ("shadow_present", shadow_present),
        ("plan_present", plan_present),
        ("plan_boundary_matched", plan_boundary_matched),
        ("target_consumer_matched", target_consumer_matched),
        ("consumption_planned", consumption_planned),
        ("historical_shape_matched", historical_shape_matched),
        ("semantic_state_consumable", semantic_state_consumable),
        ("plan_shadow_aligned", plan_shadow_aligned),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    input_prepared = not missing_gates
    condition_view = rule_engine_condition_view(shadow) if input_prepared else {}

    return HistoricalSiteEventRuleEngineInputPreparation(
        boundary=BOUNDARY_NAME,
        shadow_present=shadow_present,
        plan_present=plan_present,
        plan_boundary_matched=plan_boundary_matched,
        target_consumer_matched=target_consumer_matched,
        consumption_planned=consumption_planned,
        historical_shape_matched=historical_shape_matched,
        semantic_state_consumable=semantic_state_consumable,
        plan_shadow_aligned=plan_shadow_aligned,
        missing_gates=missing_gates,
        input_prepared=input_prepared,
        condition_view=condition_view,
    )
