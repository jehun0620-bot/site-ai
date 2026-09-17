"""Typed production transport for a verified district-unit registry candidate.

This boundary does not decide SITE truth, merge registries, call the Rule Engine,
or register runtime state. It only seals the already-verified district-unit
promotion bridge output to its canonical parcel PNU so later production layers
can fail closed on raw, malformed, or cross-PNU injection.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from .district_unit_plan_site_truth_promotion_executor import REGISTRY_SOURCE
from .district_unit_plan_site_truth_promotion_rule_input_bridge import (
    BOUNDARY_NAME as BRIDGE_BOUNDARY_NAME,
    CONDITION_NAME,
    DistrictUnitPlanSiteTruthPromotionRuleInputBridge,
)

BOUNDARY_NAME = "DISTRICT_UNIT_PLAN_VERIFIED_REGISTRY_CANDIDATE_ENVELOPE"


def _candidate_valid(
    canonical_pnu: str,
    registry_candidate: Mapping[str, Any],
) -> bool:
    if not isinstance(registry_candidate, Mapping):
        return False
    if set(registry_candidate.keys()) != {CONDITION_NAME}:
        return False

    entry = registry_candidate.get(CONDITION_NAME)
    if not isinstance(entry, Mapping):
        return False

    return bool(
        entry.get("state") == "TRUE"
        and entry.get("confidence") == "HIGH"
        and entry.get("source") == REGISTRY_SOURCE
        and entry.get("pnu") == canonical_pnu
        and entry.get("provenance") == "HYBRID_SPATIAL_NOTICE_VERIFIED"
    )


@dataclass(frozen=True)
class DistrictUnitPlanVerifiedRegistryCandidateEnvelope:
    boundary: str
    canonical_pnu: str
    registry_candidate: Mapping[str, Mapping[str, Any]]
    verified: bool
    site_truth_decided: bool = False
    registry_merged: bool = False
    collision_policy_called: bool = False
    rule_engine_called: bool = False
    builder_modified: bool = False
    runtime_registered: bool = False
    public_api_exposed: bool = False

    @property
    def ready(self) -> bool:
        return bool(
            self.boundary == BOUNDARY_NAME
            and self.verified is True
            and len(self.canonical_pnu) == 19
            and self.canonical_pnu.isdigit()
            and _candidate_valid(
                self.canonical_pnu,
                self.registry_candidate,
            )
            and self.site_truth_decided is False
            and self.registry_merged is False
            and self.collision_policy_called is False
            and self.rule_engine_called is False
            and self.builder_modified is False
            and self.runtime_registered is False
            and self.public_api_exposed is False
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "canonical_pnu": self.canonical_pnu,
            "registry_candidate": copy.deepcopy(dict(self.registry_candidate)),
            "verified": self.verified,
            "ready": self.ready,
            "site_truth_decided": self.site_truth_decided,
            "registry_merged": self.registry_merged,
            "collision_policy_called": self.collision_policy_called,
            "rule_engine_called": self.rule_engine_called,
            "builder_modified": self.builder_modified,
            "runtime_registered": self.runtime_registered,
            "public_api_exposed": self.public_api_exposed,
        }


def seal_verified_district_unit_plan_registry_candidate(
    bridge: DistrictUnitPlanSiteTruthPromotionRuleInputBridge | None,
) -> DistrictUnitPlanVerifiedRegistryCandidateEnvelope:
    present = isinstance(
        bridge,
        DistrictUnitPlanSiteTruthPromotionRuleInputBridge,
    )
    bridge_valid = bool(
        present
        and bridge.boundary == BRIDGE_BOUNDARY_NAME
        and bridge.ready
    )

    pnu = str(bridge.canonical_pnu or "").strip() if present else ""
    candidate = (
        copy.deepcopy(dict(bridge.registry_candidate))
        if present and isinstance(bridge.registry_candidate, Mapping)
        else {}
    )

    verified = bool(
        bridge_valid
        and len(pnu) == 19
        and pnu.isdigit()
        and _candidate_valid(pnu, candidate)
    )

    return DistrictUnitPlanVerifiedRegistryCandidateEnvelope(
        boundary=BOUNDARY_NAME,
        canonical_pnu=pnu if verified else "",
        registry_candidate=candidate if verified else {},
        verified=verified,
    )
