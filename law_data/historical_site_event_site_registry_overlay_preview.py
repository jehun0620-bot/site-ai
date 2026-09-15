"""STEP47 non-mutating SITE registry overlay preview for HISTORICAL_SITE_EVENT.

The preview applies a STEP46 execution package only to a deep copy of an
existing SITE registry. It exposes collision/replacement diagnostics before any
real Rule Engine mutation. It never calls apply_site_registry or refresh_rule.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_overlay_execution_package import (
    BOUNDARY_NAME as EXECUTION_PACKAGE_BOUNDARY_NAME,
    EXECUTION_TARGET,
    HistoricalSiteEventOverlayExecutionPackage,
)
from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    HISTORICAL_CONDITION_TYPE,
    HISTORICAL_REGISTRY_SOURCE,
)


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_SITE_REGISTRY_OVERLAY_PREVIEW"
VALID_STATES = frozenset({"TRUE", "FALSE", "UNKNOWN"})


@dataclass(frozen=True)
class HistoricalSiteEventSiteRegistryOverlayPreview:
    boundary: str
    package_present: bool
    package_boundary_matched: bool
    execution_target_matched: bool
    execution_ready: bool
    existing_registry_valid: bool
    condition_name_present: bool
    registry_condition_present: bool
    historical_type_preserved: bool
    state_valid: bool
    registry_source_matched: bool
    original_historical_source_preserved: bool
    condition_name_collision: bool
    existing_condition_before: Mapping[str, Any]
    historical_condition_after: Mapping[str, Any]
    missing_gates: tuple[str, ...]
    preview_ready: bool
    preview_registry: Mapping[str, Mapping[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "package_present": self.package_present,
            "package_boundary_matched": self.package_boundary_matched,
            "execution_target_matched": self.execution_target_matched,
            "execution_ready": self.execution_ready,
            "existing_registry_valid": self.existing_registry_valid,
            "condition_name_present": self.condition_name_present,
            "registry_condition_present": self.registry_condition_present,
            "historical_type_preserved": self.historical_type_preserved,
            "state_valid": self.state_valid,
            "registry_source_matched": self.registry_source_matched,
            "original_historical_source_preserved": self.original_historical_source_preserved,
            "condition_name_collision": self.condition_name_collision,
            "existing_condition_before": copy.deepcopy(dict(self.existing_condition_before)),
            "historical_condition_after": copy.deepcopy(dict(self.historical_condition_after)),
            "missing_gates": list(self.missing_gates),
            "preview_ready": self.preview_ready,
            "preview_registry": copy.deepcopy(dict(self.preview_registry)),
            "original_registry_mutated": False,
            "overlay_application_executed": False,
            "site_registry_overlaid": False,
            "apply_site_registry_called": False,
            "refresh_rule_called": False,
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


def _normalize_registry(existing_registry: Any) -> tuple[bool, dict[str, dict[str, Any]]]:
    if not isinstance(existing_registry, Mapping):
        return False, {}
    normalized: dict[str, dict[str, Any]] = {}
    for raw_name, raw_condition in existing_registry.items():
        name = str(raw_name or "").strip()
        if not name or not isinstance(raw_condition, Mapping):
            return False, {}
        normalized[name] = copy.deepcopy(dict(raw_condition))
    return True, normalized


def preview_historical_site_event_site_registry_overlay(
    existing_registry: Any,
    package: HistoricalSiteEventOverlayExecutionPackage | None,
) -> HistoricalSiteEventSiteRegistryOverlayPreview:
    """Return a deep-copy preview; never mutate the supplied registry."""

    existing_registry_valid, normalized_registry = _normalize_registry(existing_registry)
    package_present = isinstance(package, HistoricalSiteEventOverlayExecutionPackage)
    package_boundary_matched = bool(
        package_present and package.boundary == EXECUTION_PACKAGE_BOUNDARY_NAME
    )
    execution_target_matched = bool(
        package_present and package.execution_target == EXECUTION_TARGET
    )
    execution_ready = bool(package_present and package.execution_ready is True)
    name = str(package.condition_name or "").strip() if package_present else ""
    condition_name_present = bool(name)
    candidate = copy.deepcopy(dict(package.registry_condition)) if package_present else {}
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
        str(historical_source or "").strip() and historical_source == runtime_source
    )
    condition_name_collision = bool(existing_registry_valid and name in normalized_registry)
    existing_condition_before = (
        copy.deepcopy(normalized_registry.get(name, {})) if condition_name_collision else {}
    )

    gates = (
        ("package_present", package_present),
        ("package_boundary_matched", package_boundary_matched),
        ("execution_target_matched", execution_target_matched),
        ("execution_ready", execution_ready),
        ("existing_registry_valid", existing_registry_valid),
        ("condition_name_present", condition_name_present),
        ("registry_condition_present", registry_condition_present),
        ("historical_type_preserved", historical_type_preserved),
        ("state_valid", state_valid),
        ("registry_source_matched", registry_source_matched),
        ("original_historical_source_preserved", original_historical_source_preserved),
    )
    missing_gates = tuple(gate for gate, passed in gates if not passed)
    preview_ready = not missing_gates

    preview_registry: dict[str, dict[str, Any]] = {}
    historical_condition_after: dict[str, Any] = {}
    if preview_ready:
        preview_registry = copy.deepcopy(normalized_registry)
        preview_registry[name] = copy.deepcopy(candidate)
        historical_condition_after = copy.deepcopy(candidate)

    return HistoricalSiteEventSiteRegistryOverlayPreview(
        boundary=BOUNDARY_NAME,
        package_present=package_present,
        package_boundary_matched=package_boundary_matched,
        execution_target_matched=execution_target_matched,
        execution_ready=execution_ready,
        existing_registry_valid=existing_registry_valid,
        condition_name_present=condition_name_present,
        registry_condition_present=registry_condition_present,
        historical_type_preserved=historical_type_preserved,
        state_valid=state_valid,
        registry_source_matched=registry_source_matched,
        original_historical_source_preserved=original_historical_source_preserved,
        condition_name_collision=condition_name_collision,
        existing_condition_before=existing_condition_before,
        historical_condition_after=historical_condition_after,
        missing_gates=missing_gates,
        preview_ready=preview_ready,
        preview_registry=preview_registry,
    )
