"""Normalize authorized SITE registries into one non-executing verified envelope.

This is a common plug boundary between family-specific live-consumption
authorizations and the existing Rule Engine. It does not call the Rule Engine,
modify the builder, merge registries, or register runtime state.
"""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Mapping

from .historical_merged_registry_live_consumption_authorization import HistoricalMergedRegistryLiveConsumptionAuthorization
from .district_unit_plan_merged_registry_live_consumption_authorization import DistrictUnitPlanMergedRegistryLiveConsumptionAuthorization

BOUNDARY_NAME = "COMMON_VERIFIED_SITE_REGISTRY_LIVE_CONSUMPTION"
HISTORICAL = "HISTORICAL_SITE_EVENT"
DISTRICT_UNIT_PLAN = "DISTRICT_UNIT_PLAN_HYBRID"

@dataclass(frozen=True)
class CommonVerifiedSiteRegistryLiveConsumption:
    boundary: str
    source_family: str
    source_authorization_verified: bool
    candidate_registry_valid: bool
    verified_site_registry: Mapping[str, Mapping[str, Any]]
    missing_gates: tuple[str, ...]
    consumption_ready: bool
    rule_engine_called: bool = False
    builder_modified: bool = False
    production_wiring_applied: bool = False
    runtime_registered: bool = False
    public_api_exposed: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.boundary == BOUNDARY_NAME
            and self.source_family in {HISTORICAL, DISTRICT_UNIT_PLAN}
            and self.source_authorization_verified
            and self.candidate_registry_valid
            and bool(self.verified_site_registry)
            and not self.missing_gates
            and self.consumption_ready
            and self.rule_engine_called is False
            and self.builder_modified is False
            and self.production_wiring_applied is False
            and self.runtime_registered is False
            and self.public_api_exposed is False
        )

    def to_dict(self):
        return {**self.__dict__, "verified_site_registry": copy.deepcopy(dict(self.verified_site_registry)), "missing_gates": list(self.missing_gates), "ready": self.ready}

def _registry_valid(candidate: Any) -> bool:
    if not isinstance(candidate, Mapping) or not candidate:
        return False
    return all(
        isinstance(name, str) and bool(name.strip())
        and isinstance(resolved, Mapping)
        and str(resolved.get("state") or "").strip().upper() in {"TRUE", "FALSE", "UNKNOWN", "UNSET"}
        and isinstance(resolved.get("confidence"), str) and bool(resolved.get("confidence").strip())
        and isinstance(resolved.get("source"), str) and bool(resolved.get("source").strip())
        for name, resolved in candidate.items()
    )

def normalize_verified_site_registry_live_consumption(authorization: Any) -> CommonVerifiedSiteRegistryLiveConsumption:
    family = ""
    source_verified = False
    candidate: Mapping[str, Mapping[str, Any]] = {}

    if isinstance(authorization, HistoricalMergedRegistryLiveConsumptionAuthorization):
        family = HISTORICAL
        source_verified = bool(authorization.live_consumption_authorized and not authorization.missing_gates)
        if source_verified:
            candidate = copy.deepcopy(dict(authorization.authorized_merged_registry))
    elif isinstance(authorization, DistrictUnitPlanMergedRegistryLiveConsumptionAuthorization):
        family = DISTRICT_UNIT_PLAN
        source_verified = bool(authorization.authorized and authorization.live_consumption_authorized and not authorization.missing_gates)
        if source_verified:
            candidate = copy.deepcopy(dict(authorization.authorized_merged_registry))

    candidate_valid = _registry_valid(candidate)
    gates = (("source_authorization_verified", source_verified), ("candidate_registry_valid", candidate_valid))
    missing = tuple(name for name, passed in gates if not passed)
    ready = bool(family and not missing)
    return CommonVerifiedSiteRegistryLiveConsumption(
        boundary=BOUNDARY_NAME,
        source_family=family,
        source_authorization_verified=source_verified,
        candidate_registry_valid=candidate_valid,
        verified_site_registry=candidate if ready else {},
        missing_gates=missing,
        consumption_ready=ready,
    )
