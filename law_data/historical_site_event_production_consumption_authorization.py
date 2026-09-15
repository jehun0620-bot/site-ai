"""Read-only STEP34 consumption authorization boundary for HISTORICAL_SITE_EVENT.

This boundary decides only whether a STEP33 ProductionSiteCondition shadow is
safe to hand to a future production consumer. Authorization is not consumption,
SITE mutation, Rule Engine application, production wiring, runtime registration,
historical producer execution, or public API exposure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_production_application_adapter import ADAPTER_NAME
from law_data.production_site_condition import (
    FALSE,
    TRUE,
    ProductionSiteCondition,
)


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_PRODUCTION_CONSUMPTION_AUTHORIZATION"
HISTORICAL_RESOLUTION_TYPE = "HISTORICAL_SITE_EVENT"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"


@dataclass(frozen=True)
class HistoricalSiteEventProductionConsumptionAuthorizationAssessment:
    boundary: str
    shadow_present: bool
    historical_resolution_type_matched: bool
    historical_condition_type_matched: bool
    semantic_state: str
    semantic_state_consumable: bool
    production_eligible: bool
    runtime_unregistered: bool
    step33_provenance_matched: bool
    step33_application_ready: bool
    step33_non_mutating: bool
    missing_gates: tuple[str, ...]
    production_consumption_authorized: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "shadow_present": self.shadow_present,
            "historical_resolution_type_matched": self.historical_resolution_type_matched,
            "historical_condition_type_matched": self.historical_condition_type_matched,
            "semantic_state": self.semantic_state,
            "semantic_state_consumable": self.semantic_state_consumable,
            "production_eligible": self.production_eligible,
            "runtime_unregistered": self.runtime_unregistered,
            "step33_provenance_matched": self.step33_provenance_matched,
            "step33_application_ready": self.step33_application_ready,
            "step33_non_mutating": self.step33_non_mutating,
            "missing_gates": list(self.missing_gates),
            "production_consumption_authorized": self.production_consumption_authorized,
            "production_consumed": False,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "production_wiring_applied": False,
            "runtime_registry_mutated": False,
            "historical_producer_auto_run": False,
            "public_api_exposed": False,
        }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def assess_historical_site_event_production_consumption_authorization(
    shadow: ProductionSiteCondition | None,
) -> HistoricalSiteEventProductionConsumptionAuthorizationAssessment:
    """Authorize a concrete STEP33 shadow without consuming or applying it."""

    shadow_present = isinstance(shadow, ProductionSiteCondition)
    condition_type = shadow.condition_type if shadow_present else ""
    resolution_type = shadow.resolution_type if shadow_present else ""
    semantic_state = shadow.state if shadow_present else "UNKNOWN"
    production_eligible = bool(shadow_present and shadow.production_eligible is True)
    runtime_unregistered = bool(shadow_present and shadow.runtime_registered is False)

    provenance = _mapping(shadow.provenance if shadow_present else None)
    diagnostics = _mapping(shadow.diagnostics if shadow_present else None)

    step33_provenance_matched = bool(
        shadow_present
        and provenance.get("adapter") == ADAPTER_NAME
        and provenance.get("step31_boundary")
        and provenance.get("step32_boundary")
    )
    step33_application_ready = bool(
        shadow_present and diagnostics.get("application_ready") is True
    )
    step33_non_mutating = bool(
        shadow_present
        and diagnostics.get("site_state_mutated") is False
        and diagnostics.get("rule_engine_state_mutated") is False
        and diagnostics.get("production_wiring_applied") is False
        and diagnostics.get("runtime_registry_mutated") is False
        and diagnostics.get("historical_producer_auto_run") is False
        and diagnostics.get("public_api_exposed") is False
    )

    historical_resolution_type_matched = resolution_type == HISTORICAL_RESOLUTION_TYPE
    historical_condition_type_matched = condition_type == HISTORICAL_CONDITION_TYPE
    semantic_state_consumable = semantic_state in {TRUE, FALSE}

    gates = (
        ("shadow_present", shadow_present),
        ("historical_resolution_type_matched", historical_resolution_type_matched),
        ("historical_condition_type_matched", historical_condition_type_matched),
        ("semantic_state_consumable", semantic_state_consumable),
        ("production_eligible", production_eligible),
        ("runtime_unregistered", runtime_unregistered),
        ("step33_provenance_matched", step33_provenance_matched),
        ("step33_application_ready", step33_application_ready),
        ("step33_non_mutating", step33_non_mutating),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)

    return HistoricalSiteEventProductionConsumptionAuthorizationAssessment(
        boundary=BOUNDARY_NAME,
        shadow_present=shadow_present,
        historical_resolution_type_matched=historical_resolution_type_matched,
        historical_condition_type_matched=historical_condition_type_matched,
        semantic_state=semantic_state,
        semantic_state_consumable=semantic_state_consumable,
        production_eligible=production_eligible,
        runtime_unregistered=runtime_unregistered,
        step33_provenance_matched=step33_provenance_matched,
        step33_application_ready=step33_application_ready,
        step33_non_mutating=step33_non_mutating,
        missing_gates=missing_gates,
        production_consumption_authorized=not missing_gates,
    )
