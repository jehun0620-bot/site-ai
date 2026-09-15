"""STEP41 builder context injection authorization for HISTORICAL_SITE_EVENT.

This boundary authorizes a valid STEP40 merged context candidate for a future
builder injection. Authorization is not injection: this module does not modify
site_analysis_builder, pass context to evaluate_site_rules, overlay the SITE
registry, evaluate rules, register runtime state, run producers, or expose API.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_site_condition_context_merge import (
    BOUNDARY_NAME as MERGE_BOUNDARY_NAME,
    HistoricalSiteEventSiteConditionContextMerge,
)


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_BUILDER_CONTEXT_INJECTION_AUTHORIZATION"
TARGET_INJECTION_POINT = "SITE_ANALYSIS_BUILDER_SITE_CONDITION_CONTEXT"


@dataclass(frozen=True)
class HistoricalSiteEventBuilderContextInjectionAuthorization:
    boundary: str
    target_injection_point: str
    merge_present: bool
    merge_boundary_matched: bool
    merge_ready: bool
    merged_context_present: bool
    historical_condition_name_present: bool
    historical_condition_preserved: bool
    no_condition_name_collision: bool
    merge_contract_aligned: bool
    missing_gates: tuple[str, ...]
    builder_injection_authorized: bool
    authorized_merged_context: Mapping[str, Mapping[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "target_injection_point": self.target_injection_point,
            "merge_present": self.merge_present,
            "merge_boundary_matched": self.merge_boundary_matched,
            "merge_ready": self.merge_ready,
            "merged_context_present": self.merged_context_present,
            "historical_condition_name_present": self.historical_condition_name_present,
            "historical_condition_preserved": self.historical_condition_preserved,
            "no_condition_name_collision": self.no_condition_name_collision,
            "merge_contract_aligned": self.merge_contract_aligned,
            "missing_gates": list(self.missing_gates),
            "builder_injection_authorized": self.builder_injection_authorized,
            "authorized_merged_context": {
                name: copy.deepcopy(dict(condition))
                for name, condition in self.authorized_merged_context.items()
            },
            "site_analysis_builder_modified": False,
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


def authorize_historical_site_event_builder_context_injection(
    merge: HistoricalSiteEventSiteConditionContextMerge | None,
) -> HistoricalSiteEventBuilderContextInjectionAuthorization:
    """Authorize a STEP40 merge candidate without performing builder injection."""

    merge_present = isinstance(merge, HistoricalSiteEventSiteConditionContextMerge)
    merge_boundary_matched = bool(
        merge_present and merge.boundary == MERGE_BOUNDARY_NAME
    )
    merge_ready = bool(merge_present and merge.merge_ready is True)
    merged = copy.deepcopy(dict(merge.merged_context_candidate)) if merge_present else {}
    merged_context_present = bool(merged)
    historical_name = merge.historical_condition_name.strip() if merge_present else ""
    historical_condition_name_present = bool(historical_name)
    historical_condition_preserved = bool(
        historical_name
        and historical_name in merged
        and isinstance(merged.get(historical_name), Mapping)
    )
    no_condition_name_collision = bool(
        merge_present and merge.condition_name_collision is False
    )
    merge_contract_aligned = bool(
        merge_present
        and merge.existing_context_valid is True
        and merge.projection_present is True
        and merge.projection_boundary_matched is True
        and merge.context_projection_ready is True
        and merge.historical_projection_valid is True
        and merge.projection_contract_aligned is True
    )

    gates = (
        ("merge_present", merge_present),
        ("merge_boundary_matched", merge_boundary_matched),
        ("merge_ready", merge_ready),
        ("merged_context_present", merged_context_present),
        ("historical_condition_name_present", historical_condition_name_present),
        ("historical_condition_preserved", historical_condition_preserved),
        ("no_condition_name_collision", no_condition_name_collision),
        ("merge_contract_aligned", merge_contract_aligned),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    builder_injection_authorized = not missing_gates

    return HistoricalSiteEventBuilderContextInjectionAuthorization(
        boundary=BOUNDARY_NAME,
        target_injection_point=TARGET_INJECTION_POINT,
        merge_present=merge_present,
        merge_boundary_matched=merge_boundary_matched,
        merge_ready=merge_ready,
        merged_context_present=merged_context_present,
        historical_condition_name_present=historical_condition_name_present,
        historical_condition_preserved=historical_condition_preserved,
        no_condition_name_collision=no_condition_name_collision,
        merge_contract_aligned=merge_contract_aligned,
        missing_gates=missing_gates,
        builder_injection_authorized=builder_injection_authorized,
        authorized_merged_context=merged if builder_injection_authorized else {},
    )
