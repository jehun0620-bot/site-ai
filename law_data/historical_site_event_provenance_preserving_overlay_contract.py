"""STEP44 provenance-preserving overlay contract for HISTORICAL_SITE_EVENT.

This module defines the registry representation required for a future historical
Rule Engine overlay. It does not modify rule_evaluation_pipeline, does not
perform a SITE registry overlay, and does not execute Rule Engine evaluation.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_PROVENANCE_PRESERVING_OVERLAY_CONTRACT"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"
HISTORICAL_REGISTRY_SOURCE = "RUNTIME_HISTORICAL_SITE_EVENT"
VALID_STATES = frozenset({"TRUE", "FALSE", "UNKNOWN"})


@dataclass(frozen=True)
class HistoricalSiteEventProvenancePreservingOverlayContract:
    boundary: str
    condition_present: bool
    condition_name_present: bool
    historical_type_matched: bool
    state_valid: bool
    source_present: bool
    provenance_family_preserved: bool
    missing_gates: tuple[str, ...]
    contract_ready: bool
    registry_condition_candidate: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "condition_present": self.condition_present,
            "condition_name_present": self.condition_name_present,
            "historical_type_matched": self.historical_type_matched,
            "state_valid": self.state_valid,
            "source_present": self.source_present,
            "provenance_family_preserved": self.provenance_family_preserved,
            "missing_gates": list(self.missing_gates),
            "contract_ready": self.contract_ready,
            "registry_condition_candidate": copy.deepcopy(dict(self.registry_condition_candidate)),
            "rule_evaluation_pipeline_modified": False,
            "site_analysis_builder_modified": False,
            "site_condition_context_injected": False,
            "site_registry_overlaid": False,
            "rule_engine_input_consumed": False,
            "rule_engine_state_mutated": False,
            "rule_evaluation_executed": False,
            "rule_applicability_changed": False,
            "builder_wiring_applied": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "runtime_registry_mutated": False,
            "historical_producer_auto_run": False,
            "public_api_exposed": False,
        }


def build_historical_site_event_provenance_preserving_overlay_contract(
    condition_name: Any,
    raw_condition: Any,
) -> HistoricalSiteEventProvenancePreservingOverlayContract:
    """Build a non-applied registry candidate with historical provenance preserved."""

    name = str(condition_name or "").strip()
    condition_present = isinstance(raw_condition, Mapping)
    condition = copy.deepcopy(dict(raw_condition)) if condition_present else {}
    condition_name_present = bool(name)
    condition_type = str(condition.get("type") or "").strip()
    historical_type_matched = condition_type == HISTORICAL_CONDITION_TYPE
    state = str(condition.get("state") or "").strip().upper()
    state_valid = state in VALID_STATES
    original_source = copy.deepcopy(condition.get("source"))
    source_present = bool(str(original_source or "").strip())
    provenance_family_preserved = bool(historical_type_matched and source_present)

    gates = (
        ("condition_present", condition_present),
        ("condition_name_present", condition_name_present),
        ("historical_type_matched", historical_type_matched),
        ("state_valid", state_valid),
        ("source_present", source_present),
        ("provenance_family_preserved", provenance_family_preserved),
    )
    missing_gates = tuple(gate for gate, passed in gates if not passed)
    contract_ready = not missing_gates

    registry_candidate: dict[str, Any] = {}
    if contract_ready:
        confidence = str(condition.get("confidence") or "").strip().upper() or "LOW"
        registry_candidate = {
            "type": HISTORICAL_CONDITION_TYPE,
            "state": state,
            "confidence": confidence,
            "source": HISTORICAL_REGISTRY_SOURCE,
            "runtime": True,
            "historical_source": original_source,
            "runtime_source": original_source,
            "resolution": copy.deepcopy(condition.get("resolution")),
            "evaluation": copy.deepcopy(condition.get("evaluation", {})),
            "evidence": copy.deepcopy(condition.get("evidence", {})),
        }

    return HistoricalSiteEventProvenancePreservingOverlayContract(
        boundary=BOUNDARY_NAME,
        condition_present=condition_present,
        condition_name_present=condition_name_present,
        historical_type_matched=historical_type_matched,
        state_valid=state_valid,
        source_present=source_present,
        provenance_family_preserved=provenance_family_preserved,
        missing_gates=missing_gates,
        contract_ready=contract_ready,
        registry_condition_candidate=registry_candidate,
    )
