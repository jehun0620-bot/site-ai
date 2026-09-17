"""Final authorization before a district-unit-plan merged registry may be consumed live.

This gate validates the fail-closed collision-policy result and preserves the
verified district-unit-plan provenance. It authorizes a registry value for later
consumption only; it does not call the Rule Engine, modify the builder, or perform
production wiring itself.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from .district_unit_plan_site_truth_promotion_executor import REGISTRY_SOURCE
from .district_unit_plan_spatial_registry_collision_policy import (
    BOUNDARY_NAME as POLICY_BOUNDARY_NAME,
    DistrictUnitPlanSpatialRegistryCollisionPolicy,
)

BOUNDARY_NAME = "DISTRICT_UNIT_PLAN_MERGED_REGISTRY_LIVE_CONSUMPTION_AUTHORIZATION"


@dataclass(frozen=True)
class DistrictUnitPlanMergedRegistryLiveConsumptionAuthorization:
    boundary: str
    policy_present: bool
    policy_boundary_matched: bool
    merge_candidate_ready: bool
    no_conflicting_collision: bool
    no_unresolved_collision: bool
    candidate_registry_valid: bool
    district_provenance_preserved: bool
    missing_gates: tuple[str, ...]
    live_consumption_authorized: bool
    authorized_merged_registry: Mapping[str, Mapping[str, Any]]
    apply_site_registry_called: bool = False
    rule_engine_called: bool = False
    rule_engine_modified: bool = False
    builder_modified: bool = False
    production_wiring_applied: bool = False
    runtime_registered: bool = False
    public_api_exposed: bool = False

    @property
    def authorized(self) -> bool:
        return (
            self.boundary == BOUNDARY_NAME
            and self.policy_present
            and self.policy_boundary_matched
            and self.merge_candidate_ready
            and self.no_conflicting_collision
            and self.no_unresolved_collision
            and self.candidate_registry_valid
            and self.district_provenance_preserved
            and not self.missing_gates
            and self.live_consumption_authorized
            and bool(self.authorized_merged_registry)
            and self.apply_site_registry_called is False
            and self.rule_engine_called is False
            and self.rule_engine_modified is False
            and self.builder_modified is False
            and self.production_wiring_applied is False
            and self.runtime_registered is False
            and self.public_api_exposed is False
        )


def _candidate_valid(candidate: Any) -> bool:
    if not isinstance(candidate, Mapping) or not candidate:
        return False
    return all(
        isinstance(name, str)
        and bool(name.strip())
        and isinstance(resolved, Mapping)
        and str(resolved.get("state") or "").strip().upper()
        in {"TRUE", "FALSE", "UNKNOWN", "UNSET"}
        and isinstance(resolved.get("confidence"), str)
        and bool(resolved.get("confidence").strip())
        and isinstance(resolved.get("source"), str)
        and bool(resolved.get("source").strip())
        for name, resolved in candidate.items()
    )


def _district_provenance_preserved(candidate: Mapping[str, Any]) -> bool:
    """Reject forged district provenance/source combinations.

    A district-unit-plan entry produced by this lane may appear with its HYBRID
    source when newly inserted. If the spatial registry already had a compatible
    TRUE entry, the collision policy deliberately preserves that spatial entry;
    that source is also allowed. Any entry claiming the verified HYBRID provenance
    must use the exact district source.
    """

    resolved = candidate.get("지구단위계획")
    if resolved is None:
        return False
    if not isinstance(resolved, Mapping):
        return False

    state = str(resolved.get("state") or "").strip().upper()
    source = str(resolved.get("source") or "").strip()
    provenance = resolved.get("provenance")
    if state != "TRUE":
        return False

    if provenance == "HYBRID_SPATIAL_NOTICE_VERIFIED":
        return source == REGISTRY_SOURCE

    return source == "RUNTIME_SPATIAL_CONDITION" and provenance in {None, ""}


def authorize_district_unit_plan_merged_registry_live_consumption(
    policy: DistrictUnitPlanSpatialRegistryCollisionPolicy | None,
) -> DistrictUnitPlanMergedRegistryLiveConsumptionAuthorization:
    """Authorize only a validated, conflict-free merged registry candidate."""

    present = isinstance(policy, DistrictUnitPlanSpatialRegistryCollisionPolicy)
    boundary_matched = bool(present and policy.boundary == POLICY_BOUNDARY_NAME)
    ready = bool(present and policy.ready and policy.merge_candidate_ready)
    no_conflict = bool(present and not policy.conflicting_collision)
    no_unresolved = bool(present and not policy.unresolved_collision)
    candidate = (
        copy.deepcopy(dict(policy.merged_registry_candidate)) if present else {}
    )
    candidate_valid = _candidate_valid(candidate)
    provenance_preserved = bool(
        candidate_valid and _district_provenance_preserved(candidate)
    )

    gates = (
        ("policy_present", present),
        ("policy_boundary_matched", boundary_matched),
        ("merge_candidate_ready", ready),
        ("no_conflicting_collision", no_conflict),
        ("no_unresolved_collision", no_unresolved),
        ("candidate_registry_valid", candidate_valid),
        ("district_provenance_preserved", provenance_preserved),
    )
    missing = tuple(name for name, passed in gates if not passed)
    authorized = not missing

    return DistrictUnitPlanMergedRegistryLiveConsumptionAuthorization(
        boundary=BOUNDARY_NAME,
        policy_present=present,
        policy_boundary_matched=boundary_matched,
        merge_candidate_ready=ready,
        no_conflicting_collision=no_conflict,
        no_unresolved_collision=no_unresolved,
        candidate_registry_valid=candidate_valid,
        district_provenance_preserved=provenance_preserved,
        missing_gates=missing,
        live_consumption_authorized=authorized,
        authorized_merged_registry=candidate if authorized else {},
    )
