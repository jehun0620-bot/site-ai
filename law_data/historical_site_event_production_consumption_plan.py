"""Read-only STEP35 consumption plan boundary for HISTORICAL_SITE_EVENT.

A plan describes a future Rule Engine SITE condition consumption target. It does
not execute consumption, mutate SITE/Rule Engine state, wire production, register
runtime state, auto-run a historical producer, or expose a public API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.historical_site_event_production_consumption_authorization import (
    BOUNDARY_NAME as AUTHORIZATION_BOUNDARY_NAME,
    HistoricalSiteEventProductionConsumptionAuthorizationAssessment,
)
from law_data.production_site_condition import FALSE, TRUE, ProductionSiteCondition


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_PRODUCTION_CONSUMPTION_PLAN"
TARGET_CONSUMER = "RULE_ENGINE_SITE_CONDITION"
HISTORICAL_RESOLUTION_TYPE = "HISTORICAL_SITE_EVENT"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"


@dataclass(frozen=True)
class HistoricalSiteEventProductionConsumptionPlan:
    boundary: str
    target_consumer: str
    condition_name: str
    semantic_state: str
    shadow_present: bool
    authorization_present: bool
    authorization_boundary_matched: bool
    authorization_granted: bool
    historical_shape_matched: bool
    semantic_state_consumable: bool
    authorization_state_aligned: bool
    authorization_shadow_aligned: bool
    missing_gates: tuple[str, ...]
    consumption_planned: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "target_consumer": self.target_consumer,
            "condition_name": self.condition_name,
            "semantic_state": self.semantic_state,
            "shadow_present": self.shadow_present,
            "authorization_present": self.authorization_present,
            "authorization_boundary_matched": self.authorization_boundary_matched,
            "authorization_granted": self.authorization_granted,
            "historical_shape_matched": self.historical_shape_matched,
            "semantic_state_consumable": self.semantic_state_consumable,
            "authorization_state_aligned": self.authorization_state_aligned,
            "authorization_shadow_aligned": self.authorization_shadow_aligned,
            "missing_gates": list(self.missing_gates),
            "consumption_planned": self.consumption_planned,
            "consumption_executed": False,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "runtime_registry_mutated": False,
            "historical_producer_auto_run": False,
            "public_api_exposed": False,
        }


def plan_historical_site_event_production_consumption(
    shadow: ProductionSiteCondition | None,
    authorization: HistoricalSiteEventProductionConsumptionAuthorizationAssessment | None,
) -> HistoricalSiteEventProductionConsumptionPlan:
    """Create a non-executing plan only for an aligned STEP34 authorization."""

    shadow_present = isinstance(shadow, ProductionSiteCondition)
    authorization_present = isinstance(
        authorization,
        HistoricalSiteEventProductionConsumptionAuthorizationAssessment,
    )

    condition_name = shadow.name if shadow_present else ""
    semantic_state = shadow.state if shadow_present else "UNKNOWN"

    authorization_boundary_matched = bool(
        authorization_present and authorization.boundary == AUTHORIZATION_BOUNDARY_NAME
    )
    authorization_granted = bool(
        authorization_present
        and authorization.production_consumption_authorized is True
    )
    historical_shape_matched = bool(
        shadow_present
        and shadow.condition_type == HISTORICAL_CONDITION_TYPE
        and shadow.resolution_type == HISTORICAL_RESOLUTION_TYPE
    )
    semantic_state_consumable = semantic_state in {TRUE, FALSE}
    authorization_state_aligned = bool(
        shadow_present
        and authorization_present
        and authorization.semantic_state == semantic_state
    )
    authorization_shadow_aligned = bool(
        shadow_present
        and authorization_present
        and authorization.shadow_present is True
        and authorization.historical_resolution_type_matched is True
        and authorization.historical_condition_type_matched is True
        and authorization.production_eligible is (shadow.production_eligible is True)
        and authorization.runtime_unregistered is (shadow.runtime_registered is False)
        and authorization.step33_provenance_matched is True
        and authorization.step33_application_ready is True
        and authorization.step33_non_mutating is True
    )

    gates = (
        ("shadow_present", shadow_present),
        ("authorization_present", authorization_present),
        ("authorization_boundary_matched", authorization_boundary_matched),
        ("authorization_granted", authorization_granted),
        ("historical_shape_matched", historical_shape_matched),
        ("semantic_state_consumable", semantic_state_consumable),
        ("authorization_state_aligned", authorization_state_aligned),
        ("authorization_shadow_aligned", authorization_shadow_aligned),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)

    return HistoricalSiteEventProductionConsumptionPlan(
        boundary=BOUNDARY_NAME,
        target_consumer=TARGET_CONSUMER,
        condition_name=condition_name,
        semantic_state=semantic_state,
        shadow_present=shadow_present,
        authorization_present=authorization_present,
        authorization_boundary_matched=authorization_boundary_matched,
        authorization_granted=authorization_granted,
        historical_shape_matched=historical_shape_matched,
        semantic_state_consumable=semantic_state_consumable,
        authorization_state_aligned=authorization_state_aligned,
        authorization_shadow_aligned=authorization_shadow_aligned,
        missing_gates=missing_gates,
        consumption_planned=not missing_gates,
    )
