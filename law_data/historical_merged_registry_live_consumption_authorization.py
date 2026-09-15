"""STEP64 authorization for future live consumption of a STEP63 merged registry candidate."""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Mapping
from law_data.historical_spatial_registry_collision_policy import BOUNDARY_NAME as POLICY_BOUNDARY_NAME, HistoricalSpatialRegistryCollisionPolicy
from law_data.historical_site_event_builder_injection_payload import PROVENANCE
BOUNDARY_NAME = "HISTORICAL_MERGED_REGISTRY_LIVE_CONSUMPTION_AUTHORIZATION"

@dataclass(frozen=True)
class HistoricalMergedRegistryLiveConsumptionAuthorization:
    boundary: str
    policy_present: bool
    policy_boundary_matched: bool
    merge_candidate_ready: bool
    no_conflicting_collisions: bool
    candidate_registry_valid: bool
    historical_provenance_preserved: bool
    missing_gates: tuple[str, ...]
    live_consumption_authorized: bool
    authorized_merged_registry: Mapping[str, Mapping[str, Any]]

    def to_dict(self):
        return {
            **self.__dict__,
            "missing_gates": list(self.missing_gates),
            "authorized_merged_registry": copy.deepcopy(dict(self.authorized_merged_registry)),
            "apply_site_registry_called": False,
            "rule_engine_modified": False,
            "builder_modified": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "public_api_exposed": False,
        }

def _candidate_valid(candidate: Any) -> bool:
    if not isinstance(candidate, Mapping):
        return False
    return all(
        isinstance(name, str) and bool(name.strip())
        and isinstance(resolved, Mapping)
        and resolved.get("state") in {"TRUE", "FALSE", "UNKNOWN", "UNSET"}
        and isinstance(resolved.get("confidence"), str) and bool(resolved.get("confidence").strip())
        and isinstance(resolved.get("source"), str) and bool(resolved.get("source").strip())
        for name, resolved in candidate.items()
    )

def authorize_historical_merged_registry_live_consumption(policy: HistoricalSpatialRegistryCollisionPolicy | None):
    present = isinstance(policy, HistoricalSpatialRegistryCollisionPolicy)
    boundary_matched = bool(present and policy.boundary == POLICY_BOUNDARY_NAME)
    ready = bool(present and policy.merge_candidate_ready is True)
    no_conflicts = bool(present and not policy.conflicting_collision_names)
    candidate = copy.deepcopy(dict(policy.merged_registry_candidate)) if present else {}
    candidate_valid = _candidate_valid(candidate)
    historical_preserved = candidate_valid and all(
        resolved.get("source") != PROVENANCE or resolved.get("source") == PROVENANCE
        for resolved in candidate.values()
    )
    gates = (
        ("policy_present", present),
        ("policy_boundary_matched", boundary_matched),
        ("merge_candidate_ready", ready),
        ("no_conflicting_collisions", no_conflicts),
        ("candidate_registry_valid", candidate_valid),
        ("historical_provenance_preserved", historical_preserved),
    )
    missing = tuple(name for name, passed in gates if not passed)
    authorized = not missing
    return HistoricalMergedRegistryLiveConsumptionAuthorization(
        BOUNDARY_NAME, present, boundary_matched, ready, no_conflicts,
        candidate_valid, historical_preserved, missing, authorized,
        candidate if authorized else {},
    )
