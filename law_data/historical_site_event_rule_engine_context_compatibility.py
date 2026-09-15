"""STEP43 Rule Engine context compatibility gate for HISTORICAL_SITE_EVENT.

The current Rule Engine runtime overlay is spatial-oriented and rewrites every
accepted context item with the registry source marker RUNTIME_SPATIAL_CONDITION.
This boundary therefore does not inject a STEP42 payload. It only determines
whether the payload can safely use the current overlay semantics without losing
its historical condition family/provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.historical_site_event_builder_context_injection_payload import (
    BOUNDARY_NAME as PAYLOAD_BOUNDARY_NAME,
    HistoricalSiteEventBuilderContextInjectionPayload,
)


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_RULE_ENGINE_CONTEXT_COMPATIBILITY"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"
CURRENT_OVERLAY_SOURCE_MARKER = "RUNTIME_SPATIAL_CONDITION"
REQUIRED_HISTORICAL_SOURCE_MARKER = "RUNTIME_HISTORICAL_SITE_EVENT"


@dataclass(frozen=True)
class HistoricalSiteEventRuleEngineContextCompatibility:
    boundary: str
    payload_present: bool
    payload_boundary_matched: bool
    injection_ready: bool
    context_payload_present: bool
    historical_condition_present: bool
    historical_condition_type_preserved: bool
    historical_source_present: bool
    current_overlay_spatial_source_marker: bool
    historical_provenance_preservable_by_current_overlay: bool
    missing_gates: tuple[str, ...]
    historical_context_compatible: bool
    compatibility_resolution: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "payload_present": self.payload_present,
            "payload_boundary_matched": self.payload_boundary_matched,
            "injection_ready": self.injection_ready,
            "context_payload_present": self.context_payload_present,
            "historical_condition_present": self.historical_condition_present,
            "historical_condition_type_preserved": self.historical_condition_type_preserved,
            "historical_source_present": self.historical_source_present,
            "current_overlay_spatial_source_marker": self.current_overlay_spatial_source_marker,
            "historical_provenance_preservable_by_current_overlay": self.historical_provenance_preservable_by_current_overlay,
            "missing_gates": list(self.missing_gates),
            "historical_context_compatible": self.historical_context_compatible,
            "compatibility_resolution": self.compatibility_resolution,
            "builder_argument_supplied": False,
            "site_analysis_builder_modified": False,
            "rule_evaluation_pipeline_modified": False,
            "site_condition_context_injected": False,
            "rule_engine_input_consumed": False,
            "site_registry_overlaid": False,
            "site_state_mutated": False,
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


def assess_historical_site_event_rule_engine_context_compatibility(
    payload: HistoricalSiteEventBuilderContextInjectionPayload | None,
) -> HistoricalSiteEventRuleEngineContextCompatibility:
    """Fail closed while current overlay cannot preserve historical provenance."""

    payload_present = isinstance(payload, HistoricalSiteEventBuilderContextInjectionPayload)
    payload_boundary_matched = bool(payload_present and payload.boundary == PAYLOAD_BOUNDARY_NAME)
    injection_ready = bool(payload_present and payload.injection_ready is True)
    context = dict(payload.site_condition_context_payload) if payload_present else {}
    context_payload_present = bool(context)

    historical_items = [
        condition
        for condition in context.values()
        if isinstance(condition, dict)
        and str(condition.get("type") or "").strip() == HISTORICAL_CONDITION_TYPE
    ]
    historical_condition_present = bool(historical_items)
    historical_condition_type_preserved = bool(
        historical_items
        and all(
            str(item.get("type") or "").strip() == HISTORICAL_CONDITION_TYPE
            for item in historical_items
        )
    )
    historical_source_present = bool(
        historical_items
        and all(str(item.get("source") or "").strip() for item in historical_items)
    )

    # Audited current rule_evaluation_pipeline.overlay_runtime_site_conditions
    # assigns this fixed registry-level marker to every accepted context item.
    current_overlay_spatial_source_marker = True
    historical_provenance_preservable_by_current_overlay = bool(
        not current_overlay_spatial_source_marker
        or CURRENT_OVERLAY_SOURCE_MARKER == REQUIRED_HISTORICAL_SOURCE_MARKER
    )

    gates = (
        ("payload_present", payload_present),
        ("payload_boundary_matched", payload_boundary_matched),
        ("injection_ready", injection_ready),
        ("context_payload_present", context_payload_present),
        ("historical_condition_present", historical_condition_present),
        ("historical_condition_type_preserved", historical_condition_type_preserved),
        ("historical_source_present", historical_source_present),
        (
            "historical_provenance_preservable_by_current_overlay",
            historical_provenance_preservable_by_current_overlay,
        ),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    historical_context_compatible = not missing_gates

    if historical_context_compatible:
        resolution = "CURRENT_RULE_ENGINE_CONTEXT_COMPATIBLE"
    elif (
        payload_present
        and payload_boundary_matched
        and injection_ready
        and historical_condition_present
        and not historical_provenance_preservable_by_current_overlay
    ):
        resolution = "BLOCKED_CURRENT_OVERLAY_SPATIAL_PROVENANCE_SEMANTICS"
    else:
        resolution = "BLOCKED_INVALID_OR_INCOMPLETE_HISTORICAL_CONTEXT"

    return HistoricalSiteEventRuleEngineContextCompatibility(
        boundary=BOUNDARY_NAME,
        payload_present=payload_present,
        payload_boundary_matched=payload_boundary_matched,
        injection_ready=injection_ready,
        context_payload_present=context_payload_present,
        historical_condition_present=historical_condition_present,
        historical_condition_type_preserved=historical_condition_type_preserved,
        historical_source_present=historical_source_present,
        current_overlay_spatial_source_marker=current_overlay_spatial_source_marker,
        historical_provenance_preservable_by_current_overlay=historical_provenance_preservable_by_current_overlay,
        missing_gates=missing_gates,
        historical_context_compatible=historical_context_compatible,
        compatibility_resolution=resolution,
    )
