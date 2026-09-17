"""Fail-closed collision policy for spatial and district-unit-plan registries.

This boundary compares one verified district-unit-plan registry candidate with the
current spatial SITE registry. It never gives implicit precedence to either side.
UNKNOWN or conflicting same-name spatial states block merging. No Rule Engine or
builder call occurs here.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from .district_unit_plan_site_truth_promotion_executor import REGISTRY_SOURCE
from .district_unit_plan_site_truth_promotion_rule_input_bridge import CONDITION_NAME

BOUNDARY_NAME = "DISTRICT_UNIT_PLAN_SPATIAL_REGISTRY_COLLISION_POLICY"
SPATIAL_SOURCE = "RUNTIME_SPATIAL_CONDITION"


@dataclass(frozen=True)
class DistrictUnitPlanSpatialRegistryCollisionPolicy:
    boundary: str
    spatial_registry_valid: bool
    district_registry_valid: bool
    district_condition_present: bool
    collision_present: bool
    spatial_collision_state: str | None
    district_collision_state: str | None
    compatible_collision: bool
    conflicting_collision: bool
    unresolved_collision: bool
    merge_candidate_ready: bool
    canonical_pnu: str
    merged_registry_candidate: Mapping[str, Mapping[str, Any]]
    implicit_precedence_used: bool = False
    site_registry_mutated: bool = False
    rule_engine_called: bool = False
    builder_modified: bool = False
    runtime_registered: bool = False
    public_api_exposed: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.boundary == BOUNDARY_NAME
            and self.spatial_registry_valid
            and self.district_registry_valid
            and self.district_condition_present
            and self.merge_candidate_ready
            and len(self.canonical_pnu) == 19
            and self.canonical_pnu.isdigit()
            and not self.conflicting_collision
            and not self.unresolved_collision
            and bool(self.merged_registry_candidate)
            and self.implicit_precedence_used is False
            and self.site_registry_mutated is False
            and self.rule_engine_called is False
            and self.builder_modified is False
            and self.runtime_registered is False
            and self.public_api_exposed is False
        )


def _valid_state(value: Any) -> bool:
    return str(value or "").strip().upper() in {"TRUE", "FALSE", "UNKNOWN", "UNSET"}


def _spatial_registry_valid(registry: Any) -> bool:
    if not isinstance(registry, Mapping):
        return False
    for name, resolved in registry.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(resolved, Mapping):
            return False
        if not _valid_state(resolved.get("state")):
            return False
        confidence = resolved.get("confidence")
        if not isinstance(confidence, str) or not confidence.strip():
            return False
        source = resolved.get("source")
        if not isinstance(source, str) or not source.strip():
            return False
    return True


def _district_registry_valid(registry: Any) -> bool:
    if not isinstance(registry, Mapping) or set(registry) != {CONDITION_NAME}:
        return False
    resolved = registry.get(CONDITION_NAME)
    return bool(
        isinstance(resolved, Mapping)
        and str(resolved.get("state") or "").strip().upper() == "TRUE"
        and str(resolved.get("confidence") or "").strip().upper() == "HIGH"
        and resolved.get("source") == REGISTRY_SOURCE
        and isinstance(resolved.get("pnu"), str)
        and len(resolved.get("pnu")) == 19
        and resolved.get("pnu").isdigit()
        and resolved.get("provenance") == "HYBRID_SPATIAL_NOTICE_VERIFIED"
    )


def evaluate_district_unit_plan_spatial_registry_collision_policy(
    spatial_registry: Mapping[str, Any] | None,
    district_registry: Mapping[str, Any] | None,
) -> DistrictUnitPlanSpatialRegistryCollisionPolicy:
    """Return a merge candidate only when no unresolved/conflicting collision exists."""

    spatial_valid = _spatial_registry_valid(spatial_registry)
    district_valid = _district_registry_valid(district_registry)
    spatial = copy.deepcopy(dict(spatial_registry)) if spatial_valid else {}
    district = copy.deepcopy(dict(district_registry)) if district_valid else {}
    district_present = district_valid and CONDITION_NAME in district
    canonical_pnu = (
        str(district[CONDITION_NAME].get("pnu") or "").strip()
        if district_present
        else ""
    )
    collision = bool(spatial_valid and district_present and CONDITION_NAME in spatial)

    spatial_state = None
    district_state = None
    compatible = False
    conflicting = False
    unresolved = False

    if district_present:
        district_state = str(district[CONDITION_NAME].get("state") or "").strip().upper()
    if collision:
        spatial_state = str(spatial[CONDITION_NAME].get("state") or "").strip().upper()
        if spatial_state == "UNKNOWN" or spatial_state == "UNSET":
            unresolved = True
        elif spatial_state == district_state:
            compatible = True
        else:
            conflicting = True

    ready = bool(
        spatial_valid
        and district_valid
        and district_present
        and not conflicting
        and not unresolved
    )

    merged: Mapping[str, Mapping[str, Any]] = {}
    if ready:
        merged_dict = copy.deepcopy(spatial)
        if not collision:
            merged_dict[CONDITION_NAME] = copy.deepcopy(district[CONDITION_NAME])
        elif compatible:
            # Same state is compatible, but preserve the current spatial entry here.
            # A later live-consumption boundary may decide how provenance is exposed.
            pass
        merged = merged_dict

    return DistrictUnitPlanSpatialRegistryCollisionPolicy(
        boundary=BOUNDARY_NAME,
        spatial_registry_valid=spatial_valid,
        district_registry_valid=district_valid,
        district_condition_present=district_present,
        collision_present=collision,
        spatial_collision_state=spatial_state,
        district_collision_state=district_state,
        compatible_collision=compatible,
        conflicting_collision=conflicting,
        unresolved_collision=unresolved,
        merge_candidate_ready=ready,
        canonical_pnu=canonical_pnu if ready else "",
        merged_registry_candidate=merged,
    )
