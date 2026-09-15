"""STEP38 non-executing Rule Engine consumption package for HISTORICAL_SITE_EVENT.

The package normalizes a successful STEP37 authorization into one immutable
Rule Engine consumption-ready contract. Ready does not mean consumed: this
module never injects site_condition_context, overlays the SITE registry,
evaluates rules, wires builder/service/orchestrator, registers runtime state,
auto-runs a historical producer, or exposes a public API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_rule_engine_consumption_authorization import (
    BOUNDARY_NAME as AUTHORIZATION_BOUNDARY_NAME,
    TARGET_CONSUMER,
    HistoricalSiteEventRuleEngineConsumptionAuthorization,
)
from law_data.production_site_condition import FALSE, TRUE


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_PACKAGE"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"


@dataclass(frozen=True)
class HistoricalSiteEventRuleEngineConsumptionPackage:
    boundary: str
    target_consumer: str
    authorization_present: bool
    authorization_boundary_matched: bool
    authorization_granted: bool
    condition_view_present: bool
    condition_name: str
    historical_condition_type_matched: bool
    semantic_state: str
    semantic_state_consumable: bool
    authorization_contract_aligned: bool
    missing_gates: tuple[str, ...]
    consumption_ready: bool
    condition_view: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "target_consumer": self.target_consumer,
            "authorization_present": self.authorization_present,
            "authorization_boundary_matched": self.authorization_boundary_matched,
            "authorization_granted": self.authorization_granted,
            "condition_view_present": self.condition_view_present,
            "condition_name": self.condition_name,
            "historical_condition_type_matched": self.historical_condition_type_matched,
            "semantic_state": self.semantic_state,
            "semantic_state_consumable": self.semantic_state_consumable,
            "authorization_contract_aligned": self.authorization_contract_aligned,
            "missing_gates": list(self.missing_gates),
            "consumption_ready": self.consumption_ready,
            "condition_view": dict(self.condition_view),
            "rule_engine_input_consumed": False,
            "site_condition_context_injected": False,
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


def package_historical_site_event_rule_engine_consumption(
    authorization: HistoricalSiteEventRuleEngineConsumptionAuthorization | None,
) -> HistoricalSiteEventRuleEngineConsumptionPackage:
    """Build a fail-closed, non-executing package from STEP37 authorization."""

    authorization_present = isinstance(
        authorization,
        HistoricalSiteEventRuleEngineConsumptionAuthorization,
    )
    authorization_boundary_matched = bool(
        authorization_present and authorization.boundary == AUTHORIZATION_BOUNDARY_NAME
    )
    authorization_granted = bool(
        authorization_present
        and authorization.rule_engine_consumption_authorized is True
    )
    view = dict(authorization.authorized_condition_view) if authorization_present else {}
    condition_view_present = bool(view)
    condition_name = str(view.get("name") or "").strip()
    historical_condition_type_matched = view.get("type") == HISTORICAL_CONDITION_TYPE
    semantic_state = str(view.get("state") or "").strip()
    semantic_state_consumable = semantic_state in {TRUE, FALSE}
    authorization_contract_aligned = bool(
        authorization_present
        and authorization.preparation_present is True
        and authorization.preparation_boundary_matched is True
        and authorization.input_prepared is True
        and authorization.condition_view_present is True
        and authorization.condition_identity_present is True
        and authorization.historical_condition_type_matched is True
        and authorization.semantic_state_consumable is True
        and authorization.preparation_non_consuming is True
    )

    gates = (
        ("authorization_present", authorization_present),
        ("authorization_boundary_matched", authorization_boundary_matched),
        ("authorization_granted", authorization_granted),
        ("condition_view_present", condition_view_present),
        ("condition_identity_present", bool(condition_name)),
        ("historical_condition_type_matched", historical_condition_type_matched),
        ("semantic_state_consumable", semantic_state_consumable),
        ("authorization_contract_aligned", authorization_contract_aligned),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    consumption_ready = not missing_gates

    return HistoricalSiteEventRuleEngineConsumptionPackage(
        boundary=BOUNDARY_NAME,
        target_consumer=TARGET_CONSUMER,
        authorization_present=authorization_present,
        authorization_boundary_matched=authorization_boundary_matched,
        authorization_granted=authorization_granted,
        condition_view_present=condition_view_present,
        condition_name=condition_name if consumption_ready else "",
        historical_condition_type_matched=historical_condition_type_matched,
        semantic_state=semantic_state if consumption_ready else "",
        semantic_state_consumable=semantic_state_consumable,
        authorization_contract_aligned=authorization_contract_aligned,
        missing_gates=missing_gates,
        consumption_ready=consumption_ready,
        condition_view=view if consumption_ready else {},
    )
