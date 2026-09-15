"""Read-only STEP37 Rule Engine consumption authorization for HISTORICAL_SITE_EVENT.

Authorization confirms that a STEP36 prepared condition view may proceed to a
future Rule Engine consumer. It does not consume the input, overlay a SITE
registry, evaluate rules, wire production, register runtime state, auto-run a
historical producer, or expose a public API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_rule_engine_input_adapter import (
    BOUNDARY_NAME as INPUT_ADAPTER_BOUNDARY_NAME,
    HistoricalSiteEventRuleEngineInputPreparation,
)
from law_data.production_site_condition import FALSE, TRUE


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_AUTHORIZATION"
TARGET_CONSUMER = "RULE_ENGINE_SITE_CONDITION"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"


@dataclass(frozen=True)
class HistoricalSiteEventRuleEngineConsumptionAuthorization:
    boundary: str
    preparation_present: bool
    preparation_boundary_matched: bool
    input_prepared: bool
    condition_view_present: bool
    condition_identity_present: bool
    historical_condition_type_matched: bool
    semantic_state_consumable: bool
    preparation_non_consuming: bool
    missing_gates: tuple[str, ...]
    rule_engine_consumption_authorized: bool
    authorized_condition_view: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "target_consumer": TARGET_CONSUMER,
            "preparation_present": self.preparation_present,
            "preparation_boundary_matched": self.preparation_boundary_matched,
            "input_prepared": self.input_prepared,
            "condition_view_present": self.condition_view_present,
            "condition_identity_present": self.condition_identity_present,
            "historical_condition_type_matched": self.historical_condition_type_matched,
            "semantic_state_consumable": self.semantic_state_consumable,
            "preparation_non_consuming": self.preparation_non_consuming,
            "missing_gates": list(self.missing_gates),
            "rule_engine_consumption_authorized": self.rule_engine_consumption_authorized,
            "authorized_condition_view": dict(self.authorized_condition_view),
            "rule_engine_input_consumed": False,
            "site_registry_overlaid": False,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "rule_evaluation_executed": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "runtime_registry_mutated": False,
            "historical_producer_auto_run": False,
            "public_api_exposed": False,
        }


def authorize_historical_site_event_rule_engine_consumption(
    preparation: HistoricalSiteEventRuleEngineInputPreparation | None,
) -> HistoricalSiteEventRuleEngineConsumptionAuthorization:
    """Authorize future consumption only for a concrete aligned STEP36 result."""

    preparation_present = isinstance(
        preparation,
        HistoricalSiteEventRuleEngineInputPreparation,
    )
    preparation_boundary_matched = bool(
        preparation_present and preparation.boundary == INPUT_ADAPTER_BOUNDARY_NAME
    )
    input_prepared = bool(preparation_present and preparation.input_prepared is True)
    view = dict(preparation.condition_view) if preparation_present else {}
    condition_view_present = bool(view)
    condition_identity_present = bool(str(view.get("name") or "").strip())
    historical_condition_type_matched = view.get("type") == HISTORICAL_CONDITION_TYPE
    semantic_state_consumable = view.get("state") in {TRUE, FALSE}

    # STEP36's contract is non-consuming by construction. This gate additionally
    # requires its own successful preparation/alignment diagnostics rather than
    # authorizing an arbitrary condition-view mapping.
    preparation_non_consuming = bool(
        preparation_present
        and preparation.plan_boundary_matched is True
        and preparation.target_consumer_matched is True
        and preparation.consumption_planned is True
        and preparation.historical_shape_matched is True
        and preparation.semantic_state_consumable is True
        and preparation.plan_shadow_aligned is True
    )

    gates = (
        ("preparation_present", preparation_present),
        ("preparation_boundary_matched", preparation_boundary_matched),
        ("input_prepared", input_prepared),
        ("condition_view_present", condition_view_present),
        ("condition_identity_present", condition_identity_present),
        ("historical_condition_type_matched", historical_condition_type_matched),
        ("semantic_state_consumable", semantic_state_consumable),
        ("preparation_non_consuming", preparation_non_consuming),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    authorized = not missing_gates

    return HistoricalSiteEventRuleEngineConsumptionAuthorization(
        boundary=BOUNDARY_NAME,
        preparation_present=preparation_present,
        preparation_boundary_matched=preparation_boundary_matched,
        input_prepared=input_prepared,
        condition_view_present=condition_view_present,
        condition_identity_present=condition_identity_present,
        historical_condition_type_matched=historical_condition_type_matched,
        semantic_state_consumable=semantic_state_consumable,
        preparation_non_consuming=preparation_non_consuming,
        missing_gates=missing_gates,
        rule_engine_consumption_authorized=authorized,
        authorized_condition_view=view if authorized else {},
    )
