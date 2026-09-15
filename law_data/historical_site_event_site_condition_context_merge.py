"""STEP40 non-injecting site_condition_context merge for HISTORICAL_SITE_EVENT.

A validated STEP39 historical projection may be merged with an existing runtime
SITE condition context only when no condition-name collision exists. The result
is a merge candidate; this module never injects it into the builder or Rule
Engine and never executes SITE overlay, rule evaluation, runtime registration,
producer, or API paths.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_site_condition_context_projection import (
    BOUNDARY_NAME as PROJECTION_BOUNDARY_NAME,
    HistoricalSiteEventSiteConditionContextProjection,
)


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_SITE_CONDITION_CONTEXT_MERGE"


@dataclass(frozen=True)
class HistoricalSiteEventSiteConditionContextMerge:
    boundary: str
    existing_context_valid: bool
    projection_present: bool
    projection_boundary_matched: bool
    context_projection_ready: bool
    historical_projection_valid: bool
    historical_condition_name: str
    condition_name_collision: bool
    projection_contract_aligned: bool
    missing_gates: tuple[str, ...]
    merge_ready: bool
    merged_context_candidate: Mapping[str, Mapping[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "existing_context_valid": self.existing_context_valid,
            "projection_present": self.projection_present,
            "projection_boundary_matched": self.projection_boundary_matched,
            "context_projection_ready": self.context_projection_ready,
            "historical_projection_valid": self.historical_projection_valid,
            "historical_condition_name": self.historical_condition_name,
            "condition_name_collision": self.condition_name_collision,
            "projection_contract_aligned": self.projection_contract_aligned,
            "missing_gates": list(self.missing_gates),
            "merge_ready": self.merge_ready,
            "merged_context_candidate": {
                name: copy.deepcopy(dict(condition))
                for name, condition in self.merged_context_candidate.items()
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


def _normalize_existing_context(
    existing_context: Mapping[str, Mapping[str, Any]] | None,
) -> tuple[bool, dict[str, dict[str, Any]]]:
    if not isinstance(existing_context, Mapping):
        return False, {}

    normalized: dict[str, dict[str, Any]] = {}
    for raw_name, raw_condition in existing_context.items():
        name = str(raw_name).strip()
        if not name or not isinstance(raw_condition, Mapping):
            return False, {}
        normalized[name] = copy.deepcopy(dict(raw_condition))
    return True, normalized


def merge_historical_site_event_site_condition_context(
    existing_context: Mapping[str, Mapping[str, Any]] | None,
    projection: HistoricalSiteEventSiteConditionContextProjection | None,
) -> HistoricalSiteEventSiteConditionContextMerge:
    """Build a fail-closed merged context candidate without injecting it."""

    existing_context_valid, existing = _normalize_existing_context(existing_context)
    projection_present = isinstance(
        projection,
        HistoricalSiteEventSiteConditionContextProjection,
    )
    projection_boundary_matched = bool(
        projection_present and projection.boundary == PROJECTION_BOUNDARY_NAME
    )
    context_projection_ready = bool(
        projection_present and projection.context_projection_ready is True
    )
    historical_projection = (
        projection.site_condition_context_projection if projection_present else {}
    )
    historical_projection_valid = bool(
        isinstance(historical_projection, Mapping)
        and len(historical_projection) == 1
        and all(
            str(name).strip() and isinstance(condition, Mapping)
            for name, condition in historical_projection.items()
        )
    )
    historical_condition_name = ""
    historical_condition: dict[str, Any] = {}
    if historical_projection_valid:
        raw_name, raw_condition = next(iter(historical_projection.items()))
        historical_condition_name = str(raw_name).strip()
        historical_condition = copy.deepcopy(dict(raw_condition))

    condition_name_collision = bool(
        historical_condition_name and historical_condition_name in existing
    )
    projection_contract_aligned = bool(
        projection_present
        and projection.package_present is True
        and projection.package_boundary_matched is True
        and projection.target_consumer_matched is True
        and projection.consumption_ready is True
        and projection.condition_name_present is True
        and projection.condition_view_present is True
        and projection.condition_name_aligned is True
        and projection.historical_condition_type_matched is True
        and projection.semantic_state_consumable is True
        and projection.package_contract_aligned is True
    )

    gates = (
        ("existing_context_valid", existing_context_valid),
        ("projection_present", projection_present),
        ("projection_boundary_matched", projection_boundary_matched),
        ("context_projection_ready", context_projection_ready),
        ("historical_projection_valid", historical_projection_valid),
        ("condition_name_no_collision", not condition_name_collision),
        ("projection_contract_aligned", projection_contract_aligned),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    merge_ready = not missing_gates

    merged: dict[str, dict[str, Any]] = {}
    if merge_ready:
        merged = copy.deepcopy(existing)
        merged[historical_condition_name] = historical_condition

    return HistoricalSiteEventSiteConditionContextMerge(
        boundary=BOUNDARY_NAME,
        existing_context_valid=existing_context_valid,
        projection_present=projection_present,
        projection_boundary_matched=projection_boundary_matched,
        context_projection_ready=context_projection_ready,
        historical_projection_valid=historical_projection_valid,
        historical_condition_name=historical_condition_name if merge_ready else "",
        condition_name_collision=condition_name_collision,
        projection_contract_aligned=projection_contract_aligned,
        missing_gates=missing_gates,
        merge_ready=merge_ready,
        merged_context_candidate=merged,
    )
