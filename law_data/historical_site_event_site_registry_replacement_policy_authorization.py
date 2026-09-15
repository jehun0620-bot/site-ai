"""STEP48 fail-closed replacement policy authorization for HISTORICAL_SITE_EVENT.

Only a STEP47 preview with no condition-name collision may be authorized for a
future registry mutation boundary. A collision is blocked pending a separately
approved explicit replacement policy. This module performs no mutation.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_site_registry_overlay_preview import (
    BOUNDARY_NAME as PREVIEW_BOUNDARY_NAME,
    HistoricalSiteEventSiteRegistryOverlayPreview,
)
from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    HISTORICAL_CONDITION_TYPE,
    HISTORICAL_REGISTRY_SOURCE,
)


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_SITE_REGISTRY_REPLACEMENT_POLICY_AUTHORIZATION"
POLICY = "NO_CONDITION_NAME_COLLISION"
VALID_STATES = frozenset({"TRUE", "FALSE", "UNKNOWN"})


@dataclass(frozen=True)
class HistoricalSiteEventSiteRegistryReplacementPolicyAuthorization:
    boundary: str
    policy: str
    preview_present: bool
    preview_boundary_matched: bool
    preview_ready: bool
    condition_name_collision: bool
    no_collision_policy_satisfied: bool
    preview_registry_present: bool
    historical_condition_present: bool
    historical_type_preserved: bool
    state_valid: bool
    registry_source_matched: bool
    original_historical_source_preserved: bool
    preview_contract_aligned: bool
    missing_gates: tuple[str, ...]
    replacement_policy_authorized: bool
    authorized_preview_registry: Mapping[str, Mapping[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "policy": self.policy,
            "preview_present": self.preview_present,
            "preview_boundary_matched": self.preview_boundary_matched,
            "preview_ready": self.preview_ready,
            "condition_name_collision": self.condition_name_collision,
            "no_collision_policy_satisfied": self.no_collision_policy_satisfied,
            "preview_registry_present": self.preview_registry_present,
            "historical_condition_present": self.historical_condition_present,
            "historical_type_preserved": self.historical_type_preserved,
            "state_valid": self.state_valid,
            "registry_source_matched": self.registry_source_matched,
            "original_historical_source_preserved": self.original_historical_source_preserved,
            "preview_contract_aligned": self.preview_contract_aligned,
            "missing_gates": list(self.missing_gates),
            "replacement_policy_authorized": self.replacement_policy_authorized,
            "authorized_preview_registry": copy.deepcopy(dict(self.authorized_preview_registry)),
            "collision_replacement_authorized": False,
            "original_registry_mutated": False,
            "overlay_application_executed": False,
            "site_registry_overlaid": False,
            "apply_site_registry_called": False,
            "refresh_rule_called": False,
            "rule_evaluation_pipeline_modified": False,
            "site_analysis_builder_modified": False,
            "rule_engine_input_consumed": False,
            "rule_evaluation_executed": False,
            "rule_applicability_recalculated": False,
            "rule_applicability_changed": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "runtime_registry_mutated": False,
            "public_api_exposed": False,
        }


def authorize_historical_site_event_site_registry_replacement_policy(
    preview: HistoricalSiteEventSiteRegistryOverlayPreview | None,
) -> HistoricalSiteEventSiteRegistryReplacementPolicyAuthorization:
    """Authorize only collision-free STEP47 previews; never mutate a registry."""

    preview_present = isinstance(preview, HistoricalSiteEventSiteRegistryOverlayPreview)
    preview_boundary_matched = bool(preview_present and preview.boundary == PREVIEW_BOUNDARY_NAME)
    preview_ready = bool(preview_present and preview.preview_ready is True)
    condition_name_collision = bool(preview_present and preview.condition_name_collision is True)
    no_collision_policy_satisfied = bool(preview_present and not condition_name_collision)
    preview_registry = copy.deepcopy(dict(preview.preview_registry)) if preview_present else {}
    preview_registry_present = bool(preview_registry)
    historical_condition = (
        copy.deepcopy(dict(preview.historical_condition_after)) if preview_present else {}
    )
    historical_condition_present = bool(historical_condition)
    historical_type_preserved = (
        str(historical_condition.get("type") or "").strip() == HISTORICAL_CONDITION_TYPE
    )
    state_valid = str(historical_condition.get("state") or "").strip().upper() in VALID_STATES
    registry_source_matched = (
        str(historical_condition.get("source") or "").strip() == HISTORICAL_REGISTRY_SOURCE
    )
    historical_source = historical_condition.get("historical_source")
    runtime_source = historical_condition.get("runtime_source")
    original_historical_source_preserved = bool(
        str(historical_source or "").strip() and historical_source == runtime_source
    )
    preview_contract_aligned = bool(
        preview_present
        and preview.package_present is True
        and preview.package_boundary_matched is True
        and preview.execution_target_matched is True
        and preview.execution_ready is True
        and preview.existing_registry_valid is True
        and preview.condition_name_present is True
        and preview.registry_condition_present is True
        and preview.historical_type_preserved is True
        and preview.state_valid is True
        and preview.registry_source_matched is True
        and preview.original_historical_source_preserved is True
    )

    gates = (
        ("preview_present", preview_present),
        ("preview_boundary_matched", preview_boundary_matched),
        ("preview_ready", preview_ready),
        ("no_collision_policy_satisfied", no_collision_policy_satisfied),
        ("preview_registry_present", preview_registry_present),
        ("historical_condition_present", historical_condition_present),
        ("historical_type_preserved", historical_type_preserved),
        ("state_valid", state_valid),
        ("registry_source_matched", registry_source_matched),
        ("original_historical_source_preserved", original_historical_source_preserved),
        ("preview_contract_aligned", preview_contract_aligned),
    )
    missing_gates = tuple(gate for gate, passed in gates if not passed)
    replacement_policy_authorized = not missing_gates

    return HistoricalSiteEventSiteRegistryReplacementPolicyAuthorization(
        boundary=BOUNDARY_NAME,
        policy=POLICY,
        preview_present=preview_present,
        preview_boundary_matched=preview_boundary_matched,
        preview_ready=preview_ready,
        condition_name_collision=condition_name_collision,
        no_collision_policy_satisfied=no_collision_policy_satisfied,
        preview_registry_present=preview_registry_present,
        historical_condition_present=historical_condition_present,
        historical_type_preserved=historical_type_preserved,
        state_valid=state_valid,
        registry_source_matched=registry_source_matched,
        original_historical_source_preserved=original_historical_source_preserved,
        preview_contract_aligned=preview_contract_aligned,
        missing_gates=missing_gates,
        replacement_policy_authorized=replacement_policy_authorized,
        authorized_preview_registry=(preview_registry if replacement_policy_authorized else {}),
    )
