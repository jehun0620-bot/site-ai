"""STEP39 non-injecting site_condition_context projection for HISTORICAL_SITE_EVENT.

A valid STEP38 consumption package is projected into the mapping shape expected
by Rule Engine `site_condition_context`. Projection readiness does not inject
that mapping into the builder or Rule Engine and does not execute any overlay,
rule evaluation, runtime registration, producer, or API path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_rule_engine_consumption_package import (
    BOUNDARY_NAME as PACKAGE_BOUNDARY_NAME,
    HISTORICAL_CONDITION_TYPE,
    HistoricalSiteEventRuleEngineConsumptionPackage,
)
from law_data.historical_site_event_rule_engine_consumption_authorization import (
    TARGET_CONSUMER,
)
from law_data.production_site_condition import FALSE, TRUE


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_SITE_CONDITION_CONTEXT_PROJECTION"


@dataclass(frozen=True)
class HistoricalSiteEventSiteConditionContextProjection:
    boundary: str
    package_present: bool
    package_boundary_matched: bool
    target_consumer_matched: bool
    consumption_ready: bool
    condition_name_present: bool
    condition_view_present: bool
    condition_name_aligned: bool
    historical_condition_type_matched: bool
    semantic_state_consumable: bool
    package_contract_aligned: bool
    missing_gates: tuple[str, ...]
    context_projection_ready: bool
    site_condition_context_projection: Mapping[str, Mapping[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "package_present": self.package_present,
            "package_boundary_matched": self.package_boundary_matched,
            "target_consumer_matched": self.target_consumer_matched,
            "consumption_ready": self.consumption_ready,
            "condition_name_present": self.condition_name_present,
            "condition_view_present": self.condition_view_present,
            "condition_name_aligned": self.condition_name_aligned,
            "historical_condition_type_matched": self.historical_condition_type_matched,
            "semantic_state_consumable": self.semantic_state_consumable,
            "package_contract_aligned": self.package_contract_aligned,
            "missing_gates": list(self.missing_gates),
            "context_projection_ready": self.context_projection_ready,
            "site_condition_context_projection": {
                name: dict(condition)
                for name, condition in self.site_condition_context_projection.items()
            },
            "site_condition_context_injected": False,
            "rule_engine_input_consumed": False,
            "site_registry_overlaid": False,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "rule_evaluation_executed": False,
            "builder_wiring_applied": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "runtime_registry_mutated": False,
            "historical_producer_auto_run": False,
            "public_api_exposed": False,
        }


def project_historical_site_event_site_condition_context(
    package: HistoricalSiteEventRuleEngineConsumptionPackage | None,
) -> HistoricalSiteEventSiteConditionContextProjection:
    """Project STEP38 into Rule Engine context shape without injecting it."""

    package_present = isinstance(
        package,
        HistoricalSiteEventRuleEngineConsumptionPackage,
    )
    package_boundary_matched = bool(
        package_present and package.boundary == PACKAGE_BOUNDARY_NAME
    )
    target_consumer_matched = bool(
        package_present and package.target_consumer == TARGET_CONSUMER
    )
    consumption_ready = bool(package_present and package.consumption_ready is True)
    condition_name = package.condition_name.strip() if package_present else ""
    condition_name_present = bool(condition_name)
    view = dict(package.condition_view) if package_present else {}
    condition_view_present = bool(view)
    condition_name_aligned = bool(
        condition_name_present
        and str(view.get("name") or "").strip() == condition_name
    )
    historical_condition_type_matched = bool(
        package_present
        and package.historical_condition_type_matched is True
        and view.get("type") == HISTORICAL_CONDITION_TYPE
    )
    semantic_state = str(view.get("state") or "").strip()
    semantic_state_consumable = bool(
        package_present
        and package.semantic_state_consumable is True
        and package.semantic_state == semantic_state
        and semantic_state in {TRUE, FALSE}
    )
    package_contract_aligned = bool(
        package_present
        and package.authorization_present is True
        and package.authorization_boundary_matched is True
        and package.authorization_granted is True
        and package.condition_view_present is True
        and package.authorization_contract_aligned is True
    )

    gates = (
        ("package_present", package_present),
        ("package_boundary_matched", package_boundary_matched),
        ("target_consumer_matched", target_consumer_matched),
        ("consumption_ready", consumption_ready),
        ("condition_name_present", condition_name_present),
        ("condition_view_present", condition_view_present),
        ("condition_name_aligned", condition_name_aligned),
        ("historical_condition_type_matched", historical_condition_type_matched),
        ("semantic_state_consumable", semantic_state_consumable),
        ("package_contract_aligned", package_contract_aligned),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    context_projection_ready = not missing_gates
    projection = {condition_name: view} if context_projection_ready else {}

    return HistoricalSiteEventSiteConditionContextProjection(
        boundary=BOUNDARY_NAME,
        package_present=package_present,
        package_boundary_matched=package_boundary_matched,
        target_consumer_matched=target_consumer_matched,
        consumption_ready=consumption_ready,
        condition_name_present=condition_name_present,
        condition_view_present=condition_view_present,
        condition_name_aligned=condition_name_aligned,
        historical_condition_type_matched=historical_condition_type_matched,
        semantic_state_consumable=semantic_state_consumable,
        package_contract_aligned=package_contract_aligned,
        missing_gates=missing_gates,
        context_projection_ready=context_projection_ready,
        site_condition_context_projection=projection,
    )
