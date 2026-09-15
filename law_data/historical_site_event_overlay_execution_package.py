"""STEP46 non-executing overlay execution package for HISTORICAL_SITE_EVENT.

This module packages an authorized STEP45 historical registry condition with its
condition name and future execution target. Packaging is not execution: no SITE
registry is mutated and no Rule Engine function is called.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_overlay_application_authorization import (
    BOUNDARY_NAME as AUTHORIZATION_BOUNDARY_NAME,
    HistoricalSiteEventOverlayApplicationAuthorization,
)
from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    HISTORICAL_CONDITION_TYPE,
    HISTORICAL_REGISTRY_SOURCE,
)


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_OVERLAY_EXECUTION_PACKAGE"
EXECUTION_TARGET = "RULE_ENGINE_SITE_REGISTRY_HISTORICAL_OVERLAY"
VALID_STATES = frozenset({"TRUE", "FALSE", "UNKNOWN"})


@dataclass(frozen=True)
class HistoricalSiteEventOverlayExecutionPackage:
    boundary: str
    execution_target: str
    authorization_present: bool
    authorization_boundary_matched: bool
    overlay_application_authorized: bool
    condition_name_present: bool
    registry_condition_present: bool
    historical_type_preserved: bool
    state_valid: bool
    registry_source_matched: bool
    original_historical_source_preserved: bool
    authorization_contract_aligned: bool
    missing_gates: tuple[str, ...]
    execution_ready: bool
    condition_name: str
    registry_condition: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "execution_target": self.execution_target,
            "authorization_present": self.authorization_present,
            "authorization_boundary_matched": self.authorization_boundary_matched,
            "overlay_application_authorized": self.overlay_application_authorized,
            "condition_name_present": self.condition_name_present,
            "registry_condition_present": self.registry_condition_present,
            "historical_type_preserved": self.historical_type_preserved,
            "state_valid": self.state_valid,
            "registry_source_matched": self.registry_source_matched,
            "original_historical_source_preserved": self.original_historical_source_preserved,
            "authorization_contract_aligned": self.authorization_contract_aligned,
            "missing_gates": list(self.missing_gates),
            "execution_ready": self.execution_ready,
            "condition_name": self.condition_name,
            "registry_condition": copy.deepcopy(dict(self.registry_condition)),
            "overlay_application_executed": False,
            "site_registry_overlaid": False,
            "apply_site_registry_called": False,
            "rule_evaluation_pipeline_modified": False,
            "site_analysis_builder_modified": False,
            "site_condition_context_injected": False,
            "rule_engine_input_consumed": False,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "rule_evaluation_executed": False,
            "rule_applicability_recalculated": False,
            "rule_applicability_changed": False,
            "builder_wiring_applied": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "runtime_registry_mutated": False,
            "historical_producer_auto_run": False,
            "public_api_exposed": False,
        }


def package_historical_site_event_overlay_execution(
    condition_name: Any,
    authorization: HistoricalSiteEventOverlayApplicationAuthorization | None,
) -> HistoricalSiteEventOverlayExecutionPackage:
    """Prepare an immutable execution-ready payload without applying it."""

    name = str(condition_name or "").strip()
    authorization_present = isinstance(
        authorization,
        HistoricalSiteEventOverlayApplicationAuthorization,
    )
    authorization_boundary_matched = bool(
        authorization_present and authorization.boundary == AUTHORIZATION_BOUNDARY_NAME
    )
    overlay_application_authorized = bool(
        authorization_present and authorization.overlay_application_authorized is True
    )
    condition_name_present = bool(name)
    candidate = (
        copy.deepcopy(dict(authorization.authorized_registry_condition))
        if authorization_present
        else {}
    )
    registry_condition_present = bool(candidate)
    historical_type_preserved = (
        str(candidate.get("type") or "").strip() == HISTORICAL_CONDITION_TYPE
    )
    state_valid = str(candidate.get("state") or "").strip().upper() in VALID_STATES
    registry_source_matched = (
        str(candidate.get("source") or "").strip() == HISTORICAL_REGISTRY_SOURCE
    )
    historical_source = candidate.get("historical_source")
    runtime_source = candidate.get("runtime_source")
    original_historical_source_preserved = bool(
        str(historical_source or "").strip()
        and historical_source == runtime_source
    )
    authorization_contract_aligned = bool(
        authorization_present
        and authorization.contract_present is True
        and authorization.contract_boundary_matched is True
        and authorization.contract_ready is True
        and authorization.registry_candidate_present is True
        and authorization.historical_type_preserved is True
        and authorization.state_valid is True
        and authorization.registry_source_matched is True
        and authorization.original_historical_source_preserved is True
        and authorization.contract_diagnostics_aligned is True
    )

    gates = (
        ("authorization_present", authorization_present),
        ("authorization_boundary_matched", authorization_boundary_matched),
        ("overlay_application_authorized", overlay_application_authorized),
        ("condition_name_present", condition_name_present),
        ("registry_condition_present", registry_condition_present),
        ("historical_type_preserved", historical_type_preserved),
        ("state_valid", state_valid),
        ("registry_source_matched", registry_source_matched),
        ("original_historical_source_preserved", original_historical_source_preserved),
        ("authorization_contract_aligned", authorization_contract_aligned),
    )
    missing_gates = tuple(gate for gate, passed in gates if not passed)
    execution_ready = not missing_gates

    return HistoricalSiteEventOverlayExecutionPackage(
        boundary=BOUNDARY_NAME,
        execution_target=EXECUTION_TARGET,
        authorization_present=authorization_present,
        authorization_boundary_matched=authorization_boundary_matched,
        overlay_application_authorized=overlay_application_authorized,
        condition_name_present=condition_name_present,
        registry_condition_present=registry_condition_present,
        historical_type_preserved=historical_type_preserved,
        state_valid=state_valid,
        registry_source_matched=registry_source_matched,
        original_historical_source_preserved=original_historical_source_preserved,
        authorization_contract_aligned=authorization_contract_aligned,
        missing_gates=missing_gates,
        execution_ready=execution_ready,
        condition_name=(name if execution_ready else ""),
        registry_condition=(candidate if execution_ready else {}),
    )
