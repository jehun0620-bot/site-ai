"""STEP63 fail-closed collision policy for spatial and historical SITE registries."""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Mapping
from law_data.historical_site_event_builder_injection_payload import PROVENANCE
BOUNDARY_NAME = "HISTORICAL_SPATIAL_REGISTRY_COLLISION_POLICY"
SPATIAL_PROVENANCE = "RUNTIME_SPATIAL_CONDITION"

@dataclass(frozen=True)
class HistoricalSpatialRegistryCollisionPolicy:
    boundary: str
    spatial_registry_valid: bool
    historical_registry_valid: bool
    collision_names: tuple[str, ...]
    compatible_duplicate_names: tuple[str, ...]
    conflicting_collision_names: tuple[str, ...]
    merge_candidate_ready: bool
    merged_registry_candidate: Mapping[str, Mapping[str, Any]]

    def to_dict(self):
        return {
            **self.__dict__,
            "collision_names": list(self.collision_names),
            "compatible_duplicate_names": list(self.compatible_duplicate_names),
            "conflicting_collision_names": list(self.conflicting_collision_names),
            "merged_registry_candidate": copy.deepcopy(dict(self.merged_registry_candidate)),
            "implicit_precedence_used": False,
            "spatial_overlay_modified": False,
            "apply_site_registry_called": False,
            "rule_engine_modified": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "public_api_exposed": False,
        }

def _registry_valid(registry: Any, allowed_sources: set[str] | None = None) -> bool:
    if not isinstance(registry, Mapping):
        return False
    for name, resolved in registry.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(resolved, Mapping):
            return False
        if resolved.get("state") not in {"TRUE", "FALSE", "UNKNOWN", "UNSET"}:
            return False
        if not isinstance(resolved.get("confidence"), str) or not resolved.get("confidence").strip():
            return False
        source = resolved.get("source")
        if not isinstance(source, str) or not source.strip():
            return False
        if allowed_sources is not None and source not in allowed_sources:
            return False
    return True

def evaluate_historical_spatial_registry_collision_policy(spatial_registry: Mapping[str, Any] | None, historical_registry: Mapping[str, Any] | None):
    spatial_valid = _registry_valid(spatial_registry)
    historical_valid = _registry_valid(historical_registry, {PROVENANCE})
    spatial = copy.deepcopy(dict(spatial_registry)) if spatial_valid else {}
    historical = copy.deepcopy(dict(historical_registry)) if historical_valid else {}
    collisions = tuple(sorted(set(spatial) & set(historical)))
    compatible = []
    conflicting = []
    for name in collisions:
        if dict(spatial[name]) == dict(historical[name]):
            compatible.append(name)
        else:
            conflicting.append(name)
    ready = spatial_valid and historical_valid and not conflicting
    merged = copy.deepcopy(spatial) if ready else {}
    if ready:
        for name, resolved in historical.items():
            if name not in merged:
                merged[name] = copy.deepcopy(resolved)
    return HistoricalSpatialRegistryCollisionPolicy(
        BOUNDARY_NAME, spatial_valid, historical_valid, collisions,
        tuple(compatible), tuple(conflicting), ready, merged,
    )
