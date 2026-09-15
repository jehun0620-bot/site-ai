"""STEP45 non-executing overlay application authorization for HISTORICAL_SITE_EVENT.

A concrete STEP44 provenance-preserving contract may be authorized for a future
historical SITE registry overlay. Authorization is not application: this module
never modifies the Rule Engine pipeline, never mutates a SITE registry, and
never executes rule evaluation/applicability recalculation.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    BOUNDARY_NAME as OVERLAY_CONTRACT_BOUNDARY_NAME,
    HISTORICAL_CONDITION_TYPE,
    HISTORICAL_REGISTRY_SOURCE,
    HistoricalSiteEventProvenancePreservingOverlayContract,
)


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_OVERLAY_APPLICATION_AUTHORIZATION"
VALID_STATES = frozenset({"TRUE", "FALSE", "UNKNOWN"})


@dataclass(frozen=True)
class HistoricalSiteEventOverlayApplicationAuthorization:
    boundary: str
    contract_present: bool
    contract_boundary_matched: bool
    contract_ready: bool
    registry_candidate_present: bool
    historical_type_preserved: bool
    state_valid: bool
    registry_source_matched: bool
    original_historical_source_preserved: bool
    contract_diagnostics_aligned: bool
    missing_gates: tuple[str, ...]
    overlay_application_authorized: bool
    authorized_registry_condition: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "contract_present": self.contract_present,
            "contract_boundary_matched": self.contract_boundary_matched,
            "contract_ready": self.contract_ready,
            "registry_candidate_present": self.registry_candidate_present,
            "historical_type_preserved": self.historical_type_preserved,
            "state_valid": self.state_valid,
            "registry_source_matched": self.registry_source_matched,
            "original_historical_source_preserved": self.original_historical_source_preserved,
            "contract_diagnostics_aligned": self.contract_diagnostics_aligned,
            "missing_gates": list(self.missing_gates),
            "overlay_application_authorized": self.overlay_application_authorized,
            "authorized_registry_condition": copy.deepcopy(dict(self.authorized_registry_condition)),
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


def authorize_historical_site_event_overlay_application(
    contract: HistoricalSiteEventProvenancePreservingOverlayContract | None,
) -> HistoricalSiteEventOverlayApplicationAuthorization:
    """Authorize a STEP44 candidate without applying it to any registry."""

    contract_present = isinstance(
        contract,
        HistoricalSiteEventProvenancePreservingOverlayContract,
    )
    contract_boundary_matched = bool(
        contract_present and contract.boundary == OVERLAY_CONTRACT_BOUNDARY_NAME
    )
    contract_ready = bool(contract_present and contract.contract_ready is True)
    candidate = (
        copy.deepcopy(dict(contract.registry_condition_candidate))
        if contract_present
        else {}
    )
    registry_candidate_present = bool(candidate)
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
    contract_diagnostics_aligned = bool(
        contract_present
        and contract.condition_present is True
        and contract.condition_name_present is True
        and contract.historical_type_matched is True
        and contract.state_valid is True
        and contract.source_present is True
        and contract.provenance_family_preserved is True
    )

    gates = (
        ("contract_present", contract_present),
        ("contract_boundary_matched", contract_boundary_matched),
        ("contract_ready", contract_ready),
        ("registry_candidate_present", registry_candidate_present),
        ("historical_type_preserved", historical_type_preserved),
        ("state_valid", state_valid),
        ("registry_source_matched", registry_source_matched),
        ("original_historical_source_preserved", original_historical_source_preserved),
        ("contract_diagnostics_aligned", contract_diagnostics_aligned),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    overlay_application_authorized = not missing_gates

    return HistoricalSiteEventOverlayApplicationAuthorization(
        boundary=BOUNDARY_NAME,
        contract_present=contract_present,
        contract_boundary_matched=contract_boundary_matched,
        contract_ready=contract_ready,
        registry_candidate_present=registry_candidate_present,
        historical_type_preserved=historical_type_preserved,
        state_valid=state_valid,
        registry_source_matched=registry_source_matched,
        original_historical_source_preserved=original_historical_source_preserved,
        contract_diagnostics_aligned=contract_diagnostics_aligned,
        missing_gates=missing_gates,
        overlay_application_authorized=overlay_application_authorized,
        authorized_registry_condition=(candidate if overlay_application_authorized else {}),
    )
